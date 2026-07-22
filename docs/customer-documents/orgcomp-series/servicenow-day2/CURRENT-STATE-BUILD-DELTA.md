# Day-2 Automation Kit — CURRENT STATE edition — Build Delta

> What an implementation team builds **in addition to** the base Build
> Specification to run the kit against today's hybrid, AD-mastered estate. This is
> a delta, not a replacement: build the base platform records from
> `KIT-BUILD-SPEC` first, then add the items here. Everything is additive and
> switched by one property, so the same instance can become the 2027 Target
> edition later by setting `hybrid_mode = false`.

**Date Code:** 2026-07-22 12:00 ET · **Scope:** FedRAMP Moderate / GCC Moderate ·
**Audience:** the implementation team — ServiceNow + Active Directory + Entra/Azure

## 1. Infrastructure — the AD leg's transport

1. **A domain-joined, in-boundary MID Server** that can reach a **writable domain
   controller** over the AD management ports. It may be the same MID that reaches
   Graph/ARM if it can reach both; use a separate MID if AD reachability requires
   it. Record its name in `x_fed_day2_ops.ad_mid_server`.
2. **A MID service account** with **delegated, least-privilege AD rights**, scoped
   to the specific OUs the kit manages:
   - create / disable user objects in the managed user OUs,
   - reset password on those objects,
   - move objects to the disabled-accounts OU,
   - modify membership of the **delegated** groups only.

   Grant these through AD **delegation of control** on those OUs — **never Domain
   Admin, never Account Operators.** The account signs into nothing interactively.
3. **A preferred writable DC** recorded in `x_fed_day2_ops.ad_dc`, so every write
   and its verify re-read hit the same DC (no replication-lag false reads).
4. **A disabled-accounts OU** recorded in `x_fed_day2_ops.ad_disabled_ou`.
5. **Entra Connect** healthy, with **password writeback** enabled if you will
   actuate password resets in Entra rather than in AD.

## 2. Platform records to add

| Record | What to build |
|---|---|
| **Script Include** | Import `script-includes/AdHybridClient.js` into scope `x_fed_day2_ops`. |
| **System properties** | `hybrid_mode = true`, `ad_mid_server`, `ad_dc`, `ad_disabled_ou` (§5 of `CURRENT-STATE-SCRIPTS`). |
| **Flow — router step** | Between Elevate and Actuate, add the routing decision: read the target's `onPremisesSyncEnabled` (Graph), and when `hybrid_mode` and the object is AD-mastered, call the `AdHybridClient` method for the verb; otherwise call the existing Graph/ARM actuator. Group membership branches on the group source. |
| **Flow — verify step** | For an AD-leg actuation, verify by re-reading **AD on the pinned DC** for the on-prem post-state, and re-reading **Entra** for the synced post-state (allowing for sync latency). |
| **MID PowerShell (production)** | Replace the skeleton ECC dispatch in `AdHybridClient._ps` with your hardened PowerShell activity / Integration Hub AD spoke, targeting `ad_mid_server`. |

Nothing in the base tables, ACLs, roles, catalog roster, Scripted REST API, or
update-set order changes — this edition only adds the Script Include, the
properties, and the two Flow steps.

## 3. Acceptance — prove the routing and the legs

Build in the sandbox with `test_mode = true`, then assert:

1. **Router classifies.** A synced test object (`onPremisesSyncEnabled = true`)
   routes lifecycle / password / AD-group verbs to `AdHybridClient`; a cloud-only
   test object routes them to `EntraHelpdeskClient`. An object whose Entra read
   fails stops at clause **`route`** (fail closed).
2. **AD leg dispatches and verifies.** In `test_mode`, an AD-leg task returns the
   canned `dispatched` result and the Flow's verify observes the (canned) AD
   post-state — the chain reaches clause **`evidence`**.
3. **Cloud-native verbs never route to AD.** MFA reset, Azure RBAC, license, guest,
   and admin consent go to Graph/ARM regardless of `hybrid_mode`.
4. **The edition switch works.** With `hybrid_mode = false`, the same synced object
   routes every verb to the Graph/ARM leg — this is the 2027 Target behavior, and
   it must run green before you rely on the switch as your migration lever.
5. **Base gates still pass.** `check_actuator_coverage.py`, `check_l3_ceiling.py`,
   and `catalog/contract_check.py` are unaffected by this delta and must stay green.

## 4. The path to 2027

This edition is built so the migration to the target state is a **configuration
change, not a rebuild.** When OPM-HRIT becomes the joiner/mover/leaver SSOT and
provisioning goes cloud-native into Entra:

1. Cut over provisioning so Entra is the master for the affected populations.
2. Set `x_fed_day2_ops.hybrid_mode = false` for those populations.
3. The router retires the AD leg; every verb actuates cloud-native in Entra —
   which is exactly the base kit's original design.

The `AdHybridClient` remains in place, dormant, until the last AD-mastered
population is migrated. Retire it only when nothing is synced anymore.
