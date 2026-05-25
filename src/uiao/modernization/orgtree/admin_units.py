"""Administrative Unit registry — Model C (ADR-084 §C3, §C9 Phase 5 #3).

Same architectural pattern as :py:mod:`uiao.modernization.orgtree.dynamic_groups`:
per-facet ``CompositionSpec`` rendered into Entra membership-rule
strings, but the emitted resource is an Administrative Unit (not a
dynamic group). Per UIAO_154 v3.0, every UIAO-managed AU is
Restricted Management — Global Administrators cannot manage AU
members without an explicit AU-scoped role assignment.

Per ADR-078 / ADR-037, this consumer supersedes the retired Model A
composite-string AU planner.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .codebook import Codebook
from .rule_renderer import render_rule
from .types import CompositionSpec, FacetOperation


@dataclass(frozen=True)
class AdminUnitSpec:
    """A single canonical Administrative Unit definition.

    Attributes
    ----------
    name
        Display name, e.g. ``AU-Department-IT``.
    composition
        The boolean composition rendered into the AU membership rule.
    rule
        The rendered Entra dynamic-membership-rule string.
    description
        Operator-facing prose.
    restricted_management
        Defaults True per UIAO_154 v3.0 doctrine.
    scoped_roles
        Tuple of ``(role_name, delegate)`` describing role assignments
        intended for this AU. Informational — actual role-assignment
        provisioning happens in a separate workflow.
    """

    name: str
    composition: CompositionSpec
    rule: str
    description: str
    restricted_management: bool = True
    scoped_roles: tuple[tuple[str, str], ...] = ()

    def to_graph_body(self) -> dict:
        """Return a ``POST /administrativeUnits`` request body for Graph."""
        body: dict[str, object] = {
            "displayName": self.name,
            "description": self.description,
            "membershipType": "Dynamic",
            "membershipRule": self.rule,
            "membershipRuleProcessingState": "On",
        }
        if self.restricted_management:
            body["isMemberManagementRestricted"] = True
        return body


@dataclass(frozen=True)
class AdminUnitRegistry:
    """In-memory view of the AU registry."""

    codebook: Codebook
    units: Mapping[str, AdminUnitSpec]

    @classmethod
    def from_specs(
        cls,
        codebook: Codebook,
        specs: Iterable[tuple[str, CompositionSpec, str, tuple[tuple[str, str], ...]]],
    ) -> AdminUnitRegistry:
        """Build a registry from ``(name, composition, description, scoped_roles)`` tuples."""
        built: dict[str, AdminUnitSpec] = {}
        for name, composition, description, scoped_roles in specs:
            if name in built:
                raise ValueError(f"Duplicate AU name: '{name}'")
            rule = render_rule(codebook, composition)
            built[name] = AdminUnitSpec(
                name=name,
                composition=composition,
                rule=rule,
                description=description,
                scoped_roles=scoped_roles,
            )
        return cls(codebook=codebook, units=built)

    @property
    def names(self) -> set[str]:
        return set(self.units.keys())

    def get(self, name: str) -> AdminUnitSpec:
        return self.units[name]


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------


class AdminUnitPlanner:
    """Plan AU operations against an observed snapshot."""

    def __init__(self, registry: AdminUnitRegistry) -> None:
        self.registry = registry

    def plan(self, observed: Iterable) -> list[FacetOperation]:
        observed_by_name = {au.name: au for au in observed}
        ops: list[FacetOperation] = []

        for name, spec in self.registry.units.items():
            if name not in observed_by_name:
                ops.append(
                    FacetOperation(
                        facet="<au-registry>",
                        attribute="<membershipRule>",
                        op="create",
                        value=spec.rule,
                        target=name,
                        metadata={
                            "graph_body": spec.to_graph_body(),
                            "description": spec.description,
                            "scoped_roles": list(spec.scoped_roles),
                        },
                    )
                )
                continue
            obs = observed_by_name[name]
            updates: dict = {}
            if obs.membership_rule != spec.rule:
                updates["membershipRule"] = spec.rule
            if spec.restricted_management and not obs.restricted_management:
                updates["isMemberManagementRestricted"] = True
            if updates:
                ops.append(
                    FacetOperation(
                        facet="<au-registry>",
                        attribute="<membershipRule>",
                        op="update",
                        value=spec.rule,
                        target=name,
                        metadata={
                            "object_id": obs.object_id,
                            "patch_body": updates,
                            "observed_rule": obs.membership_rule,
                        },
                    )
                )

        # Phantom AUs — tenant has an AU-* unit not in the registry.
        for name, obs in observed_by_name.items():
            if name.startswith("AU-") and name not in self.registry.units:
                ops.append(
                    FacetOperation(
                        facet="<au-registry>",
                        attribute="<membershipRule>",
                        op="phantom",
                        value=None,
                        target=name,
                        metadata={
                            "object_id": obs.object_id,
                            "observed_rule": obs.membership_rule,
                            "reason": "AU-prefixed unit present in tenant but not declared in canonical registry",
                        },
                    )
                )

        return ops
