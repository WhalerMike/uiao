"""Human-in-the-loop checkpoint.

Salvages the "Michael = final arbiter" invariant and ``human_checkpoint.py``
as a real, injected boundary rather than prose. The orchestrator pauses at
defined stages and asks a :class:`Checkpoint` for a :class:`Decision`; the
default auto-approves (for unattended/test runs), but a real deployment
injects one backed by a human.
"""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class Decision:
    """The arbiter's verdict on a proposed stage."""

    approved: bool
    note: str = ""


@runtime_checkable
class Checkpoint(Protocol):
    """A boundary the orchestrator must clear before proceeding."""

    async def review(self, stage: str, payload: str) -> Decision: ...


class AutoApprove:
    """Approves everything — for unattended and test runs."""

    async def review(self, stage: str, payload: str) -> Decision:
        return Decision(approved=True, note="auto-approved")


# A callback may be sync or async; both are accepted.
_CallbackResult = Decision | Awaitable[Decision]


class CallbackCheckpoint:
    """Wraps a user-supplied callable as a :class:`Checkpoint`."""

    def __init__(self, callback: Callable[[str, str], _CallbackResult]) -> None:
        self._callback = callback

    async def review(self, stage: str, payload: str) -> Decision:
        result = self._callback(stage, payload)
        if inspect.isawaitable(result):
            return await result
        return result


__all__ = ["Decision", "Checkpoint", "AutoApprove", "CallbackCheckpoint"]
