import os
from pathlib import Path
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Ensure data directory exists
data_dir = Path(__file__).resolve().parent.parent.parent / "data"
data_dir.mkdir(exist_ok=True)

# Always use the resolved data_dir path — ignore .env DATABASE_URL for SQLite
DATABASE_URL = f"sqlite:///{data_dir}/operator.db"

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
    project_tag = Column(String)  # mesh2param | ai-automation | content | business | dashboard
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
    project_tag = Column(String)  # mesh2param | ai-automation | content
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
    status = Column(String, default="new")  # new | contacted | converted | dismissed
    suggested_action = Column(Text)
    dm_draft = Column(Text)
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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
