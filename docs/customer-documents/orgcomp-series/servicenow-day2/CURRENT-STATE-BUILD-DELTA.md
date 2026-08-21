# Day-2 Automation Kit — CURRENT STATE edition — Build Delta

> What an implementation team builds **in addition to** the base Build
> Specification to run the kit against today's hybrid, AD-mastered estate. This is
> a delta, not a replacement: build the base platform records from
> `KIT-BUILD-SPEC` first, then add the items here. Everything is additive and
> switched by one property, so the same instance can become the 2027 Target
> edition later by setting `hybrid_mode = false`.

**Date Code:** 2026-08-18 08:32 ET · **Scope:** FedRAMP Moderate / GCC Moderate ·
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
| **MID PowerShell (production)** | Replace the skeleton ECC dispatch in `AdHybridClient._dispatch` with your hardened PowerShell activity / Integration Hub AD spoke, targeting `ad_mid_server`. |

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
change, not a rebuild.** When OPM-HRIT — the Federal HR 2.0 Core HCM platform
(Oracle Fusion Cloud HCM; Wave 2 agency transitions complete in FY 2027) —
becomes the joiner/mover/leaver SSOT and
provisioning goes cloud-native into Entra:

1. Cut over provisioning so Entra is the master for the affected populations.
2. Set `x_fed_day2_ops.hybrid_mode = false` for those populations.
3. The router retires the AD leg; every verb actuates cloud-native in Entra —
   which is exactly the base kit's original design.

The `AdHybridClient` remains in place, dormant, until the last AD-mastered
population is migrated. Retire it only when nothing is synced anymore.

## 5. Trust boundary — the `ecc_queue` dispatch is a second door into AD

`AdHybridClient._dispatch` (`script-includes/AdHybridClient.js`) dispatches every
AD write by inserting a `GlideRecord('ecc_queue')` with `topic = 'Command'`,
`name = 'Invoke-Day2AdAction'`, `queue = 'output'`, and
`agent = 'mid.server.' + ad_mid_server`, which the domain-joined AD MID picks up
asynchronously and executes against the pinned writable DC (`ad_dc`) under the
delegated service account (§1). That queue insert **is** the write channel to AD
once the AD leg is configured — `MacdrOrchestrator.run`'s `actuate` clause is one
caller of it, but not the only possible one. **Anyone who can insert a record
into `ecc_queue` with that `topic`/`name`/`agent` combination can drive AD
writes directly**, bypassing the Flow's router, the `elevate` clause (PIM), and
the evidence write entirely — the orchestrator never sees the request.
`ecc_queue` is a global platform table; the scoped-app ACLs this kit ships
govern `x_fed_day2_ops`'s own
tables (e.g. `x_fed_day2_ops_evidence`), not `ecc_queue`. So whether this is
exploitable on a given instance is purely a question of that instance's
`ecc_queue` insert ACL — a platform-configuration fact this kit does not control
and, until now, did not document.

This does not defeat the design: a change that reaches AD through the governed
path is evidenced, and an operator's interactive AD console session was never
evidenced either — so the `ecc_queue` path is not a regression against the
pre-kit baseline in that narrow sense. But it does widen who is "in the trust
path" for AD writes. Under Microsoft's AD tiering model, any principal able to
write a `topic = 'Command'` / `name = 'Invoke-Day2AdAction'` /
`agent = 'mid.server.<x>'` record to `ecc_queue` is effectively Tier-0-adjacent
for this domain, which makes the ServiceNow instance (and the AD MID) a
materially different trust posture than
"the MID is in-boundary" conveys on its own — and arguably a **wider** trust
path than an operator working from a PAW, not narrower, since it substitutes a
table-ACL question on a shared platform table for a hardened, single-purpose
endpoint. That is not a decision this kit should make implicitly; it needs to
be explicit and reviewed.

**Pre-production must-do:** review and restrict the `ecc_queue` insert ACL on
the target instance — who can insert into `ecc_queue` at all, and ideally scope
further to this kit's own `topic = 'Command'` / `name = 'Invoke-Day2AdAction'` /
`agent = 'mid.server.' + ad_mid_server` combination — before go-live. Note that
`topic = 'Command'` is the platform's generic MID command topic and is **not**
unique to this kit: an ACL written against `topic` alone will be both
over-broad and, on its own, insufficient to identify this channel. `name` and
`agent` are the discriminating fields; `source` is set to
`x_fed_day2_ops.AdHybridClient` on the kit's own inserts, but `source` is
caller-supplied and must not be trusted as an authorization signal.

Track this alongside the delegated-rights verification already called out as
open in `CURRENT-STATE-SCRIPTS.md` §1 (the
effective-permissions dump), and carry both into the pilot's entry criteria
(`CURRENT-STATE-PILOT-ROLLOUT.md` §0).
