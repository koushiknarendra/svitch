import re
from dataclasses import dataclass
from typing import Optional

@dataclass
class Entity:
    type: str
    value: str
    start: int
    end: int
    masked: Optional[str] = None


# ---------------------------------------------------------------------------
# Aadhaar
# Formats: 1234 5678 9012 | 1234-5678-9012 | 123456789012
# First digit cannot be 0 or 1. Verhoeff check omitted for performance —
# format match is sufficient for redaction purposes.
# Negative lookbehind: don't match inside a +91 phone number.
# ---------------------------------------------------------------------------
_AADHAAR = re.compile(
    r'(?<!\+)'                      # not preceded by + (avoids +91XXXXXXXXXX collision)
    r'(?<!\d)'                      # not preceded by another digit
    r'([2-9][0-9]{3})'             # first group of 4 (starts 2-9)
    r'[\s\-]?'
    r'([0-9]{4})'
    r'[\s\-]?'
    r'([0-9]{4})'
    r'(?!\d)'                       # not followed by another digit
)

# Masked Aadhaar: XXXX XXXX 1234 or xxxx-xxxx-1234
_AADHAAR_MASKED = re.compile(
    r'\b[Xx*]{4}[\s\-]?[Xx*]{4}[\s\-]?[0-9]{4}\b'
)

# ---------------------------------------------------------------------------
# PAN (Permanent Account Number)
# Format: ABCDE1234F — 5 uppercase letters, 4 digits, 1 uppercase letter
# Technically the 4th char encodes taxpayer type (C,P,H,F,A,T,B,L,J,G),
# but we accept any uppercase letter to catch malformed/unofficial PANs too.
# ---------------------------------------------------------------------------
_PAN = re.compile(
    r'\b([A-Z]{3}[A-Z][A-Z][0-9]{4}[A-Z])\b'
)

# ---------------------------------------------------------------------------
# UPI ID
# Format: localpart@provider (e.g. 9876543210@paytm, name@okicici)
# ---------------------------------------------------------------------------
_UPI_PROVIDERS = (
    'paytm|gpay|phonepe|okicici|okhdfcbank|oksbi|okaxis|ybl|axl|apl|'
    'ibl|icici|hdfcbank|sbi|upi|freecharge|airtel|jio|amazon|indus|'
    'boi|cnrb|psb|aubank|dbs|federal|idfc|kbl|kvb|rbl|scb|tjsb|uco|'
    'uboi|unionbank|vjb|mahb|nsdl|hsbc|cub|dena|vijaya|allahabad|'
    'kotak|pnb|bob|barb|utbi|nkgsb|abhyudaya|apgb|bdbl|brkgb|chsgb|'
    'mgb|nainital|paribas|saraswat|scbl|syndicate|tmbl|ucb|varachha'
)
_UPI = re.compile(
    r'\b[\w.\-]{2,256}@(?:' + _UPI_PROVIDERS + r')\b',
    re.IGNORECASE
)

# ---------------------------------------------------------------------------
# IFSC Code
# Format: ABCD0123456 — 4 letters (bank code), 0, 6 alphanumeric (branch)
# ---------------------------------------------------------------------------
_IFSC = re.compile(r'\b([A-Z]{4}0[A-Z0-9]{6})\b')

# ---------------------------------------------------------------------------
# Indian Mobile Number
# 10 digits starting with 6-9, optionally preceded by +91, 0, 91
# ---------------------------------------------------------------------------
_MOBILE_IN = re.compile(
    r'(?<!\d)'
    r'(?:\+91[\s\-]?|91[\s\-]?|0)?'
    r'([6-9][0-9]{9})'
    r'(?!\d)'
)

# ---------------------------------------------------------------------------
# Indian Passport
# Format: A1234567 — 1 uppercase letter followed by 7 digits
# ---------------------------------------------------------------------------
_PASSPORT_IN = re.compile(r'\b([A-PR-WYa-pr-wy][0-9]{7})\b')

# ---------------------------------------------------------------------------
# Voter ID (EPIC — Electoral Photo Identity Card)
# Format: ABC1234567 — 3 uppercase letters followed by 7 digits
# ---------------------------------------------------------------------------
_VOTER_ID = re.compile(r'\b([A-Z]{3}[0-9]{7})\b')

