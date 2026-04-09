"""
Autonomous Generate-All Agent — replaces 5 separate one-shot Claude calls
with a single agentic run that can search the web and query the DB.

The old system:
  - 5 separate Claude calls, each blind (no web, no tools)
  - Briefing items were hallucinated (no real news)
  - Market gaps were generic (no actual community scanning)

The new system:
  - 1 autonomous agent with web search + DB access
  - Finds REAL competitor news, community discussions, trending topics
  - Generates tasks, suggestions, briefing, market gaps, and content drafts
  - All data grounded in actual research
"""
import os
import json
import subprocess
import tempfile
from datetime import datetime, date, timedelta

from agents.reasoning import _find_claude_bin, _check_rate_limit, _extract_json, FAST_MODEL

CLAUDE_BIN = _find_claude_bin()
AGENT_MAX_TURNS = 18  # More turns for the full generate-all pipeline


GENERATE_SYSTEM_PROMPT = """You are an autonomous AI agent that powers a solo founder's growth dashboard.

Your job: Research the founder's situation, then generate ALL the data the dashboard needs.

## Your tools
You can run bash commands, read files, and search the web. USE THEM.
Do NOT hallucinate news or market data — actually search for it.

## Required research (do these FIRST):
1. Web search "Backflip AI" or "mesh to CAD" for competitor news (last 7 days)
2. Web search "site:reddit.com onshape" or "mesh to parametric" for community discussions
3. Web search for CAD industry news or Onshape updates
4. Check the database for current tasks, goals, and content drafts

## How to query the database
```bash
python3 -c "
import sqlite3, json
db = sqlite3.connect('/app/data/operator.db')
db.row_factory = sqlite3.Row
rows = db.execute('YOUR QUERY').fetchall()
print(json.dumps([dict(r) for r in rows], indent=2))
"
```

## CRITICAL: Your final response must be ONLY a JSON object with this exact structure:

```json
{
  "tasks": [
    {
      "title": "Specific actionable task title",
      "why": "Why this matters for growth",
      "estimated_minutes": 30,
      "project_tag": "project-slug",
      "priority_score": 7.5
    }
  ],
  "suggestions": [
    {
      "body": "Specific growth suggestion naming platforms/communities",
      "category": "outreach | content | growth | market"
    }
  ],
  "briefing": [
    {
      "headline": "Short headline",
      "summary": "1-2 sentence summary",
      "category": "growth | competitor | platform | industry | content",
      "relevance_score": 0.8,
      "suggested_action": "Specific action to take today"
    }
  ],
  "market_gaps": [
    {
      "description": "Growth opportunity description",
      "source": "reddit | hackernews | twitter | linkedin | youtube | forum",
      "source_url": "actual URL if found",
      "opportunity_score": 0.7,
      "suggested_action": "Specific action to take",
      "category": "outreach | content | growth | market"
    }
  ],
  "content_drafts": [
    {
      "title": "Post/video title",
      "body": "Full draft content (script, post text, thread)",
      "platform": "tiktok | youtube | twitter | linkedin | blog",
      "content_type": "short-form | script | thread | post | blog_post",
      "hook": "Opening hook line",
      "cta": "Call to action",
      "hashtags": "comma,separated,hashtags",
      "hook_score": 7.5
    }
  ]
}
```

Return ONLY this JSON. No markdown fences, no explanation, just the JSON object.
"""


