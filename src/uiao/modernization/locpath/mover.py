"""Location Mover pass — duty-station change recalculation + impact analysis (ADR-102 §D6 phase 3).

Per ADR-102 §D6, a duty-station change triggers Primary-LocPath
recalculation and impact analysis — the place counterpart to the OrgPath
Mover workflow. This module is that pass, read-only and dry-run by
nature: it diffs two :class:`~uiao.modernization.locpath.hr_assign.LocPathAssignmentPlan`
states (the recorded substrate state vs the fresh HR derivation, or any
earlier-vs-later pair) and produces

* :class:`MoverEvent` records — one per identity whose assigned place
  changed (``move``), appeared (``join``), or disappeared (``leave``) —
  each carrying the **impact surfaces** that must recalculate, and
* ``DRIFT-IDENTITY::location-assignment`` findings — every event *is*
  assignment drift until the downstream surfaces reconcile (the
  UIAO_163 Snapshot → Compare → Classify framing applied to place).

Impact surfaces are declarative names, not calls: the dynamic-group and
Administrative Unit write surfaces are ADR-102 §D6 phase 4, and the
E911 registered-address update belongs to the UCaaS platform consuming
the location of record. The Mover pass tells you *what is now stale*;
it never mutates anything.
"""

from __future__ import annotations

from dataclasses import dataclass

from uiao.adapters.modernization.hrit.inventory import DriftFinding
from uiao.modernization.locpath.drift import DRIFT_LOCATION_ASSIGNMENT, ERROR_STALE_ASSIGNMENT
from uiao.modernization.locpath.hr_assign import LocPathAssignment, LocPathAssignmentPlan
from uiao.modernization.locpath.registry import (
    LocationNode,
    LocationRegistry,
    load_location_registry,
)

#: Impact surfaces a location change can stale (declarative — phase 4 owns the writes).
IMPACT_E911 = "e911-dispatchable-location"
IMPACT_DYNAMIC_GROUPS = "dynamic-groups"
IMPACT_ADMIN_UNITS = "administrative-units"
IMPACT_TELEMETRY_BOUNDARY = "telemetry-boundary-transition"
IMPACT_SERVICE_ACCESS_BOUNDARY = "service-access-boundary-transition"
IMPACT_DIA_TRANSITION = "dia-approval-transition"

#: Event kinds.
KIND_JOIN = "join"
KIND_LEAVE = "leave"
KIND_MOVE = "move"


@dataclass(frozen=True)
class MoverEvent:
    """One identity's location change, with the surfaces it stales."""

    employee_id: str
    kind: str  # join | leave | move
    previous_loc_path: str | None
    new_loc_path: str | None
    previous_site: str | None
    new_site: str | None
    site_changed: bool
    impacts: tuple[str, ...]


@dataclass(frozen=True)
class LocationMoverPlan:
    """The read-only output of one Mover pass: events + their drift findings."""

    events: tuple[MoverEvent, ...]
    findings: tuple[DriftFinding, ...]

    def movers(self) -> tuple[MoverEvent, ...]:
        return tuple(e for e in self.events if e.kind == KIND_MOVE)

    def joiners(self) -> tuple[MoverEvent, ...]:
        return tuple(e for e in self.events if e.kind == KIND_JOIN)

    def leavers(self) -> tuple[MoverEvent, ...]:
        return tuple(e for e in self.events if e.kind == KIND_LEAVE)


def _site_node(registry: LocationRegistry, site_path: str | None) -> LocationNode | None:
    if site_path is None:
        return None
    return registry.node_for(site_path)


def _boundary_transition_impacts(
    registry: LocationRegistry,
    previous_site: str | None,
    new_site: str | None,
) -> tuple[str, ...]:
    """Site-classification deltas a cross-site move transits."""
    old = _site_node(registry, previous_site)
    new = _site_node(registry, new_site)
    if old is None or new is None:
        return ()
    impacts: list[str] = []
    if old.boundaries.get("telemetryBoundary") != new.boundaries.get("telemetryBoundary"):
        impacts.append(IMPACT_TELEMETRY_BOUNDARY)
    if old.boundaries.get("serviceAccessBoundary") != new.boundaries.get("serviceAccessBoundary"):
        impacts.append(IMPACT_SERVICE_ACCESS_BOUNDARY)
    if old.network.get("diaApproved") != new.network.get("diaApproved"):
        impacts.append(IMPACT_DIA_TRANSITION)
    return tuple(impacts)


