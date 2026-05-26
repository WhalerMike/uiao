"""Policy targeting library — Model C (ADR-084 §C3, §C9 Phase 5 #4).

Same architectural pattern as :py:mod:`uiao.modernization.orgtree.dynamic_groups`
and :py:mod:`uiao.modernization.orgtree.admin_units`: per-facet
``CompositionSpec`` rendered into a targeting predicate, but the
emitted artifact is a *policy assignment scope* — a rule used to bind
a policy definition (Conditional Access, Intune device-configuration,
Azure Policy, Defender, etc.) to a population of principals or
resources.

Per ADR-078 / ADR-039, this consumer supersedes the retired Model A
composite-string policy-targeting helper.
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
class PolicyTargetSpec:
    """A single canonical policy-targeting definition.

    Attributes
    ----------
    assignment_name
        Operator-facing name for the assignment, e.g.
        ``CA-Privileged-Cleared-MFA``.
    policy_definition_id
        Identifier of the policy this assignment binds (Azure Policy
        definition ID, Conditional Access policy ID, etc.). The
        consumer does not validate this — that's the policy plane's
        concern.
    transport
        ``"ca"`` (Conditional Access) | ``"azure_policy"`` |
        ``"intune"`` | ``"defender"`` — informational, used by the
        planner to route to the right downstream API.
    composition
        The boolean composition rendered into the scope rule.
    rule
        The rendered Entra dynamic-membership-rule string.
    description
        Operator-facing prose.
    """

    assignment_name: str
    policy_definition_id: str
    transport: str
    composition: CompositionSpec
    rule: str
    description: str


@dataclass(frozen=True)
class PolicyTargetLibrary:
    """In-memory view of the policy targeting library."""

    codebook: Codebook
    targets: Mapping[str, PolicyTargetSpec]

    @classmethod
    def from_specs(
        cls,
        codebook: Codebook,
        specs: Iterable[tuple[str, str, str, CompositionSpec, str]],
    ) -> PolicyTargetLibrary:
        """Build from ``(assignment_name, policy_def_id, transport, composition, description)`` tuples."""
        built: dict[str, PolicyTargetSpec] = {}
        for name, def_id, transport, composition, description in specs:
            if name in built:
                raise ValueError(f"Duplicate assignment name: '{name}'")
            if transport not in ("ca", "azure_policy", "intune", "defender"):
                raise ValueError(
                    f"Unsupported transport '{transport}'; expected one of: ca, azure_policy, intune, defender"
                )
            rule = render_rule(codebook, composition)
            built[name] = PolicyTargetSpec(
                assignment_name=name,
                policy_definition_id=def_id,
                transport=transport,
                composition=composition,
                rule=rule,
                description=description,
            )
        return cls(codebook=codebook, targets=built)

    @property
    def names(self) -> set[str]:
        return set(self.targets.keys())

    def by_transport(self, transport: str) -> tuple[PolicyTargetSpec, ...]:
        return tuple(t for t in self.targets.values() if t.transport == transport)

    def get(self, name: str) -> PolicyTargetSpec:
        return self.targets[name]


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------


class PolicyTargetPlanner:
    """Plan policy-assignment operations against an observed snapshot."""

    def __init__(self, library: PolicyTargetLibrary) -> None:
        self.library = library

    def plan(self, observed: Iterable) -> list[FacetOperation]:
        observed_by_id = {ot.assignment_id: ot for ot in observed}
        ops: list[FacetOperation] = []

        for name, spec in self.library.targets.items():
            assignment_id = self._derive_assignment_id(name)
            if assignment_id not in observed_by_id:
                ops.append(
                    FacetOperation(
                        facet="<policy-target>",
                        attribute="<scope_rule>",
                        op="create",
                        value=spec.rule,
                        target=assignment_id,
                        metadata={
                            "assignment_name": spec.assignment_name,
                            "policy_definition_id": spec.policy_definition_id,
                            "transport": spec.transport,
                            "description": spec.description,
                        },
                    )
                )
                continue
            obs = observed_by_id[assignment_id]
            if obs.scope_rule != spec.rule:
                ops.append(
                    FacetOperation(
                        facet="<policy-target>",
                        attribute="<scope_rule>",
                        op="update",
                        value=spec.rule,
                        target=assignment_id,
                        metadata={
                            "assignment_name": spec.assignment_name,
                            "policy_definition_id": spec.policy_definition_id,
                            "transport": spec.transport,
                            "observed_rule": obs.scope_rule,
                        },
                    )
                )
            elif obs.policy_definition_id != spec.policy_definition_id:
                ops.append(
                    FacetOperation(
                        facet="<policy-target>",
                        attribute="<policy_definition_id>",
                        op="rebind",
                        value=spec.policy_definition_id,
                        target=assignment_id,
                        metadata={
                            "assignment_name": spec.assignment_name,
                            "observed_definition_id": obs.policy_definition_id,
                            "expected_definition_id": spec.policy_definition_id,
                        },
                    )
                )
        return ops

    @staticmethod
    def _derive_assignment_id(name: str) -> str:
        """Derive a stable assignment id from the operator-facing name."""
        return f"assignment::{name}"


# ---------------------------------------------------------------------------
# YAML loader (ADR-084 §C1)
# ---------------------------------------------------------------------------

_YAML_PACKAGE = "uiao.canon.data.orgpath"
_YAML_RESOURCE = "policy-targets.yaml"
_SCHEMA_PACKAGE = "uiao.schemas.orgpath"
_SCHEMA_RESOURCE = "policy-targets.schema.json"


def _composition_from_doc(doc: dict[str, Any]) -> CompositionSpec:
    predicates = tuple(FacetPredicate(facet=p["facet"], op=p["op"], value=p["value"]) for p in doc["predicates"])
    return CompositionSpec(predicates=predicates, combinator=doc.get("combinator", "and"))


def load_policy_target_library(
    codebook: Codebook,
    *,
    yaml_path: Path | str | None = None,
) -> PolicyTargetLibrary:
    """Load the canonical policy-targeting library YAML and render against ``codebook``."""
    document = read_yaml_resource(_YAML_PACKAGE, _YAML_RESOURCE) if yaml_path is None else read_yaml_path(yaml_path)
    schema = read_schema_resource(_SCHEMA_PACKAGE, _SCHEMA_RESOURCE)
    validate_against_schema(document, schema, "policy-targets")

    specs: list[tuple[str, str, str, CompositionSpec, str]] = []
    for t in document["targets"]:
        specs.append(
            (
                t["assignment_name"],
                t["policy_definition_id"],
                t["transport"],
                _composition_from_doc(t["composition"]),
                t["description"],
            )
        )
    return PolicyTargetLibrary.from_specs(codebook, specs)
