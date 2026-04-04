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


PRIORITIZE_PROMPT = """Generate today's top tasks for a solo founder executing a 4-week marketing plan for ParameshAI (mesh-to-parametric CAD for Onshape). The mix should be:

- 2-3 DISTRIBUTION tasks (content creation, community engagement, outreach, launches)
- 1 PRODUCT task (only if there's a critical blocker for the marketing plan)
- 0-1 ADMIN tasks (only if absolutely necessary)

DAILY NON-NEGOTIABLES (include at least 2 of these every day):
- "Post 1 LinkedIn update about ParameshAI" (problem awareness, build journey, demo, or technical insight)
- "Spend 30 min in r/onshape, r/cad, r/3Dprinting answering questions (no self-promo, just be helpful)"
- "DM 5 people who posted about mesh/STL/Onshape problems on LinkedIn or Reddit"
- "Post 2-3 tweets on X about mesh-to-parametric workflows or build progress"

WEEKLY CONTENT (spread across the week):
- Record 1 screen-capture demo of a mesh-to-parametric conversion (15-30 sec short-form)
- Write 1 technical blog post (mesh workflows, reverse engineering, Onshape tips)
- Film 1 YouTube Short showing before/after of a mesh conversion
- Create 1 comparison post: manual rebuild vs ParameshAI

WEEK-SPECIFIC TASKS (check marketing_plan_week in context):

WEEK 1 — Foundation & Positioning:
- "Write homepage hero copy and 200-word explainer for parameshai.com"
- "Record screen-capture demo of mesh-to-parametric conversion (gear/bracket/enclosure)"
- "Edit demo into 15-30 sec short-form clip for YouTube Shorts"
- "Write blog post: 'Why mesh-to-parametric is still painful in 2026'"
- "Draft 5 LinkedIn posts: problem awareness, build journey, technical insight, demo, personal story"
- "Set up LinkedIn profile headline: 'Building ParameshAI — mesh to parametric CAD for Onshape'"
- Do NOT suggest Show HN, Product Hunt, or launches in Week 1.

WEEK 2 — Community Seeding:
- "Answer 2-3 questions in r/onshape, r/cad, r/3Dprinting about mesh workflows (no self-promo)"
- "DM 5 people on LinkedIn/Reddit who posted about mesh/STL/Onshape problems"
- "Write blog: 'I converted 10 Thingiverse STLs to parametric Onshape — what worked'"
- "Record side-by-side comparison: manual rebuild vs ParameshAI (timed)"
- "Write X thread: 'How RANSAC + region growing identifies surfaces in a mesh'"
- "LinkedIn post: 'Backflip raised $30M for scan-to-CAD. Here's why I think the real gap is...'"
- Do NOT suggest launches in Week 2.

WEEK 3 — Launch Prep:
- "Give 10 early users free access, ask them to complete one task"
- "Collect 3 short testimonials from early access users"
- "Prepare Product Hunt ship page: screenshots, GIF demo, tagline"
- "Draft Show HN post for ParameshAI (honest, technical)"
- "Draft Reddit posts for r/onshape, r/cad, r/3Dprinting (tailored to each)"
- "Publish comparison: ParameshAI vs manual rebuild vs Backflip"

WEEK 4 — Launch:
- "Launch on Product Hunt at 12:01 AM PT (Tuesday)"
- "Post Show HN at 9 AM ET"
- "Cross-post to r/onshape, r/cad, r/3Dprinting"
- "LinkedIn launch post tagging early users who gave testimonials"
- "X thread telling the full build story"
- "Follow up on all PH and HN comments personally"
- "Post Day 1 results update on LinkedIn"

Each task must:
- Have a SPECIFIC, actionable title (not vague)
- Explain WHY it matters for the marketing plan
- Have a realistic time estimate
- Be tagged to the right project using slugs from context

Scoring guide (priority_score 0-10):
- 9-10: Launch-related or high-visibility distribution (PH, HN, viral content potential)
- 7-8: Daily distribution (LinkedIn post, community engagement, DMs)
- 5-6: Content creation (blog, video recording, editing)
- 3-4: Product work (only if blocking the marketing plan)
- 1-2: Admin

Respond with a JSON array of tasks:
[
  {
    "title": "string",
    "why": "string",
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

    # Determine which week of the 4-week marketing plan we're in
    # Plan started ~April 4, 2026
    from datetime import date
    plan_start = date(2026, 4, 4)
    days_since_start = (date.today() - plan_start).days
    current_week = min(4, max(1, (days_since_start // 7) + 1))

    context = {
        "date": datetime.utcnow().isoformat(),
        "day_of_week": today_day,
        "marketing_plan_week": current_week,
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
