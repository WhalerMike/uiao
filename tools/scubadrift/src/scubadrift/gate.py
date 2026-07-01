"""Conmon gate — turn a triage report into a pass/fail decision + exit code.

This is what a continuous-monitoring pipeline calls. The gate passes (exit 0)
only when every ScubaGear failure is a governed, in-date exception; it fails
(exit non-zero) the moment there is new drift or a lapsed acceptance. The
gate deliberately does *not* fail on validly-accepted exceptions — that is the
whole point of ScubaDrift: separate the noise you have already governed from
the signal you must act on.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .models import RiskAcceptance, ScubaRun
from .triage import TriageReport, triage

#: Conventional exit codes for CI.
EXIT_PASS = 0
EXIT_ACTION_REQUIRED = 1


@dataclass(frozen=True)
class GateResult:
    passed: bool
    report: TriageReport

    @property
    def exit_code(self) -> int:
        return EXIT_PASS if self.passed else EXIT_ACTION_REQUIRED

    def headline(self) -> str:
        s = self.report.summary()
        if self.passed:
            governed = s["governed_exception"]
            tail = f" ({governed} governed exception(s))" if governed else ""
            return f"PASS — no actionable drift{tail}"
        return (
            f"FAIL — {s['actionable_total']} actionable finding(s): "
            f"{s['actionable_new_drift']} new drift, {s['lapsed_acceptance']} lapsed acceptance"
        )


def evaluate_gate(
    run: ScubaRun,
    acceptances: list[RiskAcceptance],
    *,
    as_of: date,
    include_warnings: bool = False,
) -> GateResult:
    report = triage(run, acceptances, as_of=as_of, include_warnings=include_warnings)
    return GateResult(passed=report.clean, report=report)
