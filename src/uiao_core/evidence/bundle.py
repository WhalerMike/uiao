from __future__ import annotations

import json
from typing import Any, Dict, List

from uiao_core.ir.models.core import (
    Control,
    DriftState,
    Evidence,
    Policy,
    ProvenanceRecord,
    canonical_hash,
    canonical_json,
)


class EvidenceBundle:
    """
    Canonical, deterministic bundle of a full SCuBA assessment run.
    Contains all Evidence, DriftState, Controls, Policies, and summary.
    Produces a single canonical hash representing the entire assessment.
    """

    def __init__(
        self,
        run_id: str,
        provenance: ProvenanceRecord,
        evidence: List[Evidence],
        drift_states: List[DriftState],
        controls: List[Control],
        policies: List[Policy],
        unmapped_ksi_ids: List[str],
    ) -> None:
        self.run_id = run_id
        self.provenance = provenance
        self.evidence = sorted(evidence, key=lambda e: e.id)
        self.drift_states = sorted(drift_states, key=lambda d: d.id)
        self.controls = sorted(controls, key=lambda c: c.id)
        self.policies = sorted(policies, key=lambda p: p.id)
        self.unmapped_ksi_ids = sorted(unmapped_ksi_ids)

    @property
    def pass_count(self) -> int:
        return sum(1 for e in self.evidence if e.evaluation.get("passed"))

    @property
    def warn_count(self) -> int:
        return sum(1 for e in self.evidence if e.evaluation.get("warning"))

    @property
    def fail_count(self) -> int:
        return sum(1 for e in self.evidence if e.evaluation.get("failed"))

    @property
    def drift_count(self) -> int:
        return sum(1 for d in self.drift_states if d.drift_detected)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "provenance": self.provenance.model_dump(mode="json", exclude_none=True),
            "summary": {
                "total": len(self.evidence),
                "pass": self.pass_count,
                "warn": self.warn_count,
                "fail": self.fail_count,
                "drift_detected": self.drift_count,
                "unmapped_ksi_ids": self.unmapped_ksi_ids,
            },
            "evidence": [json.loads(e.to_canonical()) for e in self.evidence],
            "drift_states": [json.loads(d.to_canonical()) for d in self.drift_states],
            "controls": [json.loads(c.to_canonical()) for c in self.controls],
            "policies": [json.loads(p.to_canonical()) for p in self.policies],
        }

    def to_canonical(self) -> str:
        return canonical_json(self.to_dict())

    def hash(self) -> str:
        return canonical_hash(self.to_dict())

    def summary(self) -> str:
        lines = [
            f"EvidenceBundle [{self.run_id}]",
            f"  Total KSI results : {len(self.evidence)}",
            f"  PASS              : {self.pass_count}",
            f"  WARN              : {self.warn_count}",
            f"  FAIL              : {self.fail_count}",
            f"  Drift detected    : {self.drift_count}",
            f"  Unmapped KSIs     : {len(self.unmapped_ksi_ids)}"
            + (f" {self.unmapped_ksi_ids}" if self.unmapped_ksi_ids else ""),
            f"  Bundle hash       : {self.hash()[:16]}...",
        ]
        return "\n".join(lines)


def build_bundle_from_transform_result(transform_result: Any) -> EvidenceBundle:
    """
    Build an EvidenceBundle directly from a SCuBATransformResult.
    Drift states are empty at this stage (no baseline to compare against).
    """
    prov = ProvenanceRecord(
        source=f"bundle:{transform_result.run_id}",
        timestamp=transform_result.evidence[0].provenance.timestamp
        if transform_result.evidence
        else "1970-01-01T00:00:00Z",
        version="1.0",
        hash=None,
    )
    return EvidenceBundle(
        run_id=transform_result.run_id,
        provenance=prov,
        evidence=transform_result.evidence,
        drift_states=[],
        controls=transform_result.controls,
        policies=transform_result.policies,
        unmapped_ksi_ids=transform_result.unmapped_ksi_ids,
    )
