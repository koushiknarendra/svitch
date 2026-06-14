from .india import Entity, detect as detect_india, redact as redact_india
from .common import detect as detect_common


def detect_all(text: str) -> list[Entity]:
    india = detect_india(text)
    common = detect_common(text)

    # Merge, deduplicate by span
    india_spans = {(e.start, e.end) for e in india}
    merged = india + [e for e in common if (e.start, e.end) not in india_spans]
    merged.sort(key=lambda e: e.start)
    return merged


def redact_all(text: str, replacement: str = "token") -> tuple[str, list[Entity]]:
    from .india import redact as _redact_india
    # Run India redaction first (highest priority), then common on result
    text_after_india, india_entities = _redact_india(text, replacement)

    # Detect common on original text, filter out spans already handled
    india_spans = {(e.start, e.end) for e in india_entities}
    common_entities = [e for e in detect_common(text) if (e.start, e.end) not in india_spans]

    if not common_entities:
        return text_after_india, india_entities

    # Apply common entity redaction on the already-redacted text is complex due to
    # position shifts. Re-run full redaction on original with all entities merged.
    all_entities = detect_all(text)
    if not all_entities:
        return text, []

    # Non-overlapping pass
    non_overlapping: list[Entity] = []
    for entity in all_entities:
        if non_overlapping and entity.start < non_overlapping[-1].end:
            if (entity.end - entity.start) > (non_overlapping[-1].end - non_overlapping[-1].start):
                non_overlapping[-1] = entity
        else:
            non_overlapping.append(entity)

    from .india import _mask
    result = []
    cursor = 0
    for entity in non_overlapping:
        result.append(text[cursor:entity.start])
        if replacement == "mask":
            result.append(_mask(entity) if entity.type in ("AADHAAR", "PAN", "MOBILE_IN", "UPI_ID") else f"[{entity.type}]")
        else:
            result.append(f"[{entity.type}]")
        cursor = entity.end
    result.append(text[cursor:])

    return "".join(result), non_overlapping
