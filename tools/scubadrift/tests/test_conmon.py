"""Continuous monitoring: history ledger, trend, and SLA aging."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from scubadrift import (
    History,
    SlaStatus,
    build_report,
    load_exceptions,
    load_run,
    record_run,
    sla_findings,
)

FIXTURES = Path(__file__).parent / "fixtures"
APR = date(2026, 4, 1)
JUL = date(2026, 7, 1)


def _history() -> History:
    """A two-period ledger: baseline (April) then current (July)."""
    acc = load_exceptions(FIXTURES / "exceptions.json")
    h = History()
    h.append(record_run(load_run(FIXTURES / "run_baseline.json"), acc, as_of=APR))
    h.append(record_run(load_run(FIXTURES / "run_current.json"), acc, as_of=JUL))
    return h


def test_history_orders_and_reports_first_seen() -> None:
    h = _history()
    assert [e.as_of for e in h.entries] == [APR, JUL]
    # AAD.5.4 fails in both runs -> first seen in April.
    assert h.first_seen("MS.AAD.5.4v1") == APR
    # AAD.1.1 first fails in the July run.
    assert h.first_seen("MS.AAD.1.1v1") == JUL
    # A policy that never failed has no first-seen.
    assert h.first_seen("MS.NOPE.9.9v9") is None


def test_persist_roundtrip(tmp_path: Path) -> None:
    h = _history()
    p = tmp_path / "ledger.jsonl"
    h.save(p)
    reloaded = History.load(p)
    assert [e.as_of for e in reloaded.entries] == [APR, JUL]
    assert reloaded.first_seen("MS.AAD.5.4v1") == APR
    assert reloaded.latest.counts["actionable_total"] == 3


def test_sla_overdue_for_aged_finding() -> None:
    # MS.AAD.5.4v1 (Shall -> High, 30-day window) has been failing since April;
    # by July it is ~91 days old -> overdue.
    sla = {s.policy_id: s for s in sla_findings(_history(), as_of=JUL)}
    aged = sla["MS.AAD.5.4v1"]
    assert aged.tier == "high"
    assert aged.window_days == 30
    assert aged.age_days >= 90
    assert aged.status is SlaStatus.OVERDUE


def test_sla_on_track_for_new_finding() -> None:
    sla = {s.policy_id: s for s in sla_findings(_history(), as_of=JUL)}
    fresh = sla["MS.AAD.1.1v1"]  # first seen July -> age 0
    assert fresh.age_days == 0
    assert fresh.status is SlaStatus.ON_TRACK


def test_governed_exceptions_are_not_aged() -> None:
    # MS.AAD.3.1v1 is a governed exception -> excluded from SLA aging.
    ids = {s.policy_id for s in sla_findings(_history(), as_of=JUL)}
    assert "MS.AAD.3.1v1" not in ids


def test_custom_sla_window_changes_status() -> None:
    # With a generous 365-day High window, the aged finding is no longer overdue.
    sla = {
        s.policy_id: s for s in sla_findings(_history(), as_of=JUL, windows={"high": 365, "moderate": 365, "low": 365})
    }
    assert sla["MS.AAD.5.4v1"].status is not SlaStatus.OVERDUE


def test_report_trend_and_breach() -> None:
    report = build_report(_history(), as_of=JUL)
    assert report.period_start == APR
    assert report.period_end == JUL
    # New actionable in July that were not actionable in April.
    assert "MS.AAD.1.1v1" in report.new_actionable
    assert "MS.EXO.1.1v1" in report.new_actionable
    # At least the aged Shall finding is an SLA breach.
    assert any(s.policy_id == "MS.AAD.5.4v1" for s in report.overdue)
    assert not report.clean
    # Framework mapping is present (support, not certification).
    fa = report.framework_alignment()
    assert "CISA BOD 25-01" in fa and "FedRAMP ConMon" in fa


def test_report_is_deterministic_across_as_of() -> None:
    # Aging grows with as_of; the model never reads the wall clock itself.
    early = {s.policy_id: s.age_days for s in sla_findings(_history(), as_of=date(2026, 4, 15))}
    late = {s.policy_id: s.age_days for s in sla_findings(_history(), as_of=date(2026, 8, 1))}
    assert late["MS.AAD.5.4v1"] > early["MS.AAD.5.4v1"]
