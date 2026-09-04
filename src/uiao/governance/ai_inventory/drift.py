"""Drift class constants for the AI identity governance surface.

Each constant is a ``DRIFT-CLASS::subtype`` string that extends the
canonical drift taxonomy (ADR-012) with AI-specific finding types.
The six classes below map to the OMB M-25-21 governance obligations
identified in ADR-112 §1–§4.

Canon reference: UIAO_196, ADR-112, ADR-012
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from uiao.governance.drift_core import Finding, Posture, Severity

if TYPE_CHECKING:
    from uiao.governance.ai_inventory.schema import AISystemRecord

# ---------------------------------------------------------------------------
# Drift class string constants
# ---------------------------------------------------------------------------

DRIFT_AI_NO_ORGPATH = "DRIFT-IDENTITY::ai-no-orgpath"
"""AI system has no organisational placement (OrgPath is None).

An AI system with no OrgPath has no governed owner in the org hierarchy.
Every policy, credential rotation, and blast-radius calculation that depends
on OrgPath is blind to this system.

Severity: P2 (binding divergence — governance gap, not an active breach)
Posture:  PER_POLICY (may be auto-stamped once bureau is confirmed)
"""

DRIFT_AI_ATO_GAP = "DRIFT-COMPLIANCE::ai-ato-gap"
"""Deployed/piloted AI system has no Authorization to Operate.

M-25-21 imposes no AI-specific ATO gate; it directs agencies to keep applying
their EXISTING authorization requirements to AI systems. This finding is raised
against that existing agency policy, using the OMB inventory's have_ato field as
the enumeration source. A system operating
without one is non-compliant with the federal mandate.

Severity: P2 (compliance gap — material but not auth-breaking today)
Posture:  NEVER_AUTOFIX (requires human ATO process; UIAO cannot remediate)
"""

DRIFT_AI_UNOWNED = "DRIFT-IDENTITY::ai-unowned"
"""AI system has no contact email / owner identity anchor.

Without an owner, the system has no credential rotation target, no
incident-response point of contact, and no governance chain. Equivalent
to an orphaned service account.

Severity: P2
Posture:  NEVER_AUTOFIX (owner must be asserted by a human)
"""

DRIFT_AI_SHADOW = "DRIFT-IDENTITY::ai-shadow"
"""Machine-identity record in UIAO registry with no matching OMB entry.

A system acting inside the identity substrate that was never reported to
OMB under M-25-21 is a shadow AI system — the highest-severity class
from this surface because the mandate to inventory is positive and the
absence means the system has evaded all governance.

Severity: P1 (integrity — ungoverned actor in the identity substrate)
Posture:  NEVER_AUTOFIX (requires human investigation and OMB reporting)
"""

DRIFT_AI_AGENTIC_UNGOVERNED = "DRIFT-COMPLIANCE::ai-agentic-ungoverned"
"""Agentic AI system deployed without ATO and without a declared governance mode.

Agentic AI acts autonomously inside the federal identity substrate. An
agentic system without an ATO *and* without a governance mode on record
is the highest-risk configuration in the inventory — it can make identity-
layer changes with no audit trail and no human approval gate.

Severity: P1 (active risk — autonomous actor, no governance gate)
Posture:  NEVER_AUTOFIX
"""

DRIFT_AI_PII_NO_PIA = "DRIFT-COMPLIANCE::ai-pii-no-pia"
"""AI system handles PII but has no Privacy Impact Assessment URL.

A PIA is required for a PII-processing system under the Privacy Act and
E-Government Act; the OMB inventory reports it through pia_url. Absence of
a PIA URL is a documentation gap that blocks evidence-bundle production
for IA-8 and AR-2.

