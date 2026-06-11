"""Enforcement-projection compiler — facet predicates → native policy groups.

The cross-vendor generalization of
:func:`uiao.modernization.orgtree.rule_renderer.render_rule`. Where the
rule renderer compiles a :class:`CompositionSpec` into a *Microsoft*
dynamic-membership-rule string (the reference enforcement projection), this
module compiles the same spec — validated identically against the
codebook — into the native segmentation construct of any enforcement
surface a binding profile describes (ADR-098 / UIAO_193 Zero Trust
projection table).

The contract has two stages:

1. **Project** — :meth:`EnforcementProjector.project` resolves a
   ``CompositionSpec`` against a binding profile's ``enforcement`` plane:
   every predicate's facet must be *bound on that plane* (you cannot
   segment on a facet the enforcement surface does not carry), and every
   value must be active in the codebook (Value Drift caught before a rule
   is written). It returns a vendor-neutral :class:`EnforcementGroup`.

2. **Render** — the per-vendor renderers turn an ``EnforcementGroup`` into
   the target construct: :func:`to_nsx` (NSX security group with
   tag-membership criteria), :func:`to_tag_match` (the generic
   tag-membership form shared by Palo Alto dynamic address groups, AWS
   security-group tag conditions, and GCP secure-tag firewall scoping —
   the table's other rows differ only in field names, not in shape).

Per UIAO_193 the Microsoft row of the projection table is the rule
renderer; this module is every other row. The ``okta`` / ``ldap`` /
``pingone`` / pure-identity profiles have no ``enforcement`` plane and are
correctly rejected by :meth:`project`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from uiao.modernization.orgtree.binding_profiles import BindingProfile
from uiao.modernization.orgtree.codebook import Codebook, Facet, load_codebook
from uiao.modernization.orgtree.types import CompositionSpec, FacetPredicate

# Operators meaningful on a tag-membership enforcement surface. Tag systems
# match on presence/equality and set membership; the ordered/text operators
# the Entra rule grammar supports (-ge, -startsWith, …) have no faithful
# equivalent in a tag-membership criterion and are rejected rather than
# silently approximated.
_ENFORCEMENT_OPS = frozenset({"-eq", "-ne", "-in", "-notIn"})
_LIST_OPS = frozenset({"-in", "-notIn"})


class EnforcementProjectionError(ValueError):
    """Raised when a CompositionSpec cannot be projected onto an enforcement plane.

    Surfaces: a profile with no ``enforcement`` plane; a predicate facet not
    bound on that plane; an operator without a faithful tag-membership form;
    a reserved facet; or a value not active in the codebook.
    """


@dataclass(frozen=True)
class EnforcementClause:
    """One resolved predicate: a native locator, an operator, and value(s)."""

    facet: str
    locator: str
    op: str
    values: tuple[str, ...]


@dataclass(frozen=True)
class EnforcementGroup:
    """A vendor-neutral, resolved enforcement membership expression.

    The output of :meth:`EnforcementProjector.project` and the input to
    every per-vendor renderer. ``profile_id`` records the source profile so
    a renderer can scope tags correctly; ``combinator`` is ``"and"`` or
    ``"or"`` per the source spec.
    """

    profile_id: str
    clauses: tuple[EnforcementClause, ...]
    combinator: str


class EnforcementProjector:
    """Project facet predicates onto one binding profile's enforcement plane."""

    PLANE = "enforcement"

    def __init__(self, profile: BindingProfile, codebook: Codebook | None = None) -> None:
        if self.PLANE not in profile.planes:
            raise EnforcementProjectionError(
                f"profile '{profile.profile_id}' does not bind an '{self.PLANE}' plane "
                f"(declares {', '.join(profile.planes)}); it cannot be an enforcement target"
            )
        self.profile = profile
        self.codebook = codebook or load_codebook()
        self._enforcement_locators = {b.facet: b.locator for b in profile.bindings_for_plane(self.PLANE)}

    def project(self, spec: CompositionSpec) -> EnforcementGroup:
        """Resolve a CompositionSpec into a vendor-neutral EnforcementGroup."""
        if not spec.predicates:
            raise EnforcementProjectionError("CompositionSpec must declare at least one predicate")
        if spec.combinator not in ("and", "or"):
            raise EnforcementProjectionError(f"Unsupported combinator '{spec.combinator}'; expected 'and' or 'or'")
        clauses = tuple(self._project_predicate(p) for p in spec.predicates)
        return EnforcementGroup(
            profile_id=self.profile.profile_id,
            clauses=clauses,
            combinator=spec.combinator,
        )

    def _project_predicate(self, predicate: FacetPredicate) -> EnforcementClause:
        locator = self._enforcement_locators.get(predicate.facet)
        if locator is None:
            raise EnforcementProjectionError(
                f"facet '{predicate.facet}' is not bound on the '{self.PLANE}' plane of "
                f"profile '{self.profile.profile_id}'; cannot segment on a facet the "
                f"enforcement surface does not carry "
                f"(bound: {', '.join(sorted(self._enforcement_locators)) or 'none'})"
            )
        facet = self._resolve_facet(predicate.facet)
        self._validate_operator(predicate)
        values = self._validate_values(facet, predicate)
        return EnforcementClause(
            facet=predicate.facet,
            locator=locator,
            op=predicate.op,
            values=values,
        )

    def _resolve_facet(self, name: str) -> Facet:
        try:
            return self.codebook.facet(name)
        except KeyError as exc:
            raise EnforcementProjectionError(f"Unknown facet '{name}' — not declared in the codebook") from exc

    def _validate_operator(self, predicate: FacetPredicate) -> None:
        if predicate.op not in _ENFORCEMENT_OPS:
            raise EnforcementProjectionError(
                f"Operator '{predicate.op}' on facet '{predicate.facet}' has no faithful "
                f"tag-membership form; enforcement accepts {sorted(_ENFORCEMENT_OPS)}"
            )
        if predicate.op in _LIST_OPS and not isinstance(predicate.value, list):
            raise EnforcementProjectionError(
                f"Operator '{predicate.op}' on facet '{predicate.facet}' requires a list value"
            )
        if predicate.op not in _LIST_OPS and isinstance(predicate.value, list):
            raise EnforcementProjectionError(
                f"Operator '{predicate.op}' on facet '{predicate.facet}' requires a scalar value"
            )

    def _validate_values(self, facet: Facet, predicate: FacetPredicate) -> tuple[str, ...]:
        if facet.kind == "reserved":
            raise EnforcementProjectionError(
                f"Facet '{facet.name}' is reserved; promote it via governed PR before "
                "projecting enforcement rules against it (ADR-078)"
            )
        values = predicate.value if isinstance(predicate.value, list) else [predicate.value]
        for v in values:
            if not facet.is_active(v):
                raise EnforcementProjectionError(
                    f"Value '{v}' is not active for facet '{facet.name}'; add it via governed PR or use an active value"
                )
        return tuple(values)


