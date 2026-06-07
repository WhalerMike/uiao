"""agent_control_plane — a small, cooperative multi-LLM orchestrator.

A salvaged, rebuilt distillation of the original "Michael Control Plane"
Copilot code. It keeps the three ideas that were worth keeping — a
vendor-neutral client contract, a layered architecture, and a human arbiter —
and rebuilds them with async I/O, dependency injection, typed errors, and
tests.

See ``README.md`` for the charter and a runnable, offline demo
(``python -m agent_control_plane.demo``).
"""

from __future__ import annotations

from .checkpoint import AutoApprove, CallbackCheckpoint, Checkpoint, Decision
from .clients import (
    AzureOpenAIClient,
    LLMClient,
    LLMError,
    LLMMetadata,
    PerplexityClient,
    ScriptedClient,
)
from .events import Event, EventSink, InMemoryEventSink, JsonlEventSink
from .orchestrator import CycleResult, OrchestrationError, Orchestrator
from .routing import Capability, Router, RoutingError

__all__ = [
    # clients
    "LLMClient",
    "LLMMetadata",
    "LLMError",
    "AzureOpenAIClient",
    "PerplexityClient",
    "ScriptedClient",
    # routing
    "Capability",
    "Router",
    "RoutingError",
    # events
    "Event",
    "EventSink",
    "InMemoryEventSink",
    "JsonlEventSink",
    # checkpoint
    "Decision",
    "Checkpoint",
    "AutoApprove",
    "CallbackCheckpoint",
    # orchestrator
    "Orchestrator",
    "CycleResult",
    "OrchestrationError",
]
