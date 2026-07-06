"""Conmon gate — turn a triage (and optional drift) into a pass/fail + exit code.

This is what a continuous-monitoring pipeline calls. The gate fails (exit
non-zero) on any of:

* ``actionable_new_drift`` — a below-target item with no acceptance on file;
* ``lapsed_acceptance`` — a below-target item whose acceptance has expired;
* any **regression below target** — when a baseline run is supplied, an item
  whose stage decreased *and* landed below its effective target fails the gate
  even if an in-date acceptance covers it: the acceptance was granted against
  a prior posture, and a fresh regression is new information the approver has
  not seen.

Governed, in-date exceptions (that did not just regress) never fail the gate —
that is the whole point of ZTTTdrift: separate the noise you have already
governed from the signal you must act on. A regression that still meets target
is reported but is not, by itself, gate-failing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .drift import DriftItem, diff_runs
from .models import DEFAULT_TARGET, MaturityRun, RiskAcceptance, Stage
from .triage import TriageReport, triage

#: Conventional exit codes for CI.
EXIT_PASS = 0
EXIT_ACTION_REQUIRED = 1


@dataclass(frozen=True)
class GateResult:
    passed: bool
    report: TriageReport
    regressions_below_target: tuple[DriftItem, ...] = ()

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
            f"{s['actionable_new_drift']} new drift, {s['lapsed_acceptance']} lapsed acceptance; "
            f"{len(self.regressions_below_target)} regression(s) below target"
        )


def evaluate_gate(
    run: MaturityRun,
    acceptances: list[RiskAcceptance],
    *,
    as_of: date,
    target: Stage = DEFAULT_TARGET,
    baseline: MaturityRun | None = None,
) -> GateResult:
    report = triage(run, acceptances, as_of=as_of, target=target)
    regressions: tuple[DriftItem, ...] = ()
    if baseline is not None:
        regressions = diff_runs(baseline, run, target=target).regressions_below_target
    passed = report.clean and not regressions
    return GateResult(passed=passed, report=report, regressions_below_target=regressions)
