"""Tests for the Model C dynamic-group consumer + Entra adapter (ADR-084)."""

from __future__ import annotations

import pytest

from uiao.adapters.entra_dynamic_groups import EntraDynamicGroupAdapter
from uiao.modernization.orgtree.dynamic_groups import (
    DynamicGroupLibrary,
    DynamicGroupPlanner,
)
from uiao.modernization.orgtree.rule_renderer import RuleRenderError
from uiao.modernization.orgtree.types import (
    CompositionSpec,
    FacetPredicate,
    GroupSnapshot,
)


# ---------------------------------------------------------------------------
# Library construction (ADR-084 §C1, §C3)
# ---------------------------------------------------------------------------


def _starter_specs():
    return [
        (
            "OrgTree-Region-NCR-Users",
            "Region",
            CompositionSpec(predicates=(FacetPredicate("region", "-eq", "NCR"),)),
            "All NCR users",
        ),
        (
            "OrgTree-IT-CyberOps-Users",
            "Division",
            CompositionSpec(
                predicates=(
                    FacetPredicate("department", "-eq", "IT"),
                    FacetPredicate("division", "-eq", "CyberOps"),
                )
            ),
            "IT/CyberOps division members",
        ),
        (
            "OrgTree-Cleared-Secret-Plus",
            "Clearance",
            CompositionSpec(predicates=(FacetPredicate("clearance_level", "-in", ["Secret", "TopSecret", "TS_SCI"]),)),
            "All cleared personnel at Secret+",
        ),
    ]


def test_library_renders_every_spec(codebook_model_c):
    lib = DynamicGroupLibrary.from_specs(codebook_model_c, _starter_specs())
    assert lib.names == {
        "OrgTree-Region-NCR-Users",
        "OrgTree-IT-CyberOps-Users",
        "OrgTree-Cleared-Secret-Plus",
    }
    # Every spec carries the rendered rule
    for spec in lib.groups.values():
        assert spec.rule.startswith("(")


def test_library_catches_value_drift_at_load(codebook_model_c):
    """A spec referencing an unknown enum value must fail load (ADR-084 §C3)."""
    bad = [
        (
            "OrgTree-Bogus",
            "Region",
            CompositionSpec(predicates=(FacetPredicate("region", "-eq", "MARS"),)),
            "Mars users",
        ),
    ]
    with pytest.raises(RuleRenderError, match="not active for facet 'region'"):
        DynamicGroupLibrary.from_specs(codebook_model_c, bad)


def test_library_rejects_duplicate_names(codebook_model_c):
    spec = CompositionSpec(predicates=(FacetPredicate("region", "-eq", "NCR"),))
    with pytest.raises(ValueError, match="Duplicate"):
        DynamicGroupLibrary.from_specs(
            codebook_model_c,
            [
                ("OrgTree-Dup", "Region", spec, "first"),
                ("OrgTree-Dup", "Region", spec, "second"),
            ],
        )


def test_by_category_filters(codebook_model_c):
    lib = DynamicGroupLibrary.from_specs(codebook_model_c, _starter_specs())
    region_groups = lib.by_category("Region")
    assert len(region_groups) == 1
    assert region_groups[0].name == "OrgTree-Region-NCR-Users"


def test_graph_body_shape(codebook_model_c):
    lib = DynamicGroupLibrary.from_specs(codebook_model_c, _starter_specs())
    body = lib.get("OrgTree-Region-NCR-Users").to_graph_body()
    assert body["displayName"] == "OrgTree-Region-NCR-Users"
    assert body["groupTypes"] == ["DynamicMembership"]
    assert body["membershipRuleProcessingState"] == "On"
    assert body["securityEnabled"] is True
    assert body["mailEnabled"] is False
    assert body["membershipRule"].startswith("(user.onPremisesExtensionAttributes")


def test_graph_body_m365_variant(codebook_model_c):
    lib = DynamicGroupLibrary.from_specs(codebook_model_c, _starter_specs(), group_type="M365")
    body = lib.get("OrgTree-Region-NCR-Users").to_graph_body()
    assert "Unified" in body["groupTypes"]
    assert body["mailEnabled"] is True


# ---------------------------------------------------------------------------
# Planner — per-facet operations (ADR-084 §C2)
# ---------------------------------------------------------------------------


def test_planner_emits_create_for_missing_group(codebook_model_c):
    lib = DynamicGroupLibrary.from_specs(codebook_model_c, _starter_specs())
    planner = DynamicGroupPlanner(lib)
    ops = planner.plan([])  # no observed groups
    assert len(ops) == 3
    assert all(o.op == "create" for o in ops)
    assert all("graph_body" in o.metadata for o in ops)


def test_planner_emits_update_on_rule_drift(codebook_model_c):
    lib = DynamicGroupLibrary.from_specs(codebook_model_c, _starter_specs())
    planner = DynamicGroupPlanner(lib)
    observed = [
        GroupSnapshot(
            object_id="g-1",
            name="OrgTree-Region-NCR-Users",
            membership_rule='(user.department -eq "Stale")',
            group_type="Security",
        ),
        GroupSnapshot(
            object_id="g-2",
            name="OrgTree-IT-CyberOps-Users",
            membership_rule=lib.get("OrgTree-IT-CyberOps-Users").rule,
            group_type="Security",
        ),
        GroupSnapshot(
            object_id="g-3",
            name="OrgTree-Cleared-Secret-Plus",
            membership_rule=lib.get("OrgTree-Cleared-Secret-Plus").rule,
            group_type="Security",
        ),
    ]
    ops = planner.plan(observed)
    assert len(ops) == 1
    assert ops[0].op == "update"
    assert ops[0].target == "OrgTree-Region-NCR-Users"
    assert ops[0].metadata["object_id"] == "g-1"


