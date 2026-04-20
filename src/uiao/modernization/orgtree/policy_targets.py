"""OrgTree policy-targeting canon loader (MOD_N, ADR-039).

Loads ``src/uiao/canon/data/orgpath/policy-targets.yaml`` and exposes a
:class:`PolicyTargetingCanon` that the ``entra-policy-targeting``
adapter consumes.

Phase 5 binds the **policy-consumer layer** (Intune configuration
profiles, Azure Policy definitions) to the OrgTree produced by phases
2–4. Policy bodies are out of scope; only the assignment/scope binding
is canon-governed.

The loader enforces cross-canon integrity:

* every Intune ``target_group`` must resolve to a live MOD_B dynamic
  group (ADR-036), otherwise the assignment points at a name that will
  never exist in a tenant;
* every Arc ``orgpath_selector.prefix`` must be either the root ``ORG``
  (baseline-everything) or an active code in the MOD_A codebook — no
  Arc assignment may scope to a deprecated or absent OrgPath;
* ``(profile_ref, target_group)`` pairs are unique within
  ``intune_assignments[]``;
* ``assignment_name`` values are unique within ``arc_policy_assignments[]``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Dict, Mapping, Optional, Set, Tuple

import yaml

from .codebook import Codebook, default_codebook
from .dynamic_groups import DynamicGroupLibrary, default_dynamic_group_library


class PolicyTargetingValidationError(ValueError):
    """Raised when the policy-targeting canon fails validation."""


@dataclass(frozen=True)
class ProfileRef:
    kind: str
    match_by: str
    value: str

    def cache_key(self) -> Tuple[str, str, str]:
        return (self.kind, self.match_by, self.value)


@dataclass(frozen=True)
class IntuneAssignment:
    profile_ref: ProfileRef
    target_group: str
    intent: str
    purpose: str

    def dedup_key(self) -> Tuple[Tuple[str, str, str], str, str]:
        return (self.profile_ref.cache_key(), self.target_group, self.intent)


@dataclass(frozen=True)
class PolicyDefinitionRef:
    match_by: str
    value: str


@dataclass(frozen=True)
class OrgPathSelector:
    prefix: str
    match_mode: str  # "startsWith" | "equals"

    def matches(self, orgpath: str) -> bool:
        if self.match_mode == "equals":
            return orgpath == self.prefix
        return orgpath == self.prefix or orgpath.startswith(self.prefix + "-")


@dataclass(frozen=True)
class ArcPolicyAssignment:
    assignment_name: str
    policy_definition: PolicyDefinitionRef
    orgpath_selector: OrgPathSelector
    purpose: str


@dataclass(frozen=True)
class PolicyTargetingCanon:
    schema_version: str
    document_id: str
    parent_canon: str
    intune_assignments: Tuple[IntuneAssignment, ...]
    arc_policy_assignments: Mapping[str, ArcPolicyAssignment]

    def intune_target_groups(self) -> Set[str]:
        return {a.target_group for a in self.intune_assignments}

    def arc_assignment_by_name(self, name: str) -> Optional[ArcPolicyAssignment]:
        return self.arc_policy_assignments.get(name)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

_DEFAULT_CANON_RESOURCE = ("uiao.canon.data.orgpath", "policy-targets.yaml")
_DEFAULT_SCHEMA_RESOURCE = ("uiao.schemas.orgpath", "policy-targets.schema.json")


def _read_default_canon() -> str:
    package, name = _DEFAULT_CANON_RESOURCE
    return resources.files(package).joinpath(name).read_text(encoding="utf-8")


def _read_default_schema() -> Dict:
    package, name = _DEFAULT_SCHEMA_RESOURCE
    return json.loads(resources.files(package).joinpath(name).read_text(encoding="utf-8"))


def _validate_schema(document: Dict) -> None:
    try:
        import jsonschema
    except ImportError as exc:  # pragma: no cover
        raise PolicyTargetingValidationError(
            "jsonschema is required to validate policy-targeting canon"
        ) from exc
    schema = _read_default_schema()
    try:
        jsonschema.validate(instance=document, schema=schema)
    except jsonschema.ValidationError as exc:
        raise PolicyTargetingValidationError(
            f"policy-targets schema validation failed: {exc.message} at "
            f"{'/'.join(str(p) for p in exc.absolute_path)}"
        ) from exc


def _validate_integrity(
    document: Dict,
    codebook: Codebook,
    dynamic_groups: DynamicGroupLibrary,
) -> None:
    # 1. Intune target_group references resolve.
    intune_seen: Set[Tuple[Tuple[str, str, str], str, str]] = set()
    for i, assignment in enumerate(document.get("intune_assignments", [])):
        if assignment["target_group"] not in dynamic_groups.names:
            raise PolicyTargetingValidationError(
                f"intune_assignments[{i}] target_group "
                f"'{assignment['target_group']}' does not resolve to a "
                "MOD_B dynamic group (ADR-036)"
            )
        dedup = (
            (
                assignment["profile_ref"]["kind"],
                assignment["profile_ref"]["match_by"],
                assignment["profile_ref"]["value"],
            ),
            assignment["target_group"],
            assignment["intent"],
        )
        if dedup in intune_seen:
            raise PolicyTargetingValidationError(
                f"Duplicate intune_assignment: {dedup}"
            )
        intune_seen.add(dedup)

    # 2. Arc orgpath_selector prefixes must be codebook-recognised, and
    # assignment_name unique.
    arc_names: Set[str] = set()
    for i, assignment in enumerate(document.get("arc_policy_assignments", [])):
        name = assignment["assignment_name"]
        if name in arc_names:
            raise PolicyTargetingValidationError(
                f"Duplicate arc_policy_assignment name: {name}"
            )
        arc_names.add(name)

        prefix = assignment["orgpath_selector"]["prefix"]
        if codebook.is_deprecated(prefix):
            raise PolicyTargetingValidationError(
                f"arc_policy_assignment '{name}' selector prefix '{prefix}' "
                "is deprecated in MOD_A codebook"
            )
        # ORG (root) is not an entry in the codebook's `codes` list if the
        # codebook chooses to omit the root, so accept it explicitly.
        if prefix != "ORG" and not codebook.is_active(prefix):
            raise PolicyTargetingValidationError(
                f"arc_policy_assignment '{name}' selector prefix '{prefix}' "
                "is not an active OrgPath in the MOD_A codebook"
            )


def _build(document: Dict) -> PolicyTargetingCanon:
    intune = tuple(
        IntuneAssignment(
            profile_ref=ProfileRef(
                kind=a["profile_ref"]["kind"],
                match_by=a["profile_ref"]["match_by"],
                value=a["profile_ref"]["value"],
            ),
            target_group=a["target_group"],
            intent=a["intent"],
            purpose=a["purpose"],
        )
        for a in document.get("intune_assignments", []) or []
    )
    arc = {
        a["assignment_name"]: ArcPolicyAssignment(
            assignment_name=a["assignment_name"],
            policy_definition=PolicyDefinitionRef(
                match_by=a["policy_definition"]["match_by"],
                value=a["policy_definition"]["value"],
            ),
            orgpath_selector=OrgPathSelector(
                prefix=a["orgpath_selector"]["prefix"],
                match_mode=a["orgpath_selector"]["match_mode"],
            ),
            purpose=a["purpose"],
        )
        for a in document.get("arc_policy_assignments", []) or []
    }
    return PolicyTargetingCanon(
        schema_version=document["schema_version"],
        document_id=document["document_id"],
        parent_canon=document["parent_canon"],
        intune_assignments=intune,
        arc_policy_assignments=arc,
    )


def load_policy_targeting_canon(
    path: Optional[Path] = None,
    codebook: Optional[Codebook] = None,
    dynamic_groups: Optional[DynamicGroupLibrary] = None,
) -> PolicyTargetingCanon:
    """Load and validate the Phase 5 policy-targeting canon."""
    raw_text = (
        _read_default_canon() if path is None
        else Path(path).read_text(encoding="utf-8")
    )
    document = yaml.safe_load(raw_text)
    if not isinstance(document, dict):
        raise PolicyTargetingValidationError(
            "policy-targets must be a YAML mapping at the top level"
        )
    _validate_schema(document)
    _validate_integrity(
        document,
        codebook or default_codebook(),
        dynamic_groups or default_dynamic_group_library(),
    )
    return _build(document)


@lru_cache(maxsize=1)
def default_policy_targeting_canon() -> PolicyTargetingCanon:
    return load_policy_targeting_canon()
