"""
End-to-end: BlueCat adapter → OSCAL SAR generation.

Pipeline: bluecat-host-records.json → BlueCatAdapter → ClaimSet →
  build_adapter_bundle() → EvidenceBundle → build_sar() → OSCAL JSON

Covers canon-declared controls SC-20, SC-21, CM-8 for the BAM IPAM surface.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from uiao.adapters.adapter_to_oscal import build_adapter_bundle
from uiao.adapters.bluecat_adapter import BlueCatAdapter
from uiao.adapters.database_base import ClaimObject, ClaimSet
from uiao.generators.sar import build_sar

FIXTURES = Path(__file__).parent / "fixtures"
IPAM_CONTROLS = ["SC-20", "SC-21", "CM-8"]


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture
def adapter() -> BlueCatAdapter:
    return BlueCatAdapter({
        "bam_host": "bam01.agency.com",
        "configuration": "prod",
        "_dns-records_json": _load("bluecat-host-records.json"),
        "_dhcp-scopes_json": _load("bluecat-dhcp-ranges.json"),
        "_ip-allocations_json": _load("bluecat-ip-addresses.json"),
    })


class TestBlueCatToOscal:
    def test_records_to_claims(self, adapter: BlueCatAdapter) -> None:
        claims = adapter.get_all_objects(scope="dns-records")
        assert len(claims.claims) >= 3

    def test_claims_to_bundle(self, adapter: BlueCatAdapter) -> None:
        claims = adapter.get_all_objects(scope="dns-records")
        bundle = build_adapter_bundle(
            adapter_id="bluecat-address-manager",
            claim_set=claims,
            control_ids=IPAM_CONTROLS,
        )
        assert len(bundle.evidence) == len(claims.claims)
        assert len(bundle.controls) == len(IPAM_CONTROLS)

    def test_bundle_to_oscal_sar(self, adapter: BlueCatAdapter) -> None:
        claims = adapter.get_all_objects(scope="dhcp-scopes")
        bundle = build_adapter_bundle(
            adapter_id="bluecat-address-manager",
            claim_set=claims,
            control_ids=IPAM_CONTROLS,
        )
        sar = build_sar(bundle=bundle, system_name="UIAO BAM Assessment")
        assert "assessment-results" in sar
        result = sar["assessment-results"]["results"][0]
        assert len(result["observations"]) == len(claims.claims)
        assert len(result["findings"]) == len(claims.claims)

    def test_bundle_wires_all_ipam_controls(self, adapter: BlueCatAdapter) -> None:
        claims = adapter.get_all_objects(scope="dns-records")
        bundle = build_adapter_bundle(
            adapter_id="bluecat-address-manager",
            claim_set=claims,
            control_ids=IPAM_CONTROLS,
        )
        assert {c.id for c in bundle.controls} == set(IPAM_CONTROLS)
        assert {p.control_ref for p in bundle.policies} == set(IPAM_CONTROLS)

    def test_sar_cites_primary_control(self, adapter: BlueCatAdapter) -> None:
        claims = adapter.get_all_objects(scope="dns-records")
        bundle = build_adapter_bundle(
            adapter_id="bluecat-address-manager",
            claim_set=claims,
            control_ids=IPAM_CONTROLS,
        )
        sar = build_sar(bundle=bundle, system_name="BAM Control Coverage")
        assert IPAM_CONTROLS[0] in json.dumps(sar)

    def test_sar_json_serializable(self, adapter: BlueCatAdapter) -> None:
        claims = adapter.get_all_objects()
        bundle = build_adapter_bundle("bluecat-address-manager", claims, control_ids=["SC-20"])
        sar = build_sar(bundle=bundle, system_name="BAM Serialization Test")
        output = json.dumps(sar, indent=2)
        assert len(output) > 500
        assert '"observations"' in output

    def test_dns_change_drift_in_bundle(self, adapter: BlueCatAdapter) -> None:
        claims = adapter.get_all_objects(scope="dns-records")
        drift = adapter.push_dns_change(
            "HostRecord", "web01.contoso.gov", {"addresses": "10.9.9.9"}
        )
        bundle = build_adapter_bundle(
            adapter_id="bluecat-address-manager",
            claim_set=claims,
            drift=drift,
            control_ids=["SC-20"],
        )
        sar = build_sar(bundle=bundle, system_name="BAM Change Assessment")
        assert "assessment-results" in sar

    def test_evidence_bundle_roundtrip(self, adapter: BlueCatAdapter) -> None:
        evidence = adapter.generate_ipam_evidence(scope="dns-records")
        assert evidence.source == "bluecat-address-manager"
        assert evidence.normalized_data is not None

        claim_objects = [
            ClaimObject(
                claim_id=c.get("claim_id", ""),
                entity=c.get("entity", ""),
                fields=c.get("fields", {}),
                source=c.get("source", "bluecat-address-manager"),
                provenance_hash=c.get("provenance_hash", ""),
            )
            for c in evidence.normalized_data.get("claims", [])
        ]
        cs = ClaimSet(claims=claim_objects, source_reference="bam-evidence")
        bundle = build_adapter_bundle("bluecat-address-manager", cs, control_ids=["SC-20"])
        sar = build_sar(bundle=bundle, system_name="BAM Evidence Roundtrip")
        assert len(sar["assessment-results"]["results"][0]["observations"]) == len(claim_objects)
