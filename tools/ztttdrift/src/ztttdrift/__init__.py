"""ZTTTdrift — drift, exception-lifecycle, and conmon gating for Zero Trust maturity assessments.

A Zero Trust maturity self-assessment (Microsoft ZTTT, a CISA ZTMM v2.0
worksheet, or similar) emits a point-in-time maturity stage per assessed item.
It does not track run-to-run drift, the lifecycle of documented
risk-acceptances, or gate a pipeline. ZTTTdrift is a thin, tested layer that
adds exactly those three, standing on the assessment tool rather than
reimplementing it. Input is the versioned ``ztttdrift-input/1.0`` contract.

Public API::

    from ztttdrift import load_run, load_exceptions, triage, diff_runs, evaluate_gate
"""

from __future__ import annotations

__version__ = "0.1.0"

from .conmon import (
    DEFAULT_SLA_WINDOWS,
    ConMonReport,
    History,
    HistoryEntry,
    SlaFinding,
    SlaStatus,
    build_report,
    pillar_scores,
    record_run,
    sla_findings,
    tier_for_gap,
)
from .drift import DriftKind, DriftReport, diff_runs
from .gate import GateResult, evaluate_gate
from .models import DEFAULT_TARGET, PILLARS, MaturityItem, MaturityRun, RiskAcceptance, Stage
from .parser import SCHEMA, ParseError, load_exceptions, load_run, parse_run
from .triage import Disposition, TriageReport, triage

__all__ = [
    "__version__",
    "ConMonReport",
    "DEFAULT_SLA_WINDOWS",
    "DEFAULT_TARGET",
    "Disposition",
    "DriftKind",
    "DriftReport",
    "GateResult",
    "History",
    "HistoryEntry",
    "MaturityItem",
    "MaturityRun",
    "PILLARS",
    "ParseError",
    "RiskAcceptance",
    "SCHEMA",
    "SlaFinding",
    "SlaStatus",
    "Stage",
    "TriageReport",
    "build_report",
    "diff_runs",
    "evaluate_gate",
    "load_exceptions",
    "load_run",
    "parse_run",
    "pillar_scores",
    "record_run",
    "sla_findings",
    "tier_for_gap",
    "triage",
]
