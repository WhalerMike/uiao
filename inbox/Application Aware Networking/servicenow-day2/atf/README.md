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
| **negative — standing privilege** | A `privileged` group grant with no `expiry` **fails at preflight** (least privilege, AC-6). |
| **negative — unreconciled target** | An action whose target does not match an authoritative identity routes to the reconcile-exception queue (CM-8), not to closure. |

## Build

Author these as `sys_atf_test` records in the scoped app (one Test per row above),
each driving the "Governed Day-2 Request" flow with the catalog inputs that trigger
the asserted path, then export them into the update set. Keep them `test_mode`-driven
so CI/sub-prod runs need no tenant credentials.
