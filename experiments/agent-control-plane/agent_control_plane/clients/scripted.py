"""Deterministic in-memory client for tests and offline demos.

The original project shipped no way to exercise the orchestrator without live
API keys. :class:`ScriptedClient` fixes that: it returns canned replies and
records every call, so the cooperative loop can be tested end-to-end offline.
"""

from __future__ import annotations

from typing import Any

from .base import LLMClient, LLMMetadata


class ScriptedClient(LLMClient):
    """An :class:`LLMClient` that returns scripted replies and records calls.

    ``replies`` maps a substring to the reply returned when that substring is
    present in the prompt (first match wins); otherwise ``default`` is used.
    """

    def __init__(
        self,
        name: str,
        *,
        replies: dict[str, str] | None = None,
        default: str = "<scripted-reply>",
        fail: bool = False,
    ) -> None:
        self.name = name
        self._replies = dict(replies or {})
        self._default = default
        self._fail = fail
        #: Ordered log of ``(method, argument)`` tuples for assertions.
        self.calls: list[tuple[str, str]] = []

    async def ask(self, prompt: str, *, system: str | None = None, **kwargs: Any) -> str:
        from .base import LLMTransportError

        self.calls.append(("ask", prompt))
        if self._fail:
            raise LLMTransportError(f"{self.name}: scripted failure")
        for needle, reply in self._replies.items():
            if needle in prompt:
                return reply
        return self._default

    async def embed(self, text: str, **kwargs: Any) -> list[float]:
        self.calls.append(("embed", text))
        return [float(len(text))]

    def describe(self) -> LLMMetadata:
        return LLMMetadata(provider="scripted", model=self.name, supports_embeddings=True)


__all__ = ["ScriptedClient"]
