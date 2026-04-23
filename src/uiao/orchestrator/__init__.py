"""UIAO Compliance Orchestrator — Public API.

Two layers, one module:

1. **Data-flow orchestration** (``orchestrator.py``) — chain the 4 planes of
   a single compliance pipeline run: SCuBA → IR → KSI → Evidence → OSCAL/POA&M.

2. **Scheduler** (``scheduler.py``) — UIAO_100's "schedule + dispatch"
   responsibility. Reads the canonical adapter registry, invokes each
   registered adapter's ``collect_evidence()`` + ``detect_drift()``, and
   persists a deterministic manifest per run. Routed to the evidence graph
   (UIAO_113, WIP) and drift engine (UIAO_016) for downstream consumption.

Public exports
--------------
Data flow:
  orchestrate()               — chain the 4 planes of one pipeline run
  PlaneResult                 — outcome of a single plane execution
  RunManifest                 — summary of one pipeline run
  main()                      — Typer CLI entry point for the 4-plane runner

Scheduler:
  OrchestratorScheduler       — adapter-registry dispatcher
  AdapterRun                  — per-adapter outcome in a scheduler run
  ScheduleRunManifest         — full scheduler-run manifest
"""

from __future__ import annotations

from .orchestrator import PlaneResult, RunManifest, main, orchestrate
from .scheduler import AdapterRun, OrchestratorScheduler, ScheduleRunManifest

__all__ = [
    "orchestrate",
    "PlaneResult",
    "RunManifest",
    "main",
    "OrchestratorScheduler",
    "AdapterRun",
    "ScheduleRunManifest",
]
