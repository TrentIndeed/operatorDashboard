import os
from pathlib import Path
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Use DATABASE_URL env var if set, otherwise default to ./data relative to backend/
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    data_dir = Path(__file__).resolve().parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    DATABASE_URL = f"sqlite:///{data_dir}/operator.db"
else:
    # Ensure the directory exists for sqlite paths
    if DATABASE_URL.startswith("sqlite"):
        db_path = DATABASE_URL.replace("sqlite:///", "").replace("sqlite://", "")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# --- ORM Models ---

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    why = Column(Text)
    estimated_minutes = Column(Integer, default=30)
    project_tag = Column(String)  # matches project slug
    priority_score = Column(Float, default=0.0)
    status = Column(String, default="pending")  # pending | in_progress | done | deferred
    ai_generated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    slug = Column(String, nullable=False, unique=True)
    description = Column(Text)
    current_stage = Column(Integer, default=1)
    total_stages = Column(Integer, default=6)
    stage_label = Column(String)
    blockers = Column(Text)
    next_milestone = Column(String)
    github_repo = Column(String)
    last_commit_at = Column(DateTime)
    days_since_commit = Column(Integer)
    color = Column(String, default="#3b82f6")  # tailwind blue-500


class Goal(Base):
    __tablename__ = "goals"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    timeframe = Column(String, default="week")  # week | month | quarter
    progress = Column(Float, default=0.0)  # 0.0 - 1.0
    project_slug = Column(String)
    status = Column(String, default="active")  # active | completed | paused
    created_at = Column(DateTime, default=datetime.utcnow)


class AISuggestion(Base):
    __tablename__ = "ai_suggestions"
    id = Column(Integer, primary_key=True, index=True)
    body = Column(Text, nullable=False)
    category = Column(String)  # content | product | growth | market
    dismissed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class NewsBriefing(Base):
    __tablename__ = "news_briefings"
    id = Column(Integer, primary_key=True, index=True)
    headline = Column(String, nullable=False)
    summary = Column(Text)
    category = Column(String)  # ai | competitor | marketing | cad
    relevance_score = Column(Float, default=0.5)
    suggested_action = Column(Text)
    dismissed = Column(Boolean, default=False)
    briefing_date = Column(String)  # YYYY-MM-DD
    created_at = Column(DateTime, default=datetime.utcnow)


class GithubRepo(Base):
    __tablename__ = "github_repos"
    id = Column(Integer, primary_key=True, index=True)
    owner = Column(String, nullable=False)
    name = Column(String, nullable=False)
    full_name = Column(String, nullable=False, unique=True)
    description = Column(Text)
    stars = Column(Integer, default=0)
    open_issues = Column(Integer, default=0)
    open_prs = Column(Integer, default=0)
    last_commit_sha = Column(String)
    last_commit_message = Column(Text)
    last_commit_at = Column(DateTime)
    is_private = Column(Boolean, default=True)
    synced_at = Column(DateTime, default=datetime.utcnow)


class ContentDraft(Base):
    __tablename__ = "content_drafts"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    platform = Column(String, nullable=False)  # tiktok | youtube | instagram | twitter | blog | email
    content_type = Column(String, nullable=False)  # script | description | caption | thread | blog_post | newsletter
    hook = Column(Text)
    cta = Column(Text)
    hashtags = Column(Text)  # comma-separated
    suggested_post_time = Column(String)  # e.g. "2026-03-29T10:00"
    status = Column(String, default="draft")  # draft | approved | declined | scheduled | posted
    ai_generated = Column(Boolean, default=True)
    remix_of_id = Column(Integer)  # ID of original draft if this is a remix
    feedback = Column(Text)  # user feedback for remix
    project_tag = Column(String)  # matches project slug
    hook_score = Column(Float)  # predicted virality 0-10
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ContentScheduleItem(Base):
    __tablename__ = "content_schedule"
    id = Column(Integer, primary_key=True, index=True)
    draft_id = Column(Integer)  # FK to content_drafts
    title = Column(String, nullable=False)
    platform = Column(String, nullable=False)
    scheduled_at = Column(DateTime, nullable=False)
    status = Column(String, default="scheduled")  # scheduled | posted | cancelled
    block_type = Column(String, default="content")  # content | deep_work | business | research
    color = Column(String, default="#A855F7")
    created_at = Column(DateTime, default=datetime.utcnow)


