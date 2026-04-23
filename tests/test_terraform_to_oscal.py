"""
End-to-end integration test: Terraform adapter → OSCAL SAR generation.

Proves the full pipeline:
  terraform.tfstate → TerraformAdapter → ClaimSet → IR Evidence →
  EvidenceBundle → build_sar() → OSCAL Assessment Results JSON

This is the "last mile" test that validates the entire architecture
from vendor data to auditable output.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from uiao.adapters.terraform_adapter import TerraformAdapter
from uiao.adapters.adapter_to_oscal import build_adapter_bundle
from uiao.generators.sar import build_sar


@pytest.fixture
def state_path() -> str:
    return str(Path(__file__).parent / "fixtures" / "terraform.tfstate")


@pytest.fixture
def plan_path() -> Path:
    return Path(__file__).parent / "fixtures" / "terraform-plan.json"


@pytest.fixture
def adapter() -> TerraformAdapter:
    return TerraformAdapter(
        {
            "state_source": "tests/fixtures/terraform.tfstate",
            "workspace": "production",
        }
    )


class TestTerraformToOscalPipeline:
    """Full pipeline: vendor data → adapter → claims → IR → OSCAL SAR."""

    def test_extract_state_to_claims(self, adapter: TerraformAdapter, state_path: str) -> None:
        """Step 1: Adapter extracts state into ClaimSet."""
        claims = adapter.extract_terraform_state(state_path)
        assert len(claims.claims) == 4  # 4 managed resources

    def test_claims_to_ir_bundle(self, adapter: TerraformAdapter, state_path: str) -> None:
        """Step 2: ClaimSet converts to IR EvidenceBundle."""
        claims = adapter.extract_terraform_state(state_path)
        bundle = build_adapter_bundle(
            adapter_id="terraform",
            claim_set=claims,
            control_ids=["CM-2", "CM-3", "CM-6", "CM-8", "CA-7"],
        )
        assert len(bundle.evidence) == 4
        assert len(bundle.controls) == 5
        assert bundle.pass_count == 4  # all claims = evidence of state = pass

    def test_bundle_to_oscal_sar(self, adapter: TerraformAdapter, state_path: str) -> None:
        """Step 3: EvidenceBundle generates OSCAL Assessment Results."""
        claims = adapter.extract_terraform_state(state_path)
        bundle = build_adapter_bundle(
            adapter_id="terraform",
            claim_set=claims,
            control_ids=["CM-2", "CM-3", "CM-6", "CM-8", "CA-7"],
        )
        sar = build_sar(
            bundle=bundle,
            system_name="UIAO Terraform Infrastructure Assessment",
            tenant_id="production",
        )

        # Verify OSCAL structure
        assert "assessment-results" in sar
        ar = sar["assessment-results"]
        assert "metadata" in ar
        assert "UIAO Terraform Infrastructure Assessment" in ar["metadata"]["title"]
        assert "results" in ar
        assert len(ar["results"]) == 1

        result = ar["results"][0]
        assert "observations" in result
        assert "findings" in result
        assert len(result["observations"]) == 4  # one per resource
        assert len(result["findings"]) == 4

    def test_sar_has_reviewed_controls(self, adapter: TerraformAdapter, state_path: str) -> None:
        """OSCAL SAR includes reviewed controls section."""
        claims = adapter.extract_terraform_state(state_path)
        bundle = build_adapter_bundle(
            adapter_id="terraform",
            claim_set=claims,
            control_ids=["CM-2", "CM-8"],
        )
        sar = build_sar(bundle=bundle, system_name="Test")
        result = sar["assessment-results"]["results"][0]
        assert "reviewed-controls" in result
        controls = result["reviewed-controls"]["control-selections"]
        # The SAR generator includes controls from the evidence
        assert len(controls) >= 1

    def test_sar_with_plan_drift(self, adapter: TerraformAdapter, state_path: str, plan_path: Path) -> None:
        """OSCAL SAR includes drift from terraform plan."""
        claims = adapter.extract_terraform_state(state_path)
        plan = json.loads(plan_path.read_text())
        drift = adapter.consume_terraform_plan(plan)

        bundle = build_adapter_bundle(
            adapter_id="terraform",
            claim_set=claims,
            drift=drift,
            control_ids=["CM-2", "CM-3"],
        )

        assert len(bundle.drift_states) > 0  # drift items from plan

        sar = build_sar(bundle=bundle, system_name="Test with Drift")
        assert "assessment-results" in sar

    def test_sar_json_serializable(self, adapter: TerraformAdapter, state_path: str) -> None:
        """The full SAR output must be JSON-serializable (no datetime objects, etc)."""
        claims = adapter.extract_terraform_state(state_path)
        bundle = build_adapter_bundle(
            adapter_id="terraform",
            claim_set=claims,
            control_ids=["CM-8"],
        )
        sar = build_sar(bundle=bundle, system_name="Serialization Test")
        # This will raise TypeError if any value isn't serializable
        output = json.dumps(sar, indent=2)
        assert len(output) > 100
        assert '"assessment-results"' in output

    def test_full_pipeline_produces_valid_json(self, adapter: TerraformAdapter, state_path: str) -> None:
        """The full pipeline produces valid, non-trivial OSCAL JSON."""
        claims = adapter.extract_terraform_state(state_path)
        bundle = build_adapter_bundle(
            adapter_id="terraform",
            claim_set=claims,
            control_ids=["CM-8"],
        )
        sar = build_sar(bundle=bundle, system_name="Validity Test")
        output = json.dumps(sar, indent=2)

        # Must be substantial (not empty/stub)
        assert len(output) > 500
        # Must contain key OSCAL elements
        assert '"observations"' in output
        assert '"findings"' in output
        assert '"reviewed-controls"' in output
        assert '"back-matter"' in output
