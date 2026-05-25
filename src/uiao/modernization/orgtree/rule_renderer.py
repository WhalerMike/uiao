"""Boolean composition renderer for facet predicates (ADR-084 §C3).

Three Phase 5 consumers (``dynamic_groups``, ``admin_units``,
``policy_targeting``) emit Entra dynamic-membership-rule strings of the
form::

    (user.onPremisesExtensionAttributes.extensionAttribute2 -eq "IT") and
    (user.onPremisesExtensionAttributes.extensionAttribute3 -eq "CyberOps")

This module is the single source of truth for that translation: given a
``CompositionSpec`` and a ``Codebook`` (per ADR-084 §C1), resolve each
``FacetPredicate.facet`` to its slot, validate each ``value`` against
the facet's enumeration / typed pattern, and emit the canonical rule
string.

Per ADR-084 §C6 the renderer ships with 100% test coverage before any
consumer is built on top of it.
"""

from __future__ import annotations

from typing import Iterable

from .codebook import Codebook, Facet
from .types import CompositionSpec, FacetPredicate

# Operators accepted in Entra dynamic membership rules. Anything outside
# this set is rejected at render time — consumers cannot smuggle
# arbitrary PowerShell into the rule string.
_SCALAR_OPS = frozenset({"-eq", "-ne", "-ge", "-le", "-gt", "-lt", "-startsWith", "-contains", "-match"})
_LIST_OPS = frozenset({"-in", "-notIn"})
_ALL_OPS = _SCALAR_OPS | _LIST_OPS

_USER_ATTRIBUTE_PREFIX = "user.onPremisesExtensionAttributes."


class RuleRenderError(ValueError):
    """Raised when a CompositionSpec cannot be rendered against a Codebook.

    Surfaces three error classes:

    * unknown facet name (``facet`` not declared in the Codebook);
    * unsupported operator (``op`` not in the accepted set);
    * value validation failure (predicate value not active for the
      facet — Value Drift surfaced at render time, before the rule is
      written to Entra).
    """


def render_rule(codebook: Codebook, spec: CompositionSpec) -> str:
    """Render a CompositionSpec into an Entra dynamic-membership-rule string.

    Parameters
    ----------
    codebook
        The active per-facet codebook. Each predicate's ``facet`` must
        resolve via :py:meth:`Codebook.facet`; each predicate's
        ``value`` must be active for that facet (per
        :py:meth:`Facet.is_active`).
    spec
        The boolean composition.

    Returns
    -------
    str
        The rendered rule string, with parenthesised clauses joined by
        the spec's combinator (``" and "`` or ``" or "``).

    Raises
    ------
    RuleRenderError
        On unknown facet, unsupported operator, or non-active value.
    """
    if not spec.predicates:
        raise RuleRenderError("CompositionSpec must declare at least one predicate")
    if spec.combinator not in ("and", "or"):
        raise RuleRenderError(f"Unsupported combinator '{spec.combinator}'; expected 'and' or 'or'")
    clauses = [_render_predicate(codebook, p) for p in spec.predicates]
    joiner = f" {spec.combinator} "
    return joiner.join(clauses)


def render_predicates(codebook: Codebook, predicates: Iterable[FacetPredicate]) -> list[str]:
    """Render each predicate independently — used for debug / inspection."""
    return [_render_predicate(codebook, p) for p in predicates]


def _render_predicate(codebook: Codebook, predicate: FacetPredicate) -> str:
    facet = _resolve_facet(codebook, predicate.facet)
    _validate_operator(predicate)
    _validate_value(facet, predicate)
    attribute = f"{_USER_ATTRIBUTE_PREFIX}{facet.attribute}"
    rendered_value = _render_value(predicate)
    return f"({attribute} {predicate.op} {rendered_value})"


def _resolve_facet(codebook: Codebook, name: str) -> Facet:
    try:
        return codebook.facet(name)
    except KeyError as exc:
        raise RuleRenderError(f"Unknown facet '{name}' — not declared in the codebook") from exc


def _validate_operator(predicate: FacetPredicate) -> None:
    if predicate.op not in _ALL_OPS:
        raise RuleRenderError(
            f"Unsupported operator '{predicate.op}' for facet '{predicate.facet}'; accepted: {sorted(_ALL_OPS)}"
        )
    if predicate.op in _LIST_OPS and not isinstance(predicate.value, list):
        raise RuleRenderError(f"Operator '{predicate.op}' on facet '{predicate.facet}' requires a list value")
    if predicate.op in _SCALAR_OPS and isinstance(predicate.value, list):
        raise RuleRenderError(f"Operator '{predicate.op}' on facet '{predicate.facet}' requires a scalar value")


def _validate_value(facet: Facet, predicate: FacetPredicate) -> None:
    # Reserved facets cannot appear in rules until promoted via governed PR.
    if facet.kind == "reserved":
        raise RuleRenderError(
            f"Facet '{facet.name}' is reserved; cannot render rules against it. "
            "Promote the facet via governed PR per ADR-078 before rule construction."
        )
    values = predicate.value if isinstance(predicate.value, list) else [predicate.value]
    for v in values:
        # Empty string is permitted on typed facets that allow_empty (e.g.,
        # TermDate == "" for active employees).
        if v == "" and facet.kind == "typed" and facet.allow_empty:
            continue
        if not facet.is_active(v):
            raise RuleRenderError(
                f"Value '{v}' is not active for facet '{facet.name}' "
                f"(slot {facet.attribute}). "
                "Either add it to the facet's enumeration via governed PR or "
                "use a different value."
            )


def _render_value(predicate: FacetPredicate) -> str:
    if isinstance(predicate.value, list):
        items = ", ".join(f'"{v}"' for v in predicate.value)
        return f"[{items}]"
    return f'"{predicate.value}"'
