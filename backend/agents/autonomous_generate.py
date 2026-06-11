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

Your job: Generate ALL the data the dashboard needs for tomorrow — tasks, briefing items, market gaps, content drafts. Grounded ONLY in what you can actually verify.

## ABSOLUTELY CRITICAL — ANTI-HALLUCINATION RULES
This is the #1 rule. The founder will lose trust if you invent facts.

- Do NOT invent specific competitor news, funding rounds, beta status changes, product launches, feature releases, or pricing
- Do NOT say "Backflip just launched X" or "Onshape shipped Y" unless you have a working URL from a real search result that confirms it
- If a web search returns nothing reliable or specific, SKIP that briefing/gap item. An empty category is better than a made-up item.
- Only claim something if you can cite it. If you cite it, the URL MUST be from a real search result you ran, not guessed.

## Research rules
IF you do use web search:
- Only report facts from results that actually came back
- Include the real URL in the source_url field (never a fabricated one)
- If a search returned empty or irrelevant results, do not include that as a briefing/gap item
- It is BETTER to return fewer, verified items than many fabricated ones

IF you skip web search:
- Rely on the project state given to you
- Generate TASKS based purely on what's in the snapshot and the marketing plan
- For briefing/market_gaps, prefer empty arrays over hallucinated content

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

    hours = snapshot.get("available_hours_today", 2)
    today = snapshot.get("today", "today")
    schedule = snapshot.get("weekly_schedule", {})
    grounding = snapshot.get("context_block") or snapshot.get("stage_block", "")

    # Compact snapshot
    pending = snapshot.get("tasks", {}).get("pending", [])
    completed = snapshot.get("tasks", {}).get("completed_recently", [])
    goals = snapshot.get("goals", [])
    projects = snapshot.get("projects", [])
    commits = snapshot.get("github", {}).get("recent_commits", [])

    # Anti-repetition: what's already on the board. Don't regenerate these verbatim.
    prior_suggestions = [s.get("body", "") for s in snapshot.get("suggestions", [])]
    prior_briefing = [b.get("headline", "") for b in snapshot.get("briefing", [])]
    prior_task_titles = [t.get("title", "") for t in pending]
    already_lines = "\n".join(
        f"  - {x}" for x in (prior_task_titles[:8] + prior_suggestions[:5] + prior_briefing[:5]) if x
    ) or "  (nothing yet)"

    task_lines = "\n".join(f"  - {t['title']}" for t in pending[:5]) or "  None"
    done_lines = "\n".join(f"  - {t['title']}" for t in completed[:5]) or "  None"
    goal_lines = "\n".join(f"  - {g['title']} ({g['progress']}%)" for g in goals[:5]) or "  None"
    project_lines = "\n".join(
        f"  - {p['name']} (slug: {p.get('github_repo') or p['name'].lower().replace(' ', '-')}): {p.get('stage', 'unknown')}"
        for p in projects
    ) or "  None"
    commit_lines = "\n".join(f"  - {c['repo']}: {c['message']}" for c in commits[:5]) or "  None"

    # Calculate task budget (max — agent can return fewer if estimates are realistic)
    available_minutes = int(hours * 60)
    if hours == 0:
        task_count = 0
        task_instruction = "IMPORTANT: Today is a day off (0 hours). Generate an EMPTY tasks array []."
    elif hours <= 2:
        task_count = 3
        task_instruction = f"User has ~{available_minutes} min today. Likely 1 realistic product task (90-120 min) + 1 outreach task (30 min). USE REAL ESTIMATES, don't compress."
    elif hours <= 4:
        task_count = 5
        task_instruction = f"User has ~{available_minutes} min today. Likely 2-3 product tasks + outreach + content. USE REAL ESTIMATES."
    else:
        task_count = 7
        task_instruction = f"User has ~{available_minutes} min today. Full stack: 3-4 product tasks + outreach + content. USE REAL ESTIMATES, don't compress."

    prompt = f"""Generate dashboard data for {today}.

{grounding}

Daily split: product/pipeline work is the bulk of the day; cold outreach ~30 min ONLY in the form the stage allows; content is optional.

SCHEDULE: {hours}h available today. {task_instruction}
Task mix: mostly PRODUCT tasks (pipeline, testing, bugs). Add outreach/content ONLY if the current stage permits it (early stages keep outreach quiet and educational, no launches).
Priority scoring: 9-10 critical pipeline work, 7-8 important product work, 5-6 stage-appropriate outreach, 3-4 content, 1-2 admin.

DO NOT REPEAT what's already on the board. These were already generated — produce DIFFERENT, fresh, or advancing items, not reworded copies:
{already_lines}

CRITICAL — REALISTIC TIME ESTIMATES:
Product/pipeline tasks take LONGER than you'd think. Use these minimums:
- Bug fix in pipeline (chamfer detection, RANSAC tuning, plane fitting): 90-180 min
- New feature (cut-extrude, multi-extrusion, decimation, scan sim): 120-240 min
- Writing a test script: 60-120 min
- Running + debugging tests on new mesh set: 60-90 min
- Reverse engineering a failure case: 60-120 min
Marketing tasks:
- Cold outreach batch (10-15 DMs): 30 min
- Forum replies (2-3 answers): 30 min
- Blog writing (1000 words in one sitting): 60-90 min
- Waitlist page build: 60-90 min
- Record demo video: 15-30 min

NEVER estimate a coding/debugging task at 30 min. Minimum 60 min, typically 90-120.
If the user only has 2 hours, it's BETTER to give them 1 real task (120 min) + outreach (30 min)
than 4 underestimated tasks that won't finish.

CURRENT STATE:
Projects: {project_lines}
Existing tasks (these are often STALE and arbitrary, do not just rewrite them): {task_lines}
Recently completed: {done_lines}
Goals: {goal_lines}
Git activity: {commit_lines}

GROUND TRUTH (read carefully): the grounding block above separates RECENTLY COMPLETED work (commits, already DONE), IN PROGRESS files, recent Claude prompts, and OPEN PRIORITIES (unchecked items from the repo's own TODO/plan docs).
- Generate tasks from the OPEN PRIORITIES list and what's IN PROGRESS, NOT from the completed commits. A topic with many recent commits was just FINISHED, do not re-add it.
- The existing dashboard tasks are stale, replace them with what genuinely comes next per the open priorities.

REMINDER: Do NOT invent competitor news or feature releases. If you use web search, only report verified results with real URLs. Prefer empty arrays over hallucinated content.

OPTIONAL research (skip if you can't find reliable results):
- Web search for verifiable public posts in r/onshape or r/cad about mesh-to-parametric pain
- Web search for verifiable Onshape platform updates or new APIs
- Skip competitor research entirely unless you find a real, datable news article

GENERATE:
- tasks: {task_count} prioritized tasks for today that continue the founder's ACTUAL recent work (recent diffs + recent Claude prompts) and fit the current stage (or empty array if day off)
- suggestions: 3-5 growth suggestions tied to the founder's current situation (no need to be fancy — simple and actionable)
- briefing: 0-5 items, ONLY if you can verify them with real search results. Empty array is fine.
- market_gaps: 0-5 items, ONLY if you found real communities/posts. Include the actual URL in source_url. Empty array is fine.
- content_drafts: 2 drafts (1 short-form for TikTok/YouTube Shorts, 1 longer for LinkedIn/YouTube/blog) based on the founder's actual product and current stage

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
                    "--allowedTools", "WebSearch", "WebFetch", "Bash", "Read", "Glob", "Grep",
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
