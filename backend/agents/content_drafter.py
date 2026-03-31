"""
Content Drafter Agent — generates hooks, drafts, remixes, and repurposed content.
Uses the Claude CLI gateway (same pattern as agents/reasoning.py).
"""
import json
import subprocess
import shutil
import os
from typing import Any

# Reuse the same CLI finder from reasoning
from agents.reasoning import CLAUDE_BIN

FAST_MODEL = "claude-sonnet-4-6"

CONTENT_SYSTEM_PROMPT = """You are a content strategist and copywriter for a solo founder's projects (details provided in context).

You create viral-optimized content designed to GROW the founder's business. Every piece should:
- Hook in the first 1-3 seconds (pattern interrupt or curiosity gap)
- Deliver real value (tutorial, insight, surprising result, build-in-public update)
- End with a CTA that drives BUSINESS results (waitlist signup, follow, DM, comment)
- Make viewers want to share, save, or tag someone

Content themes that grow a solo founder's business:
- Build in public: show progress, failures, metrics, behind-the-scenes
- Tutorials: teach something valuable related to your niche
- Hot takes: contrarian opinions about your industry
- Results/demos: show the product working, before/after transformations
- Day-in-the-life: solo founder lifestyle, tools, workflow
- Comparisons: your tool vs competitors, old way vs new way

Platform-specific rules:
- TikTok/Reels: Fast pace, pattern interrupt hooks, save-worthy tips, under 60 sec, trending sounds
- YouTube: Curiosity gap opener, longer value (8-15 min), subscribe + comment CTA, SEO title
- Twitter/X: Hot takes, contrarian angles, quote-tweet bait, threads with hooks
- Instagram: Clean visuals, carousel-friendly, educational saves, Reels
- LinkedIn: Professional insights, milestone posts, founder journey stories
- Blog: SEO headers, code snippets, 800-1500 words, email capture CTA

Always respond with valid JSON."""


def _call_claude(prompt: str, model: str = FAST_MODEL) -> str:
    """
    Call Claude via the CLI. Uses OAuth from your Claude Code login.
    Returns the raw response text.
    """
    print(f"[ContentDrafter] Calling CLI at: {CLAUDE_BIN} (prompt length: {len(prompt)})")

    # Write prompt to temp file to avoid Windows shell issues
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(prompt)
        prompt_file = f.name

    try:
        with open(prompt_file, 'r', encoding='utf-8') as pf:
            result = subprocess.run(
                [
                    CLAUDE_BIN,
                    "--model", model,
                    "--output-format", "json",
                    "--max-turns", "3",
                    "--append-system-prompt", CONTENT_SYSTEM_PROMPT,
                ],
                stdin=pf,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=180,
            )
    except FileNotFoundError:
        raise RuntimeError(
            f"Claude CLI not found at '{CLAUDE_BIN}'. "
            "Make sure 'claude' is installed globally: npm install -g @anthropic-ai/claude-code"
        )
    finally:
        try:
            os.unlink(prompt_file)
        except OSError:
            pass

    print(f"[ContentDrafter] Exit code: {result.returncode}")
    if result.stderr:
        print(f"[ContentDrafter] stderr (first 300): {result.stderr[:300]}")

    if result.returncode not in (0, 1):
        raise RuntimeError(
            f"Claude CLI failed (exit {result.returncode}): {result.stderr}"
        )

    stdout = result.stdout.strip()
    if not stdout:
        raise RuntimeError("Claude CLI returned empty output")

    # --output-format json wraps in {"result": "..."} — extract the inner result
    try:
        data = json.loads(stdout)
        if isinstance(data, dict) and "result" in data:
            return data["result"]
        return stdout
    except json.JSONDecodeError:
        return stdout


def _parse_json(raw: str) -> Any:
    """Parse JSON from Claude response, handling markdown fences and mixed content."""
    from agents.reasoning import _extract_json
    return _extract_json(raw)


def generate_hooks(topic: str, platform: str = "tiktok", project_tag: str = "ai-automation") -> list[dict]:
    """Generate 3 hook variations with scores, full scripts, and CTAs."""
    prompt = f"""Generate 3 viral hook variations for a {platform} post about: {topic}

Project context: {project_tag}

Return JSON in this exact format:
{{
  "variations": [
    {{
      "hook": "The opening hook line",
      "score": 8.5,
      "full_script": "The complete script including hook, body, and CTA",
      "cta": "The call-to-action"
    }}
  ]
}}

Score each hook 0-10 based on predicted virality (pattern interrupt strength, curiosity gap, shareability).
"""
    raw = _call_claude(prompt)
    data = _parse_json(raw)
    return data.get("variations", [])


def generate_draft(topic: str, platform: str = "tiktok", content_type: str = "script", project_tag: str = "ai-automation") -> dict:
    """Generate a full content draft for a given topic and platform."""
    prompt = f"""Generate a complete {content_type} for {platform} about: {topic}

Project context: {project_tag}

Return JSON in this exact format:
{{
  "title": "Compelling title for the content",
  "body": "The full content body with [Hook], [Body], and [CTA] sections",
  "hook": "The opening hook line extracted",
  "cta": "The call-to-action extracted",
  "hashtags": "comma,separated,hashtags",
  "hook_score": 8.0,
  "suggested_post_time": "2026-03-29T10:00"
}}

Make the hook a pattern interrupt or curiosity gap. The body should deliver real value. The CTA should drive engagement.
"""
    raw = _call_claude(prompt)
    return _parse_json(raw)


def remix_content(original_body: str, feedback: str, platform: str = "tiktok") -> dict:
    """Remix existing content with user feedback to create a new version."""
    prompt = f"""Remix the following {platform} content based on user feedback.

ORIGINAL CONTENT:
{original_body}

USER FEEDBACK:
{feedback}

Create an improved version incorporating the feedback. Return JSON in this exact format:
{{
  "title": "New title for the remixed content",
  "body": "The full remixed content body",
  "hook": "The new opening hook",
  "cta": "The new call-to-action",
  "hashtags": "comma,separated,hashtags",
  "hook_score": 8.0
}}
"""
    raw = _call_claude(prompt)
    return _parse_json(raw)


def repurpose_content(original_body: str, original_platform: str, target_platform: str) -> dict:
    """Repurpose content from one platform to another."""
    prompt = f"""Repurpose the following {original_platform} content for {target_platform}.

ORIGINAL CONTENT ({original_platform}):
{original_body}

Adapt the content for {target_platform}'s format, tone, and best practices. Return JSON in this exact format:
{{
  "title": "Title optimized for {target_platform}",
  "body": "The full repurposed content body",
  "hook": "The opening hook adapted for {target_platform}",
  "cta": "CTA appropriate for {target_platform}",
  "hashtags": "comma,separated,hashtags",
  "hook_score": 8.0
}}
"""
    raw = _call_claude(prompt)
    return _parse_json(raw)