def run_autonomous_generate(snapshot: dict) -> dict:
    """
    Run the autonomous generate-all agent.

    Returns: {"data": dict, "success": bool, "error": str}
    The data dict contains tasks, suggestions, briefing, market_gaps, content_drafts.
    """
    _check_rate_limit()

    week = snapshot.get("marketing_plan_week", 1)
    day = snapshot.get("marketing_plan_day", 1)
    hours = snapshot.get("available_hours_today", 2)
    today = snapshot.get("today", "today")
    schedule = snapshot.get("weekly_schedule", {})

    week_focus = {
        1: "WEEK 1: Fix core pipeline + start outreach. PRODUCT PRIMARY (5-6h). Fix holes/chamfers on degraded meshes, scan sim script, decimation, cut-extrude for pockets. Ship waitlist page. 10-15 DMs/day. Blog #1. NO launches, no heavy social.",
        2: "WEEK 2: Multi-extrusion parts + grow conversations. L-brackets, motor mounts, enclosures on degraded meshes. AI mesh + real scan testing. Record demo videos. Continue DMs with videos attached. Blog #2. NO launches.",
        3: "WEEK 3: Beta testing + full landing page. Harden pipeline, 10-15 beta testers, collect testimonials. Full landing page with demos + pricing (Free/Pro $29mo/PAYG). Draft PH/HN/Reddit launch materials. Blog #3.",
        4: "WEEK 4: Launch. PH Tuesday 12:01 AM PT, Show HN 9 AM ET, Reddit launches, email waitlist, engage everywhere. Analyze: paying customers, conversion rate, top channel.",
    }

    # Compact snapshot
    pending = snapshot.get("tasks", {}).get("pending", [])
    completed = snapshot.get("tasks", {}).get("completed_recently", [])
    goals = snapshot.get("goals", [])
    projects = snapshot.get("projects", [])
    commits = snapshot.get("github", {}).get("recent_commits", [])

    task_lines = "\n".join(f"  - {t['title']}" for t in pending[:5]) or "  None"
    done_lines = "\n".join(f"  - {t['title']}" for t in completed[:5]) or "  None"
    goal_lines = "\n".join(f"  - {g['title']} ({g['progress']}%)" for g in goals[:5]) or "  None"
    project_lines = "\n".join(
        f"  - {p['name']} (slug: {p.get('github_repo') or p['name'].lower().replace(' ', '-')}): {p.get('stage', 'unknown')}"
        for p in projects
    ) or "  None"
    commit_lines = "\n".join(f"  - {c['repo']}: {c['message']}" for c in commits[:5]) or "  None"

    # Calculate task budget
    available_minutes = int(hours * 60)
    if hours == 0:
        task_count = 0
        task_instruction = "IMPORTANT: Today is a day off (0 hours). Generate an EMPTY tasks array []."
    elif hours <= 2:
        task_count = 3
        task_instruction = f"Generate {task_count} tasks totaling ~{available_minutes} minutes."
    elif hours <= 4:
        task_count = 5
        task_instruction = f"Generate {task_count} tasks totaling ~{available_minutes} minutes."
    else:
        task_count = 7
        task_instruction = f"Generate {task_count} tasks totaling ~{available_minutes} minutes."

    prompt = f"""Generate all dashboard data for {today}.

CONTEXT: Solo founder building ParameshAI (mesh-to-parametric CAD for Onshape).
Product state: plate+extrude works, holes/chamfers close, needs multi-extrusion and cut-extrude, untested on real scans.
Competitor: Backflip AI ($30M funded, enterprise focus, still closed beta, 2-4 months from public launch).
ParameshAI's edge: live product soon, self-serve pricing, Onshape-native, AI assistant for post-conversion editing.
{week_focus.get(week, week_focus[1])} (Day {day} of 28-day plan)
Daily split: Product dev 5-6h (PRIMARY), Cold outreach 30 min (10-15 DMs), Blog 30 min, Social 10 min every other day.

SCHEDULE: {hours}h available today. {task_instruction}
Task mix: 3-4 PRODUCT tasks (pipeline, testing, bugs), 1 OUTREACH task (DMs, forum), 0-1 CONTENT task (blog, video).
Priority scoring: 9-10 critical pipeline work or launch tasks, 7-8 important product work, 5-6 outreach, 3-4 content, 1-2 social/admin.

CURRENT STATE:
Projects: {project_lines}
Current tasks: {task_lines}
Recently completed: {done_lines}
Goals: {goal_lines}
Git activity: {commit_lines}

RESEARCH INSTRUCTIONS:
1. Search the web for "Backflip AI" news from the last 7 days
2. Search for trending discussions in r/onshape, r/cad, or about mesh-to-parametric workflows
3. Search for any Onshape platform updates or CAD industry news
4. Use what you find to make briefing items and market gaps REAL (with actual URLs and sources)

GENERATE:
- tasks: {task_count} prioritized tasks for today (or empty array if day off)
- suggestions: 5 growth suggestions (at least 3 about outreach/content, name specific platforms)
- briefing: 5 items (2 growth opportunities, 1 competitor, 1 platform change, 1 industry). Use REAL news from your research.
- market_gaps: 5 growth opportunities (communities to join, content gaps, outreach targets). Use REAL sources.
- content_drafts: 2 drafts (1 short-form for TikTok/YouTube Shorts, 1 longer for LinkedIn/YouTube/blog)

Your final response must be ONLY the JSON object. No markdown, no explanation."""

    print(f"[GenerateAll] Starting autonomous generation (max-turns: {AGENT_MAX_TURNS})")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(prompt)
        prompt_file = f.name

    try:
        with open(prompt_file, 'r', encoding='utf-8') as pf:
            result = subprocess.run(
                [
                    CLAUDE_BIN,
                    "--model", FAST_MODEL,
                    "--output-format", "json",
                    "--max-turns", str(AGENT_MAX_TURNS),
                    "--append-system-prompt", GENERATE_SYSTEM_PROMPT,
                ],
                stdin=pf,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=420,  # 7 min timeout for full generation
            )
    except subprocess.TimeoutExpired:
        print("[GenerateAll] Timed out after 420s")
        return {"data": {}, "success": False, "error": "timeout"}
    except FileNotFoundError:
        return {"data": {}, "success": False, "error": "cli_not_found"}
    finally:
        try:
            os.unlink(prompt_file)
        except OSError:
            pass

    print(f"[GenerateAll] Exit code: {result.returncode}, turns used")
    if result.stderr:
        print(f"[GenerateAll] stderr: {result.stderr[:300]}")

    if result.returncode not in (0, 1):
        return {"data": {}, "success": False, "error": f"exit_{result.returncode}: {result.stderr[:200]}"}

    stdout = result.stdout.strip()
    if not stdout:
        return {"data": {}, "success": False, "error": "empty_output"}

    # Parse CLI JSON envelope
    inner = ""
    try:
        envelope = json.loads(stdout)
        if isinstance(envelope, dict):
            inner = envelope.get("result", "")
            turns = envelope.get("num_turns", "?")
            cost = envelope.get("total_cost_usd", 0)
            print(f"[GenerateAll] Turns: {turns}, Cost: ${cost:.4f}")
    except json.JSONDecodeError:
        inner = stdout

    if not inner:
        return {"data": {}, "success": False, "error": "no_result_in_envelope"}

    # Parse the structured data from Claude's response
    try:
        data = _extract_json(inner)
        if not isinstance(data, dict):
            return {"data": {}, "success": False, "error": f"expected_dict_got_{type(data).__name__}"}

        # Validate required keys exist
        for key in ["tasks", "suggestions", "briefing", "market_gaps", "content_drafts"]:
            if key not in data:
                data[key] = []

        task_count = len(data.get("tasks", []))
        sug_count = len(data.get("suggestions", []))
        brief_count = len(data.get("briefing", []))
        gap_count = len(data.get("market_gaps", []))
        draft_count = len(data.get("content_drafts", []))
        print(f"[GenerateAll] Generated: {task_count} tasks, {sug_count} suggestions, "
              f"{brief_count} briefing, {gap_count} gaps, {draft_count} drafts")

        return {"data": data, "success": True, "error": ""}

    except (ValueError, json.JSONDecodeError) as e:
        print(f"[GenerateAll] Failed to parse response: {e}")
        print(f"[GenerateAll] Raw (first 500): {inner[:500]}")
        return {"data": {}, "success": False, "error": f"parse_error: {e}"}
