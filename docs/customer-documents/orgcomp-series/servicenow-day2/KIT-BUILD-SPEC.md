# Day-2 Automation Kit — Build Specification

> The specification an implementation team needs to **build the full
> `x_fed_day2_ops` scoped app in a ServiceNow sub-production instance and export
> it as an update set.** The kit ships every artifact that can be authored as
> source (Script Includes, the scripted REST resource, control maps, the ATF
> suites, one representative variable set, the Flow blueprint). This document
> specifies the platform records that **must be built on an instance and cannot
> ship as authentic authored XML** — tables, ACLs, roles, catalog items, the Flow,
> and the update-set assembly — with exact field lists derived from the code, so
> nothing is left to guesswork.
>
> **Why these are built, not shipped:** an update-set / Flow / ATF XML is a
> machine-serialized snapshot (sys_ids, checksums, platform metadata). A
> hand-authored one would look importable and then fail or drift — worse than a
> spec. So you build them from this spec and export the real thing.

**Date Code:** 2026-07-22 11:00 ET · **Scope:** FedRAMP Moderate / GCC Moderate ·
**Audience:** the implementation team (ServiceNow + Entra/Azure + SAM)

## 0. Build order (summary)

1. Scoped app `x_fed_day2_ops` + roles (§1)
2. Tables (§2)
3. System properties + Connection & Credential aliases (see KIT-VARIABLES-REFERENCE.md)
4. Script Includes — import the kit's `.js` (§3)
5. Scripted REST API + ACLs (§4, §5)
6. Catalog items + variable sets (§6)
7. The Governed Day-2 Request Flow (§7)
8. ATF tests (§8)
9. Capture everything in one update set and export (§9)

Build in sub-prod with `x_fed_day2_ops.test_mode = true` throughout; prove the ATF
suite; then promote per the Implementation Guide.

## 1. Scoped application + roles

| Object | Value | Purpose |
|---|---|---|
| Scoped app | `x_fed_day2_ops` | Namespace for every record below |
| Role | `x_fed_day2_ops.operator` | May submit catalog items |
| Role | `x_fed_day2_ops.approver` | May approve; enforced ≠ requester |
| Role | `x_fed_day2_ops.sam_inbound` | The IIQ integration user only — gates the SAM push endpoint |
| Role | `x_fed_day2_ops.admin` | Manage properties, aliases, tables |

## 2. Tables (exact fields — derived from the code's `setValue`/`_insert` calls)

Create two scoped tables. The columns below are **every field the Script Includes
write** — if a column is missing, the write silently drops (ServiceNow ignores
unknown fields), so the closure record would be incomplete. All columns are
String unless noted.

### 2a. `x_fed_day2_ops_evidence` — the closure/evidence record (`tbl_evidence`)

Written by `MacdrOrchestrator._writeEvidence` and `Day2NativeActuator`.

| Column | Type | Written by | Meaning |
|---|---|---|---|
| `record_type` | String | both | `macdr_closure` \| `authorization_verdict` \| … |
| `verb` | String | orchestrator | Move/Add/Change/Deletion/Reset |
| `control` | String | both | NIST control (e.g. `AC-2`) |
| `ksi` | String | orchestrator | comma-separated KSI ids |
| `ritm` | String | orchestrator | the request item number |
| `sam_request_id` | String | orchestrator | the SAM/IIQ IdentityRequest id |
| `pim_activation_id` | String | orchestrator | the JIT elevation id (who-could-act) |
| `closed` | True/False (String) | orchestrator | did the task close |
| `stopped_at` | String | orchestrator | the failing clause, if any |
| `trail` | String (max length ↑) | orchestrator | JSON of the full MACD-R trail |
| `verdict` | String | native actuator | SA-9 authorization verdict |
| `approver` | Reference (`sys_user`) | native actuator | the named approver |
| `marketplace_ref` | String | native actuator | FedRAMP Marketplace reference |
| `integration` | Reference (integration row) | native actuator | link to the integration record |
| `boundary` | String | both | `gcc-moderate` |

> Set `trail` to a large max length (e.g. 8000) — it stores the serialized
> clause-by-clause trail.

### 2b. `x_fed_day2_ops_integration` — correlation + SaaS intake (`tbl_integration`)

Written by `SamCorrelationClient.recordLineage`, `Day2NativeActuator`, and the
inbound REST resource. (An instance that already carries a SaaS-integration table
may repoint `tbl_integration` to it — the property exists for that.)

