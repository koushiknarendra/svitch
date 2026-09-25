"""
Prefix Stabilizer — normalize system prompts for LLM provider KV cache hits.

Unstable system prompts (timestamps, session IDs, request tokens) cause a
cache miss on every single call, paying full input token cost each time.
Stabilizing the prefix lets the provider serve from its KV cache:

  Anthropic — cache-read tokens cost ~10% of normal input token price.
  OpenAI    — prompts > 1024 tokens are auto-cached when the prefix is stable.

Latency impact: 30-50% lower TTFT on repeated agent calls with the same
system prompt structure.

This is also a compliance signal: timestamps and session IDs embedded in
system prompts are inadvertent per-request data leaks. `StabilizeResult.removed`
surfaces exactly what was replaced so the audit trail knows what changed.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

# (label, compiled pattern, stable placeholder)
_UNSTABLE: list[tuple[str, re.Pattern, str]] = [
    (
        "timestamp_iso",
        re.compile(
            r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2})?(\.\d+)?(Z|[+-]\d{2}:?\d{2})?",
        ),
        "[TIMESTAMP]",
    ),
    (
        "timestamp_date_phrase",
        re.compile(
            r"(today is|current date[:\s]+|as of[:\s]+)\s*[\w,]+ \d{1,2}[,\s]+\d{4}",
            re.IGNORECASE,
        ),
        "[DATE_PHRASE]",
    ),
    (
        "unix_timestamp",
        re.compile(r"\b1[6-9]\d{8}\b"),
        "[UNIX_TS]",
    ),
    (
        "uuid",
        re.compile(
            r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
            re.IGNORECASE,
        ),
        "[UUID]",
    ),
    (
        "session_id",
        re.compile(r"\bsession[_-]?id[:\s]+[\w\-]{8,}\b", re.IGNORECASE),
        "[SESSION_ID]",
    ),
    (
        "request_id",
        re.compile(r"\brequest[_-]?id[:\s]+[\w\-]{8,}\b", re.IGNORECASE),
        "[REQUEST_ID]",
    ),
    (
        "hex_id",
        re.compile(r"\b[0-9a-f]{24,}\b"),
        "[HEX_ID]",
    ),
]


@dataclass
class StabilizeResult:
    text: str           # normalized system prompt — safe to send to the provider
    original: str       # unmodified original — preserved for audit
    hash: str           # SHA-256 prefix of `text` — use for cache-hit rate tracking
    removed: list[str]  # pattern labels replaced (e.g. ["timestamp_iso", "uuid"])
    changed: bool       # True when at least one substitution occurred


def stabilize(system: str) -> StabilizeResult:
    """
    Normalize a system prompt to maximize LLM provider KV cache hits.

    Replaces per-request variables (timestamps, UUIDs, session/request IDs)
    with stable placeholders. The original is preserved in `StabilizeResult.original`
    so callers can log it to the audit trail without losing information.

    Args:
        system: Raw system prompt string.

    Returns:
        StabilizeResult with normalized text, SHA-256 prefix hash, and a list
        of pattern labels that were replaced.
    """
    if not system:
        return StabilizeResult(text=system, original=system, hash="", removed=[], changed=False)

    text = system
    removed: list[str] = []

    for label, pattern, placeholder in _UNSTABLE:
        new_text, n = pattern.subn(placeholder, text)
        if n:
            text = new_text
            removed.append(label)

    digest = hashlib.sha256(text.encode()).hexdigest()[:16]
    return StabilizeResult(
        text=text,
        original=system,
        hash=digest,
        removed=removed,
        changed=bool(removed),
    )


def anthropic_cache_block(text: str) -> list[dict]:
    """
    Wrap stabilized text in an Anthropic prompt-caching block.

    Pass the returned list as the `system` parameter to `client.messages.create()`.
    Anthropic caches tokens at this breakpoint; subsequent requests with the
    same prefix pay ~10% of normal input token cost (minimum 1024 tokens).

    Example:
        system_blocks = anthropic_cache_block(stabilize(raw_system).text)
        client.messages.create(model=..., system=system_blocks, messages=...)
    """
    return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]
