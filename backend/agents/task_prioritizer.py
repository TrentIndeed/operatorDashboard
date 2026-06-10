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


PRIORITIZE_PROMPT = """Generate today's top tasks for a solo founder executing a PRODUCT-FIRST 4-week plan for ParameshAI (mesh-to-parametric CAD for Onshape).

DAILY TIME SPLIT:
- Product development: 5-6 hours (PRIMARY until Week 3)
- Cold outreach: 30 min (10-15 DMs/day + 2-3 public forum replies)
- Blog post writing: 30 min (1 post/week, AI-assisted)
- Social media: 10 min (every other day, skip if busy)

TASK MIX:
- 3-4 PRODUCT tasks (pipeline work, testing, bug fixes — this is the bulk of the day)
- 1 OUTREACH task (DMs, forum replies — 30 min)
- 0-1 CONTENT task (blog writing, video recording — 30 min)
- Do NOT generate social media tasks unless it's every-other-day and the user has time

REALISTIC TIME ESTIMATES (CRITICAL — these are HARD MINIMUMS):
Product/pipeline tasks take LONGER than you'd think. These are the MINIMUMS:
- Bug fix in pipeline (chamfer, RANSAC tuning, plane fitting): MINIMUM 90 min, typically 120-180
- New feature (cut-extrude, multi-extrusion, decimation, scan sim): MINIMUM 120 min, typically 180-240
- Writing a new test script: MINIMUM 60 min, typically 90-120
- Debugging a test failure: MINIMUM 60 min
- Integration work (wiring a new stage into the pipeline): MINIMUM 90 min
- Reverse-engineering why something broke: MINIMUM 60 min

Marketing tasks are shorter:
- Cold outreach batch (10-15 DMs): 30 min
- Forum replies (2-3 helpful answers): 30 min
- Blog post writing (1000 words in one session): 60-90 min
- Ship waitlist page: 60-90 min
- Record demo video: 15-30 min
- Edit demo video: 30-45 min

**HARD RULE**: If the title contains "fix", "implement", "build", "add", "write script", "debug",
  estimated_minutes MUST be >= 60. Typical minimum for product work is 90.
**NEVER** output 30 or 45 min for a coding/debugging task. Only marketing tasks get those values.

EXAMPLE of a CORRECT response for a 2-hour day:
[
  {"title": "Fix chamfer/fillet detection on degraded mesh normals", "estimated_minutes": 120, "priority_score": 9.5, "why": "...", "project_tag": "parameshai"},
  {"title": "Send 10-15 cold DMs to Onshape users with mesh pain", "estimated_minutes": 30, "priority_score": 7, "why": "...", "project_tag": "parameshai"}
]
Notice: only 2 tasks because the chamfer fix REALISTICALLY takes 2h. Do not compress to fit.

EXAMPLE of an INCORRECT response (do not do this):
[
  {"title": "Fix chamfer detection", "estimated_minutes": 45, "priority_score": 9},  // WRONG — coding task is never 45 min
  {"title": "Implement cut-extrude", "estimated_minutes": 60, "priority_score": 9},  // WRONG — new feature is never 60 min
  {"title": "Write scan simulation script", "estimated_minutes": 30, "priority_score": 8}  // WRONG — script takes 60-120 min
]

STAGE-DRIVEN FOCUS:
The context includes a CURRENT STAGE block (1-4) with what to focus on and what is OFF-LIMITS.
Follow it strictly. Do NOT generate launch/Show HN/Product Hunt/heavy-marketing tasks unless the stage
explicitly says distribution is in launch mode. When the stage is early, the product is not ready, so the
bulk of tasks are pipeline/engineering work and any outreach is the quiet, educational kind the stage allows.

Good PRODUCT task examples (phrase to match the founder's actual code and blockers in context):
- "Fix chamfer/fillet detection on degraded mesh normals"
- "Implement cut-extrude: parallel plane pair detection for pockets"
- "Run real scan meshes through the pipeline, fix the top failure mode"
- "Add decimation as the first pipeline stage (target 20-50K triangles)"
Stage-appropriate OUTREACH task examples (only what the stage permits):
- Early stages: "Find 5 r/onshape or r/cad posts about mesh-to-CAD pain and write genuinely helpful replies (no product mention), save the posters as leads"
- Beta/launch stages only: recruiting testers, demo-video DMs, drafting/posting launch materials

Each task must:
- Have a SPECIFIC, actionable title (not vague)
- Explain WHY it matters for the plan
- Use REALISTIC time estimates from the baselines above (coding tasks are NEVER 30 min)
- Be tagged to the right project using slugs from context

If a user has only 2 hours today, it's better to have 1 real product task (120 min) + outreach (30 min)
than to cram 4 underestimated tasks that won't actually finish.

Scoring guide (priority_score 0-10):
- 9-10: Critical pipeline work blocking the plan (Weeks 1-2) or launch tasks (Week 4)
- 7-8: Important product work (testing, new geometry types, bug fixes)
- 5-6: Cold outreach (DMs, forum replies — daily non-negotiable)
- 3-4: Content creation (blog writing, video recording)
- 1-2: Social media, admin

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

    # Current stage drives focus (replaces the old calendar-week math).
    from agents.stage import get_stage, stage_name, context_block as _stage_context
    current_stage = get_stage(db)

    context = {
        "date": datetime.utcnow().isoformat(),
        "day_of_week": today_day,
        "current_stage": current_stage,
        "stage_name": stage_name(current_stage),
        "stage_context": _stage_context(db),
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

    # Adjust task count based on available time (MAX — Claude can return fewer)
    if available_hours == 0:
        # Day off — no tasks
        return []
    elif available_hours <= 2:
        n = 3  # up to 3 tasks max (might be just 1 big coding task + outreach)
    elif available_hours <= 4:
        n = 5
    else:
        n = 7

    task_instruction = f"""

IMPORTANT: The user has {available_hours} hours ({available_minutes} minutes) available today ({today_day}).

USE REALISTIC TIME ESTIMATES — do NOT compress them to fit the daily budget.
A chamfer fix is 90-120 min whether the user has 2 hours or 8 hours.
If a single realistic task takes all their time, return fewer tasks.

Budget guidance:
- 2h available: often 1 realistic product task (90-120 min) + outreach (30 min). That's 2 tasks, not 3.
- 4h available: 2-3 product tasks (totaling ~3h) + outreach (30 min) + content (30 min)
- 6h+: full stack — 3-4 product + outreach + content

The estimated_minutes field must reflect HOW LONG THE TASK ACTUALLY TAKES, not how much time is left in the day.
If estimates exceed available time, that's fine — the user will pick the highest priority ones."""

    tasks_data = reason_json(PRIORITIZE_PROMPT + task_instruction, context=context)

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
