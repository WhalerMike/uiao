"""
UIAO STIG Compliance Adapter — conformance class, read-only.

Evaluates system configuration against DISA STIG baselines and produces
normalized compliance findings. Policy-class adapter: ingests
configuration state and evaluates it against declared security technical
implementation guides.

Classification (per uiao-core/canon/adapter-registry.yaml):
    class:            conformance
    mission-class:    policy  (UIAO_003 s4.4)
    status:           reserved
    automation-domain: configuration-management (NIST SP 800-137 App. D)

File: src/uiao_impl/adapters/stigcompliance_adapter.py
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .database_base import (
    ClaimObject, ClaimSet, ConnectionProvenance, DatabaseAdapterBase,
    DriftReport, EvidenceObject, QueryProvenance, SchemaMappingObject,
)


class StigComplianceAdapter(DatabaseAdapterBase):
    """STIG Compliance adapter — conformance class (read-only, policy)."""

    ADAPTER_ID: str = "stig-compliance"

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        super().__init__(config or {})
        self._benchmark: str = self._config.get("benchmark", "")
        self._target: str = self._config.get("target", "")
        self._engine: str = self._config.get("engine", "openscap")

    def connect(self) -> ConnectionProvenance:
        return ConnectionProvenance(
            identity=f"stig-compliance:{self._engine}:{self._target}",
            auth_method=self._config.get("auth_method", "local"),
            endpoint=self._target or "localhost",
            tls_version=self._config.get("tls_version"),
            mtls_enabled=False,
            timestamp=self._now(),
        )

    def discover_schema(self) -> SchemaMappingObject:
        vendor_schema: Dict[str, Any] = {
            "rule_id": "string", "severity": "string", "title": "string",
            "result": "string", "fix_text": "string",
        }
        canonical_schema: Dict[str, Any] = {
            "identity": f"stig-compliance:{self._engine}:<rule_id>",
            "control_id": "CM-6", "evidence.source": "stig-compliance",
        }
        return SchemaMappingObject(
            vendor_schema=vendor_schema, canonical_schema=canonical_schema,
            mapping_rules={"rule_id": "identity suffix", "result": "pass/fail/error"},
            unmapped_fields=["fix_text", "check_content"],
            version_hash=self._hash({"vendor": vendor_schema, "canonical": canonical_schema}),
        )

    def execute_query(self, canonical_query: Dict[str, Any]) -> QueryProvenance:
        benchmark = canonical_query.get("from", self._benchmark or "RHEL9-STIG")
        vendor_query = f"oscap xccdf eval --benchmark {benchmark} --target {self._target}"
        return QueryProvenance(
            canonical_query=canonical_query, vendor_query=vendor_query,
            execution_plan_hash=self._hash(vendor_query), row_count=0,
            timestamp=self._now(),
        )

    def normalize(self, raw_rows: List[Dict[str, Any]]) -> ClaimSet:
        claims: List[ClaimObject] = []
        for rule in raw_rows:
            rule_id = rule.get("rule_id", "unknown")
            claims.append(ClaimObject(
                claim_id=f"stig-compliance:{self._engine}:{rule_id}",
                entity=f"stig-compliance:{rule_id}",
                fields={"identity": f"stig-compliance:{self._engine}:{rule_id}",
                        "result": rule.get("result", ""), "severity": rule.get("severity", ""),
                        "title": rule.get("title", ""), "vendor_overlay_ref": "stig.yaml"},
                source=self.ADAPTER_ID, provenance_hash=self._hash(rule),
            ))
        return ClaimSet(claims=claims, source_reference=f"stig:{self._benchmark}")

    def detect_drift(self) -> DriftReport:
        return DriftReport(
            drift_type="stig-compliance-posture", severity="info",
            first_observed=self._now(), last_observed=self._now(),
            details={"message": "Drift detection scaffold — compare STIG results against accepted baseline.",
                     "adapter": self.ADAPTER_ID, "engine": self._engine, "benchmark": self._benchmark},
            remediation="Evaluate XCCDF results against prior accepted-risk register.",
        )

    def run_stig_assessment(self, results_data: Optional[Dict[str, Any]] = None) -> ClaimSet:
        """Parse STIG assessment results and return claims.

        Args:
            results_data: Parsed JSON with a "results" list of XCCDF rule outcomes.
        """
        results = (results_data or {}).get("results", [])
        return self.normalize(results)

    def generate_stig_evidence(self, results_data: Optional[Dict[str, Any]] = None) -> EvidenceObject:
        """Generate evidence bundle from STIG assessment results."""
        conn = self.connect()
        results = (results_data or {}).get("results", [])
        claim_set = self.normalize(results)
        pass_count = sum(1 for r in results if r.get("result") == "pass")
        fail_count = sum(1 for r in results if r.get("result") == "fail")

        return EvidenceObject(
            ksi_id=f"KSI-CM-06-{self._engine}",
            source=self.ADAPTER_ID,
            timestamp=self._now(),
            raw_data={"connection": conn.to_dict(), "pass": pass_count, "fail": fail_count, "total": len(results)},
            normalized_data=claim_set.to_dict(),
            provenance={"adapter_id": self.ADAPTER_ID, "engine": self._engine, "hash": self._hash(claim_set.to_dict()), "timestamp": self._now().isoformat()},
            freshness_valid=True,
        )

    def collect_and_align(self) -> Dict[str, Any]:
        claim_set = self.normalize([])
        return {"vendor": self._engine.title(), "adapter_id": self.ADAPTER_ID,
                "claims": claim_set.to_dict(),
                "metadata": {"engine": self._engine, "benchmark": self._benchmark,
                             "target": self._target, "last_collected": self._now().isoformat()}}
