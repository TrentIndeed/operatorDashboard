"""
Operator Dashboard — FastAPI Backend
"""
import os
from datetime import datetime, timedelta, date
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from db.database import (
    init_db, get_db, Project, Goal, Task, AISuggestion, ContentDraft, ContentScheduleItem,
    SocialMetric, ContentScore, Competitor, CompetitorPost, MarketGap, Lead, CommentReply, WaitlistSignup,
)
from api.tasks import router as tasks_router, goals_router, suggestions_router, briefing_router, command_router
from api.projects import router as projects_router
from api.github_sync import router as github_router
from api.content import router as content_router
from api.analytics import router as analytics_router
from api.market_intel import router as market_intel_router
from api.leads import router as leads_router
from api.google_auth import router as google_auth_router
from api.social_sync import router as social_sync_router
from api.billing import router as billing_router
from api.settings import router as settings_router
from api.sms_webhook import router as sms_router
from api.support_chat import router as support_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables
    init_db()
    # Seed initial data if empty
    _seed_initial_data()
    yield


def _seed_initial_data():
    """No seed data — dashboard starts empty. Users add their own projects via the API or UI.
    AI Generate populates tasks, suggestions, drafts, and briefing on first run."""
    pass


app = FastAPI(
    title="Operator Dashboard API",
    description="Backend for the AI-powered solo founder command center",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(command_router)
app.include_router(tasks_router)
app.include_router(goals_router)
app.include_router(suggestions_router)
app.include_router(briefing_router)
app.include_router(projects_router)
app.include_router(github_router)
app.include_router(content_router)
app.include_router(analytics_router)
app.include_router(market_intel_router)
app.include_router(leads_router)
app.include_router(google_auth_router)
app.include_router(social_sync_router)
app.include_router(billing_router)
app.include_router(settings_router)
app.include_router(sms_router)
app.include_router(support_router)


# --- Background task wrappers (create their own DB sessions) ---

def _bg_generate_tasks():
    """Background wrapper: creates its own session so it works after request ends."""
    from db.database import SessionLocal
    from agents.task_prioritizer import generate_priority_tasks
    db = SessionLocal()
    try:
        generate_priority_tasks(db)
    except Exception as e:
        print(f"[AI] generate_priority_tasks failed: {e}")
    finally:
        db.close()


def _bg_generate_suggestions():
    from db.database import SessionLocal
    from agents.task_prioritizer import generate_suggestions
    db = SessionLocal()
    try:
        generate_suggestions(db)
    except Exception as e:
        print(f"[AI] generate_suggestions failed: {e}")
    finally:
        db.close()


def _bg_scan_market():
    from db.database import SessionLocal
    from agents.market_intel import scan_market_gaps
    db = SessionLocal()
    try:
        scan_market_gaps(db)
    except Exception as e:
        print(f"[AI] scan_market_gaps failed: {e}")
    finally:
        db.close()


def _bg_generate_briefing():
    """Background: generate today's news briefing via Claude."""
    from db.database import SessionLocal, NewsBriefing
    from agents.reasoning import reason_json
    db = SessionLocal()
    try:
        # Clear old briefing items for today
        today_str = date.today().isoformat()
        db.query(NewsBriefing).filter(NewsBriefing.briefing_date == today_str).delete()

        projects = db.query(Project).all()
        context = {
            "date": today_str,
            "projects": [{"name": p.name, "description": p.description} for p in projects],
        }

        prompt = """Generate 5 briefing items for a solo founder focused on business growth. Mix of:

- 2 items about growth opportunities (trending topics, viral formats, community discussions to join)
- 1 item about competitors or market shifts
- 1 item about platform/algorithm changes (TikTok, YouTube, Twitter, Reddit)
- 1 item about the founder's industry/niche

Each should include a SPECIFIC action the founder can take TODAY.

Return ONLY a JSON array of 5 objects:
{
  "headline": "Short headline",
  "summary": "1-2 sentence summary",
  "category": "growth | competitor | platform | industry | content",
  "relevance_score": 0.0 to 1.0,
  "suggested_action": "Specific action to take today"
}

Return ONLY the JSON array, nothing else."""

        result = reason_json(prompt, context=context)
        # Handle both list and dict wrapper (e.g. {"items": [...]})
        if isinstance(result, dict):
            items = result.get("items") or result.get("briefing") or result.get("news") or next(
                (v for v in result.values() if isinstance(v, list)), []
            )
        elif isinstance(result, list):
            items = result
        else:
            print(f"[AI] briefing returned unexpected type: {type(result)}")
            return

        for item in items[:5]:
            if not isinstance(item, dict):
                continue
            db.add(NewsBriefing(
                headline=item.get("headline", ""),
                summary=item.get("summary"),
                category=item.get("category"),
                relevance_score=float(item.get("relevance_score", 0.5)),
                suggested_action=item.get("suggested_action"),
                briefing_date=today_str,
            ))

        db.commit()
        print(f"[AI] Generated {min(len(items), 5)} briefing items")
    except Exception as e:
        print(f"[AI] generate_briefing failed: {e}")
    finally:
        db.close()


def _bg_sync_github():
    """Background wrapper for GitHub sync — uses sync API via httpx."""
    import asyncio
    from db.database import SessionLocal
    from api.github_sync import sync_repo

    async def _do_sync():
        db = SessionLocal()
        try:
            owner = os.getenv("GITHUB_OWNER")
            if not owner:
                return
            # Sync all projects that have a github_repo set
            projects = db.query(Project).filter(Project.github_repo.isnot(None)).all()
            for p in projects:
                if not p.github_repo:
                    continue
                try:
                    await sync_repo(owner, p.github_repo, db)
                    print(f"[GitHub] synced {p.github_repo}")
                except Exception as e:
                    print(f"[GitHub] sync {p.github_repo} failed: {e}")

            # After syncing, ask Claude to update project stages based on commit history
            _update_project_stages_from_commits(db, owner)
        finally:
            db.close()

    # Run the async function in an event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_do_sync())
        else:
            asyncio.run(_do_sync())
    except RuntimeError:
        asyncio.run(_do_sync())


def _update_project_stages_from_commits(db, owner: str):
    """After GitHub sync, ask Claude to infer project stages from recent commits."""
    from db.database import GithubRepo
    from agents.reasoning import reason_json
    import httpx

    projects = db.query(Project).filter(Project.github_repo.isnot(None)).all()
    if not projects:
        return

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return

    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}

    project_data = []
    for p in projects:
        if not p.github_repo:
            continue
        # Fetch last 10 commits
        try:
            import httpx as hx
            resp = hx.get(
                f"https://api.github.com/repos/{owner}/{p.github_repo}/commits",
                headers=headers,
                params={"per_page": 10},
                timeout=15,
            )
            if resp.status_code != 200:
                continue
            commits = [c["commit"]["message"].split("\n")[0][:80] for c in resp.json()]
        except Exception:
            commits = []

        project_data.append({
            "name": p.name,
            "slug": p.slug,
            "description": p.description,
            "current_stage": p.current_stage,
            "total_stages": p.total_stages,
            "stage_label": p.stage_label,
            "recent_commits": commits,
        })

    if not project_data:
        return

    prompt = """Based on the recent commits for each project, update the project stage, stage_label, blockers, and next_milestone.

Return a JSON array with one object per project:
[
  {
    "slug": "project-slug",
    "current_stage": integer (1 to total_stages),
    "stage_label": "Current stage description based on what commits show",
    "blockers": "Any apparent blockers from commit messages, or null",
    "next_milestone": "What should come next"
  }
]

Only update stages if the commits clearly indicate progress. If unsure, keep the current stage."""

    try:
        result = reason_json(prompt, context={"projects": project_data})
        if not isinstance(result, list):
            result = next((v for v in result.values() if isinstance(v, list)), []) if isinstance(result, dict) else []

        for update in result:
            if not isinstance(update, dict) or "slug" not in update:
                continue
            p = db.query(Project).filter(Project.slug == update["slug"]).first()
            if not p:
                continue
            if "current_stage" in update:
                p.current_stage = min(int(update["current_stage"]), p.total_stages)
            if update.get("stage_label"):
                p.stage_label = update["stage_label"]
            if "blockers" in update:
                p.blockers = update["blockers"] if update["blockers"] else None
            if update.get("next_milestone"):
                p.next_milestone = update["next_milestone"]

        db.commit()
        print(f"[AI] Updated {len(result)} project stages from commits")
    except Exception as e:
        print(f"[AI] Project stage update failed: {e}")


