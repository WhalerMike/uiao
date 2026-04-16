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

import pytest

from uiao_impl.adapters.terraform_adapter import TerraformAdapter
from uiao_impl.adapters.database_base import (
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
        from uiao_impl.adapters.database_base import DatabaseAdapterBase

        assert isinstance(adapter, DatabaseAdapterBase)


# ---------------------------------------------------------------------------
# 2.1 Connection & Identity
# ---------------------------------------------------------------------------


class TestConnect:
    def test_connect_returns_provenance(self, adapter: TerraformAdapter) -> None:
        result = adapter.connect()
        assert isinstance(result, ConnectionProvenance)

    def test_connect_identity_includes_workspace(
        self, adapter: TerraformAdapter
    ) -> None:
        result = adapter.connect()
        assert "prod" in result.identity

    def test_connect_endpoint_matches_source(
        self, adapter: TerraformAdapter
    ) -> None:
        result = adapter.connect()
        assert result.endpoint == "s3://my-bucket/terraform.tfstate"

    def test_connect_auth_method(self, adapter: TerraformAdapter) -> None:
        result = adapter.connect()
        assert result.auth_method == "iam-role"

    def test_connect_default_endpoint(
        self, adapter_empty: TerraformAdapter
    ) -> None:
        result = adapter_empty.connect()
        assert result.endpoint == "local://terraform.tfstate"


# ---------------------------------------------------------------------------
# 2.2 Schema Discovery
# ---------------------------------------------------------------------------


class TestDiscoverSchema:
    def test_returns_schema_mapping(self, adapter: TerraformAdapter) -> None:
        result = adapter.discover_schema()
        assert isinstance(result, SchemaMappingObject)

    def test_vendor_schema_has_resource_type(
        self, adapter: TerraformAdapter
    ) -> None:
        result = adapter.discover_schema()
        assert "resource_type" in result.vendor_schema

    def test_unmapped_fields_present(self, adapter: TerraformAdapter) -> None:
        result = adapter.discover_schema()
        assert len(result.unmapped_fields) > 0

    def test_version_hash_deterministic(
        self, adapter: TerraformAdapter
    ) -> None:
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

    def test_vendor_query_includes_state_source(
        self, adapter: TerraformAdapter
    ) -> None:
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


class TestTerraformExtensions:
    def test_extract_terraform_state_raises(
        self, adapter: TerraformAdapter
    ) -> None:
        with pytest.raises(NotImplementedError, match="extract_terraform_state"):
            adapter.extract_terraform_state("s3://bucket/state")

    def test_parse_hcl_config_raises(
        self, adapter: TerraformAdapter
    ) -> None:
        with pytest.raises(NotImplementedError, match="parse_hcl_config"):
            adapter.parse_hcl_config("resource {}")

    def test_consume_terraform_plan_raises(
        self, adapter: TerraformAdapter
    ) -> None:
        with pytest.raises(NotImplementedError, match="consume_terraform_plan"):
            adapter.consume_terraform_plan({"format_version": "1.0"})

    def test_detect_terraform_drift_raises(
        self, adapter: TerraformAdapter
    ) -> None:
        with pytest.raises(NotImplementedError, match="detect_terraform_drift"):
            adapter.detect_terraform_drift([])

    def test_generate_terraform_evidence_raises(
        self, adapter: TerraformAdapter
    ) -> None:
        with pytest.raises(
            NotImplementedError, match="generate_terraform_evidence"
        ):
            adapter.generate_terraform_evidence()


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
