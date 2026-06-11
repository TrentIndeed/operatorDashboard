"""
Stage model — the single source of truth for "where is the startup, really".

This REPLACES the old calendar-week logic (`plan_start = date(2026, 4, 8)` +
`week = days_since // 7`). That math clamped the founder to "Week 4 — LAUNCH"
forever, so the AI kept telling him to post Show HN / Product Hunt when he's
actually still building the core pipeline.

Now the stage is a stored value (User.startup_stage, 1-4) that the founder
controls and the codebase digest can propose updates to. Every agent reads its
focus + distribution guidance from here so advice matches reality.
"""
from datetime import datetime

DEFAULT_STAGE = 1

# Fallback product description if the founder hasn't set a living profile yet.
# Deliberately stage-neutral — no "4-week plan", no launch framing.
DEFAULT_PROFILE = (
    "ParameshAI, a mesh-to-parametric CAD tool for Onshape. It converts STL/OBJ/PLY "
    "mesh files into editable parametric CAD with real feature trees. Works on prismatic "
    "mechanical parts: brackets, plates, mounts, enclosures, holes, chamfers, fillets. Does "
    "NOT handle organic/freeform surfaces or assemblies. ICP: solo mechanical engineers, "
    "product designers, and hardware makers on Onshape. Main competitor: Backflip AI "
    "($30M funded, enterprise-first, still in closed beta)."
)

STAGES = {
    1: {
        "name": "Building core pipeline",
        "reality": "The core mesh-to-CAD conversion is not reliable yet. No outside users. "
                   "This is months from anything public, not weeks.",
        "focus": "Almost all time goes into the pipeline. Make conversion actually work on real, "
                 "messy meshes. Nothing else matters until a part converts cleanly end to end.",
        "distribution": "Quiet and educational ONLY. You can answer Tier-1 Reddit/HN/forum posts as a "
                        "genuinely helpful engineer, but do NOT mention ParameshAI, do NOT link anything, "
                        "do NOT say you're building a tool. Goal: learn how people describe this pain, build "
                        "a reputation, and save the names of people who have it so you can come back later.",
        "forbidden": "Show HN, Product Hunt, launch posts, 'we're live', waitlist pushes, demo-video DMs, "
                     "paid ads, hype threads. The product can't back any of it up yet.",
    },
    2: {
        "name": "Working prototype, no users",
        "reality": "Conversion works on your own test parts, but nobody else has run it and it's "
                   "untested on real-world scans.",
        "focus": "Harden the pipeline on degraded/real meshes until a stranger could push one part "
                 "through it. Start lining up a few specific people to try it.",
        "distribution": "Still mostly educational. In warm 1:1 DMs with Tier-1 people you've already helped, "
                        "you can say 'I've been building something for exactly this, want to be an early "
                        "tester?' No public launch, no broad blasting.",
        "forbidden": "Public launches (Show HN / Product Hunt / big Reddit posts), pricing pages, "
                     "'sign up now' CTAs. Still too early.",
    },
    3: {
        "name": "Private beta",
        "reality": "A handful of real testers are using it. You're fixing real-world breakage and "
                   "collecting feedback.",
        "focus": "Tight feedback loop with beta users, fix the top failure modes, gather testimonials, "
                 "build the landing page + pricing, and DRAFT (not post) launch materials.",
        "distribution": "Now you actively recruit. Mention ParameshAI naturally in relevant replies, invite "
                        "people into the beta, build a waitlist. Demo videos in DMs are good now.",
        "forbidden": "Don't do the big public launch until the beta is stable and you have testimonials. "
                     "Drafting launch posts is fine; posting them is not.",
    },
    4: {
        "name": "Public launch",
        "reality": "Stable, tested on real users, testimonials in hand.",
        "focus": "Launch and convert. Hit every channel, then double down on whatever actually drives signups.",
        "distribution": "Show HN (9am ET), Product Hunt (Tue 12:01am PT), Reddit launches, email the waitlist, "
                        "reply to every comment. Full court press.",
        "forbidden": "Nothing is off-limits now, but don't fake metrics or spam communities.",
    },
}


def _clamp(stage) -> int:
    try:
        return max(1, min(4, int(stage)))
    except (ValueError, TypeError):
        return DEFAULT_STAGE


def get_stage(db) -> int:
    """Read the founder's current stage (1-4). Defaults to 1 (building core pipeline)."""
    from db.database import User
    user = db.query(User).first()
    if user and getattr(user, "startup_stage", None):
        return _clamp(user.startup_stage)
    return DEFAULT_STAGE


def get_stage_standalone() -> int:
    """Stage lookup for callers that don't hold a DB session."""
    from db.database import SessionLocal
    db = SessionLocal()
    try:
        return get_stage(db)
    finally:
        db.close()


def set_stage(db, stage: int) -> int:
    """Persist a new stage. Returns the clamped value actually stored."""
    from db.database import User
    stage = _clamp(stage)
    user = db.query(User).first()
    if user:
        user.startup_stage = stage
        user.stage_updated_at = datetime.utcnow()
        db.commit()
    return stage