def _bg_sync_social():
    """Background: sync social media platforms."""
    import asyncio

    async def _do_sync():
        from db.database import SessionLocal
        from api.social_sync import sync_all_platforms
        db = SessionLocal()
        try:
            result = await sync_all_platforms(db)
            print(f"[Social] Synced: {result}")
        except Exception as e:
            print(f"[Social] sync failed: {e}")
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


def _bg_generate_draft_and_schedule(topic: str, platform: str, content_type: str, project_tag: str, day_offset: int = 1):
    """Background: generate a content draft and schedule it day_offset days from now.
    Replaces old AI-generated drafts for the same platform to avoid duplicates."""
    from db.database import SessionLocal
    from agents.content_drafter import generate_draft
    db = SessionLocal()
    try:
        # Remove old AI-generated draft drafts for this platform (replace, don't stack)
        old_drafts = (
            db.query(ContentDraft)
            .filter(ContentDraft.ai_generated == True, ContentDraft.platform == platform, ContentDraft.status == "draft")
            .all()
        )
        old_draft_ids = [d.id for d in old_drafts]
        for d in old_drafts:
            db.delete(d)
        # Also remove their schedule items
        if old_draft_ids:
            db.query(ContentScheduleItem).filter(ContentScheduleItem.draft_id.in_(old_draft_ids)).delete(synchronize_session=False)
        db.commit()

        result = generate_draft(topic, platform, content_type, project_tag)
        if not isinstance(result, dict):
            print(f"[AI] generate_draft returned non-dict: {type(result)}")
            return

        # Schedule on the next available day (skip days off)
        import json as _json
        from db.database import User
        user = db.query(User).first()
        day_names = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        user_schedule = {}
        if user and user.weekly_hours:
            try:
                user_schedule = _json.loads(user.weekly_hours)
            except (_json.JSONDecodeError, TypeError):
                pass

        # Find next available day starting from day_offset
        sched_dt = datetime.utcnow() + timedelta(days=day_offset)
        for attempt in range(7):
            day_key = day_names[sched_dt.weekday()]
            if user_schedule.get(day_key, 2) > 0:
                break
            sched_dt += timedelta(days=1)

        sched_dt = sched_dt.replace(hour=10, minute=0, second=0, microsecond=0)
        sched_time_str = sched_dt.isoformat()

        # Parse hook_score to float
        hook_score = result.get("hook_score")
        if hook_score is not None:
            try:
                hook_score = float(hook_score) / (10.0 if float(hook_score) > 1 else 1.0)
            except (ValueError, TypeError):
                hook_score = None

        draft = ContentDraft(
            title=result.get("title", topic) or topic,
            body=result.get("body", "") or "",
            platform=platform,
            content_type=content_type,
            hook=result.get("hook"),
            cta=result.get("cta"),
            hashtags=result.get("hashtags"),
            status="draft",
            ai_generated=True,
            project_tag=project_tag,
            hook_score=hook_score,
            suggested_post_time=sched_time_str or sched_dt.isoformat(),
        )
        db.add(draft)
        db.commit()
        db.refresh(draft)
        print(f"[AI] Created draft: {draft.title[:60]}")

        # Auto-schedule the draft
        schedule_item = ContentScheduleItem(
            draft_id=draft.id,
            title=draft.title,
            platform=platform,
            scheduled_at=sched_dt,
            status="scheduled",
            block_type="content",
            color="#A855F7",
        )
        db.add(schedule_item)
        db.commit()
        print(f"[AI] Scheduled draft for {sched_dt}")
    except Exception as e:
        print(f"[AI] generate_draft_and_schedule failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


# --- AI Rate Limiting ---
import time as _time

_ai_endpoint_timestamps: list[float] = []
_AI_ENDPOINT_LIMIT = int(os.getenv("AI_ENDPOINT_LIMIT_PER_HOUR", "10"))


def _check_ai_endpoint_limit():
    """Prevent spamming AI endpoints. Raises HTTPException if too many calls."""
    now = _time.time()
    cutoff = now - 3600
    _ai_endpoint_timestamps[:] = [t for t in _ai_endpoint_timestamps if t > cutoff]
    if len(_ai_endpoint_timestamps) >= _AI_ENDPOINT_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit: {_AI_ENDPOINT_LIMIT} AI calls per hour. Try again later.",
        )
    _ai_endpoint_timestamps.append(now)


