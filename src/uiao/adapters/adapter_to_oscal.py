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

from ..adapters.database_base import ClaimSet, DriftReport
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
            classification=classification,  # type: ignore[arg-type]  # duck-typed: canonical classifier returns the Literal set
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


# ---------------------------------------------------------------------------
# Drift → POA&M bridge
# ---------------------------------------------------------------------------

_SEVERITY_TO_RISK = {
    "high": "high",
    "warning": "moderate",
    "info": "low",
    "none": "low",
}


def drift_to_poam_findings(
    drift: DriftReport,
    adapter_id: str,
    control_ids: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Convert an adapter DriftReport into POA&M findings.

    Each drifted resource becomes a POA&M item with title, description,
    risk level, and related controls. The output format matches what
    `generators/poam.py` `build_poam(manual_findings=...)` expects.

    Args:
        drift: DriftReport from any adapter method (consume_terraform_plan,
               apply_baseline, push_config_change, etc.)
        adapter_id: The adapter ADAPTER_ID.
        control_ids: NIST 800-53 control IDs to associate with findings.

    Returns:
        List of finding dicts, each with:
        - title, description, risk_level, related_controls
    """
    ctrl_ids = control_ids or []
    findings: List[Dict[str, Any]] = []

    resources = drift.details.get("resources", {})
    if resources:
        # Per-resource drift items (e.g., from consume_terraform_plan)
        for addr, info in resources.items():
            actions = info.get("actions", [])
            diff = info.get("diff", {})
            severity = info.get("severity", drift.severity)
            risk = _SEVERITY_TO_RISK.get(severity, "moderate")

            action_str = "/".join(actions) if actions else "drift"
            changed_fields = list(diff.keys()) if diff else []

            findings.append(
                {
                    "title": f"[{adapter_id}] {action_str}: {addr}",
                    "description": (
                        f"Adapter {adapter_id} detected {action_str} on resource "
                        f"{addr}. "
                        + (f"Changed fields: {', '.join(changed_fields)}. " if changed_fields else "")
                        + f"Severity: {severity}."
                    ),
                    "risk_level": risk,
                    "related_controls": ctrl_ids,
                }
            )
    else:
        # Aggregate drift (e.g., from baseline comparison)
        comparison = drift.details.get("comparison", {})
        summary = comparison.get("summary", {})
        nc_count = summary.get("non_compliant_count", 0)
        missing_count = summary.get("missing_count", 0)

        if nc_count > 0 or missing_count > 0:
            risk = _SEVERITY_TO_RISK.get(drift.severity, "moderate")
            findings.append(
                {
                    "title": f"[{adapter_id}] Baseline drift: {drift.drift_type}",
                    "description": (
                        f"Adapter {adapter_id} baseline comparison found "
                        f"{nc_count} non-compliant setting(s) and "
                        f"{missing_count} missing setting(s). "
                        f"Drift type: {drift.drift_type}."
                    ),
                    "risk_level": risk,
                    "related_controls": ctrl_ids,
                }
            )

        # Non-compliant items as individual findings
        for nc in comparison.get("non_compliant", []):
            findings.append(
                {
                    "title": f"[{adapter_id}] Non-compliant: {nc.get('key', 'unknown')}",
                    "description": (f"Expected: {nc.get('expected')}, Actual: {nc.get('actual')}."),
                    "risk_level": _SEVERITY_TO_RISK.get(drift.severity, "moderate"),
                    "related_controls": ctrl_ids,
                }
            )

    return findings


def build_adapter_poam(
    adapter_id: str,
    drift: DriftReport,
    control_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build a complete OSCAL POA&M from adapter drift output.

    Convenience function that converts drift → findings → POA&M.

    Args:
        adapter_id: The adapter ADAPTER_ID.
        drift: DriftReport from any adapter method.
        control_ids: NIST 800-53 control IDs.

    Returns:
        OSCAL POA&M document dict.
    """
    from ..generators.poam import build_poam

    findings = drift_to_poam_findings(drift, adapter_id, control_ids)
    # build_poam expects a context dict; pass empty since we're using manual_findings
    poam = build_poam(context={}, manual_findings=findings)
    return poam


# ---------------------------------------------------------------------------
# Adapter → SSP injection
# ---------------------------------------------------------------------------


def _minimal_ssp_skeleton(
    system_name: str = "UIAO Adapter-Assessed System",
    system_id: str = "",
) -> Dict[str, Any]:
    """Create a minimal OSCAL SSP skeleton suitable for evidence injection.

    This is a lightweight alternative to build_ssp_skeleton() that doesn't
    require the full canon data directory. Used for adapter-only testing
    and adapter-first SSP bootstrapping.
    """
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "uuid": str(uuid.uuid4()),
        "metadata": {
            "title": system_name,
            "version": "1.0",
            "oscal-version": "1.0.4",
            "last-modified": now,
            "published": now,
        },
        "system-characteristics": {
            "system-name": system_name,
            "system-id": system_id or str(uuid.uuid4()),
            "security-sensitivity-level": "moderate",
            "system-information": {
                "information-types": [
                    {
                        "title": "Adapter-assessed infrastructure",
                        "description": "System components assessed via UIAO adapters.",
                    }
                ],
            },
            "security-impact-level": {
                "security-objective-confidentiality": "moderate",
                "security-objective-integrity": "moderate",
                "security-objective-availability": "moderate",
            },
            "status": {"state": "operational"},
            "authorization-boundary": {
                "description": "GCC-Moderate boundary per UIAO ARCHITECTURE.md §2.1",
            },
        },
        "system-implementation": {
            "components": [
                {
                    "uuid": str(uuid.uuid4()),
                    "type": "this-system",
                    "title": system_name,
                    "status": {"state": "operational"},
                }
            ],
        },
        "control-implementation": {
            "description": "Controls implemented via UIAO adapter evidence.",
            "implemented-requirements": [],
        },
    }


def inject_adapter_evidence_into_ssp(
    ssp: Dict[str, Any],
    bundle: EvidenceBundle,
) -> Dict[str, Any]:
    """Inject adapter evidence from an EvidenceBundle into an SSP.

    Generic wrapper around inject_scuba_evidence() that works with any
    adapter's bundle. The underlying function is generic despite its
    SCuBA-specific name.

    Args:
        ssp: OSCAL SSP plan dict (the value of ssp["system-security-plan"],
             NOT the outer wrapper).
        bundle: EvidenceBundle from build_adapter_bundle().

    Returns:
        The mutated SSP dict with injected evidence.
    """
    from ..generators.ssp_inject import inject_scuba_evidence

    return inject_scuba_evidence(ssp, bundle)


def build_adapter_ssp(
    adapter_id: str,
    claim_set: ClaimSet,
    control_ids: Optional[List[str]] = None,
    system_name: str = "UIAO Adapter-Assessed System",
    timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a complete OSCAL SSP from adapter claims.

    Convenience function: adapter claims → bundle → minimal SSP skeleton →
    inject evidence → return wrapped SSP.

    Args:
        adapter_id: The adapter ADAPTER_ID.
        claim_set: ClaimSet from the adapter.
        control_ids: NIST 800-53 control IDs.
        system_name: SSP system name.
        timestamp: Override timestamp.

    Returns:
        OSCAL SSP document dict with top-level "system-security-plan" key.
    """
    bundle = build_adapter_bundle(
        adapter_id=adapter_id,
        claim_set=claim_set,
        control_ids=control_ids,
        timestamp=timestamp,
    )
    ssp = _minimal_ssp_skeleton(system_name=system_name)
    inject_adapter_evidence_into_ssp(ssp, bundle)
    return {"system-security-plan": ssp}
