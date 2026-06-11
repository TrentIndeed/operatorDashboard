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
import json
import re
import subprocess
from pathlib import Path

# Default location relative to operatorDashboard/. Override with MESH_REPO_PATH.
DEFAULT_REPO_PATH = os.getenv("MESH_REPO_PATH", str(Path(__file__).resolve().parents[2] / ".." / "meshToParametric"))

# How much real activity to fold in (configurable — "up to a certain amount of changes").
DIFF_DAYS = int(os.getenv("MESH_DIFF_DAYS", "2"))            # look back this many days for code changes
DIFF_MAX_CHARS = int(os.getenv("MESH_DIFF_MAX_CHARS", "6000"))  # cap the diff text size
PROMPT_COUNT = int(os.getenv("MESH_PROMPT_COUNT", "12"))    # how many recent Claude prompts to pull
PROMPT_MAX_LEN = int(os.getenv("MESH_PROMPT_MAX_LEN", "300"))  # trim each prompt to this many chars
# Where Claude Code stores per-project transcripts. Override with CLAUDE_PROJECTS_DIR.
CLAUDE_PROJECTS_DIR = os.getenv("CLAUDE_PROJECTS_DIR", str(Path.home() / ".claude" / "projects"))

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


def _recent_diff(path: Path, days: int, max_chars: int) -> str:
    """
    The actual code changes from the last `days` days (committed + uncommitted),
    capped at `max_chars`. This is the ground truth of what's being worked on,
    not a stale task list.
    """
    shas = _git(path, ["log", f"--since={days}.days.ago", "--format=%H"]).split()
    rng = None
    if shas:
        oldest = shas[-1]
        # diff from the parent of the oldest in-window commit, falling back if it's the root
        if _git(path, ["rev-parse", f"{oldest}^"]):
            rng = f"{oldest}^..HEAD"
        else:
            rng = f"{oldest}..HEAD"
    else:
        rng = "HEAD~3..HEAD"  # quiet week: show the last few commits anyway

    excludes = [":(exclude)*.lock", ":(exclude)*.log", ":(exclude)out.txt",
                ":(exclude)*.svg", ":(exclude)package-lock.json", ":(exclude)*.ipynb",
                ":(exclude)*.png", ":(exclude)*.jpg", ":(exclude)*.jpeg",
                ":(exclude)tests/visual_reports/*", ":(exclude)_render_out/*", ":(exclude)models/*"]
    stat = _git(path, ["diff", "--stat", rng])
    patch = _git(path, ["diff", rng, "--", ".", *excludes])
    uncommitted = _git(path, ["diff", "--", ".", *excludes])

    out = ""
    if stat:
        out += "Files changed recently:\n" + stat + "\n\n"
    if patch:
        out += "Committed changes:\n" + patch
    if uncommitted:
        out += "\n\nUncommitted working changes (in progress right now):\n" + uncommitted
    out = out.strip()
    if len(out) > max_chars:
        out = out[:max_chars] + "\n[... diff truncated to fit budget ...]"
    return out


def _plan_docs(path: Path) -> list[Path]:
    """Planning docs in the repo root or docs/ (TODO, roadmap, handoff, plan, next)."""
    out = []
    for d in (path, path / "docs"):
        if d.is_dir():
            for f in d.glob("*.md"):
                n = f.name.lower()
                if any(k in n for k in ("todo", "roadmap", "next", "plan", "handoff", "tasks")):
                    out.append(f)
    # TODO/roadmap first (they hold the actual priority list), then others
    out.sort(key=lambda f: (0 if any(k in f.name.lower() for k in ("todo", "roadmap")) else 1, f.name.lower()))
    return out


def _open_items(path: Path, limit: int = 12) -> list[str]:
    """
    Unchecked checklist items ('- [ ] ...') from the repo's own planning docs.
    THIS is the real open-priority signal, vs commit history which is trailing
    (a burst of commits about X means X was just FINISHED, not that X is open).
    """
    items, seen = [], set()
    for f in _plan_docs(path):
        try:
            txt = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for ln in txt.splitlines():
            s = ln.strip()
            low = s.lower()
            if low.startswith("- [ ]") or low.startswith("* [ ]"):
                t = re.sub(r"[*_`]", "", s[5:]).strip()
                t = " ".join(t.split())[:180]
                if t and t not in seen:
                    seen.add(t)
                    items.append(f"{f.name}: {t}")
                    if len(items) >= limit:
                        return items
    return items


def _in_progress_files(path: Path, limit: int = 12) -> list[str]:
    """Uncommitted code files = what's literally being worked on right now."""
    out = []
    for line in _git(path, ["status", "--porcelain"]).splitlines():
        if len(line) < 4:
            continue
        f = line[3:].strip().strip('"')
        low = f.lower()
        if low.endswith((".png", ".jpg", ".jpeg", ".svg", ".lock", ".log")):
            continue
        if "visual_reports" in low or "_render_out" in low or low.startswith("models/"):
            continue
        out.append(f)
        if len(out) >= limit:
            break
    return out


def _todo_markers(path: Path, limit: int = 6) -> list[str]:
    """TODO/FIXME/HACK markers in source (.py only, to skip launch-gated UI noise)."""
    out = []
    skip = {".git", "node_modules", ".venv", "venv", "__pycache__", "tests",
            "_render_out", "models", ".pytest_cache", "docs"}
    pat = re.compile(r"\b(TODO|FIXME|HACK)\b[:\s]?(.*)")
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in skip and not d.startswith(".")]
        for fn in files:
            if not fn.endswith(".py"):
                continue
            fp = Path(root) / fn
            try:
                lines = fp.read_text(encoding="utf-8", errors="replace").splitlines()
            except Exception:
                continue
            for i, ln in enumerate(lines, 1):
                m = pat.search(ln)
                if m:
                    txt = (m.group(2).strip() or ln.strip())[:100]
                    out.append(f"{fp.relative_to(path)}:{i}: {txt}")
                    if len(out) >= limit:
                        return out
    return out


