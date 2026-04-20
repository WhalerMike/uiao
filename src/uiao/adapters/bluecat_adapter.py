"""
UIAO BlueCat Address Manager (BAM) DNS / IPAM Adapter — alignment only.

Consumes BlueCat Address Manager JSON via the BAM REST v1 API to produce
object-keyed canonical claims with KSI provenance. Covers DNS records,
DHCP scopes, IP allocations, and side-by-side-AD event streams (per
canon scope). Sibling to InfobloxAdapter; the two share IPAM contract
shape but target different vendors.

Classification (per src/uiao/canon/modernization-registry.yaml):
    class:         modernization
    mission-class: integration  (UIAO_003 s4.7, ratified ODA-15 2026-04-15)
    status:        active
    runner-class:  on-prem-self-hosted
    license:       Commercial (not FedRAMP-authorized — federal-preferred
                   sibling is the `infoblox` adapter)

This adapter is intentionally lightweight and sits OUTSIDE the main data
path. Its only job: create alignments (vendor-overlay + claim + evidence
hash). It does NOT perform OSCAL JSON, SSP, POA&M, or SBOM conversions.
Those happen downstream in src/uiao/generators/.

File: src/uiao/adapters/bluecat_adapter.py
"""

from __future__ import annotations

import contextlib
import json
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

_SCOPE_TO_BAM: Dict[str, str] = {
    "dns-records": "getEntitiesByName?type=HostRecord",
    "dhcp-scopes": "getDHCP4Ranges",
    "ip-allocations": "getIP4Address",
    "side-by-side-ad": "event-stream",
}


