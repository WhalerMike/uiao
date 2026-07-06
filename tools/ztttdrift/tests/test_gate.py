"""Gate: pass/fail + exit code for a conmon pipeline, including the regression rule."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from ztttdrift import MaturityItem, MaturityRun, RiskAcceptance, Stage, evaluate_gate, load_exceptions, load_run

FIXTURES = Path(__file__).parent / "fixtures"
AS_OF = date(2026, 7, 1)


def _in_date(item_id: str) -> RiskAcceptance:
    return RiskAcceptance(item_id, "j", "isso", date(2026, 6, 1), date(2026, 12, 31), f"T-{item_id}")


def test_gate_fails_on_actionable_drift() -> None:
    run = load_run(FIXTURES / "run_current.json")
    acc = load_exceptions(FIXTURES / "exceptions.json")
    result = evaluate_gate(run, acc, as_of=AS_OF)
    assert result.passed is False
    assert result.exit_code == 1
    assert "FAIL" in result.headline()


def test_gate_fails_on_lapsed_acceptance_alone() -> None:
    run = load_run(FIXTURES / "run_current.json")
    # Cover everything in-date except ZT.DV.01, whose acceptance stays lapsed.
    acc = load_exceptions(FIXTURES / "exceptions.json") + [_in_date("ZT.ID.01"), _in_date("ZT.CC.01")]
    result = evaluate_gate(run, acc, as_of=AS_OF)
    assert result.passed is False
    assert result.report.summary()["lapsed_acceptance"] == 1
    assert result.report.summary()["actionable_new_drift"] == 0


def test_gate_passes_when_only_governed_exceptions_remain() -> None:
    run = load_run(FIXTURES / "run_current.json")
    acc = [_in_date(i) for i in ("ZT.ID.01", "ZT.DV.01", "ZT.NW.01", "ZT.CC.01")]
    result = evaluate_gate(run, acc, as_of=AS_OF)
    assert result.passed is True
    assert result.exit_code == 0
    assert "PASS" in result.headline()


def test_gate_with_no_exceptions_fails_on_any_gap() -> None:
    run = load_run(FIXTURES / "run_current.json")
    result = evaluate_gate(run, [], as_of=AS_OF)
    assert result.passed is False
    # All four below-target items are now actionable new drift.
    assert result.report.summary()["actionable_new_drift"] == 4


def test_gate_fails_on_regression_below_target_even_when_governed() -> None:
    # Everything governed in-date, but with a baseline showing ZT.ID.01
    # regressed advanced->initial (below target): the acceptance was granted
    # against a prior posture, so the regression still fails the gate.
    run = load_run(FIXTURES / "run_current.json")
    baseline = load_run(FIXTURES / "run_baseline.json")
    acc = [_in_date(i) for i in ("ZT.ID.01", "ZT.DV.01", "ZT.NW.01", "ZT.CC.01")]
    result = evaluate_gate(run, acc, as_of=AS_OF, baseline=baseline)
    assert result.report.clean  # triage alone is clean...
    assert result.passed is False  # ...but the regression below target fails the gate
    assert [i.item_id for i in result.regressions_below_target] == ["ZT.ID.01"]


def test_regression_that_meets_target_does_not_fail_the_gate() -> None:
    # A baseline where only ZT.DT.02 differs (optimal -> advanced, still at
    # target) must not fail an otherwise-clean gate.
    current = load_run(FIXTURES / "run_current.json")
    baseline = MaturityRun(
        assessed_at=date(2026, 4, 1),
        source="synthetic",
        items=tuple(
            i if i.item_id != "ZT.DT.02" else MaturityItem(i.item_id, i.pillar, Stage.OPTIMAL, i.title)
            for i in current.items
        ),
    )
    acc = [_in_date(i) for i in ("ZT.ID.01", "ZT.DV.01", "ZT.NW.01", "ZT.CC.01")]
    result = evaluate_gate(current, acc, as_of=AS_OF, baseline=baseline)
    assert result.passed is True
    assert result.regressions_below_target == ()
