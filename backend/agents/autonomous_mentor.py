"""
Autonomous Growth Mentor — runs Claude Code CLI in full agentic mode.

Unlike the old mentor which got a pre-assembled prompt and returned text,
this agent can autonomously:
  - Search the web for competitor news, community discussions, trending topics
  - Query the database for deeper analysis
  - Check GitHub activity via API
  - Analyze patterns across multiple data sources
  - Then compose and return a personalized growth message

Uses Claude Code CLI with higher max-turns and tool access.
"""
import os
import json
import subprocess
import tempfile
import time
from datetime import datetime

from agents.reasoning import _find_claude_bin, _check_rate_limit, _is_auth_error, FAST_MODEL

CLAUDE_BIN = _find_claude_bin()

# Max turns for autonomous exploration (vs 3 for one-shot)
AGENT_MAX_TURNS = 12

AGENT_SYSTEM_PROMPT = """You are an autonomous growth advisor agent for a solo founder.

You have TOOLS available. Use them to gather real information before giving advice.
Do NOT guess or make up data — actually look it up.

## Your tools
You can run bash commands, read files, and search the web. Use them.

## How to get dashboard data
The founder's data is in a SQLite database. Query it directly:
```bash
python3 -c "
import sqlite3, json
db = sqlite3.connect('/app/data/operator.db')
db.row_factory = sqlite3.Row
# Example: get pending tasks
rows = db.execute('SELECT title, priority_score, estimated_minutes, project_tag FROM tasks WHERE status=\"pending\" ORDER BY priority_score DESC LIMIT 10').fetchall()
print(json.dumps([dict(r) for r in rows], indent=2))
"
```

Useful tables: tasks, goals, projects, github_repos, content_drafts, market_gaps,
leads, social_metrics, competitors, agent_memory, chat_messages

## How to check GitHub
```bash
curl -s -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/users/TrentIndeed/events?per_page=10"
```

## How to search the web
Use your web_search tool to find:
- Competitor activity (Backflip AI, Onshape updates)
- Trending discussions in r/onshape, r/cad, r/3Dprinting
- CAD industry news that creates content opportunities

## CRITICAL RULES
1. Your final response must be ONLY the Telegram message text. Nothing else.
2. Text like a gen Z friend — "ngl", "lowkey", "fr", "bet", "deadass", "W", "L"
3. Do NOT start every message with "bro". Vary: "yo", "aye", "ngl", "ok so", "real talk", a question
4. Short sentences. No em dashes. No semicolons. No ellipsis. Just periods and commas.
5. NEVER use corporate words: "game-changer", "leverage", "compound", "needle-mover"
6. Keep it 2-5 sentences. Be specific to what you actually found.
7. If you found something interesting (competitor news, trending thread, community opportunity), mention it specifically.
8. Be honest — if daily non-negotiables weren't met, call it out.
9. Reference the marketing plan week and what should be happening now.
"""


