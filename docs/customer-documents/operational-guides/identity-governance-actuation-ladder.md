---
title: "Identity Governance — Actuation Ladder"
subtitle: "What each governance layer does and what it cannot do without human approval"
document_id: UIAO_200
status: DRAFT
publish_to_site: false
---

# Identity Governance Actuation Ladder

This document maps each piece of the identity governance implementation to
the ADR-092 L0–L4 actuation ladder.  It answers the question an auditor or
hostile reviewer will ask first:

> *"Is UIAO actually governing anything, or is it just producing reports?"*

The short answer: **the code operates at L1–L2 today; every action that
changes a system requires a human to execute it (L3 behavior); L4 autonomous
actuation is explicitly excluded.**

The complete answer is below.

---

## The ADR-092 Actuation Ladder

| Tier | Name | What the system does | Human in the loop? |
|---|---|---|---|
| L0 | Record | Persists governance facts | Not required |
| L1 | Observe | Read-only projection; answers queries | Not required |
| L2 | Advise | Emits events, findings, action lists | Not required |
| L3 | Gated actuation | Submits requests; human approves before execution | **Required** |
| L4 | Autonomous | Executes without prior human approval | Not required — **federal ceiling is L3** |

Federal policy ceiling: the federal default is L3.  No component in this
implementation operates above L3.  L4 is not planned.

---

## Component-by-component mapping

### Active Governance Directory (AGD) — L1

**File:** `src/uiao/directory/`
**ADR:** ADR-100

The AGD is an LDAPv3 read projection of the OrgPath governance substrate.
It answers LDAP queries; it writes nothing.

- Receives: LDAP Search requests (from SailPoint ISC, ServiceNow, Entra adapters)
- Produces: LDAP Search responses (organizational placement data)
- Changes to any system: **none**
- Tier: **L1 (Observe)**

The AGD becomes load-bearing when downstream systems are configured to
*halt* rather than fall back if the AGD is unreachable (see
[AGD Authority Designation](agd-authority-designation.md)).

---

### Human JML Detector — L2

**File:** `src/uiao/governance/identity/jml.py`

Diffs two HRIT snapshots; produces `HumanJMLEvent` objects with action lists
and drift findings.

- Receives: two lists of `HRRecord` (current and prior HRIT extract)
- Produces: `HumanJMLEventSet` (joiner/mover/leaver/pending events), JSON evidence artifacts
- Changes to any system: **none** — the action list is advisory
- Tier: **L2 (Advise)**

**What L3 looks like for this component:** when `create_tickets_for_event_set()`
is called with `dry_run=False` and a live ServiceNow instance, a Service
Catalog Request is submitted. A human in ServiceNow must then approve and
execute each action step.  The code cannot execute the step itself.

**Explicit L3 guards:**

```python
# Every action that changes a system carries requires_confirmation=True
JMLAction(step="J-2", description="Create Entra account ...",
          posture=Posture.NEVER_AUTOFIX, requires_confirmation=True)

# Ticket creator is dry-run by default
create_ticket(event, dry_run=True)   # default — no POST
create_ticket(event, dry_run=False, instance_url="https://...")  # live POST
```

---

### Approval Routing — L2

**File:** `src/uiao/governance/identity/routing.py`

Computes which authority must approve a JML action, based on OrgPath facets.

- Receives: `HumanJMLEvent`
- Produces: `RoutingDecision` (authority string, tier label, rationale)
- Changes to any system: **none**
- Tier: **L2 (Advise)**

All routing decisions carry `ApprovalTier.GATED` — the decision is a
recommendation to the ServiceNow ticket system, not an automated assignment.
The routing decision becomes binding only when a human confirms it in
ServiceNow.

---

### ServiceNow Ticket Creator — L2 → L3 boundary

**File:** `src/uiao/governance/identity/servicenow_ticket.py`

Translates JML events into ServiceNow Service Catalog Request payloads.

