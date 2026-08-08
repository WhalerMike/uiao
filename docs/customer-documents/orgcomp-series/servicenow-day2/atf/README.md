# ATF tests — Day-2 Operations app

Automated Test Framework coverage for the `x_fed_day2_ops` scoped app, runnable in
a **sub-production** instance via `x_fed_day2_ops.test_mode = 'true'` — the Script
Includes return deterministic canned values, so the whole Flow exercises with **no
live Microsoft Graph connectivity**. Never enable `test_mode` in production.

Mirrors the DDI app's ATF pattern (`infoblox-ddi-book/servicenow-app/atf/`): one
happy path plus the negative tests that prove the safety gates actually fire.

| Test | Asserts |
|---|---|
| **happy-path** | A password-reset request runs the full loop — preflight ok → approval → actuate (`resetPassword`) → verify gate → CMDB reconcile → closed with evidence. |
| **negative — self-approve** | A request whose `approver_id == requester_id` **fails at preflight** (separation of duties, CM-5) and never actuates. |
| **negative — SoD indeterminate** | A request with `requester_id` or `approver_id` **unpopulated** fails at preflight — the SoD check is fail-closed, not skipped when an id is empty. |
| **negative — standing privilege** | A `privileged` group grant with no `expiry` **fails at preflight** (least privilege, AC-6). |
| **negative — privileged as string** | `privileged: 'true'` (a ServiceNow catalog variable, a string) with no `expiry` still **fails at preflight** — the coercion works, the string form does not slip through. |
| **negative — verify read failure** | When the post-actuation Graph re-read returns non-2xx, `verify()` returns **ok:false (inconclusive)** and the request does **not** close — a failed read is never treated as closure. |
| **negative — verify wrong state** | `disableUser` whose re-read shows `accountEnabled:true` returns **ok:false** — a 2xx on the read is not closure; the property must be observed. |
| **negative — unreconciled target** | An action whose target does not match an authoritative identity routes to the reconcile-exception queue (CM-8), not to closure. |
| **hybrid — synced → AD leg** | A synced object (`onPremisesSyncEnabled = true`) classifies as AD-mastered and the AD-leg disable reports an AD-mastered, syncing write. Current State edition. |
| **hybrid — cloud-only → Graph leg** | A cloud-only object (`onPremisesSyncEnabled = false`) does **not** classify as AD-mastered — the write stays on the Graph leg. |
| **negative — unclassified route** | An unclassifiable object (null / empty / no sync flag / stringified flag) is **never** treated as AD-mastered — the router fails closed to clause `route` instead of writing to the wrong master. |
| **hybrid — sync-projection verify** | The AD-leg create flags `synced:true` so the Flow's verify allows for Entra Connect latency on the cloud-side re-read — a dispatch, or an un-synced read, is not closure. |
| **negative — AD parameter injection (P0-1)** | A hostile attribute *name* (not just value) reaching `setUserAttributesAd` is refused by `AdHybridClient`'s per-action allowlist, not merely escaped. |
| **negative — forced leg (NEW-1)** | A caller-supplied `actuation_leg: 'ad'` on a Graph-only request does **not** skip PIM elevation — the leg is server-derived from a live Graph read, never accepted from the request. |
| **negative — no origin (P0-6)** | A request with no RITM/SAM origin is refused at clause 1 before `ritm`/`sam_request_id` ever reach the evidence record. |
| **negative — protected group, both directions (NEW-2)** | Both `addGroupMemberAd` **and** `removeGroupMemberAd` refuse a Tier-0/protected group — stripping a break-glass account out of Domain Admins is blocked the same as adding to it. |
| **negative — test_mode environment binding (P0-5)** | `test_mode = true` is refused unless the instance is declared non-prod (`x_fed_day2_ops.nonprod_instances`) — a stray `test_mode` flag on a production instance cannot emit a false-but-plausible evidence trail. |
| **SAM — happy path** | A well-formed IIQ push validates, pull-verifies (canned in `test_mode`), writes lineage *before* the RITM exists, then binds the RITM — the ServiceNow-side sequence of a 201, and the shape of the write-back the SDIM reads for `IdentityRequest.externalTicketId`. |
| **SAM negative — missing fields** | A push missing any of `sam_request_id` / `access_item` / `requested_for` / `approval_authority` (or blank/whitespace-only, or an empty body) fails contract validation — refused before pull-verify or lineage. |
| **SAM negative — missing role** | A caller without the explicit `x_fed_day2_ops.sam_inbound` grant fails the AuthZ check — including an `admin`-scoped caller, the exact `hasRole()` vs `hasRoleExactly()` gap the P0-7 remediation closed. |
| **SAM negative — unresolved subject** | A `requested_for` correlation id matching zero active users, or matching more than one (ambiguous), both fail `resolveSubject()` — refused (422), never resolved to the first row. |
| **SAM — idempotent re-push** | A second push carrying a `sam_request_id` that already correlated resolves to the SAME RITM rather than creating a second one — the SDIM-retry case the troubleshooting table documents as safe. |
| **SAM negative — pull-verify unavailable** | With neither `iiq_verify_endpoint` nor `sam_jws_public_key` configured (the shipped default), and in live mode generally, `fetchIdentityRequest`/`verifyJws` refuse rather than trust the caller's assertion — "refuses every push" is the intended state, not a bug to work around. |
| **SAM — test_mode vs. live mode** | `getRequestStatus`/`fetchIdentityRequest` return canned "approved" data under `test_mode` and fail-closed/inconclusive results under live mode with no SAM reachable, and the flip is fully reversible — the dual-mode contract `SamCorrelationClient`'s header promises actually holds. |

