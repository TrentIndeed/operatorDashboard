"""
Codebase digest — reads the founder's actual product repo and produces a
compact, factual summary of what's there and how far along it is.

WHY: the bot runs on the VPS and can only see git commit *messages* truncated
to 80 chars. That's not enough to understand the product. This module reads the
real repo (README, recent commits, file tree, maturity signals) and stores a
digest in the DB so the bot's advice is grounded in reality.

WHERE IT RUNS: wherever the repo is on disk. Locally that's the founder's
machine at ../meshToParametric. Since the VPS can't see that path, a small local
script (scripts/push_codebase_digest.py) runs this and POSTs the result to the
cloud DB. The agents only ever read the stored digest, so they work in both
places.

Pure file/git reads. No Claude call, deterministic, cheap.
"""
import os
import re
import subprocess
from pathlib import Path

# Default location relative to operatorDashboard/. Override with MESH_REPO_PATH.
DEFAULT_REPO_PATH = os.getenv("MESH_REPO_PATH", str(Path(__file__).resolve().parents[2] / ".." / "meshToParametric"))

# Maturity signals → which keywords in recent commits hint at which stage.
_LAUNCH_WORDS = ("launch", "show hn", "product hunt", "waitlist", "pricing", "stripe", "signup", "sign up")
_BETA_WORDS = ("beta", "tester", "feedback", "testimonial", "onboard", "landing page")
_PIPELINE_WORDS = ("fillet", "chamfer", "extrude", "mesh", "ransac", "matcher", "pipeline", "decimation",
                   "topology", "fix", "debug", "bug", "stage trace", "diag")

_CODE_EXTS = (".py", ".js", ".ts", ".tsx", ".jsx", ".rs", ".cpp", ".c", ".go")


def _git(path: Path, args: list[str]) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(path), *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20,
        )
        return out.stdout.strip()
    except Exception:
        return ""


def _read_first(path: Path, names: list[str], limit: int) -> str:
    for n in names:
        f = path / n
        if f.is_file():
            try:
                return f.read_text(encoding="utf-8", errors="replace")[:limit]
            except Exception:
                continue
    return ""


def _readme_intro(readme: str, limit: int = 600) -> str:
    """First couple of meaningful paragraphs of the README (skip badges/headers)."""
    lines = []
    for line in readme.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("!") or s.startswith("["):
            if lines:
                break
            continue
        lines.append(s)
        if sum(len(x) for x in lines) > limit:
            break
    return " ".join(lines)[:limit]


def _count_code_files(path: Path, cap: int = 4000) -> int:
    n = 0
    skip = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".next"}
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in skip]
        for f in files:
            if f.endswith(_CODE_EXTS):
                n += 1
                if n >= cap:
                    return n
    return n


def _top_dirs(path: Path) -> list[str]:
    skip = {".git", "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache", ".vscode", ".idea"}
    out = []
    try:
        for entry in sorted(path.iterdir()):
            if entry.is_dir() and entry.name not in skip and not entry.name.startswith("."):
                out.append(entry.name)
    except Exception:
        pass
    return out[:20]


def _signal_counts(commit_subjects: list[str]) -> dict:
    text = " ".join(commit_subjects).lower()
    return {
        "pipeline": sum(text.count(w) for w in _PIPELINE_WORDS),
        "beta": sum(text.count(w) for w in _BETA_WORDS),
        "launch": sum(text.count(w) for w in _LAUNCH_WORDS),
    }


def heuristic_stage(signals: dict, has_landing: bool, has_tests: bool) -> int:
    """
    Conservative stage GUESS from code signals only. Never auto-advances the
    founder; it's a proposal the founder confirms. Biases low on purpose —
    code maturity alone never proves you have users.
    """
    if signals["launch"] >= 3 and has_landing:
        return 3  # launch-y commits + a landing page → maybe beta. Never auto-propose 4.
    if signals["beta"] >= 2 or has_landing:
        return 2
    return 1


