from __future__ import annotations

from typing import Any, Dict, List, Optional

from uiao_core.ir.models.core import DriftState, ProvenanceRecord, canonical_hash


def _classify_drift(
    expected_hash: str,
    actual_hash: str,
    delta: Dict[str, List[str]],
) -> str:
    if expected_hash == actual_hash:
        return "benign"
    changed_fields = set(delta.get("changed", [])) | set(delta.get("added", [])) | set(delta.get("removed", []))
    if len(changed_fields) <= 3:
        return "risky"
    return "unauthorized"


def _dict_delta(
    expected: Dict[str, Any],
    actual: Dict[str, Any],
) -> Dict[str, List[str]]:
    expected_keys = set(expected.keys())
    actual_keys = set(actual.keys())
    added = sorted(actual_keys - expected_keys)
    removed = sorted(expected_keys - actual_keys)
    changed: List[str] = []
    for key in sorted(expected_keys & actual_keys):
        if expected[key] != actual[key]:
            changed.append(key)
    return {"added": added, "removed": removed, "changed": changed}


def build_drift_state(
    *,
    resource_id: str,
    policy_ref: str,
    expected_state: Dict[str, Any],
    actual_state: Dict[str, Any],
    provenance: ProvenanceRecord,
    drift_id: Optional[str] = None,
) -> DriftState:
    """Deterministically compute a DriftState from expected vs actual state."""
    expected_hash = canonical_hash(expected_state)
    actual_hash = canonical_hash(actual_state)
    delta = _dict_delta(expected_state, actual_state)
    classification = _classify_drift(expected_hash, actual_hash, delta)
    drift_state_id = drift_id or f"drift:{resource_id}:{policy_ref}"
    return DriftState(
        id=drift_state_id,
        resource_id=resource_id,
        policy_ref=policy_ref,
        expected_hash=expected_hash,
        actual_hash=actual_hash,
        drift_detected=expected_hash != actual_hash,
        classification=classification,
        delta=delta,
        provenance=provenance,
    )