Severity: P2
Posture:  NEVER_AUTOFIX (PIA must be authored and published by the agency)
"""


# ---------------------------------------------------------------------------
# Finding constructors  (convenience wrappers around drift_core.Finding)
# ---------------------------------------------------------------------------


def finding_no_orgpath(record: AISystemRecord, evidence_ref: str = "omg-inventory") -> Finding:
    return Finding(
        plane="identity",
        name=record.identity_label,
        drift_class=DRIFT_AI_NO_ORGPATH,
        severity=Severity.P2,
        posture=Posture.PER_POLICY,
        intended=f"OrgPath derived from agency={record.agency} bureau={record.agency_bureau}",
        observed="OrgPath: None — agency or bureau field blank in OMB inventory",
        evidence_ref=evidence_ref,
    )


def finding_ato_gap(record: AISystemRecord, evidence_ref: str = "omg-inventory") -> Finding:
    return Finding(
        plane="identity",
        name=record.identity_label,
        drift_class=DRIFT_AI_ATO_GAP,
        severity=Severity.P2,
        posture=Posture.NEVER_AUTOFIX,
        intended=(
            "have_ato=Yes for any deployed/pilot AI system, per the agency's "
            "existing authorization requirements — M-25-21 imposes no AI-specific "
            "ATO gate and have_ato is the inventory's reporting field for that "
            "existing posture"
        ),
        observed=f"have_ato={record.ato_status.value}  stage={record.development_stage.value}",
        evidence_ref=evidence_ref,
    )


def finding_unowned(record: AISystemRecord, evidence_ref: str = "omg-inventory") -> Finding:
    return Finding(
        plane="identity",
        name=record.identity_label,
        drift_class=DRIFT_AI_UNOWNED,
        severity=Severity.P2,
        posture=Posture.NEVER_AUTOFIX,
        intended="contact_email present — system has a named owner in the identity substrate",
        observed="contact_email: None — no owner identity anchor in OMB inventory",
        evidence_ref=evidence_ref,
    )


def finding_shadow(system_name: str, evidence_ref: str = "uiao-registry") -> Finding:
    """P1: UIAO registry has a record that OMB does not know about."""
    return Finding(
        plane="identity",
        name=system_name,
        drift_class=DRIFT_AI_SHADOW,
        severity=Severity.P1,
        posture=Posture.NEVER_AUTOFIX,
        intended="every active AI system appears in the OMB M-25-21 inventory",
        observed="system present in UIAO registry but absent from OMB inventory",
        evidence_ref=evidence_ref,
    )


def finding_agentic_ungoverned(record: AISystemRecord, evidence_ref: str = "omg-inventory") -> Finding:
    return Finding(
        plane="identity",
        name=record.identity_label,
        drift_class=DRIFT_AI_AGENTIC_UNGOVERNED,
        severity=Severity.P1,
        posture=Posture.NEVER_AUTOFIX,
        intended="Agentic AI system has ATO and declared governance mode (L1 minimum per ADR-112 §4)",
        observed=f"classification=Agentic AI  have_ato={record.ato_status.value}  governance_mode=undeclared",
        evidence_ref=evidence_ref,
    )


def finding_pii_no_pia(record: AISystemRecord, evidence_ref: str = "omg-inventory") -> Finding:
    return Finding(
        plane="identity",
        name=record.identity_label,
        drift_class=DRIFT_AI_PII_NO_PIA,
        severity=Severity.P2,
        posture=Posture.NEVER_AUTOFIX,
        intended="has_pii=Yes → pia_url present (inventory PIA reporting field)",
        observed="has_pii=Yes  pia_url: None",
        evidence_ref=evidence_ref,
    )


DRIFT_AI_STALENESS = "DRIFT-COMPLIANCE::ai-staleness"
"""Live AI system has had no mover event detected in 365+ days.

The inventory record may be stale — either the system is genuinely
unchanged (acceptable) or governance fields have drifted without
the inventory being updated (governance failure).

Severity: P3 (informational — does not block certification)
Posture:  PER_POLICY (auto-closes when any mover event is detected)
Threshold: STALENESS_THRESHOLD_DAYS (365) days since last mover event
"""


def finding_staleness(
    record: AISystemRecord,
    days_since_mover: int,
    evidence_ref: str = "omg-inventory",
) -> Finding:
    return Finding(
        plane="identity",
        name=record.identity_label,
        drift_class=DRIFT_AI_STALENESS,
        severity=Severity.P3,
        posture=Posture.PER_POLICY,
        intended="mover event detected within last 365 days — inventory record is current",
        observed=f"no mover event in {days_since_mover} days — record may be stale",
        evidence_ref=evidence_ref,
    )
