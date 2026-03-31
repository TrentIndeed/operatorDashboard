"""
Market intelligence agent — scans for gaps and analyzes competitors.
"""
import json
from agents.reasoning import _call_claude, FAST_MODEL, CLAUDE_BIN


def scan_market_gaps(db):
    """Generate market gap insights via Claude, save to DB."""
    from db.database import MarketGap, Project

    # Build project context from DB so the scan is relevant to the user's actual projects
    projects = db.query(Project).all()
    project_lines = "\n".join(
        f"- {p.name}: {p.description or 'No description'}" for p in projects
    ) or "- No projects configured yet"

    prompt = f"""Find 5 GROWTH OPPORTUNITIES for a solo founder building these projects. Focus on places to find clients, build audience, and generate revenue — not just product gaps.

Projects:
{project_lines}

Look for:
- Communities (Reddit, Discord, forums) with active discussions the founder should join
- Content gaps (topics nobody is covering well on TikTok/YouTube in this niche)
- Outreach opportunities (people asking for solutions the founder builds)
- Competitor weaknesses (what they're bad at that the founder can exploit)
- Trending topics the founder can ride for visibility

For each opportunity, return:
{{
  "description": "Clear description of the growth opportunity",
  "source": "reddit | hackernews | twitter | discord | youtube | tiktok | forum | linkedin",
  "source_url": "",
  "opportunity_score": 0.0 to 1.0,
  "suggested_action": "Specific action to take TODAY (be precise — name the subreddit, Discord, or platform)",
  "category": "outreach | content | growth | market"
}}

Return ONLY a JSON array of 5 objects, no extra text."""

    raw = _call_claude(prompt, FAST_MODEL)

    try:
        from agents.reasoning import _extract_json
        gaps = _extract_json(raw)
    except (ValueError, json.JSONDecodeError) as e:
        print(f"[Market] Failed to parse market gaps: {e}")
        return

    # Ensure we got a list of dicts
    if not isinstance(gaps, list):
        print(f"[Market] Expected list, got {type(gaps).__name__}")
        return

    for g in gaps:
        if not isinstance(g, dict):
            continue
        gap = MarketGap(
            description=g.get("description", ""),
            source=g.get("source"),
            source_url=g.get("source_url"),
            opportunity_score=g.get("opportunity_score", 0.5),
            suggested_action=g.get("suggested_action"),
            category=g.get("category"),
            status="new",
        )
        db.add(gap)

    db.commit()


def analyze_competitor_post(post_data: dict) -> str:
    """Analyze a competitor's post and return insights."""
    prompt = f"""Analyze this competitor post and provide a brief strategic analysis (2-3 sentences).

Post data:
- Title: {post_data.get('title', 'N/A')}
- Platform: {post_data.get('platform', 'N/A')}
- Views: {post_data.get('views', 0)}
- Likes: {post_data.get('likes', 0)}
- Engagement: {post_data.get('engagement', 0)}

Focus on: what made it perform well/poorly, what we can learn, and how to differentiate.
Return plain text only, no JSON."""

    return _call_claude(prompt, FAST_MODEL)
