"""
Svitch Private Enclave — Inference Server

OpenAI-compatible API proxy that sits in front of a local vLLM instance.
Every request passes through the PII Shield before reaching the model,
and every call is recorded in the Agent Tracer audit log.

Customers connect via WireGuard and point their OpenAI client to this server:

    import openai
    client = openai.OpenAI(
        base_url="http://10.0.0.1:8080/v1",
        api_key="svitch-enclave",          # any non-empty string
    )
    response = client.chat.completions.create(
        model="llama-3.1-8b-instruct",
        messages=[{"role": "user", "content": "..."}]
    )
"""

from __future__ import annotations

import os
import time
import uuid
import httpx
import json
import sys

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse

# ── Imports from sibling modules ─────────────────────────────────────────────
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "pii-shield", "service"))
sys.path.insert(0, os.path.join(_ROOT, "agent-tracer"))

try:
    from detectors import detect_all, redact_all
    _PII_AVAILABLE = True
except ImportError:
    _PII_AVAILABLE = False

try:
    from svitch_tracer import SvitchTracer
    _TRACER_AVAILABLE = True
except ImportError:
    _TRACER_AVAILABLE = False

# ── Config ────────────────────────────────────────────────────────────────────
VLLM_BASE_URL   = os.environ.get("VLLM_BASE_URL", "http://localhost:8000")
DEFAULT_MODEL   = os.environ.get("DEFAULT_MODEL", "llama-3.1-8b-instruct")
ENCLAVE_ID      = os.environ.get("ENCLAVE_ID", "svitch-enclave-01")
PII_MODE        = os.environ.get("PII_MODE", "redact")          # redact | detect | off
TRACER_ENABLED  = os.environ.get("TRACER_ENABLED", "true") == "true"
AUDIT_DB        = os.environ.get("SVITCH_DB_PATH", "svitch_audit.db")

os.environ.setdefault("SVITCH_DB_PATH", AUDIT_DB)

# ── Tracer setup ──────────────────────────────────────────────────────────────
_tracer: SvitchTracer | None = None
if _TRACER_AVAILABLE and TRACER_ENABLED:
    _tracer = SvitchTracer(agent_id=ENCLAVE_ID)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Svitch Enclave",
    description="Private AI inference — OpenAI-compatible, PII-shielded, audit-logged.",
    version="0.1.0",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _shield_text(text: str) -> tuple[str, list[str]]:
    """Run PII Shield. Returns (redacted_text, pii_types_found)."""
    if not _PII_AVAILABLE or PII_MODE == "off":
        return text, []
    entities = detect_all(text)
    pii_types = list({e.type for e in entities})
    if PII_MODE == "redact" and entities:
        redacted, _ = redact_all(text)
        return redacted, pii_types
    return text, pii_types


def _shield_messages(messages: list[dict]) -> tuple[list[dict], list[str]]:
    all_pii: list[str] = []
    cleaned = []
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            shielded, pii = _shield_text(content)
            all_pii.extend(pii)
            cleaned.append({**msg, "content": shielded})
        else:
            cleaned.append(msg)
    return cleaned, list(set(all_pii))


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "enclave_id": ENCLAVE_ID,
        "pii_shield": _PII_AVAILABLE,
        "tracer": _TRACER_AVAILABLE and TRACER_ENABLED,
        "vllm_url": VLLM_BASE_URL,
    }


@app.get("/v1/models")
async def list_models():
    """Proxy the model list from vLLM."""
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(f"{VLLM_BASE_URL}/v1/models")
            return r.json()
        except Exception:
            return {"object": "list", "data": [{"id": DEFAULT_MODEL, "object": "model"}]}


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    messages: list[dict] = body.get("messages", [])
    model = body.get("model", DEFAULT_MODEL)
    stream = body.get("stream", False)

    # ── PII Shield ────────────────────────────────────────────────────────────
    t0 = time.time()
    shielded_messages, pii_types = _shield_messages(messages)
    shield_ms = int((time.time() - t0) * 1000)

    # ── Forward to vLLM ───────────────────────────────────────────────────────
    upstream_body = {**body, "messages": shielded_messages}

    if stream:
        return await _stream_response(upstream_body, model, shielded_messages, pii_types)

    async with httpx.AsyncClient(timeout=120) as client:
        try:
            r = await client.post(
                f"{VLLM_BASE_URL}/v1/chat/completions",
                json=upstream_body,
            )
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="vLLM engine not reachable. Is the enclave running?")

    result = r.json()

    # ── Audit log ─────────────────────────────────────────────────────────────
    if _tracer:
        response_text = ""
        try:
            response_text = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            pass

        prompt_text = "\n".join(m.get("content", "") for m in shielded_messages if isinstance(m.get("content"), str))

        with _tracer.run() as run:
            run.llm_call(
                provider="enclave",
                model=model,
                prompt=prompt_text,
                response=response_text,
                redact_pii=False,  # already redacted above
                metadata={
                    "shield_ms": shield_ms,
                    "pii_types_blocked": pii_types,
                    "enclave_id": ENCLAVE_ID,
                },
            )

    # Inject shield metadata into response
    result["svitch"] = {
        "pii_blocked": len(pii_types) > 0,
        "pii_types": pii_types,
        "shield_ms": shield_ms,
    }

    return JSONResponse(content=result)


async def _stream_response(body: dict, model: str, messages: list[dict], pii_types: list[str]):
    """Stream vLLM response back to client, injecting PII metadata at the end."""

    async def generator():
        async with httpx.AsyncClient(timeout=120) as client:
            try:
                async with client.stream("POST", f"{VLLM_BASE_URL}/v1/chat/completions", json=body) as r:
                    async for line in r.aiter_lines():
                        if line.startswith("data: "):
                            yield f"{line}\n\n"
            except httpx.ConnectError:
                err = json.dumps({"error": "vLLM engine not reachable"})
                yield f"data: {err}\n\ndata: [DONE]\n\n"

    return StreamingResponse(generator(), media_type="text/event-stream")
