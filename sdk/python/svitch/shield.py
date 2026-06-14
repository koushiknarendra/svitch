"""
Core PII detection and redaction — runs entirely locally, no network calls.
Mirrors the logic in pii-shield/service/detectors/ as a standalone module
so the SDK has zero runtime dependencies beyond the stdlib.
"""

import re
import sys
import os
from dataclasses import dataclass, field
from typing import Literal

# Allow the SDK to import detector logic directly when used from source.
# In installed package mode the patterns are inlined below.
_SERVICE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "pii-shield", "service")
if os.path.isdir(_SERVICE_PATH):
    sys.path.insert(0, _SERVICE_PATH)
    try:
        from detectors.india import detect as _detect_india, redact as _redact_india
        from detectors.common import detect as _detect_common
        from detectors import detect_all, redact_all
        _USE_SERVICE_DETECTORS = True
    except ImportError:
        _USE_SERVICE_DETECTORS = False
else:
    _USE_SERVICE_DETECTORS = False


@dataclass
class Entity:
    type: str
    value: str
    start: int
    end: int


@dataclass
class SvitchResult:
    text: str
    original_text: str
    entities: list[Entity] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.entities)

    @property
    def clean(self) -> bool:
        return len(self.entities) == 0

    def __repr__(self):
        return f"SvitchResult(count={self.count}, text={self.text!r})"


# ---------------------------------------------------------------------------
# Inline patterns — used when the service detectors aren't available
# (i.e., when installed via pip without the full repo)
# ---------------------------------------------------------------------------

_AADHAAR = re.compile(r'(?<!\+)(?<!\d)([2-9][0-9]{3})[\s\-]?([0-9]{4})[\s\-]?([0-9]{4})(?!\d)')
_AADHAAR_MASKED = re.compile(r'\b[Xx*]{4}[\s\-]?[Xx*]{4}[\s\-]?[0-9]{4}\b')
_PAN = re.compile(r'\b([A-Z]{5}[0-9]{4}[A-Z])\b')
_UPI_PROVIDERS = (
    'paytm|gpay|phonepe|okicici|okhdfcbank|oksbi|okaxis|ybl|axl|apl|ibl|'
    'icici|hdfcbank|sbi|upi|freecharge|airtel|jio|amazon|indus|boi|cnrb|'
    'psb|aubank|dbs|federal|idfc|kbl|kvb|rbl|scb|tjsb|uco|uboi|unionbank|'
    'kotak|pnb|bob|barb|nkgsb|saraswat|mahb|nsdl|hsbc|cub|paribas'
)
_UPI = re.compile(r'\b[\w.\-]{2,256}@(?:' + _UPI_PROVIDERS + r')\b', re.IGNORECASE)
_IFSC = re.compile(r'\b([A-Z]{4}0[A-Z0-9]{6})\b')
_MOBILE_IN = re.compile(r'(?<!\d)(?:\+91[\s\-]?|91[\s\-]?|0)?([6-9][0-9]{9})(?!\d)')
_GST = re.compile(r'\b([0-3][0-9][A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]Z[0-9A-Z])\b')
_BANK_ACCOUNT = re.compile(
    r'(?:account\s*(?:number|no\.?|#)|a/?c\s*(?:no\.?|#)|bank\s*a/?c)[\s:]*([0-9]{9,18})',
    re.IGNORECASE
)
_EMAIL = re.compile(r'\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b')
_IPV4 = re.compile(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b')


def _inline_detect(text: str) -> list[Entity]:
    entities: list[Entity] = []

    def _add(pat, etype, grp=0):
        for m in pat.finditer(text):
            entities.append(Entity(type=etype, value=m.group(grp), start=m.start(grp), end=m.end(grp)))

    _add(_AADHAAR, "AADHAAR")
    _add(_AADHAAR_MASKED, "AADHAAR_MASKED")
    _add(_PAN, "PAN", 1)
    _add(_UPI, "UPI_ID")
    _add(_IFSC, "IFSC", 1)
    _add(_MOBILE_IN, "MOBILE_IN", 1)
    _add(_GST, "GST", 1)
    _add(_BANK_ACCOUNT, "BANK_ACCOUNT", 1)
    _add(_EMAIL, "EMAIL")
    _add(_IPV4, "IPV4")

    entities.sort(key=lambda e: e.start)
    return entities


def _inline_redact(text: str, replacement: Literal["token", "mask"] = "token") -> tuple[str, list[Entity]]:
    entities = _inline_detect(text)
    if not entities:
        return text, []

    non_overlapping: list[Entity] = []
    for e in entities:
        if non_overlapping and e.start < non_overlapping[-1].end:
            if (e.end - e.start) > (non_overlapping[-1].end - non_overlapping[-1].start):
                non_overlapping[-1] = e
        else:
            non_overlapping.append(e)

    result, cursor = [], 0
    for e in non_overlapping:
        result.append(text[cursor:e.start])
        if replacement == "mask":
            result.append(_mask_entity(e))
        else:
            result.append(f"[{e.type}]")
        cursor = e.end
    result.append(text[cursor:])
    return "".join(result), non_overlapping


def _mask_entity(e: Entity) -> str:
    if e.type == "AADHAAR":
        digits = re.sub(r'[\s\-]', '', e.value)
        return f"XXXX XXXX {digits[-4:]}"
    if e.type == "PAN":
        return e.value[:5] + "XXXX" + e.value[-1]
    if e.type == "MOBILE_IN":
        return "XXXXXX" + e.value[-4:]
    if e.type == "UPI_ID":
        parts = e.value.split("@")
        return f"XXXX@{parts[1]}" if len(parts) == 2 else "[UPI_ID]"
    return f"[{e.type}]"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect(text: str, locale: Literal["in", "global", "all"] = "all") -> list[Entity]:
    """Detect PII entities in text. Returns a list of Entity objects."""
    if _USE_SERVICE_DETECTORS:
        if locale == "in":
            raw = _detect_india(text)
        elif locale == "global":
            raw = _detect_common(text)
        else:
            raw = detect_all(text)
        return [Entity(type=e.type, value=e.value, start=e.start, end=e.end) for e in raw]
    return _inline_detect(text)


def redact(
    text: str,
    locale: Literal["in", "global", "all"] = "all",
    replacement: Literal["token", "mask"] = "token",
) -> SvitchResult:
    """
    Detect and redact PII from text.

    Args:
        text: Input text to scan.
        locale: "in" for India-only, "global" for global only, "all" for both.
        replacement: "token" replaces with [AADHAAR], "mask" uses partial masking.

    Returns:
        SvitchResult with .text (redacted), .original_text, .entities, .count, .clean
    """
    if _USE_SERVICE_DETECTORS:
        if locale == "in":
            redacted_text, raw_entities = _redact_india(text, replacement)
        else:
            redacted_text, raw_entities = redact_all(text, replacement)
        entities = [Entity(type=e.type, value=e.value, start=e.start, end=e.end) for e in raw_entities]
    else:
        redacted_text, entities = _inline_redact(text, replacement)

    return SvitchResult(text=redacted_text, original_text=text, entities=entities)
