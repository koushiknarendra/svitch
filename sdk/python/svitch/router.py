"""
Svitch Router — route prompts to the right LLM provider automatically.

Usage:
    from svitch import Router
    import openai, anthropic

    router = Router()
    router.add("openai",    openai.OpenAI())
    router.add("anthropic", anthropic.Anthropic())

    # Auto-routing: Svitch classifies complexity and picks provider + model
    r = router.chat(messages=[{"role": "user", "content": "What is Aadhaar?"}])
    print(r.content)
    print(r.provider, r.model, r.tier)   # "openai", "gpt-4o-mini", "fast"

    # Explicit provider/model
    r = router.chat(messages=[...], model="anthropic/claude-sonnet-4-6")

    # Failover: try OpenAI, fall back to Anthropic on error
    r = router.chat(messages=[...], model="openai/gpt-4o",
                    fallback="anthropic/claude-sonnet-4-6")

    # Drop-in OpenAI client replacement
    client = router.as_openai_client()
    response = client.chat.completions.create(model="auto", messages=[...])
    print(response.choices[0].message.content)
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from .classify import classify as _classify
from .cache import stabilize as _stabilize, anthropic_cache_block as _cache_block

# ── Default model tiers per provider type ─────────────────────────────────

_OPENAI_DEFAULTS: dict[str, str] = {
    "fast":    "gpt-4o-mini",
    "default": "gpt-4o",
    "complex": "gpt-4o",
}
_ANTHROPIC_DEFAULTS: dict[str, str] = {
    "fast":    "claude-haiku-4-5-20251001",
    "default": "claude-sonnet-4-6",
    "complex": "claude-opus-4-8",
}


# ── Normalised response (mimics openai.ChatCompletion) ────────────────────

@dataclass
class _Message:
    role: str
    content: str


@dataclass
class _Choice:
    index: int
    message: _Message
    finish_reason: str


@dataclass
class _Usage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class RouteResult:
    """
    Unified response from any provider.
    Mimics openai.ChatCompletion so existing code works unchanged:
        response.choices[0].message.content
        response.usage.prompt_tokens
    Extra fields:
        response.provider  — "openai" | "anthropic" | your custom name
        response.tier      — "fast" | "default" | "complex" | "explicit"
    """
    id: str
    object: str
    choices: list[_Choice]
    usage: _Usage
    model: str
    provider: str
    tier: str = ""

    @property
    def content(self) -> str:
        """Shortcut: response.content instead of response.choices[0].message.content"""
        return self.choices[0].message.content if self.choices else ""


# ── Provider registry ──────────────────────────────────────────────────────

@dataclass
class _Provider:
    name: str
    client: Any
    kind: str        # "openai" | "anthropic"
    models: dict[str, str]

    def model_for(self, tier: str) -> str:
        return self.models.get(tier) or self.models.get("default") or next(iter(self.models.values()))


def _detect_kind(client: Any) -> str:
    name = type(client).__name__
    if "Anthropic" in name:
        return "anthropic"
    return "openai"


# ── Message format translation ─────────────────────────────────────────────

def _split_system(messages: list[dict], extra_system: Optional[str]) -> tuple[Optional[str], list[dict]]:
    """Extract system message from OpenAI-style list for Anthropic format."""
    system_parts: list[str] = []
    filtered: list[dict] = []
    for m in messages:
        if m.get("role") == "system":
            system_parts.append(m.get("content", ""))
        else:
            filtered.append(m)
    if extra_system:
        system_parts.insert(0, extra_system)
    return ("\n\n".join(system_parts) or None), filtered


def _normalise_openai(resp: Any, provider_name: str) -> RouteResult:
    choice = resp.choices[0]
    usage = resp.usage
    return RouteResult(
        id=resp.id,
        object="chat.completion",
        choices=[_Choice(
            index=0,
            message=_Message(role="assistant", content=choice.message.content or ""),
            finish_reason=choice.finish_reason or "stop",
        )],
        usage=_Usage(
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
        ),
        model=resp.model,
        provider=provider_name,
    )


def _normalise_anthropic(resp: Any, provider_name: str) -> RouteResult:
    content = resp.content[0].text if resp.content else ""
    usage = resp.usage
    return RouteResult(
        id=f"svitch-{uuid.uuid4().hex[:12]}",
        object="chat.completion",
        choices=[_Choice(
            index=0,
            message=_Message(role="assistant", content=content),
            finish_reason="stop",
        )],
        usage=_Usage(
            prompt_tokens=usage.input_tokens,
            completion_tokens=usage.output_tokens,
            total_tokens=usage.input_tokens + usage.output_tokens,
        ),
        model=resp.model,
        provider=provider_name,
    )


# ── OpenAI-compatible shim ─────────────────────────────────────────────────

class _RouterCompletions:
    def __init__(self, router: "Router") -> None:
        self._r = router

    def create(self, *, messages: list[dict], model: str = "auto", **kwargs) -> RouteResult:
        return self._r.chat(messages=messages, model=model, **kwargs)


class _RouterChat:
    def __init__(self, router: "Router") -> None:
        self.completions = _RouterCompletions(router)


class RouterClient:
    """
    Drop-in replacement for openai.OpenAI() that routes across all registered providers.
    Returned by router.as_openai_client().
    """
    def __init__(self, router: "Router") -> None:
        self.chat = _RouterChat(router)


# ── Router ─────────────────────────────────────────────────────────────────

class Router:
    """
    Route prompts to the right LLM provider based on complexity or explicit choice.

    Quick start:
        router = Router()
        router.add("openai",    openai.OpenAI())
        router.add("anthropic", anthropic.Anthropic())
        r = router.chat(messages=[...], model="auto")
    """

    def __init__(self) -> None:
        self._providers: list[_Provider] = []

    # ── Registration ───────────────────────────────────────────────────────

    def add(
        self,
        name: str,
        client: Any,
        models: Optional[dict[str, str]] = None,
    ) -> "Router":
        """
        Register a provider.

        Args:
            name:    Short identifier — "openai", "anthropic", "local", etc.
            client:  openai.OpenAI(), anthropic.Anthropic(), or any compatible client.
            models:  Map of tier → model ID.
                     Keys: "fast", "default", "complex".
                     Omit to use sensible defaults for the detected client type.

        Returns self so calls can be chained:
            router.add("openai", ...).add("anthropic", ...)
        """
        kind = _detect_kind(client)
        if models is None:
            models = (_ANTHROPIC_DEFAULTS if kind == "anthropic" else _OPENAI_DEFAULTS).copy()
        self._providers.append(_Provider(name=name, client=client, kind=kind, models=models))
        return self

    # ── Chat ───────────────────────────────────────────────────────────────

    def chat(
        self,
        messages: list[dict],
        model: str = "auto",
        system: Optional[str] = None,
        fallback: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> RouteResult:
        """
        Send messages to the best provider.

        model:
            "auto"                        Auto-select based on complexity
            "openai/gpt-4o"               Explicit provider/model
            "anthropic/claude-sonnet-4-6" Explicit provider/model
            "gpt-4o-mini"                 Model name — uses first provider that has it

        fallback:
            "anthropic/claude-sonnet-4-6" Try this if primary raises an exception.
        """
        if not self._providers:
            raise RuntimeError("No providers registered. Call router.add() first.")

        provider, model_id, tier = self._resolve(model, messages)

        try:
            result = self._call(provider, model_id, messages, system, max_tokens, temperature)
            result.tier = tier
            return result
        except Exception as primary_err:
            if fallback:
                fb_provider, fb_model_id, fb_tier = self._resolve(fallback, messages)
                result = self._call(fb_provider, fb_model_id, messages, system, max_tokens, temperature)
                result.tier = fb_tier
                return result
            raise primary_err

    def as_openai_client(self) -> RouterClient:
        """
        Return a drop-in openai.OpenAI() replacement that routes across providers.

            client = router.as_openai_client()
            r = client.chat.completions.create(model="auto", messages=[...])
            print(r.choices[0].message.content)
        """
        return RouterClient(self)

    # ── Internal ───────────────────────────────────────────────────────────

    def _resolve(self, model: str, messages: list[dict]) -> tuple[_Provider, str, str]:
        if model == "auto":
            tier = _classify(messages)
            provider = self._providers[0]
            return provider, provider.model_for(tier), tier

        if "/" in model:
            provider_name, model_id = model.split("/", 1)
            return self._get(provider_name), model_id, "explicit"

        # Bare model name — find a provider that has it configured
        for p in self._providers:
            if model in p.models.values():
                return p, model, "explicit"

        # Fall back to first provider, pass model name as-is
        return self._providers[0], model, "explicit"

    def _get(self, name: str) -> _Provider:
        for p in self._providers:
            if p.name == name:
                return p
        available = [p.name for p in self._providers]
        raise ValueError(f"Provider '{name}' not registered. Available: {available}")

    def _call(
        self,
        provider: _Provider,
        model_id: str,
        messages: list[dict],
        system: Optional[str],
        max_tokens: int,
        temperature: float,
    ) -> RouteResult:
        if provider.kind == "anthropic":
            sys_prompt, anthro_messages = _split_system(messages, system)
            kwargs: dict[str, Any] = {
                "model": model_id,
                "messages": anthro_messages,
                "max_tokens": max_tokens,
            }
            if sys_prompt:
                stable = _stabilize(sys_prompt)
                kwargs["system"] = _cache_block(stable.text)
            resp = provider.client.messages.create(**kwargs)
            return _normalise_anthropic(resp, provider.name)
        else:
            oai_messages = list(messages)
            if system:
                stable = _stabilize(system)
                oai_messages = [{"role": "system", "content": stable.text}] + oai_messages
            resp = provider.client.chat.completions.create(
                model=model_id,
                messages=oai_messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return _normalise_openai(resp, provider.name)
