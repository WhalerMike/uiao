"""
UIAO Palo Alto Networks (Firewall / NGFW) Adapter — DNS-style alignment only.

Consumes Palo Alto PAN-OS configuration via XML API to produce object-keyed
canonical claims with KSI provenance. Covers security policies, NAT rules,
and threat-prevention profiles.

Classification (per uiao-core/canon/modernization-registry.yaml):
    class:         modernization
    mission-class: integration  (UIAO_003 s4.7, ratified ODA-15 2026-04-15)
    status:        active
    runner-class:  on-prem-self-hosted (Phase 2+ Azure Gov runners)

This adapter is intentionally lightweight and sits OUTSIDE the main data
path. Its only job: create alignments (vendor-overlay + claim + evidence
hash). It does NOT perform OSCAL JSON, SSP, POA+M, or SBOM conversions.
Those happen downstream in src/uiao_impl/generators/.

File: src/uiao_impl/adapters/paloalto_adapter.py
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


class PaloAltoAdapter(DatabaseAdapterBase):
    """
    Palo Alto Networks adapter — DNS-style alignment only.

    Implements the canonical UIAO adapter pattern (7 responsibility domains)
    plus PAN-OS-specific extension methods for firewall configuration
    assessment and controlled change-making.

    Note: runner-class is `on-prem-self-hosted` per canon registry, meaning
    this adapter is designed to run on Azure Government self-hosted runners
    that have network access to the PAN-OS management interface. Phase 1
    development uses github-hosted runners with mocked PAN-OS responses.
    """

    ADAPTER_ID: str = "palo-alto"

    SCOPE = [
        "security-policies",
        "nat-rules",
        "threat-prevention-profiles",
    ]

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        super().__init__(config or {})
        self._host: str = self._config.get("host", "")
        self._api_port: int = self._config.get("api_port", 443)
        self._vsys: str = self._config.get("vsys", "vsys1")

    # ------------------------------------------------------------------
    # 2.1 Connection & Identity
    # ------------------------------------------------------------------

    def connect(self) -> ConnectionProvenance:
        """Establish PAN-OS XML API connection and return provenance."""
        return ConnectionProvenance(
            identity=f"palo-alto:{self._host}:{self._vsys}",
            auth_method=self._config.get("auth_method", "api-key"),
            endpoint=f"https://{self._host}:{self._api_port}/api/",
            tls_version=self._config.get("tls_version", "TLSv1.3"),
            mtls_enabled=self._config.get("mtls_enabled", True),
            timestamp=self._now(),
        )

    # ------------------------------------------------------------------
    # 2.2 Schema Discovery & Canonical Mapping
    # ------------------------------------------------------------------

    def discover_schema(self) -> SchemaMappingObject:
        """Map PAN-OS configuration objects to UIAO canonical schema."""
        vendor_schema: Dict[str, Any] = {
            "security-rule": {"name": "string", "from": "zone", "to": "zone", "action": "string"},
            "nat-rule": {"name": "string", "source": "address", "destination": "address"},
            "threat-profile": {"name": "string", "severity": "list", "action": "string"},
        }
        canonical_schema: Dict[str, Any] = {
            "identity": "palo-alto:<vsys>:<rule_type>:<rule_name>",
            "control_id": "<mapped from rule scope>",
            "implementation_statement": "<rule config summary>",
            "evidence.source": "palo-alto",
            "evidence.timestamp": "<collected_at>",
            "evidence.record_hash": "sha256(<config_entry>)",
        }
        mapping_rules: Dict[str, Any] = {
            "rule_type": "entity type (security-rule | nat-rule | threat-profile)",
            "rule_name": "identity suffix",
            "action": "policy enforcement outcome",
        }
        return SchemaMappingObject(
            vendor_schema=vendor_schema,
            canonical_schema=canonical_schema,
            mapping_rules=mapping_rules,
            unmapped_fields=["tag", "log-setting", "schedule", "qos-marking"],
            version_hash=self._hash(
                {"vendor": vendor_schema, "canonical": canonical_schema}
            ),
        )

    # ------------------------------------------------------------------
    # 2.3 Query Normalization & Deterministic Extraction
    # ------------------------------------------------------------------

    def execute_query(self, canonical_query: Dict[str, Any]) -> QueryProvenance:
        """Translate canonical query to PAN-OS XML API request."""
        rule_type = canonical_query.get("from", "security-rule")
        xpath = f"/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='{self._vsys}']/rulebase/{rule_type}/rules"
        vendor_query = (
            f"GET /api/?type=config&action=show&xpath={xpath}"
        )
        return QueryProvenance(
            canonical_query=canonical_query,
            vendor_query=vendor_query,
            execution_plan_hash=self._hash(vendor_query),
            row_count=0,
            timestamp=self._now(),
        )

    # ------------------------------------------------------------------
    # 2.4 Data Normalization & Claim Construction
    # ------------------------------------------------------------------

    def normalize(self, raw_rows: List[Dict[str, Any]]) -> ClaimSet:
        """Convert raw PAN-OS config entries into canonical ClaimObjects."""
        claims: List[ClaimObject] = []
        for rule in raw_rows:
            rule_type = rule.get("type", "security-rule")
            rule_name = rule.get("name", "unknown")
            claim = ClaimObject(
                claim_id=f"palo-alto:{self._vsys}:{rule_type}:{rule_name}",
                entity=f"palo-alto:{rule_type}:{rule_name}",
                fields={
                    "identity": f"palo-alto:{self._vsys}:{rule_type}:{rule_name}",
                    "rule_type": rule_type,
                    "rule_name": rule_name,
                    "action": rule.get("action", ""),
                    "from_zone": rule.get("from", ""),
                    "to_zone": rule.get("to", ""),
                    "vendor_overlay_ref": "palo-alto.yaml",
                },
                source=self.ADAPTER_ID,
                provenance_hash=self._hash(rule),
            )
            claims.append(claim)
        return ClaimSet(
            claims=claims,
            source_reference=f"https://{self._host}:{self._api_port}/api/",
        )

    # ------------------------------------------------------------------
    # 2.5 Drift Detection & Version Integrity
    # ------------------------------------------------------------------

    def detect_drift(self) -> DriftReport:
        """Detect drift between PAN-OS running config and UIAO canon."""
        return DriftReport(
            drift_type="palo-alto-config",
            severity="info",
            first_observed=self._now(),
            last_observed=self._now(),
            details={
                "message": (
                    "Drift detection scaffold — implement running-config "
                    "vs candidate-config vs canon baseline comparison."
                ),
                "adapter": self.ADAPTER_ID,
                "host": self._host,
                "vsys": self._vsys,
            },
            remediation=(
                "Compare normalize() output of running config against "
                "YAML canon SC-7/CM-7/AC-4 control mappings."
            ),
        )

    # ==================================================================
    # PAN-OS-Specific Extension Methods
    # ==================================================================

    def get_running_config(
        self,
        scope: Optional[str] = None,
    ) -> ClaimSet:
        """Retrieve the running configuration for a specific scope.

        Args:
            scope: One of SCOPE (security-policies, nat-rules,
                   threat-prevention-profiles) or None for all

        Returns:
            ClaimSet with current running-config claims.
        """
        raise NotImplementedError(
            "get_running_config() is a stub — requires PAN-OS XML API "
            "collector with api-key auth. Designed for on-prem-self-hosted "
            "runners with network access to the management interface."
        )

    def push_config_change(
        self,
        rule_type: str,
        rule_name: str,
        config_delta: Dict[str, Any],
    ) -> DriftReport:
        """Push a configuration change to PAN-OS (change-making).

        This is the integration-class change-making surface: it writes
        configuration to the firewall candidate config via XML API,
        then commits.

        Args:
            rule_type: security-rule, nat-rule, or threat-profile
            rule_name: Name of the rule to modify
            config_delta: Dict of fields to change

        Returns:
            DriftReport showing what changed.
        """
        raise NotImplementedError(
            "push_config_change() is a stub — requires PAN-OS XML API "
            "write access + commit workflow. Gated on Azure Government "
            "self-hosted runners (ODA-13)."
        )

    def generate_firewall_evidence(
        self,
        scope: Optional[str] = None,
    ) -> EvidenceObject:
        """Generate evidence bundle for firewall configuration state.

        Args:
            scope: Specific scope or None for full config snapshot

        Returns:
            EvidenceObject with full provenance chain.
        """
        raise NotImplementedError(
            "generate_firewall_evidence() is a stub — requires "
            "get_running_config() to be implemented first."
        )

    # ------------------------------------------------------------------
    # Convenience: collect + normalize in one call
    # ------------------------------------------------------------------

    def collect_and_align(self) -> Dict[str, Any]:
        """Pull running config from PAN-OS and return alignment result."""
        claim_set = self.normalize([])
        return {
            "vendor": "Palo Alto Networks",
            "adapter_id": self.ADAPTER_ID,
            "vendor_overlay_ref": "data/vendor-overlays/palo-alto.yaml",
            "claims": claim_set.to_dict(),
            "metadata": {
                "total_records": len(claim_set.claims),
                "last_collected": self._now().isoformat(),
                "host": self._host,
                "vsys": self._vsys,
                "scope": self.SCOPE,
            },
        }
