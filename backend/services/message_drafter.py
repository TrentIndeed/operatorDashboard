"""
Message Drafter — uses Claude to generate DM drafts, public replies,
account summaries, and demo video recommendations for leads.
"""
import json
from agents.reasoning import _call_claude, _extract_json, FAST_MODEL
from agents.stage import get_stage_standalone, stage_name, distribution_guidance, mentions_product_publicly


def draft_all_for_lead(lead_data: dict) -> dict:
    """
    Generate all drafts for a lead in a single Claude call.

    Args:
        lead_data: dict with keys: username, platform, post_text, post_url

    Returns:
        dict with keys: draft_dm, draft_public_reply, account_summary,
                        include_demo_video, tier, tier_reason
    """
    stage = get_stage_standalone()
    mention = mentions_product_publicly(stage)
    mention_tool = (
        "YES, mention ParameshAI naturally at the end if directly relevant"
        if mention else
        "NO, do NOT mention ParameshAI and do NOT link anything. Just be a genuinely helpful engineer."
    )

    prompt = f"""You are helping Trenton, a solo founder building ParameshAI (mesh-to-parametric CAD for Onshape).

Analyze this person's post and generate everything needed for outreach.

POST:
Platform: {lead_data.get('platform', 'unknown')}
Username: {lead_data.get('username', 'unknown')}
URL: {lead_data.get('post_url', '')}
Text: "{lead_data.get('post_text', '')}"

Current stage: {stage}/4 — {stage_name(stage)}
Distribution rule for this stage: {distribution_guidance(stage)}
Mention ParameshAI in public reply: {mention_tool}

Product capabilities: Converts STL/OBJ/PLY meshes to parametric Onshape parts with real feature trees. Works on prismatic parts: brackets, plates, mounts, enclosures, motor mounts with holes, chamfers, fillets. Does NOT handle organic shapes, freeform surfaces, or assemblies. Currently in development.

Generate a JSON object with these fields:

1. "draft_dm": A short DM to send this person (max 3 sentences for Reddit, 4-5 for LinkedIn/forum). Reference their specific post. Sound like an engineer, not a salesperson. No em dashes. No marketing words. End with a low-pressure ask like "would you want to try it?"

2. "draft_public_reply": A helpful public reply to their post. Actually answer their question first with useful technical advice. Follow the stage distribution rule above for whether to mention ParameshAI ({mention_tool}). Keep under 150 words for Reddit. No em dashes.

3. "account_summary": 3-5 bullet points about this person. What CAD software they use, industry, skill level, specific problem, hobbyist vs professional. Say "unclear" rather than guessing.

4. "include_demo_video": "yes" or "no" followed by one sentence explaining why. Say yes if they asked about a part type ParameshAI handles and expressed frustration.

5. "tier": 1, 2, or 3. Tier 1 = Onshape user asking about mesh conversion. Tier 2 = asking about mesh-to-CAD but not Onshape-specific. Tier 3 = adjacent topic.

6. "tier_reason": One sentence explaining the tier assignment.

Return ONLY the JSON object, nothing else."""

    try:
        raw = _call_claude(prompt, FAST_MODEL)
        result = _extract_json(raw)
        if not isinstance(result, dict):
            return {}
        return result
    except Exception as e:
        print(f"[Drafter] Failed to draft for {lead_data.get('username')}: {e}")
        return {}


def draft_follow_up(lead_data: dict, has_demos: bool = False) -> str:
    """Generate a follow-up message for a lead who hasn't responded."""
    stage = get_stage_standalone()
    demo_note = "Trenton now has demo videos to include." if has_demos and stage >= 2 else ""

    prompt = f"""Write a very short follow-up DM (1-2 sentences max) for someone who didn't reply to the first message.

Original context:
Platform: {lead_data.get('platform', 'unknown')}
Username: {lead_data.get('username', 'unknown')}
Their post was about: "{lead_data.get('post_text', '')[:200]}"
{demo_note}

Rules:
- Keep it to 1-2 sentences
- Be casual and low-pressure: "just bumping this in case it got buried"
- If demo videos are available, mention it naturally
- Don't be pushy or apologetic
- No em dashes

Return ONLY the message text."""

    try:
        raw = _call_claude(prompt, FAST_MODEL)
        msg = raw.strip().strip('"').strip("'")
        msg = msg.replace(" — ", ". ").replace("—", ". ")
        return msg
    except Exception as e:
        print(f"[Drafter] Follow-up draft failed: {e}")
        return "Hey, just bumping this in case it got buried. No worries if it's not relevant."
