"""Tests for the boolean-composition rule renderer (ADR-084 §C3).

Per ADR-084 §C6 the renderer ships with 100% coverage before any
consumer is built on top of it. The ``codebook_model_c`` fixture
(``tests/conftest.py``) provides the canonical 10-facet Codebook.
"""

from __future__ import annotations

import pytest

from uiao.modernization.orgtree.rule_renderer import (
    RuleRenderError,
    render_predicates,
    render_rule,
)
from uiao.modernization.orgtree.types import CompositionSpec, FacetPredicate


# ---------------------------------------------------------------------------
# Happy-path: every supported composition pattern from ADR-084
# ---------------------------------------------------------------------------


def test_single_facet_eq(codebook_model_c):
    spec = CompositionSpec(predicates=(FacetPredicate("region", "-eq", "EASTUS"),))
    assert render_rule(codebook_model_c, spec) == (
        '(user.onPremisesExtensionAttributes.extensionAttribute1 -eq "EASTUS")'
    )


def test_single_facet_in_list(codebook_model_c):
    spec = CompositionSpec(predicates=(FacetPredicate("clearance_level", "-in", ["Secret", "TopSecret", "TS_SCI"]),))
    assert render_rule(codebook_model_c, spec) == (
        '(user.onPremisesExtensionAttributes.extensionAttribute9 -in ["Secret", "TopSecret", "TS_SCI"])'
    )


def test_multi_facet_and(codebook_model_c):
    spec = CompositionSpec(
        predicates=(
            FacetPredicate("department", "-eq", "IT"),
            FacetPredicate("division", "-eq", "CyberOps"),
        )
    )
    rendered = render_rule(codebook_model_c, spec)
    assert rendered == (
        '(user.onPremisesExtensionAttributes.extensionAttribute2 -eq "IT") and '
        '(user.onPremisesExtensionAttributes.extensionAttribute3 -eq "CyberOps")'
    )


def test_multi_facet_or(codebook_model_c):
    spec = CompositionSpec(
        predicates=(
            FacetPredicate("classification", "-eq", "Employee"),
            FacetPredicate("classification", "-eq", "Contractor"),
        ),
        combinator="or",
    )
    rendered = render_rule(codebook_model_c, spec)
    assert " or " in rendered
    assert rendered.count("extensionAttribute6") == 2


def test_three_facet_composition(codebook_model_c):
    """ADR-084 §C3 worked example: NCR + IT + Manager-tier roles."""
    spec = CompositionSpec(
        predicates=(
            FacetPredicate("region", "-eq", "NCR"),
            FacetPredicate("department", "-eq", "IT"),
            FacetPredicate("role", "-in", ["Manager", "Director"]),
        )
    )
    rendered = render_rule(codebook_model_c, spec)
    # Each clause is parenthesised
    assert rendered.count("(") == 3
    assert rendered.count(") and (") == 2


def test_typed_facet_allow_empty(codebook_model_c):
    """term_date allow_empty=True — empty string should render cleanly."""
    spec = CompositionSpec(predicates=(FacetPredicate("term_date", "-eq", ""),))
    assert render_rule(codebook_model_c, spec) == ('(user.onPremisesExtensionAttributes.extensionAttribute8 -eq "")')


def test_typed_facet_matching_pattern(codebook_model_c):
    """hire_date typed with ISO 8601 pattern — valid date renders cleanly."""
    spec = CompositionSpec(predicates=(FacetPredicate("hire_date", "-eq", "2024-01-15"),))
    assert "2024-01-15" in render_rule(codebook_model_c, spec)


# ---------------------------------------------------------------------------
# Error cases — every RuleRenderError branch
# ---------------------------------------------------------------------------


def test_empty_predicates_rejected(codebook_model_c):
    spec = CompositionSpec(predicates=())
    with pytest.raises(RuleRenderError, match="at least one predicate"):
        render_rule(codebook_model_c, spec)


def test_unknown_facet_rejected(codebook_model_c):
    spec = CompositionSpec(predicates=(FacetPredicate("nonexistent", "-eq", "x"),))
    with pytest.raises(RuleRenderError, match="Unknown facet 'nonexistent'"):
        render_rule(codebook_model_c, spec)


