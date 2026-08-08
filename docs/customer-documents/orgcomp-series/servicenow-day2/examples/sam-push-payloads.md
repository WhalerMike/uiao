# SAM push payloads + field-map reference

> Concrete request bodies for `POST /api/x_fed_day2_ops/sam/ritm`, plus the
> exact mapping from IIQ SDIM attributes to the JSON fields the endpoint
> reads and to where each value ends up in ServiceNow. Pairs with
> `KIT-USAGE-SAM-INTEGRATION.md` (the operational guide) and
> `atf/atf-sam-*.xml` (the tests these fixtures back).

## Field map: IIQ SDIM attribute → push field → ServiceNow destination

| IIQ / SDIM attribute | Push JSON field | Required | ServiceNow destination | Notes |
|---|---|---|---|---|
| `IdentityRequest.id` (workflow case id) | `sam_request_id` | ✅ | `x_fed_day2_ops_integration.sam_request_id` (correlation key); the idempotency key | Also the id the endpoint calls back on for pull-verify (`fetchIdentityRequest`), and what `getRequestStatus` reads at closure. |
| LCM request line item — Role/Entitlement `displayableName` | `access_item` | ✅ | RITM `short_description`/`description` text; lineage `verified_item` (from the VERIFIED read, not this field, once pull-verify runs) | The pushed value is a claim; `verifyWithSam()` must agree with SAM's own read of the item before it is trusted for lineage. |
| Identity `correlationId` (the attribute mapped to the Entra/`sys_user` correlation id — see `KIT-VARIABLES-REFERENCE.md` §4 for the Entra-source mapping) | `requested_for` | ✅ | Resolves to `sys_user.sys_id` via `sys_user.correlation_id`; written to `x_fed_day2_ops_integration.entra_object_id` | **Correlation id only** — no email fallback (email is mutable, non-unique in practice). Must resolve to exactly one **active** user or the push is refused (422). |
| Approval workflow's final approver step (`ApprovalItem.owner` on the closing step) | `approval_authority` | ✅ | RITM `description` text ("Approval authority (verified with SAM, not asserted by caller): …"); not persisted as its own lineage column | One of `IGO` \| `app-owner` \| `dept-owner`. The endpoint records the **verified** authority (from pull-verify/JWS), not the pushed claim, if the two ever disagree pull-verify already refused. |
| `IdentityRequest.riskScore` / role's configured risk tier | `risk_tier` | recommended | RITM `short_description` text only — **not a lineage table column** (see `KIT-BUILD-SPEC.md` §2b) | `1` (High) \| `2` (Moderate) \| `3` (Low); drives the IIQ-side approval chain length before the push ever happens, not a ServiceNow-side decision. |
| `IdentityRequest` business justification / comments field | `justification` | recommended | RITM `description` text; lineage `verified_item`'s sibling field on the verification result | |
| *(no separate SDIM field — carried by the push transport)* | `jws` | only in signed-push mode | Not persisted directly; its **claims** (once verified) feed the same lineage fields pull-verify would | Present only when `x_fed_day2_ops.sam_jws_public_key` is configured. See `payloads/sam-push-signed-jws.json`. |

**Not part of the inbound push contract, but part of the same loop:**

| Direction | What moves | Where |
|---|---|---|
| ServiceNow → IIQ (write-back) | RITM number | `IdentityRequest.externalTicketId`, written by the SDIM once it reads the endpoint's `201` response (`ritm` field) — see `KIT-USAGE-SAM-INTEGRATION.md` "Correlation and lineage" for how to confirm this completed. |
| ServiceNow → IIQ (closure read) | SAM-side status | `SamCorrelationClient.getRequestStatus(samRequestId)` reads IIQ `LaunchedWorkflows` (or ISC `access-request-status`) when a ServiceNow task closes — a failed/unparseable read is **inconclusive, not approved**. |

## Sample payloads

### 1. Success — Tier 2 (`payloads/sam-push-success-tier2.json`)

The ordinary case: App Owner is the final approver on a Tier-2 (Moderate)
chain.

```json
{
  "sam_request_id": "IIQ-REQ-2026-0000481",
  "access_item": "role:Finance-AP-Approver",
  "requested_for": "opm-hrit:emp:00294417",
  "approval_authority": "app-owner",
  "risk_tier": "2",
  "justification": "New AP approver duty assigned by department transfer; approved by App Owner per Tier-2 chain (Dept Owner -> App Owner)."
}
```

Expected response (`201`):

```json
{
  "ok": true,
  "ritm": "RITM0012345",
  "ritm_sys_id": "<sc_request sys_id>",
  "sam_request_id": "IIQ-REQ-2026-0000481",
  "lineage_sys_id": "<x_fed_day2_ops_integration sys_id>",
  "verified": true
}
```

### 2. Success — Tier 1 (`payloads/sam-push-success-tier1.json`)

The highest chain: Dept Owner → App Owner → **IGO (final)**. Note the
justification's caveat — a successful push here only means the RITM
correlates; a Tier-0/protected-group *target* is still refused at
**actuation** by `AdHybridClient` (see
`atf/atf-negative-protected-group-both-directions.xml`). Push acceptance and
actuation authorization are separate clauses on purpose.

### 3. Success — Tier 3 (`payloads/sam-push-success-tier3.json`)

The lightest chain: Dept Owner only, for a low-risk item.

### 4. Required-field failure (`payloads/sam-push-missing-fields.json`) — `400`

```json
{
  "sam_request_id": "IIQ-REQ-2026-0000600",
  "requested_for": "opm-hrit:emp:00294417"
}
```

Response:

```json
{ "ok": false, "error": "bad_request" }
```

The detailed reason (which fields are missing) goes to the system log, not
the response body — an authenticated-but-hostile caller does not get a map
of the contract (see the endpoint header's design goal #6).

### 5. Unresolved `requested_for` (`payloads/sam-push-unresolvable-subject.json`) — `422`

Same shape as a valid push; only the correlation id is wrong (typo,
not-yet-reconciled identity, or an identity that resolved to more than one
active `sys_user`). Response: `{ "ok": false, "error": "unresolved_subject" }`.

### 6. Signed push (`payloads/sam-push-signed-jws.json`)

Only relevant once `x_fed_day2_ops.sam_jws_public_key` is configured — see
the field map above and `verifyWithSam()` in `scripted-rest/sam_inbound_ritm.js`
for exactly how the `jws` claims are validated and bound to the top-level
`sam_request_id`.

## What is *not* shown here

A genuine `201` from a live pull-verify call (`fetchIdentityRequest` reaching
a real IIQ/ISC instance) needs a live tenant — `fetchIdentityRequest`/
`verifyJws` are deliberate fail-closed stubs until a tenant wires them (see
the "NOT IMPLEMENTED" comments in `script-includes/SamCorrelationClient.js`).
In `test_mode` they return the same canned "approved" shape as sample #1
above, which is what lets `atf/atf-sam-happy-path.xml` exercise the full
contract-validation → pull-verify → lineage → RITM-bind sequence with no live
SAM connectivity. Test-mode vs. live-mode behavior is exercised explicitly by
`atf/atf-sam-testmode-vs-live.xml`.
