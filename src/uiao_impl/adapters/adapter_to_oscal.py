"""
adapter_to_oscal.py — Bridge from adapter outputs to OSCAL artifacts.

Converts adapter ClaimSets, DriftReports, and EvidenceObjects into the
IR model format consumed by generators/sar.py, generators/ssp.py, etc.

This is the "last mile" that connects the adapter layer to the OSCAL
output layer, completing the full pipeline:

  vendor data → adapter → claims → IR → OSCAL (SSP/SAR/POA&M)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..adapters.database_base import ClaimSet, DriftReport, EvidenceObject
from ..evidence.bundle import EvidenceBundle
from ..ir.models.core import (
    Control,
    DriftState,
    Evidence,
    Policy,
    ProvenanceRecord,
    canonical_hash,
)


def claims_to_ir_evidence(
    claim_set: ClaimSet,
    adapter_id: str,
    control_id: str = "CM-8",
    timestamp: Optional[str] = None,
) -> List[Evidence]:
    """Convert adapter ClaimSet into IR Evidence objects.

    Each ClaimObject becomes one IR Evidence entry with:
    - source = adapter_id
    - control_id from the adapter's canon registry controls
    - data = claim fields
    - evaluation = {passed: True} (claim exists = evidence of state)
    """
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    results: List[Evidence] = []

    for claim in claim_set.claims:
        prov = ProvenanceRecord(
            source=adapter_id,
            timestamp=ts,
            version="1.0",
            content_hash=claim.provenance_hash,
        )
        ev = Evidence(
            id=f"ev-{adapter_id}-{claim.claim_id}",
            source=adapter_id,
            control_id=control_id,
            timestamp=ts,
            data={
                "claim_id": claim.claim_id,
                "entity": claim.entity,
                **claim.fields,
            },
            evaluation={
                "passed": True,
                "control_mapped": True,
                "method": "automated-adapter",
            },
            provenance=prov,
        )
        results.append(ev)

    return results


def drift_to_ir_states(
    drift: DriftReport,
    adapter_id: str,
    timestamp: Optional[str] = None,
) -> List[DriftState]:
    """Convert adapter DriftReport into IR DriftState objects.

    Each resource in the drift details becomes a DriftState entry.
    """
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    prov = ProvenanceRecord(
        source=adapter_id,
        timestamp=ts,
        version="1.0",
    )

    states: List[DriftState] = []
    resources = drift.details.get("resources", {})

    for addr, info in resources.items():
        actions = info.get("actions", [])
        drift_detected = "no-op" not in actions
        classification = "risky" if "delete" in actions else ("benign" if not drift_detected else "risky")

        ds = DriftState(
            id=f"drift-{adapter_id}-{addr}",
            resource_id=addr,
            policy_ref=f"policy-{adapter_id}-baseline",
            expected_hash=canonical_hash(info.get("diff", {})),
            actual_hash=canonical_hash(info),
            drift_detected=drift_detected,
            classification=classification,
            delta={"changed_fields": list(info.get("diff", {}).keys())},
            provenance=prov,
        )
        states.append(ds)

    return states


def build_adapter_bundle(
    adapter_id: str,
    claim_set: ClaimSet,
    drift: Optional[DriftReport] = None,
    control_ids: Optional[List[str]] = None,
    timestamp: Optional[str] = None,
) -> EvidenceBundle:
    """Build a full EvidenceBundle from adapter outputs.

    This is the entry point for the adapter → OSCAL pipeline.
    The returned bundle can be passed directly to generators/sar.py's
    build_sar() function.

    Args:
        adapter_id: The adapter ADAPTER_ID.
        claim_set: ClaimSet from the adapter's normalize() or extract method.
        drift: Optional DriftReport from consume_terraform_plan() or similar.
        control_ids: NIST 800-53 control IDs this adapter supports.
        timestamp: Override timestamp (ISO 8601).

    Returns:
        EvidenceBundle suitable for build_sar().
    """
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    ctrl_ids = control_ids or ["CM-8"]

    # Convert claims to IR Evidence
    evidence_list = claims_to_ir_evidence(claim_set, adapter_id, ctrl_ids[0], ts)

    # Convert drift to IR DriftStates
    drift_states: List[DriftState] = []
    if drift:
        drift_states = drift_to_ir_states(drift, adapter_id, ts)

    # Build minimal Controls
    prov = ProvenanceRecord(source=adapter_id, timestamp=ts, version="1.0")
    controls = [
        Control(
            id=cid,
            source="nist",
            description=f"NIST SP 800-53 Rev 5 {cid}",
            provenance=prov,
        )
        for cid in ctrl_ids
    ]

    # Build minimal Policies
    policies = [
        Policy(
            id=f"policy-{adapter_id}-{cid}",
            control_ref=cid,
            description=f"{adapter_id} baseline for {cid}",
            provenance=prov,
        )
        for cid in ctrl_ids
    ]

    bundle = EvidenceBundle(
        run_id=f"run-{adapter_id}-{uuid.uuid4().hex[:8]}",
        provenance=prov,
        evidence=evidence_list,
        drift_states=drift_states,
        controls=controls,
        policies=policies,
        unmapped_ksi_ids=[],
    )

    return bundle
