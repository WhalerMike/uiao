"""Severity scoring and remediation prioritization for Zero Trust Assessment findings.

The scoring is intentionally simple and transparent (documented here and surfaced
on the workbook's Methodology sheet) so it can be tuned:

* **Severity (0–100)** = ``risk_weight × status_weight × 10``. Only findings
  (Failed / Investigate) score; everything else — including ``Error`` ("check
  could not run", a coverage issue) — scores 0, matching :attr:`ZtTest.is_finding`.
* **Effort weight** from ``TestImplementationCost`` (Low=1 … High=3; blank=2).
* **Priority** = ``severity / effort_weight`` — higher means remediate sooner,
  so a high-severity / low-effort check (a quick win) outranks a high-severity /
  high-effort one. Bucketed P1≥50, P2≥30, P3≥15, P4>0.
"""

from __future__ import annotations

from dataclasses import dataclass

from uiao.adapters.zta.applicability import derive_applicability, is_premium_gated, license_str
from uiao.adapters.zta.model import ZtReport, ZtTest
from uiao.adapters.zta.triage import id_namespace

RISK_WEIGHT: dict[str, int] = {"High": 10, "Medium": 6, "Low": 3}
STATUS_WEIGHT: dict[str, float] = {"Failed": 1.0, "Investigate": 0.6}
EFFORT_WEIGHT: dict[str, int] = {"Low": 1, "Medium": 2, "High": 3}
_DEFAULT_EFFORT = 2


def severity_score(test: ZtTest) -> int:
    """0–100 severity. Non-findings (incl. Error) score 0."""
    return round(RISK_WEIGHT.get(test.test_risk, 1) * STATUS_WEIGHT.get(test.test_status, 0.0) * 10)


def effort_weight(test: ZtTest) -> int:
    """Remediation-effort proxy from TestImplementationCost (1 easy … 3 hard)."""
    return EFFORT_WEIGHT.get(test.test_implementation_cost, _DEFAULT_EFFORT)


def priority_score(test: ZtTest) -> float:
    """Severity per unit effort — higher means remediate sooner (quick wins win)."""
    return round(severity_score(test) / effort_weight(test), 1)


def priority_bucket(score: float) -> str:
    """Bucket a priority score into P1–P4 (em dash for non-findings)."""
    if score <= 0:
        return "—"
    if score >= 50:
        return "P1"
    if score >= 30:
        return "P2"
    if score >= 15:
        return "P3"
    return "P4"


def applicability_note(test: ZtTest) -> str:
    """Boundary-scope caveat (premium SKU may be unavailable in GCC-Moderate)."""
    if is_premium_gated(test):
        return "premium SKU — verify GCC/FedRAMP-Moderate availability before treating as a real gap"
    return ""


@dataclass(frozen=True)
class Fact:
    """An enriched, flattened per-test record — the unit the dashboard renders."""

    test_id: str
    id_namespace: str
    pillar: str
    sfi_pillar: str
    category: str
    title: str
    risk: str
    status: str
    is_finding: bool
    impact: str
    effort: str
    effort_weight: int
    minimum_license: str
    premium_gated: bool
    applicability: str
    applicability_note: str
    severity: int
    priority: float
    bucket: str


def fact_for(test: ZtTest) -> Fact:
    """Build the enriched :class:`Fact` for one test."""
    sev = severity_score(test)
    pri = priority_score(test)
    return Fact(
        test_id=test.test_id,
        id_namespace=id_namespace(test.test_id),
        pillar=test.pillar,
        sfi_pillar=test.test_sfi_pillar or "",
        category=test.test_category or "",
        title=test.test_title,
        risk=test.test_risk,
        status=test.test_status,
        is_finding=test.is_finding,
        impact=test.test_impact,
        effort=test.test_implementation_cost,
        effort_weight=effort_weight(test),
        minimum_license=license_str(test),
        premium_gated=is_premium_gated(test),
        applicability=derive_applicability(test).value,
        applicability_note=applicability_note(test),
        severity=sev,
        priority=pri,
        bucket=priority_bucket(pri),
    )


def build_facts(report: ZtReport) -> list[Fact]:
    """Enrich every test, sorted findings-first by priority then severity."""
    facts = [fact_for(t) for t in report.tests]
    facts.sort(key=lambda f: (not f.is_finding, -f.priority, -f.severity))
    return facts


def findings(facts: list[Fact]) -> list[Fact]:
    """The actionable subset (Failed / Investigate)."""
    return [f for f in facts if f.is_finding]


#: Column order for tabular exports (workbook + Power BI CSV).
FACT_COLUMNS: tuple[str, ...] = (
    "TestId",
    "IdNamespace",
    "Pillar",
    "SfiPillar",
    "Category",
    "Title",
    "Risk",
    "Status",
    "IsFinding",
    "Impact",
    "Effort",
    "EffortWeight",
    "MinimumLicense",
    "PremiumGated",
    "Applicability",
    "ApplicabilityNote",
    "SeverityScore",
    "PriorityScore",
    "PriorityBucket",
)


def fact_record(fact: Fact) -> dict[str, str | int | float]:
    """Flatten a :class:`Fact` to a column-keyed record for CSV / worksheet rows."""
    return {
        "TestId": fact.test_id,
        "IdNamespace": fact.id_namespace,
        "Pillar": fact.pillar,
        "SfiPillar": fact.sfi_pillar,
        "Category": fact.category,
        "Title": fact.title,
        "Risk": fact.risk,
        "Status": fact.status,
        "IsFinding": "yes" if fact.is_finding else "no",
        "Impact": fact.impact,
        "Effort": fact.effort,
        "EffortWeight": fact.effort_weight,
        "MinimumLicense": fact.minimum_license,
        "PremiumGated": "yes" if fact.premium_gated else "no",
        "Applicability": fact.applicability,
        "ApplicabilityNote": fact.applicability_note,
        "SeverityScore": fact.severity,
        "PriorityScore": fact.priority,
        "PriorityBucket": fact.bucket,
    }
