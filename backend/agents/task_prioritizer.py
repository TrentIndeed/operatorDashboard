"""
Task prioritization agent.
Uses Claude to rank and generate today's top tasks.
"""
from typing import List
from datetime import datetime
from sqlalchemy.orm import Session

from agents.reasoning import reason_json, FAST_MODEL
from db.database import Task, Project, Goal, AISuggestion


PRIORITIZE_PROMPT = """Given the current state of the operator dashboard, generate and rank today's top 5 tasks.

Each task must:
- Have a clear, specific title
- Explain WHY it matters right now (tie to revenue, growth, or risk mitigation)
- Have a realistic time estimate
- Be tagged to the right project

Use the project slugs from the context as project_tag values.

Scoring guide (priority_score 0-10):
- 9-10: Blocks revenue or has expiring time window (trending topic, competitor launch)
- 7-8: High-growth impact (content that could go viral, key feature for waitlist)
- 5-6: Important but not urgent (regular dev work, scheduled content)
- 3-4: Nice to have (documentation, minor improvements)
- 1-2: Backlog (exploratory, low priority)

Respond with a JSON array of tasks:
[
  {
    "title": "string",
    "why": "string — 1-2 sentences on why this matters today",
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

    context = {
        "date": datetime.utcnow().isoformat(),
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

    tasks_data = reason_json(PRIORITIZE_PROMPT, context=context)

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


SUGGESTIONS_PROMPT = """Based on the current project state and market context, generate 5 high-signal AI suggestions for the operator.

Each suggestion should be:
- Specific and actionable (not generic advice)
- Tied to a real opportunity or risk
- Categorized: content | product | growth | market

Respond with JSON:
[
  {
    "body": "string — the suggestion (1-3 sentences, direct and specific)",
    "category": "content | product | growth | market"
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
