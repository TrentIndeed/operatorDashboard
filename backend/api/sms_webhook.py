"""
SMS webhook handler — receives Twilio incoming messages and responds.

Supports:
  - "done 1" / "done 2" — complete task by position
  - "add [task]" — create a new task
  - "tasks" — list pending tasks
  - Anything else — Claude generates a conversational growth mentor reply
"""
import os
from fastapi import APIRouter, Request, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
import httpx

from db.database import get_db, Task, Project, Goal

router = APIRouter(prefix="/sms", tags=["sms"])


def _send_sms(body: str):
    """Send an SMS reply via Twilio."""
    sid = os.getenv("TWILIO_SID")
    token = os.getenv("TWILIO_TOKEN")
    to = os.getenv("TWILIO_TO")
    msid = os.getenv("TWILIO_MESSAGING_SID")
    if not all([sid, token, to, msid]):
        return

    httpx.post(
        f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
        data={"To": to, "MessagingServiceSid": msid, "Body": body[:1600]},
        auth=(sid, token),
        timeout=15,
    )


@router.post("/webhook")
async def sms_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle incoming SMS from Twilio."""
    form = await request.form()
    text = form.get("Body", "").strip()
    from_number = form.get("From", "")

    if not text:
        return PlainTextResponse("ok")

    lower = text.lower().strip()

    # Command: done N
    import re
    done_match = re.match(r"^done\s*(\d+)", lower)
    if done_match:
        num = int(done_match.group(1))
        tasks = db.query(Task).filter(Task.status == "pending").order_by(Task.priority_score.desc()).all()
        if num < 1 or num > len(tasks):
            _send_sms(f"No task #{num}. You have {len(tasks)} tasks.")
        else:
            task = tasks[num - 1]
            task.status = "done"
            db.commit()
            _send_sms(f"Done: {task.title}")
        return PlainTextResponse("ok")

    # Command: add [task]
    add_match = re.match(r"^(?:add|focus)\s+(.+)", lower)
    if add_match:
        title = add_match.group(1).strip()
        new_task = Task(title=title, priority_score=7.0, status="pending", estimated_minutes=30)
        db.add(new_task)
        db.commit()
        _send_sms(f"Added: {title}")
        return PlainTextResponse("ok")

    # Command: tasks
    if lower in ("tasks", "status", "list"):
        tasks = db.query(Task).filter(Task.status == "pending").order_by(Task.priority_score.desc()).all()
        if not tasks:
            _send_sms("No pending tasks. Hit AI Generate on the dashboard!")
        else:
            lines = [f"{i+1}. {t.title} ({t.estimated_minutes}m)" for i, t in enumerate(tasks[:7])]
            _send_sms("Tasks:\n" + "\n".join(lines))
        return PlainTextResponse("ok")

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
        reply = reply.strip().strip('"').strip("'")
        if len(reply) > 320:
            reply = reply[:317] + "..."
        _send_sms(reply)
    except Exception as e:
        _send_sms("Got it! Check the dashboard for your full task list.")

    return PlainTextResponse("ok")