| Column | Type | Written by | Meaning |
|---|---|---|---|
| `record_type` | String | all | `sam_lineage` \| `sam_push_outcome` \| `requested` \| … |
| `ritm` | String | SAM client / REST | the request item number |
| `ritm_sys_id` | String | SAM client (`attachRitmToLineage`) | the request item's `sys_id` — set once the RITM exists; was already written by the code but missing from this table's build doc, so a build that stopped at the columns above dropped it silently |
| `sam_flavor` | String | SAM client | `identityiq` \| `isc` |
| `sam_request_id` | String | SAM client / REST | the SAM-side request id. **`sam_lineage` rows only** — telemetry uses `sam_request_ref`. Carries the UNIQUE INDEX below, which is only implementable because of that split |
| `sam_request_ref` | String | SAM client (`recordPushOutcome`) | the SAM-side request id on `sam_push_outcome` telemetry rows. A **separate column from `sam_request_id` on purpose**: telemetry writes one row per push *attempt*, so many rows share a request id, and the inbound endpoint's idempotency lookup keys on `sam_request_id`. Writing telemetry into `sam_request_id` made that lookup match a prior refusal and silently drop the retried request |
| `sam_source_id` | String | SAM client | IIQ Application / ISC source |
| `entra_object_id` | String | SAM client | the subject in the directory |
| `verified_by` | String | SAM client (`recordLineage`) | `pull-verify` \| `jws` — how the push was independently verified (P0-7) |
| `verified_at` | String (GlideDateTime value) | SAM client | when verification ran |
| `verified_authority` | String | SAM client | the VERIFIED approval authority (never the caller-asserted one) |
| `verified_status` | String | SAM client | the VERIFIED SAM-side status at push time |
| `verified_item` | String | SAM client | the VERIFIED access item |
| `test_mode` | True/False (String) | SAM client | was this row written while `test_mode` was honoured — machine-filterable, same purpose as the evidence table's stamp |
| `synthetic` | True/False (String) | SAM client | mirrors `test_mode`; a monitoring query MUST exclude `synthetic=true` rows (see `KIT-USAGE-SAM-INTEGRATION.md` "Monitoring the inbound endpoint") |
| `vendor` | String | native actuator | SaaS vendor (Lane F) |
| `business_owner` | Reference (`sys_user`) | native actuator | integration owner |
| `business_need` | String | native actuator; SAM client (`sam_push_outcome` rows) | justification (native actuator) or `http_status=<n> reason=<code>` (push-outcome telemetry) |
| `attributes_shared` | String | native actuator | directory attributes leaving the boundary (AC-20) |
| `state` | String | native actuator; SAM client (`sam_push_outcome` rows) | `requested` → … (native actuator), or `accepted` \| `refused` (push-outcome telemetry) |
| `boundary` | String | all | `gcc-moderate` |

### 2b-i. Required unique index

`scripted-rest/sam_inbound_ritm.js` calls this out as a deployment requirement,
not an option, and until now it was specified in that file's header comment and
nowhere in this build spec — so a builder following §2 alone did not create it,
leaving the endpoint's idempotency guarantee as a single racy check-then-insert
with no database-level backstop.

| Index | Table | Columns | Unique |
|---|---|---|---|
| `sam_request_id_unique` | `x_fed_day2_ops_integration` | `sam_request_id` | **yes** |

Two things make this correct only in combination with the column split above:

- **It must be on `sam_request_id` alone**, not `(record_type, sam_request_id)`.
  A composite is no safer: `recordPushOutcome` writes a row per push *attempt*,
  so `(sam_push_outcome, X)` legitimately repeats.
- **It is only implementable because telemetry no longer writes
  `sam_request_id`.** While it did, any unique index over that column would have
  rejected every telemetry insert after the first — swallowed by
  `recordPushOutcome`'s own `try/catch`, which returns `{ok:false}` that no
  caller reads. The failure would have been invisible.

`sam_lineage` is one row per correlated request, so uniqueness on that column is
exactly the constraint the endpoint's check-then-insert needs.

> `record_type = sam_push_outcome` rows are operational telemetry (one per
> inbound push attempt, accepted or refused) written by
> `SamCorrelationClient.recordPushOutcome` — see "Monitoring the inbound
> endpoint" in `KIT-USAGE-SAM-INTEGRATION.md`. They reuse this table rather
> than a new one, distinguished by `record_type` the same way `sam_lineage`
> and the native-actuator's `requested` rows already are.

## 3. Script Includes

Import the kit's `script-includes/*.js` into scope `x_fed_day2_ops` (client-callable
= false; accessible from all application scopes = false). The set:

`EntraHelpdeskClient`, `EntraHelpdeskGate`, `AzureArmClient`, `PimActivationClient`,
`SamCorrelationClient`, `MacdrOrchestrator`, `Day2NativeActuator`,
`EntraAppRegClient`, `EntraSaasClient`, `AcmeCredentialClient`,
`TeamsTelephonyClient`, `TerraformCpgClient`.

## 4. Scripted REST API (the IIQ-push endpoint)

| Field | Value |
|---|---|
| API name | `x_fed_day2_ops/sam` |
| Resource | `POST /ritm` |
| Script | `scripted-rest/sam_inbound_ritm.js` |
| Requires authentication | **true** |
| ACL / required role | `x_fed_day2_ops.sam_inbound` |
| Base URL (result) | `POST /api/x_fed_day2_ops/sam/ritm` |

## 5. ACLs (least privilege — build these explicitly)

