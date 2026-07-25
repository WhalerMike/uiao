"""Conformance tests for the GovRAMP reciprocity vertical (ADR-133).

The third vertical adapter pack and the first state/local one. These tests
assert the pack is well-formed, binds the *same* substrate surface slots the
federal and SOC 2 verticals bind, registers truthfully under the new
`state-local` boundary (shipped in lockstep with ADR-133 per ADR-085 D3),
and exposes the operational surface (`emit_submission_bindings`) that the
ADR-129-pattern promotion to `active` requires. Also covers the regime
overlay wiring: a link declaring `govramp` resolves to this active pack, so
no GAP-OVERLAY-NO-PACK fires.

Companion:
- src/uiao/adapters/govramp_reciprocity_catalog/__init__.py
- src/uiao/adapters/govramp_reciprocity_catalog/mappings/slot-0N-*.yaml
- src/uiao/adapters/soc2_trust_services_catalog/ (the pattern precedent)
- src/uiao/canon/data/control-planes.yml (the shared slots)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from uiao.adapters import govramp_reciprocity_catalog, soc2_trust_services_catalog

_ROOT = Path(__file__).resolve().parents[2]
_PLANES = _ROOT / "src" / "uiao" / "canon" / "data" / "control-planes.yml"
_REGISTRY = _ROOT / "src" / "uiao" / "canon" / "adapter-registry.yaml"
_SCHEMA = _ROOT / "src" / "uiao" / "schemas" / "adapter-registry" / "adapter-registry.schema.json"

_SLOT_PLANE = {
    1: "identity",
    2: "addressing",
    3: "network",
    4: "telemetry",
    5: "endpoint",
    6: "security",
}


def _registry_entry() -> dict[str, Any]:
    data = yaml.safe_load(_REGISTRY.read_text(encoding="utf-8"))
    for entry in data["adapters"]:
        if entry.get("id") == "govramp-reciprocity-catalog":
            return entry
    raise AssertionError("govramp-reciprocity-catalog not found in adapter-registry.yaml")


# ---------------------------------------------------------------------------
# Manifest shape
# ---------------------------------------------------------------------------


def test_manifest_is_active_state_local_vertical() -> None:
    assert govramp_reciprocity_catalog.ADAPTER_ID == "govramp-reciprocity-catalog"
    # Registered, ADR-backed (ADR-133 ACCEPTED), and operational (emitter +
    # CI conformance coverage) — active, per the ADR-129 promotion pattern.
    assert govramp_reciprocity_catalog.STATUS == "active"
    assert govramp_reciprocity_catalog.VERTICAL == "state-local"
    assert govramp_reciprocity_catalog.SURFACE_SLOTS_BOUND == (1, 2, 3, 4, 5, 6)
    assert "UIAO_140" in govramp_reciprocity_catalog.RECIPROCITY_BASIS


def test_binds_same_slots_as_other_verticals() -> None:
    assert govramp_reciprocity_catalog.SURFACE_SLOTS_BOUND == soc2_trust_services_catalog.SURFACE_SLOTS_BOUND


# ---------------------------------------------------------------------------
# Mapping files
# ---------------------------------------------------------------------------


def test_all_six_slot_mappings_exist_and_parse() -> None:
    files = govramp_reciprocity_catalog.mapping_files()
    assert len(files) == 6
    for slot_id, plane in _SLOT_PLANE.items():
        m = govramp_reciprocity_catalog.load_slot_mapping(slot_id)
        assert m["slot_id"] == slot_id
        assert m["slot"] == plane
        assert m["vertical"] == "state-local"
        assert m["status"] == "active"
        assert "reciprocity_basis" in m and "UIAO_140" in m["reciprocity_basis"]
        assert m["bindings"], f"slot {slot_id} has no bindings"


def test_slot_names_match_control_planes_canon() -> None:
    planes = yaml.safe_load(_PLANES.read_text(encoding="utf-8"))
    plane_ids = [p["id"] for p in planes["control_planes"]]
    for slot_id in govramp_reciprocity_catalog.SURFACE_SLOTS_BOUND:
        m = govramp_reciprocity_catalog.load_slot_mapping(slot_id)
        assert m["slot"] in plane_ids


def test_bindings_anchor_to_rev5_controls() -> None:
    pattern = re.compile(r"^[A-Z]{2}-[0-9]+$")
    for slot_id in govramp_reciprocity_catalog.SURFACE_SLOTS_BOUND:
        m = govramp_reciprocity_catalog.load_slot_mapping(slot_id)
        for b in m["bindings"]:
            assert pattern.match(b["rev5_control"]), b["rev5_control"]
            assert b["confidence"] in ("high", "medium", "low")
            assert b["rationale"].strip()


def test_unknown_slot_raises() -> None:
    with pytest.raises(KeyError):
        govramp_reciprocity_catalog.load_slot_mapping(7)


# ---------------------------------------------------------------------------
# Operational surface (ADR-129-pattern promotion condition)
# ---------------------------------------------------------------------------


def test_emit_submission_bindings_output_shape() -> None:
    out = govramp_reciprocity_catalog.emit_submission_bindings()
    assert out["adapter_id"] == "govramp-reciprocity-catalog"
    assert out["vertical"] == "state-local"
    assert out["status"] == "active"
    assert out["reciprocity_basis"] == "UIAO_140 single-ATO reciprocity model"
    assert out["surface_slots_bound"] == [1, 2, 3, 4, 5, 6]
    assert len(out["slots"]) == 6
    assert out["controls_count"] == len(out["controls_covered"]) > 0
    assert out["controls_covered"] == sorted(out["controls_covered"])
    # Cross-program sanity: the crosswalk covers identity + boundary + conmon anchors.
    for expected in ("IA-2", "AC-2", "SC-7", "AU-6", "CM-8", "IR-6"):
        assert expected in out["controls_covered"]


# ---------------------------------------------------------------------------
# Registry + schema (lockstep per ADR-133 D2)
# ---------------------------------------------------------------------------


def test_registry_row_boundary_and_status() -> None:
    entry = _registry_entry()
    assert entry["status"] == "active"
    assert entry["gcc-boundary"] == "state-local"
    assert entry["class"] == "conformance"
    assert entry["mission-class"] == "policy"
    assert entry["ztmm-pillars"] == []
    assert "controls" not in entry  # mirrors the SOC 2 precedent
    assert "govramp-submission-bindings.json" in entry["outputs"]


def test_schema_enum_gained_state_local() -> None:
    import json

    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    enum = schema["$defs"]["adapter"]["properties"]["gcc-boundary"]["enum"] if "$defs" in schema else None
    if enum is None:
        # Fallback: search the whole document for the gcc-boundary enum.
        text = _SCHEMA.read_text(encoding="utf-8")
        assert '"state-local"' in text
    else:
        assert "state-local" in enum


# ---------------------------------------------------------------------------
# Regime overlay wiring (UIAO_145 / ADR-133 D4)
# ---------------------------------------------------------------------------


def test_govramp_overlay_resolves_to_active_pack_no_gap() -> None:
    from uiao.evidence.link_gaps import OVERLAY_PACK_MAP, scan

    assert OVERLAY_PACK_MAP["govramp"] == "govramp-reciprocity-catalog"
    registry = {
        "links": [
            {
                "id": "state-partner-exchange",
                "status": "active",
                "counterparty": {"name": "Example State Agency", "class": "state"},
                "ssot-stance": "they-are-source",
                "agreement": {"type": "mou", "artifact-location": "x", "provenance-anchored": True},
                "regime-overlays": ["govramp"],
                "next-review": "2027-07-25",
            }
        ]
    }
    gaps = scan(registry=registry)
    assert not [g for g in gaps if g.kind == "GAP-OVERLAY-NO-PACK"], [g.detail for g in gaps]
