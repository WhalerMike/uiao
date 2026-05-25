"""Tests for the Model C policy-targeting consumer + Entra adapter (ADR-084)."""

from __future__ import annotations

import pytest

from uiao.adapters.entra_policy_targeting import EntraPolicyTargetAdapter
from uiao.modernization.orgtree.policy_targeting import (
    PolicyTargetLibrary,
    PolicyTargetPlanner,
)
from uiao.modernization.orgtree.rule_renderer import RuleRenderError
from uiao.modernization.orgtree.types import (
    CompositionSpec,
    FacetPredicate,
    PolicyTargetSnapshot,
)


def _starter_specs():
    return [
        (
            "CA-Privileged-Cleared-MFA",
            "ca-policy-mfa-strong",
            "ca",
            CompositionSpec(
                predicates=(
                    FacetPredicate("account_type", "-eq", "Privileged"),
                    FacetPredicate("clearance_level", "-in", ["Secret", "TopSecret", "TS_SCI"]),
                )
            ),
            "Stronger MFA on privileged cleared accounts",
        ),
        (
            "AzPolicy-Executive-Resource-Tags",
            "az-policy-exec-tag-enforce",
            "azure_policy",
            CompositionSpec(predicates=(FacetPredicate("classification", "-eq", "Executive"),)),
            "Enforce executive-tier resource tags",
        ),
    ]


def test_library_renders_every_spec(codebook_model_c):
    lib = PolicyTargetLibrary.from_specs(codebook_model_c, _starter_specs())
    assert lib.names == {"CA-Privileged-Cleared-MFA", "AzPolicy-Executive-Resource-Tags"}
    for t in lib.targets.values():
        assert t.rule.startswith("(")


def test_library_catches_value_drift(codebook_model_c):
    bad = [
        (
            "CA-Bogus",
            "id",
            "ca",
            CompositionSpec(predicates=(FacetPredicate("region", "-eq", "MARS"),)),
            "Mars only",
        ),
    ]
    with pytest.raises(RuleRenderError):
        PolicyTargetLibrary.from_specs(codebook_model_c, bad)


def test_library_rejects_unknown_transport(codebook_model_c):
    spec = CompositionSpec(predicates=(FacetPredicate("region", "-eq", "NCR"),))
    with pytest.raises(ValueError, match="Unsupported transport"):
        PolicyTargetLibrary.from_specs(
            codebook_model_c,
            [("CA-X", "id", "bogus_transport", spec, "x")],
        )


def test_library_rejects_duplicate_names(codebook_model_c):
    spec = CompositionSpec(predicates=(FacetPredicate("region", "-eq", "NCR"),))
    with pytest.raises(ValueError, match="Duplicate"):
        PolicyTargetLibrary.from_specs(
            codebook_model_c,
            [
                ("CA-Dup", "id", "ca", spec, "first"),
                ("CA-Dup", "id", "ca", spec, "second"),
            ],
        )


def test_by_transport_filters(codebook_model_c):
    lib = PolicyTargetLibrary.from_specs(codebook_model_c, _starter_specs())
    ca_only = lib.by_transport("ca")
    assert len(ca_only) == 1
    assert ca_only[0].assignment_name == "CA-Privileged-Cleared-MFA"


def test_planner_emits_create_for_missing_assignment(codebook_model_c):
    lib = PolicyTargetLibrary.from_specs(codebook_model_c, _starter_specs())
    planner = PolicyTargetPlanner(lib)
    ops = planner.plan([])
    assert len(ops) == 2
    assert all(o.op == "create" for o in ops)


def test_planner_emits_update_on_scope_drift(codebook_model_c):
    lib = PolicyTargetLibrary.from_specs(codebook_model_c, _starter_specs())
    planner = PolicyTargetPlanner(lib)
    observed = [
        PolicyTargetSnapshot(
            assignment_id="assignment::CA-Privileged-Cleared-MFA",
            policy_definition_id="ca-policy-mfa-strong",
            scope_rule="STALE-SCOPE",
        ),
        PolicyTargetSnapshot(
            assignment_id="assignment::AzPolicy-Executive-Resource-Tags",
            policy_definition_id="az-policy-exec-tag-enforce",
            scope_rule=lib.get("AzPolicy-Executive-Resource-Tags").rule,
        ),
    ]
    ops = planner.plan(observed)
    assert len(ops) == 1
    assert ops[0].op == "update"


def test_planner_emits_rebind_on_definition_drift(codebook_model_c):
    """If the scope matches but the policy_definition_id is wrong → rebind (governance review)."""
    lib = PolicyTargetLibrary.from_specs(codebook_model_c, _starter_specs())
    planner = PolicyTargetPlanner(lib)
    observed = [
        PolicyTargetSnapshot(
            assignment_id="assignment::CA-Privileged-Cleared-MFA",
            policy_definition_id="WRONG-DEFINITION-ID",
            scope_rule=lib.get("CA-Privileged-Cleared-MFA").rule,
        ),
        PolicyTargetSnapshot(
            assignment_id="assignment::AzPolicy-Executive-Resource-Tags",
            policy_definition_id="az-policy-exec-tag-enforce",
            scope_rule=lib.get("AzPolicy-Executive-Resource-Tags").rule,
        ),
    ]
    ops = planner.plan(observed)
    assert len(ops) == 1
    assert ops[0].op == "rebind"


def test_adapter_dry_run_skips(codebook_model_c):
    lib = PolicyTargetLibrary.from_specs(codebook_model_c, _starter_specs())
    adapter = EntraPolicyTargetAdapter(lib)
    ops = adapter.plan([])
    result = adapter.apply(ops, dry_run=True)
    assert result.sent_count == 0


def test_adapter_dispatches_create_with_correct_route(codebook_model_c):
    lib = PolicyTargetLibrary.from_specs(codebook_model_c, _starter_specs())
    recorded = []
    adapter = EntraPolicyTargetAdapter(lib, transport=lambda m, p, b: (recorded.append((m, p, b)), {})[1])
    ops = adapter.plan([])
    result = adapter.apply(ops, dry_run=False)
    assert result.sent_count == 2
    paths = [p for _, p, _ in recorded]
    assert "/identity/conditionalAccess/policies" in paths
    assert "/providers/Microsoft.Authorization/policyAssignments" in paths


def test_adapter_skips_rebind_even_when_dry_run_false(codebook_model_c):
    """Rebind is in governance_review_ops."""
    lib = PolicyTargetLibrary.from_specs(codebook_model_c, _starter_specs())
    adapter = EntraPolicyTargetAdapter(lib, transport=lambda *a: {})
    observed = [
        PolicyTargetSnapshot(
            assignment_id="assignment::CA-Privileged-Cleared-MFA",
            policy_definition_id="WRONG",
            scope_rule=lib.get("CA-Privileged-Cleared-MFA").rule,
        ),
        PolicyTargetSnapshot(
            assignment_id="assignment::AzPolicy-Executive-Resource-Tags",
            policy_definition_id="az-policy-exec-tag-enforce",
            scope_rule=lib.get("AzPolicy-Executive-Resource-Tags").rule,
        ),
    ]
    ops = adapter.plan(observed)
    result = adapter.apply(ops, dry_run=False)
    assert any(op.op == "rebind" for op in result.skipped)
