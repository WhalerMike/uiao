"""Vendor-neutral LLM client contract.

This is the one genuinely load-bearing idea salvaged from the original
"Michael Control Plane" Copilot code: every provider implements the *same*
small surface, so the orchestration logic never depends on a concrete vendor.

Differences from the original ``llm_client.py``:

* **Async.** Every call is awaitable, so the orchestrator can fan out to
  several agents concurrently (the entire point of consensus / divergence,
  which the synchronous original could never actually do).
* **DRY defaults.** ``summarize`` and ``critique`` are implemented once here
  in terms of ``ask``; a concrete client only has to implement ``ask`` (and
  optionally ``embed``).
* **Typed errors.** Failures raise :class:`LLMError` subclasses instead of
  leaking ``requests``/``httpx`` exceptions, so the orchestrator can degrade
  one agent without aborting the whole cycle.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

_SUMMARIZE_PROMPT = "Summarize the following at systems altitude, highlighting load-bearing elements. Be concise.\n\n"
_CRITIQUE_PROMPT = (
    "Provide a structured critique of the following, focusing on invariants, "
    "boundary conditions, and architectural coherence.\n\n"
)


class LLMError(RuntimeError):
    """Base class for every error raised by a client."""


class LLMTransportError(LLMError):
    """The provider could not be reached, or returned an unusable response."""


class LLMNotSupported(LLMError):
    """The client does not implement the requested capability (e.g. embeddings)."""


@dataclass(frozen=True)
class LLMMetadata:
    """Static description of a client, used for logging and routing."""

    provider: str
    model: str
    supports_embeddings: bool = False
    extra: dict[str, str] = field(default_factory=dict)


class LLMClient(ABC):
    """A single cognitive engine.

    Concrete subclasses set :attr:`name` (the stable identifier the router and
    event log use) and implement :meth:`ask` and :meth:`describe`.
    """

    #: Stable short name, e.g. ``"azure-openai"`` or ``"perplexity"``.
    name: str = "llm"

    @abstractmethod
    async def ask(self, prompt: str, *, system: str | None = None, **kwargs: Any) -> str:
        """Answer a single prompt and return plain text."""

    async def summarize(self, text: str, **kwargs: Any) -> str:
        """Summarize ``text``. Default implementation routes through :meth:`ask`."""
        return await self.ask(_SUMMARIZE_PROMPT + text, **kwargs)

    async def critique(self, text: str, **kwargs: Any) -> str:
        """Critique ``text``. Default implementation routes through :meth:`ask`."""
        return await self.ask(_CRITIQUE_PROMPT + text, **kwargs)

    async def embed(self, text: str, **kwargs: Any) -> list[float]:
        """Return an embedding vector. Optional; raises unless overridden."""
        raise LLMNotSupported(f"{self.name} does not support embeddings")

    @abstractmethod
    def describe(self) -> LLMMetadata:
        """Return static metadata about this client."""


__all__ = [
    "LLMClient",
    "LLMMetadata",
    "LLMError",
    "LLMTransportError",
    "LLMNotSupported",
]
