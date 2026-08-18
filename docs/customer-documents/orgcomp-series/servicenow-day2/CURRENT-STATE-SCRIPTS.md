# Day-2 Automation Kit — CURRENT STATE edition — Scripts

> What this edition adds to the base script set: **one new Script Include**
> (`AdHybridClient`) and a **routing decision**. Everything else — the gate, the
> orchestrator, the PIM client, the Graph/ARM clients, the SAM correlation — is
> reused unchanged. The two editions are the same scripts with `hybrid_mode`
> deciding the path, not a fork.

**Date Code:** 2026-08-18 08:32 ET · **Scope:** FedRAMP Moderate / GCC Moderate ·
**Audience:** ServiceNow platform admins

## 1. `AdHybridClient` — the AD leg

`AdHybridClient` (`script-includes/AdHybridClient.js`) is the sibling of
`EntraHelpdeskClient`: where the Graph client writes to Entra, this one writes to
**Active Directory** for synced objects, on a **domain-joined, in-boundary MID
Server** pinned to a **writable domain controller**. It follows the house pattern
exactly — `Class.create`, config from `gs.getProperty`, MID-routed transport,
`test_mode` canned values, scoped `gs.error` logging with the
`[x_fed_day2_ops.AdHybridClient]` prefix, and fail-closed returns.

| Method | Cmdlet (skeleton) | Serves |
|---|---|---|
| `createUserAd(payload)` | `New-ADUser` | Joiner — create in the role OU; sync projects into Entra |
| `disableUserAd(id)` | `Disable-ADAccount` + `Move-ADObject` | Leaver — disable + move to the disabled OU |
| `setPasswordAd(id, opts)` | `Set-ADAccountPassword -Reset` + `Set-ADUser -ChangePasswordAtLogon` | Password reset (synced user) |
| `setUserAttributesAd(id, attrs)` | `Set-ADUser` | Mover — on-prem-mastered attributes |
| `moveUserOuAd(id, ou)` | `Move-ADObject` | Mover — OU change |
| `addGroupMemberAd(g, m)` / `removeGroupMemberAd(g, m)` | `Add-/Remove-ADGroupMember` | AD-sourced group membership |
| `isAdMastered(entraUser)` | — | The routing predicate: `onPremisesSyncEnabled === true` |

Every write above returns `{ ok, dispatched, ecc_sys_id }` and asserts nothing
about post-state. Closure comes from the read-back half of the class, added by
the P0-4 remediation:

| Method | Reads | Serves |
|---|---|---|
| `getUserAd(id, properties)` | `Get-ADUser` on the pinned DC | VERIFY — the on-prem post-state after a lifecycle / attribute / password write |
| `getGroupMembersAd(g, recursive)` | `Get-ADGroupMember` on the pinned DC | VERIFY — membership after a group write |
| `isGroupMemberAd(g, m, recursive)` | — | Direct membership assertion. **Tri-state:** `true` / `false` / `null`, where `null` is INCONCLUSIVE — never conflate it with `false` at the call site |
| `resolveDispatch(eccSysId)` | the ECC response record | Parses one dispatch's result. Fails closed: missing, errored, or unparseable is `ok:false`, never an assumed success |
| `awaitDispatch(eccSysId, maxMs)` | — | Bounded poll (`x_fed_day2_ops.ad_await_ms`, capped at 60s) for ATF and synchronous scripts. A timeout is *inconclusive*, not *verified*. The production path is the Flow's own asynchronous VERIFY step, not this |

