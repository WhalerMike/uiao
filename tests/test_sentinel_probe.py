"""
Tests for the GCC Boundary Probe Sentinel surface.

Covers the offline-testable surface of
``src/uiao/adapters/modernization/gcc_boundary_probe/sentinel_probe.py``:
the query registry, the .kql loader, the SentinelFinding dataclass, and
the dashboard_completeness_score scorecard. The async network-facing
``SentinelProbe.run_query`` / ``run_all`` paths are not covered here —
they require an httpx mock and a Log Analytics workspace, which are out
of scope for offline unit tests.

File: tests/test_sentinel_probe.py
"""

from __future__ import annotations

import pytest

from uiao.adapters.modernization.gcc_boundary_probe.sentinel_probe import (
    QUERY_REGISTRY,
    DashboardCompletenessScore,
    SentinelFinding,
    dashboard_completeness_score,
    load_kql_query,
)


# ------------------------------------------------------------------
# Query registry — single source of truth for what the probe runs
# ------------------------------------------------------------------


def test_query_registry_has_seven_queries() -> None:
    """The seven §13.3 KQL queries are registered."""
    assert len(QUERY_REGISTRY) == 7


def test_query_registry_entries_have_required_keys() -> None:
    """Every registry entry carries filename, symptom_id, severity, description."""
    required = {"filename", "symptom_id", "severity", "description"}
    for query_id, meta in QUERY_REGISTRY.items():
        assert required <= set(meta.keys()), f"missing keys in {query_id}: {required - set(meta.keys())}"


def test_query_registry_severities_are_valid() -> None:
    """Severities follow the P1/P2/P3 vocabulary used elsewhere."""
    valid = {"P1", "P2", "P3"}
    for query_id, meta in QUERY_REGISTRY.items():
        assert meta["severity"] in valid, f"{query_id} has invalid severity {meta['severity']}"


def test_query_registry_filenames_are_unique() -> None:
    filenames = [m["filename"] for m in QUERY_REGISTRY.values()]
    assert len(filenames) == len(set(filenames))


# ------------------------------------------------------------------
# .kql loader
# ------------------------------------------------------------------


def test_load_kql_returns_non_empty_text_for_every_registered_query() -> None:
    for query_id in QUERY_REGISTRY:
        kql = load_kql_query(query_id)
        assert isinstance(kql, str)
        assert len(kql) > 0, f"empty .kql for {query_id}"


def test_load_kql_raises_for_unknown_query() -> None:
    with pytest.raises(KeyError):
        load_kql_query("does-not-exist")


# ------------------------------------------------------------------
# SentinelFinding
# ------------------------------------------------------------------


def test_sentinel_finding_drift_class_matches_boundary_class() -> None:
    f = SentinelFinding(query_id="q", symptom_id="s", description="d")
    assert f.drift_class == "DRIFT-EVIDENCE-PIPELINE"
    assert f.boundary_class == "DRIFT-EVIDENCE-PIPELINE"


def test_sentinel_finding_path_uses_query_id() -> None:
    f = SentinelFinding(query_id="entra-diagnostic-completeness", symptom_id="s", description="d")
    assert f.path == "sentinel-evidence/entra-diagnostic-completeness"


def test_sentinel_finding_as_dict_strips_raw_response() -> None:
    """Raw response payloads can be large; they belong in logs, not the findings ledger."""
    f = SentinelFinding(query_id="q", symptom_id="s", description="d", raw_response={"big": "x" * 1000})
    d = f.as_dict()
    assert "raw_response" not in d
    assert d["drift_class"] == "DRIFT-EVIDENCE-PIPELINE"
    assert d["path"] == "sentinel-evidence/q"


# ------------------------------------------------------------------
# dashboard_completeness_score — assessment §10.2 reproduction
# ------------------------------------------------------------------


