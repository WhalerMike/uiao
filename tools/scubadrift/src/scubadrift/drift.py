"""Run-to-run drift — the trend axis ScubaGear omits.

ScubaGear is point-in-time: each run stands alone. Comparing two runs tells you
what *changed* — the regressions (new failures) that matter most for continuous
monitoring, the remediations to credit, and the baseline churn (policies added
or removed as ScubaGear versions bump).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .models import PolicyResult, ScubaRun


class DriftKind(str, Enum):
    NEW_FAILURE = "new_failure"  # was passing/absent, now failing  (regression)
    RESOLVED = "resolved"  # was failing, now passing         (credit)
    PERSISTENT_FAILURE = "persistent_failure"
    NEW_POLICY = "new_policy"  # not in baseline at all
    REMOVED_POLICY = "removed_policy"  # in baseline, gone from current


@dataclass(frozen=True)
class DriftItem:
    policy_id: str
    kind: DriftKind
    baseline_result: str | None
    current_result: str | None

    def to_dict(self) -> dict:
        return {
            "policy_id": self.policy_id,
            "kind": self.kind.value,
            "baseline_result": self.baseline_result,
            "current_result": self.current_result,
        }


@dataclass(frozen=True)
class DriftReport:
    items: tuple[DriftItem, ...]

    def of(self, kind: DriftKind) -> tuple[DriftItem, ...]:
        return tuple(i for i in self.items if i.kind is kind)

    @property
    def regressions(self) -> tuple[DriftItem, ...]:
        return self.of(DriftKind.NEW_FAILURE)

    def summary(self) -> dict[str, int]:
        return {k.value: len(self.of(k)) for k in DriftKind}

    def to_dict(self) -> dict:
        return {"summary": self.summary(), "items": [i.to_dict() for i in self.items]}


def _fails(p: PolicyResult | None, include_warnings: bool) -> bool:
    return p is not None and p.is_failing(include_warnings)


def diff_runs(baseline: ScubaRun, current: ScubaRun, *, include_warnings: bool = False) -> DriftReport:
    """Classify every policy by how it changed from ``baseline`` to ``current``.

    Only policies whose status is interesting are reported — a policy that
    passed in both runs produces no drift item.
    """
    base = baseline.by_id()
    curr = current.by_id()
    items: list[DriftItem] = []

    for pid in sorted(set(base) | set(curr)):
        b = base.get(pid)
        c = curr.get(pid)
        b_res = b.result.value if b else None
        c_res = c.result.value if c else None

        if b is None and c is not None:
            if _fails(c, include_warnings):
                items.append(DriftItem(pid, DriftKind.NEW_POLICY, None, c_res))
            continue
        if c is None and b is not None:
            items.append(DriftItem(pid, DriftKind.REMOVED_POLICY, b_res, None))
            continue

        b_fail = _fails(b, include_warnings)
        c_fail = _fails(c, include_warnings)
        if c_fail and not b_fail:
            items.append(DriftItem(pid, DriftKind.NEW_FAILURE, b_res, c_res))
        elif b_fail and not c_fail:
            items.append(DriftItem(pid, DriftKind.RESOLVED, b_res, c_res))
        elif b_fail and c_fail:
            items.append(DriftItem(pid, DriftKind.PERSISTENT_FAILURE, b_res, c_res))
        # passing -> passing: not interesting, omitted.

    return DriftReport(items=tuple(items))
