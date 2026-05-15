"""
UIAO-Core ServiceNow Adapter — DNS-style alignment only.

This adapter is intentionally lightweight and sits OUTSIDE the main data path.
Its only job: create alignments (vendor-overlay + claim + evidence hash).
It does NOT perform OSCAL JSON, SSP, POA&M, or SBOM conversions.
Those happen downstream in src/uiao/impl/generators/.

Analogy: like a DNS resolver — it tells the engine HOW to get there;
the generators/ layer does the actual conversion work.

File: src/uiao/impl/adapters/servicenow_adapter.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests  # type: ignore[import-untyped]

from ..collectors.servicenow_collector import ServiceNowCollector
from .database_base import (
    ClaimObject,
    ClaimSet,
    ConnectionProvenance,
    DatabaseAdapterBase,
    DriftReport,
    QueryProvenance,
    SchemaMappingObject,
)


class ServiceNowAdapter(DatabaseAdapterBase):
    """
    ServiceNow adapter — DNS-style alignment only (no heavy conversion).

    Implements the canonical UIAO adapter pattern:
    1. Collector reaches out to ServiceNow via Table API.
    2. Adapter normalizes raw records into identity-rooted UIAO claims.
    3. Adapter builds a vendor-specific overlay reference + evidence hash.
    4. Engine merges the alignment into the canon for downstream generation.

    This adapter never owns or duplicates data. SSOT remains in the YAML canon.
    """

    ADAPTER_ID: str = "servicenow"

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        super().__init__(config or {})
        self.collector = ServiceNowCollector(
            instance=self._config.get("instance", ""),
            token=self._config.get("token", ""),
        )

    # ------------------------------------------------------------------
    # 2.1 Connection & Identity — delegate to collector
    # ------------------------------------------------------------------

    def connect(self) -> ConnectionProvenance:
        """Establish ServiceNow connection and return provenance."""
        from .database_base import ConnectionProvenance

        return ConnectionProvenance(
            identity=f"servicenow:{self.collector.instance}",
            auth_method="oauth-bearer",
            endpoint=f"https://{self.collector.instance}.service-now.com",
            tls_version="TLSv1.3",
            mtls_enabled=False,  # Set True when mTLS certs are configured
            timestamp=self._now(),
        )

    # ------------------------------------------------------------------
    # 2.2 Schema Discovery — map ServiceNow fields to UIAO schema
    # ------------------------------------------------------------------

    def discover_schema(self) -> SchemaMappingObject:
        """Return canonical mapping of ServiceNow fields → UIAO schema."""
        from .database_base import SchemaMappingObject

        vendor_schema = {
            "sys_id": "string",
            "short_description": "string",
            "state": "integer",
            "assigned_to": "reference",
            "opened_at": "datetime",
            "uiao_control_id": "string",  # custom field recommended
        }
        canonical_schema = {
            "identity": "servicenow:ticket:<sys_id>",
            "control_id": "<uiao_control_id or default AC-2>",
            "implementation_statement": "<short_description>",
            "evidence.source": "servicenow",
            "evidence.timestamp": "<collected_at>",
            "evidence.record_hash": "sha256(<record>)",
        }
        mapping_rules = {
            "sys_id": "identity suffix",
            "short_description": "implementation_statement",
            "uiao_control_id": "control_id (fallback: AC-2)",
        }
        version_hash = self._hash({"vendor": vendor_schema, "canonical": canonical_schema})
        return SchemaMappingObject(
            vendor_schema=vendor_schema,
            canonical_schema=canonical_schema,
            mapping_rules=mapping_rules,
            unmapped_fields=["state", "assigned_to", "opened_at"],
            version_hash=version_hash,
        )

    # ------------------------------------------------------------------
    # 2.3 Query Normalization — translate canonical query to ServiceNow
    # ------------------------------------------------------------------

    def execute_query(self, canonical_query: Dict[str, Any]) -> QueryProvenance:
        """Translate canonical query to ServiceNow Table API parameters."""
        from .database_base import QueryProvenance

        table = canonical_query.get("from", "incident")
        fields = canonical_query.get("select", ["sys_id", "short_description", "uiao_control_id"])
        vendor_query = f"GET /api/now/table/{table}?sysparm_fields={','.join(fields)}"
        return QueryProvenance(
            canonical_query=canonical_query,
            vendor_query=vendor_query,
            execution_plan_hash=self._hash(vendor_query),
            row_count=0,  # populated after real fetch
            timestamp=self._now(),
        )

    # ------------------------------------------------------------------
    # 2.4 Data Normalization — build UIAO-aligned claims (alignment only)
    # ------------------------------------------------------------------

    def normalize(self, raw_rows: List[Dict[str, Any]]) -> ClaimSet:
        """
        Convert raw ServiceNow records into canonical UIAO ClaimObjects.

        ALIGNMENT ONLY — no OSCAL conversion happens here.
        The claim is a pointer + evidence hash; generators/ does the rest.
        """
        claims: List[ClaimObject] = []
        for record in raw_rows:
            sys_id = record.get("sys_id", "unknown")
            claim_payload = {
                "identity": f"servicenow:ticket:{sys_id}",
                "control_id": record.get("uiao_control_id", "AC-2"),
                "implementation_statement": record.get("short_description", ""),
                "vendor_overlay_ref": "servicenow.yaml",
                "telemetry_enabled": True,
                "raw_link": (f"https://{self.collector.instance}.service-now.com/incident.do?sys_id={sys_id}"),
            }
            claim = ClaimObject(
                claim_id=f"servicenow:{sys_id}",
                entity=f"servicenow:ticket:{sys_id}",
                fields=claim_payload,
                source=self.ADAPTER_ID,
                provenance_hash=self._hash(record),
            )
            claims.append(claim)

        return ClaimSet(
            claims=claims,
            source_reference=(f"https://{self.collector.instance}.service-now.com/api/now/table/incident"),
        )

    # ------------------------------------------------------------------
    # 2.5 Drift Detection — compare current vs expected state
    # ------------------------------------------------------------------

    def detect_drift(self) -> DriftReport:
        """
        Detect drift between ServiceNow state and UIAO canon.

        Algorithm:
        1. Load the documented scope set for the 'service-now' adapter from
           modernization-registry.yaml (expected state).
        2. Fetch current records via the collector (empty-scaffold fallback
           when no token is configured — safe for CI).
        3. Delegate the comparison to collector.compare_for_drift().
        4. Return a DriftReport with severity 'high' when drifted records
           exist, 'info' otherwise.
        """
        # Step 1 — expected state from canon
        registry_path = Path(__file__).parent.parent / "canon" / "modernization-registry.yaml"
        expected_records: List[Dict[str, Any]] = []
        try:
            import yaml  # type: ignore[import-untyped]

            registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
            adapters = registry.get("adapters", [])
            for entry in adapters:
                if entry.get("id") == "service-now":
                    for scope_item in entry.get("scope", []):
                        expected_records.append(
                            {
                                "sys_id": scope_item,
                                "short_description": scope_item,
                            }
                        )
                    break
        except Exception:
            # Registry unavailable — proceed with empty expected set
            expected_records = []

        # Step 2 — current state from collector (empty scaffold when no token)
        raw = self.collector.fetch_relevant_records()
        current_records: List[Dict[str, Any]] = raw.get("result", [])

        # Step 3 — compute drift
        drifted = self.collector.compare_for_drift(current_records, expected_records)

        # Step 4 — classify
        new_sys_ids = [r.get("sys_id", "") for r in drifted if r.get("_drift") == "new_record"]
        changed_sys_ids = [r.get("sys_id", "") for r in drifted if r.get("_drift") == "changed"]
        severity = "high" if drifted else "info"

        remediation = (
            "Review drifted records returned by ServiceNowCollector.compare_for_drift() "
            "and reconcile them against the scope entries in modernization-registry.yaml. "
            "New records may indicate undocumented change activity; changed records may "
            "reflect manual edits that bypass the UIAO change-management workflow."
            if drifted
            else "No drift detected — ServiceNow records align with canon scope."
        )

        now = self._now()
        return DriftReport(
            drift_type="servicenow-record-divergence",
            severity=severity,
            first_observed=now,
            last_observed=now,
            details={
                "drifted_count": len(drifted),
                "new_records": new_sys_ids,
                "changed_records": changed_sys_ids,
                "adapter": self.ADAPTER_ID,
            },
            remediation=remediation,
        )

    # ------------------------------------------------------------------
    # Convenience: collect + normalize in one call
    # ------------------------------------------------------------------

    def collect_and_align(self) -> Dict[str, Any]:
        """
        Pull records from ServiceNow and return alignment result.

        Returns the ClaimSet as a dict for downstream engine consumption.
        Does NOT generate OSCAL — that stays in generators/.
        """
        raw_data = self.collector.fetch_relevant_records()
        records = raw_data.get("result", [])
        claim_set = self.normalize(records)
        return {
            "vendor": "ServiceNow",
            "adapter_id": self.ADAPTER_ID,
            "vendor_overlay_ref": "data/vendor-overlays/servicenow.yaml",
            "claims": claim_set.to_dict(),
            "metadata": {
                "total_records": len(claim_set.claims),
                "last_collected": self._now().isoformat(),
                "instance": self.collector.instance,
            },
        }

    # ------------------------------------------------------------------
    # Write-side methods — create / update records in ServiceNow
    # ------------------------------------------------------------------

    def create_incident(
        self,
        short_description: str,
        uiao_control_id: str = "AC-2",
        **fields: Any,
    ) -> Dict[str, Any]:
        """
        Create a new incident record in ServiceNow.

        Args:
            short_description: Human-readable summary of the incident.
            uiao_control_id: UIAO canonical control ID (default 'AC-2').
            **fields: Additional ServiceNow field values merged into the payload.

        Returns:
            ClaimObject-shaped evidence dict with keys:
            ``ok``, ``sys_id``, ``error``, ``evidence``.
        """
        payload: Dict[str, Any] = {
            "short_description": short_description,
            "u_uiao_control_id": uiao_control_id,
            **fields,
        }
        try:
            response = self.collector.post_record("incident", payload)
            result = response.get("result", {})
            sys_id: str = result.get("sys_id", "")
            evidence = self._build_evidence(
                operation="create_incident",
                table="incident",
                sys_id=sys_id,
                payload=payload,
                response=result,
            )
            return {"ok": True, "sys_id": sys_id, "error": None, "evidence": evidence}
        except requests.HTTPError as exc:
            return {"ok": False, "sys_id": "", "error": str(exc), "evidence": {}}

    def update_incident(
        self,
        sys_id: str,
        **fields: Any,
    ) -> Dict[str, Any]:
        """
        Update an existing incident record in ServiceNow via PATCH.

        Args:
            sys_id: ServiceNow sys_id of the incident to update.
            **fields: Field values to apply to the existing record.

        Returns:
            ClaimObject-shaped evidence dict with keys:
            ``ok``, ``sys_id``, ``error``, ``evidence``.
        """
        payload: Dict[str, Any] = {**fields}
        try:
            response = self.collector.patch_record("incident", sys_id, payload)
            result = response.get("result", {})
            evidence = self._build_evidence(
                operation="update_incident",
                table="incident",
                sys_id=sys_id,
                payload=payload,
                response=result,
            )
            return {"ok": True, "sys_id": sys_id, "error": None, "evidence": evidence}
        except requests.HTTPError as exc:
            return {"ok": False, "sys_id": sys_id, "error": str(exc), "evidence": {}}

    def create_change_request(
        self,
        short_description: str,
        uiao_control_id: str,
        **fields: Any,
    ) -> Dict[str, Any]:
        """
        Create a new change request record in ServiceNow.

        Args:
            short_description: Human-readable summary of the change request.
            uiao_control_id: UIAO canonical control ID (e.g. 'CM-3').
            **fields: Additional ServiceNow field values merged into the payload.

        Returns:
            ClaimObject-shaped evidence dict with keys:
            ``ok``, ``sys_id``, ``error``, ``evidence``.
        """
        payload: Dict[str, Any] = {
            "short_description": short_description,
            "u_uiao_control_id": uiao_control_id,
            **fields,
        }
        try:
            response = self.collector.post_record("change_request", payload)
            result = response.get("result", {})
            sys_id: str = result.get("sys_id", "")
            evidence = self._build_evidence(
                operation="create_change_request",
                table="change_request",
                sys_id=sys_id,
                payload=payload,
                response=result,
            )
            return {"ok": True, "sys_id": sys_id, "error": None, "evidence": evidence}
        except requests.HTTPError as exc:
            return {"ok": False, "sys_id": "", "error": str(exc), "evidence": {}}

    def create_problem(
        self,
        short_description: str,
        uiao_control_id: str,
        **fields: Any,
    ) -> Dict[str, Any]:
        """
        Create a new problem record in ServiceNow.

        Args:
            short_description: Human-readable summary of the problem.
            uiao_control_id: UIAO canonical control ID (e.g. 'IR-4').
            **fields: Additional ServiceNow field values merged into the payload.

        Returns:
            ClaimObject-shaped evidence dict with keys:
            ``ok``, ``sys_id``, ``error``, ``evidence``.
        """
        payload: Dict[str, Any] = {
            "short_description": short_description,
            "u_uiao_control_id": uiao_control_id,
            **fields,
        }
        try:
            response = self.collector.post_record("problem", payload)
            result = response.get("result", {})
            sys_id: str = result.get("sys_id", "")
            evidence = self._build_evidence(
                operation="create_problem",
                table="problem",
                sys_id=sys_id,
                payload=payload,
                response=result,
            )
            return {"ok": True, "sys_id": sys_id, "error": None, "evidence": evidence}
        except requests.HTTPError as exc:
            return {"ok": False, "sys_id": "", "error": str(exc), "evidence": {}}

    # ------------------------------------------------------------------
    # Ticket-manifest emitter (declared output in modernization-registry)
    # ------------------------------------------------------------------

    def _emit_ticket_manifest(
        self,
        claims: List[Dict[str, Any]],
        out_dir: Path,
    ) -> Path:
        """
        Write ``ticket-manifest.json`` to *out_dir*.

        The filename matches the ``outputs`` entry declared in
        ``modernization-registry.yaml`` for the ``service-now`` adapter.
        If the file already exists a timestamp suffix is appended to avoid
        silent overwrites (append-only contract).

        Args:
            claims: List of ClaimObject-shaped dicts to persist.
            out_dir: Directory where the manifest file will be written.

        Returns:
            Path to the written manifest file.
        """
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / "ticket-manifest.json"
        if target.exists():
            ts = self._now().strftime("%Y%m%dT%H%M%SZ")
            target = out_dir / f"ticket-manifest-{ts}.json"

        manifest: Dict[str, Any] = {
            "adapter_id": self.ADAPTER_ID,
            "generated_at": self._now().isoformat(),
            "instance": self.collector.instance,
            "claims": claims,
        }
        target.write_text(json.dumps(manifest, indent=2, default=str))
        return target

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_evidence(
        self,
        operation: str,
        table: str,
        sys_id: str,
        payload: Dict[str, Any],
        response: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build a ClaimObject-shaped evidence dict for a write operation."""
        claim_payload: Dict[str, Any] = {
            "identity": f"servicenow:ticket:{sys_id}",
            "operation": operation,
            "table": table,
            "vendor_overlay_ref": "servicenow.yaml",
            "telemetry_enabled": True,
            "raw_link": (f"https://{self.collector.instance}.service-now.com/{table}.do?sys_id={sys_id}"),
        }
        return {
            "claim_id": f"servicenow:{operation}:{sys_id}",
            "entity": f"servicenow:ticket:{sys_id}",
            "fields": claim_payload,
            "source": self.ADAPTER_ID,
            "provenance_hash": self._hash(
                {
                    "operation": operation,
                    "table": table,
                    "sys_id": sys_id,
                    "payload": payload,
                    "response": response,
                    "timestamp": self._now().isoformat(),
                }
            ),
        }

    # Expose Optional so mypy is satisfied on callers that annotate with it
    _OptionalStr = Optional[str]
