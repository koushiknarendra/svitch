import re
from .india import Entity


_EMAIL = re.compile(r'\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b')
_IPV4 = re.compile(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b')
_IPV6 = re.compile(r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b')

# Generic international phone (10-15 digits, optional + prefix, hyphens/spaces)
# Deliberately conservative — only flags clear phone patterns with country code
_PHONE_INTL = re.compile(r'(?<!\d)\+(?:[1-9][0-9]{6,14})(?!\d)')


def detect(text: str) -> list[Entity]:
    entities: list[Entity] = []

    for m in _EMAIL.finditer(text):
        entities.append(Entity(type="EMAIL", value=m.group(), start=m.start(), end=m.end()))

    for m in _IPV4.finditer(text):
        entities.append(Entity(type="IPV4", value=m.group(), start=m.start(), end=m.end()))

    for m in _IPV6.finditer(text):
        entities.append(Entity(type="IPV6", value=m.group(), start=m.start(), end=m.end()))

    for m in _PHONE_INTL.finditer(text):
        # Skip if already detected as Indian mobile (handled in india.py with context)
        entities.append(Entity(type="PHONE_INTL", value=m.group(), start=m.start(), end=m.end()))

    entities.sort(key=lambda e: e.start)
    return entities
