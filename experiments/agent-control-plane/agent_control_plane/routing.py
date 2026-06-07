"""Capability-based routing.

The original ``routing.py`` was a string ``if`` ladder hard-wired to two agent
names. This replaces it with an explicit capability map: the orchestrator asks
for a *capability* (reason, execute, …) and the router resolves it to an agent
name. Adding an agent is a config change, not a code change.
"""

from __future__ import annotations

from enum import Enum


class Capability(str, Enum):
    """What a step needs, independent of which agent provides it."""

    REASON = "reason"
    EXECUTE = "execute"
    SEARCH = "search"
    CRITIQUE = "critique"
    SYNTHESIZE = "synthesize"


class RoutingError(KeyError):
    """No agent is registered for the requested capability."""


class Router:
    """Resolves a :class:`Capability` to a registered agent name."""

    def __init__(self, mapping: dict[Capability, str]) -> None:
        self._map = dict(mapping)

    def agent_for(self, capability: Capability) -> str:
        try:
            return self._map[capability]
        except KeyError as exc:
            raise RoutingError(f"no agent registered for capability {capability.value!r}") from exc

    def capabilities(self) -> frozenset[Capability]:
        return frozenset(self._map)


__all__ = ["Capability", "Router", "RoutingError"]
