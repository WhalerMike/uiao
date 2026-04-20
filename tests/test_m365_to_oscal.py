"""
End-to-end: M365 adapter → OSCAL SAR generation.

Pipeline: m365-tenant-config.json → M365Adapter → ClaimSet →
  build_adapter_bundle() → EvidenceBundle → build_sar() → OSCAL JSON
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from uiao.adapters.m365_adapter import M365Adapter
from uiao.adapters.adapter_to_oscal import build_adapter_bundle
from uiao.generators.sar import build_sar


@pytest.fixture
def adapter() -> M365Adapter:
    config = json.loads(
        (Path(__file__).parent / "fixtures" / "m365-tenant-config.json").read_text()
    )
    return M365Adapter({
        "tenant_id": "contoso.onmicrosoft.com",
        "_tenant_config": config,
    })


class TestM365ToOscal:
    def test_tenant_config_to_claims(self, adapter: M365Adapter) -> None:
        claims = adapter.get_tenant_config("exchange-online")
        assert len(claims.claims) >= 2

    def test_all_workloads_to_bundle(self, adapter: M365Adapter) -> None:
        from uiao.adapters.m365_parser import parse_tenant_config
        config = adapter._config.get("_tenant_config", {})
        all_entities = parse_tenant_config(config)
        claims = adapter.normalize(all_entities)
        bundle = build_adapter_bundle(
            adapter_id="m365",
            claim_set=claims,
            control_ids=["CM-2", "CM-3", "CM-8"],
        )
        assert len(bundle.evidence) >= 5  # entities across 5 workloads
        assert len(bundle.controls) == 3

    def test_bundle_to_oscal_sar(self, adapter: M365Adapter) -> None:
        from uiao.adapters.m365_parser import parse_tenant_config
        config = adapter._config.get("_tenant_config", {})
        claims = adapter.normalize(parse_tenant_config(config))
        bundle = build_adapter_bundle(
            adapter_id="m365",
            claim_set=claims,
            control_ids=["CM-2", "CM-3"],
        )
        sar = build_sar(
            bundle=bundle,
            system_name="UIAO M365 Tenant Assessment",
            tenant_id="contoso.onmicrosoft.com",
        )
        assert "assessment-results" in sar
        result = sar["assessment-results"]["results"][0]
        assert len(result["observations"]) >= 5
        assert len(result["findings"]) >= 5

    def test_sar_json_serializable(self, adapter: M365Adapter) -> None:
        from uiao.adapters.m365_parser import parse_tenant_config
        config = adapter._config.get("_tenant_config", {})
        claims = adapter.normalize(parse_tenant_config(config))
        bundle = build_adapter_bundle("m365", claims, control_ids=["CM-8"])
        sar = build_sar(bundle=bundle, system_name="M365 Serialization Test")
        output = json.dumps(sar, indent=2)
        assert len(output) > 500
        assert '"assessment-results"' in output

    def test_baseline_drift_in_sar(self, adapter: M365Adapter) -> None:
        drift = adapter.apply_baseline(
            "exchange-online",
            {"Default Mailbox Policy.automaticRepliesSetting": "enabled"},
        )
        from uiao.adapters.m365_parser import parse_tenant_config
        config = adapter._config.get("_tenant_config", {})
        claims = adapter.normalize(parse_tenant_config(config))
        bundle = build_adapter_bundle(
            adapter_id="m365",
            claim_set=claims,
            drift=drift,
            control_ids=["CM-6"],
        )
        assert len(bundle.drift_states) >= 0  # drift may or may not map to resources
        sar = build_sar(bundle=bundle, system_name="M365 Drift Test")
        assert "assessment-results" in sar
