"""
Tests for the Terraform / OpenTofu Evidence Adapter.

Covers:
- Instantiation and configuration
- All 7 canonical responsibility domains (base class contract)
- Terraform-specific extension methods (stub behavior)
- collect_and_align convenience method
- ADAPTER_ID consistency with canon registry

File: tests/test_terraform_adapter.py
"""

from __future__ import annotations

from pathlib import Path
import pytest

from uiao.adapters.terraform_adapter import TerraformAdapter
from uiao.adapters.database_base import (
    ClaimObject,
    ClaimSet,
    ConnectionProvenance,
    DriftReport,
    EvidenceObject,
    QueryProvenance,
    SchemaMappingObject,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def adapter() -> TerraformAdapter:
    """Default adapter with minimal config."""
    return TerraformAdapter(
        {
            "state_source": "s3://my-bucket/terraform.tfstate",
            "workspace": "prod",
            "auth_method": "iam-role",
        }
    )


@pytest.fixture
def adapter_empty() -> TerraformAdapter:
    """Adapter with no config (tests defaults)."""
    return TerraformAdapter()


# ---------------------------------------------------------------------------
# Instantiation
# ---------------------------------------------------------------------------


class TestInstantiation:
    def test_adapter_id(self, adapter: TerraformAdapter) -> None:
        assert adapter.ADAPTER_ID == "terraform"

    def test_default_config(self, adapter_empty: TerraformAdapter) -> None:
        assert adapter_empty._state_source == ""
        assert adapter_empty._workspace == "default"

    def test_custom_config(self, adapter: TerraformAdapter) -> None:
        assert adapter._state_source == "s3://my-bucket/terraform.tfstate"
        assert adapter._workspace == "prod"

    def test_is_database_adapter_base(self, adapter: TerraformAdapter) -> None:
        from uiao.adapters.database_base import DatabaseAdapterBase

        assert isinstance(adapter, DatabaseAdapterBase)


# ---------------------------------------------------------------------------
# 2.1 Connection & Identity
# ---------------------------------------------------------------------------


class TestConnect:
    def test_connect_returns_provenance(self, adapter: TerraformAdapter) -> None:
        result = adapter.connect()
        assert isinstance(result, ConnectionProvenance)

    def test_connect_identity_includes_workspace(self, adapter: TerraformAdapter) -> None:
        result = adapter.connect()
        assert "prod" in result.identity

    def test_connect_endpoint_matches_source(self, adapter: TerraformAdapter) -> None:
        result = adapter.connect()
        assert result.endpoint == "s3://my-bucket/terraform.tfstate"

    def test_connect_auth_method(self, adapter: TerraformAdapter) -> None:
        result = adapter.connect()
        assert result.auth_method == "iam-role"

    def test_connect_default_endpoint(self, adapter_empty: TerraformAdapter) -> None:
        result = adapter_empty.connect()
        assert result.endpoint == "local://terraform.tfstate"


# ---------------------------------------------------------------------------
# 2.2 Schema Discovery
# ---------------------------------------------------------------------------


class TestDiscoverSchema:
    def test_returns_schema_mapping(self, adapter: TerraformAdapter) -> None:
        result = adapter.discover_schema()
        assert isinstance(result, SchemaMappingObject)

    def test_vendor_schema_has_resource_type(self, adapter: TerraformAdapter) -> None:
        result = adapter.discover_schema()
        assert "resource_type" in result.vendor_schema

    def test_unmapped_fields_present(self, adapter: TerraformAdapter) -> None:
        result = adapter.discover_schema()
        assert len(result.unmapped_fields) > 0

    def test_version_hash_deterministic(self, adapter: TerraformAdapter) -> None:
        h1 = adapter.discover_schema().version_hash
        h2 = adapter.discover_schema().version_hash
        assert h1 == h2


# ---------------------------------------------------------------------------
# 2.3 Query Normalization
# ---------------------------------------------------------------------------


class TestExecuteQuery:
    def test_returns_query_provenance(self, adapter: TerraformAdapter) -> None:
        result = adapter.execute_query({"from": "aws_instance"})
        assert isinstance(result, QueryProvenance)

    def test_vendor_query_includes_state_source(self, adapter: TerraformAdapter) -> None:
        result = adapter.execute_query({"from": "aws_instance"})
        assert "s3://my-bucket/terraform.tfstate" in result.vendor_query

    def test_wildcard_query(self, adapter: TerraformAdapter) -> None:
        result = adapter.execute_query({"from": "*"})
        assert "grep" not in result.vendor_query


# ---------------------------------------------------------------------------
# 2.4 Data Normalization
# ---------------------------------------------------------------------------


class TestNormalize:
    def test_empty_input(self, adapter: TerraformAdapter) -> None:
        result = adapter.normalize([])
        assert isinstance(result, ClaimSet)
        assert len(result.claims) == 0

    def test_single_resource(self, adapter: TerraformAdapter) -> None:
        raw = [
            {
                "type": "aws_instance",
                "name": "web",
                "provider": "aws",
                "attributes": {"ami": "ami-123", "instance_type": "t3.micro"},
            }
        ]
        result = adapter.normalize(raw)
        assert len(result.claims) == 1
        claim = result.claims[0]
        assert isinstance(claim, ClaimObject)
        assert "aws_instance" in claim.claim_id
        assert claim.source == "terraform"

    def test_provenance_hash_set(self, adapter: TerraformAdapter) -> None:
        raw = [{"type": "aws_s3_bucket", "name": "logs", "provider": "aws"}]
        result = adapter.normalize(raw)
        assert result.claims[0].provenance_hash  # non-empty

    def test_multiple_resources(self, adapter: TerraformAdapter) -> None:
        raw = [
            {"type": "aws_instance", "name": "a", "provider": "aws"},
            {"type": "azurerm_virtual_machine", "name": "b", "provider": "azurerm"},
        ]
        result = adapter.normalize(raw)
        assert len(result.claims) == 2
        ids = {c.claim_id for c in result.claims}
        assert len(ids) == 2  # unique claim IDs


# ---------------------------------------------------------------------------
# 2.5 Drift Detection
# ---------------------------------------------------------------------------


class TestDetectDrift:
    def test_returns_drift_report(self, adapter: TerraformAdapter) -> None:
        result = adapter.detect_drift()
        assert isinstance(result, DriftReport)

    def test_drift_type_is_terraform(self, adapter: TerraformAdapter) -> None:
        result = adapter.detect_drift()
        assert result.drift_type == "terraform-state"

    def test_details_include_workspace(self, adapter: TerraformAdapter) -> None:
        result = adapter.detect_drift()
        assert result.details["workspace"] == "prod"


# ---------------------------------------------------------------------------
# 2.6 Evidence Packaging (base class orchestrator)
# ---------------------------------------------------------------------------


class TestCollectEvidence:
    def test_returns_evidence_object(self, adapter: TerraformAdapter) -> None:
        result = adapter.collect_evidence("KSI-CM-01")
        assert isinstance(result, EvidenceObject)

    def test_evidence_ksi_id(self, adapter: TerraformAdapter) -> None:
        result = adapter.collect_evidence("KSI-CM-01")
        assert result.ksi_id == "KSI-CM-01"

    def test_evidence_source(self, adapter: TerraformAdapter) -> None:
        result = adapter.collect_evidence("KSI-CM-01")
        assert result.source == "terraform"


# ---------------------------------------------------------------------------
# Terraform-Specific Extensions (stub behavior)
# ---------------------------------------------------------------------------


class TestExtractTerraformState:
    """Real parsing tests against fixture state file."""

    @pytest.fixture
    def state_path(self) -> str:
        return str(Path(__file__).parent / "fixtures" / "terraform.tfstate")

    def test_parses_real_state_file(self, adapter: TerraformAdapter, state_path: str) -> None:
        result = adapter.extract_terraform_state(state_path)
        assert isinstance(result, ClaimSet)
        # 4 managed resources in fixture (excludes data source)
        assert len(result.claims) == 4

    def test_resource_count_matches_state(self, adapter: TerraformAdapter, state_path: str) -> None:
        result = adapter.extract_terraform_state(state_path)
        types = {c.fields.get("resource_type") for c in result.claims}
        assert "aws_instance" in types
        assert "azurerm_resource_group" in types

    def test_claim_ids_include_provider_and_type(self, adapter: TerraformAdapter, state_path: str) -> None:
        result = adapter.extract_terraform_state(state_path)
        for claim in result.claims:
            assert "terraform:" in claim.claim_id
            assert claim.source == "terraform"

    def test_attributes_preserved_in_fields(self, adapter: TerraformAdapter, state_path: str) -> None:
        result = adapter.extract_terraform_state(state_path)
        web_claims = [c for c in result.claims if "web" in c.claim_id and "instance" in c.claim_id]
        assert len(web_claims) == 1
        attrs = web_claims[0].fields.get("attributes", {})
        assert attrs.get("instance_type") == "t3.micro"
        assert attrs.get("ami") == "ami-0c55b159cbfafe1f0"

    def test_provenance_hash_deterministic(self, adapter: TerraformAdapter, state_path: str) -> None:
        r1 = adapter.extract_terraform_state(state_path)
        r2 = adapter.extract_terraform_state(state_path)
        hashes1 = {c.provenance_hash for c in r1.claims}
        hashes2 = {c.provenance_hash for c in r2.claims}
        assert hashes1 == hashes2

    def test_resource_filter(self, adapter: TerraformAdapter, state_path: str) -> None:
        result = adapter.extract_terraform_state(state_path, resource_filter="aws_instance")
        assert len(result.claims) == 1
        assert "aws_instance" in result.claims[0].claim_id

    def test_empty_state_returns_empty(self, adapter: TerraformAdapter, tmp_path: Path) -> None:
        empty_state = tmp_path / "empty.tfstate"
        empty_state.write_text('{"version": 4, "resources": []}')
        result = adapter.extract_terraform_state(str(empty_state))
        assert len(result.claims) == 0


class TestParseHclConfig:
    """Real HCL parsing tests against fixture .tf file."""

    @pytest.fixture
    def hcl_path(self) -> str:
        return str(Path(__file__).parent / "fixtures" / "example.tf")

    def test_parses_real_hcl_file(self, adapter: TerraformAdapter, hcl_path: str) -> None:
        result = adapter.parse_hcl_config(hcl_path)
        assert isinstance(result, ClaimSet)
        assert len(result.claims) >= 3  # web, web_sg, governance

    def test_resource_blocks_extracted(self, adapter: TerraformAdapter, hcl_path: str) -> None:
        result = adapter.parse_hcl_config(hcl_path)
        types = {c.fields.get("resource_type") for c in result.claims}
        assert "aws_instance" in types
        assert "aws_security_group" in types
        assert "azurerm_resource_group" in types

    def test_variable_substitution(self, adapter: TerraformAdapter, hcl_path: str) -> None:
        result = adapter.parse_hcl_config(hcl_path, variables={"instance_type": "t3.large"})
        web_claims = [c for c in result.claims if c.fields.get("resource_type") == "aws_instance"]
        assert len(web_claims) >= 1
        # Variable should be resolved in attributes
        attrs = web_claims[0].fields.get("attributes", {})
        assert attrs.get("instance_type") == "t3.large"

    def test_inline_hcl_string(self, adapter: TerraformAdapter) -> None:
        hcl = 'resource "aws_s3_bucket" "logs" {\n  bucket = "my-logs"\n}\n'
        result = adapter.parse_hcl_config(hcl)
        assert len(result.claims) == 1
        assert "s3_bucket" in result.claims[0].claim_id


class TestConsumeTerraformPlan:
    """Real plan JSON parsing tests against fixture."""

    @pytest.fixture
    def plan(self) -> dict:
        import json

        path = Path(__file__).parent / "fixtures" / "terraform-plan.json"
        return json.loads(path.read_text())

    def test_parses_real_plan(self, adapter: TerraformAdapter, plan: dict) -> None:
        result = adapter.consume_terraform_plan(plan)
        assert isinstance(result, DriftReport)

    def test_change_count(self, adapter: TerraformAdapter, plan: dict) -> None:
        result = adapter.consume_terraform_plan(plan)
        # 1 create + 1 update + 1 delete = 3 changes (no-op excluded)
        assert result.details["total_changes"] == 3

    def test_create_action_counted(self, adapter: TerraformAdapter, plan: dict) -> None:
        result = adapter.consume_terraform_plan(plan)
        assert result.details["creates"] == 1

    def test_delete_severity_high(self, adapter: TerraformAdapter, plan: dict) -> None:
        result = adapter.consume_terraform_plan(plan)
        # Overall severity should be "high" because of the delete action
        assert result.severity == "high"

    def test_noop_excluded(self, adapter: TerraformAdapter, plan: dict) -> None:
        result = adapter.consume_terraform_plan(plan)
        resources = result.details.get("resources", {})
        # azurerm_resource_group.governance is no-op, should not appear
        assert "azurerm_resource_group.governance" not in resources

    def test_update_diff_in_details(self, adapter: TerraformAdapter, plan: dict) -> None:
        result = adapter.consume_terraform_plan(plan)
        resources = result.details.get("resources", {})
        web = resources.get("aws_instance.web", {})
        assert "instance_type" in web.get("diff", {})


class TestDetectTerraformDrift:
    """Three-way drift detection tests."""

    def test_aligned_returns_clean(self, adapter: TerraformAdapter) -> None:
        state = {
            "version": 4,
            "resources": [
                {
                    "mode": "managed",
                    "type": "aws_instance",
                    "name": "web",
                    "provider": 'provider["registry.terraform.io/hashicorp/aws"]',
                    "instances": [{"attributes": {"id": "i-123", "instance_type": "t3.micro"}}],
                }
            ],
        }
        hcl = 'resource "aws_instance" "web" {\n  instance_type = "t3.micro"\n}\n'
        live_claim = ClaimObject(
            claim_id="terraform:aws:aws_instance:web",
            entity="terraform:aws_instance:web",
            fields={
                "resource_type": "aws_instance",
                "resource_name": "web",
                "provider": "aws",
                "attributes": {"id": "i-123", "instance_type": "t3.micro"},
            },
            source="terraform",
            provenance_hash="abc",
        )
        result = adapter.detect_terraform_drift([live_claim], tf_state=state, tf_config=hcl)
        assert isinstance(result, DriftReport)
        assert result.drift_type == "terraform-three-way"

    def test_drift_detected_when_mismatched(self, adapter: TerraformAdapter) -> None:
        state = {
            "version": 4,
            "resources": [
                {
                    "mode": "managed",
                    "type": "aws_instance",
                    "name": "web",
                    "provider": 'provider["registry.terraform.io/hashicorp/aws"]',
                    "instances": [{"attributes": {"id": "i-123", "instance_type": "t3.micro"}}],
                }
            ],
        }
        # Empty live = everything in state is "removed" from live perspective
        result = adapter.detect_terraform_drift([], tf_state=state)
        assert result.details["summary"]["drift_count"] > 0
        assert result.severity == "high"


class TestGenerateTerraformEvidence:
    """Evidence bundle generation tests."""

    @pytest.fixture
    def state(self) -> dict:
        import json

        path = Path(__file__).parent / "fixtures" / "terraform.tfstate"
        return json.loads(path.read_text())

    def test_returns_evidence_object(self, adapter: TerraformAdapter, state: dict) -> None:
        result = adapter.generate_terraform_evidence(state_snapshot=state)
        assert isinstance(result, EvidenceObject)

    def test_provenance_chain_complete(self, adapter: TerraformAdapter, state: dict) -> None:
        result = adapter.generate_terraform_evidence(state_snapshot=state)
        assert result.provenance["adapter_id"] == "terraform"
        assert "hash" in result.provenance
        assert "timestamp" in result.provenance

    def test_raw_data_includes_state(self, adapter: TerraformAdapter, state: dict) -> None:
        result = adapter.generate_terraform_evidence(state_snapshot=state)
        assert "state_snapshot" in result.raw_data
        assert "connection" in result.raw_data

    def test_normalized_data_has_claims(self, adapter: TerraformAdapter, state: dict) -> None:
        result = adapter.generate_terraform_evidence(state_snapshot=state)
        assert result.normalized_data is not None
        assert "claims" in result.normalized_data
        assert len(result.normalized_data["claims"]) == 4  # 4 managed resources

    def test_source_is_terraform(self, adapter: TerraformAdapter, state: dict) -> None:
        result = adapter.generate_terraform_evidence(state_snapshot=state)
        assert result.source == "terraform"


# ---------------------------------------------------------------------------
# Convenience: collect_and_align
# ---------------------------------------------------------------------------


class TestCollectAndAlign:
    def test_returns_dict(self, adapter: TerraformAdapter) -> None:
        result = adapter.collect_and_align()
        assert isinstance(result, dict)

    def test_vendor_field(self, adapter: TerraformAdapter) -> None:
        result = adapter.collect_and_align()
        assert result["vendor"] == "Terraform / OpenTofu"

    def test_adapter_id_field(self, adapter: TerraformAdapter) -> None:
        result = adapter.collect_and_align()
        assert result["adapter_id"] == "terraform"

    def test_metadata_workspace(self, adapter: TerraformAdapter) -> None:
        result = adapter.collect_and_align()
        assert result["metadata"]["workspace"] == "prod"

    def test_empty_claims_on_stub(self, adapter: TerraformAdapter) -> None:
        result = adapter.collect_and_align()
        assert result["claims"]["claims"] == []
