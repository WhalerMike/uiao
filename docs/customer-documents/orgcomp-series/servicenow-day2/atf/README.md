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

The four **hybrid** rows cover the Current State (AD-mastered) edition's router and
AD leg (`AdHybridClient`). They **ship only with the Active Directory (Current
State) download** — the HRIT (2027 Target) edition has no AD leg, so the base
suites plus the non-hybrid negatives are all it carries.

## Build

The 17 tests above are **authored as `sys_atf_test` records** in this folder —
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

They are `test_mode`-driven, so a sub-prod/CI run needs **no tenant credentials**.
Import them into the scoped app and add them to a Test Suite; the negatives are the
ones that prove the safety gates actually fire — a suite of only happy paths proves
nothing about a control. 14 of 17 pass as authored against the remediated code;
`atf-negative-unreconciled-target.xml` needs a live instance to exercise its
catalog/UI path, and the two `verify-read-failure`/`verify-wrong-state` tests are
flagged open above (see `../CURRENT-STATE-START-HERE.md` §5 for the design
question blocking them). See the PDI live-validation runbook for running all 17
for real, not just reading the assertions.
