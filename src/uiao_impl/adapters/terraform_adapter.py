"""
UIAO Terraform / OpenTofu Evidence Adapter — DNS-style alignment only.

Consumes Terraform / OpenTofu state, plans, and HCL configuration to
produce object-keyed canonical claims with KSI provenance.  Supports
three-way drift detection (live system vs Terraform state vs HCL config)
and controlled change-making actions against target environments.

Classification (per uiao-core/canon/modernization-registry.yaml):
    class:         modernization
    mission-class: integration  (UIAO_003 s4.7, ratified ODA-15 2026-04-15)
    status:        reserved     (-> active once tests pass and canon is bumped)

This adapter is intentionally lightweight and sits OUTSIDE the main data
path.  Its only job: create alignments (vendor-overlay + claim + evidence
hash).  It does NOT perform OSCAL JSON, SSP, POA+M, or SBOM conversions.
Those happen downstream in src/uiao_impl/generators/.

Analogy: like a DNS resolver -- it tells the engine HOW to get there;
the generators/ layer does the actual conversion work.

File: src/uiao_impl/adapters/terraform_adapter.py
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .database_base import (
    ClaimObject,
    ClaimSet,
    ConnectionProvenance,
    DatabaseAdapterBase,
    DriftReport,
    EvidenceObject,
    QueryProvenance,
    SchemaMappingObject,
)


class TerraformAdapter(DatabaseAdapterBase):
    """
    Terraform / OpenTofu adapter -- DNS-style alignment only.

    Implements the canonical UIAO adapter pattern (7 responsibility domains)
    plus five Terraform-specific extension methods:

    - extract_terraform_state   (state file -> ClaimSet)
    - parse_hcl_config          (HCL -> ClaimSet)
    - consume_terraform_plan    (plan JSON -> DriftReport)
    - detect_terraform_drift    (three-way: live vs state vs HCL)
    - generate_terraform_evidence (run artifacts -> EvidenceObject)

    This adapter never owns or duplicates data.  SSOT remains in the YAML
    canon.  All methods are sync (matching DatabaseAdapterBase contract).
    """

    ADAPTER_ID: str = "terraform"

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        super().__init__(config or {})
        self._state_source: str = self._config.get("state_source", "")
        self._workspace: str = self._config.get("workspace", "default")

    # ------------------------------------------------------------------
    # 2.1 Connection & Identity
    # ------------------------------------------------------------------

    def connect(self) -> ConnectionProvenance:
        """Establish connection to Terraform state backend and return provenance."""
        return ConnectionProvenance(
            identity=f"terraform:{self._workspace}",
            auth_method=self._config.get("auth_method", "local-file"),
            endpoint=self._state_source or "local://terraform.tfstate",
            tls_version=self._config.get("tls_version"),
            mtls_enabled=self._config.get("mtls_enabled", False),
            timestamp=self._now(),
        )

    # ------------------------------------------------------------------
    # 2.2 Schema Discovery & Canonical Mapping
    # ------------------------------------------------------------------

    def discover_schema(self) -> SchemaMappingObject:
        """Map Terraform resource types to UIAO canonical schema."""
        vendor_schema: Dict[str, Any] = {
            "resource_type": "string",
            "resource_name": "string",
            "provider": "string",
            "attributes": "map",
            "dependencies": "list",
        }
        canonical_schema: Dict[str, Any] = {
            "identity": "terraform:<provider>:<resource_type>:<resource_name>",
            "control_id": "<mapped from resource_type>",
            "implementation_statement": "<resource config summary>",
            "evidence.source": "terraform",
            "evidence.timestamp": "<collected_at>",
            "evidence.record_hash": "sha256(<state_entry>)",
        }
        mapping_rules: Dict[str, Any] = {
            "resource_type": "entity type suffix",
            "resource_name": "entity name suffix",
            "provider": "identity prefix",
            "attributes": "fields (flattened)",
        }
        return SchemaMappingObject(
            vendor_schema=vendor_schema,
            canonical_schema=canonical_schema,
            mapping_rules=mapping_rules,
            unmapped_fields=["dependencies", "meta", "terraform_version"],
            version_hash=self._hash(
                {"vendor": vendor_schema, "canonical": canonical_schema}
            ),
        )

    # ------------------------------------------------------------------
    # 2.3 Query Normalization & Deterministic Extraction
    # ------------------------------------------------------------------

    def execute_query(self, canonical_query: Dict[str, Any]) -> QueryProvenance:
        """Translate canonical query to Terraform state read operation."""
        resource_type = canonical_query.get("from", "*")
        vendor_query = f"terraform state list -state={self._state_source}"
        if resource_type != "*":
            vendor_query += f" | grep {resource_type}"
        return QueryProvenance(
            canonical_query=canonical_query,
            vendor_query=vendor_query,
            execution_plan_hash=self._hash(vendor_query),
            row_count=0,  # populated after real state parse
            timestamp=self._now(),
        )

    # ------------------------------------------------------------------
    # 2.4 Data Normalization & Claim Construction
    # ------------------------------------------------------------------

    def normalize(self, raw_rows: List[Dict[str, Any]]) -> ClaimSet:
        """Convert raw Terraform state resources into canonical ClaimObjects."""
        claims: List[ClaimObject] = []
        for resource in raw_rows:
            resource_type = resource.get("type", "unknown")
            resource_name = resource.get("name", "unknown")
            provider = resource.get("provider", "unknown")
            claim = ClaimObject(
                claim_id=f"terraform:{provider}:{resource_type}:{resource_name}",
                entity=f"terraform:{resource_type}:{resource_name}",
                fields={
                    "identity": f"terraform:{provider}:{resource_type}:{resource_name}",
                    "resource_type": resource_type,
                    "resource_name": resource_name,
                    "provider": provider,
                    "attributes": resource.get("attributes", {}),
                    "vendor_overlay_ref": "terraform.yaml",
                },
                source=self.ADAPTER_ID,
                provenance_hash=self._hash(resource),
            )
            claims.append(claim)
        return ClaimSet(
            claims=claims,
            source_reference=self._state_source or "local://terraform.tfstate",
        )

    # ------------------------------------------------------------------
    # 2.5 Drift Detection & Version Integrity
    # ------------------------------------------------------------------

    def detect_drift(self) -> DriftReport:
        """Detect drift between Terraform state and UIAO canon."""
        return DriftReport(
            drift_type="terraform-state",
            severity="info",
            first_observed=self._now(),
            last_observed=self._now(),
            details={
                "message": (
                    "Drift detection scaffold -- implement three-way comparison "
                    "(live system vs Terraform state vs HCL configuration) "
                    "via detect_terraform_drift()."
                ),
                "adapter": self.ADAPTER_ID,
                "workspace": self._workspace,
            },
            remediation=(
                "Run detect_terraform_drift() with live_claims, tf_state, "
                "and tf_config for full three-way analysis."
            ),
        )

    # ==================================================================
    # Terraform-Specific Extension Methods
    # ==================================================================
    # These layer on top of the 7 canonical domains and provide the
    # capability surface advertised in the canon registry entry.

    def extract_terraform_state(
        self,
        state_source: str,
        workspace: Optional[str] = None,
        resource_filter: Optional[str] = None,
    ) -> ClaimSet:
        """Convert Terraform-managed resources from a state file into
        pointer-first CanonicalClaims.

        Args:
            state_source: State backend URI (local://, s3://, tfc://, etc.)
            workspace: Terraform workspace name (default: "default")
            resource_filter: Optional resource type filter (e.g., "aws_instance")

        Returns:
            ClaimSet with one ClaimObject per managed resource.
        """
        raise NotImplementedError(
            "extract_terraform_state() is a stub -- scheduled for "
            "implementation when terraform-state parsing is wired up. "
            "See uiao-core/canon/modernization-registry.yaml terraform entry."
        )

    def parse_hcl_config(
        self,
        hcl_content_or_path: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> ClaimSet:
        """Treat desired-state HCL as a policy/truth source.

        Args:
            hcl_content_or_path: Raw HCL string or path to .tf file(s)
            variables: Variable overrides for interpolation

        Returns:
            ClaimSet representing the declared desired state.
        """
        raise NotImplementedError(
            "parse_hcl_config() is a stub -- requires python-hcl2 or "
            "equivalent parser dependency. Scheduled for Stage 3 follow-up."
        )

    def consume_terraform_plan(
        self,
        plan_json: Dict[str, Any],
        workspace: Optional[str] = None,
    ) -> DriftReport:
        """Convert a `terraform plan -json` output into a UIAO DriftReport.

        Each planned action (create/update/delete) becomes a drift item.
        The DriftReport can feed downstream POA&M generation.

        Args:
            plan_json: Parsed JSON from `terraform plan -json`
            workspace: Optional workspace context

        Returns:
            DriftReport with per-resource planned changes as drift items.
        """
        raise NotImplementedError(
            "consume_terraform_plan() is a stub -- scheduled for "
            "implementation. Input: `terraform plan -json` output."
        )

    def detect_terraform_drift(
        self,
        live_claims: List[ClaimObject],
        tf_state: Optional[Dict[str, Any]] = None,
        tf_config: Optional[str] = None,
    ) -> DriftReport:
        """Three-way drift detection: live system vs Terraform state vs HCL.

        Compares:
        1. live_claims (from a live-system adapter or API call)
        2. tf_state (parsed Terraform state file)
        3. tf_config (parsed HCL configuration)

        Args:
            live_claims: ClaimObjects from a live-system query
            tf_state: Parsed Terraform state (optional)
            tf_config: Raw HCL content or path (optional)

        Returns:
            DriftReport covering all three comparison axes.
        """
        raise NotImplementedError(
            "detect_terraform_drift() is a stub -- three-way drift "
            "detection requires extract_terraform_state() and "
            "parse_hcl_config() to be implemented first."
        )

    def generate_terraform_evidence(
        self,
        plan_or_apply_json: Optional[Dict[str, Any]] = None,
        state_snapshot: Optional[Dict[str, Any]] = None,
    ) -> EvidenceObject:
        """Generate a signed KSI evidence bundle for a Terraform run.

        Bundles connection provenance, state snapshot, plan/apply output,
        and drift detection results into a canonical EvidenceObject
        suitable for OSCAL artifact generation downstream.

        Args:
            plan_or_apply_json: JSON output from terraform plan/apply
            state_snapshot: Current state file contents

        Returns:
            EvidenceObject with full provenance chain.
        """
        raise NotImplementedError(
            "generate_terraform_evidence() is a stub -- scheduled for "
            "implementation once extract_terraform_state() and "
            "consume_terraform_plan() are wired up."
        )

    # ------------------------------------------------------------------
    # Convenience: collect + normalize in one call
    # ------------------------------------------------------------------

    def collect_and_align(self) -> Dict[str, Any]:
        """Pull state from Terraform backend and return alignment result.

        Returns the ClaimSet as a dict for downstream engine consumption.
        Does NOT generate OSCAL -- that stays in generators/.
        """
        # For the stub implementation, return a scaffold result.
        # Real implementation would call extract_terraform_state().
        claim_set = self.normalize([])
        return {
            "vendor": "Terraform / OpenTofu",
            "adapter_id": self.ADAPTER_ID,
            "vendor_overlay_ref": "data/vendor-overlays/terraform.yaml",
            "claims": claim_set.to_dict(),
            "metadata": {
                "total_records": len(claim_set.claims),
                "last_collected": self._now().isoformat(),
                "state_source": self._state_source,
                "workspace": self._workspace,
            },
        }
