"""Run-to-run drift — the trend axis a point-in-time maturity assessment omits.

Each maturity self-assessment stands alone. Comparing two runs tells you what
*changed* on the ordinal stage scale: the **regressions** (stage decreased —
the signal that matters most for continuous monitoring), the **progressions**
(stage increased — credit), scope churn (**new** / **removed** items), and
**target changes** (an item's effective target moved).

A regression is always reported, but it is only *gate-relevant* when the item
landed below its effective target (``below_target``): dropping from optimal to
advanced while the target is advanced is worth knowing, not worth breaking the
build over.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .models import DEFAULT_TARGET, MaturityRun, Stage


class DriftKind(str, Enum):
    REGRESSION = "regression"  # stage decreased
    PROGRESSION = "progression"  # stage increased
    NEW_ITEM = "new_item"  # not assessed in baseline
    REMOVED_ITEM = "removed_item"  # assessed in baseline, gone from current
    TARGET_CHANGE = "target_change"  # effective target moved


@dataclass(frozen=True)
class DriftItem:
    item_id: str
    kind: DriftKind
    baseline_stage: str | None
    current_stage: str | None
    baseline_target: str | None = None
    current_target: str | None = None
    below_target: bool = False  # current stage is below the item's effective target

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "kind": self.kind.value,
            "baseline_stage": self.baseline_stage,
            "current_stage": self.current_stage,
            "baseline_target": self.baseline_target,
            "current_target": self.current_target,
            "below_target": self.below_target,
        }


@dataclass(frozen=True)
class DriftReport:
    items: tuple[DriftItem, ...]

    def of(self, kind: DriftKind) -> tuple[DriftItem, ...]:
        return tuple(i for i in self.items if i.kind is kind)

    @property
    def regressions(self) -> tuple[DriftItem, ...]:
        return self.of(DriftKind.REGRESSION)

    @property
    def regressions_below_target(self) -> tuple[DriftItem, ...]:
        """The gate-relevant subset: stage decreased AND landed below target."""
        return tuple(i for i in self.regressions if i.below_target)

    def summary(self) -> dict[str, int]:
        s = {k.value: len(self.of(k)) for k in DriftKind}
        s["regressions_below_target"] = len(self.regressions_below_target)
        return s

    def to_dict(self) -> dict:
        return {"summary": self.summary(), "items": [i.to_dict() for i in self.items]}


def diff_runs(baseline: MaturityRun, current: MaturityRun, *, target: Stage = DEFAULT_TARGET) -> DriftReport:
    """Classify every item by how it changed from ``baseline`` to ``current``.

    Only items whose status is interesting are reported — an item whose stage
    and effective target both held steady produces no drift item. One item can
    yield both a stage change and a ``target_change`` in the same diff.
    """
    base = baseline.by_id()
    curr = current.by_id()
    items: list[DriftItem] = []

    for iid in sorted(set(base) | set(curr)):
        b = base.get(iid)
        c = curr.get(iid)

        if b is None and c is not None:
            items.append(
                DriftItem(
                    iid,
                    DriftKind.NEW_ITEM,
                    None,
                    c.stage.value,
                    None,
                    c.effective_target(target).value,
                    below_target=c.is_failing(target),
                )
            )
            continue
        if c is None and b is not None:
            items.append(
                DriftItem(iid, DriftKind.REMOVED_ITEM, b.stage.value, None, b.effective_target(target).value, None)
            )
            continue
        assert b is not None and c is not None  # both present

        b_target = b.effective_target(target)
        c_target = c.effective_target(target)
        below = c.is_failing(target)

        if c.stage.rank < b.stage.rank:
            items.append(
                DriftItem(
                    iid,
                    DriftKind.REGRESSION,
                    b.stage.value,
                    c.stage.value,
                    b_target.value,
                    c_target.value,
                    below_target=below,
                )
            )
        elif c.stage.rank > b.stage.rank:
            items.append(
                DriftItem(
                    iid,
                    DriftKind.PROGRESSION,
                    b.stage.value,
                    c.stage.value,
                    b_target.value,
                    c_target.value,
                    below_target=below,
                )
            )

        if b_target is not c_target:
            items.append(
                DriftItem(
                    iid,
                    DriftKind.TARGET_CHANGE,
                    b.stage.value,
                    c.stage.value,
                    b_target.value,
                    c_target.value,
                    below_target=below,
                )
            )
        # steady stage + steady target: not interesting, omitted.

    return DriftReport(items=tuple(items))
