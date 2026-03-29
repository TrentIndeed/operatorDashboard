from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# --- Task Schemas ---

class TaskBase(BaseModel):
    title: str
    why: Optional[str] = None
    estimated_minutes: int = 30
    project_tag: Optional[str] = None
    priority_score: float = 0.0
    status: str = "pending"
    ai_generated: bool = False


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    why: Optional[str] = None
    estimated_minutes: Optional[int] = None
    project_tag: Optional[str] = None
    priority_score: Optional[float] = None
    status: Optional[str] = None


class TaskOut(TaskBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- Project Schemas ---

class ProjectBase(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    current_stage: int = 1
    total_stages: int = 6
    stage_label: Optional[str] = None
    blockers: Optional[str] = None
    next_milestone: Optional[str] = None
    github_repo: Optional[str] = None
    color: str = "#3b82f6"


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    current_stage: Optional[int] = None
    stage_label: Optional[str] = None
    blockers: Optional[str] = None
    next_milestone: Optional[str] = None


class ProjectOut(ProjectBase):
    id: int
    last_commit_at: Optional[datetime] = None
    days_since_commit: Optional[int] = None

    class Config:
        from_attributes = True


# --- Goal Schemas ---

class GoalBase(BaseModel):
    title: str
    timeframe: str = "week"
    progress: float = 0.0
    project_slug: Optional[str] = None
    status: str = "active"


class GoalCreate(GoalBase):
    pass


class GoalUpdate(BaseModel):
    progress: Optional[float] = None
    status: Optional[str] = None
    title: Optional[str] = None


class GoalOut(GoalBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# --- AI Suggestion Schemas ---

class AISuggestionOut(BaseModel):
    id: int
    body: str
    category: Optional[str] = None
    dismissed: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- News Briefing Schemas ---

class NewsBriefingOut(BaseModel):
    id: int
    headline: str
    summary: Optional[str] = None
    category: Optional[str] = None
    relevance_score: float
    suggested_action: Optional[str] = None
    dismissed: bool
    briefing_date: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- GitHub Repo Schemas ---

class GithubRepoOut(BaseModel):
    id: int
    owner: str
    name: str
    full_name: str
    description: Optional[str] = None
    stars: int
    open_issues: int
    open_prs: int
    last_commit_sha: Optional[str] = None
    last_commit_message: Optional[str] = None
    last_commit_at: Optional[datetime] = None
    is_private: bool
    synced_at: datetime

    class Config:
        from_attributes = True


# --- Command Center Response ---

class CommandCenterData(BaseModel):
    tasks: List[TaskOut]
    projects: List[ProjectOut]
    goals_week: List[GoalOut]
    goals_month: List[GoalOut]
    goals_quarter: List[GoalOut]
    suggestions: List[AISuggestionOut]
    briefing: List[NewsBriefingOut]


# --- Content Draft Schemas ---

class ContentDraftBase(BaseModel):
    title: str
    body: str
    platform: str
    content_type: str
    hook: Optional[str] = None
    cta: Optional[str] = None
    hashtags: Optional[str] = None
    suggested_post_time: Optional[str] = None
    status: str = "draft"
    ai_generated: bool = True
    remix_of_id: Optional[int] = None
    feedback: Optional[str] = None
    project_tag: Optional[str] = None
    hook_score: Optional[float] = None

class ContentDraftCreate(ContentDraftBase):
    pass

class ContentDraftUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    status: Optional[str] = None
    feedback: Optional[str] = None
    suggested_post_time: Optional[str] = None

class ContentDraftOut(ContentDraftBase):
    id: int
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

# --- Content Schedule Schemas ---

class ScheduleItemBase(BaseModel):
    draft_id: Optional[int] = None
    title: str
    platform: str
    scheduled_at: datetime
    status: str = "scheduled"
    block_type: str = "content"
    color: str = "#A855F7"

class ScheduleItemCreate(ScheduleItemBase):
    pass

class ScheduleItemUpdate(BaseModel):
    scheduled_at: Optional[datetime] = None
    status: Optional[str] = None
    block_type: Optional[str] = None

class ScheduleItemOut(ScheduleItemBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

# --- Hook Generator ---

class HookRequest(BaseModel):
    topic: str
    platform: str = "tiktok"
    project_tag: str = "ai-automation"

class HookVariation(BaseModel):
    hook: str
    score: float
    full_script: str
    cta: str

class HookResponse(BaseModel):
    variations: List[HookVariation]


# --- Social Metric Schemas ---

class SocialMetricOut(BaseModel):
    id: int
    platform: str
    date: str
    views: int
    likes: int
    comments: int
    shares: int
    saves: int
    followers: int
    engagement_rate: float
    created_at: datetime

    class Config:
        from_attributes = True


# --- Content Score Schemas ---

class ContentScoreOut(BaseModel):
    id: int
    draft_id: Optional[int] = None
    title: str
    platform: str
    views: int
    likes: int
    saves: int
    shares: int
    comments_count: int
    engagement_rate: float
    virality_score: float
    content_type: Optional[str] = None
    topic: Optional[str] = None
    posted_at: Optional[datetime] = None
    thumbnail_url: Optional[str] = None
    video_url: Optional[str] = None
    external_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Competitor Schemas ---

class CompetitorOut(BaseModel):
    id: int
    name: str
    platform: str
    handle: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    last_checked: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CompetitorPostOut(BaseModel):
    id: int
    competitor_id: Optional[int] = None
    title: Optional[str] = None
    url: Optional[str] = None
    platform: Optional[str] = None
    thumbnail_url: Optional[str] = None
    views: int
    likes: int
    comments_count: int
    engagement: float
    ai_analysis: Optional[str] = None
    posted_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Market Gap Schemas ---

class MarketGapOut(BaseModel):
    id: int
    description: str
    source: Optional[str] = None
    source_url: Optional[str] = None
    opportunity_score: float
    suggested_action: Optional[str] = None
    category: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# --- Lead Schemas ---

class LeadOut(BaseModel):
    id: int
    username: str
    platform: str
    message: Optional[str] = None
    source_url: Optional[str] = None
    sentiment: Optional[str] = None
    category: str
    status: str
    suggested_action: Optional[str] = None
    dm_draft: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class LeadUpdate(BaseModel):
    status: Optional[str] = None
    category: Optional[str] = None
    sentiment: Optional[str] = None
    suggested_action: Optional[str] = None
    dm_draft: Optional[str] = None


# --- Comment Reply Schemas ---

class CommentReplyOut(BaseModel):
    id: int
    original_comment: str
    username: Optional[str] = None
    platform: str
    source_url: Optional[str] = None
    reply_draft: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class CommentReplyUpdate(BaseModel):
    status: Optional[str] = None
    reply_draft: Optional[str] = None


# --- Waitlist Schemas ---

class WaitlistSignupOut(BaseModel):
    id: int
    email: str
    name: Optional[str] = None
    source: Optional[str] = None
    source_detail: Optional[str] = None
    status: str
    signed_up_at: datetime

    class Config:
        from_attributes = True


class WaitlistSignupCreate(BaseModel):
    email: str
    name: Optional[str] = None
    source: Optional[str] = None
    source_detail: Optional[str] = None


# --- Analytics Overview ---

class AnalyticsOverview(BaseModel):
    metrics_by_platform: dict  # platform -> latest metrics
    total_followers: int
    total_views_30d: int
    avg_engagement_rate: float
    top_content: List[ContentScoreOut]
    growth_trend: List[SocialMetricOut]
