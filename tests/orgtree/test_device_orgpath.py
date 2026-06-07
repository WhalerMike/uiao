"""Tests for the Model C device-plane OrgPath writer + dual-transport adapter (ADR-084)."""

from __future__ import annotations

import pytest

from uiao.adapters.entra_device_orgpath import EntraDeviceOrgPathAdapter
from uiao.modernization.orgtree.device_orgpath import (
    DeviceFacetAssignment,
    DeviceOrgPathPlanner,
)


def _entra_assignment(device_id="dev-1") -> DeviceFacetAssignment:
    return DeviceFacetAssignment(
        device_id=device_id,
        disposition="ENTRA-DEVICE",
        facet_values={
            "region": "EASTUS",
            "department": "IT",
            "division": "InfraOps",
            "role": "Engineer",
            "cost_center": "CC-BAL",
            "classification": "Employee",
            "hire_date": "2024-01-15",
            "term_date": "",  # active
            "clearance_level": "Secret",
            "account_type": "Standard",
        },
    )


def _arc_assignment(
    device_id="/subscriptions/x/resourceGroups/y/providers/Microsoft.HybridCompute/machines/server-1",
) -> DeviceFacetAssignment:
    return DeviceFacetAssignment(
        device_id=device_id,
        disposition="ARC-SERVER",
        facet_values={
            "region": "EASTUS",
            "department": "IT",
            "division": "InfraOps",
            "role": "Engineer",
            "cost_center": "CC-BAL",
            "classification": "Employee",
            "hire_date": "2024-01-15",
            "term_date": "",
            "clearance_level": "Secret",
            "account_type": "Service",
        },
    )


# ---------------------------------------------------------------------------
# Planner — dual-plane routing (ADR-038 / ADR-078)
# ---------------------------------------------------------------------------


def test_plan_entra_device_routes_to_entra_plane(codebook_model_c):
    planner = DeviceOrgPathPlanner(codebook_model_c)
    plan = planner.plan_device(_entra_assignment())
    assert plan.plane == "entra"
    assert len(plan.writes) == 10  # all 10 named facets
    assert all(op.attribute.startswith("extensionAttribute") for op in plan.writes)
    assert all(op.op == "write" for op in plan.writes)


def test_plan_arc_server_routes_to_arm_plane(codebook_model_c):
    planner = DeviceOrgPathPlanner(codebook_model_c)
    plan = planner.plan_device(_arc_assignment())
    assert plan.plane == "arm"
    assert len(plan.writes) == 10
    assert all(op.attribute.startswith("tags.") for op in plan.writes)
    # Per Model C, ARM tag names mirror facet names (PascalCase)
    tag_names = {op.attribute.removeprefix("tags.") for op in plan.writes}
    assert "Region" in tag_names
    assert "Department" in tag_names
    assert "ClearanceLevel" in tag_names  # snake_case → PascalCase


def test_plan_stay_ad_dc_skipped(codebook_model_c):
    """Domain controllers don't get OrgPath written (per ADR-038)."""
    planner = DeviceOrgPathPlanner(codebook_model_c)
    assignment = DeviceFacetAssignment(
        device_id="dc-1",
        disposition="STAY-AD-DC",
        facet_values={"region": "EASTUS"},
    )
    plan = planner.plan_device(assignment)
    assert plan.plane == "skip"
    assert plan.writes == ()


def test_plan_decommission_skipped(codebook_model_c):
    planner = DeviceOrgPathPlanner(codebook_model_c)
    assignment = DeviceFacetAssignment(
        device_id="dec-1",
        disposition="DECOMMISSION",
        facet_values={"region": "EASTUS"},
    )
    plan = planner.plan_device(assignment)
    assert plan.plane == "skip"
    assert plan.writes == ()


def test_plan_unknown_disposition_rejected(codebook_model_c):
    planner = DeviceOrgPathPlanner(codebook_model_c)
    assignment = DeviceFacetAssignment(
        device_id="x",
        disposition="MADE-UP",
        facet_values={"region": "NCR"},
    )
    with pytest.raises(ValueError, match="Unknown disposition"):
        planner.plan_device(assignment)


