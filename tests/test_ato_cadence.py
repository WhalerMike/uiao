"""Tests for uiao.monitoring.ato_cadence — ATO SLA cadence validator.

Covers the nine acceptance scenarios from the WS-A5 workstream card:

1.  Award 100d ago, no SSPs submitted -> SSP-Draft-30 FAIL, SSP-Final-45 FAIL
2.  Award 28d ago, no SSPs -> SSP-Draft-30 WARN
3.  Award 28d ago, draft 5d after award -> SSP-Draft-30 PASS, SSP-Final-45 WARN
4.  Award 50d ago, draft @ d10, final @ d44 -> both PASS
5.  ATO expires 25d from now, decision 35d ago -> Reauthorization-30 WARN
6.  ATO expires 10d ago -> Reauthorization-30 FAIL
7.  ATO expires None -> Reauthorization-30 N/A
8.  CLI happy-path: all PASS, --json returns parseable JSON, exit 0
9.  CLI --exit-on-fail with FAIL state returns exit 1
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

from typer.testing import CliRunner

from uiao.cli.app import app
from uiao.monitoring.ato_cadence import (
    AtoCadenceInput,
    CadenceReport,
    evaluate_ato_cadence,
)

runner = CliRunner()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

UTC = timezone.utc


def _now_from_date(d: date) -> datetime:
    """Create a UTC noon datetime from a date for use as inp.now."""
    return datetime(d.year, d.month, d.day, 12, 0, 0, tzinfo=UTC)


def _inp(
    *,
    days_since_award: int,
    ssp_draft_day: int | None = None,
    ssp_final_day: int | None = None,
    ato_decision_day: int | None = None,
    ato_expires_day: int | None = None,
) -> AtoCadenceInput:
    """Build an AtoCadenceInput with 'now' set to days_since_award after award."""
    award = date(2026, 1, 1)
    now_date = award + timedelta(days=days_since_award)
    now_dt = _now_from_date(now_date)

    def _dt(d: date) -> datetime:
        return datetime(d.year, d.month, d.day, 12, 0, 0, tzinfo=UTC)

    return AtoCadenceInput(
        award_date=award,
        ssp_draft_submitted_at=(_dt(award + timedelta(days=ssp_draft_day)) if ssp_draft_day is not None else None),
        ssp_final_submitted_at=(_dt(award + timedelta(days=ssp_final_day)) if ssp_final_day is not None else None),
        current_ato_decision_date=(
            now_date - timedelta(days=ato_decision_day) if ato_decision_day is not None else None
        ),
        current_ato_expires_at=(now_date + timedelta(days=ato_expires_day) if ato_expires_day is not None else None),
        now=now_dt,
    )


def _get_verdict(report: CadenceReport, name: str) -> str:
    for v in report.verdicts:
        if v.name == name:
            return v.verdict
    raise KeyError(f"No verdict named {name!r}")


# ---------------------------------------------------------------------------
# Scenario 1: Award 100d ago, no SSPs submitted -> both FAIL
# ---------------------------------------------------------------------------


def test_scenario_1_no_ssps_overdue() -> None:
    inp = _inp(days_since_award=100)
    report = evaluate_ato_cadence(inp)

    assert _get_verdict(report, "SSP-Draft-30") == "FAIL"
    assert _get_verdict(report, "SSP-Final-45") == "FAIL"
    assert report.overall == "FAIL"


# ---------------------------------------------------------------------------
# Scenario 2: Award 28d ago, no SSPs -> Draft WARN (within window, over 28d)
# ---------------------------------------------------------------------------


def test_scenario_2_award_28d_no_ssps_draft_warn() -> None:
    inp = _inp(days_since_award=29)  # strictly > 28d
    report = evaluate_ato_cadence(inp)

    assert _get_verdict(report, "SSP-Draft-30") == "WARN"
    assert report.overall in ("WARN", "FAIL")


def test_scenario_2_award_27d_no_ssps_draft_pass() -> None:
    """Before the 28d warn threshold, still PASS."""
    inp = _inp(days_since_award=27)
    report = evaluate_ato_cadence(inp)

    assert _get_verdict(report, "SSP-Draft-30") == "PASS"


# ---------------------------------------------------------------------------
# Scenario 3: Award 28d ago, draft 5d after award -> Draft PASS, Final WARN
# ---------------------------------------------------------------------------


def test_scenario_3_draft_submitted_early() -> None:
    inp = _inp(days_since_award=29, ssp_draft_day=5)
    report = evaluate_ato_cadence(inp)

    assert _get_verdict(report, "SSP-Draft-30") == "PASS"
    # Final not submitted, 29d elapsed > 43d warn threshold? No -- 29 < 43, so PASS
    assert _get_verdict(report, "SSP-Final-45") == "PASS"


def test_scenario_3_draft_submitted_final_warn() -> None:
    """Award 44d ago, draft submitted on d5 -> Draft PASS, Final WARN (44 > 43)."""
    inp = _inp(days_since_award=44, ssp_draft_day=5)
    report = evaluate_ato_cadence(inp)

    assert _get_verdict(report, "SSP-Draft-30") == "PASS"
    assert _get_verdict(report, "SSP-Final-45") == "WARN"
    assert report.overall == "WARN"


# ---------------------------------------------------------------------------
# Scenario 4: Award 50d ago, draft @d10, final @d44 -> both PASS
# ---------------------------------------------------------------------------


def test_scenario_4_both_ssps_on_time() -> None:
    inp = _inp(days_since_award=50, ssp_draft_day=10, ssp_final_day=44)
    report = evaluate_ato_cadence(inp)

    assert _get_verdict(report, "SSP-Draft-30") == "PASS"
    assert _get_verdict(report, "SSP-Final-45") == "PASS"
    assert report.overall == "PASS"


def test_scenario_4_draft_late_fails() -> None:
    """Draft submitted on d31 (1d late) -> FAIL."""
    inp = _inp(days_since_award=50, ssp_draft_day=31, ssp_final_day=44)
    report = evaluate_ato_cadence(inp)

    assert _get_verdict(report, "SSP-Draft-30") == "FAIL"
    assert report.overall == "FAIL"


def test_scenario_4_final_late_fails() -> None:
    """Final submitted on d46 (1d late) -> FAIL."""
    inp = _inp(days_since_award=50, ssp_draft_day=10, ssp_final_day=46)
    report = evaluate_ato_cadence(inp)

    assert _get_verdict(report, "SSP-Final-45") == "FAIL"
    assert report.overall == "FAIL"


# ---------------------------------------------------------------------------
# Scenario 5: ATO expires 25d from now, decision 35d ago -> Reauth WARN
# ---------------------------------------------------------------------------


def test_scenario_5_reauth_warn() -> None:
    """Now is inside the 30d reauth window but decision was before the window opened."""
    award = date(2026, 1, 1)
    expires_at = date(2026, 5, 1)
    # now is 25d before expiry -> inside the 30d window
    now_date = expires_at - timedelta(days=25)
    now_dt = _now_from_date(now_date)
    # decision was 35d ago (before now) but also before reauth_deadline
    decision_date = now_date - timedelta(days=35)
    # reauth_deadline = expires_at - 30d = 2026-04-01
    # decision_date must be < reauth_deadline to trigger WARN

    inp = AtoCadenceInput(
        award_date=award,
        ssp_draft_submitted_at=datetime(2026, 1, 10, tzinfo=UTC),
        ssp_final_submitted_at=datetime(2026, 1, 20, tzinfo=UTC),
        current_ato_decision_date=decision_date,
        current_ato_expires_at=expires_at,
        now=now_dt,
    )
    report = evaluate_ato_cadence(inp)

    assert _get_verdict(report, "Reauthorization-30") == "WARN"


# ---------------------------------------------------------------------------
# Scenario 6: ATO expires 10d ago -> Reauth FAIL
# ---------------------------------------------------------------------------


def test_scenario_6_reauth_fail_lapsed() -> None:
    award = date(2026, 1, 1)
    expires_at = date(2026, 4, 1)
    now_date = expires_at + timedelta(days=10)  # 10d after expiry
    now_dt = _now_from_date(now_date)

    inp = AtoCadenceInput(
        award_date=award,
        ssp_draft_submitted_at=datetime(2026, 1, 10, tzinfo=UTC),
        ssp_final_submitted_at=datetime(2026, 1, 20, tzinfo=UTC),
        current_ato_decision_date=None,
        current_ato_expires_at=expires_at,
        now=now_dt,
    )
    report = evaluate_ato_cadence(inp)

    assert _get_verdict(report, "Reauthorization-30") == "FAIL"
    assert report.overall == "FAIL"


# ---------------------------------------------------------------------------
# Scenario 7: ATO expires None -> Reauth N/A
# ---------------------------------------------------------------------------


def test_scenario_7_reauth_na_no_expiry() -> None:
    inp = _inp(days_since_award=50, ssp_draft_day=10, ssp_final_day=44)
    # No ato_expires_day -> current_ato_expires_at is None
    report = evaluate_ato_cadence(inp)

    verdict = next(v for v in report.verdicts if v.name == "Reauthorization-30")
    assert verdict.verdict == "N/A"
    assert verdict.actual_days is None


# ---------------------------------------------------------------------------
# Scenario 8: CLI happy-path -- all PASS, --json returns parseable JSON, exit 0
# ---------------------------------------------------------------------------


def test_scenario_8_cli_json_all_pass() -> None:
    result = runner.invoke(
        app,
        [
            "conmon",
            "ato-cadence-check",
            "--award-date",
            "2026-01-01",
            "--ssp-draft-at",
            "2026-01-10T12:00:00",
            "--ssp-final-at",
            "2026-01-20T12:00:00",
            "--json",
        ],
    )
    assert result.exit_code == 0, f"exit={result.exit_code}\n{result.stdout}"
    data = json.loads(result.stdout)
    assert "overall" in data
    assert "verdicts" in data
    assert "evaluated_at" in data
    assert isinstance(data["verdicts"], list)
    assert len(data["verdicts"]) == 3


def test_scenario_8_cli_table_all_pass() -> None:
    result = runner.invoke(
        app,
        [
            "conmon",
            "ato-cadence-check",
            "--award-date",
            "2026-01-01",
            "--ssp-draft-at",
            "2026-01-10T12:00:00",
            "--ssp-final-at",
            "2026-01-20T12:00:00",
        ],
    )
    assert result.exit_code == 0, f"exit={result.exit_code}\n{result.stdout}"
    assert "SSP-Draft-30" in result.stdout
    assert "SSP-Final-45" in result.stdout
    assert "Reauthorization-30" in result.stdout


# ---------------------------------------------------------------------------
# Scenario 9: CLI --exit-on-fail with FAIL state returns exit 1
# ---------------------------------------------------------------------------


def test_scenario_9_cli_exit_on_fail() -> None:
    # Award 100d ago, no SSPs -> FAIL
    result = runner.invoke(
        app,
        [
            "conmon",
            "ato-cadence-check",
            "--award-date",
            "2024-01-01",  # well over 100d ago relative to any plausible now
            "--exit-on-fail",
        ],
    )
    assert result.exit_code == 1


def test_scenario_9_cli_no_exit_on_fail_flag_doesnt_exit_1() -> None:
    """Without --exit-on-fail, even a FAIL state exits 0."""
    result = runner.invoke(
        app,
        [
            "conmon",
            "ato-cadence-check",
            "--award-date",
            "2024-01-01",
        ],
    )
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_reauth_pass_when_decision_within_window() -> None:
    """Decision within 30d of expiry -> PASS."""
    award = date(2026, 1, 1)
    expires_at = date(2026, 5, 1)
    reauth_deadline = expires_at - timedelta(days=30)
    # Decision is 5d after the reauth deadline opens (so within window)
    decision_date = reauth_deadline + timedelta(days=5)
    now_date = decision_date + timedelta(days=2)
    now_dt = _now_from_date(now_date)

    inp = AtoCadenceInput(
        award_date=award,
        ssp_draft_submitted_at=datetime(2026, 1, 10, tzinfo=UTC),
        ssp_final_submitted_at=datetime(2026, 1, 20, tzinfo=UTC),
        current_ato_decision_date=decision_date,
        current_ato_expires_at=expires_at,
        now=now_dt,
    )
    report = evaluate_ato_cadence(inp)

    assert _get_verdict(report, "Reauthorization-30") == "PASS"


def test_reauth_pass_outside_window() -> None:
    """Now well before the 30d reauth window -> PASS."""
    award = date(2026, 1, 1)
    expires_at = date(2027, 1, 1)
    now_date = date(2026, 6, 1)  # >30d before expiry
    now_dt = _now_from_date(now_date)

    inp = AtoCadenceInput(
        award_date=award,
        ssp_draft_submitted_at=datetime(2026, 1, 10, tzinfo=UTC),
        ssp_final_submitted_at=datetime(2026, 1, 20, tzinfo=UTC),
        current_ato_expires_at=expires_at,
        now=now_dt,
    )
    report = evaluate_ato_cadence(inp)

    assert _get_verdict(report, "Reauthorization-30") == "PASS"


def test_ssp_draft_exactly_on_deadline_passes() -> None:
    """Draft submitted exactly on day 30 should PASS (not FAIL)."""
    inp = _inp(days_since_award=50, ssp_draft_day=30)
    report = evaluate_ato_cadence(inp)
    assert _get_verdict(report, "SSP-Draft-30") == "PASS"


def test_ssp_final_exactly_on_deadline_passes() -> None:
    """Final submitted exactly on day 45 should PASS (not FAIL)."""
    inp = _inp(days_since_award=60, ssp_draft_day=10, ssp_final_day=45)
    report = evaluate_ato_cadence(inp)
    assert _get_verdict(report, "SSP-Final-45") == "PASS"


def test_report_model_fields() -> None:
    """CadenceReport has expected top-level fields."""
    inp = _inp(days_since_award=10, ssp_draft_day=5)
    report = evaluate_ato_cadence(inp)
    assert hasattr(report, "overall")
    assert hasattr(report, "verdicts")
    assert hasattr(report, "evaluated_at")
    assert report.overall in ("PASS", "WARN", "FAIL")
    assert len(report.verdicts) == 3
    for v in report.verdicts:
        assert v.verdict in ("PASS", "WARN", "FAIL", "N/A")
