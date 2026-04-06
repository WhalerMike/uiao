"""UIAO-Core SCuBA (Secure Cloud Business Applications) Adapter

Reads CISA SCuBA assessment output (JSON or YAML) and maps findings
to UIAO KSI evidence, producing OSCAL-aligned claims.

SCuBA assessments are produced by the ScubaGear tool:
  https://github.com/cisagov/ScubaGear

Each SCuBA report contains policy baseline results per product
(AAD, Defender, EXO, TEAMS, etc.). This adapter ingests those
results and creates KSI evidence records in the UIAO canon format.

File: src/uiao_core/adapters/scuba_adapter.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .database_base import (
    ClaimObject,
    ClaimSet,
    ConnectionProvenance,
    DatabaseAdapterBase,
    DriftReport,
    QueryProvenance,
    SchemaMappingObject,
)

# ---------------------------------------------------------------------------
# SCuBA policy ID -> UIAO KSI/OSCAL control mapping
# ---------------------------------------------------------------------------
SCUBA_TO_KSI_MAP: Dict[str, str] = {
    # AAD (Azure Active Directory / Entra ID)
    "MS.AAD.1.1v1": "AC-2",
    "MS.AAD.2.1v1": "IA-2",
    "MS.AAD.2.3v1": "IA-2(1)",
    "MS.AAD.3.1v1": "AC-3",
    "MS.AAD.3.2v1": "AC-6",
    "MS.AAD.5.1v1": "IA-5",
    "MS.AAD.7.1v1": "IA-8",
    "MS.AAD.7.2v1": "IA-8(1)",
    # Defender
    "MS.DEFENDER.1.1v1": "SI-3",
    "MS.DEFENDER.1.2v1": "SI-3(1)",
    "MS.DEFENDER.2.1v1": "AU-2",
    "MS.DEFENDER.4.1v1": "IR-4",
    # Exchange Online
    "MS.EXO.1.1v1": "SC-8",
    "MS.EXO.2.1v1": "SC-8(1)",
    "MS.EXO.4.1v1": "SI-8",
    # SharePoint / OneDrive
    "MS.SHAREPOINT.1.1v1": "AC-22",
    "MS.SHAREPOINT.2.1v1": "AC-3",
    # Teams
    "MS.TEAMS.1.1v1": "AC-20",
    "MS.TEAMS.1.2v1": "AC-20(1)",
}

# SCuBA result strings -> pass/fail boolean
RESULT_PASS = {"Pass", "pass", "PASS", "true", "True"}
RESULT_FAIL = {"Fail", "fail", "FAIL", "false", "False", "Warning", "warning"}


class ScubaAdapter(DatabaseAdapterBase):
    """CISA SCuBA assessment adapter.

    Ingests ScubaGear output reports and converts policy baseline
    results into UIAO KSI evidence records (alignment only -- no
    OSCAL generation; that stays in generators/).

    Supported input formats:
    - ScubaGear JSON report (TestResults array)
    - ScubaGear YAML summary

    Usage::

        adapter = ScubaAdapter(config={"report_path": "path/to/report.json"})
        adapter.connect()
        claims = adapter.collect_and_align()
    """

    ADAPTER_ID: str = "scuba"

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        super().__init__(config or {})
        self._report_path: Optional[Path] = Path(self._config["report_path"]) if "report_path" in self._config else None
        self._raw_report: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------
    # 2.1 Connection -- load report file
    # ------------------------------------------------------------------

    def connect(self) -> ConnectionProvenance:
        """Load the SCuBA report file and return provenance."""
        if self._report_path and self._report_path.exists():
            suffix = self._report_path.suffix.lower()
            with open(self._report_path, encoding="utf-8") as f:
                self._raw_report = json.load(f) if suffix == ".json" else yaml.safe_load(f)
            source = str(self._report_path)
        else:
            self._raw_report = {}
            source = "no-report-loaded"

        return ConnectionProvenance(
            identity=f"scuba:{source}",
            auth_method="file",
            endpoint=source,
            tls_version="N/A",
            mtls_enabled=False,
            timestamp=self._now(),
        )

    # ------------------------------------------------------------------
    # 2.2 Schema Discovery -- map SCuBA fields to UIAO schema
    # ------------------------------------------------------------------

    def discover_schema(self) -> SchemaMappingObject:
        """Return canonical mapping of SCuBA report fields -> UIAO schema."""
        vendor_schema = {
            "PolicyId": "string",
            "Criticality": "string",
            "Commandlet": "list[string]",
            "ActualValue": "object",
            "RequirementMet": "boolean",
            "NoSuchEvent": "boolean",
        }
        canonical_schema = {
            "identity": "scuba:<product>:<policy_id>",
            "control_id": "<mapped via SCUBA_TO_KSI_MAP>",
            "implementation_statement": "<policy description>",
            "evidence.source": "scuba",
            "evidence.timestamp": "<report_date>",
            "evidence.record_hash": "sha256(<policy_result>)",
        }
        mapping_rules = {
            "PolicyId": "identity suffix + KSI lookup",
            "RequirementMet": "pass_criteria boolean",
            "ActualValue": "evidence payload",
            "Criticality": "risk weight",
        }
        version_hash = self._hash({"vendor": vendor_schema})
        return SchemaMappingObject(
            vendor_schema=vendor_schema,
            canonical_schema=canonical_schema,
            mapping_rules=mapping_rules,
            unmapped_fields=["Commandlet", "NoSuchEvent"],
            version_hash=version_hash,
        )

    # ------------------------------------------------------------------
    # 2.3 Query Normalization -- filter SCuBA results
    # ------------------------------------------------------------------

    def execute_query(self, canonical_query: Dict[str, Any]) -> QueryProvenance:
        """Filter SCuBA results by product, policy, or pass/fail status."""
        filters = {
            "product": canonical_query.get("product"),
            "control_id": canonical_query.get("control_id"),
            "passing_only": canonical_query.get("passing_only", False),
        }
        vendor_query = f"SCuBA filter: {json.dumps(filters)}"
        return QueryProvenance(
            canonical_query=canonical_query,
            vendor_query=vendor_query,
            execution_plan_hash=self._hash(vendor_query),
            row_count=len(self._extract_results()),
            timestamp=self._now(),
        )

    # ------------------------------------------------------------------
    # 2.4 Data Normalization -- build UIAO claims from SCuBA results
    # ------------------------------------------------------------------

    def normalize(self, raw_rows: List[Dict[str, Any]]) -> ClaimSet:
        """Convert SCuBA policy results into canonical UIAO ClaimObjects."""
        claims: List[ClaimObject] = []

        for result in raw_rows:
            policy_id = result.get("PolicyId", "unknown")
            control_id = SCUBA_TO_KSI_MAP.get(policy_id, "N/A")
            requirement_met = result.get("RequirementMet", False)
            criticality = result.get("Criticality", "Shall")
            description = result.get("Description", result.get("Requirement", ""))

            # Determine pass/fail
            if isinstance(requirement_met, bool):
                passed = requirement_met
            elif isinstance(requirement_met, str):
                passed = requirement_met in RESULT_PASS
            else:
                passed = False

            claim_payload = {
                "identity": f"scuba:{policy_id}",
                "control_id": control_id,
                "implementation_statement": description or f"SCuBA policy {policy_id}",
                "vendor_overlay_ref": "scuba.yaml",
                "scuba_policy_id": policy_id,
                "scuba_criticality": criticality,
                "scuba_result": "pass" if passed else "fail",
                "actual_value": result.get("ActualValue", {}),
                "telemetry_enabled": True,
            }

            claim = ClaimObject(
                claim_id=f"scuba:{policy_id}",
                entity=f"scuba:policy:{policy_id}",
                fields=claim_payload,
                source=self.ADAPTER_ID,
                provenance_hash=self._hash(result),
            )
            claims.append(claim)

        return ClaimSet(
            claims=claims,
            source_reference=str(self._report_path or "scuba-report"),
        )

    # ------------------------------------------------------------------
    # 2.5 Drift Detection
    # ------------------------------------------------------------------

    def detect_drift(self) -> DriftReport:
        """Detect SCuBA policy regressions against previous baseline."""
        results = self._extract_results()
        failing = [r for r in results if not r.get("RequirementMet", False)]
        return DriftReport(
            drift_type="scuba-policy-regression",
            severity="high" if failing else "none",
            first_observed=self._now(),
            last_observed=self._now(),
            details={
                "total_policies": len(results),
                "failing_policies": len(failing),
                "failing_ids": [r.get("PolicyId") for r in failing[:10]],
            },
            remediation=(
                "Review failing SCuBA policies and update Entra/Defender configurations."
                if failing
                else "All SCuBA policies passing."
            ),
        )

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def collect_and_align(self) -> Dict[str, Any]:
        """Load report, normalize all results, return alignment dict."""
        self.connect()
        results = self._extract_results()
        claim_set = self.normalize(results)
        passing = sum(1 for c in claim_set.claims if c.fields.get("scuba_result") == "pass")
        return {
            "vendor": "CISA SCuBA / ScubaGear",
            "adapter_id": self.ADAPTER_ID,
            "vendor_overlay_ref": "data/vendor-overlays/scuba.yaml",
            "claims": claim_set.to_dict(),
            "metadata": {
                "total_policies": len(claim_set.claims),
                "passing": passing,
                "failing": len(claim_set.claims) - passing,
                "last_collected": self._now().isoformat(),
                "report_path": str(self._report_path or ""),
            },
        }

    def _extract_results(self) -> List[Dict[str, Any]]:
        """Extract the list of policy results from the raw report."""
        if not self._raw_report:
            return []
        # ScubaGear JSON: {"TestResults": [...]}
        if "TestResults" in self._raw_report:
            return self._raw_report["TestResults"]
        # ScubaGear YAML summary: {"Results": [...]}
        if "Results" in self._raw_report:
            return self._raw_report["Results"]
        # Direct list
        if isinstance(self._raw_report, list):
            return self._raw_report
        return []

    def get_ksi_evidence(self, ksi_id: str) -> List[Dict[str, Any]]:
        """Return all SCuBA policy results that map to a given KSI/control ID."""
        results = self._extract_results()
        return [r for r in results if SCUBA_TO_KSI_MAP.get(r.get("PolicyId", ""), "") == ksi_id]
