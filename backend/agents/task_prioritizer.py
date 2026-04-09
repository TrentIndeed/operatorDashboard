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

WEEK-SPECIFIC TASKS (check marketing_plan_week in context):

WEEK 1 — Fix Core Pipeline + Start Outreach:
Product tasks:
- "Fix hole detection (RANSAC cylinder fitting) on clean test meshes"
- "Fix chamfer/fillet detection on plates"
- "Build scan simulation script using lidar, industrial, and ai_mesh presets"
- "Run degraded meshes through pipeline, fix noise tolerance in RANSAC/plane fitting"
- "Add Open3D/trimesh decimation as first pipeline stage (target 20-50K triangles)"
- "Implement cut-extrude: parallel plane pair detection for pockets/channels"
- "Test: U-channel and open-top box should reconstruct as extrude + cut-extrude"
Marketing tasks:
- "Ship minimal waitlist page: one-liner, GIF of plate conversion, email signup, 'How did you hear?' field"
- "Cold outreach: search Onshape forum, r/onshape, r/cad, r/3Dprinting, LinkedIn for mesh frustration posts"
- "DM 10-15 people who posted about mesh/STL/Onshape problems"
- "Reply to 2-3 forum threads with genuine helpful answers (no self-promo)"
- "Write blog post #1 targeting 'convert STL to parametric CAD' (800-1200 words)"
- Do NOT suggest Show HN, Product Hunt, launches, or heavy social media.

WEEK 2 — Multi-Extrusion Parts + Grow Conversations:
Product tasks:
- "Build multi-extrusion: L-brackets (two extrusions at 90 degrees)"
- "Build multi-extrusion: motor mounts (plate + raised boss/standoff)"
- "Build multi-extrusion: simple enclosures (extrude + cut-extrude)"
- "Test all multi-extrusion parts on degraded meshes, not just clean exports"
- "Download 5 mechanical parts from Meshy, run through pipeline, identify failures"
- "Add wider angular threshold for AI mesh plane detection"
- "Download 3-5 real scan meshes from Artec 3D / Sketchfab, run through pipeline"
- "Record first demo videos: 10-15 sec each, mesh in → parametric out → edit dimension"
Marketing tasks:
- "Continue 10-15 DMs/day, follow up with Week 1 responders"
- "Once demo videos ready: include them in DMs for higher response rates"
- "Write blog post #2 targeting 'mesh to Onshape' or 'reverse engineer STL to STEP'"
- Do NOT suggest launches.

WEEK 3 — Beta Testing + Full Landing Page:
Product tasks (4-5 hours — some time shifts to marketing):
- "Review every failed conversion from Week 2, fix most common failure modes"
- "Add clear error messages for unsupported geometry"
- "Give 10-15 beta testers access, ask each to convert one part from their workflow"
- "Collect feedback: 'Did it work? What broke? What would make this useful?'"
- "Start AI assistant MVP: natural language to FeatureScript parameter update"
Marketing tasks (2 hours/day):
- "Build full landing page: hero + demo video, 3-4 looping demos, how-it-works, pricing, CTA"
- "Pricing: Free (5 conversions), Pro ($29/mo, 30 conversions), Pay-as-you-go ($2-3/conversion)"
- "Collect 2-3 testimonials from beta testers, add to landing page"
- "Draft Product Hunt ship page: 5 screenshots, GIF demo, tagline, maker story"
- "Draft Show HN post: technical, honest, focused on engineering problem"
- "Draft Reddit posts for r/onshape, r/cad, r/3Dprinting (tailored to each)"
- "Write blog post #3 targeting 'Backflip AI alternative' or 'AI mesh to CAD tool'"

WEEK 4 — Launch:
- "Launch on Product Hunt at 12:01 AM PT (Tuesday)"
- "Post Show HN at 9 AM ET"
- "Post to r/onshape, r/cad, r/3Dprinting throughout the day"
- "LinkedIn launch post tagging beta testers who gave testimonials"
- "DM everyone on beta list and outreach list: 'We just launched'"
- "Email waitlist: 'ParameshAI is live — here's your free account'"
- "Respond personally to every comment on PH, HN, and Reddit"
- "Post Day 1 results update on LinkedIn"
- "Blog post #4: launch retrospective — 'I built a mesh-to-CAD tool and launched in 4 weeks'"
- "Record 'Getting Started' tutorial video for new signups"
- "Analyze: where did signups come from? Top channel? Conversion success rate?"

Each task must:
- Have a SPECIFIC, actionable title (not vague)
- Explain WHY it matters for the plan
- Have a realistic time estimate matching the daily time split
- Be tagged to the right project using slugs from context

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

    # Determine which week of the 4-week marketing plan we're in
    # Plan started ~April 4, 2026
    from datetime import date
    plan_start = date(2026, 4, 8)
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
