"""
Core Claude reasoning engine.
Routes all AI calls through the Claude Code CLI, which handles OAuth
authentication via your Claude Max subscription. No API key needed.
"""
import os
import json
import subprocess
import shutil
import sys
from typing import Any

# Find claude CLI — check multiple common locations on Windows
def _find_claude_bin() -> str:
    # 1. Check PATH
    found = shutil.which("claude")
    if found:
        return found
    # 2. Windows APPDATA npm global install
    appdata = os.environ.get("APPDATA", "")
    for ext in (".cmd", ".exe", ""):
        candidate = os.path.join(appdata, "npm", f"claude{ext}")
        if os.path.isfile(candidate):
            return candidate
    # 3. Try npm prefix
    try:
        npm_prefix = subprocess.check_output(
            ["npm", "prefix", "-g"], text=True, timeout=5, stderr=subprocess.DEVNULL
        ).strip()
        for ext in (".cmd", ".exe", ""):
            candidate = os.path.join(npm_prefix, f"claude{ext}")
            if os.path.isfile(candidate):
                return candidate
    except Exception:
        pass
    # 4. Fallback
    return "claude"

CLAUDE_BIN = _find_claude_bin()

FAST_MODEL = "claude-sonnet-4-6"
DEEP_MODEL = "claude-opus-4-6"

SYSTEM_PROMPT = """You are the AI growth engine for a solo founder's operator dashboard.

The founder's projects are provided in the context. Your PRIMARY job is to help them GROW their business — get clients, build audience, generate revenue. Product development is secondary to distribution.

Key principles:
- GROWTH FIRST: every task should move the needle on clients, audience, or revenue
- Distribution > Development: a mediocre product with great distribution beats a great product nobody knows about
- Daily outreach is mandatory: the founder should be engaging on social media, forums, Discord, Reddit, HN every single day
- Content is the growth engine: short-form video (TikTok/Reels), YouTube, Twitter threads, blog posts
- Networking compounds: reply to comments, DM potential collaborators, engage in communities
- Revenue before perfection: ship, sell, iterate — don't over-engineer

Growth channels to prioritize:
1. Social media content (TikTok, YouTube, Twitter, Instagram, LinkedIn)
2. Community engagement (Reddit, Discord, HN, IndieHackers, forums)
3. Direct outreach (DMs, cold emails, comment replies)
4. SEO and content marketing (blog posts, tutorials)
5. Partnerships and collaborations
6. Product-led growth (waitlist, free tools, open source)

Always respond with valid JSON unless explicitly told otherwise.
"""


def _call_claude(prompt: str, model: str = FAST_MODEL) -> str:
    """
    Call Claude via the CLI. Uses OAuth from your Claude Code login.
    Returns the raw response text.
    """
    print(f"[Claude] Calling CLI at: {CLAUDE_BIN} (prompt length: {len(prompt)})")

    # Write prompt to a temp file to avoid Windows command-line length/encoding issues
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(prompt)
        prompt_file = f.name

    try:
        # Use stdin to pass the prompt — avoids shell escaping issues with -p
        with open(prompt_file, 'r', encoding='utf-8') as pf:
            result = subprocess.run(
                [
                    CLAUDE_BIN,
                    "--model", model,
                    "--output-format", "json",
                    "--max-turns", "3",
                    "--append-system-prompt", SYSTEM_PROMPT,
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

    print(f"[Claude] Exit code: {result.returncode}")
    if result.stderr:
        print(f"[Claude] stderr (first 300): {result.stderr[:300]}")

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
        if isinstance(data, dict):
            if "result" in data and data["result"]:
                return data["result"]
            # CLI returned metadata envelope but no result (tool_use hit max-turns)
            if data.get("subtype") == "error_max_turns" or data.get("stop_reason") == "tool_use":
                raise RuntimeError(
                    f"Claude used a tool and hit max-turns limit. "
                    f"stop_reason={data.get('stop_reason')}, subtype={data.get('subtype')}"
                )
            return stdout
        return stdout
    except json.JSONDecodeError:
        return stdout


def reason(
    prompt: str,
    context: dict[str, Any] = None,
    model: str = FAST_MODEL,
    max_tokens: int = 2048,
) -> str:
    """
    Core reasoning call. Returns raw text from Claude.
    """
    if context:
        full = f"Context:\n{json.dumps(context, indent=2, default=str)}\n\n{prompt}"
    else:
        full = prompt

    return _call_claude(full, model)


def _extract_json(raw: str) -> Any:
    """Extract JSON from Claude response, handling markdown fences and mixed content."""
    text = raw.strip()

    # 1. Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Strip markdown code fences (```json ... ``` or ``` ... ```)
    if "```" in text:
        import re
        # Find JSON inside code fences
        match = re.search(r'```(?:json)?\s*\n(.*?)\n```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass

    # 3. Find first [ or { and extract to matching ] or }
    for start_char, end_char in [('[', ']'), ('{', '}')]:
        start_idx = text.find(start_char)
        if start_idx >= 0:
            end_idx = text.rfind(end_char)
            if end_idx > start_idx:
                candidate = text[start_idx:end_idx + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    pass

    raise ValueError(f"Could not extract JSON from Claude response:\n{text[:500]}")


def reason_json(
    prompt: str,
    context: dict[str, Any] = None,
    model: str = FAST_MODEL,
    max_tokens: int = 2048,
) -> Any:
    """
    Reasoning call that parses and returns JSON.
    """
    raw = reason(prompt, context, model, max_tokens)
    return _extract_json(raw)
