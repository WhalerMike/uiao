"""AI System JML Lifecycle — joiner, mover, and leaver events.

Detects lifecycle events for federal AI system identities by diffing two
OMB inventory vintages.  Each event produces a set of required governance
actions and any drift findings that fire immediately on detection.

Canon reference: UIAO_197, ADR-114
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from uiao.governance.ai_inventory.drift import (
    finding_agentic_ungoverned,
    finding_no_orgpath,
    finding_staleness,
)
from uiao.governance.ai_inventory.schema import AgentClass, ATOStatus, DevStage
from uiao.governance.drift_core import Finding, Posture

if TYPE_CHECKING:
    from uiao.governance.ai_inventory.schema import AISystemRecord

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Fields whose change between vintages triggers a mover event.
MOVER_TRIGGER_FIELDS: tuple[str, ...] = (
    "contact_email",
    "agency_bureau",
    "agent_class",
    "is_high_impact",
    "ato_status",
    "development_stage",
)

#: Days of inactivity (no mover event detected) that trigger ai-staleness.
STALENESS_THRESHOLD_DAYS = 365

#: Stage values that place a system in the governed (live) population.
_LIVE_STAGES = {DevStage.PILOT, DevStage.DEPLOYED}

#: Stage values that trigger a confirmed leaver event.
_LEAVER_STAGES = {DevStage.RETIRED}

#: Days a system can sit in PAUSED before being treated as a candidate leaver.
PAUSED_LEAVER_THRESHOLD_DAYS = 90


# ---------------------------------------------------------------------------
# Enums and value types
# ---------------------------------------------------------------------------


class JMLEventType(str, Enum):
    JOINER = "ai-system.joiner"
    MOVER = "ai-system.mover"
    LEAVER = "ai-system.leaver"
    CANDIDATE_LEAVER = "ai-system.candidate-leaver"


@dataclass
class JMLAction:
    """One required governance action produced by a JML event."""

    step: str
    """Step code — J-1…J-8, M-{field}, L-1…L-8."""

    description: str
    """Human-readable action description."""

    posture: Posture
    """PER_POLICY (may execute automatically) or NEVER_AUTOFIX (human required)."""

    timeline_days: int | None = None
    """Days from event detection before the action must complete (leaver only)."""

    requires_confirmation: bool = False
    """True when posture is NEVER_AUTOFIX."""

    def to_dict(self) -> dict:
        return {
            "step": self.step,
            "description": self.description,
            "posture": self.posture.value,
            "timeline_days": self.timeline_days,
            "requires_confirmation": self.requires_confirmation,
        }


@dataclass
class JMLEvent:
    """One lifecycle event for one AI system identity."""

    event_type: JMLEventType
    record: AISystemRecord
    """Current-vintage record."""

    prior_record: AISystemRecord | None = None
    """Prior-vintage record — None for joiners."""

    changed_fields: list[str] = field(default_factory=list)
    """Fields that changed between vintages (mover only)."""

    actions: list[JMLAction] = field(default_factory=list)
    """Required governance actions for this event."""

    findings: list[Finding] = field(default_factory=list)
    """Drift findings emitted immediately on event detection."""

    candidate_leaver: bool = False
    """True when the system is absent from the current vintage without
    an explicit retired stage entry.  Steps L-3..L-8 are held pending
    human confirmation."""

    @property
    def system_label(self) -> str:
        return self.record.identity_label

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type.value,
            "system": self.system_label,
            "omg_id": self.record.omg_id,
            "changed_fields": self.changed_fields,
            "candidate_leaver": self.candidate_leaver,
            "actions": [a.to_dict() for a in self.actions],
            "findings": [
                {
                    "finding_id": f.finding_id,
                    "drift_class": f.drift_class,
                    "severity": f.severity.value,
                }
                for f in self.findings
            ],
        }


@dataclass
class JMLEventSet:
    """Collection of JML events from one vintage diff."""

    joiners: list[JMLEvent] = field(default_factory=list)
    movers: list[JMLEvent] = field(default_factory=list)
    leavers: list[JMLEvent] = field(default_factory=list)
    candidate_leavers: list[JMLEvent] = field(default_factory=list)
    staleness_findings: list[Finding] = field(default_factory=list)

    @property
    def all_events(self) -> list[JMLEvent]:
        return self.joiners + self.movers + self.leavers + self.candidate_leavers

    @property
    def all_findings(self) -> list[Finding]:
        fs = []
        for ev in self.all_events:
            fs.extend(ev.findings)
        fs.extend(self.staleness_findings)
        return fs

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(
            {
                "joiners": [e.to_dict() for e in self.joiners],
                "movers": [e.to_dict() for e in self.movers],
                "leavers": [e.to_dict() for e in self.leavers],
                "candidate_leavers": [e.to_dict() for e in self.candidate_leavers],
                "staleness_findings": [
                    {"finding_id": f.finding_id, "drift_class": f.drift_class, "name": f.name}
                    for f in self.staleness_findings
                ],
            },
            indent=indent,
        )

    def summary(self) -> str:
        lines = [
            f"JML events: {len(self.joiners)} joiner(s), {len(self.movers)} mover(s), "
            f"{len(self.leavers)} leaver(s), {len(self.candidate_leavers)} candidate leaver(s)",
            f"Staleness findings: {len(self.staleness_findings)}",
            f"Total drift findings: {len(self.all_findings)}",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Action constructors
# ---------------------------------------------------------------------------


def _joiner_actions(record: AISystemRecord) -> tuple[list[JMLAction], list[Finding]]:
    actions: list[JMLAction] = [
        JMLAction(
            step="J-1",
            description="Derive OrgPath from agency + agency_bureau and stamp AISystemRecord",
            posture=Posture.PER_POLICY,
        ),
        JMLAction(
            step="J-2",
            description="Stamp AISystemRecord in the machine-identity surface",
            posture=Posture.PER_POLICY,
        ),
        JMLAction(
            step="J-3",
            description="Assign bureau governance contact as credential owner (from contact_email)",
            posture=Posture.NEVER_AUTOFIX,
            requires_confirmation=True,
        ),
        JMLAction(
            step="J-4",
            description="Set credential rotation schedule per bureau OrgPath tier",
            posture=Posture.PER_POLICY,
        ),
        JMLAction(
            step="J-5",
            description="Create credential lifecycle entry in IGA platform",
            posture=Posture.PER_POLICY,
        ),
        JMLAction(
            step="J-6",
            description="Enqueue initial access review within 30 days",
            posture=Posture.PER_POLICY,
            timeline_days=30,
        ),
    ]

    findings: list[Finding] = []

    # J-7: agentic without ATO
    if record.agent_class == AgentClass.AGENTIC and record.ato_status != ATOStatus.YES:
        actions.append(
            JMLAction(
                step="J-7",
                description=(
                    f"DRIFT-COMPLIANCE::ai-agentic-ungoverned detected — "
                    f"agentic system {record.identity_label} has no ATO"
                ),
                posture=Posture.NEVER_AUTOFIX,
                requires_confirmation=True,
            )
        )
        findings.append(finding_agentic_ungoverned(record))

    # J-8: no OrgPath
    if record.orgpath is None:
        actions.append(
            JMLAction(
                step="J-8",
                description=(
                    f"DRIFT-IDENTITY::ai-no-orgpath — OrgPath cannot be derived; "
                    f"agency_bureau is blank for {record.identity_label}"
                ),
                posture=Posture.PER_POLICY,
            )
        )
        findings.append(finding_no_orgpath(record))

    return actions, findings


def _mover_actions(
    record: AISystemRecord,
    prior: AISystemRecord,
    changed: list[str],
) -> tuple[list[JMLAction], list[Finding]]:
    actions: list[JMLAction] = []
    findings: list[Finding] = []

    if "agency_bureau" in changed:
        actions.append(
            JMLAction(
                step="M-agency_bureau",
                description=(
                    f"Re-derive OrgPath from new agency_bureau={record.agency_bureau!r}; "
                    f"notify prior and new bureau governance contacts"
                ),
                posture=Posture.PER_POLICY,
            )
        )
        if record.orgpath is None:
            findings.append(finding_no_orgpath(record))

    if "contact_email" in changed:
        actions.append(
            JMLAction(
                step="M-contact_email",
                description=(
                    f"Re-assign IGA credential owner to new contact {record.contact_email!r}; notify prior owner"
                ),
                posture=Posture.NEVER_AUTOFIX,
                requires_confirmation=True,
            )
        )

    if "agent_class" in changed and record.agent_class == AgentClass.AGENTIC:
        actions.append(
            JMLAction(
                step="M-agent_class",
                description=(
                    "agent_class changed to AGENTIC — escalate to P1 governance path; "
                    "require declared governance mode (L1 minimum per ADR-092 §4)"
                ),
                posture=Posture.NEVER_AUTOFIX,
                requires_confirmation=True,
            )
        )
        if record.ato_status != ATOStatus.YES:
            findings.append(finding_agentic_ungoverned(record))

    if "is_high_impact" in changed and record.is_high_impact and not prior.is_high_impact:
        actions.append(
            JMLAction(
                step="M-is_high_impact",
                description=(
                    "is_high_impact newly True — elevate credential tier; "
                    "accelerate rotation to privileged-service-account schedule; "
                    "trigger immediate access review"
                ),
                posture=Posture.PER_POLICY,
            )
        )

    if "ato_status" in changed:
        if record.ato_status == ATOStatus.NO:
            actions.append(
                JMLAction(
                    step="M-ato_status-gap",
                    description="ato_status changed to NO — emit DRIFT-COMPLIANCE::ai-ato-gap",
                    posture=Posture.NEVER_AUTOFIX,
                    requires_confirmation=True,
                )
            )
        elif record.ato_status == ATOStatus.YES and prior.ato_status != ATOStatus.YES:
            actions.append(
                JMLAction(
                    step="M-ato_status-cleared",
                    description=(
                        "ato_status changed to YES — close any open ai-ato-gap finding; "
                        "reset rotation clock if credential is unchanged"
                    ),
                    posture=Posture.PER_POLICY,
                )
            )

    if "development_stage" in changed:
        if prior.development_stage == DevStage.PILOT and record.development_stage == DevStage.DEPLOYED:
            actions.append(
                JMLAction(
                    step="M-development_stage",
                    description=(
                        "Stage pilot → deployed: expand credential scope to production boundary; "
                        "remove pilot expiry; confirm ATO is YES"
                    ),
                    posture=Posture.NEVER_AUTOFIX,
                    requires_confirmation=True,
                )
            )

    return actions, findings


def _leaver_actions(candidate: bool = False) -> list[JMLAction]:
    """8-step leaver sequence (UIAO_197 §1.3).

    Steps L-3..L-8 are marked requires_confirmation=True when this is a
    candidate leaver (absent from vintage without an explicit retired entry)
    so they are held pending human disposition.
    """
    hold = candidate

    return [
        JMLAction(
            step="L-1",
            description="Alert credential owner and bureau governance contact",
            posture=Posture.PER_POLICY,
            timeline_days=0,
        ),
        JMLAction(
            step="L-2",
            description="Freeze new permission grants on all credentials",
            posture=Posture.PER_POLICY,
            timeline_days=0,
        ),
        JMLAction(
            step="L-3",
            description="Export full audit trail to evidence bundle",
            posture=Posture.PER_POLICY,
            timeline_days=7,
            requires_confirmation=hold,
        ),
        JMLAction(
            step="L-4",
            description="Revoke API keys and OAuth client credentials",
            posture=Posture.NEVER_AUTOFIX,
            timeline_days=14,
            requires_confirmation=True,
        ),
        JMLAction(
            step="L-5",
            description="Rotate or revoke service account credentials",
            posture=Posture.NEVER_AUTOFIX,
            timeline_days=14,
            requires_confirmation=True,
        ),
        JMLAction(
            step="L-6",
            description="Remove system from active access review queues",
            posture=Posture.PER_POLICY,
            timeline_days=14,
            requires_confirmation=hold,
        ),
        JMLAction(
            step="L-7",
            description="Archive OrgPath record (queryable, no longer active)",
            posture=Posture.PER_POLICY,
            timeline_days=30,
            requires_confirmation=hold,
        ),
        JMLAction(
            step="L-8",
            description="Emit closed-loop evidence to ATO record and UIAO evidence fabric",
            posture=Posture.PER_POLICY,
            timeline_days=30,
            requires_confirmation=hold,
        ),
    ]


# ---------------------------------------------------------------------------
# Diff helpers
# ---------------------------------------------------------------------------


def _diff_fields(current: AISystemRecord, prior: AISystemRecord) -> list[str]:
    """Return the subset of MOVER_TRIGGER_FIELDS that changed."""
    changed = []
    for f in MOVER_TRIGGER_FIELDS:
        if getattr(current, f) != getattr(prior, f):
            changed.append(f)
    return changed


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_events(
    current_vintage: list[AISystemRecord],
    prior_vintage: list[AISystemRecord] | None = None,
    days_since_last_mover: dict[str, int] | None = None,
) -> JMLEventSet:
    """Diff two inventory vintages and return the full JML event set.

    Parameters
    ----------
    current_vintage:
        Records from the current (most recent) OMB inventory vintage.
    prior_vintage:
        Records from the previous vintage.  When None, every live record
        in ``current_vintage`` is treated as a joiner (first-time scan).
    days_since_last_mover:
        Mapping of ``omg_id`` → days since the last mover event was
        detected for that system.  When provided, systems whose value
        exceeds ``STALENESS_THRESHOLD_DAYS`` produce an ``ai-staleness``
        finding.  Systems absent from the map are assumed fresh.

    Returns
    -------
    JMLEventSet
        All joiners, movers, leavers, candidate leavers, and staleness
        findings produced by this diff.
    """
    result = JMLEventSet()

    prior_by_id: dict[str, AISystemRecord] = {r.omg_id: r for r in prior_vintage} if prior_vintage is not None else {}
    current_by_id: dict[str, AISystemRecord] = {r.omg_id: r for r in current_vintage}

    # --- Pass 1: joiners and movers (iterate current vintage) ---------------
    for record in current_vintage:
        prior = prior_by_id.get(record.omg_id)

        if prior is None:
            # New system — joiner only if now in live population
            if record.is_live:
                actions, findings = _joiner_actions(record)
                result.joiners.append(
                    JMLEvent(
                        event_type=JMLEventType.JOINER,
                        record=record,
                        prior_record=None,
                        actions=actions,
                        findings=findings,
                    )
                )
        else:
            # Existing system — check for mover triggers
            changed = _diff_fields(record, prior)
            if changed:
                actions, findings = _mover_actions(record, prior, changed)
                result.movers.append(
                    JMLEvent(
                        event_type=JMLEventType.MOVER,
                        record=record,
                        prior_record=prior,
                        changed_fields=changed,
                        actions=actions,
                        findings=findings,
                    )
                )

            # Confirmed leaver: explicitly retired in current vintage
            if record.development_stage in _LEAVER_STAGES and prior.development_stage not in _LEAVER_STAGES:
                result.leavers.append(
                    JMLEvent(
                        event_type=JMLEventType.LEAVER,
                        record=record,
                        prior_record=prior,
                        actions=_leaver_actions(candidate=False),
                    )
                )

    # --- Pass 2: candidate leavers (in prior but absent from current) -------
    if prior_vintage is not None:
        for prior_record in prior_vintage:
            if prior_record.omg_id not in current_by_id and prior_record.is_live:
                result.candidate_leavers.append(
                    JMLEvent(
                        event_type=JMLEventType.CANDIDATE_LEAVER,
                        record=prior_record,
                        prior_record=prior_record,
                        candidate_leaver=True,
                        actions=_leaver_actions(candidate=True),
                    )
                )

    # --- Pass 3: staleness findings -----------------------------------------
    if days_since_last_mover:
        for record in current_vintage:
            if not record.is_live:
                continue
            days = days_since_last_mover.get(record.omg_id)
            if days is not None and days > STALENESS_THRESHOLD_DAYS:
                result.staleness_findings.append(finding_staleness(record, days_since_mover=days))

    return result
