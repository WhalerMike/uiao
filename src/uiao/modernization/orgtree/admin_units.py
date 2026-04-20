"""Delegation matrix loader — AUs + scoped roles (MOD_D, ADR-037).

Loads ``src/uiao/canon/data/orgpath/admin-units.yaml`` and exposes a
:class:`DelegationMatrix` the ``entra-admin-units`` adapter consumes to
reconcile the tenant against MOD_D.

The loader enforces three layers of validation:

1. **JSON Schema** — structural shape, role template GUIDs, restricted=true.
2. **Cross-canon integrity** — every AU's ``orgpath_refs`` must be active in
   the codebook (MOD_A/ADR-035); every role_assignment's ``principal_group``
   must resolve to either a MOD_B dynamic group (ADR-036) or one of the
   admin groups declared in this file; every ``au_scope`` must exist here;
   every ``role`` must exist in the built-in roles table.
3. **Uniqueness** — AU names, admin-group names, role assignments are
   each unique.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Set, Tuple

import yaml

from .codebook import Codebook, default_codebook
from .dynamic_groups import DynamicGroupLibrary, default_dynamic_group_library


class DelegationMatrixValidationError(ValueError):
    """Raised when the delegation matrix fails schema or integrity validation."""


@dataclass(frozen=True)
class AdministrativeUnit:
    name: str
    tier: str
    membership_rule: str
    orgpath_refs: Tuple[str, ...]
    restricted: bool
    description: str

    def to_graph_body(self) -> Dict[str, object]:
        """Return a ``POST /directoryAdministrativeUnits`` body for Graph."""
        return {
            "displayName": self.name,
            "description": self.description,
            "visibility": "HiddenMembership",
            "isMemberManagementRestricted": bool(self.restricted),
            "membershipType": "Dynamic",
            "membershipRule": self.membership_rule,
            "membershipRuleProcessingState": "On",
        }


@dataclass(frozen=True)
class RoleTemplate:
    display_name: str
    template_id: str


@dataclass(frozen=True)
class AdminGroup:
    name: str
    description: str
    governance_workflow: str


@dataclass(frozen=True)
class RoleAssignment:
    role: str
    principal_group: str
    au_scope: str
    tier: str
    purpose: str

    def key(self) -> Tuple[str, str, str]:
        """Uniqueness key — (role, principal_group, au_scope)."""
        return (self.role, self.principal_group, self.au_scope)

    def to_graph_body(
        self,
        *,
        role_template_id: str,
        principal_id: str,
        directory_scope_id: str,
    ) -> Dict[str, object]:
        """Graph ``POST /roleManagement/directory/roleAssignments`` body.

        Caller is responsible for resolving ``principal_id`` (group object id)
        and ``directory_scope_id`` (`/administrativeUnits/{id}`) at apply
        time — those values come from the tenant, not the canon.
        """
        return {
            "roleDefinitionId": role_template_id,
            "principalId": principal_id,
            "directoryScopeId": directory_scope_id,
        }


@dataclass(frozen=True)
class DelegationMatrix:
    schema_version: str
    document_id: str
    parent_canon: str
    au_regex: str
    admin_group_regex: str
    administrative_units: Mapping[str, AdministrativeUnit]
    roles: Mapping[str, RoleTemplate]
    admin_groups: Mapping[str, AdminGroup]
    role_assignments: Tuple[RoleAssignment, ...]

    @property
    def au_names(self) -> Set[str]:
        return set(self.administrative_units.keys())

    @property
    def admin_group_names(self) -> Set[str]:
        return set(self.admin_groups.keys())

    def role_template_id(self, display_name: str) -> Optional[str]:
        r = self.roles.get(display_name)
        return r.template_id if r else None

    def get_au(self, name: str) -> Optional[AdministrativeUnit]:
        return self.administrative_units.get(name)

    def assignments_for_au(self, au_name: str) -> List[RoleAssignment]:
        return [a for a in self.role_assignments if a.au_scope == au_name]


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

_DEFAULT_MATRIX_RESOURCE = ("uiao.canon.data.orgpath", "admin-units.yaml")
_DEFAULT_SCHEMA_RESOURCE = ("uiao.schemas.orgpath", "admin-units.schema.json")


def _read_default_matrix() -> str:
    package, name = _DEFAULT_MATRIX_RESOURCE
    return resources.files(package).joinpath(name).read_text(encoding="utf-8")


def _read_default_schema() -> Dict:
    package, name = _DEFAULT_SCHEMA_RESOURCE
    return json.loads(resources.files(package).joinpath(name).read_text(encoding="utf-8"))


def _validate_schema(document: Dict) -> None:
    try:
        import jsonschema
    except ImportError as exc:  # pragma: no cover
        raise DelegationMatrixValidationError(
            "jsonschema is required to validate the delegation matrix"
        ) from exc
    schema = _read_default_schema()
    try:
        jsonschema.validate(instance=document, schema=schema)
    except jsonschema.ValidationError as exc:
        raise DelegationMatrixValidationError(
            f"Delegation matrix schema validation failed: {exc.message} at "
            f"{'/'.join(str(p) for p in exc.absolute_path)}"
        ) from exc


def _validate_integrity(
    document: Dict,
    codebook: Codebook,
    dynamic_groups: DynamicGroupLibrary,
) -> None:
    # 1. AU orgpath_refs must be active in MOD_A codebook; AU names unique.
    au_names: Set[str] = set()
    for au in document["administrative_units"]:
        if au["name"] in au_names:
            raise DelegationMatrixValidationError(
                f"Duplicate administrative_unit: {au['name']}"
            )
        au_names.add(au["name"])
        for code in au["orgpath_refs"]:
            if codebook.is_deprecated(code):
                raise DelegationMatrixValidationError(
                    f"AU '{au['name']}' references deprecated OrgPath "
                    f"'{code}' (replaced by '{codebook.replacement_for(code)}')"
                )
            if not codebook.is_active(code):
                raise DelegationMatrixValidationError(
                    f"AU '{au['name']}' references unknown OrgPath '{code}' "
                    "— not in MOD_A codebook"
                )
            if f'"{code}"' not in au["membership_rule"]:
                raise DelegationMatrixValidationError(
                    f"AU '{au['name']}' orgpath_refs declares '{code}' but "
                    "its membership_rule does not quote it"
                )

    # 2. Role display_name unique; template_id unique.
    role_names: Set[str] = set()
    role_ids: Set[str] = set()
    for role in document["roles"]:
        if role["display_name"] in role_names:
            raise DelegationMatrixValidationError(
                f"Duplicate role display_name: {role['display_name']}"
            )
        if role["template_id"] in role_ids:
            raise DelegationMatrixValidationError(
                f"Duplicate role template_id: {role['template_id']}"
            )
        role_names.add(role["display_name"])
        role_ids.add(role["template_id"])

    # 3. Admin-group names unique; don't collide with MOD_B dynamic groups.
    ag_names: Set[str] = set()
    for ag in document.get("admin_groups", []):
        if ag["name"] in ag_names:
            raise DelegationMatrixValidationError(
                f"Duplicate admin_group: {ag['name']}"
            )
        if ag["name"] in dynamic_groups.names:
            raise DelegationMatrixValidationError(
                f"admin_group '{ag['name']}' collides with MOD_B dynamic "
                "group of the same name — admin groups are assigned, not "
                "dynamic; pick a different suffix"
            )
        ag_names.add(ag["name"])

    # 4. role_assignment references resolve; tuples unique.
    seen_assignments: Set[Tuple[str, str, str]] = set()
    valid_principals = dynamic_groups.names | ag_names
    for ra in document["role_assignments"]:
        key = (ra["role"], ra["principal_group"], ra["au_scope"])
        if key in seen_assignments:
            raise DelegationMatrixValidationError(
                f"Duplicate role_assignment: {key}"
            )
        seen_assignments.add(key)
        if ra["role"] not in role_names:
            raise DelegationMatrixValidationError(
                f"role_assignment '{key}' references unknown role "
                f"'{ra['role']}' — add to roles[]"
            )
        if ra["au_scope"] not in au_names:
            raise DelegationMatrixValidationError(
                f"role_assignment '{key}' references unknown AU "
                f"'{ra['au_scope']}' — add to administrative_units[]"
            )
        if ra["principal_group"] not in valid_principals:
            raise DelegationMatrixValidationError(
                f"role_assignment '{key}' references principal_group "
                f"'{ra['principal_group']}' — must be a MOD_B dynamic group "
                "or a MOD_D admin_group"
            )


def _build(document: Dict) -> DelegationMatrix:
    aus = {
        au["name"]: AdministrativeUnit(
            name=au["name"],
            tier=au["tier"],
            membership_rule=au["membership_rule"],
            orgpath_refs=tuple(au["orgpath_refs"]),
            restricted=bool(au["restricted"]),
            description=au["description"],
        )
        for au in document["administrative_units"]
    }
    roles = {
        r["display_name"]: RoleTemplate(
            display_name=r["display_name"], template_id=r["template_id"]
        )
        for r in document["roles"]
    }
    admin_groups = {
        ag["name"]: AdminGroup(
            name=ag["name"],
            description=ag["description"],
            governance_workflow=ag["governance_workflow"],
        )
        for ag in document.get("admin_groups", []) or []
    }
    role_assignments = tuple(
        RoleAssignment(
            role=ra["role"],
            principal_group=ra["principal_group"],
            au_scope=ra["au_scope"],
            tier=ra["tier"],
            purpose=ra["purpose"],
        )
        for ra in document["role_assignments"]
    )
    return DelegationMatrix(
        schema_version=document["schema_version"],
        document_id=document["document_id"],
        parent_canon=document["parent_canon"],
        au_regex=document["naming"]["au_regex"],
        admin_group_regex=document["naming"]["admin_group_regex"],
        administrative_units=aus,
        roles=roles,
        admin_groups=admin_groups,
        role_assignments=role_assignments,
    )


def load_delegation_matrix(
    path: Optional[Path] = None,
    codebook: Optional[Codebook] = None,
    dynamic_groups: Optional[DynamicGroupLibrary] = None,
) -> DelegationMatrix:
    """Load and validate the delegation matrix (AUs + scoped roles)."""
    raw_text = (
        _read_default_matrix() if path is None
        else Path(path).read_text(encoding="utf-8")
    )
    document = yaml.safe_load(raw_text)
    if not isinstance(document, dict):
        raise DelegationMatrixValidationError(
            "Delegation matrix must be a YAML mapping at the top level"
        )
    _validate_schema(document)
    _validate_integrity(
        document,
        codebook or default_codebook(),
        dynamic_groups or default_dynamic_group_library(),
    )
    return _build(document)


@lru_cache(maxsize=1)
def default_delegation_matrix() -> DelegationMatrix:
    return load_delegation_matrix()