def stage_name(stage: int) -> str:
    return STAGES.get(_clamp(stage), STAGES[DEFAULT_STAGE])["name"]


def stage_block(stage: int) -> str:
    """The focus block dropped into every prompt. Replaces the old week_focus dicts."""
    s = STAGES.get(_clamp(stage), STAGES[DEFAULT_STAGE])
    return (
        f"CURRENT STAGE: {_clamp(stage)}/4: {s['name']}\n"
        f"Reality: {s['reality']}\n"
        f"Where time should go: {s['focus']}\n"
        f"Distribution at this stage: {s['distribution']}\n"
        f"OFF-LIMITS right now (do not suggest these): {s['forbidden']}"
    )


def distribution_guidance(stage: int) -> str:
    """Just the distribution rule — used by the outreach drafter."""
    return STAGES.get(_clamp(stage), STAGES[DEFAULT_STAGE])["distribution"]


def mentions_product_publicly(stage: int) -> bool:
    """Whether public replies should name ParameshAI. Only from private beta on."""
    return _clamp(stage) >= 3


def _latest_digest_summary(db) -> str:
    """Most recent codebase digest summary, if one has been pushed/generated."""
    try:
        from db.database import CodebaseSnapshot
        snap = db.query(CodebaseSnapshot).order_by(CodebaseSnapshot.id.desc()).first()
        if snap and snap.summary:
            return snap.summary.strip()
    except Exception:
        pass
    return ""


def _latest_recent_changes(db) -> str:
    """The actual recent code diff from the latest digest, if present."""
    import json as _json
    try:
        from db.database import CodebaseSnapshot
        snap = db.query(CodebaseSnapshot).order_by(CodebaseSnapshot.id.desc()).first()
        if snap and snap.detail:
            return (_json.loads(snap.detail).get("recent_changes") or "").strip()
    except Exception:
        pass
    return ""


def proposed_stage(db) -> tuple[int | None, str]:
    """
    Stage the latest codebase digest suggests, with a short reason. Returns
    (None, "") if there's no digest or it agrees with the current stage.
    The founder always confirms before this changes anything.
    """
    import json as _json
    try:
        from db.database import CodebaseSnapshot
        snap = db.query(CodebaseSnapshot).order_by(CodebaseSnapshot.id.desc()).first()
        if not snap or not snap.detail:
            return None, ""
        detail = _json.loads(snap.detail)
        prop = detail.get("proposed_stage")
        if not prop or _clamp(prop) == get_stage(db):
            return None, ""
        sig = detail.get("signals", {})
        lead = max(sig, key=sig.get) if sig else "pipeline"
        reason = (f"recent commits look like {lead} work, "
                  f"landing dir: {detail.get('has_landing')}, tests: {detail.get('has_tests')}")
        return _clamp(prop), reason
    except Exception:
        return None, ""


def stage_check_line(db) -> str:
    """One-line nudge for the daily brief when the code suggests a different stage."""
    prop, reason = proposed_stage(db)
    if not prop:
        return ""
    return (f"STAGE CHECK: your codebase looks like Stage {prop} ({stage_name(prop)}) "
            f"({reason}), but you're set to Stage {get_stage(db)} ({stage_name(get_stage(db))}). "
            f"If that's right, tell the founder to reply 'stage {prop}' to confirm. Do not assume it.")


def profile_text(db) -> str:
    """Living product description — founder-set if present, else the default."""
    from db.database import User
    user = db.query(User).first()
    profile = (getattr(user, "startup_profile", "") or "").strip() if user else ""
    return profile or DEFAULT_PROFILE


def context_block(db, include_digest: bool = True, include_diff: bool = False) -> str:
    """
    The full grounding block every agent prepends: what's being built + the
    real current stage + (if available) the actual codebase state.

    include_diff=True also appends the recent code diff. Use it only on the
    Claude-CLI-subprocess paths (autonomous mentor/generate), which have no
    8K prompt cap. The _call_claude paths (sms, fallback, tasks) leave it off
    and rely on the compact summary (which already includes recent prompts).

    This is the one function that replaces all the scattered hardcoded
    "ParameshAI ... 4-week plan ... Week N" paragraphs.
    """
    parts = [
        f"WHAT THE FOUNDER IS BUILDING:\n{profile_text(db)}",
        stage_block(get_stage(db)),
    ]
    if include_digest:
        digest = _latest_digest_summary(db)
        if digest:
            parts.append(
                "LATEST CODEBASE STATE (from the actual repo and the founder's recent Claude prompts). "
                "This is the GROUND TRUTH of what they're working on right now. The dashboard task list "
                "can be stale, so when it conflicts with this, trust this and steer off this:\n" + digest
            )
        if include_diff:
            changes = _latest_recent_changes(db)
            if changes:
                parts.append("RECENT CODE CHANGES (actual diffs from the last couple days):\n" + changes)
    return "\n\n".join(parts)
