"""ADR-127 derived-path enforcement on the remaining Python surfaces.

* ``classify_identity_drift`` (governance/drift.py, DRIFT-IDENTITY): a
  stored derived OrgPath that diverges from its recomputation is a
  ``derived_divergence`` per-facet finding, with the recomputed path
  carried as the ``replacement`` (the corrective write).
* ``BindingProfilePlanner``: profiles that bind ``org_path`` get the
  recomputed path injected; caller-supplied values for the derived
  facet are always discarded.
"""

from __future__ import annotations

import pytest

from uiao.governance.drift import classify_identity_drift
from uiao.ir.models.core import ProvenanceRecord
from uiao.modernization.orgtree.binding_profiles import BindingProfile, FacetBinding
from uiao.modernization.orgtree.codebook import load_codebook
from uiao.modernization.orgtree.profile_assign import BindingProfilePlanner

PROV = ProvenanceRecord(source="test", timestamp="2026-07-08T00:00:00Z", version="1.0.0")

_FULL_PATH = "Region=NCR|Department=IT|Division=CyberOps|"


def _classify(state):
    return classify_identity_drift(
        resource_id="user-1",
        policy_ref="orgpath-facets",
        expected_state=state,
        actual_state=state,
        provenance=PROV,
        orgpath_codebook=load_codebook(),
    )


# ---------------------------------------------------------------------------
# classify_identity_drift — derived_divergence
# ---------------------------------------------------------------------------


def test_in_sync_derived_path_is_not_identity_drift() -> None:
    state = {
        "extensionAttribute1": "NCR",
        "extensionAttribute2": "IT",
        "extensionAttribute3": "CyberOps",
        "extensionAttribute15": _FULL_PATH,
    }
    assert _classify(state) is None


def test_stale_derived_path_is_derived_divergence() -> None:
    # Well-formed path (the per-facet loop reports it active) — the
    # reconciliation is the only arm that catches the stale value.
    state = {
        "extensionAttribute1": "NCR",
        "extensionAttribute2": "HR",
        "extensionAttribute15": "Region=NCR|Department=IT|",
    }
    result = _classify(state)
    assert result is not None
    assert any("recomputation" in r for r in result.delta["identity_reasons"])
    entry = next(p for p in result.delta["per_facet"] if "derived_divergence" in p)
    # `facet|slot|value|status|replacement` — replacement is the corrective write.
    assert entry.startswith("org_path|extensionAttribute15|Region=NCR|Department=IT||derived_divergence|")
    assert entry.endswith("|derived_divergence|Region=NCR|Department=HR|")


def test_unstamped_derived_path_is_derived_divergence() -> None:
    state = {"extensionAttribute1": "NCR", "extensionAttribute2": "IT"}
    result = _classify(state)
    assert result is not None
    assert any(p.startswith("org_path|") for p in result.delta["per_facet"])


def test_derived_divergence_does_not_elevate_to_unauthorized() -> None:
    # A stale derived value is a modification, not an out-of-codebook value.
    state = {
        "extensionAttribute1": "NCR",
        "extensionAttribute2": "HR",
        "extensionAttribute15": "Region=NCR|Department=IT|",
    }
    result = _classify(state)
    assert result is not None
    assert result.classification != "unauthorized"


def test_empty_hierarchy_and_empty_slot_is_clean() -> None:
    assert _classify({}) is None


# ---------------------------------------------------------------------------
# BindingProfilePlanner — org_path derivation
# ---------------------------------------------------------------------------


def _profile(*facets: str, profile_id: str = "test-profile") -> BindingProfile:
    return BindingProfile(
        profile_id=profile_id,
        display_name="Test",
        status="proposed",
        boundary="commercial",
        planes=("identity",),
        endpoint_resolution="operator config",
        bindings=tuple(
            FacetBinding(facet=f, plane="identity", locator=f, locator_kind="custom_attribute", writable=True)
            for f in facets
        ),
    )


_HIERARCHY = {"region": "NCR", "department": "IT", "division": "CyberOps"}


@pytest.fixture(scope="module")
def codebook():
    return load_codebook()


def test_profile_binding_org_path_gets_derived_value(codebook) -> None:
    planner = BindingProfilePlanner(_profile("region", "department", "division", "org_path"), codebook)
    ops = planner.plan_principal("u1", _HIERARCHY)
    derived = next(op for op in ops if op.facet == "org_path")
    assert derived.op == "write"
    assert derived.value == _FULL_PATH
    assert derived.attribute == "org_path"  # the binding's locator


def test_caller_supplied_org_path_is_discarded_and_recomputed(codebook) -> None:
    planner = BindingProfilePlanner(_profile("region", "department", "division", "org_path"), codebook)
    ops = planner.plan_principal("u1", {**_HIERARCHY, "org_path": "Region=FAKE|"})
    derived = [op for op in ops if op.facet == "org_path"]
    assert len(derived) == 1
    assert derived[0].value == _FULL_PATH


def test_unbound_profile_drops_caller_supplied_org_path(codebook) -> None:
    # No org_path binding: the hand-authored value neither writes nor
    # surfaces as an uncaptured finding — derived data is not a fact to
    # preserve.
    planner = BindingProfilePlanner(_profile("region", "department"), codebook)
    ops = planner.plan_principal("u1", {**_HIERARCHY, "org_path": "Region=FAKE|"})
    assert all(op.facet != "org_path" for op in ops)


def test_partial_assignment_without_hierarchy_does_not_write_path(codebook) -> None:
    planner = BindingProfilePlanner(_profile("clearance_level", "org_path"), codebook)
    ops = planner.plan_principal("u1", {"clearance_level": "Secret"})
    assert all(op.facet != "org_path" for op in ops)


def test_partial_hierarchy_writes_contiguous_prefix(codebook) -> None:
    planner = BindingProfilePlanner(_profile("region", "department", "org_path"), codebook)
    ops = planner.plan_principal("u1", {"region": "NCR", "department": "IT"})
    derived = next(op for op in ops if op.facet == "org_path")
    assert derived.value == "Region=NCR|Department=IT|"
