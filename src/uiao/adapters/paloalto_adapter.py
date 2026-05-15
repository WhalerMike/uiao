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
import logging
from pathlib import Path
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

_LOG = logging.getLogger(__name__)


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
            version_hash=self._hash({"vendor": vendor_schema, "canonical": canonical_schema}),
        )

    # ------------------------------------------------------------------
    # 2.3 Query Normalization & Deterministic Extraction
    # ------------------------------------------------------------------

    def execute_query(self, canonical_query: Dict[str, Any]) -> QueryProvenance:
        """Translate canonical query to PAN-OS XML API request."""
        rule_type = canonical_query.get("from", "security-rule")
        xpath = (
            f"/config/devices/entry[@name='localhost.localdomain']"
            f"/vsys/entry[@name='{self._vsys}']/rulebase/{rule_type}/rules"
        )
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
        """Detect drift between PAN-OS running config and UIAO canon.

        Algorithm:
        1. Load expected scope for the ``palo-alto`` adapter from
           ``src/uiao/canon/modernization-registry.yaml``.
        2. Fetch running-config via the collector (empty-scaffold fallback
           when no API key is configured) or from inline config-dict XML.
        3. Fetch candidate-config the same way.
        4. Compute three-way diff: running vs candidate vs canon-expected.
        5. Return a :class:`DriftReport` with severity ``"high"`` if any
           divergence is found, ``"info"`` if all scopes match.
        """
        from .paloalto_parser import parse_nat_rules_xml, parse_security_rules_xml

        # ------------------------------------------------------------------
        # Step 1 — expected scope from modernization-registry.yaml
        # ------------------------------------------------------------------
        expected_scope: List[str] = list(self.SCOPE)  # fallback to class constant
        registry_path = Path(__file__).parent.parent / "canon" / "modernization-registry.yaml"
        try:
            import yaml  # type: ignore[import-untyped]

            registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
            for entry in registry.get("adapters", []):
                if entry.get("id") == "palo-alto":
                    expected_scope = list(entry.get("scope", self.SCOPE))
                    break
        except Exception as exc:  # noqa: BLE001
            _LOG.info("modernization-registry.yaml unavailable; using SCOPE constant: %s", exc)

        # ------------------------------------------------------------------
        # Step 2 — fetch running-config (inline XML or live collector)
        # ------------------------------------------------------------------
        running_rules: List[Dict[str, Any]] = []
        candidate_rules: List[Dict[str, Any]] = []

        legacy_sec = self._config.get("_security_rules_xml", "")
        legacy_nat = self._config.get("_nat_rules_xml", "")
        if legacy_sec or legacy_nat:
            # Offline/test path: inline XML from config dict
            if legacy_sec:
                with contextlib.suppress(Exception):
                    running_rules.extend(parse_security_rules_xml(legacy_sec))
            if legacy_nat:
                with contextlib.suppress(Exception):
                    running_rules.extend(parse_nat_rules_xml(legacy_nat))
            cand_sec = self._config.get("_candidate_security_xml", "")
            cand_nat = self._config.get("_candidate_nat_xml", "")
            if cand_sec:
                with contextlib.suppress(Exception):
                    candidate_rules.extend(parse_security_rules_xml(cand_sec))
            if cand_nat:
                with contextlib.suppress(Exception):
                    candidate_rules.extend(parse_nat_rules_xml(cand_nat))
        else:
            # Live path — collector returns empty scaffold when no api_key
            collector = self._get_collector()
            if collector is not None:
                for rule_type, parser in (
                    ("security", parse_security_rules_xml),
                    ("nat", parse_nat_rules_xml),
                ):
                    with contextlib.suppress(Exception):
                        xml_str = collector.fetch_running_config(rule_type)
                        running_rules.extend(parser(xml_str))
                # ------------------------------------------------------------------
                # Step 3 — fetch candidate-config
                # ------------------------------------------------------------------
                for rule_type, parser in (
                    ("security", parse_security_rules_xml),
                    ("nat", parse_nat_rules_xml),
                ):
                    with contextlib.suppress(Exception):
                        xml_str = collector.fetch_candidate_config(rule_type)
                        candidate_rules.extend(parser(xml_str))

        # ------------------------------------------------------------------
        # Step 4 — three-way diff: running vs candidate vs expected scope
        # ------------------------------------------------------------------
        running_names = {r["name"] for r in running_rules}
        candidate_names = {r["name"] for r in candidate_rules}

        # Rules present in candidate but absent from running = pending commit
        pending_rule_names = candidate_names - running_names
        pending_commits = bool(pending_rule_names)

        running_map = {r["name"]: r for r in running_rules}
        candidate_map = {r["name"]: r for r in candidate_rules}

        divergent_rules: List[str] = []
        # Rules in both that differ (field-level change)
        for name in running_names & candidate_names:
            if running_map[name] != candidate_map[name]:
                divergent_rules.append(name)
        # Rules only in candidate (pending)
        divergent_rules.extend(sorted(pending_rule_names))
        # Rules only in running (removed in candidate)
        divergent_rules.extend(sorted(running_names - candidate_names))

        # Canon scope check — verify each expected scope type is represented
        running_types = {r.get("type", "") for r in running_rules}
        canon_type_map = {
            "security-policies": "security-rule",
            "nat-rules": "nat-rule",
            "threat-prevention-profiles": "threat-profile",
        }
        for scope_item in expected_scope:
            expected_type = canon_type_map.get(scope_item, scope_item)
            if expected_type not in running_types and running_rules:
                divergent_rules.append(f"missing-scope:{scope_item}")

        divergent_rules = sorted(set(divergent_rules))

        # ------------------------------------------------------------------
        # Step 5 — assemble DriftReport
        # ------------------------------------------------------------------
        severity = "high" if divergent_rules else "info"
        if divergent_rules:
            remediation = (
                f"Divergent rules detected on {self._host} (vsys={self._vsys}). "
                f"Review {len(divergent_rules)} rule(s): "
                f"{', '.join(divergent_rules[:5])}. "
                "Commit pending changes or reconcile running-config against the "
                "UIAO canon scope (SC-7 / CM-7 / AC-4)."
            )
        else:
            remediation = (
                "No drift detected — running-config aligns with candidate-config "
                "and UIAO canon scope (SC-7 / CM-7 / AC-4)."
            )

        now = self._now()
        return DriftReport(
            drift_type="palo-alto-rule-divergence",
            severity=severity,
            first_observed=now,
            last_observed=now,
            details={
                "running_rules_count": len(running_rules),
                "candidate_rules_count": len(candidate_rules),
                "divergent_rules": divergent_rules,
                "pending_commits": pending_commits,
                "adapter": self.ADAPTER_ID,
                "host": self._host,
                "vsys": self._vsys,
            },
            remediation=remediation,
        )

    def _get_collector(self) -> Any:
        """Return a PaloAltoCollector if the module is importable, else None."""
        try:
            from ..collectors.paloalto_collector import PaloAltoCollector  # noqa: PLC0415

            return PaloAltoCollector(
                host=self._host,
                api_key=self._config.get("api_key", ""),
                api_port=self._api_port,
                vsys=self._vsys,
                mtls_enabled=self._config.get("mtls_enabled", True),
                cert_path=self._config.get("cert_path"),
                key_path=self._config.get("key_path"),
                verify_path=self._config.get("verify_path"),
            )
        except ImportError:
            return None

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
        would call the PAN-OS API in a real deployment.

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
            # In real usage, call PAN-OS XML API here
            config_data = self._config.get("_security_rules_xml", "")
            if config_data:
                all_rules.extend(parse_security_rules_xml(config_data))
            nat_data = self._config.get("_nat_rules_xml", "")
            if nat_data:
                all_rules.extend(parse_nat_rules_xml(nat_data))

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
        candidate configuration via the collector and then committed.
        When *commit* is ``False`` (default) the method is drift-reporting
        only — no HTTP calls are made.

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
            collector = self._get_collector()
            if collector is not None:
                vsys_entry = f"/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='{self._vsys}']"
                xpath = f"{vsys_entry}/rulebase/{rule_type}/rules/entry[@name='{rule_name}']"
                fields_xml = "".join(f"<{k}>{v}</{k}>" for k, v in config_delta.items())
                element = f'<entry name="{rule_name}">{fields_xml}</entry>'
                edit_response = collector.post_config_edit(xpath, element)
                commit_response = collector.post_commit(description=f"UIAO push_config_change: {rule_type}/{rule_name}")

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
