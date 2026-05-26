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
from pathlib import Path
from typing import Any, Iterable, Mapping

from ._yaml_loaders import (
    read_schema_resource,
    read_yaml_path,
    read_yaml_resource,
    validate_against_schema,
)
from .codebook import Codebook
from .rule_renderer import render_rule
from .types import CompositionSpec, FacetOperation, FacetPredicate


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


# ---------------------------------------------------------------------------
# YAML loader (ADR-084 §C1)
# ---------------------------------------------------------------------------

_YAML_PACKAGE = "uiao.canon.data.orgpath"
_YAML_RESOURCE = "admin-units.yaml"
_SCHEMA_PACKAGE = "uiao.schemas.orgpath"
_SCHEMA_RESOURCE = "admin-units.schema.json"


def _composition_from_doc(doc: dict[str, Any]) -> CompositionSpec:
    predicates = tuple(FacetPredicate(facet=p["facet"], op=p["op"], value=p["value"]) for p in doc["predicates"])
    return CompositionSpec(predicates=predicates, combinator=doc.get("combinator", "and"))


def load_admin_unit_registry(
    codebook: Codebook,
    *,
    yaml_path: Path | str | None = None,
) -> AdminUnitRegistry:
    """Load the canonical AU registry YAML and render against ``codebook``."""
    document = read_yaml_resource(_YAML_PACKAGE, _YAML_RESOURCE) if yaml_path is None else read_yaml_path(yaml_path)
    schema = read_schema_resource(_SCHEMA_PACKAGE, _SCHEMA_RESOURCE)
    validate_against_schema(document, schema, "admin-units")

    specs: list[tuple[str, CompositionSpec, str, tuple[tuple[str, str], ...]]] = []
    for u in document["units"]:
        scoped_roles_tuple: tuple[tuple[str, str], ...] = tuple(
            (r["role"], r["delegate"]) for r in u.get("scoped_roles", [])
        )
        specs.append(
            (
                u["name"],
                _composition_from_doc(u["composition"]),
                u["description"],
                scoped_roles_tuple,
            )
        )
    return AdminUnitRegistry.from_specs(codebook, specs)
