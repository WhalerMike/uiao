"""Tests for the Model C AU consumer + Entra adapter (ADR-084)."""

from __future__ import annotations

import pytest

from uiao.adapters.entra_admin_units import EntraAdminUnitAdapter
from uiao.modernization.orgtree.admin_units import (
    AdminUnitPlanner,
    AdminUnitRegistry,
)
from uiao.modernization.orgtree.rule_renderer import RuleRenderError
from uiao.modernization.orgtree.types import (
    AdminUnitSnapshot,
    CompositionSpec,
    FacetPredicate,
)


def _starter_specs():
    return [
        (
            "AU-Department-IT",
            CompositionSpec(predicates=(FacetPredicate("department", "-eq", "IT"),)),
            "IT department AU",
            (("User Administrator", "IT Division Lead"),),
        ),
        (
            "AU-NCR-Privileged",
            CompositionSpec(
                predicates=(
                    FacetPredicate("region", "-eq", "NCR"),
                    FacetPredicate("account_type", "-eq", "Privileged"),
                )
            ),
            "NCR privileged accounts",
            (("Authentication Administrator", "NCR PAM Steward"),),
        ),
    ]


def test_registry_renders_every_spec(codebook_model_c):
    reg = AdminUnitRegistry.from_specs(codebook_model_c, _starter_specs())
    assert reg.names == {"AU-Department-IT", "AU-NCR-Privileged"}
    for spec in reg.units.values():
        assert spec.rule.startswith("(")
        assert spec.restricted_management is True


def test_registry_catches_value_drift(codebook_model_c):
    bad = [
        (
            "AU-Bogus",
            CompositionSpec(predicates=(FacetPredicate("region", "-eq", "MARS"),)),
            "Mars AU",
            (),
        ),
    ]
    with pytest.raises(RuleRenderError):
        AdminUnitRegistry.from_specs(codebook_model_c, bad)


def test_registry_rejects_duplicate_names(codebook_model_c):
    spec = CompositionSpec(predicates=(FacetPredicate("region", "-eq", "NCR"),))
    with pytest.raises(ValueError, match="Duplicate"):
        AdminUnitRegistry.from_specs(
            codebook_model_c,
            [
                ("AU-Dup", spec, "first", ()),
                ("AU-Dup", spec, "second", ()),
            ],
        )


def test_graph_body_includes_restricted_management(codebook_model_c):
    reg = AdminUnitRegistry.from_specs(codebook_model_c, _starter_specs())
    body = reg.get("AU-Department-IT").to_graph_body()
    assert body["isMemberManagementRestricted"] is True
    assert body["membershipType"] == "Dynamic"
    assert body["membershipRule"].startswith("(user.onPremisesExtensionAttributes")


def test_planner_emits_create_for_missing_au(codebook_model_c):
    reg = AdminUnitRegistry.from_specs(codebook_model_c, _starter_specs())
    planner = AdminUnitPlanner(reg)
    ops = planner.plan([])
    assert len(ops) == 2
    assert all(o.op == "create" for o in ops)


def test_planner_emits_update_on_rule_drift(codebook_model_c):
    reg = AdminUnitRegistry.from_specs(codebook_model_c, _starter_specs())
    planner = AdminUnitPlanner(reg)
    observed = [
        AdminUnitSnapshot(
            object_id="au-1",
            name="AU-Department-IT",
            membership_rule="STALE",
            restricted_management=True,
        ),
        AdminUnitSnapshot(
            object_id="au-2",
            name="AU-NCR-Privileged",
            membership_rule=reg.get("AU-NCR-Privileged").rule,
            restricted_management=True,
        ),
    ]
    ops = planner.plan(observed)
    assert len(ops) == 1
    assert ops[0].op == "update"
    assert "membershipRule" in ops[0].metadata["patch_body"]


def test_planner_emits_update_when_restricted_management_off(codebook_model_c):
    reg = AdminUnitRegistry.from_specs(codebook_model_c, _starter_specs())
    planner = AdminUnitPlanner(reg)
    observed = [
        AdminUnitSnapshot(
            object_id="au-1",
            name="AU-Department-IT",
            membership_rule=reg.get("AU-Department-IT").rule,
            restricted_management=False,  # drift!
        ),
        AdminUnitSnapshot(
            object_id="au-2",
            name="AU-NCR-Privileged",
            membership_rule=reg.get("AU-NCR-Privileged").rule,
            restricted_management=True,
        ),
    ]
    ops = planner.plan(observed)
    assert len(ops) == 1
    assert ops[0].metadata["patch_body"].get("isMemberManagementRestricted") is True


def test_planner_emits_phantom_for_unknown_au(codebook_model_c):
    reg = AdminUnitRegistry.from_specs(codebook_model_c, _starter_specs())
    planner = AdminUnitPlanner(reg)
    observed = [
        AdminUnitSnapshot(
            object_id="au-rogue",
            name="AU-Mystery",
            membership_rule="x",
            restricted_management=False,
        ),
    ] + [
        AdminUnitSnapshot(
            object_id=f"au-{i}",
            name=n,
            membership_rule=reg.get(n).rule,
            restricted_management=True,
        )
        for i, n in enumerate(reg.names)
    ]
    ops = planner.plan(observed)
    phantoms = [o for o in ops if o.op == "phantom"]
    assert len(phantoms) == 1
    assert phantoms[0].target == "AU-Mystery"


def test_adapter_dry_run_skips(codebook_model_c):
    reg = AdminUnitRegistry.from_specs(codebook_model_c, _starter_specs())
    adapter = EntraAdminUnitAdapter(reg)
    ops = adapter.plan([])
    result = adapter.apply(ops, dry_run=True)
    assert result.sent_count == 0


def test_adapter_dispatches_create(codebook_model_c):
    reg = AdminUnitRegistry.from_specs(codebook_model_c, _starter_specs())
    recorded = []
    adapter = EntraAdminUnitAdapter(reg, transport=lambda m, p, b: (recorded.append((m, p, b)), {})[1])
    ops = adapter.plan([])
    result = adapter.apply(ops, dry_run=False)
    assert result.sent_count == 2
    assert all(p == "/directory/administrativeUnits" for _, p, _ in recorded)


def test_adapter_skips_phantom_when_dry_run_false(codebook_model_c):
    reg = AdminUnitRegistry.from_specs(codebook_model_c, _starter_specs())
    adapter = EntraAdminUnitAdapter(reg, transport=lambda *a: {})
    observed = [
        AdminUnitSnapshot(
            object_id="x",
            name="AU-Rogue",
            membership_rule="x",
            restricted_management=False,
        ),
    ] + [
        AdminUnitSnapshot(
            object_id=f"au-{i}",
            name=n,
            membership_rule=reg.get(n).rule,
            restricted_management=True,
        )
        for i, n in enumerate(reg.names)
    ]
    ops = adapter.plan(observed)
    result = adapter.apply(ops, dry_run=False)
    assert any(op.op == "phantom" for op in result.skipped)
