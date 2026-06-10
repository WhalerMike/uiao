"""Tests for the OrgPath binding-profile loader (ADR-098 / UIAO_193).

Covers the happy path (all nine canonical profiles load, validate against
the JSON Schema, and cross-check against the codebook) and the failure
modes the loader must reject: unknown facets, duplicate locators,
missing planes on multi-plane profiles, overflow-ordering integrity,
composite-locator collisions, and schema violations.
"""

from __future__ import annotations

import pytest

from uiao.modernization.orgtree.binding_profiles import (
    CANONICAL_PROFILE_IDS,
    BindingProfileValidationError,
    load_all_binding_profiles,
    load_binding_profile,
    load_binding_profile_from_path,
)
from uiao.modernization.orgtree.codebook import load_codebook

# ---------------------------------------------------------------------------
# Happy path — canonical profiles
# ---------------------------------------------------------------------------


def test_all_canonical_profiles_load():
    profiles = load_all_binding_profiles()
    assert set(profiles) == set(CANONICAL_PROFILE_IDS)


def test_microsoft_entra_is_the_reference_profile():
    p = load_binding_profile("microsoft-entra")
    assert p.status == "reference"
    assert p.boundary == "gcc-moderate"
    assert set(p.planes) == {"identity", "workload"}


def test_reference_profile_matches_codebook_slot_table():
    """The microsoft-entra identity bindings ARE the ADR-078 slot table."""
    p = load_binding_profile("microsoft-entra")
    cb = load_codebook()
    for binding in p.bindings_for_plane("identity"):
        assert binding.locator == cb.facets[binding.facet].attribute, (
            f"facet '{binding.facet}': profile locator '{binding.locator}' "
            f"diverges from codebook slot '{cb.facets[binding.facet].attribute}'"
        )


def test_every_bound_facet_exists_in_codebook():
    cb = load_codebook()
    for profile in load_all_binding_profiles().values():
        for binding in profile.bindings:
            assert binding.facet in cb.facets


def test_boundary_is_moderate_or_commercial_only():
    """ADR-098 boundary scope: no high-side value may appear."""
    for profile in load_all_binding_profiles().values():
        assert profile.boundary in {"commercial", "gcc-moderate"}


def test_vmware_binds_three_planes():
    p = load_binding_profile("vmware")
    assert set(p.planes) == {"identity", "workload", "enforcement"}
    assert len(p.facets_for_plane("identity")) == 10
    enforcement = set(p.facets_for_plane("enforcement"))
    assert enforcement == {"department", "division", "role", "classification", "account_type"}


def test_okta_binds_all_named_facets_with_no_overflow():
    p = load_binding_profile("okta")
    assert len(p.bindings) == 10
    assert p.overflow is None


@pytest.mark.parametrize("profile_id", ["pingone", "keycloak", "auth0"])
def test_idp_expansion_profiles_are_pure_identity_no_overflow(profile_id):
    """ADR-099: PingOne / Keycloak / Auth0 mirror the okta shape exactly."""
    p = load_binding_profile(profile_id)
    assert p.status == "proposed"
    assert p.boundary == "commercial"
    assert set(p.planes) == {"identity"}
    assert len(p.bindings) == 10
    assert p.overflow is None
    assert all(b.locator_kind == "custom_attribute" and b.writable for b in p.bindings)
    # Locators round-trip on the facet name (snake_case), like okta.
    assert {b.facet for b in p.bindings} == {b.locator for b in p.bindings}


def test_idp_expansion_profiles_are_canonical():
    """The ADR-099 ids are registered so load_all picks them up."""
    profiles = load_all_binding_profiles()
    assert {"pingone", "keycloak", "auth0"} <= set(profiles)


def test_priority_overflow_orderings_are_bound_facets():
    for profile in load_all_binding_profiles().values():
        if profile.overflow is None or profile.overflow.rule != "priority":
            continue
        plane = profile.overflow.plane or profile.planes[0]
        plane_facets = set(profile.facets_for_plane(plane))
        assert set(profile.overflow.ordering) <= plane_facets


def test_locator_lookup():
    p = load_binding_profile("microsoft-entra")
    assert p.locator_for("region", "identity") == "extensionAttribute1"
    assert p.locator_for("region", "workload") == "region"
    assert p.locator_for("hire_date", "workload") is None


