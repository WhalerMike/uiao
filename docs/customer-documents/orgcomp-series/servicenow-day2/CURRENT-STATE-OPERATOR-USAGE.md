# Day-2 Automation Kit — CURRENT STATE edition — Operator Usage

> Running the governed catalog tasks against today's **hybrid, AD-mastered**
> estate. Each task below carries a diagram of its **current-state write path** —
> which leg actuates it (AD or cloud), how the closure is verified, and the NIST
> control and FedRAMP KSI it emits. The controls and KSIs are the same as the
> target edition; only the write path differs.

**Date Code:** 2026-07-22 12:00 ET · **Scope:** FedRAMP Moderate / GCC Moderate ·
**Audience:** service-desk / CST operators and their approvers

## How to read each task

Every task runs the five MACD-R clauses in order — **Authorize** (SoD, fail
closed), **Elevate** (PIM/PAG, just-in-time), **Actuate + Verify**, **Evidence**.
What this edition adds is a **router** between Elevate and Actuate: for a **synced
object** it sends lifecycle / attribute / password / AD-group writes to the **AD
leg** (`AdHybridClient`, via the domain-joined MID to a writable DC) and keeps
**cloud-native** work on the **Graph/ARM leg**. A task is closed only when its
post-state is re-read and the evidence record is written — a dispatch is not a
closure.

The tasks group into three shapes:

- **Split** (both legs): password reset, joiner, mover, group membership.
- **Cloud-native only** (no AD leg): MFA reset, Azure RBAC, license, guest invite,
  admin consent.
- **Read-only** (writes nothing): the morning check.

---

## Credential tasks

### Password reset — `entra.credential.password_reset` (IA-5)

For a **synced user** the password is mastered in AD: reset it on the writable DC
(`Set-ADAccountPassword -Reset` + force-change), and it flows to Entra via hash
sync / writeback. SSPR is the preferred self-service path; this admin path is the
approver-gated fallback. A **cloud-only** user is reset directly in Entra.

![Password reset current-state write path.](servicenow-day2/figs/day2kit-task-01-password-reset.png){fig-alt="Password reset task card: split actuation — AD leg Set-ADAccountPassword on the writable DC for a synced user, Graph leg for a cloud-only user; emits NIST IA-5, feeds KSI-IAM." width="100%"}

### MFA method reset — `entra.credential.mfa_reset` (IA-5)

MFA methods live in Entra even for a synced user, so this is **cloud-native** —
there is no AD leg. Identity-proof the requester first, delete the method in Entra,
require re-enrollment, and **log + alert** (a takeover-adjacent verb).

![MFA method reset current-state write path.](servicenow-day2/figs/day2kit-task-02-mfa-reset.png){fig-alt="MFA method reset task card: cloud-native only, no AD leg — Graph DELETE of the authentication method, re-enrollment required, log and alert; emits NIST IA-5, feeds KSI-IAM." width="100%"}

---

## Joiner / Mover / Leaver

### New account (joiner) — `entra.jml.joiner` (AC-2)

**Split.** The account is created in AD (`New-ADUser` in the role's OU, owner +
least-privilege baseline) and Entra Connect projects it into Entra. Once the
synced object appears in Entra, the cloud leg assigns license and cloud-only
groups **by role** — derived, never hand-picked.

![Joiner current-state write path.](servicenow-day2/figs/day2kit-task-03-joiner.png){fig-alt="Joiner task card: split actuation — AD leg New-ADUser in the role OU then Entra Connect sync, Graph leg assigns license and cloud groups by role after the object appears; emits NIST AC-2 and IA-4, feeds KSI-IAM." width="100%"}

### Role / scope change (mover) — `entra.jml.mover` (AC-6)

**Split.** Change on-prem attributes, OU, and AD-sourced group membership in AD
(`Set-ADUser`, `Move-ADObject`, add/remove groups); re-derive the cloud license
and cloud-only groups in Entra. **Remove the stale grants** — a mover that only
adds is a finding, because a stale entitlement is standing risk.

![Mover current-state write path.](servicenow-day2/figs/day2kit-task-04-mover.png){fig-alt="Mover task card: split actuation — AD leg sets attributes, moves OU, adds/removes AD groups; Graph leg re-derives cloud access and removes stale grants; emits NIST AC-6 and AC-2, feeds KSI-IAM." width="100%"}

### De-provision (leaver) — `entra.jml.leaver` (AC-2)

**Split.** Disable the account where it is mastered — `Disable-ADAccount` + move to
the disabled OU on the writable DC — and sync flows `accountEnabled = false` to
Entra. Kill the live cloud session directly in Entra (`revokeSignInSessions`) and
reassign cloud-owned objects. Both legs, evidenced, or it is not closed.

![Leaver current-state write path.](servicenow-day2/figs/day2kit-task-05-leaver.png){fig-alt="Leaver task card: split actuation — AD leg Disable-ADAccount and move to disabled OU then sync, Graph leg revokes sessions and reassigns cloud-owned objects; emits NIST AC-2, feeds KSI-IAM." width="100%"}

