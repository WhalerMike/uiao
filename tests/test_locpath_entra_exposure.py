"""Tests for the LocPath Entra exposure planners (ADR-102 §D6 phase 4).

Covers: site-scoped group and Administrative Unit derivation from the
governed assignment plan; both membership modes (assigned — no
attribute storage, per ADR-102 §D5 — and dynamic-rule against a
caller-supplied locator); Graph body rendering; and the fail-closed
identity-resolution contract.
"""

from __future__ import annotations

import pytest

from uiao.adapters.modernization.hrit.inventory import HRRecord
from uiao.modernization.locpath import (
    LocPathAssignmentPlan,
    assign_locpaths,
    plan_locpath_admin_units,
    plan_locpath_site_groups,
)
from uiao.modernization.locpath.entra_exposure import LocPathExposureError

LOCATOR = "user.onPremisesExtensionAttributes.extensionAttribute11"


def _record(employee_id: str, location_code: str) -> HRRecord:
    return HRRecord(
        employee_id=employee_id,
        first_name="Jordan",
        last_name="Example",
        department="Finance",
        hire_date="2024-01-08",
        worker_type="FullTimeEmployee",
        location_code=location_code,
        country="US",
        employment_status="Active",
        extracted_at="2026-06-11T00:00:00Z",
    )


def _plan(*pairs: tuple[str, str]) -> LocPathAssignmentPlan:
    return assign_locpaths([_record(emp, code) for emp, code in pairs])


# ---------------------------------------------------------------------------
# Group planning
# ---------------------------------------------------------------------------


def test_one_group_per_assigned_site_with_prefix_membership() -> None:
    plan = _plan(("E-1", "HQ"), ("E-2", "HQ-B3"), ("E-3", "HQ-B3-210"))
    (group,) = plan_locpath_site_groups(plan)
    assert group.name == "LocPath-Site-ANNAPOLIS-HQ-Users"
    assert group.loc_path == "/USA/MD/ANNAPOLIS-HQ"
    # Site-level, building-level, and space-level assignments all roll up.
    assert group.member_employee_ids == ("E-1", "E-2", "E-3")
    assert group.membership_rule is None  # no locator → assigned membership


def test_sites_without_assignments_produce_no_groups() -> None:
    plan = _plan()
    assert plan_locpath_site_groups(plan) == ()


def test_explicit_prefix_must_be_registered() -> None:
    plan = _plan(("E-1", "HQ"))
    with pytest.raises(LocPathExposureError, match="not in location registry"):
        plan_locpath_site_groups(plan, prefixes=["/USA/MD/NOWHERE"])


def test_explicit_deeper_prefix_scopes_membership() -> None:
    plan = _plan(("E-1", "HQ"), ("E-2", "HQ-B3"))
    (group,) = plan_locpath_site_groups(plan, prefixes=["/USA/MD/ANNAPOLIS-HQ/BLDG-3"])
    assert group.member_employee_ids == ("E-2",)  # site-level E-1 is outside BLDG-3


def test_dynamic_rule_rendered_against_supplied_locator() -> None:
    plan = _plan(("E-1", "HQ"))
    (group,) = plan_locpath_site_groups(plan, locator=LOCATOR)
    assert group.membership_rule == f'({LOCATOR} -startsWith "/USA/MD/ANNAPOLIS-HQ")'


def test_blank_locator_rejected() -> None:
    plan = _plan(("E-1", "HQ"))
    with pytest.raises(LocPathExposureError, match="non-empty"):
        plan_locpath_site_groups(plan, locator="   ")


# ---------------------------------------------------------------------------
# Graph bodies — groups
# ---------------------------------------------------------------------------


def test_dynamic_group_graph_body() -> None:
    plan = _plan(("E-1", "HQ"))
    (group,) = plan_locpath_site_groups(plan, locator=LOCATOR)
    body = group.to_graph_body()
    assert body["groupTypes"] == ["DynamicMembership"]
    assert body["membershipRule"] == group.membership_rule
    assert body["securityEnabled"] is True


def test_assigned_group_graph_body_binds_resolved_members() -> None:
    plan = _plan(("E-1", "HQ"), ("E-2", "HQ-B3"))
    (group,) = plan_locpath_site_groups(plan)
    body = group.to_graph_body(object_ids={"E-1": "0000-aaaa", "E-2": "0000-bbbb"})
    assert body["groupTypes"] == []
    assert body["members@odata.bind"] == [
        "https://graph.microsoft.com/v1.0/directoryObjects/0000-aaaa",
        "https://graph.microsoft.com/v1.0/directoryObjects/0000-bbbb",
    ]


def test_assigned_group_fails_closed_on_unresolved_identity() -> None:
    plan = _plan(("E-1", "HQ"), ("E-2", "HQ-B3"))
    (group,) = plan_locpath_site_groups(plan)
    with pytest.raises(LocPathExposureError, match="E-2"):
        group.to_graph_body(object_ids={"E-1": "0000-aaaa"})
    with pytest.raises(LocPathExposureError, match="pass object_ids"):
        group.to_graph_body()


# ---------------------------------------------------------------------------
# Administrative Units
# ---------------------------------------------------------------------------


def test_admin_unit_defaults_to_restricted_management() -> None:
    plan = _plan(("E-1", "HQ"))
    (unit,) = plan_locpath_admin_units(plan)
    assert unit.name == "AU-Site-ANNAPOLIS-HQ"
    assert unit.restricted_management is True
    body = unit.to_graph_body()
    assert body["isMemberManagementRestricted"] is True
    assert "membershipRule" not in body  # assigned mode


def test_dynamic_admin_unit_carries_rule_and_rejects_assigned_members() -> None:
    plan = _plan(("E-1", "HQ"))
    (unit,) = plan_locpath_admin_units(plan, locator=LOCATOR)
    body = unit.to_graph_body()
    assert body["membershipType"] == "Dynamic"
    assert body["membershipRule"] == f'({LOCATOR} -startsWith "/USA/MD/ANNAPOLIS-HQ")'
    with pytest.raises(LocPathExposureError, match="rule-managed"):
        unit.member_bindings({"E-1": "0000-aaaa"})


def test_assigned_admin_unit_member_bindings() -> None:
    plan = _plan(("E-1", "HQ"))
    (unit,) = plan_locpath_admin_units(plan)
    assert unit.member_bindings({"E-1": "0000-aaaa"}) == ["https://graph.microsoft.com/v1.0/directoryObjects/0000-aaaa"]
