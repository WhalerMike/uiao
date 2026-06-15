"""Entra ID exposure for LocPath — site groups + Administrative Unit scoping (ADR-102 §D6 phase 4).

Derives Entra-consumable plans from the governed location substrate:
one group / Administrative Unit per **Site** (the minimum governance
unit, ADR-102 §D1), with membership read from the Primary-LocPath
assignments produced by
:func:`~uiao.modernization.locpath.hr_assign.assign_locpaths`.

Two membership modes, honoring ADR-102 §D5 (LocPath claims **no**
``extensionAttribute`` slot; storage-on-target rides ADR-098 binding
profiles when it ships):

* **Assigned membership** (default) — members are enumerated from the
  assignment plan by LocPath prefix. Requires no attribute storage at
  all: the governed substrate, not a stamped attribute, is the
  membership source. Graph bodies bind members through an
  ``employee_id → Entra objectId`` mapping supplied at render time
  (identity correlation is the existing substrate concern; this module
  never guesses).
* **Dynamic rule** (optional) — when the deployment *has* chosen a
  storage locator for LocPath (an extension attribute or directory
  extension named by a future binding profile), pass it as ``locator``
  and each spec also carries an Entra dynamic-membership rule of the
  form ``(<locator> -startsWith "/USA/MD/ANNAPOLIS-HQ")``. The locator
  is a parameter, never canon — no slot is claimed here.

Planning is pure (no Graph I/O), mirroring
:mod:`uiao.modernization.orgtree.dynamic_groups` /
:mod:`uiao.modernization.orgtree.admin_units`: specs expose
``to_graph_body()`` and the transport/apply cycle stays with the
existing Entra adapters and operator decisions. Administrative Units
default to **restricted management** per UIAO_154 doctrine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from uiao.modernization.locpath.hr_assign import LocPathAssignmentPlan
from uiao.modernization.locpath.registry import (
    LocationRegistry,
    load_location_registry,
)

#: Naming prefixes, parallel to the OrgTree-* / AU-* conventions.
GROUP_NAME_PREFIX = "LocPath-Site-"
ADMIN_UNIT_NAME_PREFIX = "AU-Site-"


class LocPathExposureError(ValueError):
    """Raised when an Entra exposure plan cannot be built or rendered."""


def _render_prefix_rule(locator: str, loc_path: str) -> str:
    """One Entra dynamic-membership clause: prefix match on the locator."""
    cleaned = locator.strip()
    if not cleaned:
        raise LocPathExposureError("locator must be a non-empty attribute path")
    if '"' in cleaned or '"' in loc_path:
        raise LocPathExposureError("locator and locPath must not contain double quotes")
    return f'({cleaned} -startsWith "{loc_path}")'


def _member_bindings(
    member_employee_ids: tuple[str, ...],
    object_ids: Mapping[str, str],
) -> list[str]:
    unresolved = [emp for emp in member_employee_ids if emp not in object_ids]
    if unresolved:
        raise LocPathExposureError(
            f"no Entra objectId mapping for employee(s): {', '.join(sorted(unresolved))} — "
            "resolve identities before rendering assigned membership"
        )
    return [f"https://graph.microsoft.com/v1.0/directoryObjects/{object_ids[emp]}" for emp in member_employee_ids]


@dataclass(frozen=True)
class LocPathGroupSpec:
    """One Entra group derived from a governed Site (or deeper prefix)."""

    name: str
    description: str
    loc_path: str
    member_employee_ids: tuple[str, ...]
    membership_rule: str | None = None  # present only when a locator was supplied

    def to_graph_body(self, object_ids: Mapping[str, str] | None = None) -> dict[str, object]:
        """Graph ``POST /groups`` body — dynamic when a rule exists, else assigned.

        Assigned mode requires ``object_ids`` (employee_id → Entra
        objectId); every member must resolve or the render fails closed.
        """
        if self.membership_rule is not None:
            return {
                "displayName": self.name,
                "description": self.description,
                "mailEnabled": False,
                "mailNickname": self.name,
                "securityEnabled": True,
                "groupTypes": ["DynamicMembership"],
                "membershipRule": self.membership_rule,
                "membershipRuleProcessingState": "On",
            }
        if object_ids is None:
            raise LocPathExposureError(
                f"group '{self.name}' uses assigned membership — pass object_ids to render members"
            )
        return {
            "displayName": self.name,
            "description": self.description,
            "mailEnabled": False,
            "mailNickname": self.name,
            "securityEnabled": True,
            "groupTypes": [],
            "members@odata.bind": _member_bindings(self.member_employee_ids, object_ids),
        }


@dataclass(frozen=True)
class LocPathAdminUnitSpec:
    """One Entra Administrative Unit scoping a governed Site."""

    name: str
    description: str
    loc_path: str
    member_employee_ids: tuple[str, ...]
    membership_rule: str | None = None
    restricted_management: bool = True  # UIAO_154 doctrine: UIAO-managed AUs are restricted

    def to_graph_body(self) -> dict[str, object]:
        """Graph ``POST /directory/administrativeUnits`` body.

        Members are added per-AU after creation (Graph adds AU members
        via a separate call); dynamic AUs carry the rule inline.
        """
        body: dict[str, object] = {
            "displayName": self.name,
            "description": self.description,
            "isMemberManagementRestricted": self.restricted_management,
        }
        if self.membership_rule is not None:
            body["membershipType"] = "Dynamic"
            body["membershipRule"] = self.membership_rule
            body["membershipRuleProcessingState"] = "On"
        return body

    def member_bindings(self, object_ids: Mapping[str, str]) -> list[str]:
        """Directory-object URLs for the AU member-add calls (assigned mode)."""
        if self.membership_rule is not None:
            raise LocPathExposureError(f"AU '{self.name}' is dynamic — members are rule-managed, not assigned")
        return _member_bindings(self.member_employee_ids, object_ids)


def _site_prefixes(
    plan: LocPathAssignmentPlan,
    registry: LocationRegistry,
    prefixes: Iterable[str] | None,
) -> tuple[str, ...]:
    if prefixes is not None:
        resolved: list[str] = []
        for prefix in prefixes:
            node = registry.node_for(prefix)
            if node is None:
                raise LocPathExposureError(f"prefix '{prefix}' is not in location registry '{registry.registry_id}'")
            resolved.append(node.loc_path)
        return tuple(resolved)
    # Default: every governed Site that has at least one assignment.
    assigned_sites = {a.site_path.lower() for a in plan.assignments}
    return tuple(site.loc_path for site in registry.sites() if site.loc_path.lower() in assigned_sites)


def _members_under(plan: LocPathAssignmentPlan, prefix: str) -> tuple[str, ...]:
    needle = prefix.lower()
    return tuple(
        a.employee_id
        for a in plan.assignments
        if a.loc_path.lower() == needle or a.loc_path.lower().startswith(needle + "/")
    )


def plan_locpath_site_groups(
    plan: LocPathAssignmentPlan,
    registry: LocationRegistry | None = None,
    locator: str | None = None,
    prefixes: Iterable[str] | None = None,
) -> tuple[LocPathGroupSpec, ...]:
    """One group spec per governed Site (or per explicit prefix) — pure, no I/O.

    Default scope is every Site with at least one Primary-LocPath
    assignment in ``plan``. With ``locator`` the specs carry dynamic
    membership rules; without it they carry assigned membership from
    the governed substrate (no attribute storage required).
    """
    reg = registry or load_location_registry()
    specs: list[LocPathGroupSpec] = []
    for prefix in _site_prefixes(plan, reg, prefixes):
        segment = prefix.rsplit("/", 1)[-1]
        specs.append(
            LocPathGroupSpec(
                name=f"{GROUP_NAME_PREFIX}{segment}-Users",
                description=f"All identities whose Primary LocPath is under {prefix} "
                f"(governed by location registry '{reg.registry_id}')",
                loc_path=prefix,
                member_employee_ids=_members_under(plan, prefix),
                membership_rule=_render_prefix_rule(locator, prefix) if locator else None,
            )
        )
    return tuple(specs)


def plan_locpath_admin_units(
    plan: LocPathAssignmentPlan,
    registry: LocationRegistry | None = None,
    locator: str | None = None,
    prefixes: Iterable[str] | None = None,
    restricted_management: bool = True,
) -> tuple[LocPathAdminUnitSpec, ...]:
    """One Administrative Unit spec per governed Site — pure, no I/O.

    Same scoping and membership modes as
    :func:`plan_locpath_site_groups`; AUs default to restricted
    management per UIAO_154 doctrine.
    """
    reg = registry or load_location_registry()
    specs: list[LocPathAdminUnitSpec] = []
    for prefix in _site_prefixes(plan, reg, prefixes):
        segment = prefix.rsplit("/", 1)[-1]
        specs.append(
            LocPathAdminUnitSpec(
                name=f"{ADMIN_UNIT_NAME_PREFIX}{segment}",
                description=f"Administrative Unit scoping identities assigned under {prefix} "
                f"(governed by location registry '{reg.registry_id}')",
                loc_path=prefix,
                member_employee_ids=_members_under(plan, prefix),
                membership_rule=_render_prefix_rule(locator, prefix) if locator else None,
                restricted_management=restricted_management,
            )
        )
    return tuple(specs)
