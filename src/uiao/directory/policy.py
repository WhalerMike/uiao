"""Per-bind read scoping for the Active Governance Directory (ADR-100 §5).

A read projection is still an information-disclosure surface: an anonymous
`SEARCH` returns whatever the tree holds. ADR-100 §5 names *per-bind read
scoping* as the control that bounds that disclosure — restricting which
facets an anonymous (vs. authenticated) bind may read — and flags it as
the precondition for projecting any sensitive facet or leaving loopback.

This module implements the facet-level half of that control: a
:class:`ReadPolicy` marks certain projected attributes **sensitive**, so
they are stripped from results unless the connection has completed a
successful *authenticated* (non-anonymous) simple bind. The governed but
non-sensitive facets (region, department, role, …) stay anonymously
readable, preserving the increment-1 behaviour for everything that is not
security- or finance-bearing.

The default policy marks the clearance and cost-center facets sensitive,
resolved to their canonical ``uiaoOrgPath<Facet>`` attribute names from
the ``ldap`` binding profile (UIAO_193) rather than hardcoded here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from uiao.directory.protocol import Entry
from uiao.modernization.orgtree.binding_profiles import load_binding_profile

_IDENTITY_PLANE = "identity"

#: Facets whose values are security- or finance-bearing and therefore
#: require an authenticated bind to read. Named by codebook facet (not LDAP
#: attribute) so the binding profile resolves the wire name.
_DEFAULT_SENSITIVE_FACETS: tuple[str, ...] = ("clearance_level", "cost_center")


@dataclass(frozen=True)
class ReadPolicy:
    """Decides which attributes a bind may read.

    ``sensitive_attributes`` is a set of LDAP attribute names (e.g.
    ``uiaoOrgPathClearanceLevel``) hidden from anonymous binds. Matching
    is case-insensitive, mirroring LDAP attribute-description equality.
    """

    sensitive_attributes: frozenset[str] = field(default_factory=frozenset)

    def is_sensitive(self, attribute: str) -> bool:
        lowered = attribute.lower()
        return any(lowered == s.lower() for s in self.sensitive_attributes)

    def apply(self, entry: Entry, *, authenticated: bool) -> Entry:
        """Return ``entry`` with sensitive attributes removed for anon binds.

        An authenticated bind sees the entry unchanged. The DN itself is
        never redacted — only attribute values — because a stripped entry
        must still be addressable.
        """
        if authenticated or not self.sensitive_attributes:
            return entry
        kept = {name: vals for name, vals in entry.attributes.items() if not self.is_sensitive(name)}
        if len(kept) == len(entry.attributes):
            return entry
        return Entry(dn=entry.dn, attributes=kept)


def _resolve_sensitive_attributes(facets: tuple[str, ...]) -> frozenset[str]:
    """Map codebook facet names to their ``ldap`` binding-profile locators."""
    profile = load_binding_profile("ldap")
    out: set[str] = set()
    for facet in facets:
        locator = profile.locator_for(facet, _IDENTITY_PLANE)
        if locator:
            out.add(locator)
    return frozenset(out)


@lru_cache(maxsize=1)
def default_read_policy() -> ReadPolicy:
    """The default policy: clearance + cost-center facets require auth."""
    return ReadPolicy(sensitive_attributes=_resolve_sensitive_attributes(_DEFAULT_SENSITIVE_FACETS))
