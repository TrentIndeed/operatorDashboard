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


def generate_mentor_message(
    message_type: str,
    tasks: list[dict],
    goals: list[dict],
    projects: list[dict],
    completed_today: int = 0,
    available_hours: float = 2,
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

    prompts = {
        "morning": f"""You are a personal business growth mentor texting a solo founder at 7am.

Their tasks today:
{task_summary}

Goals:
{goal_summary}

Available hours: {available_hours}h

Write a SHORT motivational text message (2-4 sentences max) that:
- Calls out their #1 priority by name
- Gives a specific growth action to do FIRST (before anything else)
- Feels like a friend/coach, not a robot
- Uses casual tone, maybe an emoji or two
- Under 280 characters

Return ONLY the message text, no quotes or JSON.""",

        "midday": f"""You are a personal business growth mentor texting a solo founder at noon.

Their tasks today:
{task_summary}

Completed so far: {completed_today}
Available hours remaining: ~{max(0, available_hours - 4)}h

Write a SHORT check-in text (2-3 sentences) that:
- Asks about progress on their top task
- Reminds them about outreach/networking if they haven't done it
- Nudges them to post content if they haven't
- Feels encouraging, not nagging
- Under 280 characters

Return ONLY the message text, no quotes or JSON.""",

        "afternoon": f"""You are a personal business growth mentor texting a solo founder at 4pm.

Their tasks today:
{task_summary}

Completed so far: {completed_today}
Projects:
{project_summary}

Write a SHORT afternoon nudge (2-3 sentences) that:
- If they haven't filmed content today, remind them to do it NOW (best light)
- Mention a specific community/platform they should engage with before EOD
- Create urgency without stress
- Under 280 characters

Return ONLY the message text, no quotes or JSON.""",

        "evening": f"""You are a personal business growth mentor texting a solo founder at 8pm.

Their tasks today:
{task_summary}

Completed today: {completed_today}
Total tasks: {len(tasks)}
Goals:
{goal_summary}

Write a SHORT evening recap text (2-3 sentences) that:
- Acknowledge what they accomplished (or didn't — be honest but kind)
- Give ONE thing to think about before bed (a content idea, a connection to make)
- Preview tomorrow's priority
- Feels like a friend wrapping up the day
- Under 280 characters

Return ONLY the message text, no quotes or JSON.""",
    }

    prompt = prompts.get(message_type, prompts["morning"])

    try:
        result = _call_claude(prompt, FAST_MODEL)
        # Strip any quotes or markdown
        msg = result.strip().strip('"').strip("'").strip("`")
        # Truncate to SMS-friendly length
        if len(msg) > 320:
            msg = msg[:317] + "..."
        return msg
    except Exception as e:
        # Fallback messages if Claude fails
        fallbacks = {
            "morning": "Good morning! Time to crush it today. What's the #1 thing that moves the needle?",
            "midday": "Halfway through the day — have you done your outreach yet? Don't let it slip!",
            "afternoon": "Still time to film that content. The best time is NOW, not tomorrow.",
            "evening": "Day's wrapping up. What did you ship? What's the ONE thing for tomorrow?",
        }
        return fallbacks.get(message_type, "Stay focused on growth!")
