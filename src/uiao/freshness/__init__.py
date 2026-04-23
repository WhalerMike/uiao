"""UIAO freshness evaluators.

Two layers, one module:

1. ``engine`` — legacy evidence-level freshness for the SCuBA bundle path.
2. ``drift_semantic`` — DRIFT-SEMANTIC evaluator for UIAO_100 scheduler
   runs (roadmap §1.1). Per-adapter staleness windows declared in canon
   registries; emits DRIFT-SEMANTIC findings per UIAO_016.

Public exports focus on the DRIFT-SEMANTIC surface; legacy engine
functions remain importable from ``uiao.freshness.engine``.
"""

from __future__ import annotations

from .drift_semantic import (
    DEFAULT_SEVERITY,
    DEFAULT_WINDOW_HOURS,
    DEFAULT_WINDOW_HOURS_BY_FAMILY,
    DRIFT_TYPE,
    AdapterFreshnessPolicy,
    FreshnessFinding,
    drift_semantic_findings,
    evaluate_evidence_payload,
    evaluate_scheduler_run,
    load_adapter_windows,
    resolve_policy,
    summarize,
    write_findings,
)

__all__ = [
    "DEFAULT_SEVERITY",
    "DEFAULT_WINDOW_HOURS",
    "DEFAULT_WINDOW_HOURS_BY_FAMILY",
    "DRIFT_TYPE",
    "AdapterFreshnessPolicy",
    "FreshnessFinding",
    "drift_semantic_findings",
    "evaluate_evidence_payload",
    "evaluate_scheduler_run",
    "load_adapter_windows",
    "resolve_policy",
    "summarize",
    "write_findings",
]
