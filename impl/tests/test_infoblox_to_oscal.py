"""
End-to-end: Infoblox adapter → OSCAL SAR generation.

Pipeline: infoblox-records.json → InfobloxAdapter → ClaimSet →
  build_adapter_bundle() → EvidenceBundle → build_sar() → OSCAL JSON

Covers canon-declared controls SC-20, SC-21, CM-8 for the IPAM surface.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from uiao.impl.adapters.adapter_to_oscal import build_adapter_bundle
from uiao.impl.adapters.database_base import ClaimObject, ClaimSet
from uiao.impl.adapters.infoblox_adapter import InfobloxAdapter
from uiao.impl.generators.sar import build_sar

FIXTURES = Path(__file__).parent / "fixtures"
IPAM_CONTROLS = ["SC-20", "SC-21", "CM-8"]


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture
def adapter() -> InfobloxAdapter:
    return InfobloxAdapter({
        "grid_master": "gm.agency.gov",
        "network_view": "prod",
        "_dns-records_json": _load("infoblox-records.json"),
        "_dhcp-scopes_json": _load("infoblox-dhcp-ranges.json"),
        "_ip-allocations_json": _load("infoblox-fixed-addresses.json"),
        "_network-views_json": _load("infoblox-networks.json"),
    })


class TestInfobloxToOscal:
    def test_records_to_claims(self, adapter: InfobloxAdapter) -> None:
        claims = adapter.get_all_objects(scope="dns-records")
        assert len(claims.claims) >= 3

    def test_claims_to_bundle(self, adapter: InfobloxAdapter) -> None:
        claims = adapter.get_all_objects(scope="dns-records")
        bundle = build_adapter_bundle(
            adapter_id="infoblox",
            claim_set=claims,
            control_ids=IPAM_CONTROLS,
        )
        assert len(bundle.evidence) == len(claims.claims)
        assert len(bundle.controls) == len(IPAM_CONTROLS)

    def test_bundle_to_oscal_sar(self, adapter: InfobloxAdapter) -> None:
        claims = adapter.get_all_objects(scope="dhcp-scopes")
        bundle = build_adapter_bundle(
            adapter_id="infoblox",
            claim_set=claims,
            control_ids=IPAM_CONTROLS,
        )
        sar = build_sar(
            bundle=bundle,
            system_name="UIAO IPAM Assessment",
        )
        assert "assessment-results" in sar
        result = sar["assessment-results"]["results"][0]
        assert len(result["observations"]) == len(claims.claims)
        assert len(result["findings"]) == len(claims.claims)

    def test_bundle_wires_all_ipam_controls(self, adapter: InfobloxAdapter) -> None:
        claims = adapter.get_all_objects(scope="dns-records")
        bundle = build_adapter_bundle(
            adapter_id="infoblox",
            claim_set=claims,
            control_ids=IPAM_CONTROLS,
        )
        bundle_ctrl_ids = {c.id for c in bundle.controls}
        assert bundle_ctrl_ids == set(IPAM_CONTROLS)
        policy_ctrl_refs = {p.control_ref for p in bundle.policies}
        assert policy_ctrl_refs == set(IPAM_CONTROLS)

    def test_sar_cites_primary_control(self, adapter: InfobloxAdapter) -> None:
        claims = adapter.get_all_objects(scope="dns-records")
        bundle = build_adapter_bundle(
            adapter_id="infoblox",
            claim_set=claims,
            control_ids=IPAM_CONTROLS,
        )
        sar = build_sar(bundle=bundle, system_name="IPAM Control Coverage")
        assert IPAM_CONTROLS[0] in json.dumps(sar)

    def test_sar_json_serializable(self, adapter: InfobloxAdapter) -> None:
        claims = adapter.get_all_objects()
        bundle = build_adapter_bundle("infoblox", claims, control_ids=["SC-20"])
        sar = build_sar(bundle=bundle, system_name="IPAM Serialization Test")
        output = json.dumps(sar, indent=2)
        assert len(output) > 500
        assert '"observations"' in output

    def test_dns_change_drift_in_bundle(self, adapter: InfobloxAdapter) -> None:
        claims = adapter.get_all_objects(scope="dns-records")
        drift = adapter.push_dns_change(
            "record:a", "web01.contoso.gov", {"ipv4addr": "10.9.9.9"}
        )
        bundle = build_adapter_bundle(
            adapter_id="infoblox",
            claim_set=claims,
            drift=drift,
            control_ids=["SC-20"],
        )
        sar = build_sar(bundle=bundle, system_name="DNS Change Assessment")
        assert "assessment-results" in sar

    def test_evidence_bundle_roundtrip(self, adapter: InfobloxAdapter) -> None:
        evidence = adapter.generate_ipam_evidence(scope="dns-records")
        assert evidence.source == "infoblox"
        assert evidence.normalized_data is not None

        claim_objects = [
            ClaimObject(
                claim_id=c.get("claim_id", ""),
                entity=c.get("entity", ""),
                fields=c.get("fields", {}),
                source=c.get("source", "infoblox"),
                provenance_hash=c.get("provenance_hash", ""),
            )
            for c in evidence.normalized_data.get("claims", [])
        ]
        cs = ClaimSet(claims=claim_objects, source_reference="ipam-evidence")
        bundle = build_adapter_bundle("infoblox", cs, control_ids=["SC-20"])
        sar = build_sar(bundle=bundle, system_name="IPAM Evidence Roundtrip")
        assert len(sar["assessment-results"]["results"][0]["observations"]) == len(claim_objects)
