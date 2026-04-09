        ssp_doc: Full OSCAL document dict (top-level key system-security-plan).
        bundle: EvidenceBundle used for the injection pass.

    Returns:
        Multi-line summary string.
    """
    ssp = ssp_doc.get("system-security-plan", ssp_doc)
    impl = ssp.get("control-implementation", {})
    reqs = impl.get("implemented-requirements", [])

    total_reqs = len(reqs)
    injected = sum(1 for r in reqs if r.get("statements"))
    status_counts: dict[str, int] = {}
    for r in reqs:
        for p in r.get("props", []):
            if p.get("name") == "implementation-status":
                val = p.get("value", "planned")
                status_counts[val] = status_counts.get(val, 0) + 1

    implemented = status_counts.get("implemented", 0)
    partial = status_counts.get("partially-implemented", 0)
    not_impl = status_counts.get("not-implemented", 0)
    no_evidence = total_reqs - injected

    lines = [
        f"Live SSP [{bundle.run_id}]",
        f"  Total requirements  : {total_reqs}",
        f"  Evidence injected   : {injected}",
        f"  Implemented         : {implemented}",
        f"  Partial             : {partial}",
        f"  Not-implemented     : {not_impl}",
        f"  No evidence (planned): {no_evidence}",
        f"  SCuBA run           : {bundle.run_id}",
        f"  PASS / WARN / FAIL  : {bundle.pass_count} / {bundle.warn_count} / {bundle.fail_count}",
    ]
    return "\n".join(lines)
Augments a baseline SSP skeleton (built from canon YAML + data files) with
real-world evidence drawn from a SCuBA transform result.  Each
implemented-requirement that maps to a KSI is enriched with:

  - An OSCAL statement carrying the evidence status and hash
  - A by-components entry linking to the matching control-plane component
  - An implementation-status prop reflecting the live PASS/WARN/FAIL verdict
  - A remarks annotation with the SCuBA run ID and assessment timestamp

The baseline SSP skeleton is unchanged when no matching evidence exists for a
control; this function is purely additive / non-destructive.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from uiao_core.evidence.bundle import EvidenceBundle, build_bundle_from_transform_result
from uiao_core.generators.ssp import build_ssp_skeleton
from uiao_core.ir.adapters.scuba.transformer import transform_scuba_to_ir
from uiao_core.utils.context import get_settings, load_context


def _oscal_status(evaluation: dict[str, Any]) -> str:
    """Derive OSCAL implementation-status from an evidence evaluation dict."""
    if evaluation.get("passed"):
        return "implemented"
    if evaluation.get("warning"):
        return "partially-implemented"
    return "not-implemented"


"""Live evidence injection layer for OSCAL SSP.

Augments a baseline SSP skeleton (built from canon YAML + data files) with
real-world evidence drawn from a SCuBA transform result.  Each
implemented-requirement that maps to a KSI is enriched with:

  - An OSCAL statement carrying the evidence status and hash
  - A by-components entry linking to the matching control-plane component
  - An implementation-status prop reflecting the live PASS/WARN/FAIL verdict
  - A remarks annotation with the SCuBA run ID and assessment timestamp

The baseline SSP skeleton is unchanged when no matching evidence exists for a
control; this function is purely additive / non-destructive.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from uiao_core.evidence.bundle import EvidenceBundle, build_bundle_from_transform_result
from uiao_core.generators.ssp import build_ssp_skeleton
from uiao_core.ir.adapters.scuba.transformer import transform_scuba_to_ir
from uiao_core.utils.context import get_settings, load_context


def _oscal_status(evaluation: dict[str, Any]) -> str:
    """Derive OSCAL implementation-status from an evidence evaluation dict."""
    if evaluation.get("passed"):
        return "implemented"
    if evaluation.get("warning"):
        return "partially-implemented"
    return "not-implemented"


def _find_component_uuid(ssp: dict[str, Any], ksi_id: str) -> str | None:
    """Return the UUID of the first component in the SSP.

    SCuBA evidence is tenant-wide rather than per-pillar, so we attach all
    findings to the first available component as a best-effort linkage.
    The ksi_id parameter is reserved for future per-pillar routing.
    """
    del ksi_id  # reserved for future per-pillar routing
    components = ssp.get("system-implementation", {}).get("components", [])
    if not components:
        return None
    return components[0]["uuid"]


