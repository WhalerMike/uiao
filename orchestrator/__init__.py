"""UIAO Compliance Orchestrator — Public API.

This module exports the high-level orchestration interface for chaining
the 4 planes of the UIAO compliance pipeline (SCuBA → IR → KSI → Evidence → OSCAL/POA&M).

Public exports
--------------
  orchestrate()     — Orchestrate a complete pipeline run with error handling
  PlaneResult       — Outcome of a single plane execution
  RunManifest       — Summary of a complete orchestrator run
  main()            — Typer CLI entry point
"""

from __future__ import annotations

from .orchestrator import PlaneResult, RunManifest, main, orchestrate

__all__ = [
    "orchestrate",
    "PlaneResult",
    "RunManifest",
    "main",
]
