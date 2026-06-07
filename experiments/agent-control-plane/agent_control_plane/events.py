"""Structured, injectable event log.

The original split traceability across ``logs/logger.py`` (a JSON-line file)
and ``memory/memory_store.py`` (a JSON state file), both imported directly.
This unifies them behind one :class:`EventSink` protocol so the orchestrator
depends on the *interface*, not a file path — an in-memory sink makes the
cooperative loop trivially testable.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Event:
    """A single traceable step in a cooperative cycle."""

    session_id: str
    task_id: str
    agent: str
    action: str
    status: str
    content: str = ""
    error: str = ""
    at: str = field(default_factory=_now)


@runtime_checkable
class EventSink(Protocol):
    """Anything that can record an :class:`Event`."""

    def emit(self, event: Event) -> None: ...


class InMemoryEventSink:
    """Collects events in a list (default; ideal for tests)."""

    def __init__(self) -> None:
        self.events: list[Event] = []

    def emit(self, event: Event) -> None:
        self.events.append(event)


class JsonlEventSink:
    """Appends each event as one JSON object per line."""

    def __init__(self, path: str) -> None:
        self._path = path

    def emit(self, event: Event) -> None:
        with open(self._path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(event)) + "\n")


__all__ = ["Event", "EventSink", "InMemoryEventSink", "JsonlEventSink"]