def _all_findings(result: str, rows: int = 10) -> list[SentinelFinding]:
    return [
        SentinelFinding(
            query_id=qid,
            symptom_id=meta["symptom_id"],
            description=meta["description"],
            probe_result=result,
            rows_returned=rows,
        )
        for qid, meta in QUERY_REGISTRY.items()
    ]


def test_scorecard_baseline_when_all_operational() -> None:
    """All queries OPERATIONAL → every product score equals its §10.2 baseline."""
    scores = dashboard_completeness_score(_all_findings("OPERATIONAL"))
    by_product = {s.product: s for s in scores}

    # §10.2 baselines (sample subset — full table is in _BASELINE_SCORES).
    assert by_product["Entra ID (P2)"].score == 75
    assert by_product["Microsoft Intune"].score == 60
    assert by_product["Exchange Online"].score == 70
    assert by_product["Power Platform (Apps / Automate / BI)"].score == 45
    assert by_product["Microsoft Sentinel"].score == 75


def test_scorecard_deductions_apply_when_not_detected() -> None:
    """All queries NOT_DETECTED → each contributing product's score drops by its deduction."""
    scores = dashboard_completeness_score(_all_findings("NOT_DETECTED"))
    by_product = {s.product: s for s in scores}

    # Entra ID has two impacting queries: entra-diagnostic-completeness (-25)
    # and ca-evaluation-completeness (-10) → 75 - 35 = 40.
    assert by_product["Entra ID (P2)"].score == 40
    # Intune: -30 from intune-ingestion → 60 - 30 = 30.
    assert by_product["Microsoft Intune"].score == 30
    # Exchange: -20 (mailitemsaccessed) and -5 (security baseline) → 70 - 25 = 45.
    assert by_product["Exchange Online"].score == 45
    # Sentinel: -25 from master-telemetry-health → 75 - 25 = 50.
    assert by_product["Microsoft Sentinel"].score == 50


def test_scorecard_query_failed_treated_same_as_not_detected() -> None:
    """A QUERY_FAILED is also a deduction — silent failure must not preserve baseline."""
    scores = dashboard_completeness_score(_all_findings("QUERY_FAILED"))
    by_product = {s.product: s for s in scores}
    assert by_product["Microsoft Sentinel"].score == 50


def test_scorecard_floors_at_zero() -> None:
    """A product whose deductions exceed the baseline floors at 0, not negative."""
    # Synthesize an unrealistic scenario where deductions exceed baseline.
    findings = _all_findings("NOT_DETECTED")
    scores = dashboard_completeness_score(findings)
    for s in scores:
        assert s.score >= 0, f"{s.product} negative: {s.score}"


def test_scorecard_unimpacted_products_preserve_baseline_under_failure() -> None:
    """Products with no contributing query keep their baseline regardless of probe outcomes."""
    scores_ok = dashboard_completeness_score(_all_findings("OPERATIONAL"))
    scores_fail = dashboard_completeness_score(_all_findings("NOT_DETECTED"))
    by_ok = {s.product: s.score for s in scores_ok}
    by_fail = {s.product: s.score for s in scores_fail}

    # SharePoint Online has no impacting query in the registry -> baseline preserved.
    assert by_ok["SharePoint Online"] == by_fail["SharePoint Online"] == 65
    # Defender for Endpoint same.
    assert by_ok["Defender for Endpoint"] == by_fail["Defender for Endpoint"] == 85


def test_scorecard_components_record_baseline_and_deduction() -> None:
    scores = dashboard_completeness_score(_all_findings("NOT_DETECTED"))
    by_product = {s.product: s for s in scores}
    entra = by_product["Entra ID (P2)"]
    assert entra.components["baseline"] == 75
    assert entra.components["deduction"] == 35
    assert entra.score == 40


def test_scorecard_returns_dashboard_completeness_score_objects() -> None:
    scores = dashboard_completeness_score([])
    assert all(isinstance(s, DashboardCompletenessScore) for s in scores)
    assert len(scores) == 15  # 15-product rubric per §10.2
