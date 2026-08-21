# Day-2 Automation Kit — SAM Integration Usage Guide

> How the **SAM (Systems Access Management / SailPoint IGA) ↔ ServiceNow**
> integration is operated and troubleshot day to day. SAM is the authoritative
> origin of higher-tier (Tier-1/2, privileged) access decisions; **IdentityIQ
> pushes** an approved request into ServiceNow, which correlates it to a RITM and
> executes it under the governed flow. This guide is for the integration
> admin / IGA operator, not the service-desk operator (see `KIT-USAGE-OPERATOR.md`
> for the catalog tasks).

**Date Code:** 2026-08-19 10:22 ET · **Audience:** IGA / integration admin ·
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

See `examples/sam-push-payloads.md` for concrete sample bodies (success at each
risk tier, missing fields, an unresolvable `requested_for`, and the optional
signed-push shape) plus the full IIQ-attribute ↔ ServiceNow-field map, and
`atf/atf-sam-*.xml` for the ATF suite that exercises every row of the table above
against the code.

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

### Optional: richer closure write-back

The write-back every deployment gets for free is the RITM number onto
`IdentityRequest.externalTicketId` (via the SDIM, when it reads the endpoint's
`201`). Set `x_fed_day2_ops.sam_closure_writeback = true` to also push a
**structured status/evidence summary** — verb, control, actuation leg, the
evidence record's `sys_id` and tamper-evident hash, and the closure timestamp
— back onto the IdentityRequest once a SAM-originated task reaches Closed
Complete (`MacdrOrchestrator._writeSamClosureSummary` →
`SamCorrelationClient.writeClosureSummary`). An IGA operator reading the
IdentityRequest then sees how the request closed without crossing into
ServiceNow.

This is **optional** (default `false`) and **fail-open toward closure**: the
call is made *after* ServiceNow has already recorded the closure evidence, is
wrapped so any failure only logs, and can never turn a real closure into a
stuck or failed request — an unreachable SAM at closure time is not a reason
to withhold a closure ServiceNow has already decided. Like `fetchIdentityRequest`
and `verifyJws`, `writeClosureSummary` is a deliberate **NOT IMPLEMENTED**
stub in live mode until a tenant wires it to a real IIQ/ISC write API (a SCIM
PATCH, an IIQ REST comment endpoint, or a custom workflow variable — tenant
specific, so it cannot be filled in generically). Leaving the property `false`
(the default) is a fully supported, safe state — the RITM-number write-back
alone is a complete, working integration.

## Monitoring the inbound endpoint

Every push the endpoint sees — accepted or refused — writes one
`record_type = sam_push_outcome` row to the integration table
(`SamCorrelationClient.recordPushOutcome`, called from every `deny()` and every
success path in `sam_inbound_ritm.js`). It stores the same opaque HTTP status
and reason code the caller receives (never the detailed log-only reason —
telemetry is not a second channel for control-surface detail), and is stamped
`test_mode`/`synthetic` so a sub-prod ATF run never contaminates a production
count.

Both counting methods exclude rows **known** to be synthetic
(`synthetic != 'true'`) rather than requiring `synthetic == 'false'`. The
difference matters operationally: the stricter form drops every row where the
field is unpopulated — rows written before the column existed, rows from
another writer, rows a future change forgets to stamp — so it under-reports.
A monitoring predicate that under-reports shows a green board during an
outage, which is worse than no monitoring at all. These queries fail toward
counting, not toward silence.

Three read paths, all on `SamCorrelationClient`:

| Method | Answers | Use it for |
|---|---|---|
| `dailyOutcomeCounts(sinceDays)` | Accepted vs. refused counts over the window, refused broken down by reason code | A daily operational report — "how many pushes today, and why did the refused ones fail" |
| `sustainedFailureCheck(windowMinutes, threshold)` | Has the endpoint refused at least `threshold` pushes in the trailing `windowMinutes`? | A Scheduled Job that pages when refusals cluster — usually a SAM-side outage (pull-verify unreachable), a rotated/expired credential, or SDIM field-map drift, not one-off caller mistakes |
| `correlationReport(samRequestId)` | The `sam_lineage` row and every evidence row for one SAM request id, joined | "What happened to SAM request X end to end" — the dashboard/report Tier-1 item 6 asks for, expressed as a callable query rather than a platform report definition (which, like the update set, is a machine-serialized export you build on your instance — see `START-HERE.md` §1) |

`sustainedFailureCheck` is a **predicate**, not an alert channel — wire its
`alert: true`/`false` result into whatever your instance already uses for
paging (a Scheduled Job that emails/pages, an Event + Notification, a webhook
into your monitoring stack). A concentration of `not_approved` or
`verification_unavailable` refusals in `dailyOutcomeCounts().refusedByReason`
usually means the SAM verification path itself is down, not that callers are
sending bad pushes — see the troubleshooting table below.

Three codes mean something different and should be treated as security
signals, not availability ones. `signature_subject_unbound` means a signer
returned a claim set with no `requested_for`: the subject would have been
caller-asserted and unsigned, so the push was refused. `subject_mismatch`
means a validly-signed assertion was pushed for a *different* person than it
was signed for. `not_approved` on the JWS path means a correctly-signed
**denial** was pushed as if it were an approval. None of these is a
misconfiguration to wave through — a run of them is worth reading the raw
pushes over.

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
| Duplicate pushes | SDIM retried | The endpoint is idempotent on the `sam_lineage` row for that `sam_request_id` — it returns the existing RITM, safe. The lookup is scoped to `record_type=sam_lineage` on purpose: `sam_push_outcome` telemetry must never satisfy it, or a push refused once could never succeed on retry |
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
- `examples/sam-push-payloads.md` — sample push bodies and the field map.
- `atf/atf-sam-*.xml` — the dedicated SAM ATF suite (`atf/README.md` for the full index).
- `update-set/README.md` — the SAM inbound objects bundled into the importable update set.
- Vol IX Book 05 (SaaS/Lane F), Book 06 (identity governance); the Help Desk
  operations guides (the SAM/ServiceNow/PIM authority model).
