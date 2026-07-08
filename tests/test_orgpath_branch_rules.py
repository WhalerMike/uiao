"""Tests for the ADR-127 branch (subtree-prefix) rules in the canon libraries.

The first real consumers of the inheritance layer: dynamic groups and
policy targets whose composition prefix-matches the derived OrgPath on
``extensionAttribute15``. The rule renderer is the enforcement point for
the trailing-delimiter contract — an unterminated prefix fails the whole
library load, so a collision-prone rule can never reach Entra.
"""

from __future__ import annotations

import pytest

from uiao.modernization.orgtree.codebook import load_codebook
from uiao.modernization.orgtree.dynamic_groups import load_dynamic_group_library
from uiao.modernization.orgtree.policy_targeting import load_policy_target_library
from uiao.modernization.orgtree.rule_renderer import RuleRenderError, render_rule
from uiao.modernization.orgtree.types import CompositionSpec, FacetPredicate


@pytest.fixture(scope="module")
def codebook():
    return load_codebook()


# ---------------------------------------------------------------------------
# Renderer: -startsWith on the derived facet
# ---------------------------------------------------------------------------


def test_renderer_emits_branch_rule_with_terminated_prefix(codebook) -> None:
    spec = CompositionSpec(
        predicates=(FacetPredicate(facet="org_path", op="-startsWith", value="Region=NCR|Department=IT|"),),
    )
    rule = render_rule(codebook, spec)
    assert rule == (
        '(user.onPremisesExtensionAttributes.extensionAttribute15 -startsWith "Region=NCR|Department=IT|")'
    )


def test_renderer_rejects_unterminated_branch_prefix(codebook) -> None:
    spec = CompositionSpec(
        predicates=(FacetPredicate(facet="org_path", op="-startsWith", value="Region=NCR|Department=IT"),),
    )
    with pytest.raises(RuleRenderError, match="trailing"):
        render_rule(codebook, spec)


def test_renderer_rejects_empty_branch_prefix(codebook) -> None:
    spec = CompositionSpec(
        predicates=(FacetPredicate(facet="org_path", op="-startsWith", value=""),),
    )
    with pytest.raises(RuleRenderError, match="trailing"):
        render_rule(codebook, spec)


def test_renderer_error_names_the_collision_and_the_fix(codebook) -> None:
    spec = CompositionSpec(
        predicates=(FacetPredicate(facet="org_path", op="-startsWith", value="Division=East"),),
    )
    with pytest.raises(RuleRenderError, match="Get-OrgPathPrefix"):
        render_rule(codebook, spec)


def test_branch_predicate_composes_with_facet_predicates(codebook) -> None:
    # Branch prefix AND a governance facet — the two layers in one rule.
    spec = CompositionSpec(
        predicates=(
            FacetPredicate(facet="org_path", op="-startsWith", value="Region=NCR|"),
            FacetPredicate(facet="account_type", op="-eq", value="Privileged"),
        ),
    )
    rule = render_rule(codebook, spec)
    assert '-startsWith "Region=NCR|"' in rule
    assert '-eq "Privileged"' in rule
    assert " and " in rule


# ---------------------------------------------------------------------------
# Canon libraries: the shipped branch entries
# ---------------------------------------------------------------------------


def test_canon_library_ships_branch_groups(codebook) -> None:
    lib = load_dynamic_group_library(codebook)
    branch = lib.by_category("Branch")
    assert {g.name for g in branch} == {"OrgTree-Branch-NCR-Users", "OrgTree-Branch-NCR-IT-Users"}
    for group in branch:
        # Every branch rule prefix carries the trailing delimiter.
        assert group.rule.rstrip('")').endswith("|"), group.rule
        assert "extensionAttribute15 -startsWith" in group.rule


def test_canon_branch_group_rule_is_exact(codebook) -> None:
    lib = load_dynamic_group_library(codebook)
    group = lib.get("OrgTree-Branch-NCR-IT-Users")
    assert group.rule == (
        '(user.onPremisesExtensionAttributes.extensionAttribute15 -startsWith "Region=NCR|Department=IT|")'
    )


def test_canon_policy_targets_ship_branch_assignment(codebook) -> None:
    lib = load_policy_target_library(codebook)
    target = lib.targets["Intune-NCR-IT-Branch-Baseline"]
    assert target.transport == "intune"
    predicates = target.composition.predicates
    assert len(predicates) == 1
    assert predicates[0].facet == "org_path"
    assert predicates[0].op == "-startsWith"
    assert predicates[0].value == "Region=NCR|Department=IT|"
