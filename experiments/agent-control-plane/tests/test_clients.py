"""Tests for the vendor-neutral client contract and the scripted client."""

from __future__ import annotations

import asyncio

import pytest
from agent_control_plane.clients import LLMNotSupported, ScriptedClient


def test_scripted_ask_matches_substring_else_default() -> None:
    client = ScriptedClient("a", replies={"hello": "world"}, default="fallback")
    assert asyncio.run(client.ask("say hello please")) == "world"
    assert asyncio.run(client.ask("nothing here")) == "fallback"
    assert client.calls == [("ask", "say hello please"), ("ask", "nothing here")]


def test_summarize_and_critique_default_to_ask() -> None:
    # The base class implements summarize/critique in terms of ask; the
    # scripted client only defines ask, so these must still work.
    client = ScriptedClient("a", default="ok")
    assert asyncio.run(client.summarize("some text")) == "ok"
    assert asyncio.run(client.critique("some text")) == "ok"
    assert [m for m, _ in client.calls] == ["ask", "ask"]


def test_embeddings_optional_and_raise_by_default() -> None:
    # ScriptedClient supports embeddings...
    client = ScriptedClient("a")
    assert asyncio.run(client.embed("abc")) == [3.0]

    # ...but a minimal client that only implements ask does not.
    from agent_control_plane.clients.base import LLMClient, LLMMetadata

    class Minimal(LLMClient):
        name = "minimal"

        async def ask(self, prompt: str, *, system: str | None = None, **kwargs: object) -> str:
            return "x"

        def describe(self) -> LLMMetadata:
            return LLMMetadata(provider="x", model="x")

    with pytest.raises(LLMNotSupported):
        asyncio.run(Minimal().embed("abc"))


def test_describe_reports_metadata() -> None:
    meta = ScriptedClient("a").describe()
    assert meta.provider == "scripted"
    assert meta.supports_embeddings is True
