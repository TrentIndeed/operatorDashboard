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
def _get_marketing_context():
    from datetime import date
    plan_start = date(2026, 4, 8)
    days_since = (date.today() - plan_start).days
    week = min(4, max(1, (days_since // 7) + 1))

    week_focus = {
        1: "WEEK 1: Fix core pipeline + start outreach. PRODUCT IS PRIMARY (5-6h/day). Fix holes/chamfers on degraded meshes, build scan simulation script, add decimation, implement cut-extrude. Ship minimal waitlist page. Start cold outreach (10-15 DMs/day). Blog post #1. Do NOT suggest launches or heavy social media.",
        2: "WEEK 2: Multi-extrusion parts + grow conversations. Build L-brackets, motor mounts, enclosures on degraded meshes. Test on AI meshes and real scans. Record first demo videos (10-15 sec each). Continue 10-15 DMs/day, now with demo videos in DMs. Blog post #2. Do NOT suggest launches.",
        3: "WEEK 3: Beta testing + full landing page. Harden pipeline, give 10-15 beta testers access, collect testimonials. Build full landing page with demos and pricing (Free/Pro/$29mo/PAYG). Draft PH, HN, Reddit launch materials. Blog post #3. Start AI assistant MVP if time.",
        4: "WEEK 4: Launch. Product Hunt Tuesday 12:01 AM PT, Show HN 9 AM ET, Reddit launches, email waitlist, engage everywhere. Analyze: paying customers, conversion success rate, top acquisition channel.",
    }

    return f"""
CONTEXT: The founder is building ParameshAI, a mesh-to-parametric CAD tool for Onshape users.
They're in {week_focus.get(week, week_focus[1])}
Day {days_since + 1} of the 4-week plan.

Product state: plate sketch + extrude works, holes/chamfers close, multi-extrusion needed, cut-extrude needed, untested on real scans.
Competitor: Backflip AI ($30M funded, enterprise focus, still in closed beta). ParameshAI's edge: live product soon, self-serve, Onshape-native.
Daily time split: Product dev 5-6h (PRIMARY), Cold outreach 30 min (10-15 DMs), Blog writing 30 min, Social 10 min every other day.
Three numbers that matter: paying customers, conversion success rate on real uploads, top acquisition channel.
"""

STYLE_RULES = """
CRITICAL STYLE RULES:
- Text like a real gen z friend. Use slang naturally like "ngl", "lowkey", "fr", "no cap", "bet", "deadass", "W", "L" etc. Don't overdo it, just sprinkle it in.
- IMPORTANT: Do NOT start every message with "bro". Vary openings: "yo", "aye", "ngl", "ok so", "real talk", a question, or just jump into it.
- Short sentences. No em dashes. No semicolons. No ellipsis. Just periods and commas.
- NEVER use corporate words like "game-changer", "massive upside", "leverage", "compound", "needle-mover".
- Sound like a 22 year old texting their friend, not a motivational speaker.
- Give actual useful advice tied to the plan. Product work is PRIMARY in Weeks 1-2. Outreach is secondary but daily.
- Keep it 2-4 sentences. Not too short, not a paragraph.
- Only reference tasks and platforms they ACTUALLY have. Don't invent tasks.
- Be honest. If they didn't code or didn't do outreach, call it out. Product progress matters most.
- Reference the plan timeline. Weeks 1-2 = product + outreach. Week 3 = beta testing + landing page. Week 4 = launch.
"""


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

    prompts = {
        "morning": f"""You're texting your boy who's a solo founder. You're his growth advisor and close friend. It's 7am.

His tasks today:
{task_summary}

Goals:
{goal_summary}
{completed_summary}{commits_summary}{notes_section}

Available hours: {available_hours}h

Text him like you're his best friend who happens to be a killer business advisor. Keep it real, keep it short. Tell him what to do FIRST today. If he made commits or progress yesterday, acknowledge it. No corporate BS, no motivational poster energy. Talk like a real person texting their friend.

2-3 sentences max. Return ONLY the text message, nothing else.""",

        "midday": f"""You're texting your boy who's a solo founder. You're his growth advisor and close friend. It's noon.

His tasks today:
{task_summary}
{completed_summary}{commits_summary}{notes_section}

Completed so far: {completed_today}

Check in on him. Has he done the important stuff? If he made progress (completed tasks or pushed code), hype him up. If not, call it out — but like a friend, not a boss. Keep it real.

2-3 sentences max. Return ONLY the text message, nothing else.""",

        "afternoon": f"""You're texting your boy who's a solo founder. You're his growth advisor and close friend. It's 4pm.

His tasks today:
{task_summary}
{completed_summary}{commits_summary}{notes_section}

Completed so far: {completed_today}
Projects:
{project_summary}

The day's almost over. If he's been coding (check commits), acknowledge that but remind him about content/outreach. If he hasn't done anything, call it out. Be direct but supportive.

2-3 sentences max. Return ONLY the text message, nothing else.""",

        "evening": f"""You're texting your boy who's a solo founder. You're his growth advisor and close friend. It's 8pm.

His tasks today:
{task_summary}
{completed_summary}{commits_summary}{notes_section}

Completed today: {completed_today}
Total tasks: {len(tasks)}
Goals:
{goal_summary}

Wrap up the day with him. Be real about what happened — if he crushed it, hype him up. If he did nothing, don't sugarcoat it but don't be a dick either. Give him ONE thought to sleep on and ONE thing to attack tomorrow.

2-3 sentences max. Return ONLY the text message, nothing else.""",
    }

    prompt = _get_marketing_context() + "\n" + STYLE_RULES + "\n" + prompts.get(message_type, prompts["morning"])

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
        # Fallback messages if Claude fails
        fallbacks = {
            "morning": "Good morning! Time to crush it today. What's the #1 thing that moves the needle?",
            "midday": "Halfway through the day — have you done your outreach yet? Don't let it slip!",
            "afternoon": "Still time to film that content. The best time is NOW, not tomorrow.",
            "evening": "Day's wrapping up. What did you ship? What's the ONE thing for tomorrow?",
        }
        return fallbacks.get(message_type, "Stay focused on growth!")
