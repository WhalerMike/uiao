"""
End-to-end: Adapter claims → OSCAL SSP injection.

Proves the pipeline: adapter → claims → EvidenceBundle → SSP skeleton →
inject evidence → OSCAL System Security Plan JSON.

Completes the OSCAL trifecta: SAR + POA&M + SSP.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from uiao_impl.adapters.terraform_adapter import TerraformAdapter
from uiao_impl.adapters.m365_adapter import M365Adapter
from uiao_impl.adapters.paloalto_adapter import PaloAltoAdapter
from uiao_impl.adapters.adapter_to_oscal import build_adapter_ssp


class TestTerraformToSsp:
    @pytest.fixture
    def adapter(self) -> TerraformAdapter:
        return TerraformAdapter({"workspace": "prod"})

    @pytest.fixture
    def state_path(self) -> str:
        return str(Path(__file__).parent / "fixtures" / "terraform.tfstate")

    def test_produces_valid_ssp(self, adapter: TerraformAdapter, state_path: str) -> None:
        claims = adapter.extract_terraform_state(state_path)
        ssp = build_adapter_ssp("terraform", claims, ["CM-2", "CM-8"])
        assert "system-security-plan" in ssp
        plan = ssp["system-security-plan"]
        assert "metadata" in plan
        assert "control-implementation" in plan

    def test_ssp_has_implemented_requirements(self, adapter: TerraformAdapter, state_path: str) -> None:
        claims = adapter.extract_terraform_state(state_path)
        ssp = build_adapter_ssp("terraform", claims, ["CM-2", "CM-8"])
        reqs = ssp["system-security-plan"]["control-implementation"]["implemented-requirements"]
        control_ids = {r.get("control-id") for r in reqs}
        assert "CM-2" in control_ids

    def test_ssp_json_serializable(self, adapter: TerraformAdapter, state_path: str) -> None:
        claims = adapter.extract_terraform_state(state_path)
        ssp = build_adapter_ssp("terraform", claims, ["CM-8"])
        output = json.dumps(ssp, indent=2)
        assert len(output) > 500
        assert '"system-security-plan"' in output
        assert '"implemented-requirements"' in output


class TestM365ToSsp:
    @pytest.fixture
    def adapter(self) -> M365Adapter:
        config = json.loads(
            (Path(__file__).parent / "fixtures" / "m365-tenant-config.json").read_text()
        )
        return M365Adapter({"tenant_id": "contoso", "_tenant_config": config})

    def test_produces_valid_ssp(self, adapter: M365Adapter) -> None:
        from uiao_impl.adapters.m365_parser import parse_tenant_config
        config = adapter._config.get("_tenant_config", {})
        claims = adapter.normalize(parse_tenant_config(config))
        ssp = build_adapter_ssp("m365", claims, ["CM-2", "CM-3", "CM-8"])
        assert "system-security-plan" in ssp
        reqs = ssp["system-security-plan"]["control-implementation"]["implemented-requirements"]
        assert len(reqs) >= 1

    def test_ssp_system_characteristics(self, adapter: M365Adapter) -> None:
        claims = adapter.normalize([])
        ssp = build_adapter_ssp("m365", claims, system_name="Contoso M365 Tenant")
        sc = ssp["system-security-plan"]["system-characteristics"]
        assert sc["system-name"] == "Contoso M365 Tenant"
        assert sc["security-sensitivity-level"] == "moderate"


class TestPaloAltoToSsp:
    @pytest.fixture
    def adapter(self) -> PaloAltoAdapter:
        xml = (Path(__file__).parent / "fixtures" / "panos-security-rules.xml").read_text()
        return PaloAltoAdapter({"host": "fw01", "vsys": "vsys1", "_security_rules_xml": xml})

    def test_produces_valid_ssp(self, adapter: PaloAltoAdapter) -> None:
        claims = adapter.get_running_config(scope="security-policies")
        ssp = build_adapter_ssp("palo-alto", claims, ["SC-7", "CM-7", "AC-4"])
        assert "system-security-plan" in ssp
        reqs = ssp["system-security-plan"]["control-implementation"]["implemented-requirements"]
        control_ids = {r.get("control-id") for r in reqs}
        assert "SC-7" in control_ids

    def test_firewall_rules_in_ssp(self, adapter: PaloAltoAdapter) -> None:
        claims = adapter.get_running_config()
        ssp = build_adapter_ssp("palo-alto", claims, ["SC-7"])
        output = json.dumps(ssp, indent=2)
        assert '"SC-7"' in output
        assert '"system-security-plan"' in output


class TestMultiAdapterSsp:
    """Prove multiple adapters can inject into the same SSP."""

    def test_terraform_plus_paloalto(self) -> None:
        from uiao_impl.adapters.adapter_to_oscal import (
            build_adapter_bundle,
            inject_adapter_evidence_into_ssp,
            _minimal_ssp_skeleton,
        )

        # Terraform claims
        tf = TerraformAdapter({"workspace": "prod"})
        tf_claims = tf.extract_terraform_state(
            str(Path(__file__).parent / "fixtures" / "terraform.tfstate")
        )
        tf_bundle = build_adapter_bundle("terraform", tf_claims, control_ids=["CM-2", "CM-8"])

        # Palo Alto claims
        pa_xml = (Path(__file__).parent / "fixtures" / "panos-security-rules.xml").read_text()
        pa = PaloAltoAdapter({"host": "fw01", "_security_rules_xml": pa_xml})
        pa_claims = pa.get_running_config()
        pa_bundle = build_adapter_bundle("palo-alto", pa_claims, control_ids=["SC-7"])

        # Inject both into the same SSP
        ssp = _minimal_ssp_skeleton("Multi-Adapter System")
        inject_adapter_evidence_into_ssp(ssp, tf_bundle)
        inject_adapter_evidence_into_ssp(ssp, pa_bundle)

        reqs = ssp["control-implementation"]["implemented-requirements"]
        control_ids = {r.get("control-id") for r in reqs}
        assert "CM-2" in control_ids  # from Terraform
        assert "SC-7" in control_ids  # from Palo Alto
        assert len(reqs) >= 2  # at least 1 per adapter
