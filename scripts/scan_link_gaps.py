#!/usr/bin/env python3
"""Link-gap scanner (UIAO_145 §7 / ADR-132 Phase 2).

Scans the link registry (src/uiao/canon/link-registry.yaml) for governance
gaps the deterministic substrate walker deliberately does not judge:

  GAP-AGREEMENT-UNRECORDED   active link with agreement.type: unrecorded
  GAP-NOT-ANCHORED           active link whose agreement artifact is not
                             provenance-anchored (document-library state)
  GAP-REVIEW-MISSING         active link with an agreement but no
                             next-review date declared
  GAP-REVIEW-PAST-DUE        next-review date is in the past (wall-clock
                             comparison — this is why the check lives here
                             and not in the walker)
  GAP-OVERLAY-NO-PACK        regime overlay declared with no active
                             vertical adapter pack registered for it
  GAP-CONTROL-UNKNOWN        link cites a control with no entry in the
                             control library
  GAP-EVIDENCE-DOC-LIBRARY   a control bound in the registry still cites a
                             document-library locator ("SharePoint >") in
                             its control-library evidence — the pointer
                             pattern ADR-132 Phase 2 retires

Sibling of scan_publication_gaps.py and scan_lifecycle_consistency.py:
advisory by default (exit 0, report to stdout); --strict exits 1 when any
gap is found; --json emits machine-readable findings.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import pathlib
import sys
from dataclasses import asdict, dataclass

import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
LINK_REGISTRY = REPO_ROOT / "src" / "uiao" / "canon" / "link-registry.yaml"
ADAPTER_REGISTRY = REPO_ROOT / "src" / "uiao" / "canon" / "adapter-registry.yaml"
CONTROL_LIBRARY = REPO_ROOT / "src" / "uiao" / "canon" / "data" / "control-library"

# Regime overlay -> adapter-registry pack id. An overlay listed here maps
# to the vertical pack that satisfies it; an overlay absent from this map
# has no shipped pack yet and always gaps. Extend in lockstep with each
# pack's authorizing ADR (ADR-132 D5).
OVERLAY_PACK_MAP: dict[str, str] = {
    "soc2": "soc2-trust-services-catalog",
}

DOC_LIBRARY_MARKER = "SharePoint >"


@dataclass
class Gap:
    kind: str
    link_id: str
    detail: str


def _load_yaml(path: pathlib.Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data if isinstance(data, dict) else {}


def _control_library_ids() -> set[str]:
    ids: set[str] = set()
    if not CONTROL_LIBRARY.is_dir():
        return ids
    for path in CONTROL_LIBRARY.rglob("*.yml"):
        ids.add(path.stem)
    return ids


def _active_pack_ids() -> set[str]:
    if not ADAPTER_REGISTRY.is_file():
        return set()
    doc = _load_yaml(ADAPTER_REGISTRY)
    adapters = doc.get("adapters") or []
    return {
        str(entry.get("id", "")).strip()
        for entry in adapters
        if isinstance(entry, dict) and str(entry.get("status", "")).strip().lower() == "active"
    }


def scan(today: _dt.date | None = None) -> list[Gap]:
    """Run all gap checks. `today` is injectable for tests."""
    if today is None:
        today = _dt.date.today()

    gaps: list[Gap] = []
    if not LINK_REGISTRY.is_file():
        return gaps

    doc = _load_yaml(LINK_REGISTRY)
    links = [entry for entry in (doc.get("links") or []) if isinstance(entry, dict)]
    known_controls = _control_library_ids()
    active_packs = _active_pack_ids()
    controls_in_registry: set[str] = set()

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
                    gaps.append(
                        Gap(
                            "GAP-REVIEW-PAST-DUE",
                            link_id,
                            f"agreement review was due {next_review}",
                        )
                    )

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

    # Doc-library locator check: controls bound in the registry whose
    # control-library evidence still points at a document library.
    for control_id in sorted(controls_in_registry & known_controls):
        family = control_id.split("-")[0].lower()
        path = CONTROL_LIBRARY / family / f"{control_id}.yml"
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if DOC_LIBRARY_MARKER in text:
            gaps.append(
                Gap(
                    "GAP-EVIDENCE-DOC-LIBRARY",
                    control_id,
                    f"control-library/{family}/{control_id}.yml still cites a document-library evidence locator; render from the link registry instead",
                )
            )

    return gaps


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--strict", action="store_true", help="exit 1 if any gap is found")
    parser.add_argument("--json", action="store_true", help="emit findings as JSON")
    args = parser.parse_args(argv)

    gaps = scan()

    if args.json:
        print(json.dumps([asdict(g) for g in gaps], indent=2))
    else:
        if gaps:
            width = max(len(g.kind) for g in gaps)
            for g in gaps:
                print(f"{g.kind:<{width}}  {g.link_id}: {g.detail}")
        print(f"\nLink gaps: {len(gaps)}")
        print(f"Mode:      {'STRICT' if args.strict else 'ADVISORY (use --strict to fail on gaps)'}")

    if args.strict and gaps:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