def _find_claude_transcript_dir(repo_path: Path) -> Path | None:
    """Find Claude Code's transcript folder for this repo (matches on repo name)."""
    base = Path(CLAUDE_PROJECTS_DIR)
    if not base.exists():
        return None
    repo_name = repo_path.name.lower()
    candidates = [
        d for d in base.iterdir()
        if d.is_dir() and (d.name.lower().endswith("-" + repo_name) or d.name.lower().endswith(repo_name))
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _user_prompt_text(content) -> str:
    """Extract the human-typed text from a transcript 'user' message, or '' if it's noise."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for b in content:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_result":
                return ""  # this is a tool result, not something the founder typed
            if b.get("type") == "text":
                parts.append(b.get("text", ""))
        return "\n".join(parts).strip()
    return ""


def _is_prompt_noise(text: str) -> bool:
    """
    Filter out everything that isn't the founder actually talking to Claude:
    command wrappers, caveats, slash-command stdout, interrupts, context-continuation
    summaries, and the app's OWN automated LLM calls (meshToParametric runs
    `claude -p "You are a CAD construction planner..."` as its backend, which
    pollutes the transcript with system prompts that are not founder intent).
    """
    t = text.lstrip()
    head = t[:60].lower()
    if t.startswith("<") and any(tag in head for tag in (
        "<command-", "<local-command", "<bash-", "<system-reminder", "<user-memory")):
        return True
    if "caveat: the messages below" in head:
        return True
    if t.startswith("[Request interrupted"):
        return True
    if head.startswith("this session is being continued"):
        return True
    # App's automated system/role prompts (not the founder asking for something).
    if head.startswith("you are a ") or head.startswith("you are an "):
        return True
    if "only output valid json" in t[:200].lower():
        return True
    return False


def extract_recent_prompts(repo_path: Path, count: int = PROMPT_COUNT, max_len: int = PROMPT_MAX_LEN) -> list[str]:
    """
    The founder's most recent Claude prompts for this repo (what they asked for,
    NOT Claude's responses). High-signal intent — what they're actually trying to do.
    """
    tdir = _find_claude_transcript_dir(repo_path)
    if not tdir:
        return []
    entries: list[tuple[str, str]] = []
    files = sorted(tdir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    for f in files[-10:]:  # newest handful of sessions
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if obj.get("type") != "user":
                continue
            msg = obj.get("message", {})
            if not isinstance(msg, dict) or msg.get("role") != "user":
                continue
            prompt = _user_prompt_text(msg.get("content"))
            if not prompt or _is_prompt_noise(prompt):
                continue
            entries.append((obj.get("timestamp", ""), prompt))
    entries.sort(key=lambda e: e[0])  # ISO timestamps sort chronologically
    # Keep the most recent `count` UNIQUE prompts (the planner spam repeats a lot).
    seen, kept = set(), []
    for _, text in reversed(entries):
        flat = " ".join(text.split())
        key = flat[:80].lower()
        if key in seen:
            continue
        seen.add(key)
        kept.append(flat[:max_len] + ("..." if len(flat) > max_len else ""))
        if len(kept) >= count:
            break
    return list(reversed(kept))


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

    # High-signal additions: actual code changes, recent prompts, and crucially the
    # FORWARD-looking signals (open TODO items, in-progress files) so the bot can tell
    # what's OPEN vs what was just FINISHED.
    recent_changes = _recent_diff(path, DIFF_DAYS, DIFF_MAX_CHARS)
    recent_prompts = extract_recent_prompts(path)
    open_items = _open_items(path)
    in_progress = _in_progress_files(path)
    markers = _todo_markers(path)

    # newest commits first; these are DONE work, not open priorities
    done = "\n".join(commit_lines[:8]) or "- (no commits found)"
    prompts_block = "\n".join(f"  - \"{p}\"" for p in recent_prompts) or "  (none found)"
    open_block = "\n".join(f"  - {x}" for x in open_items) or "  (no open checklist items found in TODO/plan docs)"
    inprog_block = ", ".join(in_progress) or "(nothing uncommitted)"
    markers_block = "\n".join(f"  - {m}" for m in markers) or "  (none)"

    summary = (
        f"Repo: {path.name} (branch {branch}, HEAD {head}). "
        f"{commits_14d} commits in the last 14 days, ~{code_files} source files.\n"
        f"README says: {intro or 'n/a'}\n"
        f"\nRECENTLY COMPLETED (newest commits first). This work is DONE. A cluster of "
        f"commits about a topic means that topic was just FINISHED, NOT that it is the open priority:\n{done}\n"
        f"\nIN PROGRESS right now (uncommitted code files): {inprog_block}\n"
        f"\nWHAT THE FOUNDER HAS BEEN ASKING CLAUDE FOR (oldest first, LAST line = current focus):\n{prompts_block}\n"
        f"\nOPEN PRIORITIES from the repo's own planning docs (unchecked items, trust these over commit history for what's NEXT):\n{open_block}\n"
        f"\nOpen code markers (TODO/FIXME):\n{markers_block}"
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
        "recent_prompts": recent_prompts,
        "open_items": open_items,
        "in_progress": in_progress,
        "todo_markers": markers,
        "recent_changes": recent_changes,
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
