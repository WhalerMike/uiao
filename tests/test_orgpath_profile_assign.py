"""Tests for the profile-driven OrgPath planner and the Okta/LDAP transports.

The planner (uiao.modernization.orgtree.profile_assign) turns a binding
profile + derived facet values into FacetOperation writes routed by the
profile's locators. These tests cover the happy path against the Okta and
Microsoft reference profiles, the skip rules (reserved facet, inactive
value, non-writable binding), and the priority-overflow "uncaptured" path.
The transport tests use fakes — no live Okta org or directory — to confirm
the apply convenience dispatches only `write` operations.
"""

from __future__ import annotations

import pytest

from uiao.adapters.ldap_transport import LdapTransport
from uiao.adapters.okta_transport import OktaTransport
from uiao.modernization.orgtree.binding_profiles import (
    load_binding_profile,
    load_binding_profile_from_path,
)
from uiao.modernization.orgtree.profile_assign import BindingProfilePlanner
from uiao.modernization.orgtree.types import FacetOperation

# Codebook-active values used across the planner tests.
_FACETS = {
    "region": "NCR",
    "department": "IT",
    "division": "CyberOps",
    "role": "Engineer",
    "classification": "Employee",
    "account_type": "Standard",
}

# ---------------------------------------------------------------------------
# Planner — happy path
# ---------------------------------------------------------------------------


def test_okta_plan_routes_to_profile_locators():
    planner = BindingProfilePlanner(load_binding_profile("okta"))
    ops = planner.plan_principal("user-1", _FACETS, plane="identity")
    assert {o.facet for o in ops} == set(_FACETS)
    assert all(o.op == "write" for o in ops)
    # Okta locator == facet name (custom attribute keyed by facet).
    region = next(o for o in ops if o.facet == "region")
    assert region.attribute == "region"
    assert region.metadata["locator_kind"] == "custom_attribute"
    assert region.metadata["profile"] == "okta"


def test_reference_profile_routes_to_extension_slots():
    planner = BindingProfilePlanner(load_binding_profile("microsoft-entra"))
    ops = planner.plan_principal("user-1", {"region": "NCR"}, plane="identity")
    assert ops[0].attribute == "extensionAttribute1"


def test_plan_skips_inactive_value():
    planner = BindingProfilePlanner(load_binding_profile("okta"))
    ops = planner.plan_principal("user-1", {"department": "NotARealDept"}, plane="identity")
    assert ops == []


def test_plan_many_principals_flattens():
    planner = BindingProfilePlanner(load_binding_profile("okta"))
    ops = planner.plan(
        [("user-1", {"region": "NCR"}), ("user-2", {"department": "IT"})],
        plane="identity",
    )
    assert {o.target for o in ops} == {"user-1", "user-2"}


def test_plan_rejects_undeclared_plane():
    planner = BindingProfilePlanner(load_binding_profile("okta"))
    with pytest.raises(ValueError, match="does not bind plane"):
        planner.plan_principal("user-1", _FACETS, plane="enforcement")


def test_vmware_enforcement_plane_plans_security_tags():
    planner = BindingProfilePlanner(load_binding_profile("vmware"))
    ops = planner.plan_principal("vm-1", _FACETS, plane="enforcement")
    # Enforcement plane binds the subset: department, division, role, classification, account_type.
    assert {o.facet for o in ops} == {"department", "division", "role", "classification", "account_type"}
    assert all(o.metadata["locator_kind"] == "tag" for o in ops)


# ---------------------------------------------------------------------------
# Planner — skip rules and overflow, via synthetic profiles
# ---------------------------------------------------------------------------

_READONLY_PROFILE = """\
schema_version: "1.0.0"
document_id: UIAO_193
profile_id: test-readonly
display_name: "Test read-only binding"
status: proposed
boundary: commercial
planes: [identity]
endpoint_resolution: "operator config"
facet_bindings:
  - { facet: region, locator: region, locator_kind: attribute, writable: false }
  - { facet: department, locator: department, locator_kind: attribute, writable: true }
"""

_OVERFLOW_PROFILE = """\
schema_version: "1.0.0"
document_id: UIAO_193
profile_id: test-overflow
display_name: "Test overflow binding"
status: proposed
boundary: commercial
planes: [workload]
endpoint_resolution: "operator config"
facet_bindings:
  - { facet: region, locator: region, locator_kind: tag, writable: true }
  - { facet: department, locator: department, locator_kind: tag, writable: true }
  - { facet: division, locator: division, locator_kind: tag, writable: true }
overflow:
  rule: priority
  plane: workload
  ordering: [region, department, division]
constraints:
  max_keys: 2
"""


def test_non_writable_binding_skipped(tmp_path):
    path = tmp_path / "p.yaml"
    path.write_text(_READONLY_PROFILE, encoding="utf-8")
    planner = BindingProfilePlanner(load_binding_profile_from_path(path))
    ops = planner.plan_principal("u", {"region": "NCR", "department": "IT"}, plane="identity")
    assert {o.facet for o in ops} == {"department"}  # region is writable:false


def test_priority_overflow_emits_uncaptured(tmp_path):
    path = tmp_path / "p.yaml"
    path.write_text(_OVERFLOW_PROFILE, encoding="utf-8")
    planner = BindingProfilePlanner(load_binding_profile_from_path(path))
    ops = planner.plan_principal("vm", _FACETS, plane="workload")
    writes = [o for o in ops if o.op == "write"]
    uncaptured = [o for o in ops if o.op == "uncaptured"]
    # max_keys=2 → first two by ordering captured, the third uncaptured (not dropped).
    assert {o.facet for o in writes} == {"region", "department"}
    assert {o.facet for o in uncaptured} == {"division"}
    assert uncaptured[0].metadata["reason"] == "overflow"
    assert uncaptured[0].value == "CyberOps"


# ---------------------------------------------------------------------------
# Transports — apply dispatches only writes (fakes, no network)
# ---------------------------------------------------------------------------


def test_okta_transport_apply_only_writes():
    calls: list[tuple[str, str, dict | None]] = []

    class _RecordingOkta(OktaTransport):
        def __call__(self, method, path, body=None):
            calls.append((method, path, body))
            return {}

    transport = _RecordingOkta(org_url="https://example.okta.com", api_token="t")
    ops = [
        FacetOperation(facet="region", attribute="region", op="write", value="NCR", target="u1"),
        FacetOperation(facet="division", attribute="", op="uncaptured", value="CyberOps", target="u1"),
    ]
    applied = transport.apply(ops)
    assert applied == 1
    assert calls == [("POST", "/api/v1/users/u1", {"profile": {"region": "NCR"}})]


def test_okta_transport_requires_org_url():
    with pytest.raises(ValueError, match="org_url"):
        OktaTransport(org_url="", api_token="t")


def test_ldap_transport_apply_only_writes():
    modified: list[tuple[str, str, str]] = []

    class _RecordingLdap(LdapTransport):
        def __init__(self):  # no ldap3 connection needed for the dispatch test
            pass

        def modify(self, dn, attribute, value):
            modified.append((dn, attribute, value))
            return {"result": 0}

    transport = _RecordingLdap()
    ops = [
        FacetOperation(facet="region", attribute="uiaoOrgPathRegion", op="write", value="NCR", target="cn=u1,dc=x"),
        FacetOperation(facet="division", attribute="", op="uncaptured", value="CyberOps", target="cn=u1,dc=x"),
    ]
    applied = transport.apply(ops)
    assert applied == 1
    assert modified == [("cn=u1,dc=x", "uiaoOrgPathRegion", "NCR")]
