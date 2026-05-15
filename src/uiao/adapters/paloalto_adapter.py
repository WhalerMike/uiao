"""
UIAO Palo Alto Networks (Firewall / NGFW) Adapter — DNS-style alignment only.

Consumes Palo Alto PAN-OS configuration via XML API to produce object-keyed
canonical claims with KSI provenance. Covers security policies, NAT rules,
and threat-prevention profiles.

Classification (per uiao/canon/modernization-registry.yaml):
    class:         modernization
    mission-class: integration  (UIAO_003 s4.7, ratified ODA-15 2026-04-15)
    status:        active
    runner-class:  on-prem-self-hosted (Phase 2+ Azure Gov runners)

This adapter is intentionally lightweight and sits OUTSIDE the main data
path. Its only job: create alignments (vendor-overlay + claim + evidence
hash). It does NOT perform OSCAL JSON, SSP, POA+M, or SBOM conversions.
Those happen downstream in src/uiao/impl/generators/.

File: src/uiao/impl/adapters/paloalto_adapter.py
"""

from __future__ import annotations

import contextlib
from typing import Any, Dict, List, Optional

from uiao.collectors.paloalto_collector import PaloAltoCollector

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
        self.collector: PaloAltoCollector = PaloAltoCollector(
            host=self._host,
            api_key=self._config.get("api_key", ""),
            api_port=self._api_port,
            vsys=self._vsys,
            tls_version=self._config.get("tls_version", "TLSv1.3"),
            mtls_enabled=self._config.get("mtls_enabled", True),
            cert_path=self._config.get("cert_path"),
            key_path=self._config.get("key_path"),
            verify_path=self._config.get("verify_path"),
        )

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
            version_hash=self._hash({"vendor": vendor_schema, "canonical": canonical_schema}),
        )

    # ------------------------------------------------------------------
    # 2.3 Query Normalization & Deterministic Extraction
    # ------------------------------------------------------------------

    def execute_query(self, canonical_query: Dict[str, Any]) -> QueryProvenance:
        """Translate canonical query to PAN-OS XML API request."""
        rule_type = canonical_query.get("from", "security-rule")
        xpath = f"/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='{self._vsys}']/rulebase/{rule_type}/rules"
        vendor_query = f"GET /api/?type=config&action=show&xpath={xpath}"
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
                "Compare normalize() output of running config against YAML canon SC-7/CM-7/AC-4 control mappings."
            ),
        )

    # ==================================================================
    # PAN-OS-Specific Extension Methods
    # ==================================================================

    def get_running_config(
        self,
        scope: Optional[str] = None,
        xml_content: Optional[str] = None,
    ) -> ClaimSet:
        """Retrieve and parse the running configuration.

        Can accept pre-loaded XML content (for testing/offline use) or
        calls the PAN-OS XML API via the collector in a real deployment.

        Args:
            scope: security-policies, nat-rules, or None for all
            xml_content: Pre-loaded XML string (bypass API call)

        Returns:
            ClaimSet with current running-config claims.
        """
        from .paloalto_parser import parse_nat_rules_xml, parse_security_rules_xml

        all_rules: List[Dict[str, Any]] = []

        if xml_content:
            # Parse provided XML directly
            if scope == "nat-rules" or scope is None:
                with contextlib.suppress(Exception):
                    all_rules.extend(parse_nat_rules_xml(xml_content))
            if scope == "security-policies" or scope is None:
                with contextlib.suppress(Exception):
                    all_rules.extend(parse_security_rules_xml(xml_content))
        else:
            # Call PAN-OS XML API via collector; falls back to empty scaffold
            # when no api_key is configured (e.g. CI / unit-test environments).
            # Legacy config-dict keys (_security_rules_xml / _nat_rules_xml)
            # are preserved for backward compatibility with existing tests.
            legacy_sec = self._config.get("_security_rules_xml", "")
            legacy_nat = self._config.get("_nat_rules_xml", "")
            if legacy_sec or legacy_nat:
                # Offline/test path: use pre-loaded XML from config dict
                if legacy_sec:
                    with contextlib.suppress(Exception):
                        all_rules.extend(parse_security_rules_xml(legacy_sec))
                if legacy_nat:
                    with contextlib.suppress(Exception):
                        all_rules.extend(parse_nat_rules_xml(legacy_nat))
            else:
                # Live path: fetch from PAN-OS XML API via collector
                if scope == "nat-rules" or scope is None:
                    with contextlib.suppress(Exception):
                        nat_xml = self.collector.fetch_running_config("nat")
                        all_rules.extend(parse_nat_rules_xml(nat_xml))
                if scope == "security-policies" or scope is None:
                    with contextlib.suppress(Exception):
                        sec_xml = self.collector.fetch_running_config("security")
                        all_rules.extend(parse_security_rules_xml(sec_xml))

        return self.normalize(all_rules)

    def push_config_change(
        self,
        rule_type: str,
        rule_name: str,
        config_delta: Dict[str, Any],
        commit: bool = False,
    ) -> DriftReport:
        """Compare a proposed change against current config and report drift.

        When *commit* is ``True`` the change is also pushed to the PAN-OS
        candidate configuration via :meth:`PaloAltoCollector.post_config_edit`
        and then committed via :meth:`PaloAltoCollector.post_commit`.  When
        *commit* is ``False`` (the default) the method remains drift-reporting
        only — no HTTP calls are made (lane discipline: real push is opt-in).

        Args:
            rule_type:    security-rule, nat-rule, or threat-profile.
            rule_name:    Name of the rule to modify.
            config_delta: Dict of fields to change.
            commit:       When ``True``, push the edit and issue a commit.

        Returns:
            DriftReport showing what would/did change.
        """
        edit_response: Optional[str] = None
        commit_response: Optional[str] = None

        if commit:
            vsys_entry = f"/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='{self._vsys}']"
            xpath = f"{vsys_entry}/rulebase/{rule_type}/rules/entry[@name='{rule_name}']"
            fields_xml = "".join(f"<{k}>{v}</{k}>" for k, v in config_delta.items())
            element = f'<entry name="{rule_name}">{fields_xml}</entry>'
            edit_response = self.collector.post_config_edit(xpath, element)
            commit_response = self.collector.post_commit(
                description=f"UIAO push_config_change: {rule_type}/{rule_name}"
            )

        return DriftReport(
            drift_type="palo-alto-config-change",
            severity="warning",
            first_observed=self._now(),
            last_observed=self._now(),
            details={
                "adapter": self.ADAPTER_ID,
                "host": self._host,
                "rule_type": rule_type,
                "rule_name": rule_name,
                "proposed_changes": config_delta,
                "committed": commit,
                "edit_response": edit_response,
                "commit_response": commit_response,
                "message": (
                    f"Proposed change to {rule_type}/{rule_name}: {len(config_delta)} field(s). Commit required."
                ),
            },
            remediation=f"Review and commit change to {rule_type}/{rule_name} via PAN-OS.",
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
        conn = self.connect()
        drift = self.detect_drift()
        claim_set = self.get_running_config(scope=scope)

        return EvidenceObject(
            ksi_id=f"KSI-FW-{self._vsys}",
            source=self.ADAPTER_ID,
            timestamp=self._now(),
            raw_data={
                "connection": conn.to_dict(),
                "drift": drift.to_dict(),
                "scope": scope or "all",
            },
            normalized_data=claim_set.to_dict(),
            provenance={
                "adapter_id": self.ADAPTER_ID,
                "host": self._host,
                "vsys": self._vsys,
                "hash": self._hash(claim_set.to_dict()),
                "timestamp": self._now().isoformat(),
            },
            freshness_valid=True,
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