def test_planner_emits_phantom_for_unknown_orgtree_group(codebook_model_c):
    lib = DynamicGroupLibrary.from_specs(codebook_model_c, _starter_specs())
    planner = DynamicGroupPlanner(lib)
    observed = [
        GroupSnapshot(
            object_id="g-rogue",
            name="OrgTree-Rogue-Department",
            membership_rule='(user.department -eq "Mystery")',
            group_type="Security",
        ),
    ] + [
        GroupSnapshot(
            object_id=f"g-{i}",
            name=name,
            membership_rule=lib.get(name).rule,
            group_type="Security",
        )
        for i, name in enumerate(lib.names)
    ]
    ops = planner.plan(observed)
    phantoms = [o for o in ops if o.op == "phantom"]
    assert len(phantoms) == 1
    assert phantoms[0].target == "OrgTree-Rogue-Department"


def test_planner_ignores_non_orgtree_groups(codebook_model_c):
    """Tenant groups without OrgTree- prefix aren't UIAO's concern."""
    lib = DynamicGroupLibrary.from_specs(codebook_model_c, _starter_specs())
    planner = DynamicGroupPlanner(lib)
    observed = [
        GroupSnapshot(
            object_id=f"g-{i}",
            name=name,
            membership_rule=lib.get(name).rule,
            group_type="Security",
        )
        for i, name in enumerate(lib.names)
    ] + [
        GroupSnapshot(
            object_id="g-app",
            name="App-Engineering-Members",
            membership_rule='(user.department -eq "Engineering")',
            group_type="Security",
        ),
    ]
    ops = planner.plan(observed)
    # No ops for the App- group; library groups all match
    assert ops == []


# ---------------------------------------------------------------------------
# Adapter — apply() with transport seam (ADR-084 §C4)
# ---------------------------------------------------------------------------


def test_adapter_dry_run_skips_everything(codebook_model_c):
    lib = DynamicGroupLibrary.from_specs(codebook_model_c, _starter_specs())
    adapter = EntraDynamicGroupAdapter(lib)
    ops = adapter.plan([])
    result = adapter.apply(ops, dry_run=True)
    assert result.dry_run is True
    assert result.sent_count == 0
    assert result.skipped_count == len(ops)


def test_adapter_dispatches_create_on_real_apply(codebook_model_c):
    lib = DynamicGroupLibrary.from_specs(codebook_model_c, _starter_specs())
    recorded = []

    def recorder(method, path, body):
        recorded.append((method, path, body))
        return {"id": "new-id"}

    adapter = EntraDynamicGroupAdapter(lib, transport=recorder)
    ops = adapter.plan([])
    result = adapter.apply(ops, dry_run=False)
    assert result.sent_count == 3
    assert all(method == "POST" and path == "/groups" for method, path, _ in recorded)


def test_adapter_dispatches_update_on_rule_drift(codebook_model_c):
    lib = DynamicGroupLibrary.from_specs(codebook_model_c, _starter_specs())
    recorded = []

    def recorder(method, path, body):
        recorded.append((method, path, body))
        return {}

    adapter = EntraDynamicGroupAdapter(lib, transport=recorder)
    observed = [
        GroupSnapshot(
            object_id="g-1",
            name="OrgTree-Region-NCR-Users",
            membership_rule="STALE",
            group_type="Security",
        ),
        # Other two groups match — no op for them
        GroupSnapshot(
            object_id="g-2",
            name="OrgTree-IT-CyberOps-Users",
            membership_rule=lib.get("OrgTree-IT-CyberOps-Users").rule,
            group_type="Security",
        ),
        GroupSnapshot(
            object_id="g-3",
            name="OrgTree-Cleared-Secret-Plus",
            membership_rule=lib.get("OrgTree-Cleared-Secret-Plus").rule,
            group_type="Security",
        ),
    ]
    ops = adapter.plan(observed)
    result = adapter.apply(ops, dry_run=False)
    assert result.sent_count == 1
    method, path, body = recorded[0]
    assert method == "PATCH"
    assert path == "/groups/g-1"
    assert "membershipRule" in body


def test_adapter_skips_phantoms_even_when_dry_run_false(codebook_model_c):
    """Phantom is in governance_review_ops — never auto-remediated."""
    lib = DynamicGroupLibrary.from_specs(codebook_model_c, _starter_specs())
    recorded = []
    adapter = EntraDynamicGroupAdapter(lib, transport=lambda *a: recorded.append(a) or {})
    observed = [
        GroupSnapshot(
            object_id="g-rogue",
            name="OrgTree-Rogue",
            membership_rule="x",
            group_type="Security",
        ),
    ] + [
        GroupSnapshot(
            object_id=f"g-{i}",
            name=n,
            membership_rule=lib.get(n).rule,
            group_type="Security",
        )
        for i, n in enumerate(lib.names)
    ]
    ops = adapter.plan(observed)
    result = adapter.apply(ops, dry_run=False)
    # The one phantom op was skipped despite dry_run=False
    assert any(op.op == "phantom" for op in result.skipped)


def test_adapter_governance_review_set_includes_phantom(codebook_model_c):
    lib = DynamicGroupLibrary.from_specs(codebook_model_c, _starter_specs())
    adapter = EntraDynamicGroupAdapter(lib)
    assert "phantom" in adapter.governance_review_ops


def test_adapter_no_transport_records_error(codebook_model_c):
    lib = DynamicGroupLibrary.from_specs(codebook_model_c, _starter_specs())
    adapter = EntraDynamicGroupAdapter(lib, transport=None)
    ops = adapter.plan([])
    result = adapter.apply(ops, dry_run=False)
    assert result.error_count == len(ops)