def test_unknown_profile_id_rejected():
    with pytest.raises(BindingProfileValidationError, match="unknown binding profile"):
        load_binding_profile("kubernetes")


# ---------------------------------------------------------------------------
# Failure modes — loader integrity checks
# ---------------------------------------------------------------------------

_VALID_DOC = """\
schema_version: "1.0.0"
document_id: UIAO_193
profile_id: test-profile
display_name: "Test"
status: proposed
boundary: commercial
planes: [identity]
endpoint_resolution: "operator config"
facet_bindings:
  - {{ facet: {facet}, locator: {locator}, locator_kind: attribute, writable: true }}
"""


def _write(tmp_path, text):
    path = tmp_path / "profile.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_unknown_facet_rejected(tmp_path):
    path = _write(tmp_path, _VALID_DOC.format(facet="flavor", locator="attr1"))
    with pytest.raises(BindingProfileValidationError, match="unknown facet 'flavor'"):
        load_binding_profile_from_path(path)


def test_happy_minimal_profile_loads(tmp_path):
    path = _write(tmp_path, _VALID_DOC.format(facet="region", locator="attr1"))
    profile = load_binding_profile_from_path(path)
    assert profile.locator_for("region", "identity") == "attr1"


def test_duplicate_locator_on_plane_rejected(tmp_path):
    doc = _VALID_DOC.format(facet="region", locator="attr1") + (
        "  - { facet: department, locator: attr1, locator_kind: attribute, writable: true }\n"
    )
    path = _write(tmp_path, doc)
    with pytest.raises(BindingProfileValidationError, match="locator 'attr1' used by more than one facet"):
        load_binding_profile_from_path(path)


def test_duplicate_facet_on_plane_rejected(tmp_path):
    doc = _VALID_DOC.format(facet="region", locator="attr1") + (
        "  - { facet: region, locator: attr2, locator_kind: attribute, writable: true }\n"
    )
    path = _write(tmp_path, doc)
    with pytest.raises(BindingProfileValidationError, match="bound more than once"):
        load_binding_profile_from_path(path)


def test_multi_plane_binding_without_plane_rejected(tmp_path):
    doc = _VALID_DOC.format(facet="region", locator="attr1").replace(
        "planes: [identity]", "planes: [identity, workload]"
    )
    path = _write(tmp_path, doc)
    with pytest.raises(BindingProfileValidationError, match="omits 'plane'"):
        load_binding_profile_from_path(path)


def test_binding_on_undeclared_plane_rejected(tmp_path):
    doc = _VALID_DOC.format(facet="region", locator="attr1").replace(
        "locator_kind: attribute, writable: true }",
        "locator_kind: attribute, writable: true, plane: workload }",
    )
    path = _write(tmp_path, doc)
    with pytest.raises(BindingProfileValidationError, match="does not declare"):
        load_binding_profile_from_path(path)


def test_overflow_ordering_must_name_bound_facets(tmp_path):
    doc = _VALID_DOC.format(facet="region", locator="attr1") + (
        "overflow:\n  rule: priority\n  ordering: [region, department]\n"
    )
    path = _write(tmp_path, doc)
    with pytest.raises(BindingProfileValidationError, match="not bound on plane"):
        load_binding_profile_from_path(path)


def test_composite_locator_collision_rejected(tmp_path):
    doc = _VALID_DOC.format(facet="region", locator="attr1") + (
        "overflow:\n  rule: composite-secondary\n  composite_locator: attr1\n"
    )
    path = _write(tmp_path, doc)
    with pytest.raises(BindingProfileValidationError, match="collides with a facet binding"):
        load_binding_profile_from_path(path)


def test_schema_violation_rejected(tmp_path):
    doc = _VALID_DOC.format(facet="region", locator="attr1").replace("locator_kind: attribute", "locator_kind: sticker")
    path = _write(tmp_path, doc)
    with pytest.raises(BindingProfileValidationError, match="schema validation failed"):
        load_binding_profile_from_path(path)


def test_high_side_boundary_rejected_by_schema(tmp_path):
    doc = _VALID_DOC.format(facet="region", locator="attr1").replace("boundary: commercial", "boundary: gcc-high")
    path = _write(tmp_path, doc)
    with pytest.raises(BindingProfileValidationError, match="schema validation failed"):
        load_binding_profile_from_path(path)
