"""Tests for the enforcement-projection compiler (ADR-098 / UIAO_193 phase 4).

Covers projecting facet predicates onto a binding profile's enforcement
plane (VMware/NSX), the per-vendor renderers (NSX security group + the
generic tag-membership form), and the failure modes the projector must
reject: pure-identity profiles with no enforcement plane, facets not bound
on the enforcement plane, unsupported operators, reserved facets, and
inactive values.
"""

from __future__ import annotations

import pytest

from uiao.modernization.orgtree.binding_profiles import load_binding_profile
from uiao.modernization.orgtree.enforcement_projection import (
    NSX_TAG_SCOPE,
    EnforcementProjectionError,
    EnforcementProjector,
    project_to_nsx,
    project_to_tag_match,
    to_tag_match,
)
from uiao.modernization.orgtree.types import CompositionSpec, FacetPredicate

_VMWARE = "vmware"


def _spec(*preds, combinator="and"):
    return CompositionSpec(predicates=tuple(preds), combinator=combinator)


# ---------------------------------------------------------------------------
# Projection — happy path
# ---------------------------------------------------------------------------


def test_project_resolves_enforcement_locators():
    proj = EnforcementProjector(load_binding_profile(_VMWARE))
    group = proj.project(
        _spec(
            FacetPredicate(facet="department", op="-eq", value="IT"),
            FacetPredicate(facet="classification", op="-eq", value="Contractor"),
        )
    )
    assert group.profile_id == "vmware"
    assert group.combinator == "and"
    assert {c.facet for c in group.clauses} == {"department", "classification"}
    # vmware enforcement locator == facet name (NSX security tag).
    assert all(c.locator == c.facet for c in group.clauses)


def test_to_nsx_emits_scoped_tag_criteria():
    out = project_to_nsx(
        load_binding_profile(_VMWARE),
        _spec(FacetPredicate(facet="role", op="-eq", value="Engineer")),
    )
    assert out["resource_type"] == "Group"
    assert out["expression_combinator"] == "AND"
    crit = out["expression"][0]
    assert crit["operator"] == "EQUALS"
    assert crit["value"] == [f"{NSX_TAG_SCOPE}|role|Engineer"]


def test_to_nsx_negates_ne():
    out = project_to_nsx(
        load_binding_profile(_VMWARE),
        _spec(FacetPredicate(facet="classification", op="-ne", value="Contractor")),
    )
    assert out["expression"][0]["operator"] == "NOTEQUALS"


def test_tag_match_generic_form():
    out = project_to_tag_match(
        load_binding_profile(_VMWARE),
        _spec(
            FacetPredicate(facet="department", op="-eq", value="IT"),
            FacetPredicate(facet="account_type", op="-in", value=["Privileged", "Service"]),
            combinator="or",
        ),
    )
    assert out["combinator"] == "or"
    by_tag = {m["tag"]: m for m in out["match"]}
    assert by_tag["department"]["op"] == "eq"
    assert by_tag["department"]["values"] == ["IT"]
    assert by_tag["account_type"]["op"] == "in"
    assert by_tag["account_type"]["values"] == ["Privileged", "Service"]


# ---------------------------------------------------------------------------
# Projection — failure modes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("profile_id", ["okta", "ldap", "pingone"])
def test_pure_identity_profile_has_no_enforcement_plane(profile_id):
    with pytest.raises(EnforcementProjectionError, match="does not bind an 'enforcement' plane"):
        EnforcementProjector(load_binding_profile(profile_id))


def test_facet_not_on_enforcement_plane_rejected():
    # cost_center is bound on vmware's workload plane but NOT enforcement.
    proj = EnforcementProjector(load_binding_profile(_VMWARE))
    with pytest.raises(EnforcementProjectionError, match="not bound on the 'enforcement' plane"):
        proj.project(_spec(FacetPredicate(facet="cost_center", op="-eq", value="CC-4100")))


def test_unsupported_operator_rejected():
    proj = EnforcementProjector(load_binding_profile(_VMWARE))
    with pytest.raises(EnforcementProjectionError, match="no faithful tag-membership form"):
        proj.project(_spec(FacetPredicate(facet="role", op="-startsWith", value="Eng")))


def test_inactive_value_rejected():
    proj = EnforcementProjector(load_binding_profile(_VMWARE))
    with pytest.raises(EnforcementProjectionError, match="not active for facet"):
        proj.project(_spec(FacetPredicate(facet="department", op="-eq", value="NotADept")))


def test_list_operator_requires_list_value():
    proj = EnforcementProjector(load_binding_profile(_VMWARE))
    with pytest.raises(EnforcementProjectionError, match="requires a list value"):
        proj.project(_spec(FacetPredicate(facet="department", op="-in", value="IT")))


def test_empty_spec_rejected():
    proj = EnforcementProjector(load_binding_profile(_VMWARE))
    with pytest.raises(EnforcementProjectionError, match="at least one predicate"):
        proj.project(CompositionSpec(predicates=()))


def test_bad_combinator_rejected():
    proj = EnforcementProjector(load_binding_profile(_VMWARE))
    with pytest.raises(EnforcementProjectionError, match="Unsupported combinator"):
        proj.project(_spec(FacetPredicate(facet="role", op="-eq", value="Engineer"), combinator="xor"))


def test_to_tag_match_notin_maps_to_not_in():
    proj = EnforcementProjector(load_binding_profile(_VMWARE))
    group = proj.project(_spec(FacetPredicate(facet="division", op="-notIn", value=["GRC"])))
    assert to_tag_match(group)["match"][0]["op"] == "not_in"