| Operation | Table / resource | Roles allowed |
|---|---|---|
| create/read | `x_fed_day2_ops_evidence` | `x_fed_day2_ops.admin`, app (script) |
| create/read | `x_fed_day2_ops_integration` | `x_fed_day2_ops.admin`, `x_fed_day2_ops.sam_inbound` (create), app |
| execute | `POST /api/x_fed_day2_ops/sam/ritm` | `x_fed_day2_ops.sam_inbound` only |
| submit | catalog items (§6) | `x_fed_day2_ops.operator` |
| approve | catalog approvals | `x_fed_day2_ops.approver` (≠ requester, enforced by the Gate) |

Evidence and integration rows are **write-once**: no update/delete ACL for
operators — a closure record must not be editable after the fact (AU-9).

## 6. Catalog items + variable sets (the roster)

Each control map is the SSOT for its lane's items; build one catalog item per map
entry, bound to the variable set for that lane. Counts and the map that defines
each item's control/approval/actuator/KSI:

| Lane | Map file | Items | Variable set |
|---|---|---|---|
| Helpdesk (Lane C) | `helpdesk-control-map.json` | 10 | `catalog/variable-set-helpdesk-identity.xml` (shipped exemplar) |
| Landing zone (Lane D) | `landingzone-control-map.json` | 5 | build per §6a |
| App registration (Lane E) | `appreg-control-map.json` | 5 | build per §6a |
| Telephony (§4) | `telephony-control-map.json` | 6 | build per §6a |
| SaaS integration (Lane F) | `saas-control-map.json` | 24 | build per §6a |

**Total: 50 governed catalog items.**

### 6a. Variable-set build rule (the form is the contract)

For each lane, build a variable set the way `catalog/variable-set-helpdesk-identity.xml`
does it, then let `catalog/contract_check.py` enforce it:

- Every parameter the lane's actuator client reads → a variable with `<map_to>`
  naming that parameter, **or** `<resolved_by_mid>` for a secret (never a form field).
- Every field the Gate's `preflight()` reads (`requester_id`, `approver_id`,
  `privileged`, `expiry`) → a variable.
- Identity fields are reference lookups (type 7), not free text.
- `contract_check.py` fails the build if the form isn't a superset of what the
  client + gate require, or if a secret is `<map_to>`. Run it in pre-commit + CI
  (already wired as `aan-day2-catalog-contract`).

The shipped helpdesk variable set is the worked template; the other four lanes
follow the same shape against their control map.

## 7. The Governed Day-2 Request Flow

Build in Flow Designer per `flow/flow-blueprint.md`. The actuation step calls:

```
MacdrOrchestrator.run(request, actuate, verifyArgs)
```

passing `requester_id`, `approver_id`, `privileged`, `expiry`, `control`, `ksi`,
`verb`, `ritm`, `sam_request_id` from the catalog variables. The orchestrator
threads the five MACD-R clauses (authorize → elevate → actuate → verify →
evidence) and writes the evidence row (§2a). Privileged items route through
`PimActivationClient.activate` before actuation. The approver field must enforce
requester ≠ approver (the Gate's `preflight` is the backstop).

## 8. ATF tests

Import the kit's `atf/*.xml` as the starting suite: `atf-happy-path` plus seven
negatives (self-approve, standing-privilege, unreconciled-target,
verify-wrong-state, SoD-indeterminate, verify-read-failure, privileged-string).
Add per-lane happy paths as you build each lane. All run with
`x_fed_day2_ops.test_mode = true`.

## 9. Assemble + export the update set

1. Create an update set `x_fed_day2_ops v1.0` and make it current.
2. Build §1–§8 in order — every record is captured into the update set.
3. Add the imported Script Includes and the scripted REST resource to the update
   set (edit-and-save each once so it's captured).
4. Verify completeness: run `python check_actuator_coverage.py` and
   `python check_l3_ceiling.py` against the repo to confirm every map item names a
   real method or a declared gap.
5. Export the update set XML. **This is the artifact the `update-set/` folder's
   README describes** — it is produced here, not shipped, for the reason in the
   banner above.

## What ships vs what you build

| Artifact | Ships in the kit | You build+export |
|---|---|---|
| Script Includes (`.js`) | ✅ | — |
| Scripted REST resource (`.js`) | ✅ | — |
| Control maps (`.json`) | ✅ | — |
| ATF suites (`.xml`) | ✅ (8) | + per-lane happy paths |
| Helpdesk variable set (`.xml`) | ✅ (exemplar) | + 4 lanes |
| Flow | blueprint (`.md`) | Flow Designer build |
| Tables, ACLs, roles | this spec (§1–§5) | build on instance |
| Catalog items (50) | control maps + this spec | build on instance |
| Update set (`.xml`) | README + this spec (§9) | export from sub-prod |

## Cross-references

- `KIT-IMPLEMENTATION-GUIDE.md` — the phased stand-up (this spec is the record-level detail behind it).
- `KIT-VARIABLES-REFERENCE.md` — properties, aliases, credentials.
- `KIT-SCRIPTS.md` — what each Script Include does.
- `catalog/contract_check.py`, `check_actuator_coverage.py`, `check_l3_ceiling.py` — the build-time gates.
