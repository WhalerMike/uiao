"""Approval routing — OrgPath facets → governing authority.

Given a JML event and its resolved OrgPath context, returns the approval
routing key: which authority or role should receive the ServiceNow request.

Routing rules (in precedence order):

1. Service account (account_type = Service / Non-Human)
   → Identity team (identity-team)
2. Clearance change  (clearance_level in changed_fields for a Mover)
   → ISSO (isso)
3. Privileged account (account_type = Privileged)
   → GRC Manager (grc-manager)
4. Standard Employee/Contractor, placement change (dept/div in changed_fields)
   → Division Manager of the *new* department (division-manager:<division>)
5. Default
   → Division Manager of the record's current division (division-manager:<division>)

Canon reference: ADRs 051-054 (HRIT), ADR-092 L3 actuation, governance/identity/jml.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from uiao.adapters.modernization.hrit.inventory import HRRecord
from uiao.governance.identity.jml import HumanJMLEvent, HumanJMLEventType

# ---------------------------------------------------------------------------
# Authority labels
# ---------------------------------------------------------------------------

AUTHORITY_IDENTITY_TEAM = "identity-team"
AUTHORITY_ISSO = "isso"
AUTHORITY_GRC_MANAGER = "grc-manager"
AUTHORITY_DIVISION_MANAGER = "division-manager"


class ApprovalTier(str, Enum):
    """L1-L3 actuation tier for this routing decision."""

    OBSERVE = "L1"  # read-only; no ticket needed
    ADVISE = "L2"  # advisory alert; human decides
    GATED = "L3"  # human must approve before action proceeds


@dataclass
class RoutingDecision:
    """Result of computing the approval routing for one JML event."""

    authority: str  # e.g. "grc-manager" or "division-manager:Identity"
    tier: ApprovalTier
    rationale: str
    fallback_authority: str = AUTHORITY_IDENTITY_TEAM

    def to_dict(self) -> dict:
        return {
            "authority": self.authority,
            "tier": self.tier.value,
            "rationale": self.rationale,
            "fallback_authority": self.fallback_authority,
        }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_routing(event: HumanJMLEvent) -> RoutingDecision:
    """Return the RoutingDecision for a JML event.

    This function inspects the event type, changed_fields, and HR record
    attributes to determine who must approve the governance action.  It is
    intentionally simple — no external calls.  The result is stamped onto
    the event before it is passed to the ServiceNow ticket creator.
    """
    record = event.record
    changed = set(event.changed_fields)
    division = record.division or "unknown"

    # Rule 1: service / non-human accounts always route to the identity team
    account_type = _extract_account_type(record)
    if account_type in {"service", "non-human"}:
        return RoutingDecision(
            authority=AUTHORITY_IDENTITY_TEAM,
            tier=ApprovalTier.GATED,
            rationale="Service account — identity team owns all lifecycle changes",
        )

    # Rule 2: clearance level change → ISSO  (Mover only)
    if event.event_type == HumanJMLEventType.MOVER and "clearance_level" in changed:
        return RoutingDecision(
            authority=AUTHORITY_ISSO,
            tier=ApprovalTier.GATED,
            rationale="Clearance level change — ISSO approval required per SORN",
        )

    # Rule 3: privileged account → GRC Manager
    if account_type == "privileged":
        return RoutingDecision(
            authority=AUTHORITY_GRC_MANAGER,
            tier=ApprovalTier.GATED,
            rationale="Privileged account — GRC manager approval required",
        )

    # Rule 4: placement change (dept or div in changed_fields) → division manager of NEW division
    if "department" in changed or "division" in changed:
        return RoutingDecision(
            authority=f"{AUTHORITY_DIVISION_MANAGER}:{division}",
            tier=ApprovalTier.GATED,
            rationale=f"Placement change — division manager for {division!r} approves re-entitlement",
        )

    # Rule 5: default — division manager of current division
    return RoutingDecision(
        authority=f"{AUTHORITY_DIVISION_MANAGER}:{division}",
        tier=ApprovalTier.GATED,
        rationale=f"Default routing — division manager for {division!r}",
    )


def stamp_routing(event: HumanJMLEvent) -> HumanJMLEvent:
    """Compute and stamp routing_key onto *event* in-place; return event."""
    decision = compute_routing(event)
    event.routing_key = decision.authority
    return event


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_account_type(record: HRRecord) -> str:
    """Derive account type from worker_type and resolved_orgpath metadata.

    The canonical account_type facet lives in extensionAttribute10 / OrgPath
    facet 10 (UIAO_151 codebook).  When it is not directly available on the
    HRRecord (HRIT doesn't carry it), we proxy from worker_type:

    - Contractor / Vendor / ExternalCollaborator → standard (no elevated routing)
    - FullTimeEmployee / PartTimeEmployee         → standard unless orgpath says privileged
    - explicit "Privileged" substring in orgpath   → privileged

    Service accounts are not HR records; this path is a defensive fallback for
    misclassified records where worker_type contains "Service".
    """
    wt = (record.worker_type or "").lower()
    orgpath = (record.resolved_orgpath or "").lower()

    if "service" in wt:
        return "service"
    if "privileged" in orgpath:
        return "privileged"
    return "standard"
