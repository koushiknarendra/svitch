"""
Svitch — OpenAI-compatible /v1/chat/completions endpoint.

Drop-in replacement for the OpenAI API. Change one line in your app:
    client = openai.OpenAI(base_url="https://your-router.vercel.app/v1", api_key="any")

Supports:
    model="auto"                         Svitch picks provider + model based on complexity
    model="openai/gpt-4o"                Explicit routing
    model="anthropic/claude-sonnet-4-6"  Explicit routing

Environment variables:
    OPENAI_API_KEY      — enables OpenAI provider
    ANTHROPIC_API_KEY   — enables Anthropic provider
    SVITCH_API_KEY      — optional: require this key in Authorization header
"""

from __future__ import annotations

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SDK  = os.path.join(ROOT, "sdk", "python")
if os.path.isdir(SDK):
    sys.path.insert(0, SDK)

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(
    title="Svitch",
    description="OpenAI-compatible endpoint — routes to the best provider automatically.",
    version="0.1.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Lazy provider init (avoid import errors if a lib isn't installed) ──────

_openai_client = None
_anthropic_client = None


def _openai():
    global _openai_client
    if _openai_client is None:
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            return None
        try:
            import openai as _oai
            _openai_client = _oai.OpenAI(api_key=key)
        except ImportError:
            return None
    return _openai_client


def _anthropic():
    global _anthropic_client
    if _anthropic_client is None:
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            return None
        try:
            import anthropic as _ant
            _anthropic_client = _ant.Anthropic(api_key=key)
        except ImportError:
            return None
    return _anthropic_client


def _build_router():
    from svitch import Router
    router = Router()
    oai = _openai()
    ant = _anthropic()
    if oai:
        router.add("openai", oai)
    if ant:
        router.add("anthropic", ant)
    if not router._providers:
        raise HTTPException(503, detail="No providers configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY.")
    return router


# ── Auth check (optional) ─────────────────────────────────────────────────

def _check_auth(request: Request) -> None:
    expected = os.getenv("SVITCH_API_KEY")
    if not expected:
        return
    auth = request.headers.get("Authorization", "")
    token = auth.removeprefix("Bearer ").strip()
    if token != expected:
        raise HTTPException(401, detail="Invalid API key.")


# ── Request / response models ──────────────────────────────────────────────

class MessageIn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = "auto"
    messages: list[MessageIn]
    max_tokens: int = 2048
    temperature: float = 0.7
    system: Optional[str] = None
    fallback: Optional[str] = None
    stream: bool = False


# ── Routes ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "0.1.0",
        "providers": {
            "openai":    bool(os.getenv("OPENAI_API_KEY")),
            "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
        },
    }


@app.get("/v1/models")
def list_models(request: Request):
    _check_auth(request)
    models = [{"id": "auto", "object": "model", "owned_by": "svitch"}]
    if os.getenv("OPENAI_API_KEY"):
        for m in ["gpt-4o", "gpt-4o-mini"]:
            models.append({"id": m, "object": "model", "owned_by": "openai"})
        for m in ["openai/gpt-4o", "openai/gpt-4o-mini"]:
            models.append({"id": m, "object": "model", "owned_by": "openai"})
    if os.getenv("ANTHROPIC_API_KEY"):
        for m in ["claude-sonnet-4-6", "claude-haiku-4-5-20251001", "claude-opus-4-8"]:
            models.append({"id": f"anthropic/{m}", "object": "model", "owned_by": "anthropic"})
    return {"object": "list", "data": models}


@app.post("/v1/chat/completions")
def chat_completions(req: ChatRequest, request: Request):
    _check_auth(request)

    if req.stream:
        raise HTTPException(400, detail="Streaming is not supported yet.")

    router = _build_router()
    messages = [m.model_dump() for m in req.messages]

    try:
        result = router.chat(
            messages=messages,
            model=req.model,
            system=req.system,
            fallback=req.fallback,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
        )
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except Exception as e:
        raise HTTPException(502, detail=f"Provider error: {e}")

    return {
        "id": result.id,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": result.model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": result.content},
            "finish_reason": result.choices[0].finish_reason,
        }],
        "usage": {
            "prompt_tokens":     result.usage.prompt_tokens,
            "completion_tokens": result.usage.completion_tokens,
            "total_tokens":      result.usage.total_tokens,
        },
        # Svitch metadata
        "x_svitch_provider": result.provider,
        "x_svitch_tier":     result.tier,
        "x_svitch_model":    result.model,
    }
