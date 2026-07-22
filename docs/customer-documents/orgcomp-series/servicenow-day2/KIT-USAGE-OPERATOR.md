# Day-2 Automation Kit — Operator Usage Guide

> How a service-desk operator uses the governed catalog day to day. Every task is
> a **request**, not a portal click: you submit a typed catalog item, the approval
> the control requires holds it, the kit actuates through the in-boundary MID under
> a just-in-time role, re-reads to confirm the change took, and writes the
> evidence. You never hold standing admin, and you never run a pasted command.
> This is the [Operator Runbook](../OrgComp_Operator_Runbook_Day2_Compliant.qmd)
> in the operator's chair, with the catalog item and the fields for each task.

**Date Code:** 2026-07-21 16:30 ET · **Audience:** Service-desk / CST operators ·
**Scope:** FedRAMP Moderate / GCC Moderate

## The one loop every task follows

1. **Submit** the catalog item — fill the typed fields; the form is the contract,
   it can only send what the item declares.
2. **Approval** routes automatically to the gate the control requires. You do not
   approve your own request — the system refuses `requester == approver`.
3. **Elevate** — for privileged items you (or the assigned operator) activate the
   PIM Privileged Access Group when prompted: justification + MFA, time-boxed. No
   activation, no action.
4. **Actuate & verify** — the kit runs the change through the MID and re-reads the
   target to confirm it took. A green write is not "done"; the re-read is.
5. **Close** — the request closes carrying its evidence (who asked, who approved,
   the PIM activation id, the result, the verify verdict). You do not type "done."

If any step fails, the request stops there and records why. That is correct — a
task that skipped a step is not something you should force through.

> **How each task actuates.** The diagram under each task shows its cloud-native
> write path — actuated directly in Entra Graph / Azure ARM, with
> joiner/mover/leaver originating from the OPM-HRIT SSOT.

## What you never do

- Reset a password or MFA on an emailed request **without identity re-proofing**.
- Email a temporary password or credential **to the requesting mailbox**.
- Run a **command pasted from a request** — submit the typed catalog item instead.
- Use **standing global/portal admin** — activate the PAG instead.
- Approve a request you submitted.

## The tasks

### Password reset — `entra.credential.password_reset` (IA-5)

- **Catalog item:** Password reset.
- **Fields:** target user (resolves against the identity record), verification
  method used.
- **Approval:** self-service where policy allows; otherwise service-desk with
  identity re-proofing against the record.
- **Delivery:** the kit issues a **Temporary Access Pass / out-of-band** credential
  — never a password mailed to the requester.
- **Done when:** the request closes with the verify confirming the old credential
  is dead and a one-time credential is issued out of band.

![Password reset target-state write path.](servicenow-day2/figs/day2kit-target-task-01-password-reset.png){fig-alt="Password reset 2027 target task card: cloud-native, reset directly in Entra; emits NIST IA-5, feeds KSI-IAM." width="100%"}

### MFA method reset — `entra.credential.mfa_reset` (IA-5, the takeover verb)

- **Catalog item:** MFA method reset.
- **Fields:** target user, **re-proofing evidence** (required), risk tier.
- **Approval:** service-desk **+ verify** — identity-proof to policy before you
  submit; privileged/sensitive accounts require a second approver.
- **Note:** every MFA reset raises a security alert; repeated resets on one
  identity are a detection signal, not routine.
- **Done when:** the old method is removed and a new enrollment is pending under
  the user's control, with the re-proofing captured.

![MFA method reset target-state write path.](servicenow-day2/figs/day2kit-target-task-02-mfa-reset.png){fig-alt="MFA method reset 2027 target task card: cloud-native, no AD leg — Graph deletes the method, re-enrollment required, log and alert; emits NIST IA-5, feeds KSI-IAM." width="100%"}

### Account unlock — `entra.credential.account_unlock` (IA-5)

- **Catalog item:** Account unlock. Self-service where policy allows.
- **Note:** repeated unlocks on one account are a detection signal — the kit
  surfaces the count.

### New account / joiner — `entra.jml.joiner` (AC-2)

- **Catalog item:** New account (Joiner). **Originates from the HR joiner event**,
  not an ad-hoc ask; a pre-HR provision is the flagged exception path.
- **Fields:** identity record; entitlements are **derived** (department/role/
  location) — you do not hand-pick groups.
- **Approval:** manager + identity.
- **Delivery:** credentials **out of band** (TAP), never cleartext email.
- **Done when:** the account exists with exactly the derived entitlements and an
  owner anchored.

![Joiner target-state write path.](servicenow-day2/figs/day2kit-target-task-03-joiner.png){fig-alt="Joiner 2027 target task card: OPM-HRIT origin, cloud-native provisioning into Entra with derived entitlements; emits NIST AC-2 and IA-4, feeds KSI-IAM." width="100%"}

### De-provision / leaver — `entra.jml.leaver` (AC-2)

- **Catalog item:** De-provision (Leaver). Originates from the HR leaver event.
- **What it does:** disable, **revoke sessions and tokens**, deprovision federated
  apps, reassign owned objects — including the leaver's **anchored non-human
  estate** (owned service accounts / app registrations transfer).
- **Done when:** the account is unusable everywhere, zero live sessions, and no
  orphaned objects or ownerless non-human identities remain.

![Leaver target-state write path.](servicenow-day2/figs/day2kit-target-task-05-leaver.png){fig-alt="Leaver 2027 target task card: OPM-HRIT origin, cloud-native disable in Entra, sessions revoked, owned objects reassigned; emits NIST AC-2, feeds KSI-IAM." width="100%"}

