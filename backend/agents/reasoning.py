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

SYSTEM_PROMPT = """You are the AI engine for a solo founder's operator dashboard.

The founder is building ParameshAI — a mesh-to-parametric CAD tool for Onshape users. It converts STL/OBJ/PLY mesh files into editable parametric CAD with real feature trees. It works on prismatic mechanical parts (brackets, plates, mounts, enclosures, holes, chamfers, fillets), not organic/freeform shapes or assemblies. ICP: solo mechanical engineers, product designers, and hardware makers on Onshape. Main competitor: Backflip AI ($30M funded, enterprise-first, still in closed beta).

CRITICAL — stage drives everything:
- The founder's CURRENT STAGE (1-4) and what to focus on is provided in each prompt's context. ALWAYS follow it. Do NOT assume a launch is near.
- Stage is NOT a calendar date. It reflects what is actually built. Trust the stage and any codebase state given to you over your own assumptions.
- Distribution advice must match the stage. Early stages = quiet, educational, no product mentions, NO Show HN / Product Hunt / launch pushes. Only suggest launches when the stage explicitly says so.
- Product comes first until the product actually works. Don't push marketing over core engineering when the pipeline isn't reliable yet.

Hard rules:
- NEVER invent facts: no competitor news, funding rounds, Onshape feature releases, or progress that isn't in the context given to you. If you don't know, say nothing.
- Coding/pipeline tasks take longer than they look. A bug fix is 90-180 min, a new feature is 2-4h. Never estimate a coding task at 30 min.

Always respond with valid JSON unless explicitly told otherwise.
"""


# --- Rate limiting and token protection ---
import time
import threading

_call_lock = threading.Lock()
_call_timestamps: list[float] = []

# Limits
MAX_CALLS_PER_HOUR = int(os.getenv("AI_MAX_CALLS_PER_HOUR", "30"))
# Raised from 8000: the grounding block now carries the codebase digest + recent
# Claude prompts, which is high-value context we don't want truncated. Abuse is
# already bounded by the hourly call limit, so a larger single-user prompt is fine.
MAX_PROMPT_CHARS = int(os.getenv("AI_MAX_PROMPT_CHARS", "16000"))
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


# Patterns for stderr/error output (CLI failure messages)
_AUTH_STDERR_PATTERNS = [
    "failed to authenticate", "unauthorized", "401", "login required",
    "token expired", "invalid_token", "session expired", "not logged in",
    "oauth error", "credential expired", "authentication required",
]


def _is_auth_error(stderr: str, stdout: str) -> bool:
    """Detect OAuth/auth failures in CLI error output (not response text)."""
    # Only check stderr for auth errors — stdout may legitimately mention auth topics
    text = stderr.lower()
    return any(p in text for p in _AUTH_STDERR_PATTERNS)


def _run_claude_subprocess(prompt_file: str, model: str) -> subprocess.CompletedProcess:
    """Run the Claude CLI subprocess once."""
    with open(prompt_file, 'r', encoding='utf-8') as pf:
        return subprocess.run(
            [
                CLAUDE_BIN,
                "--model", model,
                "--output-format", "json",
                "--max-turns", "3",
                "--allowedTools", "WebSearch", "WebFetch", "Bash", "Read", "Glob", "Grep",
                "--append-system-prompt", SYSTEM_PROMPT,
            ],
            stdin=pf,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )


def _call_claude(prompt: str, model: str = FAST_MODEL) -> str:
    """
    Call Claude via the CLI. Uses OAuth from your Claude Code login.
    Returns the raw response text.

    Protections:
    - Prompt injection patterns stripped
    - Prompt length capped at MAX_PROMPT_CHARS
    - Rate limited to MAX_CALLS_PER_HOUR
    - Subprocess timeout at 180s
    - Auth failure detection with one retry
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
        result = _run_claude_subprocess(prompt_file, model)

        # Detect auth failure and retry once
        if result.returncode not in (0, 1) and _is_auth_error(result.stderr, result.stdout):
            print(f"[Claude] Auth failure detected (exit {result.returncode}), retrying in 5s...")
            # Write status file so health check picks it up
            try:
                import datetime
                with open("data/claude-auth-status.txt", "w") as sf:
                    sf.write(f"EXPIRED {datetime.datetime.now()}")
            except OSError:
                pass
            time.sleep(5)
            # Re-write the prompt file (stdin was consumed)
            with open(prompt_file, 'w', encoding='utf-8') as f:
                f.write(prompt)
            result = _run_claude_subprocess(prompt_file, model)
            if result.returncode in (0, 1):
                print("[Claude] Retry succeeded after auth failure")
                try:
                    import datetime
                    with open("data/claude-auth-status.txt", "w") as sf:
                        sf.write(f"OK {datetime.datetime.now()}")
                except OSError:
                    pass
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
        # Write auth status on persistent failure
        if _is_auth_error(result.stderr, result.stdout):
            try:
                import datetime
                with open("data/claude-auth-status.txt", "w") as sf:
                    sf.write(f"EXPIRED {datetime.datetime.now()}")
            except OSError:
                pass
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
