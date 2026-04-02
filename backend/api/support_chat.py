"""AI support chatbot for Operator Dashboard.

Uses Claude CLI for responses with context about the dashboard features.
Falls back to FAQ answers if CLI unavailable.
"""

import json
import logging
import shutil
import subprocess
import os

from fastapi import APIRouter

router = APIRouter(prefix="/support", tags=["support"])
logger = logging.getLogger(__name__)


def _find_claude():
    found = shutil.which("claude")
    if found:
        return found
    appdata = os.environ.get("APPDATA", "")
    for ext in (".cmd", ".exe", ""):
        p = os.path.join(appdata, "npm", f"claude{ext}")
        if os.path.isfile(p):
            return p
    return "claude"


CLAUDE = _find_claude()


@router.post("/chat")
def support_chat(body: dict):
    message = body.get("message", "").strip()
    if not message:
        return {"reply": "Please type a question."}

    # Try Claude CLI
    try:
        result = subprocess.run(
            [CLAUDE, "--model", "claude-sonnet-4-6", "--output-format", "json", "--max-turns", "1"],
            input=f"""You are the support assistant for Operator Dashboard (dragonoperator.com),
an AI-powered solo founder command center.

Key features:
- Task prioritization with AI scoring
- Project management with GitHub sync
- Content drafting for social media
- Market intelligence and competitor analysis
- AI-generated daily briefings
- Weekly availability scheduling
- SaaS billing (Starter $9/mo, Pro $29/mo)

Be concise (2-3 sentences). Be helpful.

User question: {message}""",
            capture_output=True, text=True, timeout=30,
        )
        text = result.stdout.strip()
        try:
            data = json.loads(text)
            if "result" in data:
                return {"reply": data["result"]}
        except (json.JSONDecodeError, KeyError):
            pass
        if text:
            return {"reply": text}
    except Exception as e:
        logger.warning("Claude CLI failed: %s", e)

    # Fallback FAQ
    msg_lower = message.lower()
    if "price" in msg_lower or "cost" in msg_lower or "plan" in msg_lower:
        return {"reply": "Operator Dashboard has three plans: Local (free, self-hosted), Starter ($9/mo, shared VPS), and Pro ($29/mo, dedicated VPS with unlimited projects)."}
    elif "task" in msg_lower or "priority" in msg_lower:
        return {"reply": "The AI prioritizes your tasks based on project deadlines, estimated effort, and your weekly availability. Click 'Generate' to get fresh AI-scored tasks."}
    elif "github" in msg_lower:
        return {"reply": "Connect your GitHub by setting GITHUB_TOKEN and GITHUB_OWNER in your .env file. The dashboard syncs commits and updates project stages automatically."}
    else:
        return {"reply": "I can help with tasks, projects, content, billing, and GitHub integration. What would you like to know?"}
