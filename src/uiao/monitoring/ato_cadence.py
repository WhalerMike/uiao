"""uiao.monitoring.ato_cadence — ATO SLA cadence validator.

Enforces the SSP and reauthorization SLAs defined in UIAO_140 §4 (lines
63–75) and ADR-054 Q&A #44 / Consequences line 131:

* SSP-Draft-30  : Draft SSP submitted within 30 days of contract award.
* SSP-Final-45  : Final SSP submitted within 45 days of contract award.
* Reauthorization-30 : Reauthorization package submitted at least 30 days
  before the current ATO expires.

Usage::

    from datetime import date, datetime, timezone
    from uiao.monitoring.ato_cadence import AtoCadenceInput, evaluate_ato_cadence

    inp = AtoCadenceInput(
        award_date=date(2026, 1, 1),
        ssp_draft_submitted_at=datetime(2026, 1, 25, tzinfo=timezone.utc),
    )
    report = evaluate_ato_cadence(inp)
    print(report.overall)  # "PASS" | "WARN" | "FAIL"
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Input model
# ---------------------------------------------------------------------------


class AtoCadenceInput(BaseModel):
    """Input parameters for ATO cadence SLA evaluation."""

    award_date: date
    """Date of the qualifying contractual event (e.g., contract award)."""

    ssp_draft_submitted_at: Optional[datetime] = None
    """Datetime the draft SSP was submitted; None if not yet submitted."""

    ssp_final_submitted_at: Optional[datetime] = None
    """Datetime the final SSP was submitted; None if not yet submitted."""

    current_ato_decision_date: Optional[date] = None
    """Date of the most recent ATO authorization decision."""

    current_ato_expires_at: Optional[date] = None
    """Date the current ATO expires; None if no active ATO."""

    now: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    """Reference timestamp for evaluations; defaults to current UTC time."""


# ---------------------------------------------------------------------------
# Output models
# ---------------------------------------------------------------------------

VerdictLiteral = Literal["PASS", "WARN", "FAIL", "N/A"]
OverallLiteral = Literal["PASS", "WARN", "FAIL"]

_SEVERITY: dict[str, int] = {"FAIL": 3, "WARN": 2, "PASS": 1, "N/A": 0}


class CadenceVerdict(BaseModel):
    """Result for a single SLA check."""

    name: str
    """Machine-readable SLA name (e.g., 'SSP-Draft-30')."""

    threshold_days: int
    """SLA threshold in calendar days."""

    actual_days: Optional[int] = None
    """Elapsed days relevant to the check; None when not computable."""

    verdict: VerdictLiteral
    """Evaluation outcome."""

    message: str
    """Human-readable explanation of the verdict."""


class CadenceReport(BaseModel):
    """Aggregate result of all ATO cadence SLA checks."""

    overall: OverallLiteral
    """Worst-case verdict across all individual SLA checks."""

    verdicts: list[CadenceVerdict]
    """Per-SLA results in evaluation order."""

    evaluated_at: datetime
    """Timestamp at which the evaluation was performed (from inp.now)."""


# ---------------------------------------------------------------------------
# Evaluation logic
# ---------------------------------------------------------------------------


def _days_since(ref_date: date, now_date: date) -> int:
    """Return calendar days elapsed from ref_date to now_date."""
    return (now_date - ref_date).days


def _check_ssp_draft(inp: AtoCadenceInput) -> CadenceVerdict:
    """SSP-Draft-30: draft SSP must be submitted within 30 days of award."""
    threshold = 30
    warn_threshold = 28
    deadline: date = inp.award_date + timedelta(days=threshold)
    warn_date: date = inp.award_date + timedelta(days=warn_threshold)
    now_date: date = inp.now.date()

    if inp.ssp_draft_submitted_at is not None:
        submitted_date: date = inp.ssp_draft_submitted_at.date()
        actual = _days_since(inp.award_date, submitted_date)
        if submitted_date <= deadline:
            return CadenceVerdict(
                name="SSP-Draft-30",
                threshold_days=threshold,
                actual_days=actual,
                verdict="PASS",
                message=f"Draft SSP submitted on day {actual} (threshold: {threshold}d).",
            )
        else:
            return CadenceVerdict(
                name="SSP-Draft-30",
                threshold_days=threshold,
                actual_days=actual,
                verdict="FAIL",
                message=(
                    f"Draft SSP submitted on day {actual}, "
                    f"which is {actual - threshold}d past the {threshold}d deadline."
                ),
            )

    # Not submitted yet — evaluate based on elapsed time
    elapsed = _days_since(inp.award_date, now_date)
    if now_date > deadline:
        return CadenceVerdict(
            name="SSP-Draft-30",
            threshold_days=threshold,
            actual_days=elapsed,
            verdict="FAIL",
            message=(
                f"Draft SSP not submitted; {elapsed}d elapsed ({elapsed - threshold}d past the {threshold}d deadline)."
            ),
        )
    if now_date > warn_date:
        return CadenceVerdict(
            name="SSP-Draft-30",
            threshold_days=threshold,
            actual_days=elapsed,
            verdict="WARN",
            message=(
                f"Draft SSP not yet submitted; {elapsed}d elapsed "
                f"({threshold - elapsed}d remaining — submission overdue warning)."
            ),
        )
    return CadenceVerdict(
        name="SSP-Draft-30",
        threshold_days=threshold,
        actual_days=elapsed,
        verdict="PASS",
        message=(f"Draft SSP not yet submitted; {elapsed}d elapsed, {threshold - elapsed}d remaining — within window."),
    )


def _check_ssp_final(inp: AtoCadenceInput) -> CadenceVerdict:
    """SSP-Final-45: final SSP must be submitted within 45 days of award."""
    threshold = 45
    warn_threshold = 43
    deadline: date = inp.award_date + timedelta(days=threshold)
    warn_date: date = inp.award_date + timedelta(days=warn_threshold)
    now_date: date = inp.now.date()

    if inp.ssp_final_submitted_at is not None:
        submitted_date: date = inp.ssp_final_submitted_at.date()
        actual = _days_since(inp.award_date, submitted_date)
        if submitted_date <= deadline:
            return CadenceVerdict(
                name="SSP-Final-45",
                threshold_days=threshold,
                actual_days=actual,
                verdict="PASS",
                message=f"Final SSP submitted on day {actual} (threshold: {threshold}d).",
            )
        else:
            return CadenceVerdict(
                name="SSP-Final-45",
                threshold_days=threshold,
                actual_days=actual,
                verdict="FAIL",
                message=(
                    f"Final SSP submitted on day {actual}, "
                    f"which is {actual - threshold}d past the {threshold}d deadline."
                ),
            )

    # Not submitted yet
    elapsed = _days_since(inp.award_date, now_date)
    if now_date > deadline:
        return CadenceVerdict(
            name="SSP-Final-45",
            threshold_days=threshold,
            actual_days=elapsed,
            verdict="FAIL",
            message=(
                f"Final SSP not submitted; {elapsed}d elapsed ({elapsed - threshold}d past the {threshold}d deadline)."
            ),
        )
    if now_date > warn_date:
        return CadenceVerdict(
            name="SSP-Final-45",
            threshold_days=threshold,
            actual_days=elapsed,
            verdict="WARN",
            message=(
                f"Final SSP not yet submitted; {elapsed}d elapsed "
                f"({threshold - elapsed}d remaining — submission overdue warning)."
            ),
        )
    return CadenceVerdict(
        name="SSP-Final-45",
        threshold_days=threshold,
        actual_days=elapsed,
        verdict="PASS",
        message=(f"Final SSP not yet submitted; {elapsed}d elapsed, {threshold - elapsed}d remaining — within window."),
    )


def _check_reauthorization(inp: AtoCadenceInput) -> CadenceVerdict:
    """Reauthorization-30: reauth package due at least 30 days before ATO expiry."""
    threshold = 30

    if inp.current_ato_expires_at is None:
        return CadenceVerdict(
            name="Reauthorization-30",
            threshold_days=threshold,
            actual_days=None,
            verdict="N/A",
            message="No current ATO expiration date configured.",
        )

    expires_at: date = inp.current_ato_expires_at
    reauth_deadline: date = expires_at - timedelta(days=threshold)
    now_date: date = inp.now.date()

    # PASS: reauth decision already made within the reauth window
    if inp.current_ato_decision_date is not None:
        decision: date = inp.current_ato_decision_date
        if decision >= reauth_deadline:
            days_before = _days_since(decision, expires_at)
            return CadenceVerdict(
                name="Reauthorization-30",
                threshold_days=threshold,
                actual_days=days_before,
                verdict="PASS",
                message=(
                    f"ATO decision dated {decision} satisfies the "
                    f"{threshold}d pre-expiry reauthorization window "
                    f"(expires {expires_at})."
                ),
            )

    # FAIL: ATO has already lapsed (and no qualifying recent decision)
    if now_date >= expires_at:
        days_lapsed = _days_since(expires_at, now_date)
        return CadenceVerdict(
            name="Reauthorization-30",
            threshold_days=threshold,
            actual_days=days_lapsed,
            verdict="FAIL",
            message=(f"ATO lapsed {days_lapsed}d ago (expired {expires_at}); no reauthorization decision on record."),
        )

    # WARN: now is inside the 30-day reauth window but no decision yet
    if now_date >= reauth_deadline:
        days_remaining = _days_since(now_date, expires_at)
        return CadenceVerdict(
            name="Reauthorization-30",
            threshold_days=threshold,
            actual_days=days_remaining,
            verdict="WARN",
            message=(
                f"Inside reauthorization window: {days_remaining}d until ATO expires "
                f"({expires_at}); no reauthorization decision on record."
            ),
        )

    # PASS: not yet in the reauth window
    days_until_window = _days_since(now_date, reauth_deadline)
    return CadenceVerdict(
        name="Reauthorization-30",
        threshold_days=threshold,
        actual_days=days_until_window,
        verdict="PASS",
        message=(f"Reauthorization window opens in {days_until_window}d (ATO expires {expires_at})."),
    )


def _aggregate_overall(verdicts: list[CadenceVerdict]) -> OverallLiteral:
    """Return the worst-case severity across all verdicts, excluding N/A."""
    max_sev = max((_SEVERITY[v.verdict] for v in verdicts), default=0)
    if max_sev >= _SEVERITY["FAIL"]:
        return "FAIL"
    if max_sev >= _SEVERITY["WARN"]:
        return "WARN"
    return "PASS"


def evaluate_ato_cadence(inp: AtoCadenceInput) -> CadenceReport:
    """Evaluate all ATO cadence SLAs and return a :class:`CadenceReport`.

    Args:
        inp: Input parameters describing the ATO timeline.

    Returns:
        A :class:`CadenceReport` with per-SLA :class:`CadenceVerdict` entries
        and an aggregate ``overall`` result.
    """
    verdicts: list[CadenceVerdict] = [
        _check_ssp_draft(inp),
        _check_ssp_final(inp),
        _check_reauthorization(inp),
    ]
    return CadenceReport(
        overall=_aggregate_overall(verdicts),
        verdicts=verdicts,
        evaluated_at=inp.now,
    )
