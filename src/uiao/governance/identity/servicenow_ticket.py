"""ServiceNow write path — create governance tickets from JML events.

Translates a HumanJMLEvent (with resolved OrgPath and routing decision)
into a ServiceNow Service Catalog Request via the Table API.  The
ServiceNow ServiceNowCollector (adapters/servicenow_adapter.py) is the
existing READ path; this module is the write path.

By default every call runs in dry-run mode: it builds the full payload
and logs it without posting.  Pass ``dry_run=False`` only in environments
where the ServiceNow instance is configured to accept UIAO requests.

Ticket categories:
  - GOV-JOINER    Joiner onboarding access request
  - GOV-MOVER     Transfer/placement change access review
  - GOV-LEAVER    Leaver deprovisioning request
  - GOV-PENDING   Pending leaver advance-notice alert

Canon reference: ADR-092 L3 actuation, governance/identity/routing.py,
adapters/servicenow_adapter.py (ServiceNowCollector read shape).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

import requests

from uiao.governance.identity.jml import HumanJMLEvent, HumanJMLEventSet, HumanJMLEventType
from uiao.governance.identity.routing import RoutingDecision, compute_routing

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Ticket payload
# ---------------------------------------------------------------------------

_EVENT_TYPE_TO_CATEGORY = {
    HumanJMLEventType.JOINER: "GOV-JOINER",
    HumanJMLEventType.MOVER: "GOV-MOVER",
    HumanJMLEventType.LEAVER: "GOV-LEAVER",
    HumanJMLEventType.PENDING_LEAVER: "GOV-PENDING",
}

_EVENT_TYPE_TO_SHORT_DESC = {
    HumanJMLEventType.JOINER: "Identity governance — onboarding request",
    HumanJMLEventType.MOVER: "Identity governance — transfer / placement change",
    HumanJMLEventType.LEAVER: "Identity governance — deprovisioning request",
    HumanJMLEventType.PENDING_LEAVER: "Identity governance — pending leaver advance notice",
}


@dataclass
class TicketPayload:
    """Serialisable ServiceNow Service Catalog Request payload."""

    employee_id: str
    identity_label: str
    event_type: str
    category: str
    short_description: str
    description: str
    caller_id: str  # ServiceNow sys_id of the requesting authority
    assignment_group: str  # maps from routing_key → ServiceNow group
    urgency: str  # 1=High / 2=Medium / 3=Low
    impact: str
    resolved_orgpath: str | None
    routing_authority: str
    changed_fields: list[str]
    actions: list[dict]
    findings: list[dict]
    u_uiao_orgpath: str | None
    u_uiao_routing_key: str | None

    def to_dict(self) -> dict:
        return {
            "caller_id": self.caller_id,
            "assignment_group": self.assignment_group,
            "category": self.category,
            "short_description": self.short_description,
            "description": self.description,
            "urgency": self.urgency,
            "impact": self.impact,
            "u_uiao_employee_id": self.employee_id,
            "u_uiao_identity": self.identity_label,
            "u_uiao_event_type": self.event_type,
            "u_uiao_orgpath": self.u_uiao_orgpath or "",
            "u_uiao_routing_key": self.u_uiao_routing_key or "",
            "u_uiao_changed_fields": ",".join(self.changed_fields),
            "u_uiao_action_count": str(len(self.actions)),
            "u_uiao_finding_count": str(len(self.findings)),
        }


@dataclass
class TicketResult:
    """Result of one ticket creation attempt."""

    employee_id: str
    event_type: str
    dry_run: bool
    success: bool
    ticket_number: str | None = None
    sys_id: str | None = None
    payload: dict | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "employee_id": self.employee_id,
            "event_type": self.event_type,
            "dry_run": self.dry_run,
            "success": self.success,
            "ticket_number": self.ticket_number,
            "sys_id": self.sys_id,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# Payload builder
# ---------------------------------------------------------------------------


def build_payload(
    event: HumanJMLEvent,
    routing: RoutingDecision,
    *,
    caller_id: str = "uiao-governance",
    group_map: dict[str, str] | None = None,
) -> TicketPayload:
    """Build a TicketPayload from a JML event and its routing decision.

    Parameters
    ----------
    event:
        The JML event (must have resolved_orgpath set or None).
    routing:
        The RoutingDecision from routing.compute_routing().
    caller_id:
        ServiceNow sys_id (or name) of the account creating the ticket.
        Typically the UIAO service account configured in the environment.
    group_map:
        Optional mapping from routing authority string to ServiceNow
        assignment_group name.  Defaults map authority prefixes to
        generic group names suitable for a demo/test instance.
    """
    gmap = group_map or {}
    assignment_group = gmap.get(routing.authority) or _default_group(routing.authority)

    urgency = _urgency_for_event(event)
    impact = urgency  # symmetric for governance tickets

    description_lines = [
        "UIAO Governance — Identity Lifecycle Event",
        f"Employee ID : {event.record.employee_id}",
        f"Identity    : {event.identity_label}",
        f"Event type  : {event.event_type.value}",
        f"OrgPath     : {event.resolved_orgpath or 'UNRESOLVED'}",
        f"Authority   : {routing.authority}",
        f"Rationale   : {routing.rationale}",
        "",
        "Required actions:",
    ]
    for action in event.actions:
        description_lines.append(f"  [{action.step}] {action.description}")
    if event.findings:
        description_lines.append("")
        description_lines.append("Drift findings:")
        for f in event.findings:
            description_lines.append(f"  [{f.finding_id}] {f.drift_class} — {f.observed}")
    if event.changed_fields:
        description_lines.append("")
        description_lines.append(f"Changed fields: {', '.join(event.changed_fields)}")

    return TicketPayload(
        employee_id=event.record.employee_id,
        identity_label=event.identity_label,
        event_type=event.event_type.value,
        category=_EVENT_TYPE_TO_CATEGORY[event.event_type],
        short_description=_EVENT_TYPE_TO_SHORT_DESC[event.event_type],
        description="\n".join(description_lines),
        caller_id=caller_id,
        assignment_group=assignment_group,
        urgency=urgency,
        impact=impact,
        resolved_orgpath=event.resolved_orgpath,
        routing_authority=routing.authority,
        changed_fields=event.changed_fields,
        actions=[a.to_dict() for a in event.actions],
        findings=[f.to_dict() for f in event.findings],
        u_uiao_orgpath=event.resolved_orgpath,
        u_uiao_routing_key=routing.authority,
    )


# ---------------------------------------------------------------------------
# Ticket creator
# ---------------------------------------------------------------------------


def create_ticket(
    event: HumanJMLEvent,
    *,
    instance_url: str = "",
    username: str = "",
    password: str = "",
    dry_run: bool = True,
    caller_id: str = "uiao-governance",
    group_map: dict[str, str] | None = None,
    table: str = "sc_request",
) -> TicketResult:
    """Create (or simulate) a ServiceNow ticket from a JML event.

    Parameters
    ----------
    event:
        The JML event to raise a ticket for.
    instance_url:
        Base URL of the ServiceNow instance, e.g. ``https://agency.service-now.com``.
        Required when ``dry_run=False``.
    username / password:
        Credentials for the UIAO service account in ServiceNow.
        Required when ``dry_run=False``.
    dry_run:
        When True (default), builds and logs the payload without posting.
    table:
        ServiceNow table to post to.  Defaults to ``sc_request``
        (Service Catalog Requests).
    """
    routing = compute_routing(event)
    payload = build_payload(event, routing, caller_id=caller_id, group_map=group_map)
    payload_dict = payload.to_dict()

    if dry_run:
        logger.info(
            "[DRY-RUN] Would create ServiceNow %s ticket:\n%s",
            table,
            json.dumps(payload_dict, indent=2),
        )
        return TicketResult(
            employee_id=event.record.employee_id,
            event_type=event.event_type.value,
            dry_run=True,
            success=True,
            payload=payload_dict,
        )

    if not instance_url:
        raise ValueError("instance_url required when dry_run=False")

    url = f"{instance_url.rstrip('/')}/api/now/table/{table}"
    try:
        resp = requests.post(
            url,
            auth=(username, password),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            json=payload_dict,
            timeout=30,
        )
        resp.raise_for_status()
        body = resp.json()
        result_body = body.get("result", {})
        return TicketResult(
            employee_id=event.record.employee_id,
            event_type=event.event_type.value,
            dry_run=False,
            success=True,
            ticket_number=result_body.get("number"),
            sys_id=result_body.get("sys_id"),
        )
    except requests.RequestException as exc:
        logger.error("ServiceNow ticket creation failed for %s: %s", event.record.employee_id, exc)
        return TicketResult(
            employee_id=event.record.employee_id,
            event_type=event.event_type.value,
            dry_run=False,
            success=False,
            error=str(exc),
        )


def create_tickets_for_event_set(event_set: HumanJMLEventSet, **kwargs: Any) -> list[TicketResult]:
    """Create tickets for every event in a HumanJMLEventSet.

    Keyword arguments are forwarded to ``create_ticket``.
    ``dry_run=True`` by default.
    """
    results = []
    for ev in event_set.all_events:
        results.append(create_ticket(ev, **kwargs))
    return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _urgency_for_event(event: HumanJMLEvent) -> str:
    if event.event_type == HumanJMLEventType.LEAVER:
        return "1"  # High — deprovision immediately
    if event.event_type == HumanJMLEventType.PENDING_LEAVER:
        return "2"  # Medium — advance notice
    if event.findings:
        return "1"  # Drift findings present → high
    return "2"


def _default_group(authority: str) -> str:
    if authority.startswith("division-manager:"):
        division = authority.split(":", 1)[1]
        return f"UIAO Identity — {division} Division"
    mapping = {
        "identity-team": "UIAO Identity Team",
        "grc-manager": "UIAO GRC Manager",
        "isso": "UIAO ISSO",
    }
    return mapping.get(authority, "UIAO Identity Team")
