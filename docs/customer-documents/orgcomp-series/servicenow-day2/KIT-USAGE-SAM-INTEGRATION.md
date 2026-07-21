# Day-2 Automation Kit — SAM Integration Usage Guide

> How the **SAM (Systems Access Management / SailPoint IGA) ↔ ServiceNow**
> integration is operated and troubleshot day to day. SAM is the authoritative
> origin of higher-tier (Tier-1/2, privileged) access decisions; **IdentityIQ
> pushes** an approved request into ServiceNow, which correlates it to a RITM and
> executes it under the governed flow. This guide is for the integration
> admin / IGA operator, not the service-desk operator (see `KIT-USAGE-OPERATOR.md`
> for the catalog tasks).

**Date Code:** 2026-07-21 16:30 ET · **Audience:** IGA / integration admin ·
**Primary: SailPoint IdentityIQ (on-prem)** · Secondary: Identity Security Cloud

## The decision-to-execution path

```
 1. Requester asks for access in IdentityIQ (LCM)  — or a role/entitlement is
    requested on their behalf.
 2. IIQ runs the approval chain by Risk Tier:
       Tier 1 (High)     Dept Owner → App Owner → IGO (final)
       Tier 2 (Moderate) Dept Owner → App Owner
       Tier 3 (Low)      Dept Owner
 3. On full approval, IIQ SDIM PUSHES the request →
       POST /api/x_fed_day2_ops/sam/ritm
 4. ServiceNow creates + correlates the RITM, writes SAM↔RITM↔subject lineage,
    and writes the RITM number back onto the IIQ IdentityRequest (externalTicketId).
 5. The Governed Day-2 Request Flow executes it (PIM-elevated, verified, evidenced).
 6. On closure, the evidence carries the SAM request id — the action is attestable
    back to the DECISION, not just the change.
```

**SAM decides; ServiceNow executes.** ServiceNow never re-approves, and it never
writes back into SAM's decision — the two planes stay separate on purpose.

## What SAM must send (the push contract)

The IIQ SDIM push body (see `scripted-rest/sam_inbound_ritm.js`):

| Field | Meaning | Required |
|---|---|---|
| `sam_request_id` | IIQ `IdentityRequest` id — the correlation key | ✅ |
| `access_item` | IIQ Role / Entitlement name being granted | ✅ |
| `requested_for` | correlation id that resolves to the Entra object / `sys_user` | ✅ |
| `approval_authority` | `IGO` \| `app-owner` \| `dept-owner` — who approved | ✅ |
| `risk_tier` | `1` \| `2` \| `3` | recommended |
| `justification` | business justification | recommended |

A push missing any required field, from a caller without the
`x_fed_day2_ops.sam_inbound` role, or naming a `requested_for` that does not
resolve, is **refused** (400 / 403 / 422) and **no RITM is created**. This is the
integration's fail-closed contract — an un-correlatable or unauthenticated request
must never become work.

## Correlation and lineage — what to check

Every accepted push writes one lineage record (`record_type = sam_lineage`) in the
integration table binding:

- `sam_request_id` (IIQ IdentityRequest) ↔ `ritm` (ServiceNow number) ↔
  `entra_object_id` (the subject), under `sam_flavor` and `sam_source_id`.

To confirm an end-to-end correlation: the IIQ IdentityRequest shows the RITM
number as its `externalTicketId`, and the ServiceNow lineage record shows the same
IIQ id. If the two disagree, the SDIM write-back did not complete — re-run it; do
not hand-edit either side.

## Closure back to SAM

`SamCorrelationClient.getRequestStatus(samRequestId)` reads the SAM-side status for
closure (IIQ `LaunchedWorkflows` / ISC `access-request-status`, selected by
`sam_flavor`). A failed or unparseable read is **inconclusive, not approved** — the
task does not close on an assumption. When the ServiceNow task closes, its evidence
record carries the `sam_request_id`, so the attestation pipeline (Vol VII Book 04)
can show the access is backed by an owned SAM decision.

## Switching primary ↔ secondary (IdentityIQ ↔ ISC)

The client branches on one property:

- **IdentityIQ (primary):** `x_fed_day2_ops.sam_flavor = identityiq`,
  `sam_base_url = https://<iiq-host>/identityiq`; SCIM `/scim/v2` + REST `/rest`;
  API-Client OAuth2 or a least-privilege Basic service account; SDIM raises the
  RITM. On-prem, inside the boundary.
- **ISC (secondary):** `sam_flavor = isc`,
  `sam_base_url = https://<tenant>.api.identitynow.com`; SCIM `/v2`; PAT OAuth2; an
  event trigger/webhook fires the RITM.

No code change — only the property, the alias credential, and the base URL. The
correlation contract and the approval-authority mapping are identical.

## Troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| Push returns **403** | Caller lacks `x_fed_day2_ops.sam_inbound` | Grant the role to the IIQ integration user only |
| Push returns **400** | Missing a required correlation field | Fix the SDIM field map |
| Push returns **422** | `requested_for` does not resolve to a reconciled identity | Correct the correlation id, or reconcile the identity first |
| RITM created but no lineage (**202**) | Integration table write incomplete | Check `x_fed_day2_ops.tbl_integration` exists and the table has the lineage columns |
| Duplicate pushes | SDIM retried | The endpoint is idempotent on `sam_request_id` — it returns the existing RITM, safe |
| Status read inconclusive | SAM API unreachable / auth expired | Fix the `sam` alias credential; the task correctly did **not** close on the failed read |
| Everything returns canned values | `x_fed_day2_ops.test_mode = true` | Expected in sub-prod; set `false` in production |

## Authority model (unchanged across flavors)

| Role | Approval authority | Where |
|---|---|---|
| **IGO** (Identity Governance Officer) | Level 1 — final on Tier-1 and all admin consent | SAM |
| **Application Owner** | Level 3 — application-level access | SAM |
| **Departmental Owner** | Level 4 — departmental validation, Tier-3 approval | SAM |

Admin consent for enterprise applications is **never** approved at the service
desk — it is an IGO decision, executed as the Lane F governed path (Vol IX
Book 05).

## Canon note

This SAM/IGA access-governance integration is a distinct SailPoint surface from the
`sailpoint-nerm` slot reserved in the adapter registry (ADR-059, non-employee).
Activating it as a conformance adapter needs its own slot and ADR (an ISC/IGA
boundary-expansion decision). The variable and push contracts here are the
integration contract; the canon designation is the follow-up.

## Cross-references

- `KIT-VARIABLES-REFERENCE.md` §4 — the SAM variable set (IIQ primary, ISC secondary).
- `KIT-IMPLEMENTATION-GUIDE.md` Phase 4 — standing up the push endpoint and SDIM.
- `scripted-rest/sam_inbound_ritm.js`, `script-includes/SamCorrelationClient.js` — the code.
- Vol IX Book 05 (SaaS/Lane F), Book 06 (identity governance); the Help Desk
  operations guides (the SAM/ServiceNow/PIM authority model).
