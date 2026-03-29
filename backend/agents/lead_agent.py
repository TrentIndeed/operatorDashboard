"""
Lead management agent — generates DMs, replies, and classifies leads.
"""
import json
from agents.reasoning import _call_claude, FAST_MODEL


def generate_dm_draft(lead) -> str:
    """Generate a personalized DM draft for a lead."""
    prompt = f"""Write a short, friendly, non-spammy DM to this person who showed interest in your projects or content.

Lead info:
- Username: {lead.username}
- Platform: {lead.platform}
- Their message/comment: {lead.message or 'N/A'}
- Sentiment: {lead.sentiment or 'unknown'}
- Category: {lead.category}

Guidelines:
- Keep it under 280 characters if Twitter, otherwise under 500 characters
- Be genuine, not salesy
- Reference their specific comment/interest
- Include a soft CTA (waitlist, follow, or check out content)
- Match the platform's tone (casual on TikTok, professional on LinkedIn)

Return ONLY the DM text, no quotes or extra formatting."""

    return _call_claude(prompt, FAST_MODEL)


def generate_comment_reply(comment: str, platform: str) -> str:
    """Generate a reply to a comment."""
    prompt = f"""Write a reply to this {platform} comment. Be helpful, authentic, and subtly promote your projects or content where relevant.

Comment: "{comment}"

Guidelines:
- Keep it concise (1-3 sentences)
- Be helpful first, promotional second
- Match the platform tone
- If they ask a technical question, answer it genuinely
- Only mention your product if directly relevant

Return ONLY the reply text, no quotes or extra formatting."""

    return _call_claude(prompt, FAST_MODEL)


def detect_leads_from_comments(comments: list[dict]) -> list[dict]:
    """Classify a batch of comments into potential leads.

    Each comment dict should have: username, platform, message, source_url.
    Returns list of dicts with added fields: sentiment, category, suggested_action.
    """
    prompt = f"""Classify these comments into leads. For each, determine:
- sentiment: positive | neutral | negative
- category: hot (ready to buy/sign up) | warm (interested) | curious (just asking)
- suggested_action: brief action to take

Comments:
{json.dumps(comments, indent=2)}

Return a JSON array with each original comment plus the three new fields.
Return ONLY the JSON array."""

    raw = _call_claude(prompt, FAST_MODEL)

    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1])

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback: return originals with defaults
        for c in comments:
            c.setdefault("sentiment", "neutral")
            c.setdefault("category", "curious")
            c.setdefault("suggested_action", "Review manually")
        return comments