def _get_agent_memory(db_path: str = "/app/data/operator.db", limit: int = 5) -> str:
    """Get recent agent memories for continuity between runs."""
    try:
        import sqlite3
        db = sqlite3.connect(db_path)
        db.row_factory = sqlite3.Row
        rows = db.execute(
            "SELECT run_type, message_sent, findings, created_at FROM agent_memory "
            "ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        db.close()
        if not rows:
            return "No previous agent runs."
        lines = []
        for r in rows:
            lines.append(f"[{r['created_at']}] {r['run_type']}: {r['message_sent'][:150]}")
        return "\n".join(reversed(lines))
    except Exception:
        return "No previous agent runs (table may not exist yet)."


def run_autonomous_mentor(
    message_type: str,
    snapshot: dict,
    db_path: str = "/app/data/operator.db",
) -> dict:
    """
    Run the autonomous mentor agent.

    Returns: {"message": str, "findings": str, "tools_used": list, "success": bool}
    """
    _check_rate_limit()

    # Get memory from previous runs
    memory = _get_agent_memory(db_path)

    # Build the exploration prompt
    week = snapshot.get("marketing_plan_week", 1)
    day = snapshot.get("marketing_plan_day", 1)
    hours = snapshot.get("available_hours_today", 2)
    today = snapshot.get("today", "today")

    week_focus = {
        1: "WEEK 1: Fix core pipeline + start outreach. PRODUCT PRIMARY (5-6h). Fix holes/chamfers, scan sim, decimation, cut-extrude. Waitlist page. 10-15 DMs/day. Blog #1. No launches.",
        2: "WEEK 2: Multi-extrusion parts + grow conversations. L-brackets, motor mounts, enclosures on degraded meshes. Demo videos. Continue DMs with videos. Blog #2. No launches.",
        3: "WEEK 3: Beta testing + full landing page. Harden pipeline, 10-15 beta testers, testimonials. Full landing page + pricing. Draft launch materials. Blog #3.",
        4: "WEEK 4: Launch. PH Tuesday 12:01 AM PT, Show HN 9 AM ET, Reddit, email waitlist, engage everywhere.",
    }

    # Compact snapshot for the prompt (agent can query DB for more detail)
    pending = snapshot.get("tasks", {}).get("pending", [])
    completed = snapshot.get("tasks", {}).get("completed_recently", [])
    goals = snapshot.get("goals", [])
    commits = snapshot.get("github", {}).get("recent_commits", [])
    notes = snapshot.get("mentor_notes", "")
    chat = snapshot.get("chat_history", [])

    task_lines = "\n".join(f"  - {t['title']} ({t['minutes']}m, score {t['score']})" for t in pending[:8]) or "  None"
    done_lines = "\n".join(f"  - DONE: {t['title']}" for t in completed[:5]) or "  Nothing completed recently"
    goal_lines = "\n".join(f"  - {g['title']} ({g['progress']}%)" for g in goals[:5]) or "  No goals"
    commit_lines = "\n".join(f"  - {c['repo']}: {c['message']} ({c['hours_ago']}h ago)" for c in commits[:5]) or "  No recent commits"

    recent_chat = ""
    if chat:
        last_msgs = chat[-6:]
        recent_chat = "\n".join(f"  {m['role']}: {m['content'][:100]}" for m in last_msgs)

    notes_section = f"\nThings they told you to remember:\n{notes}" if notes else ""
    chat_section = f"\nRecent conversation:\n{recent_chat}" if recent_chat else ""

    prompt = f"""It's {today}, {message_type} check-in. The founder has {hours}h available today.

CONTEXT: Building ParameshAI (mesh-to-parametric CAD for Onshape). Competitor: Backflip AI ($30M funded, still closed beta).
Product state: plate+extrude works, holes/chamfers close, needs multi-extrusion and cut-extrude.
{week_focus.get(week, week_focus[1])} (Day {day} of 28-day plan)
Daily split: Product dev 5-6h (PRIMARY), Cold outreach 30 min (10-15 DMs), Blog 30 min, Social 10 min every other day.

CURRENT STATE (from database snapshot):
Pending tasks:
{task_lines}

Completed recently:
{done_lines}

Goals:
{goal_lines}

Git activity:
{commit_lines}
{notes_section}{chat_section}

YOUR PREVIOUS MESSAGES (don't repeat yourself):
{memory}

NOW: Use your tools to dig deeper. Suggestions:
- Search the web for "Backflip AI" or "mesh to CAD" to see what competitors are doing
- Check if there are trending posts in r/onshape or r/cad that the founder should engage with
- Look at the GitHub activity to understand what was actually shipped
- Query the database for content drafts, leads, or market gaps if relevant

After your research, compose a {message_type} Telegram message.
Your FINAL response must be ONLY the message text — nothing else. No JSON, no explanation."""

    print(f"[Agent] Starting autonomous {message_type} analysis (max-turns: {AGENT_MAX_TURNS})")

    # Write prompt to temp file
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
                    "--append-system-prompt", AGENT_SYSTEM_PROMPT,
                ],
                stdin=pf,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,  # 5 min timeout for agentic runs
            )
    except subprocess.TimeoutExpired:
        print("[Agent] Timed out after 300s")
        return {"message": "", "findings": "timeout", "tools_used": [], "success": False}
    except FileNotFoundError:
        print(f"[Agent] Claude CLI not found at {CLAUDE_BIN}")
        return {"message": "", "findings": "cli_not_found", "tools_used": [], "success": False}
    finally:
        try:
            os.unlink(prompt_file)
        except OSError:
            pass

    print(f"[Agent] Exit code: {result.returncode}")
    if result.stderr:
        print(f"[Agent] stderr (first 500): {result.stderr[:500]}")

    # Auth failure detection
    if result.returncode not in (0, 1):
        if _is_auth_error(result.stderr, result.stdout):
            print("[Agent] Auth failure detected")
            try:
                with open("data/claude-auth-status.txt", "w") as sf:
                    sf.write(f"EXPIRED {datetime.now()}")
            except OSError:
                pass
        return {"message": "", "findings": f"exit_{result.returncode}", "tools_used": [], "success": False}

    stdout = result.stdout.strip()
    if not stdout:
        return {"message": "", "findings": "empty_output", "tools_used": [], "success": False}

    # Parse the JSON envelope
    message = ""
    tools_used = []
    try:
        data = json.loads(stdout)
        if isinstance(data, dict):
            message = data.get("result", "")
            # Extract tool usage info if available
            usage = data.get("usage", {})
            if usage:
                tools_used.append(f"turns={data.get('num_turns', '?')}")
                tools_used.append(f"cost=${data.get('total_cost_usd', 0):.4f}")

            if data.get("subtype") == "error_max_turns":
                print("[Agent] Hit max turns — still extracting result")
                message = data.get("result", "")
    except json.JSONDecodeError:
        message = stdout

    if not message:
        return {"message": "", "findings": "no_result", "tools_used": tools_used, "success": False}

    # Clean the message
    msg = message.strip()
    # Remove JSON wrapper if Claude returned it
    if msg.startswith("{"):
        try:
            parsed = json.loads(msg)
            msg = parsed.get("message") or parsed.get("text") or parsed.get("body") or msg
        except (json.JSONDecodeError, TypeError):
            pass
    # Strip quotes and code fences
    msg = msg.strip().strip('"').strip("'").strip("`")
    if msg.startswith("```"):
        lines = msg.splitlines()
        msg = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:]).strip()
    if msg.lower().startswith("json"):
        msg = msg[4:].strip()
    # Strip em dashes
    msg = msg.replace(" — ", ". ").replace("—", ". ")
    # Catch auth errors leaking into messages (specific patterns only)
    msg_lower = msg.lower()
    if ("failed to authenticate" in msg_lower or "login required" in msg_lower
            or "token expired" in msg_lower or "session expired" in msg_lower):
        return {"message": "", "findings": "auth_error_in_response", "tools_used": tools_used, "success": False}
    # Truncate
    if len(msg) > 600:
        msg = msg[:597] + "..."

    print(f"[Agent] Generated message ({len(msg)} chars): {msg[:100]}...")
    return {
        "message": msg,
        "findings": f"tools={tools_used}",
        "tools_used": tools_used,
        "success": True,
    }
