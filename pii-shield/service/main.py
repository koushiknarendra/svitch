from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from detectors import detect_all, redact_all
from detectors.india import detect as detect_india, redact as redact_india
from detectors.common import detect as detect_common
from models import (
    DetectRequest, DetectResponse, EntityResponse,
    RedactRequest, RedactResponse,
    WrapRequest, WrapResponse,
)

app = FastAPI(
    title="Svitch PII Shield",
    description="AI data security layer — detect and redact Indian and global PII from LLM prompts and responses.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _run_detect(text: str, locale: str):
    if locale == "in":
        return detect_india(text)
    if locale == "global":
        return detect_common(text)
    return detect_all(text)


def _run_redact(text: str, locale: str, replacement: str):
    if locale == "in":
        return redact_india(text, replacement)
    if locale == "global":
        from detectors.common import detect as _detect_common
        from detectors.india import _mask, Entity
        entities = _detect_common(text)
        if not entities:
            return text, []
        result, cursor = [], 0
        for e in entities:
            result.append(text[cursor:e.start])
            result.append(f"[{e.type}]")
            cursor = e.end
        result.append(text[cursor:])
        return "".join(result), entities
    return redact_all(text, replacement)


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


@app.post("/detect", response_model=DetectResponse)
def detect_endpoint(req: DetectRequest):
    entities = _run_detect(req.text, req.locale)
    return DetectResponse(
        entities=[EntityResponse(type=e.type, value=e.value, start=e.start, end=e.end) for e in entities],
        count=len(entities),
    )


@app.post("/redact", response_model=RedactResponse)
def redact_endpoint(req: RedactRequest):
    redacted, entities = _run_redact(req.text, req.locale, req.replacement)
    return RedactResponse(
        text=redacted,
        original_text=req.text,
        entities=[EntityResponse(type=e.type, value=e.value, start=e.start, end=e.end) for e in entities],
        count=len(entities),
    )


@app.post("/wrap", response_model=WrapResponse)
def wrap_endpoint(req: WrapRequest):
    """
    Redact PII from all messages in an LLM chat request.
    Returns the cleaned messages ready to forward to any LLM provider.
    """
    cleaned_messages = []
    all_entities = []
    total = 0

    for msg in req.messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            redacted, entities = _run_redact(content, req.locale, req.replacement)
            cleaned_messages.append({**msg, "content": redacted})
            all_entities.append([EntityResponse(type=e.type, value=e.value, start=e.start, end=e.end) for e in entities])
            total += len(entities)
        else:
            cleaned_messages.append(msg)
            all_entities.append([])

    return WrapResponse(
        messages=cleaned_messages,
        redacted_count=total,
        entities_by_message=all_entities,
    )