**Transport (remediated, commit `7d2423c74`).** `_dispatch(action, identity,
callerArgs)` validates `callerArgs` against a per-action allowlist
(`AdHybridClient.ACTIONS`), refuses any reserved parameter outright
(`AdHybridClient.RESERVED`), and emits a **structured JSON payload** — never a
rendered command string — as an `ecc_queue` output record (topic `Command`,
name `Invoke-Day2AdAction`) that `mid/Invoke-Day2AdAction.ps1` binds via
splatting. The ECC output is still asynchronous, so a successful return means
**dispatched**, not **verified**; closure depends on the Flow's VERIFY clause
re-reading AD state on the same DC. **That re-read now exists:**
`getUserAd` / `getGroupMembersAd` / `isGroupMemberAd` read against the pinned DC,
`resolveDispatch` parses the ECC response record fail-closed, and
`EntraHelpdeskGate._verifyAd` calls into them — a write's evidence record is no
longer an assertion, it is an observation. The three defects an external
security review found (2026-07-29) — unescaped parameter names reaching a
rendered PowerShell command, a caller-suppliable attribute bag able to override
`Identity`, and a cleartext password crossing `ecc_queue.payload` — are fixed by
this same commit: there is no command string to inject into, reserved
parameters are refused before dispatch, and `setPasswordAd` no longer accepts or
transports password material at all. None of this has been exercised against a
live domain controller yet — a mock ServiceNow harness executed the real script
against fixture data (`0d452b75f`), which is a different thing than a real MID
dispatching to a real DC. Migrating to the Integration Hub AD spoke for
production (§7) is still the recommended hardening path regardless; keep the
fail-closed contract (any error → `ok:false`).

**Boundary discipline.** The MID runs inside the ATO boundary; its service account
is *intended* to hold **delegated, least-privilege AD rights** on the specific OUs
it manages — never Domain Admin — though that delegation is currently asserted in
comments, not verified by anything in the kit (an effective-permissions dump is a
pre-production must-do, not optional). The write and the verify re-read both hit
the same DC (`x_fed_day2_ops.ad_dc`), so a post-state read cannot return a stale
answer from a replica that has not caught up yet.

## 2. The router — choosing the leg

Routing sits between MACD-R clause 3 (Elevate) and clause 4 (Actuate). The Flow
resolves, for the target object:

```
if (hybrid_mode == true && AdHybridClient.isAdMastered(entraUser)) {
    // lifecycle / attribute / password / AD-sourced-group writes -> AD leg
    request.actuation_leg = 'ad';
} else {
    // cloud-only object, OR hybrid_mode == false -> Graph / ARM leg
    request.actuation_leg = 'graph';
}
```

The Flow must set `request.actuation_leg` before calling `MacdrOrchestrator.run()` —
`'ad'` when routing to the AD leg, `'graph'` (or omitted, for backward
compatibility) for the cloud-only leg. `MacdrOrchestrator` reads this field to
know whether to skip the PIM elevate/deactivate clause: AD-leg writes execute
under the MID Server's service identity, not the elevated approver's token, so
activating PIM for a human is not the operative authorization for that leg and
is skipped by design, with the reason recorded in the evidence trail (see
`script-includes/MacdrOrchestrator.js`, clause 3).

Two refinements the Flow applies:

1. **Group membership branches on the *group* source, not the user.** A synced
   user can still be added to a cloud-only group in Entra; the router checks
   whether the *group* originates on-prem before choosing the AD leg.
2. **Cloud-native verbs never route to AD.** MFA reset, Azure RBAC, license, guest
   invite, and admin consent are cloud-only by nature; the router sends them to
   Graph/ARM regardless of `hybrid_mode`.

If the classifying Entra read fails, the router **fails closed** with clause
`route` — an unclassified object is not actuated.

## 3. `hybrid_mode` — the edition switch

`x_fed_day2_ops.hybrid_mode` is the single property that distinguishes the two
editions:

- **`true` (Current State):** synced-object lifecycle / attribute / password /
  AD-group writes go to the AD leg, then sync to Entra.
- **`false` (2027 Target State):** the AD leg is dormant; everything actuates
  cloud-native in Entra, matching the base kit's original assumption.

Flipping to `false` while identities are still AD-mastered is a **correctness
bug**: Entra Connect silently reverts cloud writes to synced attributes on the next
cycle. Flip it only when OPM-HRIT provisioning — the Federal HR 2.0 Core HCM
feed (Oracle Fusion Cloud HCM) — has made Entra the master.

## 4. What is unchanged from the base kit

