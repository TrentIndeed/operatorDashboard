"""
Task prioritization agent.
Uses Claude to rank and generate today's top tasks.
"""
from typing import List
from datetime import datetime
from sqlalchemy.orm import Session

import json as _json
from agents.reasoning import reason_json, FAST_MODEL
from db.database import Task, Project, Goal, AISuggestion, User


PRIORITIZE_PROMPT = """Generate today's top 5 tasks for a solo founder focused on GROWING their business. The mix should be:

- 2-3 GROWTH tasks (outreach, networking, content, community engagement)
- 1-2 PRODUCT tasks (only if there's a critical blocker or shipping deadline)
- 0-1 ADMIN tasks (only if absolutely necessary)

GROWTH task examples (be specific, not generic):
- "Reply to 10 comments on Reddit r/[relevant subreddit] about [topic]"
- "Film a 60-second TikTok showing [specific demo/result]"
- "DM 5 people on Twitter who posted about [topic] this week"
- "Post a build-in-public update thread on Twitter with screenshots"
- "Join 2 Discord servers in [niche] and introduce yourself with value"
- "Write a HackerNews Show HN post about [project]"
- "Comment on 5 YouTube videos in [niche] with genuine insights"
- "Create an Instagram carousel: '5 things I learned building [X]'"
- "Cold email 3 potential beta users found on [platform]"
- "Record a YouTube tutorial: 'How to [solve specific problem]'"
- "Post in 3 IndieHackers/Reddit threads with helpful answers (soft CTA)"
- "Reply to every comment on your last TikTok/YouTube video"
- "Send a LinkedIn post about your latest milestone"

Each task must:
- Have a SPECIFIC, actionable title (not vague like "do outreach")
- Explain WHY it matters for growth (tie to audience, clients, or revenue)
- Have a realistic time estimate
- Be tagged to the right project using slugs from context

Scoring guide (priority_score 0-10):
- 9-10: Revenue-generating or time-sensitive growth opportunity
- 7-8: High-audience-growth impact (content that could go viral, community with hot discussion)
- 5-6: Steady growth (regular posting, routine engagement)
- 3-4: Product work (development, bug fixes)
- 1-2: Admin/maintenance

Respond with a JSON array of tasks:
[
  {
    "title": "string — specific and actionable",
    "why": "string — 1-2 sentences on why this grows the business today",
    "estimated_minutes": integer,
    "project_tag": "string",
    "priority_score": float
  }
]
"""


def generate_priority_tasks(
    db: Session,
    n: int = 5,
) -> List[dict]:
    """
    Ask Claude to generate today's top N tasks based on current project state.
    Replaces old AI-generated pending tasks so there are no duplicates.
    Manually created tasks and in-progress/done tasks are never touched.
    """
    # Build context from current DB state
    projects = db.query(Project).all()
    active_goals = db.query(Goal).filter(Goal.status == "active").all()

    # Include manually created tasks so Claude knows what the user already planned
    manual_tasks = (
        db.query(Task)
        .filter(Task.status.in_(["pending", "in_progress"]), Task.ai_generated == False)
        .order_by(Task.priority_score.desc())
        .limit(10)
        .all()
    )

    # Get today's available hours from user schedule
    day_names = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    today_day = day_names[datetime.utcnow().weekday()]
    available_hours = 2  # default
    user = db.query(User).first()
    if user and user.weekly_hours:
        try:
            schedule = _json.loads(user.weekly_hours)
            available_hours = schedule.get(today_day, 2)
        except (_json.JSONDecodeError, TypeError):
            pass

    available_minutes = available_hours * 60

    context = {
        "date": datetime.utcnow().isoformat(),
        "day_of_week": today_day,
        "available_hours_today": available_hours,
        "available_minutes_today": available_minutes,
        "projects": [
            {
                "name": p.name,
                "stage": f"{p.current_stage}/{p.total_stages}",
                "stage_label": p.stage_label,
                "blockers": p.blockers,
                "next_milestone": p.next_milestone,
            }
            for p in projects
        ],
        "active_goals": [
            {"title": g.title, "timeframe": g.timeframe, "progress": g.progress}
            for g in active_goals
        ],
        "user_created_tasks": [
            {"title": t.title, "priority_score": t.priority_score}
            for t in manual_tasks
        ],
    }

    # Adjust task count based on available time
    if available_hours == 0:
        # Day off — no tasks
        return []
    elif available_hours <= 2:
        n = 3  # light day
    elif available_hours <= 4:
        n = 5  # normal day
    else:
        n = 7  # heavy day

    tasks_data = reason_json(PRIORITIZE_PROMPT + f"\n\nIMPORTANT: The user has {available_hours} hours ({available_minutes} minutes) available today ({today_day}). Generate tasks that total APPROXIMATELY {available_minutes} minutes. If 0 hours, return an empty array.", context=context)

    # Remove old AI-generated pending tasks (replace, don't stack)
    old_ai_tasks = (
        db.query(Task)
        .filter(Task.ai_generated == True, Task.status == "pending")
        .all()
    )
    for old in old_ai_tasks:
        db.delete(old)

    # Persist new tasks
    new_tasks = []
    for t in tasks_data[:n]:
        db_task = Task(
            title=t["title"],
            why=t.get("why"),
            estimated_minutes=t.get("estimated_minutes", 30),
            project_tag=t.get("project_tag"),
            priority_score=t.get("priority_score", 5.0),
            ai_generated=True,
            status="pending",
        )
        db.add(db_task)
        new_tasks.append(db_task)

    db.commit()
    for t in new_tasks:
        db.refresh(t)

    return new_tasks


SUGGESTIONS_PROMPT = """Generate 5 HIGH-IMPACT growth suggestions for a solo founder. Focus on getting clients, building audience, and generating revenue.

Categories:
- outreach: networking, DMs, cold outreach, community engagement, partnerships
- content: social media strategy, video ideas, post hooks, content gaps
- growth: audience building, virality tactics, SEO, lead generation
- market: competitor gaps, underserved niches, trending opportunities

At least 3 of 5 suggestions should be about OUTREACH or CONTENT (not product).

Each suggestion should name specific platforms, communities, or tactics — not generic advice like "post more content."

Respond with JSON:
[
  {
    "body": "string — the suggestion (1-3 sentences, direct and specific with named platforms/communities)",
    "category": "outreach | content | growth | market"
  }
]
"""


def generate_suggestions(db: Session) -> List[dict]:
    """Generate AI suggestions and save to DB."""
    projects = db.query(Project).all()
    context = {
        "projects": [
            {
                "name": p.name,
                "stage": f"{p.current_stage}/{p.total_stages}",
                "next_milestone": p.next_milestone,
                "blockers": p.blockers,
            }
            for p in projects
        ]
    }

    suggestions_data = reason_json(SUGGESTIONS_PROMPT, context=context)

    new_suggestions = []
    for s in suggestions_data[:5]:
        db_s = AISuggestion(
            body=s["body"],
            category=s.get("category"),
        )
        db.add(db_s)
        new_suggestions.append(db_s)

    db.commit()
    for s in new_suggestions:
        db.refresh(s)

    return new_suggestions
