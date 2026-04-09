"""
Dashboard Snapshot — dumps current business state for the autonomous agent.

Returns a structured dict the agent can read to understand the founder's
current situation without manual prompt assembly.
"""
import os
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from db.database import (
    Task, Goal, Project, GithubRepo, ContentDraft,
    MarketGap, Lead, ChatMessage, User, SocialMetric,
    AISuggestion, NewsBriefing, Competitor,
)


def get_snapshot(db: Session) -> dict:
    """Build a complete snapshot of the founder's current state."""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # --- Tasks ---
    pending_tasks = db.query(Task).filter(Task.status == "pending").order_by(
        Task.priority_score.desc()
    ).limit(15).all()

    completed_tasks = db.query(Task).filter(Task.status == "done").order_by(
        Task.updated_at.desc()
    ).limit(10).all()

    # --- Goals ---
    goals = db.query(Goal).filter(Goal.status == "active").all()

    # --- Projects ---
    projects = db.query(Project).all()

    # --- GitHub repos ---
    repos = db.query(GithubRepo).all()
    recent_commits = []
    for r in repos:
        if r.last_commit_at and r.last_commit_message:
            try:
                commit_time = r.last_commit_at if not isinstance(r.last_commit_at, str) else datetime.fromisoformat(str(r.last_commit_at).replace("Z", "+00:00"))
                age_hours = (now - commit_time.replace(tzinfo=None)).total_seconds() / 3600
                if age_hours < 72:  # last 3 days
                    recent_commits.append({
                        "repo": r.name,
                        "message": r.last_commit_message[:80],
                        "hours_ago": round(age_hours, 1),
                    })
            except Exception:
                pass

    # --- Content drafts ---
    recent_drafts = db.query(ContentDraft).filter(
        ContentDraft.status.in_(["draft", "approved", "scheduled"])
    ).order_by(ContentDraft.created_at.desc()).limit(5).all()

    # --- Market gaps ---
    market_gaps = db.query(MarketGap).filter(
        MarketGap.status == "new"
    ).order_by(MarketGap.opportunity_score.desc()).limit(5).all()

    # --- Leads ---
    hot_leads = db.query(Lead).filter(
        Lead.status.in_(["new", "contacted"])
    ).order_by(Lead.created_at.desc()).limit(5).all()

    # --- Chat history (recent user messages) ---
    chat_history = db.query(ChatMessage).order_by(
        ChatMessage.id.desc()
    ).limit(20).all()
    chat_history.reverse()

    # --- User context ---
    user = db.query(User).first()
    mentor_notes = (user.mentor_notes or "").strip() if user else ""

    # Weekly schedule
    day_names = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    eastern_offset = timedelta(hours=-4)
    from datetime import timezone
    now_eastern = datetime.now(timezone.utc) + eastern_offset
    today_day = day_names[now_eastern.weekday()]
    available_hours = 2
    weekly_schedule = {}
    if user and user.weekly_hours:
        try:
            weekly_schedule = json.loads(user.weekly_hours)
            available_hours = weekly_schedule.get(today_day, 2)
        except Exception:
            pass

    # --- Suggestions ---
    suggestions = db.query(AISuggestion).filter(
        AISuggestion.dismissed == False
    ).order_by(AISuggestion.created_at.desc()).limit(5).all()

    # --- Briefing ---
    briefings = db.query(NewsBriefing).filter(
        NewsBriefing.dismissed == False
    ).order_by(NewsBriefing.created_at.desc()).limit(5).all()

    # --- Social metrics (latest per platform) ---
    social = {}
    for platform in ["youtube", "tiktok", "twitter", "linkedin"]:
        latest = db.query(SocialMetric).filter(
            SocialMetric.platform == platform
        ).order_by(SocialMetric.date.desc()).first()
        if latest:
            social[platform] = {
                "followers": latest.followers,
                "views": latest.views,
                "engagement_rate": latest.engagement_rate,
                "date": latest.date,
            }

    # --- Competitors ---
    competitors = db.query(Competitor).limit(5).all()

    # --- Marketing plan week ---
    from datetime import date as date_type
    plan_start = date_type(2026, 4, 8)
    days_since = (date_type.today() - plan_start).days
    week = min(4, max(1, (days_since // 7) + 1))

    return {
        "timestamp": now.isoformat(),
        "today": now_eastern.strftime("%A %B %d, %Y"),
        "available_hours_today": available_hours,
        "weekly_schedule": weekly_schedule,
        "marketing_plan_week": week,
        "marketing_plan_day": days_since + 1,
        "tasks": {
            "pending": [
                {"id": t.id, "title": t.title, "minutes": t.estimated_minutes,
                 "score": t.priority_score, "project": t.project_tag, "why": t.why}
                for t in pending_tasks
            ],
            "completed_recently": [
                {"title": t.title, "project": t.project_tag,
                 "completed_at": t.updated_at.isoformat() if t.updated_at else None}
                for t in completed_tasks
            ],
        },
        "goals": [
            {"title": g.title, "progress": round(g.progress * 100), "timeframe": g.timeframe}
            for g in goals
        ],
        "projects": [
            {"name": p.name, "stage": p.stage_label, "blockers": p.blockers,
             "next_milestone": p.next_milestone, "github_repo": p.github_repo}
            for p in projects
        ],
        "github": {
            "recent_commits": recent_commits,
            "repos": [
                {"name": r.name, "description": r.description, "stars": r.stars,
                 "open_issues": r.open_issues, "open_prs": r.open_prs}
                for r in repos
            ],
        },
        "content": {
            "drafts": [
                {"title": d.title, "platform": d.platform, "status": d.status,
                 "hook_score": d.hook_score}
                for d in recent_drafts
            ],
        },
        "market_gaps": [
            {"description": g.description, "source": g.source,
             "opportunity_score": g.opportunity_score, "action": g.suggested_action}
            for g in market_gaps
        ],
        "leads": [
            {"username": l.username, "platform": l.platform, "category": l.category,
             "status": l.status}
            for l in hot_leads
        ],
        "social_metrics": social,
        "competitors": [
            {"name": c.name, "platform": c.platform, "handle": c.handle}
            for c in competitors
        ],
        "suggestions": [
            {"body": s.body, "category": s.category}
            for s in suggestions
        ],
        "briefing": [
            {"headline": b.headline, "summary": b.summary, "category": b.category,
             "action": b.suggested_action}
            for b in briefings
        ],
        "mentor_notes": mentor_notes,
        "chat_history": [
            {"role": m.role, "content": m.content,
             "time": m.created_at.isoformat() if m.created_at else None}
            for m in chat_history
        ],
    }
