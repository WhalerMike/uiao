"""Triage: the new-drift / lapsed / governed split on an ordinal stage scale."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from ztttdrift import Disposition, RiskAcceptance, Stage, load_exceptions, load_run, triage

FIXTURES = Path(__file__).parent / "fixtures"
AS_OF = date(2026, 7, 1)  # fixed so expiry math never drifts with the wall clock


def _report(as_of: date = AS_OF, target: Stage = Stage.ADVANCED):
    run = load_run(FIXTURES / "run_current.json")
    acc = load_exceptions(FIXTURES / "exceptions.json")
    return triage(run, acc, as_of=as_of, target=target)


def test_dispositions_are_correct() -> None:
    report = _report()
    disp = {t.item.item_id: t.disposition for t in report.triaged}
    assert disp["ZT.ID.01"] is Disposition.ACTIONABLE_NEW_DRIFT  # initial < advanced, no acceptance
    assert disp["ZT.CC.01"] is Disposition.ACTIONABLE_NEW_DRIFT  # initial < advanced, no acceptance
    assert disp["ZT.DV.01"] is Disposition.LAPSED_ACCEPTANCE  # acceptance expired 2026-01-15
    assert disp["ZT.NW.01"] is Disposition.GOVERNED_EXCEPTION  # accepted until 2026-12-31


def test_only_below_target_items_are_triaged() -> None:
    report = _report()
    ids = {t.item.item_id for t in report.triaged}
    assert "ZT.ID.02" not in ids  # advanced meets target
    assert "ZT.DT.02" not in ids  # advanced meets target
    assert "ZT.AP.01" not in ids  # advanced meets target


def test_per_item_target_stage_overrides_global() -> None:
    # ZT.DT.01 sits at optimal with an explicit optimal target -> not failing.
    report = _report()
    assert "ZT.DT.01" not in {t.item.item_id for t in report.triaged}
    # With the global target raised to optimal, the merely-advanced items fail too.
    raised = _report(target=Stage.OPTIMAL)
    ids = {t.item.item_id for t in raised.triaged}
    assert {"ZT.ID.02", "ZT.DT.02", "ZT.AP.01"} <= ids
    assert "ZT.DT.01" not in ids  # already optimal


def test_summary_counts() -> None:
    s = _report().summary()
    assert s["failing_total"] == 4
    assert s["actionable_new_drift"] == 2
    assert s["lapsed_acceptance"] == 1
    assert s["governed_exception"] == 1
    assert s["actionable_total"] == 3
    assert s["retirable_acceptances"] == 1


def test_governed_exception_is_not_actionable() -> None:
    report = _report()
    assert not report.clean  # there IS actionable work
    governed = report.of(Disposition.GOVERNED_EXCEPTION)
    assert all(not t.is_actionable for t in governed)


def test_retirable_acceptance_flagged_when_item_meets_target() -> None:
    # ZT.AP.01 has an in-date acceptance but now sits at advanced -> dead weight.
    report = _report()
    assert {a.item_id for a in report.retirable} == {"ZT.AP.01"}


def test_expiry_is_as_of_sensitive_and_deterministic() -> None:
    # Before the lapse date, the same acceptance is governed, not lapsed.
    before = {t.item.item_id: t.disposition for t in _report(as_of=date(2026, 1, 1)).triaged}
    assert before["ZT.DV.01"] is Disposition.GOVERNED_EXCEPTION
    # On the expiry date it is still valid; the day after it lapses.
    on_expiry = {t.item.item_id: t.disposition for t in _report(as_of=date(2026, 1, 15)).triaged}
    after = {t.item.item_id: t.disposition for t in _report(as_of=date(2026, 1, 16)).triaged}
    assert on_expiry["ZT.DV.01"] is Disposition.GOVERNED_EXCEPTION
    assert after["ZT.DV.01"] is Disposition.LAPSED_ACCEPTANCE


def test_clean_when_all_gaps_governed() -> None:
    run = load_run(FIXTURES / "run_current.json")
    acc = load_exceptions(FIXTURES / "exceptions.json")
    extra = [
        RiskAcceptance("ZT.ID.01", "j", "a", date(2026, 6, 1), date(2026, 12, 31), "T-1"),
        RiskAcceptance("ZT.CC.01", "j", "a", date(2026, 6, 1), date(2026, 12, 31), "T-2"),
    ]
    report = triage(run, acc + extra, as_of=AS_OF)
    # ZT.DV.01 is still lapsed, so not clean; cover it too:
    fully = triage(
        run,
        acc + extra + [RiskAcceptance("ZT.DV.01", "j", "a", date(2026, 6, 1), date(2026, 12, 31), "T-3")],
        as_of=AS_OF,
    )
    assert not report.clean
    assert fully.clean


def test_reason_reports_stage_and_target() -> None:
    reasons = {t.item.item_id: t.reason for t in _report().triaged}
    assert "stage initial below target advanced" in reasons["ZT.ID.01"]
    assert "stage traditional below target advanced" in reasons["ZT.NW.01"]
