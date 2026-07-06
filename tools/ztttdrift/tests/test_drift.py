"""Run-to-run drift classification on the ordinal stage scale."""

from __future__ import annotations

from pathlib import Path

from ztttdrift import DriftKind, diff_runs, load_run

FIXTURES = Path(__file__).parent / "fixtures"


def _report():
    return diff_runs(load_run(FIXTURES / "run_baseline.json"), load_run(FIXTURES / "run_current.json"))


def test_drift_summary() -> None:
    s = _report().summary()
    assert s["regression"] == 2  # ZT.ID.01 (advanced->initial), ZT.DT.02 (optimal->advanced)
    assert s["regressions_below_target"] == 1  # only ZT.ID.01 landed below target
    assert s["progression"] == 2  # ZT.ID.02, ZT.AP.01 (initial->advanced)
    assert s["new_item"] == 1  # ZT.CC.01
    assert s["removed_item"] == 1  # ZT.NW.02
    assert s["target_change"] == 1  # ZT.DT.01 (advanced->optimal target)


def test_regression_reports_from_and_to_stages() -> None:
    report = _report()
    by_id = {i.item_id: i for i in report.regressions}
    assert set(by_id) == {"ZT.ID.01", "ZT.DT.02"}
    assert by_id["ZT.ID.01"].baseline_stage == "advanced"
    assert by_id["ZT.ID.01"].current_stage == "initial"
    assert by_id["ZT.ID.01"].below_target is True


def test_regression_that_still_meets_target_is_reported_not_below() -> None:
    # ZT.DT.02 dropped optimal->advanced but the target is advanced: worth
    # knowing, not gate-failing by itself.
    report = _report()
    dt02 = {i.item_id: i for i in report.regressions}["ZT.DT.02"]
    assert dt02.below_target is False
    assert [i.item_id for i in report.regressions_below_target] == ["ZT.ID.01"]


def test_target_change_reports_both_targets() -> None:
    changes = _report().of(DriftKind.TARGET_CHANGE)
    assert [i.item_id for i in changes] == ["ZT.DT.01"]
    assert changes[0].baseline_target == "advanced"
    assert changes[0].current_target == "optimal"


def test_new_and_removed_items() -> None:
    report = _report()
    new = {i.item_id for i in report.of(DriftKind.NEW_ITEM)}
    removed = {i.item_id for i in report.of(DriftKind.REMOVED_ITEM)}
    assert new == {"ZT.CC.01"}
    assert removed == {"ZT.NW.02"}
    # The new item arrived below target.
    assert next(iter(report.of(DriftKind.NEW_ITEM))).below_target is True


def test_steady_items_are_omitted() -> None:
    # ZT.DV.01 and ZT.NW.01 held stage and target -> no drift row at all.
    ids = {i.item_id for i in _report().items}
    assert "ZT.DV.01" not in ids
    assert "ZT.NW.01" not in ids
    # 7 rows total: 2 regressions + 2 progressions + 1 new + 1 removed + 1 target change.
    assert len(_report().items) == 7
