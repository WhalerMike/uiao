"""The cooperative orchestrator.

Salvages the original ``orchestrator.py``'s reason -> execute -> synthesize
loop, but rebuilt on the patterns that make ``uiao.saas`` testable:

* **Dependency injection.** Clients, router, event sink, and checkpoint are
  all injected — no module-level globals, no hard imports of concrete clients.
* **Capability routing.** Steps ask the :class:`~.routing.Router` for a
  capability; which agent answers is configuration.
* **Typed degradation.** A client failure becomes an :class:`OrchestrationError`
  with an error event recorded, rather than an unhandled ``requests`` exception.
* **Human checkpoint.** The plan must clear the injected
  :class:`~.checkpoint.Checkpoint` before execution proceeds.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass

from .checkpoint import AutoApprove, Checkpoint
from .clients.base import LLMClient, LLMError
from .events import Event, EventSink, InMemoryEventSink
from .routing import Capability, Router

_REASON_PROMPT = (
    "You are operating within a cooperative, ego-free control plane. Analyze "
    "the following task at systems altitude and propose a concise execution "
    "plan.\n\nTask:\n{task}"
)
_EXECUTE_PROMPT = (
    "Execute or simulate the following plan as best you can. If execution is "
    "not possible, describe the concrete steps you would take.\n\nPlan:\n{plan}"
)
_SYNTH_PROMPT = (
    "Given the original task and the execution result, write a concise, "
    "executive-ready summary highlighting load-bearing outcomes and next "
    "steps.\n\nTask:\n{task}\n\nExecution result:\n{result}"
)


class OrchestrationError(RuntimeError):
    """A cooperative cycle could not complete."""


@dataclass
class CycleResult:
    """The outcome of one cooperative cycle."""

    session_id: str
    task_id: str
    reasoning: str = ""
    execution: str = ""
    synthesis: str = ""
    approved: bool = True
    halted_stage: str | None = None


class Orchestrator:
    """Coordinates a reason -> checkpoint -> execute -> synthesize cycle."""

    def __init__(
        self,
        *,
        clients: Mapping[str, LLMClient],
        router: Router,
        events: EventSink | None = None,
        checkpoint: Checkpoint | None = None,
    ) -> None:
        self._clients = dict(clients)
        self._router = router
        self._events = events if events is not None else InMemoryEventSink()
        self._checkpoint = checkpoint if checkpoint is not None else AutoApprove()

        # Fail fast: every routed capability must map to a known client.
        for capability in router.capabilities():
            name = router.agent_for(capability)
            if name not in self._clients:
                raise OrchestrationError(f"router points {capability.value!r} at unknown agent {name!r}")

    def _client(self, capability: Capability) -> LLMClient:
        return self._clients[self._router.agent_for(capability)]

    async def _step(
        self,
        capability: Capability,
        action: str,
        prompt: str,
        *,
        session_id: str,
        task_id: str,
        summarize: bool = False,
    ) -> str:
        client = self._client(capability)
        try:
            output = await (client.summarize(prompt) if summarize else client.ask(prompt))
        except LLMError as exc:
            self._events.emit(Event(session_id, task_id, client.name, action, "error", error=str(exc)))
            raise OrchestrationError(f"{client.name} failed during {action}: {exc}") from exc
        self._events.emit(Event(session_id, task_id, client.name, action, "success", content=output))
        return output

    async def run_cycle(self, task: str) -> CycleResult:
        """Run one cooperative cycle and return its :class:`CycleResult`."""
        session_id = str(uuid.uuid4())
        task_id = str(uuid.uuid4())
        result = CycleResult(session_id=session_id, task_id=task_id)

        result.reasoning = await self._step(
            Capability.REASON,
            "reason",
            _REASON_PROMPT.format(task=task),
            session_id=session_id,
            task_id=task_id,
        )

        decision = await self._checkpoint.review("plan", result.reasoning)
        self._events.emit(
            Event(
                session_id,
                task_id,
                "human",
                "checkpoint",
                "approved" if decision.approved else "rejected",
                content=decision.note,
            )
        )
        result.approved = decision.approved
        if not decision.approved:
            result.halted_stage = "plan"
            return result

        result.execution = await self._step(
            Capability.EXECUTE,
            "execute",
            _EXECUTE_PROMPT.format(plan=result.reasoning),
            session_id=session_id,
            task_id=task_id,
        )

        result.synthesis = await self._step(
            Capability.SYNTHESIZE,
            "synthesize",
            _SYNTH_PROMPT.format(task=task, result=result.execution),
            session_id=session_id,
            task_id=task_id,
            summarize=True,
        )
        return result


__all__ = ["Orchestrator", "CycleResult", "OrchestrationError"]
