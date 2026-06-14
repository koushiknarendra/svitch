"""
Client wrappers — drop-in replacements for OpenAI and Anthropic clients
that automatically redact PII from prompts before sending and from
responses before returning.
"""

from __future__ import annotations
from typing import Any, Literal
from .shield import redact as _redact


def wrap(client: Any, locale: Literal["in", "global", "all"] = "all") -> Any:
    """
    Wrap an OpenAI or Anthropic client to automatically redact PII.

    Usage:
        import svitch, openai
        client = svitch.wrap(openai.OpenAI())
        # Use exactly like openai.OpenAI()

        import svitch, anthropic
        client = svitch.wrap(anthropic.Anthropic())
    """
    client_type = type(client).__name__

    if "OpenAI" in client_type or "AsyncOpenAI" in client_type:
        return _wrap_openai(client, locale)
    if "Anthropic" in client_type or "AsyncAnthropic" in client_type:
        return _wrap_anthropic(client, locale)

    raise TypeError(
        f"svitch.wrap() does not support {client_type}. "
        "Supported: openai.OpenAI, openai.AsyncOpenAI, anthropic.Anthropic, anthropic.AsyncAnthropic"
    )


class _RedactingCompletions:
    def __init__(self, completions, locale):
        self._completions = completions
        self._locale = locale

    def create(self, **kwargs):
        messages = kwargs.get("messages", [])
        cleaned, total = _redact_messages(messages, self._locale)
        if total > 0:
            kwargs = {**kwargs, "messages": cleaned}
        return self._completions.create(**kwargs)

    async def acreate(self, **kwargs):
        messages = kwargs.get("messages", [])
        cleaned, total = _redact_messages(messages, self._locale)
        if total > 0:
            kwargs = {**kwargs, "messages": cleaned}
        return await self._completions.acreate(**kwargs)


class _RedactingChat:
    def __init__(self, chat, locale):
        self.completions = _RedactingCompletions(chat.completions, locale)


class _OpenAIWrapper:
    def __init__(self, client, locale):
        self._client = client
        self.chat = _RedactingChat(client.chat, locale)

    def __getattr__(self, name):
        return getattr(self._client, name)


def _wrap_openai(client: Any, locale: str) -> _OpenAIWrapper:
    return _OpenAIWrapper(client, locale)


class _AnthropicMessages:
    def __init__(self, messages_api, locale):
        self._messages = messages_api
        self._locale = locale

    def create(self, **kwargs):
        messages = kwargs.get("messages", [])
        cleaned, _ = _redact_messages(messages, self._locale)
        system = kwargs.get("system", "")
        if system:
            result = _redact(system, self._locale)
            kwargs = {**kwargs, "system": result.text}
        return self._messages.create(**{**kwargs, "messages": cleaned})

    async def acreate(self, **kwargs):
        messages = kwargs.get("messages", [])
        cleaned, _ = _redact_messages(messages, self._locale)
        return await self._messages.acreate(**{**kwargs, "messages": cleaned})


class _AnthropicWrapper:
    def __init__(self, client, locale):
        self._client = client
        self.messages = _AnthropicMessages(client.messages, locale)

    def __getattr__(self, name):
        return getattr(self._client, name)


def _wrap_anthropic(client: Any, locale: str) -> _AnthropicWrapper:
    return _AnthropicWrapper(client, locale)


def _redact_messages(messages: list[dict], locale: str) -> tuple[list[dict], int]:
    cleaned = []
    total_redacted = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str) and content:
            result = _redact(content, locale)
            cleaned.append({**msg, "content": result.text})
            total_redacted += result.count
        else:
            cleaned.append(msg)
    return cleaned, total_redacted
