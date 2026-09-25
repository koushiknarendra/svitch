"""
Prompt complexity classifier — decides "fast", "default", or "complex".
Used by the Router to pick the right model tier automatically.
"""
from __future__ import annotations

_COMPLEX_KEYWORDS = frozenset([
    "analyze", "analyse", "explain", "compare", "evaluate", "assess",
    "research", "investigate", "comprehensive", "detailed", "thorough",
    "implement", "architecture", "strategy", "design",
    "write a", "create a", "build a", "develop", "refactor", "debug",
    "step by step", "in depth", "elaborate", "translate",
    "legal", "medical", "financial", "compliance", "audit",
    "summarize", "generate code", "write code", "essay",
])

_SIMPLE_PREFIXES = ("what is ", "who is ", "when did ", "where is ",
                    "define ", "list ", "name ")


def _token_estimate(text: str) -> int:
    return max(1, int(len(text.split()) * 1.3))


def classify(messages: list[dict]) -> str:
    """
    Returns "fast", "default", or "complex".

    fast    — simple lookup, extraction, short Q&A       → cheapest model
    default — standard reasoning, explanation             → standard model
    complex — deep analysis, long-form, code generation  → strongest model
    """
    user_turns = [m for m in messages if m.get("role") == "user"]
    user_text  = " ".join(m.get("content", "") for m in user_turns).lower().strip()
    total_tokens = sum(_token_estimate(m.get("content", "")) for m in messages)

    score = 0

    # Token volume is the strongest signal
    if total_tokens > 600:
        score += 3
    elif total_tokens > 200:
        score += 1

    # Multi-turn context
    if len(user_turns) > 2:
        score += 1

    # Complex keyword hit
    for kw in _COMPLEX_KEYWORDS:
        if kw in user_text:
            score += 2
            break

    # Simple prefix — negative signal
    for prefix in _SIMPLE_PREFIXES:
        if user_text.startswith(prefix):
            score -= 1
            break

    if score <= 1:
        return "fast"
    if score <= 4:
        return "default"
    return "complex"
