"""Conformance tests for the SOC 2 Trust Services vertical (ADR-085 / ADR-129).

These tests assert the second (non-federal) vertical adapter pack is well-formed
and — the point of the whole exercise — binds the *same* substrate surface slots
the federal vertical binds, using the *same* control-planes.yml definitions,
with no federal-specific coupling. That is ADR-085 made executable: the substrate
is vertical-agnostic; the vertical adapter supplies the crosswalk.

Companion:
- src/uiao/adapters/soc2_trust_services_catalog/__init__.py
- src/uiao/adapters/soc2_trust_services_catalog/mappings/slot-0N-*.yaml
- src/uiao/adapters/fedramp_aan_catalog/ (the federal vertical, same slots)
- src/uiao/canon/data/control-planes.yml (the shared slots)
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from uiao.adapters import fedramp_aan_catalog, soc2_trust_services_catalog

_ROOT = Path(__file__).resolve().parents[2]
_PLANES = _ROOT / "src" / "uiao" / "canon" / "data" / "control-planes.yml"
_REGISTRY = _ROOT / "src" / "uiao" / "canon" / "adapter-registry.yaml"

# control-planes.yml order defines the canonical slot numbering (1-based).
_SLOT_PLANE = {
    1: "identity",
    2: "addressing",
    3: "network",
    4: "telemetry",
    5: "endpoint",
    6: "security",
}


def _plane_ids() -> list[str]:
    data = yaml.safe_load(_PLANES.read_text(encoding="utf-8"))
    return [p["id"] for p in data["control_planes"]]


# ---------------------------------------------------------------------------
# Manifest shape
# ---------------------------------------------------------------------------


def test_manifest_is_non_federal_proposed_vertical() -> None:
    assert soc2_trust_services_catalog.ADAPTER_ID == "soc2-trust-services-catalog"
    # Registered + ADR-backed (ADR-129) but not yet operational — proposed, not
    # active. Promotion to active is gated on an operational gate / customer.
    assert soc2_trust_services_catalog.STATUS == "proposed"
    assert soc2_trust_services_catalog.VERTICAL == "commercial-regulated"
    assert soc2_trust_services_catalog.SURFACE_SLOTS_BOUND == (1, 2, 3, 4, 5, 6)


def test_no_federal_terms_leak_into_the_manifest() -> None:
    # The pack must be genuinely non-federal — no FedRAMP/KSI/NIST framing in
    # its own identity fields (ADR-085 D1/D6).
    blob = " ".join(
        str(getattr(soc2_trust_services_catalog, name)) for name in ("ADAPTER_ID", "STATUS", "VERTICAL", "STANDARD")
    ).lower()
    for term in ("fedramp", "ksi", "nist", "federal", "oscal"):
        assert term not in blob


# ---------------------------------------------------------------------------
# Mapping files are well-formed and bind every declared slot
# ---------------------------------------------------------------------------


def test_a_mapping_file_exists_for_every_bound_slot() -> None:
    files = soc2_trust_services_catalog.mapping_files()
    assert len(files) == len(soc2_trust_services_catalog.SURFACE_SLOTS_BOUND)


@pytest.mark.parametrize("slot_id", sorted(_SLOT_PLANE))
def test_mapping_binds_the_matching_substrate_plane(slot_id: int) -> None:
    mapping = soc2_trust_services_catalog.load_slot_mapping(slot_id)
    assert mapping["slot_id"] == slot_id
    assert mapping["slot"] == _SLOT_PLANE[slot_id]
    assert mapping["status"] == "proposed"
    assert mapping["vertical"] == "commercial-regulated"
    # Every binding names a TSC criterion + a substrate capability + rationale.
    assert mapping["bindings"], f"slot {slot_id} has no bindings"
    for b in mapping["bindings"]:
        assert b["tsc_criterion"].startswith("CC")
        assert b["substrate_capability"].strip()
        assert b["rationale"].strip()
    # Honest scope: every slot states what it does NOT claim.
    assert mapping["out_of_scope"]["note"].strip()


# ---------------------------------------------------------------------------
# The whole point: same slots as the federal vertical, same substrate planes
# ---------------------------------------------------------------------------


def test_reuses_the_federal_vertical_slot_space() -> None:
    # Both verticals draw from the SAME slot space; SOC 2's technical Common
    # Criteria bind slots 1-6, a subset of the federal pack's 1-7 (continuity /
    # slot 7 maps to SOC 2's Availability category, deliberately out of scope for
    # this Common-Criteria scaffold). The point is shared slots, not identical
    # coverage.
    soc2 = set(soc2_trust_services_catalog.SURFACE_SLOTS_BOUND)
    federal = set(fedramp_aan_catalog.SURFACE_SLOTS_BOUND)
    assert soc2, "SOC 2 vertical binds no slots"
    assert soc2 <= federal, (
        "the second vertical must draw from the federal vertical's slot space; "
        f"SOC 2-only slots: {sorted(soc2 - federal)}"
    )


def test_every_slot_resolves_to_a_real_control_plane() -> None:
    plane_ids = set(_plane_ids())
    for slot_id in soc2_trust_services_catalog.SURFACE_SLOTS_BOUND:
        mapping = soc2_trust_services_catalog.load_slot_mapping(slot_id)
        assert mapping["slot"] in plane_ids, (
            f"slot {slot_id} plane '{mapping['slot']}' is not a real control-planes.yml plane"
        )


def test_control_plane_order_matches_the_slot_numbering() -> None:
    # Guards the crosswalk: control-planes.yml order IS the slot numbering both
    # verticals depend on.
    ordered = _plane_ids()[:6]
    assert ordered == [_SLOT_PLANE[i] for i in range(1, 7)]


# ---------------------------------------------------------------------------
# Registry admission (ADR-129) — the pack is now a first-class registry citizen
# ---------------------------------------------------------------------------


def _registry_entry() -> dict:
    reg = yaml.safe_load(_REGISTRY.read_text(encoding="utf-8"))
    matches = [a for a in reg["adapters"] if a["id"] == "soc2-trust-services-catalog"]
    assert matches, "SOC 2 pack is not registered in adapter-registry.yaml"
    return matches[0]


def test_pack_is_registered_with_the_non_federal_boundary() -> None:
    entry = _registry_entry()
    assert entry["class"] == "conformance"
    assert entry["status"] == "proposed"
    # The ADR-129 boundary value — non-federal, regime-scoped.
    assert entry["gcc-boundary"] == "commercial-general"
    # In lockstep with the module + mapping status markers.
    assert entry["status"] == soc2_trust_services_catalog.STATUS


def test_registry_status_matches_module_and_mappings() -> None:
    status = _registry_entry()["status"]
    assert status == soc2_trust_services_catalog.STATUS
    for slot_id in soc2_trust_services_catalog.SURFACE_SLOTS_BOUND:
        assert soc2_trust_services_catalog.load_slot_mapping(slot_id)["status"] == status