def test_unsupported_operator_rejected(codebook_model_c):
    spec = CompositionSpec(predicates=(FacetPredicate("region", "-bogus", "NCR"),))
    with pytest.raises(RuleRenderError, match="Unsupported operator '-bogus'"):
        render_rule(codebook_model_c, spec)


def test_scalar_op_with_list_value_rejected(codebook_model_c):
    spec = CompositionSpec(predicates=(FacetPredicate("region", "-eq", ["NCR", "EMEA"]),))
    with pytest.raises(RuleRenderError, match="requires a scalar"):
        render_rule(codebook_model_c, spec)


def test_list_op_with_scalar_value_rejected(codebook_model_c):
    spec = CompositionSpec(predicates=(FacetPredicate("region", "-in", "NCR"),))
    with pytest.raises(RuleRenderError, match="requires a list"):
        render_rule(codebook_model_c, spec)


def test_unknown_enum_value_rejected_as_value_drift(codebook_model_c):
    """A value not in the facet's enumeration is rejected at render time.

    Per ADR-084 §C3, this is Value Drift surfaced before the rule is
    written to Entra — preventing the engine from creating a group whose
    membership rule references an unknown enumeration value.
    """
    spec = CompositionSpec(predicates=(FacetPredicate("region", "-eq", "MARS"),))
    with pytest.raises(RuleRenderError, match="not active for facet 'region'"):
        render_rule(codebook_model_c, spec)


def test_typed_facet_format_violation_rejected(codebook_model_c):
    """hire_date typed pattern violation — Format Drift at render time."""
    spec = CompositionSpec(predicates=(FacetPredicate("hire_date", "-eq", "01/15/2024"),))
    with pytest.raises(RuleRenderError, match="not active for facet 'hire_date'"):
        render_rule(codebook_model_c, spec)


def test_typed_facet_empty_rejected_when_not_allow_empty(codebook_model_c):
    """hire_date does NOT allow_empty — empty string must be rejected."""
    spec = CompositionSpec(predicates=(FacetPredicate("hire_date", "-eq", ""),))
    with pytest.raises(RuleRenderError, match="not active for facet 'hire_date'"):
        render_rule(codebook_model_c, spec)


def test_reserved_facet_rejected(codebook_model_c):
    """Reserved facets cannot appear in rules until promoted via governed PR."""
    spec = CompositionSpec(predicates=(FacetPredicate("reserved_11", "-eq", "anything"),))
    with pytest.raises(RuleRenderError, match="reserved"):
        render_rule(codebook_model_c, spec)


def test_unsupported_combinator_rejected(codebook_model_c):
    spec = CompositionSpec(
        predicates=(FacetPredicate("region", "-eq", "NCR"),),
        combinator="xor",
    )
    with pytest.raises(RuleRenderError, match="Unsupported combinator 'xor'"):
        render_rule(codebook_model_c, spec)


def test_list_op_value_validates_each_element(codebook_model_c):
    """-in [a, b, BAD] — each element must be active in the facet."""
    spec = CompositionSpec(predicates=(FacetPredicate("clearance_level", "-in", ["Secret", "BogusLevel"]),))
    with pytest.raises(RuleRenderError, match="not active for facet 'clearance_level'"):
        render_rule(codebook_model_c, spec)


# ---------------------------------------------------------------------------
# render_predicates() — independent rendering for debug / inspection
# ---------------------------------------------------------------------------


def test_render_predicates_independent(codebook_model_c):
    rendered = render_predicates(
        codebook_model_c,
        [
            FacetPredicate("region", "-eq", "NCR"),
            FacetPredicate("department", "-eq", "IT"),
        ],
    )
    assert len(rendered) == 2
    assert all(r.startswith("(") and r.endswith(")") for r in rendered)


# ---------------------------------------------------------------------------
# Per-facet Codebook contract (ADR-084 §C1)
# ---------------------------------------------------------------------------


def test_consumer_never_parses_yaml_directly(codebook_model_c):
    """Smoke: the rendered string references slots from the in-memory Codebook.

    Per ADR-084 §C1 the renderer accepts a Codebook object — not a YAML
    path, dict, or filename. This test asserts the contract by passing a
    programmatically-constructed Codebook (the fixture) and confirming
    render succeeds.
    """
    spec = CompositionSpec(predicates=(FacetPredicate("account_type", "-eq", "Privileged"),))
    assert "extensionAttribute10" in render_rule(codebook_model_c, spec)