class SocialMetric(Base):
    __tablename__ = "social_metrics"
    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String, nullable=False)  # tiktok | youtube | instagram | twitter
    date = Column(String, nullable=False)  # YYYY-MM-DD
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    followers = Column(Integer, default=0)
    engagement_rate = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)


class ContentScore(Base):
    __tablename__ = "content_scores"
    id = Column(Integer, primary_key=True, index=True)
    draft_id = Column(Integer)
    title = Column(String, nullable=False)
    platform = Column(String, nullable=False)
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    engagement_rate = Column(Float, default=0.0)
    virality_score = Column(Float, default=0.0)
    content_type = Column(String)
    topic = Column(String)
    posted_at = Column(DateTime)
    thumbnail_url = Column(String)
    video_url = Column(String)
    external_id = Column(String)  # platform-specific ID
    created_at = Column(DateTime, default=datetime.utcnow)


class Competitor(Base):
    __tablename__ = "competitors"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    platform = Column(String, nullable=False)
    handle = Column(String)
    url = Column(String)
    description = Column(Text)
    last_checked = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class CompetitorPost(Base):
    __tablename__ = "competitor_posts"
    id = Column(Integer, primary_key=True, index=True)
    competitor_id = Column(Integer)
    title = Column(String)
    url = Column(String)
    platform = Column(String)
    thumbnail_url = Column(String)
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    engagement = Column(Float, default=0.0)
    ai_analysis = Column(Text)
    posted_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class MarketGap(Base):
    __tablename__ = "market_gaps"
    id = Column(Integer, primary_key=True, index=True)
    description = Column(Text, nullable=False)
    source = Column(String)  # reddit | hackernews | twitter | forum
    source_url = Column(String)
    opportunity_score = Column(Float, default=0.5)
    suggested_action = Column(Text)
    category = Column(String)  # product | content | market
    status = Column(String, default="new")  # new | acted | dismissed
    created_at = Column(DateTime, default=datetime.utcnow)


class Lead(Base):
    __tablename__ = "leads"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False)
    platform = Column(String, nullable=False)
    message = Column(Text)
    source_url = Column(String)
    sentiment = Column(String)  # positive | neutral | negative
    category = Column(String, default="curious")  # hot | warm | curious
    status = Column(String, default="new")  # new | contacted | responded | interested | beta_user | paying | not_interested | no_response | skip
    suggested_action = Column(Text)
    dm_draft = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    # Outreach Command Center fields
    tier = Column(Integer)  # 1 (hot), 2 (warm), 3 (curious)
    tier_reason = Column(Text)
    account_summary = Column(Text)  # Claude-generated bullet points
    draft_dm = Column(Text)  # Claude-generated DM draft
    draft_public_reply = Column(Text)  # Claude-generated public reply
    include_demo_video = Column(Text)  # "yes" or "no" with reasoning
    post_text = Column(Text)  # full text of their post
    post_url = Column(String)  # direct link to their post
    profile_url = Column(String)
    post_date = Column(DateTime)
    contacted_at = Column(DateTime)
    responded_at = Column(DateTime)
    follow_up_sent = Column(Boolean, default=False)
    notes = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OutreachMessage(Base):
    __tablename__ = "outreach_messages"
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, index=True)
    direction = Column(String, nullable=False)  # "outbound" or "inbound"
    message_type = Column(String, nullable=False)  # "dm", "public_reply", "follow_up"
    message_text = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class CommentReply(Base):
    __tablename__ = "comment_replies"
    id = Column(Integer, primary_key=True, index=True)
    original_comment = Column(Text, nullable=False)
    username = Column(String)
    platform = Column(String, nullable=False)
    source_url = Column(String)
    reply_draft = Column(Text)
    status = Column(String, default="pending")  # pending | approved | sent | skipped
    created_at = Column(DateTime, default=datetime.utcnow)


