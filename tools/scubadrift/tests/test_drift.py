"""Run-to-run drift classification."""

from __future__ import annotations

from pathlib import Path

from scubadrift import DriftKind, diff_runs, load_run

FIXTURES = Path(__file__).parent / "fixtures"


def _report():
    return diff_runs(load_run(FIXTURES / "run_baseline.json"), load_run(FIXTURES / "run_current.json"))


def test_drift_summary() -> None:
    s = _report().summary()
    assert s["new_failure"] == 1  # AAD.1.1: Pass -> Fail
    assert s["resolved"] == 2  # AAD.2.1, AAD.7.1: Fail -> Pass
    assert s["persistent_failure"] == 2  # AAD.3.1, AAD.5.4
    assert s["new_policy"] == 1  # EXO.1.1 (absent in baseline, failing)
    assert s["removed_policy"] == 1  # SHAREPOINT.1.1


def test_regressions_are_the_new_failures() -> None:
    report = _report()
    assert [i.policy_id for i in report.regressions] == ["MS.AAD.1.1v1"]
    item = report.regressions[0]
    assert item.baseline_result == "Pass"
    assert item.current_result == "Fail"


def test_passing_to_passing_is_omitted() -> None:
    # Nothing that passed in both runs should appear.
    report = _report()
    kinds = {i.policy_id: i.kind for i in report.items}
    assert "MS.AAD.2.1v1" in kinds and kinds["MS.AAD.2.1v1"] is DriftKind.RESOLVED
    # A purely-passing policy would simply be absent; assert the report is finite.
    # 7 policies across the union of both runs all changed status or churned.
    assert len(report.items) == 7