def test_plan_honors_injected_routing_override(codebook_model_c):
    """A deployment-supplied routing map overrides the hardcoded disposition set.

    Closes the seam where ``load_disposition_routing`` was documented as the
    override mechanism but the planner had no way to consume it.
    """
    routing = {
        "ENTRA-DEVICE": "entra",
        "ARC-SERVER": "arm",
        "STAY-AD-DC": "skip",
        # a deployment-declared disposition the hardcoded set doesn't know
        "EDGE-APPLIANCE": "arm",
    }
    planner = DeviceOrgPathPlanner(codebook_model_c, routing=routing)
    assignment = DeviceFacetAssignment(
        device_id="edge-1",
        disposition="EDGE-APPLIANCE",
        facet_values={"region": "EASTUS"},
    )
    plan = planner.plan_device(assignment)
    assert plan.plane == "arm"
    assert plan.writes[0].attribute == "tags.Region"


def test_plan_injected_routing_rejects_unlisted_disposition(codebook_model_c):
    """With a routing override, dispositions absent from it are rejected too."""
    planner = DeviceOrgPathPlanner(codebook_model_c, routing={"ENTRA-DEVICE": "entra"})
    assignment = DeviceFacetAssignment(
        device_id="x",
        disposition="ARC-SERVER",  # valid canonically, but not in the override map
        facet_values={"region": "EASTUS"},
    )
    with pytest.raises(ValueError, match="Unknown disposition"):
        planner.plan_device(assignment)


def test_plan_skips_invalid_facet_values(codebook_model_c):
    """Per-facet values failing is_active() are excluded from the write (engine surfaces them as drift on input)."""
    planner = DeviceOrgPathPlanner(codebook_model_c)
    assignment = DeviceFacetAssignment(
        device_id="dev-bad",
        disposition="ENTRA-DEVICE",
        facet_values={
            "region": "EASTUS",
            "department": "BogusDept",  # not in enumeration
            "division": "CyberOps",
        },
    )
    plan = planner.plan_device(assignment)
    # department write was excluded; only region + division survive
    written_facets = {op.facet for op in plan.writes}
    assert written_facets == {"region", "division"}


def test_plan_skips_reserved_facets(codebook_model_c):
    """Reserved facets are never written (must be promoted via governed PR first)."""
    planner = DeviceOrgPathPlanner(codebook_model_c)
    assignment = DeviceFacetAssignment(
        device_id="dev-r",
        disposition="ENTRA-DEVICE",
        facet_values={
            "region": "EASTUS",
            "reserved_11": "anything",  # reserved — must be skipped
        },
    )
    plan = planner.plan_device(assignment)
    facets_written = {op.facet for op in plan.writes}
    assert "reserved_11" not in facets_written
    assert "region" in facets_written


def test_plan_typed_facet_empty_allowed(codebook_model_c):
    """term_date allow_empty=True — empty string is a valid write."""
    planner = DeviceOrgPathPlanner(codebook_model_c)
    assignment = DeviceFacetAssignment(
        device_id="dev-active",
        disposition="ENTRA-DEVICE",
        facet_values={"term_date": ""},
    )
    plan = planner.plan_device(assignment)
    assert len(plan.writes) == 1
    assert plan.writes[0].value == ""


def test_plan_typed_facet_bad_format_skipped(codebook_model_c):
    """hire_date with non-ISO format is skipped (engine surfaces Format Drift on input)."""
    planner = DeviceOrgPathPlanner(codebook_model_c)
    assignment = DeviceFacetAssignment(
        device_id="dev-bad-date",
        disposition="ENTRA-DEVICE",
        facet_values={"hire_date": "01/15/2024"},  # US format, fails ISO regex
    )
    plan = planner.plan_device(assignment)
    assert plan.writes == ()


def test_plan_many_returns_flat_op_list(codebook_model_c):
    planner = DeviceOrgPathPlanner(codebook_model_c)
    ops = planner.plan([_entra_assignment("d1"), _arc_assignment("/x/d2")])
    # 10 entra writes + 10 arm writes = 20
    assert len(ops) == 20
    entra_ops = [o for o in ops if o.metadata["plane"] == "entra"]
    arm_ops = [o for o in ops if o.metadata["plane"] == "arm"]
    assert len(entra_ops) == 10
    assert len(arm_ops) == 10