`EntraHelpdeskGate` (Authorize + Verify), `MacdrOrchestrator` (the five-clause
chain — it is actuation-agnostic, so it takes whichever leg's closure the router
selected), `PimActivationClient`, `EntraHelpdeskClient`, `AzureArmClient`,
`Day2NativeActuator`, `EntraSaasClient`, `EntraAppRegClient`, `AcmeCredentialClient`,
`SamCorrelationClient`, and `scripted-rest/sam_inbound_ritm.js` are all reused
verbatim. The MACD-R guarantees, the closure-provenance rules, the fail-closed
behavior, and the evidence contract are identical across both editions — only the
write *path* for synced objects changes.

## 5. Config properties added by this edition

| Property | Purpose |
|---|---|
| `x_fed_day2_ops.hybrid_mode` | `true` = Current State (AD leg live); `false` = 2027 Target |
| `x_fed_day2_ops.ad_mid_server` | The domain-joined, in-boundary MID that reaches a writable DC |
| `x_fed_day2_ops.ad_dc` | The preferred writable DC (write + verify hit the same one) |
| `x_fed_day2_ops.ad_disabled_ou` | The OU leavers are moved to on disable |
| `x_fed_day2_ops.ad_managed_ous` | Comma-separated allowlist of target OU distinguished names `moveUserOuAd` may move an object into; empty/unset fails closed (no moves permitted) |
| `x_fed_day2_ops.ad_protected_groups` | Comma-separated deny-list of tier-0/protected AD group names (substring match) `addGroupMemberAd` refuses to modify; defaults to the built-in AD privileged-group set |

See `CURRENT-STATE-BUILD-DELTA.md` for how these are provisioned and the delegated
AD rights the MID service account needs.

## 6. The control-map AD actuators and the hybrid tests

The AD leg is bound to the control maps and proven by ATF, the same way the
cloud-native path is:

- **`actuator_ad` in the control map.** Every helpdesk item whose synced-object
  write lands in AD carries an `actuator_ad` naming the `AdHybridClient` method
  alongside the base (cloud) `actuator` — `entra.jml.joiner` →
  `AdHybridClient.createUserAd`, `entra.jml.mover` →
  `setUserAttributesAd`, `entra.jml.leaver` → `disableUserAd`,
  `entra.credential.password_reset` → `setPasswordAd`, and
  `entra.access.group_assignment` → `addGroupMemberAd`. Items with no
  `actuator_ad` are cloud-native in both editions.
- **`check_actuator_coverage.py` validates it.** The gate now resolves every
  `actuator_ad` to a real public method on `AdHybridClient` — a current-state AD
  write path with nothing behind it fails the build, exactly as a missing cloud
  actuator does.
- **Four hybrid ATF suites** (see `atf/README.md`) prove the routing with
  `test_mode = true` — synced → AD leg, cloud-only → Graph leg, an unclassifiable
  object failing closed to clause `route`, and the AD-leg dispatch never
  asserting an observation field (rewritten in `0d452b75f` to match the P0-4
  remediation, which removed `synced`/`accountEnabled` from write returns).
  **These suites prove routing, not the AD leg's transport under real AD:**
  `test_mode` still short-circuits every `AdHybridClient` method before
  `_dispatch` reaches `ecc_queue`, so the allowlist validation, reserved-parameter
  refusal, and read-back logic described in §1 have been exercised against a mock
  ServiceNow harness executing the real script (`0d452b75f`), but not yet against
  a live domain controller.

## 7. Production: migrating the AD leg to the Integration Hub AD Spoke

`AdHybridClient._dispatch` is a **starter skeleton** — it emits a structured JSON
job to the AD MID through the ECC queue (`topic = 'Command'`,
`name = 'Invoke-Day2AdAction'`), which `mid/Invoke-Day2AdAction.ps1` binds via
splatting (§1). For production, replace that transport with the **Integration Hub
Active Directory (v2) spoke**, which ServiceNow builds and maintains. The
client's method surface does not change; only `_dispatch` is swapped for
spoke-action calls, so the router, the control maps, and the ATF suites all
stand.