### Role / scope change (mover) — `entra.jml.mover` (AC-6)

- **Catalog item:** Role/scope change. Originates from the HR mover event.
- **What it does:** re-derive group/license/app access to the new role **and remove
  stale entitlements from the old one**.
- **Done when:** the derivation matches the record and stale access is gone.

![Mover target-state write path.](servicenow-day2/figs/day2kit-target-task-04-mover.png){fig-alt="Mover 2027 target task card: OPM-HRIT origin, cloud-native re-derivation of access in Entra with stale grants removed; emits NIST AC-6 and AC-2, feeds KSI-IAM." width="100%"}

### Group membership / RBAC grant — `entra.access.group_assignment` (AC-6)

- **Catalog item:** Group membership request (or an Azure RBAC grant).
- **Origin:** for Tier-1/2 privileged access, the request **originates in SAM**
  (SailPoint IdentityIQ) and arrives as a correlated RITM — you execute it, you do
  not originate it. Lower-tier group adds may be raised in the catalog directly.
- **Approval:** owner + approver; privileged grants **must carry an expiry** — a
  standing elevation from a click is refused.
- **Elevate:** activate the PAG first for privileged targets.
- **Done when:** the membership/assignment is present and, if privileged,
  time-bound; the verify re-read confirms it.

![Group membership target-state write path.](servicenow-day2/figs/day2kit-target-task-06-group-membership.png){fig-alt="Group membership 2027 target task card: cloud-native, membership managed directly in Entra with expiry on privileged grants; emits NIST AC-6, feeds KSI-IAM." width="100%"}

![Azure RBAC grant target-state write path.](servicenow-day2/figs/day2kit-target-task-07-azure-rbac.png){fig-alt="Azure RBAC 2027 target task card: cloud-native ARM, custom least-privilege role at a scoped level; emits NIST AC-6, feeds KSI-IAM." width="100%"}

### License assignment — `entra.access.license_assignment` (AC-2)

- **Catalog item:** License assignment. Group-based licensing preferred.
- **Approval:** manager (or a SAM-originated RITM with departmental-owner approval
  for governed licenses).

![License assignment target-state write path.](servicenow-day2/figs/day2kit-target-task-08-license.png){fig-alt="License assignment 2027 target task card: cloud-native, assign the SKU in Entra or via a cloud licensing group; emits NIST AC-2, feeds KSI-IAM." width="100%"}

### Conditional-Access exception — `entra.access.ca_exception` (AC-3)

- **Catalog item:** Conditional-Access exception — **reuses the mandatory
  break-glass-exclusion + expiry + review pattern**; you do not craft a bespoke
  exclusion.
- **Approval:** security approver.

### Guest / B2B invite — `entra.access.guest_invite` (AC-2)

- **Catalog item:** Guest / B2B invite.
- **Approval:** sponsor + security; the invite carries a sponsor and an expiry.

![Guest invite target-state write path.](servicenow-day2/figs/day2kit-target-task-09-guest.png){fig-alt="Guest invite 2027 target task card: cloud-native only, Graph invitation with sponsor and expiry; emits NIST AC-2, feeds KSI-IAM." width="100%"}

### Admin consent (third-party app) — Lane F (AC-20, SA-9)

- **Do not** approve consent by judgment. Submit the Lane F integration request;
  the **authorization verdict is recorded before consent is configured**, consent
  is scoped to the minimum the app needs, and the app's endpoints are declared.
  See `KIT-USAGE-SAM-INTEGRATION.md` and Vol IX Book 05 for the governed path.

![SaaS admin consent target-state write path.](servicenow-day2/figs/day2kit-target-task-10-admin-consent.png){fig-alt="SaaS admin consent 2027 target task card: cloud-native only, record the SA-9 authorization verdict before scoping app consent; emits NIST SA-9 and AC-20, feeds KSI-SCR." width="100%"}

### Morning check / log review — `saas.audit.review` (CA-7 / AU-6)

- **Not a request** — a scheduled, read-only routine. It queries recent
  lifecycle / auth events, reconciles the estate to the evidence table and the
  CMDB, and opens tasks / findings from the deltas. It writes nothing.
- **Done when:** the run is recorded with what was read and the work opened from
  it — the continuous-monitoring heartbeat. Silence is not assurance until it is
  observed.

![Morning check target-state read path.](servicenow-day2/figs/day2kit-target-task-11-morning-check.png){fig-alt="Morning check 2027 target task card: read-only across the cloud estate, reconcile to the evidence store, open work from deltas; emits NIST CA-7 and AU-6, feeds KSI-MLA." width="100%"}

## When a request stops

A stopped request tells you the clause it stopped at:

- **authorize** — requester == approver, or a privileged grant with no expiry. Fix
  the approver or add an expiry.
- **elevate** — PIM activation failed or was denied. Re-activate with a valid
  justification and MFA; if denied, the approval was refused — do not work around
  it.
- **actuate** — the estate call failed. Read the result; do not retry blindly.
- **verify** — the change did not take (the re-read disagrees). The task is **not**
  closed; investigate before telling anyone it is done.

Every stop writes an evidence record too — a refused task is auditable, which is
the point.

## Cross-references

- `../OrgComp_Operator_Runbook_Day2_Compliant.qmd` — the same tasks with the
  as-found gaps they replace.
- `KIT-SCRIPTS.md` — what runs under each catalog item.
- `KIT-USAGE-SAM-INTEGRATION.md` — the SAM-originated (Tier-1/2) request path.
- Vol IX Book 01 (catalog), Book 05 (SaaS), Book 06 (governance).