The four **hybrid** rows cover the Current State (AD-mastered) edition's router and
AD leg (`AdHybridClient`). They **ship only with the Active Directory (Current
State) download** — the HRIT (2027 Target) edition has no AD leg, so the base
suites plus the non-hybrid negatives are all it carries.

## Build

The 24 tests above are **authored as `sys_atf_test` records** in this folder —
one file per test, each driving the "Governed Day-2 Request" flow with the catalog
inputs that trigger the asserted path:

| File | Test |
|---|---|
| `atf-happy-path.xml` | happy path — password reset closes with evidence |
| `atf-negative-self-approve.xml` | requester == approver fails preflight (SoD, CM-5) |
| `atf-negative-sod-indeterminate.xml` | unpopulated requester/approver fails **closed** |
| `atf-negative-standing-privilege.xml` | privileged grant with no expiry fails (AC-6) |
| `atf-negative-privileged-string.xml` | `privileged: 'true'` (string) still triggers the expiry rule |
| `atf-negative-verify-read-failure.xml` | verify fails closed when the confirming re-read fails — **open, pending a test_mode failure-simulation design decision** |
| `atf-negative-verify-wrong-state.xml` | verify catches observed != intended — **open, same pending decision** |
| `atf-negative-unreconciled-target.xml` | unreconciled target routes to the exception queue (CM-8) — catalog/UI-only, not executable outside a live instance |
| `atf-hybrid-route-synced-to-ad.xml` | synced object → AD leg; AD-leg dispatch never asserts an observation field |
| `atf-hybrid-route-cloudonly-to-graph.xml` | cloud-only object stays on the Graph leg |
| `atf-negative-route-unclassified.xml` | unclassifiable object never routes to AD — fails closed (clause `route`) |
| `atf-hybrid-verify-sync-projection.xml` | AD-leg write flags sync projection for latency-aware verify |
| `atf-negative-ad-parameter-injection.xml` | hostile attribute name refused by the allowlist, not escaped (P0-1) |
| `atf-negative-forced-leg.xml` | actuation leg is server-derived, never caller-supplied (NEW-1) |
| `atf-negative-no-origin.xml` | no RITM/SAM origin → refused at clause 1 (P0-6) |
| `atf-negative-protected-group-both-directions.xml` | Tier-0 group refused on add **and** remove (NEW-2) |
| `atf-negative-testmode-environment-binding.xml` | `test_mode` refused off a declared non-prod instance (P0-5) |
| `atf-sam-happy-path.xml` | SAM push validates, pull-verifies (canned), writes lineage first, binds the RITM |
| `atf-sam-negative-missing-fields.xml` | required-field / blank-field / empty-body pushes fail contract validation (400) |
| `atf-sam-negative-missing-role.xml` | caller without the explicit `sam_inbound` grant fails AuthZ, including `admin` (403) |
| `atf-sam-negative-unresolved-subject.xml` | zero-match and ambiguous-match `requested_for` both fail to resolve (422) |
| `atf-sam-idempotent-repush.xml` | a re-push of a correlated `sam_request_id` resolves to the same RITM, not a duplicate |
| `atf-sam-negative-pull-verify-unavailable.xml` | unconfigured (or unwired live-mode) verification refuses every push |
| `atf-sam-testmode-vs-live.xml` | canned `test_mode` responses vs. fail-closed live-mode behavior, and the flip is reversible |

They are `test_mode`-driven, so a sub-prod/CI run needs **no tenant credentials**.
Import them into the scoped app and add them to a Test Suite; the negatives are the
ones that prove the safety gates actually fire — a suite of only happy paths proves
nothing about a control. 21 of 24 pass as authored against the remediated code;
`atf-negative-unreconciled-target.xml` needs a live instance to exercise its
catalog/UI path, and the two `verify-read-failure`/`verify-wrong-state` tests are
flagged open above (see `../CURRENT-STATE-START-HERE.md` §5 for the design
question blocking them). See the PDI live-validation runbook for running all 24
for real, not just reading the assertions.

The seven **SAM** tests exercise `SamCorrelationClient` and `sam_inbound_ritm.js`'s
gates directly (contract validation, role predicate, identity resolution,
idempotency lookup, verification mode) rather than driving a live HTTP round trip
through the Scripted REST resource — the same scoping choice this repo already
makes for `atf-negative-unreconciled-target.xml`. See `atf-sam-happy-path.xml`'s
header for what that does and does not prove, and `examples/sam-push-payloads.md`
for the payload fixtures they're built from.