class WaitlistSignup(Base):
    __tablename__ = "waitlist_signups"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, unique=True)
    name = Column(String)
    source = Column(String)  # tiktok | youtube | twitter | direct | referral
    source_detail = Column(String)  # specific post/video
    status = Column(String, default="active")  # active | converted | unsubscribed
    signed_up_at = Column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False, unique=True)
    email = Column(String)
    password_hash = Column(String, nullable=False)
    # Plan: "local" (self-hosted) | "starter" | "pro"
    plan = Column(String, default="local")
    # Stripe
    stripe_customer_id = Column(String)
    stripe_subscription_id = Column(String)
    subscription_status = Column(String, default="none")  # none | active | past_due | canceled
    # Cloud instance
    instance_ip = Column(String)
    instance_id = Column(String)  # Hetzner server ID
    instance_status = Column(String, default="none")  # none | provisioning | running | stopped | error
    instance_domain = Column(String)
    # Weekly availability: JSON string like {"mon":2,"tue":2,"wed":2,"thu":0,"fri":5,"sat":5,"sun":5}
    weekly_hours = Column(String, default='{"mon":2,"tue":2,"wed":2,"thu":2,"fri":2,"sat":0,"sun":0}')
    # Persistent notes the mentor remembers (user texts "note: ..." to add)
    mentor_notes = Column(Text, default="")
    # Product stage 1-4 (drives all AI advice). 1 = building core pipeline (default).
    # NOT a calendar week — set by the founder / inferred from the codebase.
    startup_stage = Column(Integer, default=1)
    stage_updated_at = Column(DateTime)
    # Living description of what the founder is building (replaces hardcoded paragraphs).
    # Refreshed from the real repo by the codebase digest.
    startup_profile = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    role = Column(String, nullable=False)  # "user" or "mentor"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class AgentMemory(Base):
    """Persistent memory for the autonomous mentor agent across runs."""
    __tablename__ = "agent_memory"
    id = Column(Integer, primary_key=True, index=True)
    run_type = Column(String, nullable=False)  # "morning" | "midday" | "evening"
    findings = Column(Text)  # JSON: what the agent discovered during analysis
    message_sent = Column(Text)  # the Telegram message that was sent
    tools_used = Column(Text)  # JSON: list of tools the agent used
    created_at = Column(DateTime, default=datetime.utcnow)


class CodebaseSnapshot(Base):
    """A digest of the founder's actual product repo (e.g. meshToParametric).

    Generated where the code lives (locally) and pushed to the cloud DB so the
    bot — which runs on the VPS and can't see the local filesystem — can still
    understand what's actually being built and how far along it is.
    """
    __tablename__ = "codebase_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    summary = Column(Text)        # compact human/AI-readable digest, dropped into prompts
    detail = Column(Text)         # fuller JSON blob (commits, signals, tree)
    commit_sha = Column(String)   # HEAD sha at digest time
    source = Column(String, default="local")  # "local" | "github" | "manual"
    created_at = Column(DateTime, default=datetime.utcnow)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _migrate_columns():
    """Add columns introduced after a DB was first created.

    SQLAlchemy's create_all() only creates missing *tables*, never missing
    *columns*. These ALTER statements are idempotent (guarded by try/except)
    so they're safe to run on every startup.
    """
    from sqlalchemy import text
    migrations = [
        "ALTER TABLE users ADD COLUMN startup_stage INTEGER DEFAULT 1",
        "ALTER TABLE users ADD COLUMN stage_updated_at DATETIME",
        "ALTER TABLE users ADD COLUMN startup_profile TEXT DEFAULT ''",
    ]
    with engine.begin() as conn:
        for stmt in migrations:
            try:
                conn.execute(text(stmt))
            except Exception:
                # Column already exists (or table not present yet) — ignore.
                pass


def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate_columns()
