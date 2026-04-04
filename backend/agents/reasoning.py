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

The founder is building ParameshAI — a mesh-to-parametric CAD tool for Onshape users. It converts STL/OBJ mesh files into editable parametric CAD. The ICP is solo mechanical engineers, product designers, and hardware makers who use Onshape.

Key competitor: Backflip AI ($30M funded, enterprise-first, scan-to-CAD). ParameshAI's gap: Onshape-native, self-serve, accessible pricing for solo engineers and small teams.

The founder is executing a 4-week marketing plan:
- Week 1: Foundation — landing page, 3 demo videos, 2 blog posts, daily LinkedIn/X posts
- Week 2: Community seeding — daily engagement in r/onshape, r/cad, r/3Dprinting, Onshape forums. DM 5-10 people/day. 2 short-form videos/week.
- Week 3: Launch prep — early access users, testimonials, Product Hunt + HN prep
- Week 4: Launch — Product Hunt, Show HN, Reddit launches, amplification

Key principles:
- DISTRIBUTION > DEVELOPMENT: the product is being built. The bottleneck is getting it in front of people.
- Daily outreach is mandatory: 30 min/day in communities, 20 min/day DMs
- Content must be product-led: screen recordings, before/after demos, workflow comparisons — not generic marketing
- LinkedIn is the #1 channel (engineers live there). X/Twitter #2. YouTube Shorts #3.
- Community seeding (Reddit, Onshape forums) = be helpful first, mention tool only when directly relevant
- Every content piece should either demonstrate the product, build founder credibility, or both

Growth channels ranked by priority:
1. LinkedIn (founder-led, daily posts — problem awareness, build journey, demos)
2. Onshape Forum + Reddit (r/onshape, r/cad, r/3Dprinting, r/SolidWorks — answer questions, be helpful)
3. YouTube Shorts / TikTok (15-30 sec mesh-to-parametric demos, before/after)
4. X/Twitter (technical threads, build-in-public, hot takes on CAD industry)
5. Product Hunt / HN (launch events in Week 4)
6. SEO blog posts (technical, optimized for AI search/GEO)
7. Direct outreach (DM people posting about mesh problems)
8. Email nurture (waitlist updates, early access invites)

Always respond with valid JSON unless explicitly told otherwise.
"""


# --- Rate limiting and token protection ---
import time
import threading

_call_lock = threading.Lock()
_call_timestamps: list[float] = []

# Limits
MAX_CALLS_PER_HOUR = int(os.getenv("AI_MAX_CALLS_PER_HOUR", "30"))
MAX_PROMPT_CHARS = int(os.getenv("AI_MAX_PROMPT_CHARS", "8000"))
MAX_CONTEXT_CHARS = int(os.getenv("AI_MAX_CONTEXT_CHARS", "12000"))

# Prompt injection patterns to strip
_INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore all instructions",
    "disregard the above",
    "forget your instructions",
    "you are now",
    "new system prompt",
    "override system",
    "act as",
    "pretend you are",
    "jailbreak",
    "do anything now",
    "developer mode",
]


def _sanitize_prompt(prompt: str) -> str:
    """Strip known prompt injection patterns and enforce length limits."""
    # Truncate to max length
    if len(prompt) > MAX_PROMPT_CHARS:
        prompt = prompt[:MAX_PROMPT_CHARS] + "\n[TRUNCATED — prompt too long]"

    # Strip injection attempts (case-insensitive)
    lower = prompt.lower()
    for pattern in _INJECTION_PATTERNS:
        if pattern in lower:
            prompt = prompt.replace(pattern, "[FILTERED]")
            prompt = prompt.replace(pattern.title(), "[FILTERED]")
            prompt = prompt.replace(pattern.upper(), "[FILTERED]")
            print(f"[Security] Stripped injection pattern: '{pattern}'")

    return prompt


def _check_rate_limit():
    """Enforce hourly call limit. Raises RuntimeError if exceeded."""
    with _call_lock:
        now = time.time()
        cutoff = now - 3600  # 1 hour window
        _call_timestamps[:] = [t for t in _call_timestamps if t > cutoff]
        if len(_call_timestamps) >= MAX_CALLS_PER_HOUR:
            raise RuntimeError(
                f"Rate limit exceeded: {len(_call_timestamps)}/{MAX_CALLS_PER_HOUR} calls in the last hour. "
                "Wait before making more AI calls."
            )
        _call_timestamps.append(now)


def _call_claude(prompt: str, model: str = FAST_MODEL) -> str:
    """
    Call Claude via the CLI. Uses OAuth from your Claude Code login.
    Returns the raw response text.

    Protections:
    - Prompt injection patterns stripped
    - Prompt length capped at MAX_PROMPT_CHARS
    - Rate limited to MAX_CALLS_PER_HOUR
    - Subprocess timeout at 180s
    """
    # Sanitize and rate limit
    prompt = _sanitize_prompt(prompt)
    _check_rate_limit()

    print(f"[Claude] Calling CLI at: {CLAUDE_BIN} (prompt length: {len(prompt)}, calls this hour: {len(_call_timestamps)})")

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
    Context is truncated to MAX_CONTEXT_CHARS to prevent token abuse.
    """
    if context:
        ctx_str = json.dumps(context, indent=2, default=str)
        if len(ctx_str) > MAX_CONTEXT_CHARS:
            ctx_str = ctx_str[:MAX_CONTEXT_CHARS] + "\n... [CONTEXT TRUNCATED]"
        full = f"Context:\n{ctx_str}\n\n{prompt}"
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