def _event_impacts(
    registry: LocationRegistry,
    kind: str,
    previous: LocPathAssignment | None,
    new: LocPathAssignment | None,
    site_changed: bool,
) -> tuple[str, ...]:
    impacts: list[str] = [IMPACT_E911]  # the location of record changed in every event kind
    if kind in (KIND_JOIN, KIND_LEAVE) or site_changed:
        impacts.append(IMPACT_DYNAMIC_GROUPS)
        impacts.append(IMPACT_ADMIN_UNITS)
    if kind == KIND_MOVE and site_changed:
        impacts.extend(
            _boundary_transition_impacts(
                registry,
                previous.site_path if previous else None,
                new.site_path if new else None,
            )
        )
    return tuple(impacts)


def _finding_for(event: MoverEvent) -> DriftFinding:
    transitions = {
        KIND_JOIN: f"no recorded assignment → '{event.new_loc_path}'",
        KIND_LEAVE: f"'{event.previous_loc_path}' → no derived assignment",
        KIND_MOVE: f"'{event.previous_loc_path}' → '{event.new_loc_path}'",
    }
    severity = "P2" if event.site_changed or event.kind != KIND_MOVE else "P3"
    return DriftFinding(
        drift_class=DRIFT_LOCATION_ASSIGNMENT,
        severity=severity,
        path=event.employee_id,
        detail=f"recorded Primary LocPath is stale: {transitions[event.kind]}; "
        f"stale surfaces: {', '.join(event.impacts)}",
        error_code=ERROR_STALE_ASSIGNMENT,
        object_type="HRRecord",
    )


def plan_location_moves(
    previous: LocPathAssignmentPlan,
    current: LocPathAssignmentPlan,
    registry: LocationRegistry | None = None,
) -> LocationMoverPlan:
    """Diff two assignment states into Mover events + assignment-drift findings.

    ``previous`` is the recorded state (the substrate's last snapshot);
    ``current`` is the fresh HR derivation from
    :func:`~uiao.modernization.locpath.hr_assign.assign_locpaths`.
    Identities whose assignment is unchanged (case-insensitive LocPath
    equality) produce nothing. Read-only.
    """
    reg = registry or load_location_registry()
    before = {a.employee_id: a for a in previous.assignments}
    after = {a.employee_id: a for a in current.assignments}

    events: list[MoverEvent] = []

    for employee_id, new in after.items():
        old = before.get(employee_id)
        if old is None:
            kind, site_changed = KIND_JOIN, True
        elif old.loc_path.lower() == new.loc_path.lower():
            continue
        else:
            kind = KIND_MOVE
            site_changed = old.site_path.lower() != new.site_path.lower()
        events.append(
            MoverEvent(
                employee_id=employee_id,
                kind=kind,
                previous_loc_path=old.loc_path if old else None,
                new_loc_path=new.loc_path,
                previous_site=old.site_path if old else None,
                new_site=new.site_path,
                site_changed=site_changed,
                impacts=_event_impacts(reg, kind, old, new, site_changed),
            )
        )

    for employee_id, old in before.items():
        if employee_id in after:
            continue
        events.append(
            MoverEvent(
                employee_id=employee_id,
                kind=KIND_LEAVE,
                previous_loc_path=old.loc_path,
                new_loc_path=None,
                previous_site=old.site_path,
                new_site=None,
                site_changed=True,
                impacts=_event_impacts(reg, KIND_LEAVE, old, None, True),
            )
        )

    return LocationMoverPlan(
        events=tuple(events),
        findings=tuple(_finding_for(e) for e in events),
    )