def generate_digest(repo_path: str | None = None) -> dict | None:
    """
    Build a digest of the repo. Returns None if the repo isn't on disk
    (e.g. running on the VPS, where it must be pushed instead).
    """
    path = Path(repo_path or DEFAULT_REPO_PATH).expanduser()
    if not path.exists() or not (path / ".git").exists():
        return None

    head = _git(path, ["rev-parse", "HEAD"])[:12]
    branch = _git(path, ["rev-parse", "--abbrev-ref", "HEAD"]) or "?"
    log_raw = _git(path, ["log", "-20", "--format=%s|%cr"])
    commit_subjects, commit_lines = [], []
    for line in log_raw.splitlines():
        subj = line.split("|", 1)[0].strip()
        when = line.split("|", 1)[1].strip() if "|" in line else ""
        if subj:
            commit_subjects.append(subj)
            commit_lines.append(f"- {subj} ({when})" if when else f"- {subj}")

    # How much has changed lately — a rough activity signal.
    shortstat = _git(path, ["log", "--since=14.days", "--oneline"])
    commits_14d = len([l for l in shortstat.splitlines() if l.strip()])

    readme = _read_first(path, ["README.md", "readme.md", "Readme.md"], 4000)
    intro = _readme_intro(readme)
    top_dirs = _top_dirs(path)
    code_files = _count_code_files(path)

    has_tests = (path / "tests").is_dir() or (path / "test").is_dir()
    has_landing = any(d in ("frontend", "landing", "web", "site", "www") for d in top_dirs)
    signals = _signal_counts(commit_subjects)
    proposed = heuristic_stage(signals, has_landing, has_tests)

    # Compact summary that gets dropped into prompts (keep it tight).
    recent = "\n".join(commit_lines[:8]) or "- (no commits found)"
    summary = (
        f"Repo: {path.name} (branch {branch}, HEAD {head}). "
        f"{commits_14d} commits in the last 14 days, ~{code_files} source files.\n"
        f"README says: {intro or 'n/a'}\n"
        f"Top-level dirs: {', '.join(top_dirs) or 'n/a'}. "
        f"Tests dir: {'yes' if has_tests else 'no'}. Landing/frontend dir: {'yes' if has_landing else 'no'}.\n"
        f"Recent work (commit subjects):\n{recent}\n"
        f"Signal read: most recent commits look like {'core pipeline / bug-fixing' if signals['pipeline'] >= signals['beta'] and signals['pipeline'] >= signals['launch'] else ('beta/landing work' if signals['beta'] >= signals['launch'] else 'launch prep')}."
    )

    detail = {
        "repo": path.name,
        "branch": branch,
        "head": head,
        "commits_14d": commits_14d,
        "code_files": code_files,
        "top_dirs": top_dirs,
        "has_tests": has_tests,
        "has_landing": has_landing,
        "signals": signals,
        "recent_commits": commit_subjects[:20],
        "readme_intro": intro,
        "proposed_stage": proposed,
    }
    return {"summary": summary, "detail": detail, "commit_sha": head, "proposed_stage": proposed, "source": "local"}


def save_digest(db, digest: dict, source: str = "local") -> None:
    """Store a digest in the DB (keep the last few, prune the rest)."""
    from db.database import CodebaseSnapshot
    import json as _json
    snap = CodebaseSnapshot(
        summary=(digest.get("summary") or "")[:8000],
        detail=_json.dumps(digest.get("detail", {}))[:16000],
        commit_sha=digest.get("commit_sha"),
        source=source,
    )
    db.add(snap)
    db.commit()
    # Keep only the 10 most recent.
    extra = db.query(CodebaseSnapshot).order_by(CodebaseSnapshot.id.desc()).offset(10).all()
    for s in extra:
        db.delete(s)
    db.commit()


def refresh_if_local(db) -> bool:
    """Generate + store a digest if the repo is on this machine. Returns True if it ran."""
    digest = generate_digest()
    if not digest:
        return False
    save_digest(db, digest, source="local")
    return True
