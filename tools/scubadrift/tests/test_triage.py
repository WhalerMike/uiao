"""Triage: the new-drift / lapsed / governed split, and expiry determinism."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from scubadrift import Disposition, load_exceptions, load_run, triage

FIXTURES = Path(__file__).parent / "fixtures"
AS_OF = date(2026, 7, 1)  # fixed so expiry math never drifts with the wall clock


def _report(as_of: date = AS_OF):
    run = load_run(FIXTURES / "run_current.json")
    acc = load_exceptions(FIXTURES / "exceptions.json")
    return triage(run, acc, as_of=as_of)


def test_dispositions_are_correct() -> None:
    report = _report()
    disp = {t.policy.policy_id: t.disposition for t in report.triaged}
    assert disp["MS.AAD.1.1v1"] is Disposition.ACTIONABLE_NEW_DRIFT  # failing, no acceptance
    assert disp["MS.EXO.1.1v1"] is Disposition.ACTIONABLE_NEW_DRIFT  # failing, no acceptance
    assert disp["MS.AAD.5.4v1"] is Disposition.LAPSED_ACCEPTANCE  # acceptance expired 2026-01-15
    assert disp["MS.AAD.3.1v1"] is Disposition.GOVERNED_EXCEPTION  # accepted until 2026-12-31


def test_only_failing_policies_are_triaged() -> None:
    report = _report()
    # Passing policies (AAD.2.1, AAD.7.1) never appear in the triage list.
    ids = {t.policy.policy_id for t in report.triaged}
    assert "MS.AAD.2.1v1" not in ids
    assert "MS.AAD.7.1v1" not in ids


def test_summary_counts() -> None:
    s = _report().summary()
    assert s["failing_total"] == 4
    assert s["actionable_new_drift"] == 2
    assert s["lapsed_acceptance"] == 1
    assert s["governed_exception"] == 1
    assert s["actionable_total"] == 3


def test_governed_exception_is_not_actionable() -> None:
    report = _report()
    assert not report.clean  # there IS actionable work
    governed = report.of(Disposition.GOVERNED_EXCEPTION)
    assert all(not t.is_actionable for t in governed)


def test_retirable_acceptance_flagged_when_policy_passes() -> None:
    # MS.AAD.7.1v1 has an in-date acceptance but now passes -> dead weight.
    report = _report()
    assert {a.policy_id for a in report.retirable} == {"MS.AAD.7.1v1"}


def test_expiry_is_as_of_sensitive_and_deterministic() -> None:
    # Before the lapse date, the same acceptance is governed, not lapsed.
    before = _report(as_of=date(2026, 1, 1))
    disp_before = {t.policy.policy_id: t.disposition for t in before.triaged}
    assert disp_before["MS.AAD.5.4v1"] is Disposition.GOVERNED_EXCEPTION
    # On the expiry date it is still valid; the day after it lapses.
    on_expiry = {t.policy.policy_id: t.disposition for t in _report(as_of=date(2026, 1, 15)).triaged}
    after = {t.policy.policy_id: t.disposition for t in _report(as_of=date(2026, 1, 16)).triaged}
    assert on_expiry["MS.AAD.5.4v1"] is Disposition.GOVERNED_EXCEPTION
    assert after["MS.AAD.5.4v1"] is Disposition.LAPSED_ACCEPTANCE


def test_clean_when_all_failures_governed() -> None:
    run = load_run(FIXTURES / "run_current.json")
    acc = load_exceptions(FIXTURES / "exceptions.json")
    # Add in-date acceptances for the two uncovered failures.
    from scubadrift import RiskAcceptance

    extra = [
        RiskAcceptance("MS.AAD.1.1v1", "j", "a", date(2026, 6, 1), date(2026, 12, 31), "T-1"),
        RiskAcceptance("MS.EXO.1.1v1", "j", "a", date(2026, 6, 1), date(2026, 12, 31), "T-2"),
    ]
    report = triage(run, acc + extra, as_of=AS_OF)
    # AAD.5.4 is still lapsed, so not clean; drop it too:
    fully = triage(
        run,
        acc + extra + [RiskAcceptance("MS.AAD.5.4v1", "j", "a", date(2026, 6, 1), date(2026, 12, 31), "T-3")],
        as_of=AS_OF,
    )
    assert not report.clean
    assert fully.clean
