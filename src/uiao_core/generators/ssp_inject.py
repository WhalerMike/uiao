"""Live evidence injection layer for OSCAL SSP.

Consumes a *SCuBA* normalised-JSON artefact (produced by
``transform_scuba_to_ir`` + ``build_bundle_from_transform_result``), merges the
resulting :class:`~uiao_core.evidence.bundle.EvidenceBundle` into an OSCAL SSP
skeleton and writes the enriched document to disk.

Public API
----------
inject_scuba_evidence(ssp, bundle)
    Mutates an OSCAL SSP plan dict in-place with SCuBA evidence.
build_live_ssp(normalized_json_path, ...)
    Full pipeline: load normalised JSON -> build bundle -> inject -> write SSP JSON.
live_ssp_summary(ssp_doc, bundle)
    Return a human-readable summary string for CLI output.
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
    """Map an evidence evaluation dict to an OSCAL implementation-status string.

    Checks the ``passed`` and ``warning`` boolean flags produced by the SCuBA
    transformer.  Falls back to ``"not-implemented"`` for empty or unknown dicts.
    """
    if evaluation.get("passed"):
        return "implemented"
    if evaluation.get("warning"):
        return "partially-implemented"
    return "not-implemented"


def _find_component_uuid(ssp: dict[str, Any], ksi_id: str) -> str | None:
    """Return the UUID of the first component in *ssp*.

    Falls back to ``None`` when no components are present.  The *ksi_id*
    parameter is accepted for API symmetry but currently unused.
    """
    del ksi_id  # best-effort: always use first component
    try:
        components = ssp["system-implementation"]["components"]
        if components:
            return components[0]["uuid"]
    except (KeyError, IndexError, TypeError):
        pass
    return None


def inject_scuba_evidence(
    ssp: dict[str, Any],
    bundle: EvidenceBundle,
) -> dict[str, Any]:
    """Inject SCuBA evidence from *bundle* into *ssp* in-place.

    Operates on the raw OSCAL plan dict (the value of
    ``ssp["system-security-plan"]``, **not** the outer wrapper).  For every
    :class:`~uiao_core.evidence.bundle.EvidenceBundle` requirement the function:

    * Adds or updates an ``implementation-status`` prop.
    * Appends the ``run_id`` to ``remarks``.
    * Creates a ``statements`` entry containing a ``by-components`` record.

    Evidence items with ``control_id=None`` are skipped.  The function is
    idempotent: calling it twice produces only one statement per control.

    Returns the mutated *ssp* for convenience.
    """
    control_impl = ssp.setdefault("control-implementation", {})
    reqs = control_impl.setdefault("implemented-requirements", [])
    req_by_id: dict[str, dict] = {r.get("control-id", ""): r for r in reqs}
    component_uuid = _find_component_uuid(ssp, "")
    run_id = bundle.run_id

    for ev in bundle.evidence:
        if ev.control_id is None:
            continue
        ctrl_id = ev.control_id
        req = req_by_id.get(ctrl_id)
        if req is None:
            req = {"uuid": str(uuid.uuid4()), "control-id": ctrl_id}
            reqs.append(req)
            req_by_id[ctrl_id] = req

        # --- implementation-status prop ---
        props = req.setdefault("props", [])
        # Remove any existing implementation-status prop (idempotent)
        props[:] = [p for p in props if p.get("name") != "implementation-status"]
        props.append(
            {
                "name": "implementation-status",
                "value": _oscal_status(ev.evaluation or {}),
                "ns": "https://fedramp.gov/ns/oscal",
            }
        )

        # --- remarks with run_id (B005 compliant: no multi-char lstrip) ---
        existing_remarks = req.get("remarks", "")
        if run_id not in existing_remarks:
            if existing_remarks:
                req["remarks"] = existing_remarks + " | " + run_id
            else:
                req["remarks"] = run_id

        # --- statements with by-components ---
        if component_uuid:
            stmts = req.setdefault("statements", [])
            # Idempotent: only add statement if none exists for this run
            existing_stmt_ids = {s.get("statement-id") for s in stmts}
            stmt_id = f"{ctrl_id}_smt.{run_id}"
            if stmt_id not in existing_stmt_ids:
                eval_data = ev.evaluation or {}
                by_comp: dict[str, Any] = {
                    "component-uuid": component_uuid,
                    "uuid": str(uuid.uuid4()),
                    "description": eval_data.get("details", ""),
                    "props": [
                        {
                            "name": "evidence-hash",
                            "value": eval_data.get("canonical_hash", ""),
                            "ns": "https://uiao.gov/ns/oscal",
                        },
                        {
                            "name": "assessment-date",
                            "value": ev.timestamp or "",
                            "ns": "https://uiao.gov/ns/oscal",
                        },
                    ],
                }
                stmts.append(
                    {
                        "statement-id": stmt_id,
                        "uuid": str(uuid.uuid4()),
                        "by-components": [by_comp],
                    }
                )

    return ssp


def build_live_ssp(
    normalized_json_path: str | Path,
    output_path: str | Path | None = None,
    tenant_id: str | None = None,
    system_id: str | None = None,
    title: str | None = None,
    enhanced: bool = True,
) -> Path:
    """Load a SCuBA normalised-JSON file, build an evidence bundle, inject
    evidence into a fresh SSP skeleton and write the result to *output_path*.

    Parameters
    ----------
    normalized_json_path:
        Path to the SCuBA normalised-JSON artefact.
    output_path:
        Destination for the live SSP JSON.  Defaults to
        ``<stem>_live_ssp.json`` next to *normalized_json_path*.
    tenant_id, system_id, title:
        Forwarded to :func:`build_ssp_skeleton`.  Values are read from
        the project context when *None*.
    enhanced:
        When *True* (default) the SSP skeleton includes extended metadata.

    Returns
    -------
    Path
        Absolute path of the written SSP JSON file.
    """
    normalized_json_path = Path(normalized_json_path)

    # --- resolve context defaults ---
    try:
        ctx = load_context()
        settings = get_settings()
        tenant_id = tenant_id or getattr(settings, "tenant_id", None) or "unknown-tenant"
        system_id = system_id or getattr(ctx, "system_id", None) or "unknown-system"
        title = title or getattr(ctx, "system_name", None) or "Live SSP"
    except Exception:  # pragma: no cover
        tenant_id = tenant_id or "unknown-tenant"
        system_id = system_id or "unknown-system"
        title = title or "Live SSP"

    # --- build evidence bundle ---
    ir_result = transform_scuba_to_ir(normalized_json_path)
    bundle = build_bundle_from_transform_result(ir_result)

    # --- build SSP skeleton ---
    ssp_doc = build_ssp_skeleton(
        context={
            "tenant_id": tenant_id,
            "system_id": system_id,
            "system_name": title,
        },
        enhanced=enhanced,
    )
    # --- inject evidence into the plan dict ---
    plan = ssp_doc.setdefault("system-security-plan", {})
    inject_scuba_evidence(plan, bundle)

    # --- write output ---
    if output_path is None:
        output_path = normalized_json_path.parent / (normalized_json_path.stem + "_live_ssp.json")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(ssp_doc, fh, indent=2)

    return output_path.resolve()


def live_ssp_summary(ssp_doc: dict[str, Any], bundle: EvidenceBundle) -> str:
    """Return a human-readable summary of the live SSP injection pass.

    Parameters
    ----------
    ssp_doc:
        Either the enriched OSCAL SSP dict with a ``"system-security-plan"``
        wrapper key, or the raw plan dict without the wrapper.
    bundle:
        The :class:`~uiao_core.evidence.bundle.EvidenceBundle` that was injected.

    Returns
    -------
    str
        Multi-line summary suitable for printing to a terminal.
    """
    # Handle both wrapped {"system-security-plan": ...} and raw plan dict
    plan = ssp_doc.get("system-security-plan", ssp_doc)

    meta = plan.get("metadata", {})
    title = meta.get("title", "Unknown")
    reqs = plan.get("control-implementation", {}).get("implemented-requirements", [])
    injected = [r for r in reqs if bundle.run_id in r.get("remarks", "")]
    implemented = sum(
        1
        for r in injected
        if any(p.get("name") == "implementation-status" and p.get("value") == "implemented" for p in r.get("props", []))
    )
    partial = sum(
        1
        for r in injected
        if any(
            p.get("name") == "implementation-status" and p.get("value") == "partially-implemented"
            for p in r.get("props", [])
        )
    )
    not_impl = sum(
        1
        for r in injected
        if any(
            p.get("name") == "implementation-status" and p.get("value") == "not-implemented" for p in r.get("props", [])
        )
    )
    lines = [
        f"Live SSP [{bundle.run_id}]",
        f"  Title            : {title}",
        f"  Evidence items   : {len(bundle.evidence)}",
        f"  Controls updated : {len(injected)}",
        f"  Total controls   : {len(reqs)}",
        f"  Implemented      : {implemented} / {partial} / {not_impl}",
    ]
    return "\n".join(lines)
