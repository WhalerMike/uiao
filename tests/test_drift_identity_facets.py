"""Per-facet DRIFT-IDENTITY (Model C) — reintroduced post ADR-078 / ADR-084 Phase 5.

Exercises ``classify_identity_drift``'s OrgPath-validation arm, which validates
each principal facet value against a Model C ``Codebook`` (deprecated / phantom /
reserved-slot detection). Uses a programmatically-constructed Codebook fixture
per ADR-084 §C6 (no YAML), so the test is hermetic and independent of the
shipped codebook's enumeration values.
"""

from __future__ import annotations

import pytest

from uiao.governance.drift import classify_identity_drift
from uiao.ir.models.core import ProvenanceRecord
from uiao.modernization.orgtree.codebook import (
    Codebook,
    DeprecatedFacetValue,
    Facet,
    FacetValue,
)

PROV = ProvenanceRecord(source="test", timestamp="2026-06-05T00:00:00Z", version="1.0.0")


@pytest.fixture()
def codebook() -> Codebook:
    """A small Model C codebook: one enumerated facet with a deprecated value,
    one typed (date) facet, one typed-empty-allowed facet, one reserved slot."""
    region = Facet(
        name="region",
        attribute="extensionAttribute1",
        description="Geographic region",
        kind="enumerated",
        enumeration={
            "NCR": FacetValue("NCR", "National Capital Region"),
            "EASTUS": FacetValue("EASTUS", "East"),
        },
        deprecated={"EAST": DeprecatedFacetValue("EAST", "EASTUS", reason="renamed")},
    )
    hire_date = Facet(
        name="hire_date",
        attribute="extensionAttribute7",
        description="Hire date (ISO 8601)",
        kind="typed",
        value_type="date",
        value_pattern=r"^\d{4}-\d{2}-\d{2}$",
        allow_empty=False,
    )
    term_date = Facet(
        name="term_date",
        attribute="extensionAttribute8",
        description="Termination date (ISO 8601, optional)",
        kind="typed",
        value_type="date",
        value_pattern=r"^\d{4}-\d{2}-\d{2}$",
        allow_empty=True,
    )
    reserved = Facet(
        name="reserved_11",
        attribute="extensionAttribute11",
        description="Reserved",
        kind="reserved",
    )
    return Codebook(
        schema_version="2.0.0",
        document_id="UIAO_151",
        parent_canon="UIAO_007",
        model="C",
        adoption_tier_min=0,
        facets={"region": region, "hire_date": hire_date, "term_date": term_date, "reserved_11": reserved},
    )


def _classify(state, codebook=None):
    return classify_identity_drift(
        resource_id="user-1",
        policy_ref="orgpath-facets",
        expected_state=state,
        actual_state=state,
        provenance=PROV,
        orgpath_codebook=codebook,
    )


def test_all_active_facets_no_drift(codebook):
    state = {"extensionAttribute1": "NCR", "extensionAttribute7": "2020-01-15", "extensionAttribute8": ""}
    assert _classify(state, codebook) is None


def test_phantom_value_is_unauthorized(codebook):
    result = _classify({"extensionAttribute1": "ATLANTIS"}, codebook)
    assert result is not None
    assert result.drift_class == "DRIFT-IDENTITY"
    assert result.classification == "unauthorized"
    assert result.delta["per_facet"] == ["region|extensionAttribute1|ATLANTIS|phantom"]
    assert any("phantom" in r for r in result.delta["identity_reasons"])


def test_deprecated_value_carries_replacement_and_is_not_elevated(codebook):
    result = _classify({"extensionAttribute1": "EAST"}, codebook)
    assert result is not None
    assert result.drift_class == "DRIFT-IDENTITY"
    # Deprecated has a known replacement path → not elevated to unauthorized.
    assert result.classification != "unauthorized"
    assert result.delta["per_facet"] == ["region|extensionAttribute1|EAST|deprecated|EASTUS"]


def test_reserved_slot_populated_is_unauthorized(codebook):
    result = _classify({"extensionAttribute11": "leaked"}, codebook)
    assert result is not None
    assert result.classification == "unauthorized"
    assert result.delta["per_facet"] == ["reserved_11|extensionAttribute11|leaked|reserved_violation"]


def test_typed_facet_pattern_validation(codebook):
    # Valid ISO date → no drift; malformed date → phantom (fails value_pattern).
    assert _classify({"extensionAttribute7": "2020-01-15"}, codebook) is None
    bad = _classify({"extensionAttribute7": "Jan 15 2020"}, codebook)
    assert bad is not None and bad.classification == "unauthorized"
    assert bad.delta["per_facet"] == ["hire_date|extensionAttribute7|Jan 15 2020|phantom"]


def test_typed_facet_allow_empty(codebook):
    # term_date allows empty; empty hire_date is "empty" (not drift here).
    assert _classify({"extensionAttribute8": "", "extensionAttribute7": ""}, codebook) is None


def test_facet_name_key_fallback(codebook):
    # Values keyed by facet name (not slot) are also resolved.
    result = _classify({"region": "ATLANTIS"}, codebook)
    assert result is not None
    assert result.delta["per_facet"] == ["region|extensionAttribute1|ATLANTIS|phantom"]


def test_mixed_facets_emit_only_drifting(codebook):
    state = {
        "extensionAttribute1": "EAST",  # deprecated
        "extensionAttribute7": "2020-01-15",  # active
        "extensionAttribute11": "x",  # reserved violation
    }
    result = _classify(state, codebook)
    assert result is not None
    # phantom OR reserved violation present → unauthorized.
    assert result.classification == "unauthorized"
    per = set(result.delta["per_facet"])
    assert "region|extensionAttribute1|EAST|deprecated|EASTUS" in per
    assert "reserved_11|extensionAttribute11|x|reserved_violation" in per
    # active facet is not emitted into the drifting subset.
    assert not any("active" in p for p in per)


def test_no_codebook_preserves_legacy_contract(codebook):
    # With no Model C codebook, the OrgPath arm is inert (legacy Set[str] /
    # None callers): an out-of-codebook facet value alone is not drift.
    assert _classify({"extensionAttribute1": "ATLANTIS"}, None) is None


def test_bare_set_codebook_is_treated_as_no_codebook():
    # A legacy Model A Set[str] must not be probed for facets.
    assert _classify({"extensionAttribute1": "ATLANTIS"}, {"NCR", "EASTUS"}) is None


def test_sentinel_arm_still_fires_without_codebook():
    # Non-facet identity drift (sentinel field change) is unaffected.
    result = classify_identity_drift(
        resource_id="u",
        policy_ref="p",
        expected_state={"employee_id": "E1"},
        actual_state={"employee_id": "E2"},
        provenance=PROV,
    )
    assert result is not None and result.drift_class == "DRIFT-IDENTITY"