| `AdHybridClient` method | Skeleton cmdlet | Integration Hub AD spoke action |
|---|---|---|
| `createUserAd` | `New-ADUser` | **Create Object** (objectClass user, in the role OU) |
| `disableUserAd` | `Disable-ADAccount` + `Move-ADObject` | **Update Object** (disable) + **Move Object** (to the disabled OU) |
| `setPasswordAd` | `Set-ADAccountPassword -Reset` + `Set-ADUser -ChangePasswordAtLogon` | **Reset Password** (+ set `pwdLastSet = 0`) |
| `setUserAttributesAd` | `Set-ADUser` | **Update Object** |
| `moveUserOuAd` | `Move-ADObject` | **Move Object** |
| `addGroupMemberAd` | `Add-ADGroupMember` | **Add to Group** |
| `removeGroupMemberAd` | `Remove-ADGroupMember` | **Remove from Group** |
| `getUserAd` | `Get-ADUser` | **Look Up Object** / **Query Objects** |
| `getGroupMembersAd` | `Get-ADGroupMember` | the spoke's group-membership read |

**Migrate the read-backs too, not just the writes.** The four write rows are the
visible half; closure depends on the read half (§1). A migration that swaps the
writes to spoke actions and leaves the reads on the ECC path — or drops them —
turns every evidence record back into an assertion. Two things to confirm
against **your** spoke version before you commit to the migration:

1.  **The action names above are the mapping to check, not a guarantee.** Read
    action naming has varied across AD spoke versions; verify against the
    version installed on your instance.
2.  **The spoke must let you pin the domain controller.** The same-DC guarantee
    (`x_fed_day2_ops.ad_dc`) is what keeps a post-state read off a replica that
    has not caught up. If the spoke's connection targets a domain rather than a
    named DC, you have traded an injection-surface problem for a
    replication-lag one, and VERIFY can report a false negative on a write that
    actually succeeded. Resolve this before migrating, not after.

`resolveDispatch` and `awaitDispatch` are ECC-queue mechanics and have no spoke
equivalent — they disappear with the queue, and the spoke action's own return
value takes their place as the observation VERIFY reads.

**Why the spoke for production**

- **No JSON-over-ECC-queue plus PowerShell-splatting transport to reason about.**
  The current skeleton already emits a structured payload rather than a rendered
  command string (§1), but the spoke removes the ECC queue and the MID script
  entirely — you configure fields in Flow Designer, not a payload contract
  between two separately-maintained artifacts.
- **Removes the `ecc_queue`-is-a-global-table exposure.** However tightly
  `AdHybridClient` validates its own payload, the write channel to AD is still a
  platform-shared table gated only by that instance's `ecc_queue` insert ACL
  (`CURRENT-STATE-BUILD-DELTA.md` §5) — a fact that does not go away until the
  spoke replaces the queue as the transport.
- **Supported and versioned.** The spoke actions are maintained by ServiceNow and
  travel with platform upgrades; the skeleton is yours to keep working.
- **Same boundary discipline.** The spoke still runs over the **domain-joined,
  in-boundary MID** against the pinned writable DC (`ad_dc`), under the same
  delegated, least-privilege service account — never Domain Admin.
- **Structured outputs for verify.** Spoke actions return typed results, so the
  Flow's VERIFY re-read and the evidence record can capture the AD post-state
  without parsing stdout — the skeleton's read-back (`getUserAd` /
  `isGroupMemberAd` / `resolveDispatch`, §1) already does this over the ECC
  queue; the spoke path would carry the same contract forward without the queue
  round-trip.

**What stays the same**

The `hybrid_mode` switch, the router predicate (`isAdMastered`), the MACD-R
ordering, the fail-closed contract, and every `actuator_ad` binding are unchanged
— the spoke is a transport swap inside the AD leg, not a redesign. Keep
`test_mode` returning canned values so the ATF suites still run with no live AD.

**Trade-off to weigh.** The spoke needs an **IntegrationHub entitlement** (and the
AD spoke's spoke-specific licensing); the ECC/PowerShell skeleton does not. If
IntegrationHub is unavailable, harden the skeleton instead — parameterize the
command (no string interpolation of untrusted input), pin the module version, and
add explicit error/timeout handling — but treat that as the fallback, not the goal.
