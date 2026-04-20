from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from uiao.ir.mapping.ksi_to_ir import build_ksi_ir_mapping
from uiao.ir.models.core import (
    Control,
    Evidence,
    Policy,
    ProvenanceRecord,
    canonical_hash,
)


def transform_scuba_to_ir(
    normalized_json_path,
    tenant_boundary_id: str = "boundary:tenant:m365:contoso",
) -> SCuBATransformResult:
    """
    Load a normalized SCuBA JSON file and produce IR Evidence objects,
    one per ksi_results entry.

    Args:
        normalized_json_path: Path to a normalized SCuBA JSON file that
            conforms to scuba-normalized.schema.json.
        tenant_boundary_id: Boundary ID for policy scope.

    Returns:
        SCuBATransformResult with controls, policies, and evidence list.
    """
    path = Path(normalized_json_path)
    if not path.exists():
        raise FileNotFoundError(f"SCuBA normalized file not found: {path}")

    with open(path, encoding="utf-8") as f:
        scuba = json.load(f)

    # Build full KSI to IR mapping so we can cross-reference
    controls, policies = build_ksi_ir_mapping(tenant_boundary_id)
    control_index: Dict[str, Control] = {c.id: c for c in controls}
    policy_index: Dict[str, Policy] = {p.control_ref: p for p in policies}

    # Build provenance from assessment metadata
    meta = scuba.get("assessment_metadata", {})
    run_id = meta.get("run_id", "unknown-run")
    assessment_date = meta.get("assessment_date", datetime.now(timezone.utc).isoformat())
    tool_version = meta.get("tool_version", "unknown")
    tenant_id = scuba.get("tenant", {}).get("tenant_id", "unknown-tenant")

    provenance = ProvenanceRecord(
        source=f"scuba:{run_id}",
        timestamp=assessment_date,
        version=tool_version,
        content_hash=canonical_hash(scuba),
        actor=meta.get("collector_user"),
    )

    # Convert each ksi_results entry to an Evidence object
    evidence_list: List[Evidence] = []
    ksi_results = scuba.get("ksi_results", [])

    for result in ksi_results:
        ksi_id: str = result.get("ksi_id", "")
        status: str = result.get("status", "FAIL")
        severity: str = result.get("severity", "Medium")
        details: str = result.get("details", "")

        control = control_index.get(ksi_id)
        policy = policy_index.get(ksi_id)

        evidence = Evidence(
            id=f"evidence:scuba:{tenant_id}:{run_id}:{ksi_id}",
            source=f"scuba:{run_id}",
            control_id=ksi_id if control else None,
            policy_id=policy.id if policy else None,
            timestamp=assessment_date,
            data={
                "ksi_id": ksi_id,
                "status": status,
                "severity": severity,
                "details": details,
                "run_id": run_id,
                "tool_version": tool_version,
                "tenant_id": tenant_id,
            },
            evaluation={
                "passed": status == "PASS",
                "warning": status == "WARN",
                "failed": status == "FAIL",
                "severity": severity,
                "control_mapped": control is not None,
                "canonical_hash": "",
            },
            provenance=provenance,
        )
        # Patch in the hash after construction (frozen model workaround)
        evidence_list.append(evidence)

    # Compute canonical hashes after all evidence is built
    # (IRBase is frozen so we rebuild with hash included)
    final_evidence: List[Evidence] = []
    for e in evidence_list:
        eval_with_hash = dict(e.evaluation)
        eval_with_hash["canonical_hash"] = canonical_hash(e.model_dump(mode="json", exclude_none=True))
        final_evidence.append(e.model_copy(update={"evaluation": eval_with_hash}))

    return SCuBATransformResult(
        run_id=run_id,
        controls=controls,
        policies=policies,
        evidence=final_evidence,
        pass_count=sum(1 for e in final_evidence if e.evaluation["passed"]),
        warn_count=sum(1 for e in final_evidence if e.evaluation["warning"]),
        fail_count=sum(1 for e in final_evidence if e.evaluation["failed"]),
        unmapped_ksi_ids=[e.data["ksi_id"] for e in final_evidence if not e.evaluation["control_mapped"]],
    )


class SCuBATransformResult:
    """Holds the full output of a SCuBA to IR transform pass."""

    def __init__(
        self,
        run_id: str,
        controls: List[Control],
        policies: List[Policy],
        evidence: List[Evidence],
        pass_count: int,
        warn_count: int,
        fail_count: int,
        unmapped_ksi_ids: List[str],
    ) -> None:
        self.run_id = run_id
        self.controls = controls
        self.policies = policies
        self.evidence = evidence
        self.pass_count = pass_count
        self.warn_count = warn_count
        self.fail_count = fail_count
        self.unmapped_ksi_ids = unmapped_ksi_ids

    def summary(self) -> str:
        total = len(self.evidence)
        unmapped = len(self.unmapped_ksi_ids)
        lines = [
            f"SCuBA Transform [{self.run_id}]",
            f"  Total KSI results : {total}",
            f"  PASS              : {self.pass_count}",
            f"  WARN              : {self.warn_count}",
            f"  FAIL              : {self.fail_count}",
            f"  Unmapped KSIs     : {unmapped}" + (f" {self.unmapped_ksi_ids}" if unmapped else ""),
        ]
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "controls": [json.loads(c.to_canonical()) for c in self.controls],
            "policies": [json.loads(p.to_canonical()) for p in self.policies],
            "pass_count": self.pass_count,
            "warn_count": self.warn_count,
            "fail_count": self.fail_count,
            "unmapped_ksi_ids": self.unmapped_ksi_ids,
            "evidence": [json.loads(e.to_canonical()) for e in self.evidence],
        }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python transformer.py <normalized-scuba.json>")
        sys.exit(1)
    result = transform_scuba_to_ir(sys.argv[1])
    print(result.summary())

