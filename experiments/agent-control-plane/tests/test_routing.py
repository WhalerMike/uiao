"""Tests for capability-based routing."""

from __future__ import annotations

import pytest
from agent_control_plane.routing import Capability, Router, RoutingError


def test_agent_for_resolves_mapped_capability() -> None:
    router = Router({Capability.REASON: "copilot", Capability.EXECUTE: "perplexity"})
    assert router.agent_for(Capability.REASON) == "copilot"
    assert router.agent_for(Capability.EXECUTE) == "perplexity"


def test_unmapped_capability_raises_routing_error() -> None:
    router = Router({Capability.REASON: "copilot"})
    with pytest.raises(RoutingError):
        router.agent_for(Capability.EXECUTE)


def test_capabilities_reports_registered_set() -> None:
    router = Router({Capability.REASON: "a", Capability.SYNTHESIZE: "b"})
    assert router.capabilities() == frozenset({Capability.REASON, Capability.SYNTHESIZE})
