"""Tests for the OrgPath projection subset (ADR-121).

`projected: false` keeps a facet's semantics but stops it being stamped to
a directory slot, so "attributes written per object" = the projected count
(6), not the defined count (10).
"""

from __future__ import annotations

from uiao.modernization.orgtree.codebook import Facet, load_codebook
from uiao.modernization.orgtree.device_orgpath import (
    DeviceFacetAssignment,
    DeviceOrgPathPlanner,
)

_ALL_TEN = {
    "region": "EASTUS",
    "department": "IT",
    "division": "InfraOps",
    "role": "Engineer",
    "cost_center": "CC-4100",
    "classification": "Employee",
    "hire_date": "2024-01-15",
    "term_date": "",
    "clearance_level": "Secret",
    "account_type": "Standard",
}

_PROJECTED = {"region", "department", "division", "classification", "clearance_level", "account_type"}
_NOT_PROJECTED = {"role", "cost_center", "hire_date", "term_date"}
# The ADR-127 derived org_path (slot 15) is projected too — 7 written per
# object — but it is the inheritance layer, not a governance facet.
_DERIVED = {"org_path"}


def test_canonical_codebook_projects_six_governance_facets_plus_derived_path() -> None:
    c = load_codebook()
    assert set(c.projected_facets()) == _PROJECTED | _DERIVED
    # All ten governance facets remain *defined* — projection demotes, it
    # does not delete — and the derived path is defined alongside them.
    named = {n for n, f in c.facets.items() if f.kind != "reserved"}
    assert named == _PROJECTED | _NOT_PROJECTED | _DERIVED


def test_demoted_facets_keep_semantics() -> None:
    c = load_codebook()
    # Still a real, valid facet — just not projected.
    assert c.facet("cost_center").projected is False
    assert c.facet("cost_center").is_active("CC-4100")
    assert c.facet("hire_date").projected is False
    assert c.facet("hire_date").is_active("2024-01-15")
    assert c.facet("region").projected is True


def test_facet_defaults_to_projected() -> None:
    # Backward compatibility: an in-memory facet with no flag is projected.
    f = Facet(name="x", attribute="extensionAttribute1", description="", kind="enumerated")
    assert f.projected is True


def test_device_writer_stamps_projected_facets_plus_derived_path() -> None:
    planner = DeviceOrgPathPlanner(load_codebook())
    plan = planner.plan_device(
        DeviceFacetAssignment(device_id="dev-1", disposition="ENTRA-DEVICE", facet_values=_ALL_TEN)
    )
    written = {op.facet for op in plan.writes}
    # 6 projected governance facets + the ADR-127 derived path.
    assert written == _PROJECTED | _DERIVED
    # The four demoted facets are not stamped to a slot.
    assert written.isdisjoint(_NOT_PROJECTED)
    assert len(plan.writes) == 7


def test_arc_plane_also_respects_projection() -> None:
    planner = DeviceOrgPathPlanner(load_codebook())
    arc = DeviceFacetAssignment(
        device_id="/subscriptions/x/resourceGroups/y/providers/Microsoft.HybridCompute/machines/s1",
        disposition="ARC-SERVER",
        facet_values=_ALL_TEN,
    )
    plan = planner.plan_device(arc)
    assert plan.plane == "arm"
    assert len(plan.writes) == 7