class BlueCatAdapter(DatabaseAdapterBase):
    """
    BlueCat Address Manager adapter — DNS-style alignment only.

    Implements the canonical UIAO adapter pattern (7 responsibility
    domains) plus BAM-specific extension methods for DNS/IPAM assessment
    and controlled change-making.

    Note: runner-class is `on-prem-self-hosted` per canon registry.
    Offline tests inject BAM JSON via the `_<scope>_json` config keys;
    no live HTTP is performed here.
    """

    ADAPTER_ID: str = "bluecat-address-manager"

    SCOPE = [
        "dns-records",
        "dhcp-scopes",
        "ip-allocations",
        "side-by-side-ad",
    ]

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        super().__init__(config or {})
        self._bam_host: str = self._config.get("bam_host", "")
        self._configuration: str = self._config.get("configuration", "default")
        self._api_version: str = self._config.get("api_version", "v1")

    # ------------------------------------------------------------------
    # 2.1 Connection & Identity
    # ------------------------------------------------------------------

    def connect(self) -> ConnectionProvenance:
        """Establish BAM REST API connection and return provenance."""
        return ConnectionProvenance(
            identity=f"bluecat:{self._bam_host}:{self._configuration}",
            auth_method=self._config.get("auth_method", "api-token"),
            endpoint=f"https://{self._bam_host}/Services/REST/{self._api_version}/",
            tls_version=self._config.get("tls_version", "TLSv1.3"),
            mtls_enabled=self._config.get("mtls_enabled", True),
            timestamp=self._now(),
        )

    # ------------------------------------------------------------------
    # 2.2 Schema Discovery & Canonical Mapping
    # ------------------------------------------------------------------

    def discover_schema(self) -> SchemaMappingObject:
        """Map BAM objects to UIAO canonical schema."""
        vendor_schema: Dict[str, Any] = {
            "HostRecord": {"absoluteName": "string", "addresses": "ipv4", "parentZoneName": "string"},
            "AliasRecord": {"absoluteName": "string", "linkedRecordName": "string"},
            "DHCP4Range": {"start": "ipv4", "end": "ipv4", "network": "cidr"},
            "IP4Address": {"address": "ipv4", "macAddress": "mac", "state": "enum"},
        }
        canonical_schema: Dict[str, Any] = {
            "identity": "bluecat:<configuration>:<object_type>:<ident>",
            "control_id": "<mapped from scope (SC-20 | SC-21 | CM-8)>",
            "implementation_statement": "<object summary>",
            "evidence.source": "bluecat",
            "evidence.timestamp": "<collected_at>",
            "evidence.record_hash": "sha256(<bam_entity>)",
        }
        mapping_rules: Dict[str, Any] = {
            "id": "BAM numeric identity — stable across renames",
            "properties": "pipe-delimited k=v string; expanded by _entity_properties",
            "object_type": "entity type (host-record | alias-record | dhcp-range | ip-address)",
            "configuration": "BAM root container (analog of Infoblox network-view)",
        }
        return SchemaMappingObject(
            vendor_schema=vendor_schema,
            canonical_schema=canonical_schema,
            mapping_rules=mapping_rules,
            unmapped_fields=["ttl", "comments", "deploymentRoles", "udfs"],
            version_hash=self._hash(
                {"vendor": vendor_schema, "canonical": canonical_schema}
            ),
        )

    # ------------------------------------------------------------------
    # 2.3 Query Normalization & Deterministic Extraction
    # ------------------------------------------------------------------

    def execute_query(self, canonical_query: Dict[str, Any]) -> QueryProvenance:
        """Translate canonical query to a BAM REST request."""
        scope = canonical_query.get("from", "dns-records")
        bam_call = _SCOPE_TO_BAM.get(scope, "getEntitiesByName?type=HostRecord")
        separator = "&" if "?" in bam_call else "?"
        vendor_query = (
            f"GET /Services/REST/{self._api_version}/{bam_call}"
            f"{separator}configuration={self._configuration}"
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
        """Convert parsed BAM rows into canonical ClaimObjects.

        Dispatches on `row["type"]` (set by bluecat_parser functions) to
        build per-object-type claim identities. Unknown types fall
        through to a generic entity keyed by `name` or `id`.
        """
        claims: List[ClaimObject] = []
        configuration = self._configuration
        for row in raw_rows:
            rtype = row.get("type", "host-record")
            ident, fields = self._claim_fields(rtype, row)
            claims.append(
                ClaimObject(
                    claim_id=f"bluecat:{configuration}:{rtype}:{ident}",
                    entity=f"bluecat:{rtype}:{ident}",
                    fields={
                        "identity": f"bluecat:{configuration}:{rtype}:{ident}",
                        "object_type": rtype,
                        "vendor_overlay_ref": "bluecat.yaml",
                        **fields,
                    },
                    source=self.ADAPTER_ID,
                    provenance_hash=self._hash(row),
                )
            )
        return ClaimSet(
            claims=claims,
            source_reference=f"https://{self._bam_host}/Services/REST/{self._api_version}/",
        )

    @staticmethod
    def _claim_fields(rtype: str, row: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        """Return (identity suffix, extra fields) for a given record type."""
        if rtype == "host-record":
            return row.get("name", "unknown"), {
                "name": row.get("name", ""),
                "ipv4addr": row.get("ipv4addr", ""),
                "zone": row.get("zone", ""),
            }
        if rtype == "alias-record":
            return row.get("name", "unknown"), {
                "name": row.get("name", ""),
                "canonical": row.get("canonical", ""),
                "zone": row.get("zone", ""),
            }
        if rtype == "dhcp-range":
            start, end = row.get("start", ""), row.get("end", "")
            return f"{start}-{end}", {
                "start": start,
                "end": end,
                "network": row.get("network", ""),
            }
        if rtype == "ip-address":
            return row.get("ipv4addr", "unknown"), {
                "ipv4addr": row.get("ipv4addr", ""),
                "mac": row.get("mac", ""),
                "name": row.get("name", ""),
                "state": row.get("state", ""),
            }
        return row.get("name", str(row.get("id", "unknown"))), {"raw": row}

    # ------------------------------------------------------------------
    # 2.5 Drift Detection & Version Integrity
    # ------------------------------------------------------------------

    def detect_drift(self) -> DriftReport:
        """Compare canon baseline against live BAM snapshot.

        Both sides are sourced from adapter config (injected by callers
        / tests):
          - `baseline_records`: expected record set (from canon snapshot)
          - `live_records`:     current BAM snapshot

        When either side is absent, returns an `info`-severity scaffold
        DriftReport so the adapter remains safe to invoke before wiring.
        """
        from .bluecat_parser import diff_record_sets

        baseline = self._config.get("baseline_records")
        live = self._config.get("live_records")

        if baseline is None or live is None:
            return DriftReport(
                drift_type="bluecat-ipam-config",
                severity="info",
                first_observed=self._now(),
                last_observed=self._now(),
                details={
                    "message": "Drift inputs not configured; skipping comparison.",
                    "adapter": self.ADAPTER_ID,
                    "bam_host": self._bam_host,
                    "configuration": self._configuration,
                },
                remediation=(
                    "Provide `baseline_records` and `live_records` in "
                    "adapter config (lists of parsed BAM rows) to enable "
                    "drift detection."
                ),
            )

        diff = diff_record_sets(baseline, live)
        drift_count = diff["summary"]["drift_count"]
        severity = "high" if drift_count > 0 else "info"
        return DriftReport(
            drift_type="bluecat-ipam-config",
            severity=severity,
            first_observed=self._now(),
            last_observed=self._now(),
            details={
                "adapter": self.ADAPTER_ID,
                "bam_host": self._bam_host,
                "configuration": self._configuration,
                "added": diff["added"],
                "removed": diff["removed"],
                "modified": diff["modified"],
                "summary": diff["summary"],
            },
            remediation=(
                f"{drift_count} record(s) drifted between canon baseline "
                f"and live BAM snapshot. Review and reconcile via BAM."
                if drift_count > 0
                else "Canon baseline matches live BAM snapshot."
            ),
        )

    # ==================================================================
    # BAM-Specific Extension Methods
    # ==================================================================

    def get_all_objects(
        self,
        scope: Optional[str] = None,
        bam_json: Optional[Dict[str, Any]] = None,
    ) -> ClaimSet:
        """Retrieve and parse BAM objects for the requested scope.

        Accepts pre-loaded JSON (for testing/offline use); in production
        a live HTTP client would be wired into this method via
        `_config`.

        Args:
            scope: one of SCOPE; None means "collect everything configured".
            bam_json: parsed JSON payload to use instead of config.

        Returns:
            ClaimSet aggregated across all collected object types.
        """
        from .bluecat_parser import (
            parse_alias_records,
            parse_dhcp_ranges,
            parse_host_records,
            parse_ip_addresses,
        )

        rows: List[Dict[str, Any]] = []
        scopes = [scope] if scope else list(self.SCOPE)

        for s in scopes:
            payload = bam_json if bam_json is not None else self._config.get(f"_{s}_json")
            if payload is None:
                continue
            if s == "dns-records":
                with contextlib.suppress(Exception):
                    rows.extend(parse_host_records(payload))
                with contextlib.suppress(Exception):
                    rows.extend(parse_alias_records(payload))
            elif s == "dhcp-scopes":
                with contextlib.suppress(Exception):
                    rows.extend(parse_dhcp_ranges(payload))
            elif s == "ip-allocations":
                with contextlib.suppress(Exception):
                    rows.extend(parse_ip_addresses(payload))
        return self.normalize(rows)

    def push_dns_change(
        self,
        record_type: str,
        name: str,
        data: Dict[str, Any],
    ) -> DriftReport:
        """Report a proposed DNS change (read-only comparison for now).

        In a full implementation, this would also POST the change via
        BAM REST. Currently it only surfaces the delta as a warning-
        severity drift report for downstream review.
        """
        return DriftReport(
            drift_type="bluecat-dns-change",
            severity="warning",
            first_observed=self._now(),
            last_observed=self._now(),
            details={
                "adapter": self.ADAPTER_ID,
                "bam_host": self._bam_host,
                "configuration": self._configuration,
                "record_type": record_type,
                "name": name,
                "proposed": data,
            },
            remediation=(
                f"Review and commit DNS change for {record_type}/{name} via BAM."
            ),
        )

    def push_dhcp_change(
        self,
        scope_type: str,
        identifier: str,
        data: Dict[str, Any],
    ) -> DriftReport:
        """Report a proposed DHCP change (range / fixed-address).

        Args:
            scope_type: `dhcp-range` or `ip-address`.
            identifier: start-end pair for ranges, IPv4 for addresses.
            data:       proposed fields to set.
        """
        return DriftReport(
            drift_type="bluecat-dhcp-change",
            severity="warning",
            first_observed=self._now(),
            last_observed=self._now(),
            details={
                "adapter": self.ADAPTER_ID,
                "bam_host": self._bam_host,
                "configuration": self._configuration,
                "scope_type": scope_type,
                "identifier": identifier,
                "proposed": data,
            },
            remediation=(
                f"Review and commit DHCP change for {scope_type}/{identifier} via BAM."
            ),
        )

    def emit_event_stream(
        self,
        events: List[Dict[str, Any]],
        output_path: Optional[Path] = None,
    ) -> Path:
        """Write an NDJSON event stream (side-by-side-AD output).

        Each event is emitted as one JSON line so the stream is
        appendable and consumable by downstream directory-migration
        processors without a framing parser.

        Args:
            events:      list of event dicts (shape dictated by caller).
            output_path: destination file; defaults to `event-stream.ndjson`
                         in the current working directory.

        Returns:
            The resolved output path.
        """
        target = Path(output_path) if output_path else Path("event-stream.ndjson")
        with target.open("w", encoding="utf-8") as fh:
            for event in events:
                fh.write(json.dumps(event, sort_keys=True))
                fh.write("\n")
        return target

    def generate_ipam_evidence(
        self,
        scope: Optional[str] = None,
        bam_json: Optional[Dict[str, Any]] = None,
    ) -> EvidenceObject:
        """Generate a KSI evidence bundle covering SC-20 / SC-21 / CM-8.

        Bundles connection provenance, drift report, and normalized
        claims for the requested scope into a canonical EvidenceObject
        suitable for OSCAL artifact generation downstream.

        Args:
            scope:    one of SCOPE; None means all configured scopes.
            bam_json: pre-loaded payload to feed `get_all_objects`.
        """
        conn = self.connect()
        drift = self.detect_drift()
        claim_set = self.get_all_objects(scope=scope, bam_json=bam_json)

        return EvidenceObject(
            ksi_id=f"KSI-IPAM-BAM-{self._configuration}",
            source=self.ADAPTER_ID,
            timestamp=self._now(),
            raw_data={
                "connection": conn.to_dict(),
                "drift": drift.to_dict(),
                "scope": scope or "all",
                "record_count": len(claim_set.claims),
            },
            normalized_data=claim_set.to_dict(),
            provenance={
                "adapter_id": self.ADAPTER_ID,
                "bam_host": self._bam_host,
                "configuration": self._configuration,
                "hash": self._hash(claim_set.to_dict()),
                "timestamp": self._now().isoformat(),
            },
            freshness_valid=True,
        )

    # ------------------------------------------------------------------
    # Convenience: collect + normalize in one call
    # ------------------------------------------------------------------

    def collect_and_align(self) -> Dict[str, Any]:
        """Pull all configured scopes from BAM and return alignment result."""
        claim_set = self.get_all_objects()
        return {
            "vendor": "BlueCat",
            "adapter_id": self.ADAPTER_ID,
            "vendor_overlay_ref": "data/vendor-overlays/bluecat.yaml",
            "claims": claim_set.to_dict(),
            "metadata": {
                "total_records": len(claim_set.claims),
                "last_collected": self._now().isoformat(),
                "bam_host": self._bam_host,
                "configuration": self._configuration,
                "api_version": self._api_version,
                "scope": self.SCOPE,
            },
        }