# ---------------------------------------------------------------------------
# GST Number
# Format: 22AAAAA0000A1Z5 — 15 chars: 2-digit state code + PAN + entity
# 4th char of embedded PAN accepted as any letter (same reasoning as PAN above).
# ---------------------------------------------------------------------------
_GST = re.compile(
    r'\b([0-3][0-9][A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]Z[0-9A-Z])\b'
)

# ---------------------------------------------------------------------------
# Bank Account Number
# 9–18 digits. Heuristic: only flag when near banking keywords to reduce
# false positives (plain long numbers are common for other reasons).
# ---------------------------------------------------------------------------
_BANK_ACCOUNT_CONTEXT = re.compile(
    r'(?:account\s*(?:number|no\.?|#)|a/?c\s*(?:no\.?|#)|bank\s*a/?c)'
    r'[\s:]*([0-9]{9,18})',
    re.IGNORECASE
)

# ---------------------------------------------------------------------------
# Driving Licence (India)
# Format varies by state: MH01 20110012345 or MH-01-2011-0012345
# General pattern: 2-letter state code + 2-digit RTO + year + serial
# ---------------------------------------------------------------------------
_DL_IN = re.compile(
    r'\b([A-Z]{2}[\s\-]?[0-9]{2}[\s\-]?[0-9]{4}[\s\-]?[0-9]{7})\b',
    re.IGNORECASE
)


def detect(text: str) -> list[Entity]:
    entities: list[Entity] = []

    def _add(pattern: re.Pattern, entity_type: str, text: str, group: int = 0):
        for m in pattern.finditer(text):
            val = m.group(group)
            entities.append(Entity(
                type=entity_type,
                value=val,
                start=m.start(group),
                end=m.end(group),
            ))

    _add(_AADHAAR, "AADHAAR", text)
    _add(_AADHAAR_MASKED, "AADHAAR_MASKED", text)
    _add(_PAN, "PAN", text, group=1)
    _add(_UPI, "UPI_ID", text)
    _add(_IFSC, "IFSC", text, group=1)
    _add(_MOBILE_IN, "MOBILE_IN", text, group=1)
    _add(_GST, "GST", text, group=1)
    _add(_BANK_ACCOUNT_CONTEXT, "BANK_ACCOUNT", text, group=1)

    # Higher false-positive risk — only add when not already matched a longer entity
    matched_spans = {(e.start, e.end) for e in entities}

    for m in _PASSPORT_IN.finditer(text):
        if (m.start(1), m.end(1)) not in matched_spans:
            entities.append(Entity(type="PASSPORT_IN", value=m.group(1), start=m.start(1), end=m.end(1)))

    for m in _VOTER_ID.finditer(text):
        if (m.start(1), m.end(1)) not in matched_spans:
            entities.append(Entity(type="VOTER_ID", value=m.group(1), start=m.start(1), end=m.end(1)))

    # Sort by position
    entities.sort(key=lambda e: e.start)
    return entities


def redact(text: str, replacement: str = "token") -> tuple[str, list[Entity]]:
    """
    Returns (redacted_text, entities_found).
    replacement="token"  → [AADHAAR], [PAN], etc.
    replacement="mask"   → XXXX XXXX 1234 for Aadhaar, XXXXXNNNNX for PAN, etc.
    """
    entities = detect(text)
    if not entities:
        return text, []

    # Build non-overlapping entity list (longer match wins on overlap)
    non_overlapping: list[Entity] = []
    for entity in entities:
        if non_overlapping and entity.start < non_overlapping[-1].end:
            # Keep the longer match
            if (entity.end - entity.start) > (non_overlapping[-1].end - non_overlapping[-1].start):
                non_overlapping[-1] = entity
        else:
            non_overlapping.append(entity)

    result = []
    cursor = 0
    for entity in non_overlapping:
        result.append(text[cursor:entity.start])
        if replacement == "mask":
            result.append(_mask(entity))
        else:
            result.append(f"[{entity.type}]")
        cursor = entity.end
    result.append(text[cursor:])

    return "".join(result), non_overlapping


def _mask(entity: Entity) -> str:
    if entity.type == "AADHAAR":
        return "XXXX XXXX " + entity.value.replace(" ", "").replace("-", "")[-4:]
    if entity.type == "PAN":
        return entity.value[:5] + "XXXX" + entity.value[-1]
    if entity.type == "MOBILE_IN":
        return "XXXXXX" + entity.value[-4:]
    if entity.type == "UPI_ID":
        parts = entity.value.split("@")
        return "XXXX@" + parts[1] if len(parts) == 2 else "[UPI_ID]"
    return f"[{entity.type}]"
