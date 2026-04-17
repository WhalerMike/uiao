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
            state_source: Path to .tfstate file (local path or URI).
                          Currently supports local files only.
            workspace: Terraform workspace name (default: "default")
            resource_filter: Optional resource type filter (e.g., "aws_instance")

        Returns:
            ClaimSet with one ClaimObject per managed resource.
        """
        import json
        from pathlib import Path

        from .terraform_parser import parse_tfstate

        path = Path(state_source.replace("local://", ""))
        state_json = json.loads(path.read_text(encoding="utf-8"))
        raw_resources = parse_tfstate(state_json)

        # Apply optional filter
        if resource_filter:
            raw_resources = [r for r in raw_resources if r["type"] == resource_filter]

        # Filter by mode — skip data sources by default for managed-only
        managed = [r for r in raw_resources if r.get("mode") == "managed"]

        return self.normalize(managed)

    def parse_hcl_config(
        self,
        hcl_content_or_path: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> ClaimSet:
        """Treat desired-state HCL as a policy/truth source.

        Args:
            hcl_content_or_path: Raw HCL string or path to .tf file
            variables: Variable overrides for interpolation

        Returns:
            ClaimSet representing the declared desired state.
        """
        from pathlib import Path

        from .terraform_parser import parse_hcl

        path = Path(hcl_content_or_path)
        hcl_content = path.read_text(encoding="utf-8") if path.exists() and path.is_file() else hcl_content_or_path

        raw_resources = parse_hcl(hcl_content, variables)
        return self.normalize(raw_resources)

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
        from .terraform_parser import parse_plan_json

        changes = parse_plan_json(plan_json)

        # Determine overall severity from the worst action
        severities = [c["severity"] for c in changes]
        if "high" in severities:
            overall_severity = "high"
        elif "warning" in severities:
            overall_severity = "warning"
        else:
            overall_severity = "info"

        # Build per-resource detail
        resource_details: Dict[str, Any] = {}
        for c in changes:
            resource_details[c["address"]] = {
                "actions": c["actions"],
                "severity": c["severity"],
                "diff": c["diff"],
            }

        return DriftReport(
            drift_type="terraform-plan",
            severity=overall_severity,
            first_observed=self._now(),
            last_observed=self._now(),
            details={
                "adapter": self.ADAPTER_ID,
                "workspace": workspace or self._workspace,
                "total_changes": len(changes),
                "creates": sum(1 for c in changes if "create" in c["actions"]),
                "updates": sum(1 for c in changes if "update" in c["actions"]),
                "deletes": sum(1 for c in changes if "delete" in c["actions"]),
                "resources": resource_details,
            },
            remediation=(
                f"Review {len(changes)} planned change(s). "
                f"Run `terraform apply` to reconcile, or update HCL config "
                f"to match current state."
            ),
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
        from .terraform_parser import parse_hcl, parse_tfstate, three_way_diff

        # Convert live claims to resource dicts for comparison
        live_resources = [
            {
                "type": c.fields.get("resource_type", c.entity.split(":")[1] if ":" in c.entity else ""),
                "name": c.fields.get("resource_name", c.entity.split(":")[-1] if ":" in c.entity else ""),
                "provider": c.fields.get("provider", ""),
                "mode": "managed",
                "attributes": c.fields,
            }
            for c in live_claims
        ]

        state_resources = parse_tfstate(tf_state) if tf_state else []
        config_resources = parse_hcl(tf_config, None) if tf_config else []

        diff_result = three_way_diff(live_resources, state_resources, config_resources)

        drift_count = diff_result["summary"]["drift_count"]
        severity = "high" if drift_count > 0 else "info"

        return DriftReport(
            drift_type="terraform-three-way",
            severity=severity,
            first_observed=self._now(),
            last_observed=self._now(),
            details={
                "adapter": self.ADAPTER_ID,
                "workspace": self._workspace,
                "live_vs_state": diff_result["live_vs_state"],
                "state_vs_config": diff_result["state_vs_config"],
                "summary": diff_result["summary"],
            },
            remediation=(
                f"{drift_count} resource(s) drifted across state/config/live. "
                f"Run `terraform plan` to see proposed changes, then "
                f"`terraform apply` to reconcile."
                if drift_count > 0
                else "All resources aligned across live, state, and config."
            ),
        )

    def generate_terraform_evidence(
        self,
        plan_or_apply_json: Optional[Dict[str, Any]] = None,
        state_snapshot: Optional[Dict[str, Any]] = None,
    ) -> EvidenceObject:
        """Generate a KSI evidence bundle for a Terraform run.

        Bundles connection provenance, state snapshot, plan/apply output,
        and drift detection results into a canonical EvidenceObject
        suitable for OSCAL artifact generation downstream.

        Args:
            plan_or_apply_json: JSON output from terraform plan/apply
            state_snapshot: Current state file contents

        Returns:
            EvidenceObject with full provenance chain.
        """
        conn = self.connect()
        drift = self.detect_drift()

        # Build raw data bundle
        raw_data: Dict[str, Any] = {
            "connection": conn.to_dict(),
            "drift": drift.to_dict(),
        }
        if plan_or_apply_json:
            raw_data["plan"] = plan_or_apply_json
        if state_snapshot:
            raw_data["state_snapshot"] = state_snapshot

        # Normalize state if provided
        normalized = None
        if state_snapshot:
            from .terraform_parser import parse_tfstate
            try:
                resources = parse_tfstate(state_snapshot)
                managed = [r for r in resources if r.get("mode") == "managed"]
                claim_set = self.normalize(managed)
                normalized = claim_set.to_dict()
            except Exception:
                normalized = None

        return EvidenceObject(
            ksi_id=f"KSI-TF-{self._workspace}",
            source=self.ADAPTER_ID,
            timestamp=self._now(),
            raw_data=raw_data,
            normalized_data=normalized,
            provenance={
                "adapter_id": self.ADAPTER_ID,
                "workspace": self._workspace,
                "hash": self._hash(raw_data),
                "timestamp": self._now().isoformat(),
            },
            freshness_valid=True,
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