- Receives: `HumanJMLEvent` + `RoutingDecision`
- Produces (dry-run, default): JSON payload logged to stdout — **L2**
- Produces (live): POST to ServiceNow Table API — **L3** (submits a request)
- Changes to any system: **none** — ServiceNow request must be approved and executed by a human
- Tier: **L2 (dry-run) / L3 at the moment of POST**

**The L3 boundary is the POST.**  The system submits a governed intent; a human
reviews and executes.  The code cannot approve its own request.

---

### Service Identity Orphan Detector — L2

**File:** `src/uiao/governance/identity/service_identity.py`

Scans service account inventory; emits `ORPHANED` events when a service
account's owner is a known human LEAVER.

- Receives: service identity snapshot + set of LEAVER employee_ids
- Produces: `ServiceIdentityEventSet` with P1 `DRIFT-ORPHAN-NHAM` findings
- Changes to any system: **none**
- Tier: **L2 (Advise)**

**Why this is not L3 even though the finding is P1:**  a P1 severity means
*act immediately* — but the system cannot disable a service account or
rotate credentials without human confirmation.  The finding carries
`Posture.NEVER_AUTOFIX`.  The OR-2 action ("disable the service account")
requires a human to execute it, even under urgency.

---

### Entra Administrative Unit Adapter — L3

**File:** `src/uiao/adapters/entra_admin_units.py`
**ADR:** ADR-037

The AU adapter writes to Entra when run in `--apply` mode.  This is the only
component in the identity governance stack that currently executes changes
autonomously — and it is explicitly bounded:

- The plan/apply pattern is enforced: `--check` (L2) before `--apply` (L3)
- Apply is gated on zero P1 drift findings
- AU membership changes are the only writes; account creation, credential
  rotation, and entitlement grants are not performed by this adapter

**Tier: L3 (Gated actuation — `--apply` requires explicit invocation)**

---

## Summary table

| Component | Tier | Writes to a system? | Human required to execute? |
|---|---|---|---|
| AGD LDAPv3 server | L1 | No | N/A |
| Human JML detector | L2 | No | Yes (for all action steps) |
| Approval routing | L2 | No | Yes |
| ServiceNow ticket (dry-run) | L2 | No | N/A |
| ServiceNow ticket (live POST) | L3 | Yes — submits request | Yes — must approve in ServiceNow |
| Service identity orphan detector | L2 | No | Yes (OR-1 through OR-5) |
| Entra AU adapter (--check) | L2 | No | Yes |
| Entra AU adapter (--apply) | L3 | Yes — AU membership | No (bounded to AU only) |

---

## What makes L3 real

The hostile reviewer's test: *"Name one thing that breaks if UIAO governance
runs but nobody looks at it."*

Current answer (before agency sign-off on the Authority Designation):

- **Nothing breaks** — the system produces advisory output (L2).  If nobody
  reads the JML event log or acts on the ServiceNow tickets, governance is
  silent.

Answer after the completion checklist in
[agd-authority-designation.md](agd-authority-designation.md) is signed:

- **SailPoint ISC aggregation halts** if the AGD is offline (the ISC source
  is configured to fail rather than fall back).
- **ServiceNow incident routing halts** for any incident where the AGD
  cannot confirm department/division placement.
- **Entra AU scoping drifts** if the AU adapter's scheduled plan/apply is
  not run — and the drift gate blocks publication until it is.

The gap between "advisory output" and "real L3 governance" is the
signed authority designation and the three system configurations it requires.

---

## Related

- [ADR-092 — Active Governance](../../../adr/adr-092-active-governance.html)
- [ADR-100 — AGD LDAPv3 read projection](../../../adr/adr-100-active-governance-directory-ldap.html)
- [AGD Authority Designation (UIAO_199)](agd-authority-designation.md)
- [AGD SailPoint ISC Connector (UIAO_198)](agd-sailpoint-connector.md)
