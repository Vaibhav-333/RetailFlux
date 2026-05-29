"""Prompt injection guard for all user-facing LLM inputs.

Protects against:
  - Prompt injection via XML/HTML-like control tokens
  - Jailbreak trigger phrases
  - DAN (Do Anything Now) style bypasses
  - Instruction override attacks

Usage::

    from app.core.prompt_guard import is_injection_attempt, sanitize_user_message

    if is_injection_attempt(message):
        return REFUSAL_RESPONSE

    safe_message = sanitize_user_message(message)
"""
from __future__ import annotations

import re
import structlog

logger = structlog.get_logger()

# ── Compiled injection patterns ───────────────────────────────────────────────

# Control-token patterns (XML/system prompt injection)
_CONTROL_TOKENS: list[re.Pattern[str]] = [
    re.compile(r"</?\s*tool_call\s*>", re.IGNORECASE),
    re.compile(r"</?\s*system\s*>", re.IGNORECASE),
    re.compile(r"</?\s*assistant\s*>", re.IGNORECASE),
    re.compile(r"</?\s*human\s*>", re.IGNORECASE),
    re.compile(r"</?\s*prompt\s*>", re.IGNORECASE),
    re.compile(r"\[/?INST\]", re.IGNORECASE),
    re.compile(r"<\|im_start\|>", re.IGNORECASE),
    re.compile(r"<\|im_end\|>", re.IGNORECASE),
]

# Instruction-override phrases
_OVERRIDE_PHRASES: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"forget\s+(everything|all)\s+(you|i)\s+(were|was|have)", re.IGNORECASE),
    re.compile(r"override\s+(your\s+)?(instructions?|guidelines?|rules?|constraints?)", re.IGNORECASE),
    re.compile(r"new\s+(instructions?|guidelines?|rules?|directives?)\s*:", re.IGNORECASE),
    re.compile(r"your\s+(true\s+)?instructions?\s+(are|is|were)\s+now", re.IGNORECASE),
]

# Jailbreak / persona-swap patterns
_JAILBREAK_PHRASES: list[re.Pattern[str]] = [
    re.compile(r"\bDAN\b"),                                     # "Do Anything Now"
    re.compile(r"\bjailbreak\b", re.IGNORECASE),
    re.compile(r"\bdev(?:eloper)?\s+mode\b", re.IGNORECASE),
    re.compile(r"\bgrandma\s+exploit\b", re.IGNORECASE),
    re.compile(r"\bsudo\s+mode\b", re.IGNORECASE),
    re.compile(r"\bact\s+as\s+(?:an?\s+)?(?:evil|unrestricted|uncensored)\b", re.IGNORECASE),
    re.compile(r"\bpretend\s+(?:you\s+are|to\s+be)\s+(?:an?\s+)?(?:ai|bot|assistant)\s+without\s+restriction", re.IGNORECASE),
    re.compile(r"\byou\s+are\s+now\s+(?:free|liberated|unrestricted)", re.IGNORECASE),
]

# Prompt-leak / exfiltration patterns
_EXFILTRATION_PHRASES: list[re.Pattern[str]] = [
    re.compile(r"(print|repeat|show|output|tell\s+me)\s+(your\s+)?(system|initial|original)\s+(prompt|instructions?|context)", re.IGNORECASE),
    re.compile(r"what\s+(are\s+)?(your\s+)?(exact\s+)?(system|initial|full)\s+(prompt|instructions?)", re.IGNORECASE),
    re.compile(r"reveal\s+(your|the)\s+(system\s+)?prompt", re.IGNORECASE),
]

_ALL_PATTERNS: list[tuple[str, list[re.Pattern[str]]]] = [
    ("control_token", _CONTROL_TOKENS),
    ("override_phrase", _OVERRIDE_PHRASES),
    ("jailbreak", _JAILBREAK_PHRASES),
    ("exfiltration", _EXFILTRATION_PHRASES),
]

# Standard refusal for flagged messages
REFUSAL_RESPONSE = (
    "I'm unable to process that request. It appears to contain content "
    "that could interfere with my operating guidelines. Please rephrase "
    "your question about RetailFlux analytics."
)


# ── Public API ────────────────────────────────────────────────────────────────


def is_injection_attempt(text: str) -> bool:
    """Return True if ``text`` contains known prompt injection patterns.

    Fast path: scan all compiled patterns and short-circuit on first match.
    Logs the matched category for security telemetry (no user PII in log).
    """
    for category, patterns in _ALL_PATTERNS:
        for pattern in patterns:
            if pattern.search(text):
                logger.warning(
                    "prompt_injection_detected",
                    category=category,
                    pattern=pattern.pattern[:60],
                    text_length=len(text),
                )
                return True
    return False


def sanitize_user_message(text: str) -> str:
    """Strip known injection control tokens from ``text``.

    - Removes XML/HTML-like control tokens (``<system>``, ``</tool_call>``, etc.)
    - Collapses repeated whitespace created by removal.
    - Does NOT remove override phrases — those are caught by
      ``is_injection_attempt`` which should be called first to reject outright.

    Returns the cleaned string (may equal the input if nothing was stripped).
    """
    sanitized = text
    for pattern in _CONTROL_TOKENS:
        sanitized = pattern.sub("", sanitized)

    # Remove [INST] style brackets used by some open-weight model prompts
    sanitized = re.sub(r"\[/?(INST|SYS|SYS_PROMPT)\]", "", sanitized, flags=re.IGNORECASE)

    # Collapse runs of whitespace / blank lines
    sanitized = re.sub(r"\n{3,}", "\n\n", sanitized)
    sanitized = sanitized.strip()

    if sanitized != text:
        logger.info("prompt_sanitized", original_length=len(text), sanitized_length=len(sanitized))

    return sanitized