# ---------------------------------------------------------------------------
# Dual-transport adapter (ADR-084 §C4, §C5)
# ---------------------------------------------------------------------------


def test_adapter_dry_run_skips_everything(codebook_model_c):
    planner = DeviceOrgPathPlanner(codebook_model_c)
    adapter = EntraDeviceOrgPathAdapter(planner)
    ops = adapter.plan([_entra_assignment()])
    result = adapter.apply(ops, dry_run=True)
    assert result.dry_run is True
    assert result.sent_count == 0


def test_adapter_batches_entra_writes_into_one_patch(codebook_model_c):
    planner = DeviceOrgPathPlanner(codebook_model_c)
    graph_recorded = []
    arm_recorded = []
    adapter = EntraDeviceOrgPathAdapter(
        planner,
        graph_transport=lambda m, p, b: (graph_recorded.append((m, p, b)), {})[1],
        arm_transport=lambda m, p, b: (arm_recorded.append((m, p, b)), {})[1],
    )
    ops = adapter.plan([_entra_assignment("dev-1")])
    result = adapter.apply(ops, dry_run=False)
    # All 10 facet writes for one device → ONE PATCH
    assert len(graph_recorded) == 1
    method, path, body = graph_recorded[0]
    assert method == "PATCH"
    assert path == "/devices/dev-1"
    assert "onPremisesExtensionAttributes" in body
    assert len(body["onPremisesExtensionAttributes"]) == 10
    assert result.sent_count == 10
    assert arm_recorded == []


def test_adapter_batches_arm_writes_into_one_patch(codebook_model_c):
    planner = DeviceOrgPathPlanner(codebook_model_c)
    graph_recorded = []
    arm_recorded = []
    arc_assignment = _arc_assignment("/subscriptions/x/rg/y/providers/Microsoft.HybridCompute/machines/srv-1")
    adapter = EntraDeviceOrgPathAdapter(
        planner,
        graph_transport=lambda m, p, b: (graph_recorded.append((m, p, b)), {})[1],
        arm_transport=lambda m, p, b: (arm_recorded.append((m, p, b)), {})[1],
    )
    ops = adapter.plan([arc_assignment])
    result = adapter.apply(ops, dry_run=False)
    assert len(arm_recorded) == 1
    method, path, body = arm_recorded[0]
    assert method == "PATCH"
    assert "api-version=" in path
    assert "tags" in body
    assert len(body["tags"]) == 10
    assert "Region" in body["tags"]
    assert result.sent_count == 10
    assert graph_recorded == []


def test_adapter_routes_to_both_transports_for_mixed_dispositions(codebook_model_c):
    planner = DeviceOrgPathPlanner(codebook_model_c)
    graph_recorded = []
    arm_recorded = []
    adapter = EntraDeviceOrgPathAdapter(
        planner,
        graph_transport=lambda m, p, b: (graph_recorded.append((m, p, b)), {})[1],
        arm_transport=lambda m, p, b: (arm_recorded.append((m, p, b)), {})[1],
    )
    ops = adapter.plan(
        [
            _entra_assignment("dev-1"),
            _arc_assignment("/x/srv-1"),
            _entra_assignment("dev-2"),
        ]
    )
    result = adapter.apply(ops, dry_run=False)
    # 2 entra devices → 2 Graph PATCHes
    # 1 arc server → 1 ARM PATCH
    assert len(graph_recorded) == 2
    assert len(arm_recorded) == 1
    assert result.sent_count == 30  # 3 devices × 10 facets


def test_adapter_no_transport_records_errors(codebook_model_c):
    planner = DeviceOrgPathPlanner(codebook_model_c)
    adapter = EntraDeviceOrgPathAdapter(planner, graph_transport=None, arm_transport=None)
    ops = adapter.plan([_entra_assignment()])
    result = adapter.apply(ops, dry_run=False)
    assert result.error_count == 10


def test_adapter_governance_review_ops_empty(codebook_model_c):
    """Device writes have no governance-review category."""
    planner = DeviceOrgPathPlanner(codebook_model_c)
    adapter = EntraDeviceOrgPathAdapter(planner)
    assert adapter.governance_review_ops == frozenset()
