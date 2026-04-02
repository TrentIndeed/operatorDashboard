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

# Style rules prepended to every mentor prompt
STYLE_RULES = """
CRITICAL STYLE RULES:
- Write like a normal person texting. Short sentences. No em dashes (—). Use periods or just start a new sentence.
- NEVER use fancy punctuation like em dashes, semicolons, or ellipsis (...). Just use periods and commas.
- Don't say things no real person would text. No "game-changer", "massive upside", "leverage", "compound", etc.
- Sound like a 25 year old friend texting, not a LinkedIn post.
- Use "you" not "the founder". This is a 1-on-1 text.
- Keep it under 200 characters if possible. Nobody reads long texts.
- Only reference tasks and platforms the user ACTUALLY has. Don't make up tasks or suggest platforms they don't use.
"""


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
        "morning": f"""You're texting your boy who's a solo founder. You're his growth advisor and close friend. It's 7am.

His tasks today:
{task_summary}

Goals:
{goal_summary}

Available hours: {available_hours}h

Text him like you're his best friend who happens to be a killer business advisor. Keep it real, keep it short. Tell him what to do FIRST today. No corporate BS, no motivational poster energy. Talk like a real person texting their friend.

2-3 sentences max. Return ONLY the text message, nothing else.""",

        "midday": f"""You're texting your boy who's a solo founder. You're his growth advisor and close friend. It's noon.

His tasks today:
{task_summary}

Completed so far: {completed_today}

Check in on him. Has he done the important stuff? If not, call it out — but like a friend, not a boss. Maybe roast him a little if he's slacking. Keep it real.

2-3 sentences max. Return ONLY the text message, nothing else.""",

        "afternoon": f"""You're texting your boy who's a solo founder. You're his growth advisor and close friend. It's 4pm.

His tasks today:
{task_summary}

Completed so far: {completed_today}
Projects:
{project_summary}

The day's almost over. If he hasn't created content yet, tell him to do it NOW. If he hasn't done outreach, call it out. Be direct but supportive — like a friend who actually cares about his success.

2-3 sentences max. Return ONLY the text message, nothing else.""",

        "evening": f"""You're texting your boy who's a solo founder. You're his growth advisor and close friend. It's 8pm.

His tasks today:
{task_summary}

Completed today: {completed_today}
Total tasks: {len(tasks)}
Goals:
{goal_summary}

Wrap up the day with him. Be real about what happened — if he crushed it, hype him up. If he did nothing, don't sugarcoat it but don't be a dick either. Give him ONE thought to sleep on and ONE thing to attack tomorrow.

2-3 sentences max. Return ONLY the text message, nothing else.""",
    }

    prompt = STYLE_RULES + "\n" + prompts.get(message_type, prompts["morning"])

    try:
        result = _call_claude(prompt, FAST_MODEL)
        # Strip quotes, markdown, JSON wrappers, debug output
        msg = result.strip().strip('"').strip("'").strip("`")
        # Remove markdown code fences
        if msg.startswith("```"):
            lines = msg.splitlines()
            msg = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
        # If Claude returned JSON, extract the message field
        if msg.startswith("{"):
            try:
                import json
                parsed = json.loads(msg)
                msg = parsed.get("message") or parsed.get("text") or parsed.get("body") or msg
            except (json.JSONDecodeError, TypeError):
                pass
        # Strip any remaining quotes
        msg = msg.strip().strip('"').strip("'")
        # Truncate
        if len(msg) > 500:
            msg = msg[:497] + "..."
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
