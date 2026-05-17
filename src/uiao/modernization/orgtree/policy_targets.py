"""OrgTree policy-targeting canon loader (UIAO_164, ADR-039 + ADR-073).

Loads ``src/uiao/canon/data/orgpath/policy-targets.yaml`` and exposes a
:class:`PolicyTargetingCanon` that the ``orgtree-policy-targeting``
adapter consumes (renamed from ``entra-policy-targeting`` by ADR-073
§D2 to reflect the broadened transport scope).

Binds the **policy-consumer layer** to the OrgTree produced by phases
2–4. Three transports are covered:

* **Intune** configuration profiles + compliance policies (ADR-039).
* **Azure Policy** assignments on Arc-enrolled machines (ADR-039).
* **NAC** policy bindings — Cisco ISE / Aruba ClearPass / Entra RADIUS
  Proxy / NPS (hybrid window only) — that bind AAA policies to
  OrgTree-*-Devices dynamic groups, with port-level enforcement
  payloads (VLAN / dACL / SGT / posture-profile) returned on RADIUS
  Access-Accept (ADR-073, Phase B).

Policy bodies are out of scope; only the assignment/scope binding is
canon-governed.

The loader enforces cross-canon integrity:

* every Intune ``target_group`` must resolve to a live UIAO_152 dynamic
  group (ADR-036), otherwise the assignment points at a name that will
  never exist in a tenant;
* every Arc ``orgpath_selector.prefix`` must be either the root ``ORG``
  (baseline-everything) or an active code in the UIAO_151 codebook — no
  Arc assignment may scope to a deprecated or absent OrgPath;
* every NAC ``target_group`` must resolve to a live UIAO_152 dynamic
  group (same rule as Intune; ADR-073 §D6 Phase B);
* ``(profile_ref, target_group, intent)`` triples are unique within
  ``intune_assignments[]``;
* ``(policy_ref, target_group, enforcement)`` triples are unique within
  ``nac_assignments[]`` (ADR-073 §D1);
* ``assignment_name`` values are unique across ``arc_policy_assignments[]``
  and ``nac_assignments[]`` combined (shared namespace per ADR-073 §D1).

Cross-canon checks deferred to ADR-073 Phase C (not enforced in this
loader): VLAN existence in IPAM canon (DM_010 / BlueCat / InfoBlox),
dACL / posture-profile existence on the AAA server, and the
hybrid-window paired-twin rule for ``aaa_server: nps``.
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


# --- NAC (ADR-073) --------------------------------------------------------


@dataclass(frozen=True)
class NacPolicyRef:
    policy_kind: str  # policy-set | service | connection-policy | posture-profile
    match_by: str  # name | id
    value: str

    def cache_key(self) -> Tuple[str, str, str]:
        return (self.policy_kind, self.match_by, self.value)


@dataclass(frozen=True)
class NacEnforcement:
    vlan_id: int
    change_of_authorization: bool
    dacl_name: Optional[str] = None
    sgt_tag: Optional[int] = None
    posture_profile: Optional[str] = None

    def cache_key(self) -> Tuple[int, bool, Optional[str], Optional[int], Optional[str]]:
        return (self.vlan_id, self.change_of_authorization, self.dacl_name, self.sgt_tag, self.posture_profile)


@dataclass(frozen=True)
class NacAssignment:
    assignment_name: str
    aaa_server: str  # cisco-ise | aruba-clearpass | entra-radius | nps
    policy_ref: NacPolicyRef
    target_group: str
    enforcement: NacEnforcement
    intent: str  # permit | quarantine | deny
    purpose: str

    def dedup_key(self) -> Tuple[Tuple[str, str, str], str, Tuple[int, bool, Optional[str], Optional[int], Optional[str]]]:
        return (self.policy_ref.cache_key(), self.target_group, self.enforcement.cache_key())


@dataclass(frozen=True)
class PolicyTargetingCanon:
    schema_version: str
    document_id: str
    parent_canon: str
    intune_assignments: Tuple[IntuneAssignment, ...]
    arc_policy_assignments: Mapping[str, ArcPolicyAssignment]
    nac_assignments: Mapping[str, NacAssignment]

    def intune_target_groups(self) -> Set[str]:
        return {a.target_group for a in self.intune_assignments}

    def arc_assignment_by_name(self, name: str) -> Optional[ArcPolicyAssignment]:
        return self.arc_policy_assignments.get(name)

    def nac_target_groups(self) -> Set[str]:
        return {a.target_group for a in self.nac_assignments.values()}

    def nac_assignment_by_name(self, name: str) -> Optional[NacAssignment]:
        return self.nac_assignments.get(name)


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
    return json.loads(resources.files(package).joinpath(name).read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _validate_schema(document: Dict) -> None:
    try:
        import jsonschema
    except ImportError as exc:  # pragma: no cover
        raise PolicyTargetingValidationError("jsonschema is required to validate policy-targeting canon") from exc
    schema = _read_default_schema()
    try:
        jsonschema.validate(instance=document, schema=schema)
    except jsonschema.ValidationError as exc:
        raise PolicyTargetingValidationError(
            f"policy-targets schema validation failed: {exc.message} at {'/'.join(str(p) for p in exc.absolute_path)}"
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
                "UIAO_152 dynamic group (ADR-036)"
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
            raise PolicyTargetingValidationError(f"Duplicate intune_assignment: {dedup}")
        intune_seen.add(dedup)

    # 2. Arc orgpath_selector prefixes must be codebook-recognised, and
    # assignment_name unique. assignment_name shares a namespace with
    # nac_assignments[] per ADR-073 §D1.
    arc_names: Set[str] = set()
    for _i, assignment in enumerate(document.get("arc_policy_assignments", [])):
        name = assignment["assignment_name"]
        if name in arc_names:
            raise PolicyTargetingValidationError(f"Duplicate arc_policy_assignment name: {name}")
        arc_names.add(name)

        prefix = assignment["orgpath_selector"]["prefix"]
        if codebook.is_deprecated(prefix):
            raise PolicyTargetingValidationError(
                f"arc_policy_assignment '{name}' selector prefix '{prefix}' is deprecated in UIAO_151 codebook"
            )
        # ORG (root) is not an entry in the codebook's `codes` list if the
        # codebook chooses to omit the root, so accept it explicitly.
        if prefix != "ORG" and not codebook.is_active(prefix):
            raise PolicyTargetingValidationError(
                f"arc_policy_assignment '{name}' selector prefix '{prefix}' "
                "is not an active OrgPath in the UIAO_151 codebook"
            )

    # 3. NAC assignments (ADR-073 §D6 Phase B): target_group must resolve
    # to a UIAO_152 dynamic group (same rule as Intune); triple
    # (policy_ref, target_group, enforcement) must be unique; assignment_name
    # must be unique across the (arc + nac) namespace.
    #
    # Cross-canon checks deferred to Phase C (not enforced here):
    #   - enforcement.vlan_id existence in IPAM canon (DM_010)
    #   - enforcement.dacl_name / posture_profile existence on AAA server
    #   - aaa_server: nps paired-twin rule (ADR-073 §D4)
    nac_seen: Set[Tuple[Tuple[str, str, str], str, Tuple[int, bool, Optional[str], Optional[int], Optional[str]]]] = set()
    for i, assignment in enumerate(document.get("nac_assignments", []) or []):
        if assignment["target_group"] not in dynamic_groups.names:
            raise PolicyTargetingValidationError(
                f"nac_assignments[{i}] target_group "
                f"'{assignment['target_group']}' does not resolve to a "
                "UIAO_152 dynamic group (ADR-036). Add the device-targeting "
                "group to dynamic-groups.yaml first."
            )
        name = assignment["assignment_name"]
        if name in arc_names:
            raise PolicyTargetingValidationError(
                f"Duplicate assignment_name across arc + nac namespace: '{name}' "
                "(ADR-073 §D1 — assignment_name is unique across the file)"
            )
        arc_names.add(name)

        enforcement = assignment["enforcement"]
        enforcement_key = (
            enforcement["vlan_id"],
            enforcement["change_of_authorization"],
            enforcement.get("dacl_name"),
            enforcement.get("sgt_tag"),
            enforcement.get("posture_profile"),
        )
        dedup = (
            (
                assignment["policy_ref"]["policy_kind"],
                assignment["policy_ref"]["match_by"],
                assignment["policy_ref"]["value"],
            ),
            assignment["target_group"],
            enforcement_key,
        )
        if dedup in nac_seen:
            raise PolicyTargetingValidationError(f"Duplicate nac_assignment: {dedup}")
        nac_seen.add(dedup)


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
    nac = {
        a["assignment_name"]: NacAssignment(
            assignment_name=a["assignment_name"],
            aaa_server=a["aaa_server"],
            policy_ref=NacPolicyRef(
                policy_kind=a["policy_ref"]["policy_kind"],
                match_by=a["policy_ref"]["match_by"],
                value=a["policy_ref"]["value"],
            ),
            target_group=a["target_group"],
            enforcement=NacEnforcement(
                vlan_id=a["enforcement"]["vlan_id"],
                change_of_authorization=a["enforcement"]["change_of_authorization"],
                dacl_name=a["enforcement"].get("dacl_name"),
                sgt_tag=a["enforcement"].get("sgt_tag"),
                posture_profile=a["enforcement"].get("posture_profile"),
            ),
            intent=a["intent"],
            purpose=a["purpose"],
        )
        for a in document.get("nac_assignments", []) or []
    }
    return PolicyTargetingCanon(
        schema_version=document["schema_version"],
        document_id=document["document_id"],
        parent_canon=document["parent_canon"],
        intune_assignments=intune,
        arc_policy_assignments=arc,
        nac_assignments=nac,
    )


def load_policy_targeting_canon(
    path: Optional[Path] = None,
    codebook: Optional[Codebook] = None,
    dynamic_groups: Optional[DynamicGroupLibrary] = None,
) -> PolicyTargetingCanon:
    """Load and validate the Phase 5 policy-targeting canon."""
    raw_text = _read_default_canon() if path is None else Path(path).read_text(encoding="utf-8")
    document = yaml.safe_load(raw_text)
    if not isinstance(document, dict):
        raise PolicyTargetingValidationError("policy-targets must be a YAML mapping at the top level")
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