def inject_scuba_evidence(
    ssp: dict[str, Any],
    bundle: EvidenceBundle,
) -> dict[str, Any]:
    """Inject live SCuBA evidence into an OSCAL SSP skeleton (in-place).

    For every Evidence object in bundle that has a non-None control_id,
    find the matching implemented-requirement in the SSP and:

    1. Set / overwrite the implementation-status prop.
    2. Append an OSCAL statement with the evidence status, hash, and
       a by-components entry referencing the first control-plane component.
    3. Append run provenance to remarks.

    Evidence items whose control_id does not match any existing
    implemented-requirement are silently skipped.

    Args:
        ssp: Mutable OSCAL SSP dict (value of the system-security-plan key).
        bundle: Populated EvidenceBundle from a SCuBA transform pass.

    Returns:
        The mutated ssp dict (same object, returned for convenience).
    """
    impl = ssp.get("control-implementation", {})
    reqs: list[dict[str, Any]] = impl.get("implemented-requirements", [])
    req_by_ctrl: dict[str, dict[str, Any]] = {r["control-id"]: r for r in reqs}

    for ev in bundle.evidence:
        ctrl_id = ev.control_id
        if not ctrl_id:
            continue
        req = req_by_ctrl.get(ctrl_id)
        if req is None:
            continue

        status = _oscal_status(ev.evaluation)
        ev_hash = ev.evaluation.get("canonical_hash", "")[:16]
        run_id = ev.data.get("run_id", bundle.run_id)
        ts = ev.timestamp
        ksi_id = ev.data.get("ksi_id", ctrl_id)
        details = ev.data.get("details", "")

        # 1. Implementation-status prop (replace if present)
        req.setdefault("props", [])
        req["props"] = [p for p in req["props"] if p.get("name") != "implementation-status"]
        req["props"].append({
            "name": "implementation-status",
            "value": status,
            "ns": "https://fedramp.gov/ns/oscal",
        })

        # 2. Statement with by-components
        comp_uuid = _find_component_uuid(ssp, ksi_id)
        by_components: list[dict[str, Any]] = []
        if comp_uuid:
            by_components.append({
                "component-uuid": comp_uuid,
                "uuid": str(uuid.uuid4()),
                "description": (
                    f"SCuBA evidence [{ksi_id}]: {status.upper()} | "
                    f"hash={ev_hash} | {ts}"
                ),
                "implementation-status": {"state": status},
                "props": [
                    {
                        "name": "evidence-hash",
                        "value": ev_hash,
                        "ns": "https://fedramp.gov/ns/oscal",
                    },
                    {
                        "name": "assessment-date",
                        "value": ts,
                        "ns": "https://fedramp.gov/ns/oscal",
                    },
                ],
            })

        stmt: dict[str, Any] = {
            "statement-id": f"{ctrl_id}_smt",
            "uuid": str(uuid.uuid4()),
            "description": (
                f"[SCuBA run: {run_id}] KSI {ksi_id} -> {status.upper()}"
                + (f": {details}" if details else "")
            ),
        }
        if by_components:
            stmt["by-components"] = by_components

        req.setdefault("statements", [])
        req["statements"] = [
            s for s in req["statements"]
            if s.get("statement-id") != f"{ctrl_id}_smt"
        ]
        req["statements"].append(stmt)

        # 3. Remarks annotation (avoid B005: no multi-char strip)
        existing_remarks = req.get("remarks", "")
        scuba_tag = f"[scuba:{run_id}:{ts}]"
        if scuba_tag not in existing_remarks:
            if existing_remarks:
                req["remarks"] = existing_remarks + " | " + scuba_tag
            else:
                req["remarks"] = scuba_tag

    return ssp


def build_live_ssp(
    normalized_json_path: str | Path,
    canon_path: str | Path | None = None,
    data_dir: str | Path | None = None,
    output_path: str | Path | None = None,
    enhanced: bool = False,
) -> Path:
    """Build a live OSCAL SSP by combining canon baseline with SCuBA evidence.

    Pipeline:
      1. Load canon context.
      2. Build baseline SSP skeleton (optionally enhanced with narratives).
      3. Transform SCuBA JSON to IR Evidence.
      4. Build evidence bundle.
      5. Inject live evidence into implemented-requirements.
      6. Write the final OSCAL JSON.

    Args:
        normalized_json_path: Path to a SCuBA normalized JSON file.
        canon_path: Path to canon YAML (defaults to settings).
        data_dir: Path to data YAML directory (defaults to settings).
        output_path: Destination JSON path (defaults to
            exports/oscal/uiao-ssp-live.json).
        enhanced: Also inject control-library narratives when True.

    Returns:
        Path to the written SSP JSON file.
    """
    settings = get_settings()
    if canon_path is None:
        canon_path = settings.canon_dir / "uiao_leadership_briefing_v1.0.yaml"
    if data_dir is None:
        data_dir = settings.data_dir
    if output_path is None:
        output_path = settings.exports_dir / "oscal" / "uiao-ssp-live.json"

    context = load_context(canon_path=canon_path, data_dir=data_dir)
    ssp_data = build_ssp_skeleton(context, data_dir=Path(data_dir), enhanced=enhanced)

    transform_result = transform_scuba_to_ir(normalized_json_path)
    bundle = build_bundle_from_transform_result(transform_result)

    inject_scuba_evidence(ssp_data, bundle)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump({"system-security-plan": ssp_data}, f, indent=2)

    return out


def live_ssp_summary(
    ssp_doc: dict[str, Any],
    bundle: EvidenceBundle,
) -> str:
    """Return a human-readable summary of a live SSP injection pass.

    Args:
