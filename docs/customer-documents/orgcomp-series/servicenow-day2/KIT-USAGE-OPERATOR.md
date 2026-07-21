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

### MFA method reset — `entra.credential.mfa_reset` (IA-5, the takeover verb)

- **Catalog item:** MFA method reset.
- **Fields:** target user, **re-proofing evidence** (required), risk tier.
- **Approval:** service-desk **+ verify** — identity-proof to policy before you
  submit; privileged/sensitive accounts require a second approver.
- **Note:** every MFA reset raises a security alert; repeated resets on one
  identity are a detection signal, not routine.
- **Done when:** the old method is removed and a new enrollment is pending under
  the user's control, with the re-proofing captured.

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

### De-provision / leaver — `entra.jml.leaver` (AC-2)

- **Catalog item:** De-provision (Leaver). Originates from the HR leaver event.
- **What it does:** disable, **revoke sessions and tokens**, deprovision federated
  apps, reassign owned objects — including the leaver's **anchored non-human
  estate** (owned service accounts / app registrations transfer).
- **Done when:** the account is unusable everywhere, zero live sessions, and no
  orphaned objects or ownerless non-human identities remain.

### Role / scope change (mover) — `entra.jml.mover` (AC-6)

- **Catalog item:** Role/scope change. Originates from the HR mover event.
- **What it does:** re-derive group/license/app access to the new role **and remove
  stale entitlements from the old one**.
- **Done when:** the derivation matches the record and stale access is gone.

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

### License assignment — `entra.access.license_assignment` (AC-2)

- **Catalog item:** License assignment. Group-based licensing preferred.
- **Approval:** manager (or a SAM-originated RITM with departmental-owner approval
  for governed licenses).

### Conditional-Access exception — `entra.access.ca_exception` (AC-3)

- **Catalog item:** Conditional-Access exception — **reuses the mandatory
  break-glass-exclusion + expiry + review pattern**; you do not craft a bespoke
  exclusion.
- **Approval:** security approver.

### Guest / B2B invite — `entra.access.guest_invite` (AC-2)

- **Catalog item:** Guest / B2B invite.
- **Approval:** sponsor + security; the invite carries a sponsor and an expiry.

### Admin consent (third-party app) — Lane F (AC-20, SA-9)

- **Do not** approve consent by judgment. Submit the Lane F integration request;
  the **authorization verdict is recorded before consent is configured**, consent
  is scoped to the minimum the app needs, and the app's endpoints are declared.
  See `KIT-USAGE-SAM-INTEGRATION.md` and Vol IX Book 05 for the governed path.

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