# ---------------------------------------------------------------------------
# Per-vendor renderers — EnforcementGroup → native construct
# ---------------------------------------------------------------------------

#: Default NSX security-tag scope (matches the vmware profile's enforcement notes).
NSX_TAG_SCOPE = "uiao-orgpath"


def _tag_token(scope: str, locator: str, value: str) -> str:
    """A single namespaced tag token, e.g. ``uiao-orgpath|department|IT``."""
    return f"{scope}|{locator}|{value}"


def to_nsx(group: EnforcementGroup, *, scope: str = NSX_TAG_SCOPE) -> dict:
    """Render an EnforcementGroup as an NSX security group with tag-membership criteria.

    The membership criteria match scoped security tags
    (``<scope>|<locator>|<value>``) combined by the group's combinator.
    ``-ne`` / ``-notIn`` become negated criteria.
    """
    criteria = []
    for clause in group.clauses:
        negate = clause.op in ("-ne", "-notIn")
        criteria.append(
            {
                "member_type": "VirtualMachine",
                "key": "Tag",
                "operator": "NOTEQUALS" if negate else "EQUALS",
                "value": [_tag_token(scope, clause.locator, v) for v in clause.values],
            }
        )
    return {
        "resource_type": "Group",
        "display_name": f"uiao-{group.profile_id}-{'-'.join(c.facet for c in group.clauses)}",
        "expression_combinator": group.combinator.upper(),
        "expression": criteria,
    }


def to_tag_match(group: EnforcementGroup) -> dict:
    """Render the generic tag-membership form.

    Shared shape for Palo Alto dynamic address groups, AWS security-group
    tag conditions, and GCP secure-tag firewall scoping — the UIAO_193
    projection-table rows that differ from NSX only in field names, not in
    structure. Returns a normalized match expression a thin per-vendor
    adapter maps onto its API verbatim.
    """
    match = []
    for clause in group.clauses:
        match.append(
            {
                "tag": clause.locator,
                "op": "in"
                if clause.op in ("-in",)
                else "not_in"
                if clause.op in ("-notIn",)
                else ("eq" if clause.op == "-eq" else "ne"),
                "values": list(clause.values),
            }
        )
    return {
        "profile": group.profile_id,
        "combinator": group.combinator,
        "match": match,
    }


def project_to_nsx(
    profile: BindingProfile,
    spec: CompositionSpec,
    *,
    codebook: Codebook | None = None,
    scope: str = NSX_TAG_SCOPE,
) -> dict:
    """Convenience: project + render to NSX in one call."""
    return to_nsx(EnforcementProjector(profile, codebook).project(spec), scope=scope)


def project_to_tag_match(
    profile: BindingProfile,
    spec: CompositionSpec,
    *,
    codebook: Codebook | None = None,
) -> dict:
    """Convenience: project + render to the generic tag-membership form."""
    return to_tag_match(EnforcementProjector(profile, codebook).project(spec))


__all__: Sequence[str] = (
    "EnforcementProjectionError",
    "EnforcementClause",
    "EnforcementGroup",
    "EnforcementProjector",
    "NSX_TAG_SCOPE",
    "to_nsx",
    "to_tag_match",
    "project_to_nsx",
    "project_to_tag_match",
)
