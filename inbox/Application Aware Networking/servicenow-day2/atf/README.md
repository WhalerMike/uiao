# ATF tests — Day-2 Operations app

Automated Test Framework coverage for the `x_ssa_day2_ops` scoped app, runnable in
a **sub-production** instance via `x_ssa_day2_ops.test_mode = 'true'` — the Script
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

## Build

The eight tests above are **authored as `sys_atf_test` records** in this folder —
one file per test, each driving the "Governed Day-2 Request" flow with the catalog
inputs that trigger the asserted path:

| File | Test |
|---|---|
| `atf-happy-path.xml` | happy path — password reset closes with evidence |
| `atf-negative-self-approve.xml` | requester == approver fails preflight (SoD, CM-5) |
| `atf-negative-sod-indeterminate.xml` | unpopulated requester/approver fails **closed** |
| `atf-negative-standing-privilege.xml` | privileged grant with no expiry fails (AC-6) |
| `atf-negative-privileged-string.xml` | `privileged: 'true'` (string) still triggers the expiry rule |
| `atf-negative-verify-read-failure.xml` | verify fails closed when the confirming re-read fails |
| `atf-negative-verify-wrong-state.xml` | verify catches observed != intended |
| `atf-negative-unreconciled-target.xml` | unreconciled target routes to the exception queue (CM-8) |

They are `test_mode`-driven, so a sub-prod/CI run needs **no tenant credentials**.
Import them into the scoped app and add them to a Test Suite; the negatives are the
ones that prove the safety gates actually fire — a suite of only happy paths proves
nothing about a control.
