"""
End-to-end: Palo Alto adapter → OSCAL SAR generation.

Pipeline: panos-security-rules.xml → PaloAltoAdapter → ClaimSet →
  build_adapter_bundle() → EvidenceBundle → build_sar() → OSCAL JSON
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from uiao.adapters.paloalto_adapter import PaloAltoAdapter
from uiao.adapters.adapter_to_oscal import build_adapter_bundle
from uiao.impl.generators.sar import build_sar


@pytest.fixture
def adapter() -> PaloAltoAdapter:
    sec_xml = (Path(__file__).parent / "fixtures" / "panos-security-rules.xml").read_text()
    return PaloAltoAdapter({
        "host": "fw01.agency.gov",
        "vsys": "vsys1",
        "_security_rules_xml": sec_xml,
    })


class TestPaloAltoToOscal:
    def test_rules_to_claims(self, adapter: PaloAltoAdapter) -> None:
        claims = adapter.get_running_config(scope="security-policies")
        assert len(claims.claims) == 3

    def test_claims_to_bundle(self, adapter: PaloAltoAdapter) -> None:
        claims = adapter.get_running_config(scope="security-policies")
        bundle = build_adapter_bundle(
            adapter_id="palo-alto",
            claim_set=claims,
            control_ids=["SC-7", "CM-7", "AC-4"],
        )
        assert len(bundle.evidence) == 3
        assert len(bundle.controls) == 3

    def test_bundle_to_oscal_sar(self, adapter: PaloAltoAdapter) -> None:
        claims = adapter.get_running_config(scope="security-policies")
        bundle = build_adapter_bundle(
            adapter_id="palo-alto",
            claim_set=claims,
            control_ids=["SC-7", "CM-7", "AC-4"],
        )
        sar = build_sar(
            bundle=bundle,
            system_name="UIAO Firewall Configuration Assessment",
        )
        assert "assessment-results" in sar
        result = sar["assessment-results"]["results"][0]
        assert len(result["observations"]) == 3
        assert len(result["findings"]) == 3

    def test_sar_json_serializable(self, adapter: PaloAltoAdapter) -> None:
        claims = adapter.get_running_config()
        bundle = build_adapter_bundle("palo-alto", claims, control_ids=["SC-7"])
        sar = build_sar(bundle=bundle, system_name="FW Serialization Test")
        output = json.dumps(sar, indent=2)
        assert len(output) > 500
        assert '"observations"' in output

    def test_config_change_drift(self, adapter: PaloAltoAdapter) -> None:
        claims = adapter.get_running_config()
        drift = adapter.push_config_change(
            "security-rule", "allow-dns-outbound", {"action": "deny"}
        )
        bundle = build_adapter_bundle(
            adapter_id="palo-alto",
            claim_set=claims,
            drift=drift,
            control_ids=["SC-7"],
        )
        sar = build_sar(bundle=bundle, system_name="FW Change Assessment")
        assert "assessment-results" in sar

    def test_evidence_bundle_generation(self, adapter: PaloAltoAdapter) -> None:
        evidence = adapter.generate_firewall_evidence()
        assert evidence.source == "palo-alto"
        assert evidence.normalized_data is not None

        # Feed evidence normalized data back through the pipeline
        from uiao.adapters.database_base import ClaimSet, ClaimObject
        claims_data = evidence.normalized_data
        # Reconstruct ClaimSet from evidence for pipeline test
        claim_objects = [
            ClaimObject(
                claim_id=c.get("claim_id", ""),
                entity=c.get("entity", ""),
                fields=c.get("fields", {}),
                source=c.get("source", "palo-alto"),
                provenance_hash=c.get("provenance_hash", ""),
            )
            for c in claims_data.get("claims", [])
        ]
        cs = ClaimSet(claims=claim_objects, source_reference="firewall-evidence")
        bundle = build_adapter_bundle("palo-alto", cs, control_ids=["SC-7"])
        sar = build_sar(bundle=bundle, system_name="Evidence Roundtrip Test")
        assert len(sar["assessment-results"]["results"][0]["observations"]) == 3
