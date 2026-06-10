"""
Growth Mentor Agent — sends personalized SMS messages throughout the day.

Reads the user's current tasks, goals, and schedule, then generates
contextual growth-focused nudges via Claude.

Message types:
  - morning: Top priorities + motivational kick
  - midday: Progress check-in + outreach reminder
  - afternoon: Content creation nudge + deadline awareness
  - evening: Day recap + tomorrow preview
"""
from agents.reasoning import reason_json, _call_claude, FAST_MODEL
from agents.voice import STYLE_RULES


def generate_mentor_message(
    message_type: str,
    tasks: list[dict],
    goals: list[dict],
    projects: list[dict],
    completed_today: int = 0,
    available_hours: float = 2,
    completed_tasks: list[dict] = None,
    recent_commits: list[dict] = None,
    mentor_notes: str = "",
    context_block: str = "",
) -> str:
    """
    Generate a personalized growth mentor SMS message.

    Args:
        message_type: 'morning' | 'midday' | 'afternoon' | 'evening'
        tasks: Current pending tasks
        goals: Active goals
        projects: User's projects
        completed_today: Tasks completed so far today
        available_hours: Hours available today
        completed_tasks: Tasks completed today (titles)
        recent_commits: Recent GitHub commits today

    Returns:
        SMS message string (under 300 chars for readability)
    """
    task_summary = "\n".join(
        f"- {t.get('title', '')} ({t.get('estimated_minutes', 30)}m, score {t.get('priority_score', 0)})"
        for t in tasks[:5]
    ) or "No tasks set"

    goal_summary = "\n".join(
        f"- {g.get('title', '')} ({int(g.get('progress', 0) * 100)}%)"
        for g in goals[:5]
    ) or "No goals set"

    project_summary = "\n".join(
        f"- {p.get('name', '')}: {p.get('stage_label', '')}"
        for p in projects[:4]
    ) or "No projects"

    completed_summary = ""
    if completed_tasks:
        completed_summary = "\n\nWhat they accomplished today:\n" + "\n".join(
            f"- DONE: {t.get('title', '')}" for t in completed_tasks[:10]
        )

    commits_summary = ""
    if recent_commits:
        commits_summary = "\n\nTheir GitHub activity today:\n" + "\n".join(
            f"- {c.get('repo', '')}: {c.get('message', '')}" for c in recent_commits[:5]
        )

    notes_section = ""
    if mentor_notes:
        notes_section = f"\n\nIMPORTANT things they told you to remember (respect these, don't contradict them):\n{mentor_notes}"

    daily_prompt = f"""You're the founder's operator advisor. This is the ONE message you send him today. Make it count.

His tasks today:
{task_summary}

Goals:
{goal_summary}
{completed_summary}{commits_summary}{notes_section}

Available hours today: {available_hours}h
Projects:
{project_summary}

Give him the single most important thing to do today and why, based on his actual tasks, code activity, and current stage. If he shipped real work recently, note it in one line. If he's been slacking on the one thing that matters at this stage, say so plainly. Match the distribution advice to his stage. Do not push launches or outreach the stage says is off-limits.

3-5 sentences. Return ONLY the message text, nothing else."""

    # All message types now route to the single daily brief (one message a day).
    prompts = {
        "daily": daily_prompt,
        "morning": daily_prompt,
        "midday": daily_prompt,
        "afternoon": daily_prompt,
        "evening": daily_prompt,
    }

    grounding = context_block.strip() if context_block else ""
    prompt = grounding + "\n\n" + STYLE_RULES + "\n\n" + prompts.get(message_type, daily_prompt)

    try:
        result = _call_claude(prompt, FAST_MODEL)
        # Aggressively clean the response
        msg = result.strip()
        # Remove "json" prefix that Claude sometimes adds
        if msg.lower().startswith("json"):
            msg = msg[4:].strip()
        # Remove markdown code fences
        if msg.startswith("```"):
            lines = msg.splitlines()
            msg = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:]).strip()
        # If Claude returned JSON, extract the message field
        if msg.startswith("{"):
            try:
                import json
                parsed = json.loads(msg)
                msg = parsed.get("message") or parsed.get("text") or parsed.get("body") or msg
            except (json.JSONDecodeError, TypeError):
                pass
        # Strip all quote types
        msg = msg.strip().strip('"').strip("'").strip("`").strip()
        # Remove leading/trailing quotes that might remain
        if msg.startswith('"') and msg.endswith('"'):
            msg = msg[1:-1]
        # Catch auth errors leaking into messages
        if "authenticate" in msg.lower() or "401" in msg or "API Error" in msg:
            raise RuntimeError("Auth error in response")
        # Strip em dashes — Claude keeps using them despite instructions
        msg = msg.replace(" — ", ". ").replace("—", ". ")
        # Truncate
        if len(msg) > 500:
            msg = msg[:497] + "..."
        return msg
    except Exception as e:
        # Fallback if Claude fails. Blunt, stage-safe, no hype.
        return "Couldn't reach the AI. Default for today: pick the one pipeline task that's blocking everything else and finish it before touching anything else."
