"""Human Identity JML Lifecycle — joiner, mover, and leaver events.

Detects lifecycle events for human identities by diffing two HRIT snapshots.
Each event produces a set of required governance actions, a resolved OrgPath,
and any drift findings that fire immediately on detection.

Pattern mirrors uiao.governance.ai_inventory.jml (UIAO_197 / ADR-114) applied
to the HRIT canonical HR schema (Spec2-D1.1) rather than the OMB AI inventory.

Key differences from the AI JML module:
- Identity anchor is ``employee_id`` (immutable), not ``omg_id``.
- Joiner trigger: new record OR employment_status PreHire → Active.
- Mover triggers: department, division, worker_type, location_code,
  cost_center, manager_employee_id — the organisational fields that drive
  OrgPath re-resolution and re-routing.
- Leaver triggers: employment_status = Terminated, or termination_date set
  without an Active status (pending-leaver path).
- Every event carries a resolved ``orgpath`` and a ``routing_key`` so the
  ServiceNow ticket creator can populate approver without a second lookup.

Canon reference: UIAO_197 (pattern), Spec2-D1.1 (HR schema),
ADRs 051-054 (HRIT adapters), governance/identity/routing.py (approver lookup).

Actuation tier: L2 (Advise).  This module produces event logs and action
lists; it changes nothing.  Actions marked ``requires_confirmation=True``
require a human to execute them.  The L3 boundary is in
servicenow_ticket.py when ``dry_run=False``.  See UIAO_200.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from uiao.adapters.modernization.hrit.inventory import HRRecord
from uiao.governance.drift_core import Posture, Severity

# ---------------------------------------------------------------------------
# Local finding type (lighter than drift_core.Finding which needs plane/intended/evidence_ref)
# ---------------------------------------------------------------------------


@dataclass
class IdentityFinding:
    """A governance finding emitted by the human JML detector."""

    finding_id: str
    name: str
    drift_class: str
    severity: Severity
    posture: Posture
    observed: str
    control_id: str

    def to_dict(self) -> dict:
        return {
            "finding_id": self.finding_id,
            "name": self.name,
            "drift_class": self.drift_class,
            "severity": self.severity.value,
            "posture": self.posture.value,
            "observed": self.observed,
            "control_id": self.control_id,
        }


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: employment_status values that mark a record as active in the governed population.
_ACTIVE_STATUSES = {"Active", "OnLeave"}

#: employment_status values that confirm a leaver event.
_LEAVER_STATUSES = {"Terminated", "Rescinded"}

#: Fields whose change between snapshots triggers a mover event.
MOVER_TRIGGER_FIELDS: tuple[str, ...] = (
    "department",
    "division",
    "worker_type",
    "location_code",
    "cost_center",
    "manager_employee_id",
)

#: employment_status value for a pre-hire record (triggers joiner when it goes Active).
_PREHIRE_STATUS = "PreHire"


# ---------------------------------------------------------------------------
# Enums and value types
# ---------------------------------------------------------------------------


class HumanJMLEventType(str, Enum):
    JOINER = "identity.joiner"
    MOVER = "identity.mover"
    LEAVER = "identity.leaver"
    PENDING_LEAVER = "identity.pending-leaver"


@dataclass
class JMLAction:
    """One required governance action produced by a JML event."""

    step: str
    description: str
    posture: Posture
    timeline_days: int | None = None
    requires_confirmation: bool = False

    def to_dict(self) -> dict:
        return {
            "step": self.step,
            "description": self.description,
            "posture": self.posture.value,
            "timeline_days": self.timeline_days,
            "requires_confirmation": self.requires_confirmation,
        }


@dataclass
class HumanJMLEvent:
    """One lifecycle event for one human identity."""

    event_type: HumanJMLEventType
    record: HRRecord
    prior_record: HRRecord | None = None
    changed_fields: list[str] = field(default_factory=list)
    actions: list[JMLAction] = field(default_factory=list)
    findings: list[IdentityFinding] = field(default_factory=list)
    pending_leaver: bool = False

    # OrgPath resolution output — set by caller or detect_events when an
    # orgpath_index is supplied.  Carried through to the ticket creator so
    # routing doesn't require a second lookup.
    resolved_orgpath: str | None = None
    routing_key: str | None = None

    @property
    def identity_label(self) -> str:
        return f"{self.record.first_name} {self.record.last_name} ({self.record.employee_id})"

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type.value,
            "identity": self.identity_label,
            "employee_id": self.record.employee_id,
            "department": self.record.department,
            "division": self.record.division,
            "worker_type": self.record.worker_type,
            "employment_status": self.record.employment_status,
            "resolved_orgpath": self.resolved_orgpath,
            "routing_key": self.routing_key,
            "changed_fields": self.changed_fields,
            "pending_leaver": self.pending_leaver,
            "actions": [a.to_dict() for a in self.actions],
            "findings": [f.to_dict() for f in self.findings],
        }


@dataclass
class HumanJMLEventSet:
    """Collection of human JML events from one snapshot diff."""

    joiners: list[HumanJMLEvent] = field(default_factory=list)
    movers: list[HumanJMLEvent] = field(default_factory=list)
    leavers: list[HumanJMLEvent] = field(default_factory=list)
    pending_leavers: list[HumanJMLEvent] = field(default_factory=list)

    @property
    def all_events(self) -> list[HumanJMLEvent]:
        return self.joiners + self.movers + self.leavers + self.pending_leavers

    @property
    def all_findings(self) -> list[IdentityFinding]:
        findings = []
        for ev in self.all_events:
            findings.extend(ev.findings)
        return findings

    def summary(self) -> str:
        return (
            f"Human JML: {len(self.joiners)} joiner(s), {len(self.movers)} mover(s), "
            f"{len(self.leavers)} leaver(s), {len(self.pending_leavers)} pending leaver(s). "
            f"Drift findings: {len(self.all_findings)}."
        )

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(
            {
                "joiners": [e.to_dict() for e in self.joiners],
                "movers": [e.to_dict() for e in self.movers],
                "leavers": [e.to_dict() for e in self.leavers],
                "pending_leavers": [e.to_dict() for e in self.pending_leavers],
            },
            indent=indent,
        )


# ---------------------------------------------------------------------------
# Drift finding constructors
# ---------------------------------------------------------------------------


def _finding_no_orgpath(record: HRRecord, error_code: str) -> IdentityFinding:
    return IdentityFinding(
        finding_id=error_code,
        name="identity-no-orgpath",
        drift_class="DRIFT-IDENTITY",
        severity=Severity.P2,
        posture=Posture.PER_POLICY,
        observed=f"HR record employee_id={record.employee_id!r} department={record.department!r} "
        f"cannot be resolved to a verified OrgPath. Provisioning into Entra requires "
        f"explicit OrgTree codebook assignment (Spec2-D3.2).",
        control_id="GOV-HRIT-NO-ORGPATH",
    )


def _finding_leaver_without_termdate(record: HRRecord, error_code: str) -> IdentityFinding:
    return IdentityFinding(
        finding_id=error_code,
        name="identity-leaver-no-termdate",
        drift_class="DRIFT-PROVENANCE",
        severity=Severity.P2,
        posture=Posture.NEVER_AUTOFIX,
        observed=f"HR record employee_id={record.employee_id!r} has employment_status=Terminated "
        f"but no termination_date recorded. Deprovisioning timeline cannot be computed.",
        control_id="GOV-HRIT-NO-TERMDATE",
    )


# ---------------------------------------------------------------------------
# Action constructors
# ---------------------------------------------------------------------------


def _joiner_actions(record: HRRecord, has_orgpath: bool) -> list[JMLAction]:
    actions = [
        JMLAction(
            step="J-1",
            description="Resolve OrgPath from HR record and stamp principal in Entra extensionAttributes",
            posture=Posture.PER_POLICY,
        ),
        JMLAction(
            step="J-2",
            description="Create Entra account and assign to OrgPath Administrative Unit",
            posture=Posture.NEVER_AUTOFIX,
            requires_confirmation=True,
            timeline_days=1,
        ),
        JMLAction(
            step="J-3",
            description="Assign manager from manager_employee_id; add to division dynamic group",
            posture=Posture.PER_POLICY,
        ),
        JMLAction(
            step="J-4",
            description="Route onboarding access request to division approver via ServiceNow",
            posture=Posture.PER_POLICY,
            timeline_days=1,
        ),
        JMLAction(
            step="J-5",
            description="Set clearance-appropriate MFA method and conditional access policy tier",
            posture=Posture.NEVER_AUTOFIX,
            requires_confirmation=True,
            timeline_days=3,
        ),
        JMLAction(
            step="J-6",
            description="Enqueue initial access review within 30 days",
            posture=Posture.PER_POLICY,
            timeline_days=30,
        ),
    ]
    if not has_orgpath:
        actions.append(
            JMLAction(
                step="J-7",
                description="DRIFT-IDENTITY — OrgPath unresolved; block Entra provisioning until codebook assigns placement",
                posture=Posture.NEVER_AUTOFIX,
                requires_confirmation=True,
            )
        )
    return actions


def _mover_actions(changed: list[str]) -> list[JMLAction]:
    actions = []
    if "department" in changed or "division" in changed:
        actions.append(
            JMLAction(
                step="M-placement",
                description="Re-resolve OrgPath from new dept/division; update extensionAttributes and AU membership",
                posture=Posture.PER_POLICY,
            )
        )
        actions.append(
            JMLAction(
                step="M-access-review",
                description="Trigger immediate access review — placement change may invalidate prior entitlements",
                posture=Posture.NEVER_AUTOFIX,
                requires_confirmation=True,
                timeline_days=7,
            )
        )
    if "worker_type" in changed:
        actions.append(
            JMLAction(
                step="M-worker-type",
                description="worker_type changed — update account_type tier; re-evaluate MFA and CA policy",
                posture=Posture.NEVER_AUTOFIX,
                requires_confirmation=True,
                timeline_days=1,
            )
        )
    if "manager_employee_id" in changed:
        actions.append(
            JMLAction(
                step="M-manager",
                description="Re-assign Entra manager attribute; update ServiceNow approval routing for open requests",
                posture=Posture.PER_POLICY,
            )
        )
    if "location_code" in changed or "cost_center" in changed:
        actions.append(
            JMLAction(
                step="M-location",
                description="location_code / cost_center changed — verify LocPath and cost owner routing in ServiceNow",
                posture=Posture.PER_POLICY,
            )
        )
    return actions


def _leaver_actions(pending: bool = False) -> list[JMLAction]:
    hold = pending
    return [
        JMLAction(
            step="L-1",
            description="Alert manager and division approver; freeze new permission grants",
            posture=Posture.PER_POLICY,
            timeline_days=0,
        ),
        JMLAction(
            step="L-2",
            description="Disable Entra account (block sign-in); preserve mailbox per retention policy",
            posture=Posture.NEVER_AUTOFIX,
            requires_confirmation=True,
            timeline_days=0,
        ),
        JMLAction(
            step="L-3",
            description="Remove from all dynamic groups and Administrative Units",
            posture=Posture.PER_POLICY,
            timeline_days=1,
            requires_confirmation=hold,
        ),
        JMLAction(
            step="L-4",
            description="Revoke active sessions and OAuth refresh tokens",
            posture=Posture.NEVER_AUTOFIX,
            requires_confirmation=True,
            timeline_days=1,
        ),
        JMLAction(
            step="L-5",
            description="Transfer owned resources (SharePoint, OneDrive, service accounts) to new owner",
            posture=Posture.NEVER_AUTOFIX,
            requires_confirmation=True,
            timeline_days=14,
        ),
        JMLAction(
            step="L-6",
            description="Delete or archive Entra account per data-retention policy",
            posture=Posture.NEVER_AUTOFIX,
            requires_confirmation=True,
            timeline_days=30,
        ),
        JMLAction(
            step="L-7",
            description="Archive OrgPath record and emit closed-loop evidence to UIAO evidence fabric",
            posture=Posture.PER_POLICY,
            timeline_days=30,
            requires_confirmation=hold,
        ),
    ]


# ---------------------------------------------------------------------------
# Diff helpers
# ---------------------------------------------------------------------------


def _is_active(record: HRRecord) -> bool:
    return record.employment_status in _ACTIVE_STATUSES


def _is_leaver(record: HRRecord) -> bool:
    return record.employment_status in _LEAVER_STATUSES


def _is_pending_leaver(record: HRRecord) -> bool:
    """termination_date set but status not yet Terminated (advance notice window)."""
    return bool(record.termination_date) and record.employment_status not in _LEAVER_STATUSES


def _diff_fields(current: HRRecord, prior: HRRecord) -> list[str]:
    changed = []
    for f in MOVER_TRIGGER_FIELDS:
        if getattr(current, f) != getattr(prior, f):
            changed.append(f)
    return changed


def _resolve_orgpath(record: HRRecord, orgpath_index: dict[str, str] | None) -> str | None:
    if not orgpath_index:
        return record.resolved_orgpath
    for key in (record.organization_code, record.division, record.department, record.cost_center):
        if key and key in orgpath_index:
            return orgpath_index[key]
    return record.resolved_orgpath


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_events(
    current_snapshot: list[HRRecord],
    prior_snapshot: list[HRRecord] | None = None,
    *,
    orgpath_index: dict[str, str] | None = None,
) -> HumanJMLEventSet:
    """Diff two HRIT snapshots and return the full human JML event set.

    Parameters
    ----------
    current_snapshot:
        HR records from the current extract (most recent HRIT pull).
    prior_snapshot:
        HR records from the previous extract.  When None, every active
        record in ``current_snapshot`` is treated as a joiner.
    orgpath_index:
        Optional lookup dict keyed by organization_code / division /
        department / cost_center (first hit wins, per Spec2-D1.3).
        When provided, OrgPath is re-resolved here and stamped on each
        event; routing.py uses the resolved value to pick the approver.

    Returns
    -------
    HumanJMLEventSet
    """
    result = HumanJMLEventSet()
    finding_counter = 0

    prior_by_id: dict[str, HRRecord] = {r.employee_id: r for r in prior_snapshot} if prior_snapshot is not None else {}
    current_by_id: dict[str, HRRecord] = {r.employee_id: r for r in current_snapshot}

    # --- Pass 1: joiners, movers, leavers, pending leavers (current vintage) ---
    for record in current_snapshot:
        prior = prior_by_id.get(record.employee_id)
        orgpath = _resolve_orgpath(record, orgpath_index)
        has_orgpath = orgpath is not None

        # Pending leaver (advance-notice: termination_date set, still Active)
        if _is_pending_leaver(record):
            ev = HumanJMLEvent(
                event_type=HumanJMLEventType.PENDING_LEAVER,
                record=record,
                prior_record=prior,
                actions=_leaver_actions(pending=True),
                resolved_orgpath=orgpath,
                pending_leaver=True,
            )
            result.pending_leavers.append(ev)
            continue

        # Confirmed leaver
        if _is_leaver(record):
            findings = []
            if not record.termination_date:
                finding_counter += 1
                findings.append(_finding_leaver_without_termdate(record, f"GOV-HRIT-{finding_counter:04d}"))
            ev = HumanJMLEvent(
                event_type=HumanJMLEventType.LEAVER,
                record=record,
                prior_record=prior,
                actions=_leaver_actions(pending=False),
                findings=findings,
                resolved_orgpath=orgpath,
            )
            result.leavers.append(ev)
            continue

        if not _is_active(record):
            continue  # PreHire with no prior — not yet in governed population

        if prior is None or prior.employment_status == _PREHIRE_STATUS:
            # New joiner or pre-hire going active
            findings = []
            if not has_orgpath:
                finding_counter += 1
                findings.append(_finding_no_orgpath(record, f"GOV-HRIT-{finding_counter:04d}"))
            ev = HumanJMLEvent(
                event_type=HumanJMLEventType.JOINER,
                record=record,
                prior_record=prior,
                actions=_joiner_actions(record, has_orgpath),
                findings=findings,
                resolved_orgpath=orgpath,
            )
            result.joiners.append(ev)
            continue

        # Mover — check trigger fields
        changed = _diff_fields(record, prior)
        if changed:
            findings = []
            if not has_orgpath and ("department" in changed or "division" in changed):
                finding_counter += 1
                findings.append(_finding_no_orgpath(record, f"GOV-HRIT-{finding_counter:04d}"))
            ev = HumanJMLEvent(
                event_type=HumanJMLEventType.MOVER,
                record=record,
                prior_record=prior,
                changed_fields=changed,
                actions=_mover_actions(changed),
                findings=findings,
                resolved_orgpath=orgpath,
            )
            result.movers.append(ev)

    # --- Pass 2: absent from current but was active (ghost leavers) ----------
    if prior_snapshot is not None:
        for prior_record in prior_snapshot:
            if prior_record.employee_id not in current_by_id and _is_active(prior_record):
                orgpath = _resolve_orgpath(prior_record, orgpath_index)
                ev = HumanJMLEvent(
                    event_type=HumanJMLEventType.PENDING_LEAVER,
                    record=prior_record,
                    prior_record=prior_record,
                    actions=_leaver_actions(pending=True),
                    resolved_orgpath=orgpath,
                    pending_leaver=True,
                )
                result.pending_leavers.append(ev)

    return result


# ---------------------------------------------------------------------------
# Evidence artifact writer
# ---------------------------------------------------------------------------


def write_evidence_artifacts(event_set: HumanJMLEventSet, output_dir: str | Path) -> list[Path]:
    """Write JML event and action logs to *output_dir*.

    Produces:
    - ``human-jml-event-log.json``
    - ``human-jml-action-log.json``
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    event_log = [ev.to_dict() for ev in event_set.all_events]
    event_log_path = out / "human-jml-event-log.json"
    event_log_path.write_text(json.dumps({"events": event_log}, indent=2, ensure_ascii=False), encoding="utf-8")

    action_log = []
    for ev in event_set.all_events:
        for action in ev.actions:
            action_log.append(
                {
                    "identity": ev.identity_label,
                    "employee_id": ev.record.employee_id,
                    "event_type": ev.event_type.value,
                    "resolved_orgpath": ev.resolved_orgpath,
                    **action.to_dict(),
                }
            )
    action_log_path = out / "human-jml-action-log.json"
    action_log_path.write_text(json.dumps({"actions": action_log}, indent=2, ensure_ascii=False), encoding="utf-8")

    return [event_log_path, action_log_path]
