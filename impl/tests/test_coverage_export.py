"""Tests for uiao.coverage: CoverageLink building and SSP section formatting."""

from __future__ import annotations

from datetime import datetime, timezone

from uiao.coverage.coverage import build_coverage_links, format_ssp_section
from uiao.ir.models.core import Evidence, ProvenanceRecord


def _prov() -> ProvenanceRecord:
    return ProvenanceRecord(
        source="test-suite",
        timestamp=datetime(2026, 4, 8, tzinfo=timezone.utc).isoformat(),
        version="0.0.1-test",
        content_hash=None,
        actor="pytest",
    )


def _evidence(
    eid: str = "e1",
    ksi_id: str = "KSI-IA-01",
    nist_control: str = "IA-2",
    scuba_policy_id: str = "SCUBA-IA-01",
    policy_id: str = "policy:ksi:KSI-IA-01:default",
) -> Evidence:
    return Evidence(
        id=eid,
        source="scuba:run",
        control_id=ksi_id,
        policy_id=policy_id,
        timestamp="2026-04-08T00:00:00Z",
        data={
            "ksi_id": ksi_id,
            "nist_control": nist_control,
            "scuba_policy_id": scuba_policy_id,
        },
        evaluation={"passed": True, "failed": False, "warning": False},
        provenance=_prov(),
    )


class TestBuildCoverageLinks:
    def test_single_evidence_produces_one_link(self) -> None:
        e = _evidence()
        links = build_coverage_links([e])
        assert len(links) == 1

    def test_link_fields_correct(self) -> None:
        e = _evidence()
        link = build_coverage_links([e])[0]
        assert link.nist_control == "IA-2"
        assert link.ksi_id == "KSI-IA-01"
        assert link.scuba_policy_id == "SCUBA-IA-01"
        assert link.evidence_id == "e1"
        assert len(link.evidence_hash) == 64

    def test_empty_evidence_returns_empty(self) -> None:
        assert build_coverage_links([]) == []

    def test_missing_nist_control_defaults_to_unknown(self) -> None:
        e = Evidence(
            id="e2",
            source="scuba:run",
            timestamp="2026-04-08T00:00:00Z",
            data={"ksi_id": "KSI-AC-01"},
            evaluation={},
            provenance=_prov(),
        )
        link = build_coverage_links([e])[0]
        assert link.nist_control == "UNKNOWN"

    def test_missing_scuba_policy_falls_back_to_policy_id(self) -> None:
        e = Evidence(
            id="e3",
            source="scuba:run",
            policy_id="policy:ksi:KSI-AC-01:default",
            timestamp="2026-04-08T00:00:00Z",
            data={"ksi_id": "KSI-AC-01", "nist_control": "AC-2"},
            evaluation={},
            provenance=_prov(),
        )
        link = build_coverage_links([e])[0]
        assert link.scuba_policy_id == "policy:ksi:KSI-AC-01:default"

    def test_multiple_evidence_produces_multiple_links(self) -> None:
        e1 = _evidence("e1", "KSI-IA-01", "IA-2", "SCUBA-IA-01")
        e2 = _evidence("e2", "KSI-AC-01", "AC-2", "SCUBA-AC-01", "policy:ksi:KSI-AC-01:default")
        links = build_coverage_links([e1, e2])
        assert len(links) == 2

    def test_evidence_hash_is_64_chars(self) -> None:
        e = _evidence()
        link = build_coverage_links([e])[0]
        assert len(link.evidence_hash) == 64

    def test_coverage_link_is_deterministic(self) -> None:
        e = _evidence()
        links_a = build_coverage_links([e])
        links_b = build_coverage_links([e])
        assert links_a[0].evidence_hash == links_b[0].evidence_hash


class TestFormatSSPSection:
    def test_contains_header(self) -> None:
        e = _evidence()
        links = build_coverage_links([e])
        ssp = format_ssp_section(links)
        assert "System Security Plan" in ssp

    def test_contains_control_heading(self) -> None:
        e = _evidence()
        links = build_coverage_links([e])
        ssp = format_ssp_section(links)
        assert "Control IA-2" in ssp

    def test_contains_ksi_reference(self) -> None:
        e = _evidence()
        links = build_coverage_links([e])
        ssp = format_ssp_section(links)
        assert "KSI **KSI-IA-01**" in ssp

    def test_controls_sorted(self) -> None:
        e1 = _evidence("e1", "KSI-IA-01", "IA-2", "SCUBA-IA-01")
        e2 = _evidence("e2", "KSI-AC-01", "AC-2", "SCUBA-AC-01", "policy:ksi:KSI-AC-01:default")
        links = build_coverage_links([e1, e2])
        ssp = format_ssp_section(links)
        pos_ac = ssp.index("Control AC-2")
        pos_ia = ssp.index("Control IA-2")
        assert pos_ac < pos_ia

    def test_empty_links_still_has_header(self) -> None:
        ssp = format_ssp_section([])
        assert "System Security Plan" in ssp

