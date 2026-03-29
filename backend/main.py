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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables
    init_db()
    # Seed initial data if empty
    _seed_initial_data()
    yield


def _seed_initial_data():
    """Seed the DB with starter projects and goals if empty."""
    from db.database import SessionLocal
    db = SessionLocal()
    try:
        if db.query(Project).count() > 0:
            return  # Already seeded

        # Example seed projects — customize these for your own use
        projects = [
            Project(
                name="Main Product",
                slug="main-product",
                description="Your primary SaaS or product",
                current_stage=0,
                total_stages=6,
                stage_label="Getting started",
                blockers=None,
                next_milestone="Define MVP scope",
                github_repo="",
                color="#3b82f6",
            ),
            Project(
                name="Content Engine",
                slug="content-engine",
                description="Content creation and distribution pipeline",
                current_stage=0,
                total_stages=4,
                stage_label="Setup",
                blockers=None,
                next_milestone="First content published",
                github_repo="",
                color="#8b5cf6",
            ),
            Project(
                name="Open Source",
                slug="open-source",
                description="Open-source tools and workflows",
                current_stage=0,
                total_stages=3,
                stage_label="Planning",
                blockers=None,
                next_milestone="First repo published",
                github_repo="",
                color="#10b981",
            ),
            Project(
                name="Operator Dashboard",
                slug="operator-dashboard",
                description="This dashboard — AI-powered solo founder command center",
                current_stage=1,
                total_stages=5,
                stage_label="Phase 1: Foundation",
                blockers=None,
                next_milestone="Phase 2: Content Engine",
                github_repo="",
                color="#f59e0b",
            ),
        ]
        db.add_all(projects)

        # Example seed goals — customize for your own projects
        goals = [
            # This week
            Goal(title="Define MVP feature set", timeframe="week", progress=0.0, project_slug="main-product"),
            Goal(title="Film and edit 3 short-form videos", timeframe="week", progress=0.0, project_slug="content-engine"),
            Goal(title="Operator dashboard Phase 1 complete", timeframe="week", progress=0.0, project_slug="operator-dashboard"),
            # This month
            Goal(title="Reach 1,000 waitlist signups", timeframe="month", progress=0.0, project_slug="main-product"),
            Goal(title="Post 20 pieces of content across platforms", timeframe="month", progress=0.0, project_slug="content-engine"),
            Goal(title="Publish 2 open-source repos", timeframe="month", progress=0.0, project_slug="open-source"),
            # This quarter
            Goal(title="Launch beta to waitlist", timeframe="quarter", progress=0.0, project_slug="main-product"),
            Goal(title="Reach 10K followers on TikTok", timeframe="quarter", progress=0.0, project_slug="content-engine"),
            Goal(title="Full operator dashboard deployed", timeframe="quarter", progress=0.0, project_slug="operator-dashboard"),
        ]
        db.add_all(goals)

        # Example seed suggestions — AI Generate will replace these with real ones
        suggestions = [
            AISuggestion(
                body="Your waitlist is the highest-leverage asset right now — every piece of content should end with a soft CTA to join.",
                category="growth",
            ),
            AISuggestion(
                body="'Build in public' content consistently outperforms generic posts — document your progress with short videos showing real results.",
                category="content",
            ),
            AISuggestion(
                body="Identify your closest competitors and find what they lack — lean into differentiators like open-source, local-first, or privacy.",
                category="product",
            ),
            AISuggestion(
                body="Reddit communities in your niche are underutilized for lead generation — a demo post showing your product in action would perform well.",
                category="market",
            ),
        ]
        db.add_all(suggestions)

        db.commit()
    finally:
        db.close()


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

        prompt = """Generate 5 news/industry briefing items relevant to the founder's projects today.

Return ONLY a JSON array of 5 objects, no wrapper object. Each object:
{
  "headline": "Short headline",
  "summary": "1-2 sentence summary",
  "category": "ai | competitor | marketing | cad | industry",
  "relevance_score": 0.0 to 1.0,
  "suggested_action": "What the founder should do"
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
                try:
                    await sync_repo(owner, p.github_repo, db)
                    print(f"[GitHub] synced {p.github_repo}")
                except Exception as e:
                    print(f"[GitHub] sync {p.github_repo} failed: {e}")
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


def _bg_generate_draft_and_schedule(topic: str, platform: str, content_type: str, project_tag: str, day_offset: int = 1):
    """Background: generate a content draft and schedule it day_offset days from now."""
    from db.database import SessionLocal
    from agents.content_drafter import generate_draft
    db = SessionLocal()
    try:
        result = generate_draft(topic, platform, content_type, project_tag)
        if not isinstance(result, dict):
            print(f"[AI] generate_draft returned non-dict: {type(result)}")
            return

        # Schedule on the specified day offset — ignore Claude's suggested time
        # to avoid stacking multiple drafts on the same day
        sched_dt = datetime.utcnow() + timedelta(days=day_offset)
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


# --- AI Action Endpoints ---

@app.post("/ai/generate-tasks")
async def ai_generate_tasks(background_tasks: BackgroundTasks):
    """Ask Claude to generate today's top priority tasks."""
    background_tasks.add_task(_bg_generate_tasks)
    return {"status": "generating", "message": "Claude is prioritizing your tasks..."}