# --- AI Action Endpoints ---

@app.post("/ai/generate-tasks")
async def ai_generate_tasks(background_tasks: BackgroundTasks):
    """Ask Claude to generate today's top priority tasks."""
    _check_ai_endpoint_limit()
    background_tasks.add_task(_bg_generate_tasks)
    return {"status": "generating", "message": "Claude is prioritizing your tasks..."}


@app.post("/ai/generate-suggestions")
async def ai_generate_suggestions(background_tasks: BackgroundTasks):
    """Ask Claude to generate fresh AI suggestions."""
    _check_ai_endpoint_limit()
    background_tasks.add_task(_bg_generate_suggestions)
    return {"status": "generating", "message": "Claude is generating suggestions..."}


@app.post("/ai/generate-draft")
async def ai_generate_draft(
    topic: str,
    platform: str = "tiktok",
    content_type: str = "script",
    project_tag: str = "ai-automation",
    db: Session = Depends(get_db),
):
    """Ask Claude to generate a content draft (synchronous)."""
    _check_ai_endpoint_limit()
    # Sanitize user-supplied topic
    if len(topic) > 500:
        raise HTTPException(status_code=400, detail="Topic too long (max 500 chars)")
    from agents.reasoning import _sanitize_prompt
    topic = _sanitize_prompt(topic)
    from agents.content_drafter import generate_draft
    result = generate_draft(topic, platform, content_type, project_tag)
    draft = ContentDraft(
        title=result.get("title", topic),
        body=result.get("body", ""),
        platform=platform,
        content_type=content_type,
        hook=result.get("hook"),
        cta=result.get("cta"),
        hashtags=result.get("hashtags"),
        status="draft",
        ai_generated=True,
        project_tag=project_tag,
        hook_score=result.get("hook_score"),
        suggested_post_time=result.get("suggested_post_time"),
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


def _bg_autonomous_generate():
    """Background: run autonomous agent to generate all AI data at once."""
    from db.database import (
        SessionLocal, Task, AISuggestion, NewsBriefing, MarketGap,
        ContentDraft, ContentScheduleItem, User, AgentMemory,
    )
    from agents.autonomous_generate import run_autonomous_generate
    from agents.dashboard_snapshot import get_snapshot
    import json as _json

    db = SessionLocal()
    try:
        snapshot = get_snapshot(db)
        result = run_autonomous_generate(snapshot)

        if not result["success"]:
            print(f"[GenerateAll] Autonomous agent failed: {result['error']}. Falling back to old method.")
            db.close()
            # Fallback: run old individual generators
            _bg_generate_tasks()
            _bg_generate_suggestions()
            _bg_generate_briefing()
            _bg_scan_market()
            return

        data = result["data"]

        # --- Write tasks ---
        tasks_data = data.get("tasks", [])
        if tasks_data:
            # Remove old AI-generated pending tasks
            old_ai = db.query(Task).filter(Task.ai_generated == True, Task.status == "pending").all()
            for t in old_ai:
                db.delete(t)
            for t in tasks_data:
                if not isinstance(t, dict):
                    continue
                db.add(Task(
                    title=t.get("title", ""),
                    why=t.get("why"),
                    estimated_minutes=int(t.get("estimated_minutes", 30)),
                    project_tag=t.get("project_tag"),
                    priority_score=float(t.get("priority_score", 5.0)),
                    ai_generated=True,
                    status="pending",
                ))
            db.commit()
            print(f"[GenerateAll] Wrote {len(tasks_data)} tasks")

        # --- Write suggestions ---
        suggestions_data = data.get("suggestions", [])
        for s in suggestions_data[:5]:
            if not isinstance(s, dict):
                continue
            db.add(AISuggestion(
                body=s.get("body", ""),
                category=s.get("category"),
            ))
        if suggestions_data:
            db.commit()
            print(f"[GenerateAll] Wrote {len(suggestions_data)} suggestions")

        # --- Write briefing ---
        briefing_data = data.get("briefing", [])
        if briefing_data:
            today_str = date.today().isoformat()
            db.query(NewsBriefing).filter(NewsBriefing.briefing_date == today_str).delete()
            for b in briefing_data[:5]:
                if not isinstance(b, dict):
                    continue
                db.add(NewsBriefing(
                    headline=b.get("headline", ""),
                    summary=b.get("summary"),
                    category=b.get("category"),
                    relevance_score=float(b.get("relevance_score", 0.5)),
                    suggested_action=b.get("suggested_action"),
                    briefing_date=today_str,
                ))
            db.commit()
            print(f"[GenerateAll] Wrote {len(briefing_data)} briefing items")

        # --- Write market gaps ---
        gaps_data = data.get("market_gaps", [])
        for g in gaps_data[:5]:
            if not isinstance(g, dict):
                continue
            db.add(MarketGap(
                description=g.get("description", ""),
                source=g.get("source"),
                source_url=g.get("source_url"),
                opportunity_score=float(g.get("opportunity_score", 0.5)),
                suggested_action=g.get("suggested_action"),
                category=g.get("category"),
                status="new",
            ))
        if gaps_data:
            db.commit()
            print(f"[GenerateAll] Wrote {len(gaps_data)} market gaps")

        # --- Write content drafts ---
        drafts_data = data.get("content_drafts", [])
        if drafts_data:
            # Schedule logic: find next available days
            user = db.query(User).first()
            day_names = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
            user_schedule = {}
            if user and user.weekly_hours:
                try:
                    user_schedule = _json.loads(user.weekly_hours)
                except Exception:
                    pass

            for i, d in enumerate(drafts_data[:2]):
                if not isinstance(d, dict):
                    continue
                platform = d.get("platform", "tiktok")

                # Remove old AI drafts for same platform
                old_drafts = db.query(ContentDraft).filter(
                    ContentDraft.ai_generated == True,
                    ContentDraft.platform == platform,
                    ContentDraft.status == "draft",
                ).all()
                old_ids = [od.id for od in old_drafts]
                for od in old_drafts:
                    db.delete(od)
                if old_ids:
                    db.query(ContentScheduleItem).filter(
                        ContentScheduleItem.draft_id.in_(old_ids)
                    ).delete(synchronize_session=False)

                # Find next available day
                sched_dt = datetime.utcnow() + timedelta(days=i + 1)
                for _ in range(7):
                    day_key = day_names[sched_dt.weekday()]
                    if user_schedule.get(day_key, 2) > 0:
                        break
                    sched_dt += timedelta(days=1)
                sched_dt = sched_dt.replace(hour=10, minute=0, second=0, microsecond=0)

                hook_score = d.get("hook_score")
                if hook_score is not None:
                    try:
                        hook_score = float(hook_score)
                        if hook_score > 1:
                            hook_score = hook_score / 10.0
                    except (ValueError, TypeError):
                        hook_score = None

                draft = ContentDraft(
                    title=d.get("title", "Untitled"),
                    body=d.get("body", ""),
                    platform=platform,
                    content_type=d.get("content_type", "short-form"),
                    hook=d.get("hook"),
                    cta=d.get("cta"),
                    hashtags=d.get("hashtags"),
                    status="draft",
                    ai_generated=True,
                    project_tag=d.get("project_tag"),
                    hook_score=hook_score,
                    suggested_post_time=sched_dt.isoformat(),
                )
                db.add(draft)
                db.commit()
                db.refresh(draft)

                schedule_item = ContentScheduleItem(
                    draft_id=draft.id,
                    title=draft.title,
                    platform=platform,
                    scheduled_at=sched_dt,
                    status="scheduled",
                    block_type="content",
                    color="#A855F7",
                )
                db.add(schedule_item)
                db.commit()
                print(f"[GenerateAll] Created draft: {draft.title[:50]} → {sched_dt.date()}")

        # Save to agent memory
        try:
            db.add(AgentMemory(
                run_type="generate_all",
                message_sent=f"tasks={len(tasks_data)} suggestions={len(suggestions_data)} "
                             f"briefing={len(briefing_data)} gaps={len(gaps_data)} drafts={len(drafts_data)}",
                findings=result.get("error", "success"),
                tools_used="autonomous",
            ))
            db.commit()
        except Exception:
            pass

        print("[GenerateAll] Autonomous generation complete")

    except Exception as e:
        print(f"[GenerateAll] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


@app.post("/ai/generate-all")
async def ai_generate_all(background_tasks: BackgroundTasks):
    """One-click AI Generate: autonomous agent researches the web and populates
    tasks, suggestions, briefing, market gaps, and content drafts.
    GitHub and social syncs run in parallel.
    """
    _check_ai_endpoint_limit()

    # Autonomous agent handles all AI generation in one smart pass
    background_tasks.add_task(_bg_autonomous_generate)

    # API syncs still run in parallel (no Claude needed)
    background_tasks.add_task(_bg_sync_github)
    background_tasks.add_task(_bg_sync_social)

    return {
        "status": "generating",
        "message": "Autonomous agent is researching and generating everything...",
        "queued": [
            "autonomous_generate (tasks + suggestions + briefing + market + drafts)",
            "sync_github",
            "sync_social",
        ],
    }


# --- Auth ---

import hashlib
import secrets

AUTH_SECRET = os.getenv("AUTH_SECRET", secrets.token_hex(32))


def _hash_password(password: str) -> str:
    return hashlib.sha256(f"{AUTH_SECRET}:{password}".encode()).hexdigest()


def _make_token(username: str) -> str:
    return hashlib.sha256(f"{AUTH_SECRET}:token:{username}".encode()).hexdigest()


@app.post("/auth/signup")
def signup(body: dict, db: Session = Depends(get_db)):
    username = body.get("username", "").strip()
    password = body.get("password", "")
    email = body.get("email", "").strip()
    plan = body.get("plan", "local")

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")
    if len(password) < 3:
        raise HTTPException(status_code=400, detail="Password must be at least 3 characters")
    if plan in ("starter", "pro") and not email:
        raise HTTPException(status_code=400, detail="Email required for cloud plans")

    from db.database import User
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username already taken")

    user = User(
        username=username,
        email=email or None,
        password_hash=_hash_password(password),
        plan=plan if plan == "local" else "local",  # stays local until payment completes
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = _make_token(username)
    result = {"token": token, "status": "ok", "username": username, "plan": plan}

    # For cloud plans, create Stripe checkout
    if plan in ("starter", "pro"):
        try:
            from services.infra.billing import create_customer, create_checkout_session
            app_url = os.getenv("APP_URL", "http://localhost:3000")

            customer_id = create_customer(email, username)
            user.stripe_customer_id = customer_id
            db.commit()

            checkout_url = create_checkout_session(
                customer_id=customer_id,
                plan=plan,
                success_url=f"{app_url}/dashboard?checkout=success",
                cancel_url=f"{app_url}/pricing?checkout=canceled",
            )
            result["checkout_url"] = checkout_url
        except Exception as e:
            # Stripe not configured — just create local account
            print(f"[Auth] Stripe checkout failed (may not be configured): {e}")

    return result


@app.post("/auth/login")
def login(body: dict, db: Session = Depends(get_db)):
    username = body.get("username", "").strip()
    password = body.get("password", "")

    from db.database import User
    user = db.query(User).filter(User.username == username).first()
    if not user or user.password_hash != _hash_password(password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = _make_token(username)
    return {"token": token, "status": "ok", "username": username}


@app.get("/auth/verify")
def verify_token(token: str, db: Session = Depends(get_db)):
    from db.database import User
    users = db.query(User).all()
    for user in users:
        if _make_token(user.username) == token:
            return {"status": "ok", "username": user.username}
    raise HTTPException(status_code=401, detail="Invalid token")


@app.post("/onboarding/parse")
def parse_onboarding_text(body: dict):
    """Parse free-text (from an LLM conversation or notes) into structured projects and goals."""
    _check_ai_endpoint_limit()
    from agents.reasoning import reason_json, _sanitize_prompt

    text = body.get("text", "")
    if not text.strip():
        raise HTTPException(status_code=400, detail="No text provided")
    if len(text) > 5000:
        raise HTTPException(status_code=400, detail="Text too long (max 5000 chars)")
    text = _sanitize_prompt(text)

    prompt = f"""Extract projects and goals from this text. Return JSON with two arrays.

For each project: name, description, github_repo (if mentioned, else empty string)
For each goal: title, timeframe (week, month, or quarter — infer from context)

Text:
{text}

Return ONLY this JSON format:
{{
  "projects": [{{"name": "str", "description": "str", "github_repo": "str"}}],
  "goals": [{{"title": "str", "timeframe": "week|month|quarter"}}]
}}"""

    try:
        result = reason_json(prompt)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse: {e}")


# --- Growth Mentor (Autonomous Agent) ---

def _send_mentor_telegram(msg: str, message_type: str, db: Session, agent_mode: str = "autonomous") -> dict:
    """Send a mentor message via Telegram and save to chat history + agent memory."""
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
    tg_chat = os.getenv("TELEGRAM_CHAT_ID")

    if not tg_token or not tg_chat:
        return {"status": "ok", "message": msg, "sent": False, "reason": "Telegram not configured"}

    import httpx
    try:
        resp = httpx.post(
            f"https://api.telegram.org/bot{tg_token}/sendMessage",
            json={"chat_id": tg_chat, "text": msg},
            timeout=15,
        )
        sent = resp.json().get("ok", False)
        if sent:
            from db.database import ChatMessage
            db.add(ChatMessage(role="mentor", content=msg[:500]))
            db.commit()
        print(f"[Mentor] {message_type} ({agent_mode}) Telegram {'sent' if sent else 'failed'}: {msg[:80]}")
        return {"status": "ok", "message": msg, "sent": sent, "type": message_type, "agent": agent_mode}
    except Exception as e:
        print(f"[Mentor] Telegram failed: {e}")
        return {"status": "ok", "message": msg, "sent": False, "reason": str(e)}


@app.post("/mentor/send")
def send_mentor_message(body: dict, db: Session = Depends(get_db)):
    """Send a growth mentor message using the autonomous agent (with fallback)."""
    _check_ai_endpoint_limit()

    message_type = body.get("type", "morning")
    if message_type not in ("morning", "midday", "afternoon", "evening"):
        raise HTTPException(status_code=400, detail="Type must be: morning, midday, afternoon, evening")

    # --- Phase 1: Try autonomous agent ---
    try:
        from agents.autonomous_mentor import run_autonomous_mentor
        from agents.dashboard_snapshot import get_snapshot
        from db.database import AgentMemory

        snapshot = get_snapshot(db)
        result = run_autonomous_mentor(
            message_type=message_type,
            snapshot=snapshot,
        )

        if result["success"] and result["message"]:
            msg = result["message"]
            # Save to agent memory for continuity
            try:
                db.add(AgentMemory(
                    run_type=message_type,
                    message_sent=msg[:500],
                    findings=result.get("findings", ""),
                    tools_used=str(result.get("tools_used", [])),
                ))
                db.commit()
            except Exception as e:
                print(f"[Mentor] Failed to save agent memory: {e}")
            return _send_mentor_telegram(msg, message_type, db, agent_mode="autonomous")

        print(f"[Mentor] Autonomous agent failed: {result.get('findings', 'unknown')}. Falling back.")
    except Exception as e:
        print(f"[Mentor] Autonomous agent error: {e}. Falling back.")

    # --- Phase 2: Fallback to old one-shot mentor ---
    from agents.growth_mentor import generate_mentor_message
    import json as _json
    from db.database import User, GithubRepo

    tasks = db.query(Task).filter(Task.status == "pending").order_by(Task.priority_score.desc()).all()
    goals = db.query(Goal).filter(Goal.status == "active").all()
    projects = db.query(Project).all()
    completed_tasks_today = db.query(Task).filter(Task.status == "done").all()

    recent_commits = []
    repos = db.query(GithubRepo).all()
    for r in repos:
        if r.last_commit_at and r.last_commit_message:
            try:
                commit_time = datetime.fromisoformat(str(r.last_commit_at).replace("Z", "+00:00")) if isinstance(r.last_commit_at, str) else r.last_commit_at
                if (datetime.utcnow() - commit_time.replace(tzinfo=None)).total_seconds() < 86400:
                    recent_commits.append({"repo": r.name, "message": r.last_commit_message[:60]})
            except Exception:
                pass

    user = db.query(User).first()
    day_names = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    from datetime import timezone
    eastern_offset = timedelta(hours=-4)
    now_eastern = datetime.now(timezone.utc) + eastern_offset
    today_day = day_names[now_eastern.weekday()]
    available_hours = 2
    if user and user.weekly_hours:
        try:
            schedule = _json.loads(user.weekly_hours)
            available_hours = schedule.get(today_day, 2)
        except Exception:
            pass

    msg = generate_mentor_message(
        message_type=message_type,
        tasks=[{"title": t.title, "estimated_minutes": t.estimated_minutes, "priority_score": t.priority_score, "project_tag": t.project_tag} for t in tasks],
        goals=[{"title": g.title, "progress": g.progress} for g in goals],
        projects=[{"name": p.name, "stage_label": p.stage_label} for p in projects],
        completed_today=len(completed_tasks_today),
        available_hours=available_hours,
        completed_tasks=[{"title": t.title} for t in completed_tasks_today],
        recent_commits=recent_commits,
        mentor_notes=user.mentor_notes or "" if user else "",
    )

    return _send_mentor_telegram(msg, message_type, db, agent_mode="fallback")


@app.get("/health")
def health():
    # Check Claude auth status file if it exists
    claude_status = "unknown"
    try:
        with open("data/claude-auth-status.txt") as f:
            content = f.read().strip()
            claude_status = "ok" if content.startswith("OK") else "expired"
    except FileNotFoundError:
        pass

    return {"status": "ok", "version": "0.1.0", "claude_auth": claude_status}
