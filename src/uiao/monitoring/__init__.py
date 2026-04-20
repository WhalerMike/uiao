"""Continuous monitoring integration package.

Provides Sentinel telemetry hooks, event processing, and ongoing
authorization artifact generation for FedRAMP 20x Phase 2 ConMon.
"""

from __future__ import annotations

from uiao.monitoring.event_processor import EventProcessor
from uiao.monitoring.ongoing_auth import OngoingAuthGenerator
from uiao.monitoring.sentinel_hook import SentinelHook

__all__ = ["SentinelHook", "EventProcessor", "OngoingAuthGenerator"]

