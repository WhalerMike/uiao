"""End-to-end tests for the cooperative orchestrator (fully offline)."""

from __future__ import annotations

import asyncio

import pytest
from agent_control_plane.checkpoint import CallbackCheckpoint, Decision
from agent_control_plane.clients import ScriptedClient
from agent_control_plane.events import InMemoryEventSink
from agent_control_plane.orchestrator import OrchestrationError, Orchestrator
from agent_control_plane.routing import Capability, Router


def _build(checkpoint=None, fail_executor: bool = False):
    reasoner = ScriptedClient("reasoner", default="PLAN")
    executor = ScriptedClient("executor", default="DONE", fail=fail_executor)
    synthesizer = reasoner
    router = Router(
        {
            Capability.REASON: "reasoner",
            Capability.EXECUTE: "executor",
            Capability.SYNTHESIZE: "reasoner",
        }
    )
    events = InMemoryEventSink()
    orch = Orchestrator(
        clients={"reasoner": reasoner, "executor": executor, "synthesizer": synthesizer},
        router=router,
        events=events,
        checkpoint=checkpoint,
    )
    return orch, events


def test_happy_path_runs_all_three_stages() -> None:
    orch, events = _build()
    result = asyncio.run(orch.run_cycle("do the thing"))

    assert result.approved is True
    assert result.halted_stage is None
    assert result.reasoning == "PLAN"
    assert result.execution == "DONE"
    assert result.synthesis  # synthesize routes through summarize -> ask

    actions = [(e.agent, e.action, e.status) for e in events.events]
    assert actions == [
        ("reasoner", "reason", "success"),
        ("human", "checkpoint", "approved"),
        ("executor", "execute", "success"),
        ("reasoner", "synthesize", "success"),
    ]


def test_rejected_checkpoint_halts_before_execution() -> None:
    reject = CallbackCheckpoint(lambda stage, payload: Decision(approved=False, note="nope"))
    orch, events = _build(checkpoint=reject)
    result = asyncio.run(orch.run_cycle("do the thing"))

    assert result.approved is False
    assert result.halted_stage == "plan"
    assert result.execution == ""
    assert result.synthesis == ""
    actions = [(e.agent, e.action, e.status) for e in events.events]
    assert actions == [
        ("reasoner", "reason", "success"),
        ("human", "checkpoint", "rejected"),
    ]


def test_async_checkpoint_callback_is_awaited() -> None:
    async def approve(stage: str, payload: str) -> Decision:
        return Decision(approved=True, note="async-ok")

    orch, events = _build(checkpoint=CallbackCheckpoint(approve))
    result = asyncio.run(orch.run_cycle("do the thing"))
    assert result.approved is True
    assert any(e.action == "execute" for e in events.events)


def test_client_failure_raises_orchestration_error_and_logs_it() -> None:
    orch, events = _build(fail_executor=True)
    with pytest.raises(OrchestrationError):
        asyncio.run(orch.run_cycle("do the thing"))

    error_events = [e for e in events.events if e.status == "error"]
    assert len(error_events) == 1
    assert error_events[0].agent == "executor"
    assert error_events[0].action == "execute"


def test_router_pointing_at_unknown_agent_fails_fast() -> None:
    router = Router({Capability.REASON: "ghost"})
    with pytest.raises(OrchestrationError):
        Orchestrator(clients={"real": ScriptedClient("real")}, router=router)
