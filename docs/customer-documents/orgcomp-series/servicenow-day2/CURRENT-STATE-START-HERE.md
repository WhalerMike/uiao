# Day-2 Automation Kit — CURRENT STATE edition — START HERE

> The on-ramp for running this kit against the estate **as it is today**: a
> **hybrid, AD-mastered** identity plane where Active Directory is the source and
> **Entra Connect syncs AD → Entra**. This edition corrects one assumption the
> base kit makes — that identities originate cloud-native from OPM-HRIT (now
> concretely the Federal HR 2.0 Core HCM platform: Oracle Fusion Cloud HCM,
> awarded June 2026) — and
> routes each task to the write path that is actually authoritative today.
>
> **The base kit is the [2027 Target State edition](#the-two-editions).** Keep it
> as the goal; run *this* edition now.

**Date Code:** 2026-07-23 06:46 ET · **Scope:** FedRAMP Moderate / GCC Moderate ·
**Audience:** the implementer and operators running day-2 tasks on today's hybrid estate

## 0. What changed, in one paragraph

Today your Entra ID users are **synced from Active Directory** (Entra Connect);
AD is the identity master and Entra is its synchronized projection. So for a
**synced object** (`onPremisesSyncEnabled = true`) the authoritative write for the
account lifecycle and its on-prem-mastered attributes must land in **AD** and flow
to Entra on the next sync cycle — writing them directly in Entra Graph is wrong
(sync overwrites cloud edits to synced attributes, and an admin cloud password
reset is unsupported for a synced user without writeback). **Cloud-native**
objects — MFA methods, Azure RBAC, guests, app consent, cloud-only groups — never
had an on-prem master and stay on the Graph/ARM path. This edition adds the **AD
leg** and a **router** that sends each task to the correct path.

![Current-state hybrid path: AD is the master and Entra Connect syncs AD to Entra, so synced-object writes land in AD and flow to Entra while cloud-native objects stay on Graph/ARM.](servicenow-day2/figs/day2kit-current-fig-01-hybrid-path.png){fig-alt="Four-column current-state house-style diagram on white. Origin: Active Directory as today's identity master plus ServiceNow catalog and SAM; a note that OPM-HRIT is the 2027 target. Orchestrate: the five MACD-R clauses plus a router keyed on onPremisesSyncEnabled. Actuate splits into an AD leg (domain-joined MID to a writable DC, New-ADUser/Disable-ADAccount/Set-ADAccountPassword/Add-ADGroupMember, then Entra Connect sync) and a Graph/ARM leg (MFA, Azure RBAC, license, guest, consent). Emit: evidence to the same NIST controls and FedRAMP KSIs." width="100%"}

## 1. The one rule is unchanged: sandbox first

**Your first install target is a non-production environment, with
`x_fed_day2_ops.test_mode = true` throughout** — plus, for this edition, a
**test Active Directory domain** and a **domain-joined test MID Server**. In
`test_mode` the AD leg (`AdHybridClient`) returns deterministic canned values and
dispatches nothing to a domain controller, so you can build and prove the whole
routed flow before a single real AD write. Only after the ATF suite is green do
you set `test_mode = false`. Do not skip this.

## 2. The two editions

| | **Current State** (this edition) | **2027 Target State** (base kit) |
|---|---|---|
| Identity master | **Active Directory**; Entra Connect syncs AD → Entra | **OPM-HRIT** (Federal HR 2.0 Core HCM — Oracle Fusion Cloud HCM) as SSOT; cloud-native provisioning into Entra |
| `x_fed_day2_ops.hybrid_mode` | **`true`** | `false` |
| Synced-object lifecycle / attributes / password / AD-group | **AD leg** (`AdHybridClient`, domain-joined MID → writable DC), then sync | Graph, cloud-native |
| MFA · Azure RBAC · license · guest · app consent · cloud groups | Graph / ARM (unchanged) | Graph / ARM (unchanged) |
| Read this edition's docs | `CURRENT-STATE-*` | the base `KIT-*` and `README` |

**One script set, config-switched.** The two editions are the *same* Script
Includes with `hybrid_mode` deciding the routing — not a fork. Setting
`hybrid_mode = false` retires the AD leg and sends everything cloud-native, which
is the 2027 target. Nothing else in the app has to change to get there.

## 3. The install path (do these in order)

Build in the sandbox with `test_mode = true`. Steps 1–4 below reuse the base kit
documents unchanged; the **Current-State docs** cover only the delta.

| # | Step | Read |
|---|---|---|
| 1 | Understand the shape: scoped app, the five MACD-R clauses, the closure-provenance rules | base `README.md` |
| 2 | Learn the base config contract — every property, alias, credential, scope | base **`KIT-VARIABLES-REFERENCE`** |
| 3 | Build the base platform records — tables, roles, ACLs, Scripted REST, catalog, Flow | base **`KIT-BUILD-SPEC`** |
| 4 | **Build the current-state delta** — the AD MID, the `AdHybridClient`, the router, the `hybrid_mode` / AD properties, the delegated AD rights | **`CURRENT-STATE-BUILD-DELTA`** |
| 5 | Know the current-state scripts — the AD leg and how routing works | **`CURRENT-STATE-SCRIPTS`** |
| 6 | Operate it: the day-to-day catalog tasks, each with its current-state write path | **`CURRENT-STATE-OPERATOR-USAGE`** |
| 7 | Operate the SAM (IdentityIQ-push) integration (unchanged) | base `KIT-USAGE-SAM-INTEGRATION` |
| 8 | **Go live on a pilot** — the sequenced enablement, the evidence review, and the update-set export/promotion | **`CURRENT-STATE-PILOT-ROLLOUT`** |

## 4. Current-state prerequisites (added to the base list)

- A **domain-joined, in-boundary MID Server** that can reach a **writable domain
  controller** — this is the AD leg's transport (may be the same MID as Graph if
  it can reach both; a separate MID if AD reachability requires it).