---

## Access grants

### Group membership — `entra.access.group_assignment` (AC-6)

**Split by group source.** If the group **originates in AD** (synced), manage its
membership in AD (`Add-/Remove-ADGroupMember`) and let it sync; if it is a
**cloud-only / M365** group, manage it in Entra. The router branches on the group's
source, not just the user. A privileged grant is time-bound and access-review-linked.

![Group membership current-state write path.](servicenow-day2/figs/day2kit-task-06-group-membership.png){fig-alt="Group membership task card: split by group source — AD leg for a synced group, Graph leg for a cloud-only group; emits NIST AC-6, feeds KSI-IAM." width="100%"}

### Azure RBAC grant — `azure.rbac.assign` (AC-6)

**Cloud-native only.** An Azure role assignment is an ARM object with no on-prem
representation, so `AzureArmClient.assignRbacRole` actuates directly on the
resource plane — a custom least-privilege role at the tightest scope (resource
group / resource, never subscription-wide by default).

![Azure RBAC current-state write path.](servicenow-day2/figs/day2kit-task-07-azure-rbac.png){fig-alt="Azure RBAC task card: cloud-native only, no AD leg — ARM assigns a custom least-privilege role at a scoped level; emits NIST AC-6, feeds KSI-IAM." width="100%"}

### License assignment — `entra.access.license_assignment` (AC-2)

**Cloud-native.** The SKU is a cloud entitlement, assigned in Entra
(`assignLicense`) or inherited via a licensing group. Group-based licensing is
preferred; the only AD touch is when that delivery group is itself a **synced**
group, in which case its membership is the AD leg.

![License assignment current-state write path.](servicenow-day2/figs/day2kit-task-08-license.png){fig-alt="License assignment task card: cloud-native — Graph assignLicense or group-based licensing; the only AD touch is a synced delivery group's membership; emits NIST AC-2, feeds KSI-IAM." width="100%"}

### Guest / B2B invite — `entra.access.guest_invite` (AC-2)

**Cloud-native only.** A B2B guest is a cloud-only identity with no AD account, so
it is created directly in Entra (`inviteGuest`) with a **sponsor** and an
**expiry**, governed under the non-employee branch. No perpetual guests.

![Guest invite current-state write path.](servicenow-day2/figs/day2kit-task-09-guest.png){fig-alt="Guest invite task card: cloud-native only, no AD leg — Graph invitation with sponsor and expiry; emits NIST AC-2, feeds KSI-IAM." width="100%"}

---

## Integration and monitoring

### SaaS admin consent — `saas.verify.authorization` (SA-9)

**Cloud-native only.** App consent is an Entra tenant operation. Record the
**authorization verdict first** (`Day2NativeActuator.recordAuthorizationVerdict`),
*then* scope the app's admin consent to least-privilege delegated / application
permissions — never blanket Directory admin. The verdict precedes the grant, never
the reverse.

![SaaS admin consent current-state write path.](servicenow-day2/figs/day2kit-task-10-admin-consent.png){fig-alt="SaaS admin consent task card: cloud-native only, no AD leg — record the SA-9 authorization verdict before scoping app consent; emits NIST SA-9 and AC-20, feeds KSI-SCR." width="100%"}

### Morning check / log review — `saas.audit.review` (CA-7 / AU-6)

**Read-only.** The only routine that writes nothing: it queries recent
lifecycle / auth events across **both planes** (AD and Entra), reconciles the
estate to the evidence table and the CMDB, and opens tasks / findings from the
deltas. The check *is* the verification — silence is not assurance until it is
observed.

![Morning check current-state read path.](servicenow-day2/figs/day2kit-task-11-morning-check.png){fig-alt="Morning check task card: read-only across AD and Entra, reconcile to the evidence store, open work from deltas; emits NIST CA-7 and AU-6, feeds KSI-MLA." width="100%"}

---

## When a request stops

The fail-closed behavior is unchanged from the base kit, with one current-state
addition — a **routing** outcome:

- **`authorize`** — SoD failed (requester == approver) or a privileged grant
  carried no expiry.
- **`elevate`** — no PIM activation id; elevation was denied or the PAG is
  misconfigured. The orchestrator then refuses to actuate. That is correct.
- **`actuate`** — the estate write failed. On the **AD leg** this is usually MID→DC
  reachability, a missing delegated right on the target OU, or the pinned DC being
  unreachable; on the **Graph/ARM leg** it is the base-kit set (scope, MID, host).
- **`route`** — the object could not be classified (the Entra read for
  `onPremisesSyncEnabled` failed), so the router could not choose a leg. Fail
  closed: an unclassified object is not actuated. Fix the Entra read, do not guess.
- **`verify`** — the post-state re-read disagreed. On the AD leg, remember sync
  latency: the AD post-state is immediate on the pinned DC, but the **Entra**
  post-state lands on the next sync cycle.

Every stopped request — like every completed one — writes an evidence row with the
full MACD-R `trail`. Open the row to see the clause it stopped at and why.
