"""ScubaDrift — drift, exception-lifecycle, and conmon gating for CISA ScubaGear.

ScubaGear assesses a Microsoft 365 tenant against the CISA SCuBA baselines and
emits a point-in-time verdict per policy. It does not track run-to-run drift,
the lifecycle of documented risk-acceptances, or gate a pipeline. ScubaDrift is
a thin, tested layer that adds exactly those three, standing on the sanctioned
tool rather than reimplementing it.

Public API::

    from scubadrift import load_run, load_exceptions, triage, diff_runs, evaluate_gate
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
    record_run,
    sla_findings,
)
from .drift import DriftKind, DriftReport, diff_runs
from .gate import GateResult, evaluate_gate
from .models import PolicyResult, Result, RiskAcceptance, ScubaRun
from .parser import ParseError, load_exceptions, load_run, parse_run
from .triage import Disposition, TriageReport, triage

__all__ = [
    "__version__",
    "ConMonReport",
    "DEFAULT_SLA_WINDOWS",
    "Disposition",
    "DriftKind",
    "DriftReport",
    "GateResult",
    "History",
    "HistoryEntry",
    "ParseError",
    "PolicyResult",
    "Result",
    "RiskAcceptance",
    "ScubaRun",
    "SlaFinding",
    "SlaStatus",
    "TriageReport",
    "build_report",
    "diff_runs",
    "evaluate_gate",
    "load_exceptions",
    "load_run",
    "parse_run",
    "record_run",
    "sla_findings",
    "triage",
]