@app.post("/ai/generate-suggestions")
async def ai_generate_suggestions(background_tasks: BackgroundTasks):
    """Ask Claude to generate fresh AI suggestions."""
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


@app.post("/ai/generate-all")
async def ai_generate_all(background_tasks: BackgroundTasks):
    """One-click AI Generate: tasks, drafts, schedule, market scan, GitHub sync.

    Runs everything in background so the frontend gets an instant response.
    """
    # 1. Generate priority tasks
    background_tasks.add_task(_bg_generate_tasks)

    # 2. Generate suggestions
    background_tasks.add_task(_bg_generate_suggestions)

    # 3. Generate content drafts for top projects — spread across different days
    background_tasks.add_task(
        _bg_generate_draft_and_schedule,
        "Building in public: latest progress update",
        "tiktok", "short-form", "ai-automation", 1,  # tomorrow
    )
    background_tasks.add_task(
        _bg_generate_draft_and_schedule,
        "Technical deep dive on latest engineering challenge",
        "youtube", "script", "mesh2param", 3,  # 3 days from now
    )

    # 4. Generate today's briefing
    background_tasks.add_task(_bg_generate_briefing)

    # 5. Scan market for gaps
    background_tasks.add_task(_bg_scan_market)

    # 6. Sync GitHub repos
    background_tasks.add_task(_bg_sync_github)

    return {
        "status": "generating",
        "message": "AI is generating tasks, drafts, briefing, scanning market, and syncing GitHub...",
        "queued": [
            "generate_tasks",
            "generate_suggestions",
            "generate_draft_tiktok",
            "generate_draft_youtube",
            "generate_briefing",
            "scan_market",
            "sync_github",
        ],
    }


# --- Auth ---

import hashlib
import secrets

# Login credentials from env (defaults for development)
AUTH_USER = os.getenv("DASHBOARD_USER", "123")
AUTH_PASS = os.getenv("DASHBOARD_PASS", "123")
AUTH_SECRET = os.getenv("AUTH_SECRET", secrets.token_hex(32))


@app.post("/auth/login")
def login(body: dict):
    if body.get("username") == AUTH_USER and body.get("password") == AUTH_PASS:
        # Generate a simple token (hash of secret + user)
        token = hashlib.sha256(f"{AUTH_SECRET}:{AUTH_USER}".encode()).hexdigest()
        return {"token": token, "status": "ok"}
    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.get("/auth/verify")
def verify_token(token: str):
    expected = hashlib.sha256(f"{AUTH_SECRET}:{AUTH_USER}".encode()).hexdigest()
    if token == expected:
        return {"status": "ok"}
    raise HTTPException(status_code=401, detail="Invalid token")


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}
