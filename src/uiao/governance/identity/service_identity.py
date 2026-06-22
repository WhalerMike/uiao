"""Service Identity governance — non-human account lifecycle and orphan detection.

Governs infrastructure service accounts: Entra service principals, managed
identities, legacy service accounts, and automation accounts.  Distinct from:

- uiao.governance.application_identity (UIAO_129) — application binding
  declarations (DNS/IAM/trust bindings); that module names applications as
  first-class primitives. This module governs the *account* that the
  application runs as.
- uiao.governance.ai_inventory.jml — OMB-scoped AI system identities.
- uiao.governance.identity.jml — human identities anchored in HRIT.

The load-bearing governance problem this module solves:

  When a human employee leaves (LEAVER event), any service accounts where
  ``owner_employee_id == leaver.employee_id`` become *orphaned* — running
  with stale credentials and no custodian.  This is the primary audit failure
  pattern in AD→Entra migrations: the human JML fires, the human account is
  disabled, but svc-* principals keep running under a departed owner.

Events detected:
- CREATED  — new service account appears in the principal inventory
- OWNER_CHANGED — owner_employee_id changed between snapshots
- CREDENTIAL_EXPIRY — credential_expiry_date is past or within warning window
- ORPHANED  — owner_employee_id refers to a known LEAVER (or missing from HR)

Canon refs: ADR-092 L3 actuation, UIAO_129 (application identity binding),
governance/identity/jml.py (human JML, leaver events).

Actuation tier: L2 (Advise).  ORPHANED findings are P1 but the system
cannot disable an account or rotate credentials without human execution.
All OR-* actions carry ``requires_confirmation=True``.  See UIAO_200.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from pathlib import Path

from uiao.governance.drift_core import Posture, Severity

# ---------------------------------------------------------------------------
# Credential expiry warning window (days before expiry to raise P2)
# ---------------------------------------------------------------------------

CREDENTIAL_EXPIRY_WARNING_DAYS = 30


# ---------------------------------------------------------------------------
# Local finding type (mirrors governance/identity/jml.IdentityFinding)
# ---------------------------------------------------------------------------


@dataclass
class ServiceFinding:
    """A governance finding emitted by the service identity detector."""

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
# Schema
# ---------------------------------------------------------------------------


@dataclass
class ServiceIdentityRecord:
    """One non-human identity in the governed service account population.

    Covers Entra service principals, managed identities, and legacy service
    accounts. The ``account_class`` field distinguishes them; all are governed
    by the same lifecycle rules.

    The ``owner_employee_id`` is the *human* custodian — the person who is
    accountable for the account's existence and credential rotation. When that
    person leaves, the account becomes a governance orphan.
    """

    # Immutable anchor
    principal_id: str  # Entra object ID, SAM account name, or stable identifier
    display_name: str  # Human-readable name (e.g. "svc-sentinel-ingest")

    # Classification
    account_class: str  # ServicePrincipal | ManagedIdentity | ServiceAccount | AutomationAccount
    department: str  # Owning department (OrgPath facet)
    division: str | None  # Owning division (OrgPath facet)
    cost_center: str | None

    # Custodianship
    owner_employee_id: str | None  # HRIT employee_id of the human custodian
    owner_display_name: str | None  # Denormalized for audit log readability

    # Credential lifecycle
    credential_expiry_date: str | None  # ISO-8601 date; None if managed identity
    last_rotation_date: str | None  # ISO-8601 date; None if never rotated

    # Catalog
    purpose: str | None  # What the account does (human-readable)
    orgpath: str | None  # Resolved OrgPath string
    extracted_at: str  # ISO-8601 UTC timestamp of this record

    # Mutable state
    is_active: bool = True

    def to_dict(self) -> dict:
        return {
            "principal_id": self.principal_id,
            "display_name": self.display_name,
            "account_class": self.account_class,
            "department": self.department,
            "division": self.division,
            "cost_center": self.cost_center,
            "owner_employee_id": self.owner_employee_id,
            "owner_display_name": self.owner_display_name,
            "credential_expiry_date": self.credential_expiry_date,
            "last_rotation_date": self.last_rotation_date,
            "purpose": self.purpose,
            "orgpath": self.orgpath,
            "extracted_at": self.extracted_at,
            "is_active": self.is_active,
        }


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------


class ServiceIdentityEventType(str, Enum):
    CREATED = "service-identity.created"
    OWNER_CHANGED = "service-identity.owner-changed"
    CREDENTIAL_EXPIRY = "service-identity.credential-expiry"
    ORPHANED = "service-identity.orphaned"


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


@dataclass
class ServiceAction:
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


# ---------------------------------------------------------------------------
# Event
# ---------------------------------------------------------------------------


@dataclass
class ServiceIdentityEvent:
    event_type: ServiceIdentityEventType
    record: ServiceIdentityRecord
    prior_record: ServiceIdentityRecord | None = None
    changed_fields: list[str] = field(default_factory=list)
    actions: list[ServiceAction] = field(default_factory=list)
    findings: list[ServiceFinding] = field(default_factory=list)
    orphaned_by_employee_id: str | None = None  # LEAVER employee_id that triggered orphan

    @property
    def identity_label(self) -> str:
        return f"{self.record.display_name} ({self.record.principal_id})"

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type.value,
            "principal_id": self.record.principal_id,
            "display_name": self.record.display_name,
            "account_class": self.record.account_class,
            "owner_employee_id": self.record.owner_employee_id,
            "orgpath": self.record.orgpath,
            "orphaned_by_employee_id": self.orphaned_by_employee_id,
            "changed_fields": self.changed_fields,
            "actions": [a.to_dict() for a in self.actions],
            "findings": [f.to_dict() for f in self.findings],
        }


@dataclass
class ServiceIdentityEventSet:
    created: list[ServiceIdentityEvent] = field(default_factory=list)
    owner_changed: list[ServiceIdentityEvent] = field(default_factory=list)
    expiring: list[ServiceIdentityEvent] = field(default_factory=list)
    orphaned: list[ServiceIdentityEvent] = field(default_factory=list)

    @property
    def all_events(self) -> list[ServiceIdentityEvent]:
        return self.created + self.owner_changed + self.expiring + self.orphaned

    @property
    def all_findings(self) -> list[ServiceFinding]:
        findings = []
        for ev in self.all_events:
            findings.extend(ev.findings)
        return findings

    def summary(self) -> str:
        return (
            f"Service identity: {len(self.created)} created, "
            f"{len(self.owner_changed)} owner changed, "
            f"{len(self.expiring)} expiring, "
            f"{len(self.orphaned)} orphaned. "
            f"Findings: {len(self.all_findings)}."
        )

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(
            {
                "created": [e.to_dict() for e in self.created],
                "owner_changed": [e.to_dict() for e in self.owner_changed],
                "expiring": [e.to_dict() for e in self.expiring],
                "orphaned": [e.to_dict() for e in self.orphaned],
            },
            indent=indent,
        )


# ---------------------------------------------------------------------------
# Finding constructors
# ---------------------------------------------------------------------------

_counter = 0


def _next_id(prefix: str = "GOV-SVC") -> str:
    global _counter
    _counter += 1
    return f"{prefix}-{_counter:04d}"


def _finding_orphan(record: ServiceIdentityRecord, leaver_id: str) -> ServiceFinding:
    return ServiceFinding(
        finding_id=_next_id(),
        name="service-identity-orphaned",
        drift_class="DRIFT-ORPHAN-NHAM",
        severity=Severity.P1,
        posture=Posture.NEVER_AUTOFIX,
        observed=(
            f"Service account {record.display_name!r} (principal_id={record.principal_id!r}) "
            f"is owned by departed employee {leaver_id!r}. "
            f"Account is now ungoverned: no human custodian holds accountability."
        ),
        control_id="GOV-SVC-ORPHAN",
    )


def _finding_credential_expiry(record: ServiceIdentityRecord, days_until_expiry: int) -> ServiceFinding:
    severity = Severity.P1 if days_until_expiry <= 0 else Severity.P2
    observed = (
        f"Service account {record.display_name!r} credential expired {abs(days_until_expiry)} days ago."
        if days_until_expiry <= 0
        else f"Service account {record.display_name!r} credential expires in {days_until_expiry} days."
    )
    return ServiceFinding(
        finding_id=_next_id(),
        name="service-identity-credential-expiry",
        drift_class="DRIFT-PROVENANCE",
        severity=severity,
        posture=Posture.NEVER_AUTOFIX,
        observed=observed,
        control_id="GOV-SVC-CRED-EXPIRY",
    )


def _finding_no_owner(record: ServiceIdentityRecord) -> ServiceFinding:
    return ServiceFinding(
        finding_id=_next_id(),
        name="service-identity-no-owner",
        drift_class="DRIFT-ORPHAN-NHAM",
        severity=Severity.P2,
        posture=Posture.NEVER_AUTOFIX,
        observed=(
            f"Service account {record.display_name!r} has no owner_employee_id. "
            f"A human custodian must be assigned before this account can be governed."
        ),
        control_id="GOV-SVC-NO-OWNER",
    )


# ---------------------------------------------------------------------------
# Action constructors
# ---------------------------------------------------------------------------


def _created_actions(record: ServiceIdentityRecord) -> list[ServiceAction]:
    actions = [
        ServiceAction(
            step="SC-1",
            description="Register service account in UIAO service identity catalog",
            posture=Posture.PER_POLICY,
        ),
        ServiceAction(
            step="SC-2",
            description="Assign human custodian (owner_employee_id) and confirm acceptance",
            posture=Posture.NEVER_AUTOFIX,
            requires_confirmation=True,
            timeline_days=3,
        ),
        ServiceAction(
            step="SC-3",
            description="Resolve and stamp OrgPath from owning department/division",
            posture=Posture.PER_POLICY,
        ),
        ServiceAction(
            step="SC-4",
            description="Set credential rotation schedule and record expiry date",
            posture=Posture.NEVER_AUTOFIX,
            requires_confirmation=True,
            timeline_days=7,
        ),
        ServiceAction(
            step="SC-5",
            description="Add to quarterly access review campaign as non-human principal",
            posture=Posture.PER_POLICY,
            timeline_days=30,
        ),
    ]
    if not record.owner_employee_id:
        actions.append(
            ServiceAction(
                step="SC-6",
                description="DRIFT-ORPHAN-NHAM — no owner; block use until custodian assigned",
                posture=Posture.NEVER_AUTOFIX,
                requires_confirmation=True,
            )
        )
    return actions


def _orphan_actions() -> list[ServiceAction]:
    return [
        ServiceAction(
            step="OR-1",
            description="IMMEDIATE: identify a replacement custodian for this service account",
            posture=Posture.NEVER_AUTOFIX,
            requires_confirmation=True,
            timeline_days=1,
        ),
        ServiceAction(
            step="OR-2",
            description="If no replacement found within 24 hours: disable the service account",
            posture=Posture.NEVER_AUTOFIX,
            requires_confirmation=True,
            timeline_days=1,
        ),
        ServiceAction(
            step="OR-3",
            description="Rotate credentials immediately — departed owner may retain knowledge of them",
            posture=Posture.NEVER_AUTOFIX,
            requires_confirmation=True,
            timeline_days=0,
        ),
        ServiceAction(
            step="OR-4",
            description="Audit recent activity of this service account since departure date",
            posture=Posture.PER_POLICY,
            timeline_days=3,
        ),
        ServiceAction(
            step="OR-5",
            description="Update service identity catalog with new custodian once assigned",
            posture=Posture.PER_POLICY,
        ),
    ]


def _expiry_actions(days_until_expiry: int) -> list[ServiceAction]:
    urgent = days_until_expiry <= 0
    return [
        ServiceAction(
            step="CE-1",
            description="Rotate service account credential immediately"
            if urgent
            else f"Schedule credential rotation (expires in {days_until_expiry} days)",
            posture=Posture.NEVER_AUTOFIX,
            requires_confirmation=True,
            timeline_days=0 if urgent else min(days_until_expiry, 14),
        ),
        ServiceAction(
            step="CE-2",
            description="Update credential_expiry_date in service identity catalog after rotation",
            posture=Posture.PER_POLICY,
        ),
        ServiceAction(
            step="CE-3",
            description="Notify service owner and document rotation in evidence fabric",
            posture=Posture.PER_POLICY,
        ),
    ]


def _owner_changed_actions() -> list[ServiceAction]:
    return [
        ServiceAction(
            step="OC-1",
            description="Confirm new custodian acceptance of ownership responsibility",
            posture=Posture.NEVER_AUTOFIX,
            requires_confirmation=True,
            timeline_days=1,
        ),
        ServiceAction(
            step="OC-2",
            description="Rotate credentials — prior custodian may retain knowledge of them",
            posture=Posture.NEVER_AUTOFIX,
            requires_confirmation=True,
            timeline_days=3,
        ),
        ServiceAction(
            step="OC-3",
            description="Update service identity catalog and OrgPath to reflect new owner's placement",
            posture=Posture.PER_POLICY,
        ),
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_service_events(
    current_snapshot: list[ServiceIdentityRecord],
    prior_snapshot: list[ServiceIdentityRecord] | None = None,
    *,
    leaver_employee_ids: set[str] | None = None,
    reference_date: date | None = None,
) -> ServiceIdentityEventSet:
    """Detect lifecycle events across a service identity snapshot.

    Parameters
    ----------
    current_snapshot:
        Service identity records from the current extract.
    prior_snapshot:
        Records from the previous extract; new records → CREATED events.
    leaver_employee_ids:
        Set of employee_ids from the current human JML run whose
        employment_status is Terminated/Rescinded.  Any service account
        owned by a leaver gets an ORPHANED event immediately.
    reference_date:
        Date to use for credential expiry calculation.  Defaults to today.
        Pass explicitly in tests to get deterministic results.

    Returns
    -------
    ServiceIdentityEventSet
    """
    result = ServiceIdentityEventSet()
    leavers = leaver_employee_ids or set()
    today = reference_date or date.today()

    prior_by_id: dict[str, ServiceIdentityRecord] = (
        {r.principal_id: r for r in prior_snapshot} if prior_snapshot is not None else {}
    )

    for record in current_snapshot:
        if not record.is_active:
            continue

        prior = prior_by_id.get(record.principal_id)

        # --- ORPHANED: owner is a leaver ---
        if record.owner_employee_id and record.owner_employee_id in leavers:
            finding = _finding_orphan(record, record.owner_employee_id)
            ev = ServiceIdentityEvent(
                event_type=ServiceIdentityEventType.ORPHANED,
                record=record,
                prior_record=prior,
                actions=_orphan_actions(),
                findings=[finding],
                orphaned_by_employee_id=record.owner_employee_id,
            )
            result.orphaned.append(ev)
            continue  # orphan takes precedence; other events fire on next snapshot

        # --- CREATED: present now, absent before ---
        if prior is None:
            findings = []
            if not record.owner_employee_id:
                findings.append(_finding_no_owner(record))
            ev = ServiceIdentityEvent(
                event_type=ServiceIdentityEventType.CREATED,
                record=record,
                actions=_created_actions(record),
                findings=findings,
            )
            result.created.append(ev)

        # --- OWNER_CHANGED ---
        elif prior.owner_employee_id != record.owner_employee_id:
            ev = ServiceIdentityEvent(
                event_type=ServiceIdentityEventType.OWNER_CHANGED,
                record=record,
                prior_record=prior,
                changed_fields=["owner_employee_id"],
                actions=_owner_changed_actions(),
            )
            result.owner_changed.append(ev)

        # --- CREDENTIAL_EXPIRY ---
        if record.credential_expiry_date:
            try:
                expiry = date.fromisoformat(record.credential_expiry_date)
                days_until = (expiry - today).days
                if days_until <= CREDENTIAL_EXPIRY_WARNING_DAYS:
                    finding = _finding_credential_expiry(record, days_until)
                    ev = ServiceIdentityEvent(
                        event_type=ServiceIdentityEventType.CREDENTIAL_EXPIRY,
                        record=record,
                        prior_record=prior,
                        actions=_expiry_actions(days_until),
                        findings=[finding],
                    )
                    result.expiring.append(ev)
            except ValueError:
                pass  # malformed date; schema validation catches this elsewhere

    return result


def detect_orphans_from_leavers(
    service_snapshot: list[ServiceIdentityRecord],
    leaver_employee_ids: set[str],
) -> ServiceIdentityEventSet:
    """Convenience wrapper: scan for orphans triggered by a human JML run.

    Intended to be called from the same orchestration layer that runs
    governance/identity/jml.py's detect_events().  Pass the employee_ids
    of all LEAVER events from that run; this returns orphaned service accounts.
    """
    return detect_service_events(
        service_snapshot,
        leaver_employee_ids=leaver_employee_ids,
    )


# ---------------------------------------------------------------------------
# Evidence artifacts
# ---------------------------------------------------------------------------


def write_evidence_artifacts(event_set: ServiceIdentityEventSet, output_dir: str | Path) -> list[Path]:
    """Write service identity event and action logs to *output_dir*."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    event_log = [ev.to_dict() for ev in event_set.all_events]
    event_log_path = out / "service-identity-event-log.json"
    event_log_path.write_text(
        json.dumps({"events": event_log}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    action_log = []
    for ev in event_set.all_events:
        for action in ev.actions:
            action_log.append(
                {
                    "principal_id": ev.record.principal_id,
                    "display_name": ev.record.display_name,
                    "event_type": ev.event_type.value,
                    "orgpath": ev.record.orgpath,
                    **action.to_dict(),
                }
            )
    action_log_path = out / "service-identity-action-log.json"
    action_log_path.write_text(
        json.dumps({"actions": action_log}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return [event_log_path, action_log_path]
