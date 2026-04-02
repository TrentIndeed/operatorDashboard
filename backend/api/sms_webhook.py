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

    # Command: tasks
    if lower in ("tasks", "status", "list"):
        tasks = db.query(Task).filter(Task.status == "pending").order_by(Task.priority_score.desc()).all()
        if not tasks:
            _send_telegram("No pending tasks. Hit AI Generate on the dashboard!", chat_id)
        else:
            lines = [f"{i+1}. {t.title} ({t.estimated_minutes}m)" for i, t in enumerate(tasks[:7])]
            _send_telegram("*Tasks:*\n" + "\n".join(lines), chat_id)
        return JSONResponse({"ok": True})

    # Anything else: conversational growth mentor reply
    try:
        from agents.reasoning import _call_claude, FAST_MODEL

        tasks = db.query(Task).filter(Task.status == "pending").order_by(Task.priority_score.desc()).all()
        goals = db.query(Goal).filter(Goal.status == "active").all()

        task_list = "\n".join(f"- {t.title}" for t in tasks[:5]) or "No tasks"
        goal_list = "\n".join(f"- {g.title} ({int(g.progress * 100)}%)" for g in goals[:3]) or "No goals"

        prompt = f"""You are a personal business growth mentor having a text conversation with a solo founder.

Their current tasks:
{task_list}

Their goals:
{goal_list}

They just texted you: "{text}"

Reply like a supportive but direct friend/coach. Keep it SHORT (2-3 sentences, under 280 chars).
Be specific to their actual tasks and goals — don't be generic.
If they're asking for advice, give ONE concrete action.
If they're venting, acknowledge then redirect to action.

Return ONLY the reply text."""

        reply = _call_claude(prompt, FAST_MODEL)
        reply = reply.strip().strip('"').strip("'").strip("`")
        if len(reply) > 500:
            reply = reply[:497] + "..."
        _send_telegram(reply, chat_id)
    except Exception:
        _send_telegram("Got it! Check the dashboard for your full task list.", chat_id)

    return JSONResponse({"ok": True})
