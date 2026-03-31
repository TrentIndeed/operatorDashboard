"""
GitHub integration — syncs repo data and project commit history.
"""
import os
from datetime import datetime, timezone
from typing import List

import httpx
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from db.database import get_db, GithubRepo, Project
from models.schemas import GithubRepoOut

router = APIRouter(prefix="/github", tags=["github"])

GITHUB_API = "https://api.github.com"


def _github_headers() -> dict:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise HTTPException(status_code=500, detail="GITHUB_TOKEN not set in environment")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def _fetch_repo(owner: str, repo: str) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{GITHUB_API}/repos/{owner}/{repo}", headers=_github_headers())
        resp.raise_for_status()
        return resp.json()


async def _fetch_latest_commit(owner: str, repo: str) -> dict | None:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/commits",
            headers=_github_headers(),
            params={"per_page": 1},
        )
        if resp.status_code == 409:  # empty repo
            return None
        resp.raise_for_status()
        commits = resp.json()
        return commits[0] if commits else None


async def _fetch_open_prs(owner: str, repo: str) -> int:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/pulls",
            headers=_github_headers(),
            params={"state": "open", "per_page": 1},
        )
        resp.raise_for_status()
        # GitHub returns paginated, check Link header for total or just count returned
        link = resp.headers.get("Link", "")
        if 'rel="last"' in link:
            # Extract last page number for approximate count
            import re
            match = re.search(r'page=(\d+)>; rel="last"', link)
            if match:
                return int(match.group(1))
        return len(resp.json())


async def sync_repo(owner: str, repo_name: str, db: Session) -> GithubRepo:
    """Fetch fresh data from GitHub and upsert into DB."""
    repo_data = await _fetch_repo(owner, repo_name)
    latest_commit = await _fetch_latest_commit(owner, repo_name)

    commit_sha = None
    commit_message = None
    commit_at = None
    days_since = None

    if latest_commit:
        commit_sha = latest_commit["sha"][:7]
        commit_message = latest_commit["commit"]["message"].split("\n")[0][:120]
        commit_at_str = latest_commit["commit"]["committer"]["date"]
        commit_at = datetime.fromisoformat(commit_at_str.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - commit_at
        days_since = delta.days

    full_name = f"{owner}/{repo_name}"
    db_repo = db.query(GithubRepo).filter(GithubRepo.full_name == full_name).first()

    if db_repo:
        db_repo.stars = repo_data.get("stargazers_count", 0)
        db_repo.open_issues = repo_data.get("open_issues_count", 0)
        db_repo.description = repo_data.get("description")
        db_repo.last_commit_sha = commit_sha
        db_repo.last_commit_message = commit_message
        db_repo.last_commit_at = commit_at
        db_repo.synced_at = datetime.utcnow()
    else:
        db_repo = GithubRepo(
            owner=owner,
            name=repo_name,
            full_name=full_name,
            description=repo_data.get("description"),
            stars=repo_data.get("stargazers_count", 0),
            open_issues=repo_data.get("open_issues_count", 0),
            open_prs=0,
            last_commit_sha=commit_sha,
            last_commit_message=commit_message,
            last_commit_at=commit_at,
            is_private=repo_data.get("private", True),
        )
        db.add(db_repo)

    # Also update related project's commit info
    project = db.query(Project).filter(
        Project.github_repo.contains(repo_name)
    ).first()
    if project:
        project.last_commit_at = commit_at
        project.days_since_commit = days_since

    db.commit()
    db.refresh(db_repo)
    return db_repo


@router.get("/repos", response_model=List[GithubRepoOut])
def get_repos(db: Session = Depends(get_db)):
    return db.query(GithubRepo).order_by(GithubRepo.last_commit_at.desc()).all()


@router.post("/sync/{owner}/{repo}", response_model=GithubRepoOut)
async def sync_single_repo(owner: str, repo: str, db: Session = Depends(get_db)):
    """Manually trigger a sync for a specific repo."""
    try:
        result = await sync_repo(owner, repo, db)
        return result
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))


def _bg_sync_all_repos():
    """Background: auto-discover and sync ALL user repos from GitHub API."""
    import asyncio
    from db.database import SessionLocal

    async def _do_sync():
        db = SessionLocal()
        try:
            owner = os.getenv("GITHUB_OWNER")
            token = os.getenv("GITHUB_TOKEN")
            if not owner or not token:
                return

            # Fetch all repos from GitHub (auto-discover, not manual)
            headers = _github_headers()
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{GITHUB_API}/user/repos",
                    headers=headers,
                    params={"per_page": 100, "sort": "pushed"},
                )
                if resp.status_code != 200:
                    print(f"[GitHub] Failed to list repos: {resp.status_code}")
                    return

                all_repos = resp.json()

            synced = 0
            for repo_data in all_repos:
                repo_name = repo_data["name"]
                try:
                    await sync_repo(owner, repo_name, db)
                    synced += 1
                except Exception as e:
                    print(f"[GitHub] sync {repo_name} failed: {e}")

            print(f"[GitHub] Synced {synced}/{len(all_repos)} repos")
        finally:
            db.close()

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_do_sync())
        else:
            asyncio.run(_do_sync())
    except RuntimeError:
        asyncio.run(_do_sync())


@router.post("/sync-all")
async def sync_all_repos(background_tasks: BackgroundTasks):
    """Sync all tracked repos in the background."""
    background_tasks.add_task(_bg_sync_all_repos)
    return {"status": "syncing", "message": "Syncing all GitHub repos..."}
