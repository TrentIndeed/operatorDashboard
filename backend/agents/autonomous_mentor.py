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
from agents.voice import STYLE_RULES

CLAUDE_BIN = _find_claude_bin()

# Max turns for autonomous exploration (vs 3 for one-shot)
AGENT_MAX_TURNS = 12

AGENT_SYSTEM_PROMPT = """You are an operator advisor for a solo founder. You send one focused message based on their actual work, code, and current stage.

## ABSOLUTELY CRITICAL — DO NOT HALLUCINATE
This is the #1 rule. Violating it destroys trust.

- Do NOT invent facts about Backflip AI, Onshape features, competitors, funding rounds, product launches, beta status, or industry news.
- Do NOT say "I read that..." or "latest news says..." or "they just launched...". You are NOT a journalist.
- Do NOT mention specific competitor product features unless they are EXPLICITLY in the context given to you.
- If you don't know something for certain, do not mention it. Silence is better than a wrong fact.
- The founder knows his own industry. He will immediately notice if you make stuff up and stop trusting you.

## What you SHOULD reference
Only reference things in the context given to you:
- The founder's pending tasks and priority scores
- Completed tasks today/recently
- Their goals and progress
- GitHub commits and the codebase state in the snapshot
- The CURRENT STAGE (1-4) and what should be happening at that stage
- Their own mentor notes and recent chat history

## Stage discipline
- The stage in the context is the truth. Match your advice to it.
- Do NOT push launches, Show HN, Product Hunt, or outreach the stage marks off-limits. If the stage is early, product work comes first and distribution stays quiet/educational.

## Optional DB lookup
If you need deeper context, you CAN query the SQLite DB at /app/data/operator.db via Bash:
```bash
python3 -c "import sqlite3; db = sqlite3.connect('/app/data/operator.db'); rows = db.execute('SELECT title, priority_score FROM tasks WHERE status=\"pending\" LIMIT 5').fetchall(); print(rows)"
```
Tables: tasks, goals, projects, github_repos, content_drafts, codebase_snapshots, agent_memory, chat_messages.

DO NOT use web search. DO NOT research competitors. Analyze THEIR data and give one tactical call.

## CRITICAL MESSAGE RULES
1. Your final response must be ONLY the Telegram message text. Nothing else.
""" + STYLE_RULES + """
- Reference the current stage and what should be happening now.
- NEVER mention Backflip, Onshape features, or industry news unless it's literally in the context given to you.
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
    hours = snapshot.get("available_hours_today", 2)
    today = snapshot.get("today", "today")
    grounding = snapshot.get("context_block") or snapshot.get("stage_block", "")
    stage_check = snapshot.get("stage_check", "")
    if stage_check:
        grounding = grounding + "\n\n" + stage_check

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

    prompt = f"""It's {today}. This is the founder's ONE check-in for today. He has {hours}h available.

{grounding}

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

Analyze what's ACTUALLY in this snapshot. Don't mention external facts, competitor news, or anything not listed above.

HOW TO READ THE SIGNALS (this is critical, get it right):
- "RECENTLY COMPLETED" commits are DONE work. A burst of commits about a topic means that topic was just FINISHED. NEVER call a recently-committed area the "open priority" or "highest-priority open item". That is the mistake to avoid.
- The OPEN PRIORITIES list (unchecked items from the repo's own TODO/plan docs) is the real source of what's NEXT. Lead with that.
- "IN PROGRESS" uncommitted files + the LAST recent prompt = what they're mid-stream on right now.
- The dashboard task list is stale and arbitrary. Ignore it when it conflicts with the above.

Focus on:
- The single most useful next move, drawn from the OPEN PRIORITIES list and what they're mid-stream on, given the current stage
- Acknowledge in one line what they just shipped (the recent commits) without calling it open work
- If the OPEN PRIORITIES list is empty and the code/prompts don't make the next step obvious, say what they're mid-stream on and ask what's next instead of inventing a priority

IMPORTANT about time estimates: pipeline/coding work takes longer than the task list shows.
A "chamfer fix" is really 90-120 min once you include debugging. A "cut-extrude feature" is 2-4h.
Don't tell the user they can stack 3 product tasks in 2h. Pick ONE realistic thing and finish it.

After your research, compose your one daily Telegram message.
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
                    "--allowedTools", "Bash", "Read", "Glob", "Grep",
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
