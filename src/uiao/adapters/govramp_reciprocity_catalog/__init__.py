"""GovRAMP Reciprocity Catalog — Conformance Adapter (state/local vertical).

Third vertical adapter pack on the UIAO substrate, authorized by
[ADR-133](../../canon/adr/adr-133-govramp-reciprocity-vertical-pack.md) and the
first for the state/local vertical [ADR-085](../../canon/adr/adr-085-universal-enterprise-positioning.md)
reserved. GovRAMP (formerly StateRAMP) provides FedRAMP-modeled cloud security
verification for state, local, and education procurement.

Why this pack is a crosswalk, not a stack
-----------------------------------------
GovRAMP assesses against the **same NIST SP 800-53 Rev 5 baseline** the
substrate's federal evidence pipeline already speaks, and its reciprocity
intake accepts **FedRAMP-derived authorization artifacts**. The pack therefore
maps existing evidence outputs onto GovRAMP submission surfaces, riding the
UIAO_140 single-ATO reciprocity model (one authoritative evidence base, N
consuming acceptance regimes). It binds the SAME surface slots
(``src/uiao/canon/data/control-planes.yml``) the federal and SOC 2 packs bind
and introduces no new engine capability — a mapping that started producing
novel control interpretations would have left the ADR-133 D1 charter.

Scope (honest)
--------------
GovRAMP eligibility is **procurement machinery adopted state-by-state, not a
regulatory mandate** (some states run their own TX-RAMP-style programs); the
pack must never be presented as compliance-with-a-law. Program administration
(membership, PMO interaction, 3PAO logistics) is engagement process, out of
scope for substrate evidence.

STATUS
------
``active`` — registered in ``adapter-registry.yaml`` under the ``state-local``
boundary (added in lockstep with ADR-133 per ADR-085 D3) and ADR-backed
(ADR-133, ACCEPTED). The two ADR-129-pattern promotion conditions are met: an
operational conformance surface exists (``emit_submission_bindings`` renders
the pack's declared ``govramp-submission-bindings.json`` output, exercised by
the adapter-conformance CI suite), and ADR-133 is ratified. On this promotion
the pack satisfies the ADR-132 D3 elevation condition requiring one active
boundary-attached regime pack; the ``govramp`` regime overlay in the link
registry resolves to this pack via the link-gap scanner's overlay map.

References
----------
    Substrate (none federal-specific):
      - src/uiao/canon/data/control-planes.yml (the shared surface slots)
      - src/uiao/canon/specs/single-ato-reciprocity-model.md (UIAO_140)
      - src/uiao/canon/adr/adr-133-govramp-reciprocity-vertical-pack.md
    Companion verticals (same slots, different regimes):
      - src/uiao/adapters/fedramp_aan_catalog/ (federal)
      - src/uiao/adapters/soc2_trust_services_catalog/ (commercial-regulated)
    External program (mapped, not vendored):
      - GovRAMP, formerly StateRAMP — https://govramp.org/
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

ADAPTER_ID: str = "govramp-reciprocity-catalog"
STATUS: str = "active"
VERTICAL: str = "state-local"
STANDARD: str = "GovRAMP (formerly StateRAMP) — NIST SP 800-53 Rev 5 baseline, reciprocity intake"
SURFACE_SLOTS_BOUND: tuple[int, ...] = (1, 2, 3, 4, 5, 6)
RECIPROCITY_BASIS: str = "UIAO_140 single-ATO reciprocity model"
# The registry's declared output (adapter-registry.yaml → outputs:).
SUBMISSION_BINDINGS_OUTPUT: str = "govramp-submission-bindings.json"

_MAPPINGS_DIR = Path(__file__).with_name("mappings")


def mappings_dir() -> Path:
    """Directory holding the slot-0N-*.yaml reciprocity-binding files."""
    return _MAPPINGS_DIR


def mapping_files() -> list[Path]:
    """Every committed slot mapping file, sorted by slot number."""
    return sorted(_MAPPINGS_DIR.glob("slot-*.yaml"))


def load_slot_mapping(slot_id: int) -> dict:
    """Load and parse the mapping file for a given surface slot id (1-6)."""
    if yaml is None:  # pragma: no cover
        raise RuntimeError("PyYAML required to load GovRAMP slot mappings")
    matches = sorted(_MAPPINGS_DIR.glob(f"slot-{slot_id:02d}-*.yaml"))
    if not matches:
        raise KeyError(f"no GovRAMP mapping file for surface slot {slot_id}")
    return cast(dict, yaml.safe_load(matches[0].read_text(encoding="utf-8")))


def emit_submission_bindings() -> dict:
    """Render the adapter's declared output: the consolidated GovRAMP submission bindings.

    This is the pack's operational surface (ADR-133 D3 / the ADR-129 D3
    pattern): it deterministically consolidates the six per-slot crosswalk
    files into the single ``govramp-submission-bindings.json`` structure the
    registry declares as this adapter's output. Side-effect free — it returns
    the structure; the caller (a CI job, a report step) decides where to
    write it.

    Each slot contributes its Rev 5 anchor, substrate source, and per-control
    bindings; the top level carries the sorted union of Rev 5 controls the
    crosswalk covers and the reciprocity basis, so a consumer can answer
    "which controls does the GovRAMP crosswalk bind, from what evidence,
    under what reciprocity theory?" without re-reading six files.
    """
    slots: list[dict] = []
    controls: set[str] = set()
    for slot_id in SURFACE_SLOTS_BOUND:
        m = load_slot_mapping(slot_id)
        bindings = m.get("bindings", [])
        for b in bindings:
            controls.add(b["rev5_control"])
        slots.append(
            {
                "slot_id": m["slot_id"],
                "slot": m["slot"],
                "govramp_anchor": m.get("govramp_anchor", ""),
                "substrate_source": m.get("substrate_source", ""),
                "reciprocity_basis": m.get("reciprocity_basis", ""),
                "bindings": bindings,
                "out_of_scope": m.get("out_of_scope", {}).get("note", ""),
            }
        )
    return {
        "adapter_id": ADAPTER_ID,
        "standard": STANDARD,
        "vertical": VERTICAL,
        "status": STATUS,
        "reciprocity_basis": RECIPROCITY_BASIS,
        "surface_slots_bound": list(SURFACE_SLOTS_BOUND),
        "controls_covered": sorted(controls),
        "controls_count": len(controls),
        "slots": slots,
    }
