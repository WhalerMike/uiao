"""Live evidence injection layer for OSCAL SSP.

Consumes a *SCuBA* normalised-JSON artefact (produced by
``transform_scuba_to_ir`` + ``build_bundle_from_transform_result``), merges the
resulting :class:`~uiao_core.evidence.bundle.EvidenceBundle` into an OSCAL SSP
skeleton and writes the enriched document to disk.

Public API
----------
inject_scuba_evidence(ssp, bundle)
    Mutates an OSCAL SSP dict in-place with SCuBA evidence.
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

_OSCAL_STATUS_MAP = {
    "pass": "implemented",
    "fail": "partial",
    "error": "partial",
    "mixed": "partial",
    "unknown": "planned",
}


def _oscal_status(evaluation: dict[str, Any]) -> str:
    """Map a SCuBA evaluation dict to an OSCAL implementation-status string."""
    raw = (evaluation.get("overall_result") or "unknown").lower()
    return _OSCAL_STATUS_MAP.get(raw, "planned")


def _find_component_uuid(ssp: dict[str, Any], ksi_id: str) -> str | None:
    """Return the UUID of the first component whose title matches *ksi_id*.

    Falls back to the first component UUID in the document regardless of
    title so that the inject step always has a UUID to work with.
    """
    del ksi_id  # best-effort lookup; always use first component for now
    try:
        components = ssp["system-security-plan"]["system-implementation"]["components"]
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

    For every :class:`~uiao_core.evidence.bundle.EvidenceBundle` requirement
    the function locates the matching ``implemented-requirement`` in the SSP
    (by ``control-id``) and:

    * Sets ``implementation-status.state``.
    * Appends a ``SCUBA:<run-id>`` tag to ``remarks``.
    * Adds a ``by-component`` observation entry linking to the component UUID.

    Returns the mutated *ssp* for convenience.
    """
    plan = ssp.setdefault("system-security-plan", {})
    control_impl = plan.setdefault("control-implementation", {})
    reqs = control_impl.setdefault("implemented-requirements", [])

    req_by_id: dict[str, dict] = {r.get("control-id", ""): r for r in reqs}
    component_uuid = _find_component_uuid(ssp, "")
    run_id = bundle.run_id

    for ev in bundle.evidence:
        ctrl_id = ev.ksi_id  # e.g. "KSI-IA-01"
        req = req_by_id.get(ctrl_id)
        if req is None:
            req = {"uuid": str(uuid.uuid4()), "control-id": ctrl_id}
            reqs.append(req)
            req_by_id[ctrl_id] = req

        # implementation-status
        req.setdefault("implementation-status", {})["state"] = _oscal_status(ev.evaluation or {})

        # remarks - B005 compliant: no multi-char lstrip
        scuba_tag = f"SCUBA:{run_id}"
        existing_remarks = req.get("remarks", "")
        if existing_remarks:
            req["remarks"] = existing_remarks + " | " + scuba_tag
        else:
            req["remarks"] = scuba_tag

        # by-component
        if component_uuid:
            by_comp = req.setdefault("by-components", [])
            by_comp.append(
                {
                    "component-uuid": component_uuid,
                    "uuid": str(uuid.uuid4()),
                    "description": (ev.evaluation.get("details", "") if ev.evaluation else ""),
                    "implementation-status": {"state": _oscal_status(ev.evaluation or {})},
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

    # --- resolve context defaults ----------------------------------------
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

    # --- build evidence bundle -------------------------------------------
    with normalized_json_path.open() as fh:
        normalized = json.load(fh)

    ir_result = transform_scuba_to_ir(normalized)
    bundle = build_bundle_from_transform_result(ir_result)

    # --- build SSP skeleton ----------------------------------------------
    ssp = build_ssp_skeleton(
        tenant_id=tenant_id,
        system_id=system_id,
        title=title,
        enhanced=enhanced,
    )

    # --- inject evidence -------------------------------------------------
    inject_scuba_evidence(ssp, bundle)

    # --- write output ----------------------------------------------------
    if output_path is None:
        output_path = normalized_json_path.parent / (normalized_json_path.stem + "_live_ssp.json")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(ssp, fh, indent=2)

    return output_path.resolve()


def live_ssp_summary(ssp_doc: dict[str, Any], bundle: EvidenceBundle) -> str:
    """Return a human-readable summary of the live SSP injection pass.

    Parameters
    ----------
    ssp_doc:
        The enriched OSCAL SSP dict (as returned by :func:`build_live_ssp`
        after loading from disk, or the in-memory result of
        :func:`inject_scuba_evidence`).
    bundle:
        The :class:`~uiao_core.evidence.bundle.EvidenceBundle` that was
        injected.

    Returns
    -------
    str
        Multi-line summary suitable for printing to a terminal.
    """
    plan = ssp_doc.get("system-security-plan", {})
    meta = plan.get("metadata", {})
    title = meta.get("title", "Unknown")
    reqs = plan.get("control-implementation", {}).get("implemented-requirements", [])
    injected = [r for r in reqs if "SCUBA:" in r.get("remarks", "")]
    lines = [
        f"Live SSP [{bundle.run_id}]",
        f"  Title            : {title}",
        f"  Evidence items   : {len(bundle.evidence)}",
        f"  Controls updated : {len(injected)}",
        f"  Total controls   : {len(reqs)}",
    ]
    return "\n".join(lines)
