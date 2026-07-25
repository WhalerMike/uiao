"""Link-gap detection (UIAO_145 §7 / ADR-132 Phase 2).

The package-side core shared by ``scripts/scan_link_gaps.py`` (CI
advisory scanner) and the ConMon dashboard's external-interconnections
panel. Canon inputs are read via ``importlib.resources`` (I4): the link
registry, the adapter registry (for regime-pack resolution), and the
control library (for control existence + doc-library evidence residue).

Gap kinds:

  GAP-AGREEMENT-UNRECORDED   active link with agreement.type: unrecorded
  GAP-NOT-ANCHORED           active link whose agreement artifact is not
                             provenance-anchored (document-library state)
  GAP-REVIEW-MISSING         active link with an agreement but no
                             next-review date declared
  GAP-REVIEW-PAST-DUE        next-review date is in the past (wall-clock
                             comparison — why this lives outside the
                             deterministic substrate walker)
  GAP-OVERLAY-NO-PACK        regime overlay declared with no active
                             vertical adapter pack registered for it
  GAP-CONTROL-UNKNOWN        link cites a control with no control-library
                             entry
  GAP-EVIDENCE-DOC-LIBRARY   a control bound in the registry still cites
                             a document-library locator ("SharePoint >")
                             in its control-library evidence
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from importlib import resources
from typing import Any

import yaml

from uiao.evidence.links import load_link_registry

# Regime overlay -> adapter-registry pack id. An overlay absent from this
# map has no shipped pack yet and always gaps. Extend in lockstep with
# each pack's authorizing ADR (ADR-132 D5).
OVERLAY_PACK_MAP: dict[str, str] = {
    "soc2": "soc2-trust-services-catalog",
    "govramp": "govramp-reciprocity-catalog",
}

DOC_LIBRARY_MARKER = "SharePoint >"


@dataclass
class Gap:
    kind: str
    link_id: str
    detail: str


def _load_canon_yaml(relpath: str) -> dict[str, Any]:
    resource = resources.files("uiao.canon").joinpath(relpath)
    if not resource.is_file():
        return {}
    with resource.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data if isinstance(data, dict) else {}


def _control_library_ids() -> set[str]:
    root = resources.files("uiao.canon").joinpath("data/control-library")
    if not root.is_dir():
        return set()
    ids: set[str] = set()
    for family_dir in root.iterdir():
        if not family_dir.is_dir():
            continue
        for entry in family_dir.iterdir():
            if entry.name.endswith(".yml"):
                ids.add(entry.name[: -len(".yml")])
    return ids


def _control_library_text(control_id: str) -> str:
    family = control_id.split("-")[0].lower()
    resource = resources.files("uiao.canon").joinpath(f"data/control-library/{family}/{control_id}.yml")
    if not resource.is_file():
        return ""
    return resource.read_text(encoding="utf-8")


def _active_pack_ids() -> set[str]:
    doc = _load_canon_yaml("adapter-registry.yaml")
    adapters = doc.get("adapters") or []
    return {
        str(entry.get("id", "")).strip()
        for entry in adapters
        if isinstance(entry, dict) and str(entry.get("status", "")).strip().lower() == "active"
    }


def scan(
    today: _dt.date | None = None,
    *,
    registry: dict[str, Any] | None = None,
) -> list[Gap]:
    """Run all gap checks against the packaged canon (or an injected registry)."""
    if today is None:
        today = _dt.date.today()

    doc = registry if registry is not None else load_link_registry()
    links = [entry for entry in (doc.get("links") or []) if isinstance(entry, dict)]
    known_controls = _control_library_ids()
    active_packs = _active_pack_ids()
    controls_in_registry: set[str] = set()
    gaps: list[Gap] = []

    for link in links:
        link_id = str(link.get("id", "")).strip() or "<unnamed>"
        status = str(link.get("status", "")).strip().lower()
        if status != "active":
            continue

        agreement = link.get("agreement") or {}
        agreement_type = str(agreement.get("type", "")).strip().lower()
        if agreement_type == "unrecorded":
            gaps.append(
                Gap(
                    "GAP-AGREEMENT-UNRECORDED",
                    link_id,
                    "no agreement artifact registered; CA-3 evidence for this link rests on an unrecorded agreement",
                )
            )
        if agreement and agreement.get("provenance-anchored") is not True:
            gaps.append(
                Gap(
                    "GAP-NOT-ANCHORED",
                    link_id,
                    f"agreement artifact is not provenance-anchored (location: {agreement.get('artifact-location', '—')})",
                )
            )

        next_review = str(agreement.get("next-review", "")).strip()
        if agreement and not next_review:
            gaps.append(
                Gap(
                    "GAP-REVIEW-MISSING",
                    link_id,
                    "agreement declares no next-review date; the CA-3 annual-review parameter is unenforceable",
                )
            )
        elif next_review:
            try:
                due = _dt.date.fromisoformat(next_review)
            except ValueError:
                pass  # malformed dates are the walker's P3; not re-reported here
            else:
                if due < today:
                    gaps.append(Gap("GAP-REVIEW-PAST-DUE", link_id, f"agreement review was due {next_review}"))

        for overlay in link.get("regime-overlays") or []:
            overlay_id = str(overlay).strip().lower()
            pack = OVERLAY_PACK_MAP.get(overlay_id)
            if pack is None or pack not in active_packs:
                gaps.append(
                    Gap(
                        "GAP-OVERLAY-NO-PACK",
                        link_id,
                        f"regime overlay '{overlay_id}' has no active vertical adapter pack (ADR-132 D5)",
                    )
                )

        for control in link.get("controls") or []:
            control_id = str(control).strip()
            controls_in_registry.add(control_id)
            if known_controls and control_id not in known_controls:
                gaps.append(
                    Gap(
                        "GAP-CONTROL-UNKNOWN",
                        link_id,
                        f"cites control {control_id} which has no control-library entry",
                    )
                )

    for control_id in sorted(controls_in_registry & known_controls):
        if DOC_LIBRARY_MARKER in _control_library_text(control_id):
            family = control_id.split("-")[0].lower()
            gaps.append(
                Gap(
                    "GAP-EVIDENCE-DOC-LIBRARY",
                    control_id,
                    f"control-library/{family}/{control_id}.yml still cites a document-library evidence locator; render from the link registry instead",
                )
            )

    return gaps


def gap_summary(gaps: list[Gap] | None = None) -> dict[str, int]:
    """Counts by gap kind (sorted keys, deterministic) for dashboards."""
    if gaps is None:
        gaps = scan()
    counts: dict[str, int] = {}
    for gap in gaps:
        counts[gap.kind] = counts.get(gap.kind, 0) + 1
    return dict(sorted(counts.items()))