- A MID service account holding **delegated, least-privilege AD rights** on the
  specific OUs it manages — create/disable users, reset password, and manage the
  membership of the delegated groups, on those OUs only. **Never Domain Admin.**
- A **preferred writable DC** (`x_fed_day2_ops.ad_dc`) so the write and the
  verify re-read hit the same DC (no replication-lag false reads), and a
  **disabled-accounts OU** (`x_fed_day2_ops.ad_disabled_ou`) for leavers.
- **Entra Connect** configured and healthy, with **password writeback** enabled if
  you intend to actuate password resets in Entra rather than AD.

## 5. Disclaimers specific to this edition

All base kit disclaimers (starter skeletons, `test_mode` sandbox-only, no secrets
in scripts, least privilege, the L3 actuation ceiling, no legal/authorization
advice, no warranty) apply unchanged. Additionally:

1. **The AD leg is a starter skeleton, too.** `AdHybridClient` models its transport
   as a MID PowerShell dispatch (the ActiveDirectory module) via the ECC queue.
   Pin it to **your** hardened PowerShell activity or Integration Hub AD spoke, and
   validate the delegated rights against your OU model, before production.
2. **Sync latency is real, and AD-leg verification does not exist yet.** An AD
   write is authoritative but not instantaneous in Entra — it lands on the next
   Entra Connect cycle. As designed, the Flow's VERIFY clause should re-read
   **AD** (on the pinned DC) for the on-prem post-state and **Entra** for the
   cloud post-state before treating a dispatch as closure. **As shipped, that AD
   re-read does not exist:** `AdHybridClient` has no read method, and
   `EntraHelpdeskGate.verify` only reads Graph. Every AD-leg method currently
   returns its post-state (e.g. `disableUserAd`'s `accountEnabled: false`) as an
   asserted fact the moment the asynchronous dispatch is queued — never having
   observed AD. Do not treat an AD-leg evidence record as verified closure until a
   real AD read-back is added (see `CURRENT-STATE-SCRIPTS.md` §1).
3. **The routing predicate is authoritative, not cosmetic.** `hybrid_mode = true`
   plus `onPremisesSyncEnabled = true` sends a task to the AD leg. If you flip
   `hybrid_mode` to `false` while identities are still AD-mastered, cloud writes to
   synced attributes **will be silently reverted by sync** — a correctness bug, not
   a style choice.
4. **Three more starter-skeleton defects, confirmed by an external security
   review (2026-07-29) — do not point this at a live directory yet.** `_render`
   (the PowerShell command builder) escapes parameter *values* but not parameter
   *names*; a hostile attribute key reaching `setUserAttributesAd` drives
   arbitrary cmdlet execution on the MID. `_merge` gives precedence to the
   caller-supplied attribute bag, so a bag containing `Identity` overrides the
   approved target — the write can land on a different object than the one
   approved. `setPasswordAd` writes the temporary password into
   `ecc_queue.payload` in cleartext. None of the three is exercised by the ATF
   suite, because `test_mode` short-circuits every method before it reaches the
   vulnerable code. Fix all three — plus the verify gap in item 2 above — before
   setting `test_mode = false` against a real domain; see
   `CURRENT-STATE-SCRIPTS.md` §7 for the production-hardening path.

## 6. Where to go next

- The per-task write paths (with a diagram for each task) → `CURRENT-STATE-OPERATOR-USAGE.md`.
- The AD leg and router internals → `CURRENT-STATE-SCRIPTS.md`.
- What the implementation team builds differently → `CURRENT-STATE-BUILD-DELTA.md`.
- The 2027 goal and the doctrine behind it → the base kit + Vol I Book 04 (HRIT SSOT), Vol 0 Book 00 (MACD-R).
