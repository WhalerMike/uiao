"""
UIAO Vulnerability Scanner Adapter — conformance class, read-only.

Observes vulnerability state across managed assets and produces
normalized, timestamped findings suitable for downstream evaluation
by the Policy Adapter class. Never mutates the target environment.

Classification (per uiao-core/canon/adapter-registry.yaml):
    class:            conformance
    mission-class:    telemetry  (UIAO_003 s4.3)
    status:           reserved   (-> active when impl ships)
    automation-domain: vulnerability-management (NIST SP 800-137 App. D)

This adapter is tool-agnostic: the vendor-specific scanner backend
(Tenable, Qualys, OpenSCAP, etc.) is injected via config. The adapter
normalizes heterogeneous scan output into the canonical UIAO claim
and evidence schema.

File: src/uiao_impl/adapters/vulnscan_adapter.py
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


class VulnScanAdapter(DatabaseAdapterBase):
    """
    Vulnerability Scanner adapter — conformance class (read-only).

    Implements the canonical UIAO adapter pattern (7 responsibility domains)
    plus vulnerability-management-specific extension methods for scan
    ingestion, finding normalization, and remediation tracking.

    This adapter NEVER mutates the target. It observes and reports.
    """

    ADAPTER_ID: str = "vuln-scan"

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        super().__init__(config or {})
        self._scanner: str = self._config.get("scanner", "generic")
        self._scanner_endpoint: str = self._config.get("endpoint", "")
        self._scan_policy: str = self._config.get("scan_policy", "default")

    # ------------------------------------------------------------------
    # 2.1 Connection & Identity
    # ------------------------------------------------------------------

    def connect(self) -> ConnectionProvenance:
        """Establish read-only connection to vulnerability scanner."""
        return ConnectionProvenance(
            identity=f"vuln-scan:{self._scanner}",
            auth_method=self._config.get("auth_method", "api-key"),
            endpoint=self._scanner_endpoint or f"https://{self._scanner}.local/api",
            tls_version=self._config.get("tls_version", "TLSv1.3"),
            mtls_enabled=self._config.get("mtls_enabled", False),
            timestamp=self._now(),
        )

    # ------------------------------------------------------------------
    # 2.2 Schema Discovery & Canonical Mapping
    # ------------------------------------------------------------------

    def discover_schema(self) -> SchemaMappingObject:
        """Map scanner-native finding schema to UIAO canonical schema."""
        vendor_schema: Dict[str, Any] = {
            "finding_id": "string",
            "cve_id": "string",
            "severity": "string",
            "cvss_score": "float",
            "affected_asset": "string",
            "plugin_id": "string",
            "first_seen": "datetime",
            "last_seen": "datetime",
            "state": "string",
        }
        canonical_schema: Dict[str, Any] = {
            "identity": f"vuln-scan:{self._scanner}:<finding_id>",
            "control_id": "RA-5",
            "implementation_statement": "<finding summary>",
            "evidence.source": "vuln-scan",
            "evidence.timestamp": "<scan_timestamp>",
            "evidence.record_hash": "sha256(<finding>)",
        }
        mapping_rules: Dict[str, Any] = {
            "finding_id": "identity suffix",
            "cve_id": "CVE cross-reference",
            "severity": "maps to evidence severity model (ADR-014)",
            "affected_asset": "target entity reference",
        }
        return SchemaMappingObject(
            vendor_schema=vendor_schema,
            canonical_schema=canonical_schema,
            mapping_rules=mapping_rules,
            unmapped_fields=["plugin_id", "plugin_family", "solution"],
            version_hash=self._hash(
                {"vendor": vendor_schema, "canonical": canonical_schema}
            ),
        )

    # ------------------------------------------------------------------
    # 2.3 Query Normalization & Deterministic Extraction
    # ------------------------------------------------------------------

    def execute_query(self, canonical_query: Dict[str, Any]) -> QueryProvenance:
        """Translate canonical query to scanner-native API request."""
        severity_filter = canonical_query.get("severity", "critical,high")
        asset_filter = canonical_query.get("from", "*")
        vendor_query = (
            f"GET /api/v1/findings?severity={severity_filter}"
            f"&asset={asset_filter}&policy={self._scan_policy}"
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
        """Convert raw scanner findings into canonical ClaimObjects."""
        claims: List[ClaimObject] = []
        for finding in raw_rows:
            finding_id = finding.get("finding_id", "unknown")
            cve_id = finding.get("cve_id", "")
            severity = finding.get("severity", "unknown")
            claim = ClaimObject(
                claim_id=f"vuln-scan:{self._scanner}:{finding_id}",
                entity=f"vuln-scan:finding:{finding_id}",
                fields={
                    "identity": f"vuln-scan:{self._scanner}:{finding_id}",
                    "cve_id": cve_id,
                    "severity": severity,
                    "cvss_score": finding.get("cvss_score", 0.0),
                    "affected_asset": finding.get("affected_asset", ""),
                    "state": finding.get("state", "open"),
                    "vendor_overlay_ref": f"{self._scanner}.yaml",
                },
                source=self.ADAPTER_ID,
                provenance_hash=self._hash(finding),
            )
            claims.append(claim)
        return ClaimSet(
            claims=claims,
            source_reference=self._scanner_endpoint or f"https://{self._scanner}.local",
        )

    # ------------------------------------------------------------------
    # 2.5 Drift Detection & Version Integrity
    # ------------------------------------------------------------------

    def detect_drift(self) -> DriftReport:
        """Detect drift in vulnerability posture vs canon baseline."""
        return DriftReport(
            drift_type="vuln-scan-posture",
            severity="info",
            first_observed=self._now(),
            last_observed=self._now(),
            details={
                "message": (
                    "Drift detection scaffold — compare current scan findings "
                    "against baseline accepted-risk register to detect new "
                    "vulnerabilities or regressions."
                ),
                "adapter": self.ADAPTER_ID,
                "scanner": self._scanner,
            },
            remediation=(
                "Run ingest_scan_results() then compare against baseline "
                "to identify delta findings for POA&M generation."
            ),
        )

    # ==================================================================
    # Vuln-Scan-Specific Extension Methods
    # ==================================================================

    def ingest_scan_results(
        self,
        scan_id: Optional[str] = None,
        severity_filter: Optional[str] = None,
    ) -> ClaimSet:
        """Ingest results from a completed vulnerability scan.

        Args:
            scan_id: Specific scan run ID, or None for latest
            severity_filter: Filter by severity (critical, high, medium, low)

        Returns:
            ClaimSet with one ClaimObject per finding.
        """
        raise NotImplementedError(
            "ingest_scan_results() is a stub — requires scanner-specific "
            "API collector (Tenable, Qualys, or OpenSCAP). Tool selection "
            "is tracked as ODA-14 in ARCHITECTURE.md §13."
        )

    def generate_vuln_evidence(
        self,
        scan_id: Optional[str] = None,
    ) -> EvidenceObject:
        """Generate KSI evidence bundle from scan results.

        Args:
            scan_id: Specific scan or None for latest

        Returns:
            EvidenceObject with RA-5 control provenance.
        """
        raise NotImplementedError(
            "generate_vuln_evidence() is a stub — requires "
            "ingest_scan_results() to be implemented first."
        )

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def collect_and_align(self) -> Dict[str, Any]:
        """Pull latest scan findings and return alignment result."""
        claim_set = self.normalize([])
        return {
            "vendor": self._scanner.title(),
            "adapter_id": self.ADAPTER_ID,
            "vendor_overlay_ref": f"data/vendor-overlays/{self._scanner}.yaml",
            "claims": claim_set.to_dict(),
            "metadata": {
                "total_records": len(claim_set.claims),
                "last_collected": self._now().isoformat(),
                "scanner": self._scanner,
                "scan_policy": self._scan_policy,
            },
        }
