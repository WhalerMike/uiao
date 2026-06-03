"""Triage analysis for a Zero Trust Assessment report.

Everything here is recomputed from :attr:`ZtReport.tests`; the report's own
``TestResultSummary`` is never trusted (it does not reconcile with the per-test
statuses in shipped reports).
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from uiao.adapters.zta.applicability import derive_applicability, is_premium_gated
from uiao.adapters.zta.model import ACTIONABLE_STATUSES, STATUS_ORDER, ZtReport, ZtTest

#: Risk levels, most-severe first.
RISK_ORDER: tuple[str, ...] = ("High", "Medium", "Low")
_RISK_RANK: dict[str, int] = {risk: i for i, risk in enumerate(RISK_ORDER)}

_GUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-", re.ASCII)


def id_namespace(test_id: str) -> str:
    """Classify a ``TestId`` into one of the tool's two namespaces.

    Graph-based checks use short numeric ids; Azure-resource checks use GUIDs.
    A crosswalk key must handle both.
    """
    tid = (test_id or "").strip()
    if _GUID_RE.match(tid):
        return "guid"
    if tid.isdigit():
        return "numeric"
    return "other"


def _risk_rank(test: ZtTest) -> int:
    return _RISK_RANK.get(test.test_risk, len(RISK_ORDER))


@dataclass(frozen=True)
class Triage:
    """Computed view of a report — the single input to every renderer."""

    report: ZtReport
    status_counts: dict[str, int]
    pillar_crosstab: dict[str, dict[str, int]]
    applicability_counts: dict[str, int]
    namespace_counts: dict[str, int]
    worklist: list[ZtTest]
    risks: tuple[str, ...]
    statuses: tuple[str, ...]
    premium_gated_total: int = field(default=0)

    @property
    def actionable_total(self) -> int:
        return sum(self.status_counts.get(s, 0) for s in ACTIONABLE_STATUSES)

    @property
    def skipped_total(self) -> int:
        return self.status_counts.get("Skipped", 0)

    @property
    def planned_total(self) -> int:
        return self.status_counts.get("Planned", 0)

    @property
    def premium_gated_in_worklist(self) -> int:
        return sum(1 for t in self.worklist if is_premium_gated(t))


def build_triage(
    report: ZtReport,
    *,
    risks: tuple[str, ...] = ("High",),
    statuses: tuple[str, ...] | None = None,
) -> Triage:
    """Compute the triage view.

    ``risks`` / ``statuses`` filter the worklist (default: High-risk findings).
    """
    target_statuses = tuple(statuses) if statuses is not None else tuple(sorted(ACTIONABLE_STATUSES))
    tests = report.tests

    status_counts = dict(Counter(t.test_status for t in tests))

    crosstab: dict[str, dict[str, int]] = defaultdict(lambda: dict.fromkeys(STATUS_ORDER, 0))
    for t in tests:
        row = crosstab[t.pillar]
        row[t.test_status] = row.get(t.test_status, 0) + 1

    applicability_counts = dict(Counter(derive_applicability(t).value for t in tests))
    namespace_counts = dict(Counter(id_namespace(t.test_id) for t in tests))
    premium_total = sum(1 for t in tests if is_premium_gated(t))

    risk_set = set(risks)
    status_set = set(target_statuses)
    work = [t for t in tests if t.test_risk in risk_set and t.test_status in status_set]
    work.sort(key=lambda t: (_risk_rank(t), t.pillar, t.test_title))

    return Triage(
        report=report,
        status_counts=status_counts,
        pillar_crosstab={k: dict(v) for k, v in sorted(crosstab.items())},
        applicability_counts=applicability_counts,
        namespace_counts=namespace_counts,
        worklist=work,
        risks=tuple(risks),
        statuses=target_statuses,
        premium_gated_total=premium_total,
    )
