"""Continuous monitoring integration package.

Provides Sentinel telemetry hooks, event processing, and ongoing
authorization artifact generation for FedRAMP 20x Phase 2 ConMon.
"""

from __future__ import annotations

from uiao_impl.monitoring.event_processor import EventProcessor
from uiao_impl.monitoring.ongoing_auth import OngoingAuthGenerator
from uiao_impl.monitoring.sentinel_hook import SentinelHook

__all__ = ["SentinelHook", "EventProcessor", "OngoingAuthGenerator"]

