"""
Telegram webhook handler — receives messages and responds.

Supports:
  - "done 1" / "done 2" — complete task by position
  - "add [task]" — create a new task
  - "tasks" — list pending tasks
  - Anything else — Claude generates a conversational growth mentor reply
"""
import os
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import httpx

from db.database import get_db, Task, Project, Goal

router = APIRouter(prefix="/sms", tags=["messaging"])

TG_API = "https://api.telegram.org/bot"


def _send_telegram(text: str, chat_id: str = ""):
    """Send a Telegram message."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return

    httpx.post(
        f"{TG_API}{token}/sendMessage",
        json={"chat_id": chat_id, "text": text[:4096], "parse_mode": "Markdown"},
        timeout=15,
    )


@router.post("/webhook")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle incoming Telegram messages."""
    data = await request.json()
    message = data.get("message", {})
    text = message.get("text", "").strip()
    chat_id = str(message.get("chat", {}).get("id", ""))

    if not text or not chat_id:
        return JSONResponse({"ok": True})

    lower = text.lower().strip()

    # Command: done N
    import re
    done_match = re.match(r"^done\s*(\d+)", lower)
    if done_match:
        num = int(done_match.group(1))
        tasks = db.query(Task).filter(Task.status == "pending").order_by(Task.priority_score.desc()).all()
        if num < 1 or num > len(tasks):
            _send_telegram(f"No task #{num}. You have {len(tasks)} tasks.", chat_id)
        else:
            task = tasks[num - 1]
            task.status = "done"
            db.commit()
            _send_telegram(f"Done: {task.title}", chat_id)
        return JSONResponse({"ok": True})

    # Command: add [task]
    add_match = re.match(r"^(?:add|focus)\s+(.+)", lower)
    if add_match:
        title = add_match.group(1).strip()
        new_task = Task(title=title, priority_score=7.0, status="pending", estimated_minutes=30)
        db.add(new_task)
        db.commit()
        _send_telegram(f"Added: {title}", chat_id)
        return JSONResponse({"ok": True})

    # Command: note [text] — persistent context for the mentor
    from db.database import User
    note_match = re.match(r"^(?:note|remember|update|context|status)[:\s]+(.+)", lower, re.IGNORECASE)
    if note_match:
        note_text = text[note_match.start(1):]  # Use original case
        user = db.query(User).first()
        if user:
            existing = user.mentor_notes or ""
            # Keep last 5 notes max
            notes = [n.strip() for n in existing.split("\n") if n.strip()]
            notes.append(note_text.strip())
            notes = notes[-5:]
            user.mentor_notes = "\n".join(notes)
            db.commit()
            _send_telegram(f"got it, i'll remember that", chat_id)
        return JSONResponse({"ok": True})

    # Command: clear notes
    if lower in ("clear notes", "forget", "reset notes"):
        user = db.query(User).first()
        if user:
            user.mentor_notes = ""
            db.commit()
            _send_telegram("cleared all notes, fresh start", chat_id)
        return JSONResponse({"ok": True})

    # Command: notes — show current notes
    if lower in ("notes", "my notes", "what do you remember"):
        user = db.query(User).first()
        notes = (user.mentor_notes or "").strip() if user else ""
        if notes:
            _send_telegram(f"here's what i remember:\n\n{notes}", chat_id)
        else:
            _send_telegram("no notes saved. text me 'note: [something]' and i'll remember it", chat_id)
        return JSONResponse({"ok": True})

    # Command: tasks
    if lower in ("tasks", "status", "list"):
        tasks = db.query(Task).filter(Task.status == "pending").order_by(Task.priority_score.desc()).all()
        if not tasks:
            _send_telegram("No pending tasks. Hit AI Generate on the dashboard!", chat_id)
        else:
            lines = [f"{i+1}. {t.title} ({t.estimated_minutes}m)" for i, t in enumerate(tasks[:7])]
            _send_telegram("*Tasks:*\n" + "\n".join(lines), chat_id)
        return JSONResponse({"ok": True})

    # Check if they're reporting progress (e.g. "I posted on reddit", "filmed a tiktok", "did outreach")
    try:
        from agents.reasoning import _call_claude, reason_json, FAST_MODEL

        tasks = db.query(Task).filter(Task.status == "pending").order_by(Task.priority_score.desc()).all()
        goals = db.query(Goal).filter(Goal.status == "active").all()

        task_list = "\n".join(f"- [{i+1}] {t.title}" for i, t in enumerate(tasks[:7])) or "No tasks"
        goal_list = "\n".join(f"- {g.title} ({int(g.progress * 100)}%)" for g in goals[:5]) or "No goals"

        # First: check if they're reporting they did something
        check_prompt = f"""The user texted: "{text}"

Their pending tasks:
{task_list}

Their goals:
{goal_list}

Is the user reporting that they completed or made progress on a task or goal?
Return JSON: {{"action": "complete_task", "task_number": N}} or {{"action": "update_goal", "goal_title": "...", "new_progress": 0.X}} or {{"action": "chat"}}
If they're just chatting or asking questions, return {{"action": "chat"}}."""

        try:
            action = reason_json(check_prompt)
            if isinstance(action, dict):
                if action.get("action") == "complete_task" and action.get("task_number"):
                    num = int(action["task_number"])
                    if 1 <= num <= len(tasks):
                        task = tasks[num - 1]
                        task.status = "done"
                        db.commit()
                        _send_telegram(f"nice, marked done: {task.title}", chat_id)
                        return JSONResponse({"ok": True})

                elif action.get("action") == "update_goal" and action.get("goal_title"):
                    for g in goals:
                        if action["goal_title"].lower() in g.title.lower():
                            g.progress = min(1.0, float(action.get("new_progress", g.progress + 0.1)))
                            db.commit()
                            _send_telegram(f"updated {g.title} to {int(g.progress * 100)}%", chat_id)
                            return JSONResponse({"ok": True})
        except Exception:
            pass

        # Get completed tasks and recent commits for context
        from db.database import GithubRepo
        completed_tasks = db.query(Task).filter(Task.status == "done").all()
        completed_list = "\n".join(f"- DONE: {t.title}" for t in completed_tasks[:10]) if completed_tasks else "Nothing completed yet"

        repos = db.query(GithubRepo).all()
        commit_list = ""
        for r in repos:
            if r.last_commit_at and r.last_commit_message:
                try:
                    from datetime import datetime as dt
                    commit_time = r.last_commit_at if not isinstance(r.last_commit_at, str) else dt.fromisoformat(r.last_commit_at.replace("Z", "+00:00"))
                    if (dt.utcnow() - commit_time.replace(tzinfo=None)).total_seconds() < 86400:
                        commit_list += f"\n- {r.name}: {r.last_commit_message[:50]}"
                except:
                    pass

        # Get mentor notes for context
        user = db.query(User).first()
        mentor_notes = (user.mentor_notes or "").strip() if user else ""
        notes_section = f"\n\nIMPORTANT context they told you to remember:\n{mentor_notes}" if mentor_notes else ""

        # Regular conversation
        prompt = f"""You're texting your friend who's a solo founder. You're their growth advisor. You know what they've been working on.

Their pending tasks:
{task_list}

Their goals:
{goal_list}

What they accomplished today:
{completed_list}

Their code activity today:{commit_list or ' No commits today'}
{notes_section}

They texted: "{text}"

STYLE: Text like a gen z friend. Use slang naturally (ngl, lowkey, fr, bet). No em dashes. No corporate speak. Be real and give actual advice based on what they've actually done today. Reference their commits or completed tasks if relevant. 2-3 sentences.

Return ONLY the reply text."""

        reply = _call_claude(prompt, FAST_MODEL)
        reply = reply.strip().strip('"').strip("'").strip("`")
        # Remove json prefix
        if reply.lower().startswith("json"):
            reply = reply[4:].strip()
        if reply.startswith("{"):
            try:
                import json
                parsed = json.loads(reply)
                reply = parsed.get("message") or parsed.get("text") or reply
            except:
                pass
        reply = reply.strip().strip('"').strip("'")
        # Catch auth errors
        if "authenticate" in reply.lower() or "401" in reply or "API Error" in reply:
            raise RuntimeError("Auth error")
        if len(reply) > 500:
            reply = reply[:497] + "..."
        _send_telegram(reply, chat_id)
    except Exception:
        _send_telegram("yo im having a brain fart rn, try again in a bit or check the dashboard", chat_id)

    return JSONResponse({"ok": True})
