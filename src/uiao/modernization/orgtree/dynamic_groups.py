"""Dynamic group library — Model C (ADR-084 §C3, §C9 Phase 5 #2).

Consumes the per-facet ``Codebook`` and the shared ``rule_renderer`` to
emit canonical Entra dynamic-group definitions. Each
:class:`DynamicGroupSpec` declares a group name + composition spec; the
library renders the composition into a membership rule string at
construction time (catching Value Drift in the codebook before any
group reaches Entra).

Per ADR-084 §C1 the consumer accepts a programmatic library — no YAML
parsing. A separate YAML loader (future PR) populates the library from
``src/uiao/canon/data/orgpath/dynamic_groups.yaml``.

Per ADR-078 / ADR-036, the rebuilt library supersedes the retired
Model A composite-string consumer.
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
class DynamicGroupSpec:
    """A single canonical dynamic group definition.

    Attributes
    ----------
    name
        Display name, e.g. ``OrgTree-Department-IT-Users``.
    category
        Logical bucket for governance reporting (Region / Department /
        Division / Role / Clearance / AccountType / Cross-Cutting / CA /
        Licensing / Lifecycle).
    composition
        The boolean composition rendered into the Entra membership
        rule.
    rule
        The rendered Entra dynamic-membership-rule string (computed at
        :py:meth:`DynamicGroupLibrary.from_specs`).
    description
        Operator-facing prose for the group's purpose.
    group_type
        ``"Security"`` (default) or ``"M365"``.
    """

    name: str
    category: str
    composition: CompositionSpec
    rule: str
    description: str
    group_type: str = "Security"

    def to_graph_body(self) -> dict:
        """Return a ``POST /groups`` request body for Microsoft Graph.

        Per https://learn.microsoft.com/graph/api/group-post-groups —
        dynamic membership requires ``groupTypes:
        ["DynamicMembership"]`` plus ``membershipRule`` and
        ``membershipRuleProcessingState``.
        """
        return {
            "displayName": self.name,
            "mailEnabled": self.group_type == "M365",
            "mailNickname": self.name.lower().replace(" ", "-"),
            "securityEnabled": True,
            "groupTypes": ["DynamicMembership"] + (["Unified"] if self.group_type == "M365" else []),
            "membershipRule": self.rule,
            "membershipRuleProcessingState": "On",
            "description": self.description,
        }


@dataclass(frozen=True)
class DynamicGroupLibrary:
    """In-memory view of the dynamic group library.

    Build via :py:meth:`from_specs`, which renders every group's
    composition against the active codebook (catches Value Drift on
    deprecated / unknown facet values before any group is created).
    """

    codebook: Codebook
    groups: Mapping[str, DynamicGroupSpec]

    @classmethod
    def from_specs(
        cls,
        codebook: Codebook,
        specs: Iterable[tuple[str, str, CompositionSpec, str]],
        *,
        group_type: str = "Security",
    ) -> DynamicGroupLibrary:
        """Build a library from ``(name, category, composition, description)`` tuples.

        Each composition is rendered against ``codebook`` at construction
        time; a :py:class:`uiao.modernization.orgtree.rule_renderer.RuleRenderError`
        on any group fails the whole library load (atomic loading per
        ADR-084 §C1).
        """
        built: dict[str, DynamicGroupSpec] = {}
        for name, category, composition, description in specs:
            if name in built:
                raise ValueError(f"Duplicate dynamic group name: '{name}'")
            rule = render_rule(codebook, composition)
            built[name] = DynamicGroupSpec(
                name=name,
                category=category,
                composition=composition,
                rule=rule,
                description=description,
                group_type=group_type,
            )
        return cls(codebook=codebook, groups=built)

    @property
    def names(self) -> set[str]:
        return set(self.groups.keys())

    def by_category(self, category: str) -> tuple[DynamicGroupSpec, ...]:
        return tuple(g for g in self.groups.values() if g.category == category)

    def get(self, name: str) -> DynamicGroupSpec:
        return self.groups[name]


# ---------------------------------------------------------------------------
# Planner (ADR-084 §C2 — per-facet operations as the unit of work)
# ---------------------------------------------------------------------------


class DynamicGroupPlanner:
    """Plan group operations against an observed snapshot.

    Compares the canonical :py:class:`DynamicGroupLibrary` against the
    observed :py:class:`uiao.modernization.orgtree.types.GroupSnapshot`
    list. Emits per-group :py:class:`FacetOperation` records the drift
    engine classifies (Rule Drift / Phantom Group / Missing Group /
    Name Drift per UIAO_152 v3.0).
    """

    def __init__(self, library: DynamicGroupLibrary) -> None:
        self.library = library

    def plan(self, observed: Iterable) -> list[FacetOperation]:
        """Emit per-group operations.

        ``observed`` is an iterable of
        :py:class:`uiao.modernization.orgtree.types.GroupSnapshot`. The
        planner returns one FacetOperation per group requiring action;
        groups already aligned with the library produce no operation.
        """
        observed_by_name = {g.name: g for g in observed}
        ops: list[FacetOperation] = []

        # Missing groups — library has it; tenant doesn't.
        for name, spec in self.library.groups.items():
            if name not in observed_by_name:
                ops.append(
                    FacetOperation(
                        facet="<group-library>",
                        attribute="<membershipRule>",
                        op="create",
                        value=spec.rule,
                        target=name,
                        metadata={
                            "category": spec.category,
                            "description": spec.description,
                            "graph_body": spec.to_graph_body(),
                        },
                    )
                )
                continue

            obs = observed_by_name[name]
            if obs.membership_rule != spec.rule:
                ops.append(
                    FacetOperation(
                        facet="<group-library>",
                        attribute="<membershipRule>",
                        op="update",
                        value=spec.rule,
                        target=name,
                        metadata={
                            "category": spec.category,
                            "object_id": obs.object_id,
                            "observed_rule": obs.membership_rule,
                            "expected_rule": spec.rule,
                        },
                    )
                )

        # Phantom groups — tenant has an OrgTree-* group not in library.
        for name, obs in observed_by_name.items():
            if name.startswith("OrgTree-") and name not in self.library.groups:
                ops.append(
                    FacetOperation(
                        facet="<group-library>",
                        attribute="<membershipRule>",
                        op="phantom",
                        value=None,
                        target=name,
                        metadata={
                            "object_id": obs.object_id,
                            "observed_rule": obs.membership_rule,
                            "reason": "OrgTree-prefixed group present in tenant but not declared in canonical library",
                        },
                    )
                )

        return ops


# ---------------------------------------------------------------------------
# YAML loader (ADR-084 §C1 — optional convenience over from_specs)
# ---------------------------------------------------------------------------

_YAML_PACKAGE = "uiao.canon.data.orgpath"
_YAML_RESOURCE = "dynamic-groups.yaml"
_SCHEMA_PACKAGE = "uiao.schemas.orgpath"
_SCHEMA_RESOURCE = "dynamic-groups.schema.json"


def _composition_from_doc(doc: dict[str, Any]) -> CompositionSpec:
    predicates = tuple(FacetPredicate(facet=p["facet"], op=p["op"], value=p["value"]) for p in doc["predicates"])
    combinator = doc.get("combinator", "and")
    return CompositionSpec(predicates=predicates, combinator=combinator)


def load_dynamic_group_library(
    codebook: Codebook,
    *,
    yaml_path: Path | str | None = None,
) -> DynamicGroupLibrary:
    """Load the canonical dynamic group library YAML and render against ``codebook``.

    Validates the YAML against the dynamic-groups JSON Schema first,
    then builds a :py:class:`DynamicGroupLibrary` via :py:meth:`from_specs`
    (which catches Value Drift before any group reaches Entra).

    Parameters
    ----------
    codebook
        Active per-facet Codebook (ADR-084 §C1).
    yaml_path
        Optional override pointing at an alternate YAML file (typically
        used in tests). When omitted, the canonical library shipped
        inside the ``uiao.canon.data.orgpath`` package is loaded via
        ``importlib.resources``.
    """
    document = read_yaml_resource(_YAML_PACKAGE, _YAML_RESOURCE) if yaml_path is None else read_yaml_path(yaml_path)
    schema = read_schema_resource(_SCHEMA_PACKAGE, _SCHEMA_RESOURCE)
    validate_against_schema(document, schema, "dynamic-groups")

    # Per-group type override (single library-wide value, defaults to Security)
    specs: list[tuple[str, str, CompositionSpec, str]] = []
    for g in document["groups"]:
        specs.append(
            (
                g["name"],
                g["category"],
                _composition_from_doc(g["composition"]),
                g["description"],
            )
        )
    return DynamicGroupLibrary.from_specs(codebook, specs)
