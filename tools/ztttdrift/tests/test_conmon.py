"""Continuous monitoring: history ledger, pillar trend, and SLA aging."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from ztttdrift import (
    History,
    SlaStatus,
    build_report,
    load_exceptions,
    load_run,
    pillar_scores,
    record_run,
    sla_findings,
    tier_for_gap,
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
    # ZT.DV.01 is below target in both runs -> first seen in April.
    assert h.first_seen("ZT.DV.01") == APR
    # ZT.ID.01 first drops below target in the July run.
    assert h.first_seen("ZT.ID.01") == JUL
    # An item that never fell below target has no first-seen.
    assert h.first_seen("ZT.DT.01") is None


def test_persist_roundtrip(tmp_path: Path) -> None:
    h = _history()
    p = tmp_path / "ledger.jsonl"
    h.save(p)
    reloaded = History.load(p)
    assert [e.as_of for e in reloaded.entries] == [APR, JUL]
    assert reloaded.first_seen("ZT.DV.01") == APR
    assert reloaded.latest.counts["actionable_total"] == 3
    assert reloaded.latest.pillar_scores == h.latest.pillar_scores


def test_pillar_scores_use_documented_stage_mapping() -> None:
    # traditional=0, initial=1, advanced=2, optimal=3, averaged per pillar.
    scores = pillar_scores(load_run(FIXTURES / "run_current.json"))
    assert scores["Identity"] == 1.5  # (initial 1 + advanced 2) / 2
    assert scores["Networks"] == 0.0  # traditional
    assert scores["Data"] == 2.5  # (optimal 3 + advanced 2) / 2
    assert scores["Cross-Cutting"] == 1.0


def test_sla_tier_comes_from_stage_gap() -> None:
    assert tier_for_gap(2) == "high"  # e.g. traditional under an advanced target
    assert tier_for_gap(3) == "high"
    assert tier_for_gap(1) == "moderate"
    assert tier_for_gap(0) == "low"


def test_sla_overdue_for_aged_finding() -> None:
    # ZT.DV.01 (gap 1 -> moderate, 90-day window) has been open since April;
    # by July it is ~91 days old -> overdue.
    sla = {s.item_id: s for s in sla_findings(_history(), as_of=JUL)}
    aged = sla["ZT.DV.01"]
    assert aged.tier == "moderate"
    assert aged.window_days == 90
    assert aged.age_days >= 90
    assert aged.status is SlaStatus.OVERDUE


def test_sla_on_track_for_new_finding() -> None:
    sla = {s.item_id: s for s in sla_findings(_history(), as_of=JUL)}
    fresh = sla["ZT.ID.01"]  # first below target in July -> age 0
    assert fresh.age_days == 0
    assert fresh.status is SlaStatus.ON_TRACK


def test_governed_exceptions_are_not_aged() -> None:
    # ZT.NW.01 is a governed exception -> excluded from SLA aging.
    ids = {s.item_id for s in sla_findings(_history(), as_of=JUL)}
    assert "ZT.NW.01" not in ids


def test_custom_sla_window_changes_status() -> None:
    windows = {"high": 365, "moderate": 365, "low": 365}
    sla = {s.item_id: s for s in sla_findings(_history(), as_of=JUL, windows=windows)}
    assert sla["ZT.DV.01"].status is not SlaStatus.OVERDUE


def test_report_trend_and_breach() -> None:
    report = build_report(_history(), as_of=JUL)
    assert report.period_start == APR
    assert report.period_end == JUL
    # Newly actionable in July.
    assert "ZT.ID.01" in report.new_actionable
    assert "ZT.CC.01" in report.new_actionable
    # ZT.ID.02 was actionable in April (initial, no acceptance) and progressed.
    assert "ZT.ID.02" in report.resolved_actionable
    # Pillar trend carries score + delta: Networks improved on paper only
    # because ZT.NW.02 left scope; Applications rose initial->advanced.
    ap = report.pillar_trend["Applications and Workloads"]
    assert ap["score"] == 2.0 and ap["previous"] == 1.0 and ap["delta"] == 1.0
    # At least the aged moderate finding is an SLA breach.
    assert any(s.item_id == "ZT.DV.01" for s in report.overdue)
    assert not report.clean
    # Framework mapping is present (support, not certification).
    fa = report.framework_alignment()
    assert "CISA BOD 25-01" in fa and "NIST 800-53 CA-7" in fa and "NIST SP 800-137 (ISCM)" in fa


def test_report_is_deterministic_across_as_of() -> None:
    # Aging grows with as_of; the model never reads the wall clock itself.
    early = {s.item_id: s.age_days for s in sla_findings(_history(), as_of=date(2026, 4, 15))}
    late = {s.item_id: s.age_days for s in sla_findings(_history(), as_of=date(2026, 8, 1))}
    assert late["ZT.DV.01"] > early["ZT.DV.01"]
