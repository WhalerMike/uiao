---
title: "Day-2 Kit — Live Validation Program RunBook"
subtitle: "ServiceNow PDI · Active Directory Lab · Microsoft 365 Tenant"
date: "2026-07-30 · Repo commit 84bdb28ca"
---

# Executive summary

Five rounds of code-reading and mock-harness execution converged on the same
conclusion: every remaining open item in the Day-2 Automation Kit — the
`ecc_queue` insert ACL, the AD delegation itself, the SER-4 per-tenant Graph
scope wiring, the two `verify()` test-mode design questions, whether the
Terraform secrets-in-state exposure is reachable — is not a "read the code
harder" problem. Each requires either real infrastructure or a decision only
a human can make. No further round of AI-reviews-AI would find or fix any of
them.

This RunBook is the next step: three self-contained validation tracks, each
closing a gap the mock-harness/adversarial-review cycle could not, in the
order they should be run.

| Track | Closes | Needs |
|---|---|---|
| 1. ServiceNow PDI | Real platform ACL behavior, real ATF Test Runner execution, the `ecc_queue` insert-ACL review | A free, self-service PDI signup (~30 min) |
| 2. Active Directory Lab | Real AD write behavior, real delegated-rights enforcement, real filter/attribute-injection resistance | A local Hyper-V VM — no cloud account |
| 3. Microsoft 365 Tenant | SER-4: whether the compliance gate's Graph scope check actually reads a real tenant correctly | A free M365 Developer Program signup |

**What changed in the repo to make these runnable**, all committed at
`84bdb28ca` on `main`:

- Corrected doc/code drift: `CURRENT-STATE-START-HERE.md` and
  `CURRENT-STATE-SCRIPTS.md` still warned "do not point this at a live
  directory yet" for three defects that commit `7d2423c74` had already fixed —
  the warning was one commit stale. The ATF `README.md` documented 12 of the
  17 specs that exist on disk; now documents all 17.
- Implemented the SER-4 Graph scope read in `ComplianceGate._checkWriteScope`
  (`x_fed_compliance`), which was previously a bare `TODO` unconditionally
  returning `'unverified'` — now reads `appRoleAssignments` /
  `oauth2PermissionGrants`, fails closed throughout, and ships with two new
  ATF specs proving the read-only/write-shaped verdicts against fixture data.
- Authored `lab/New-Day2AdLab.ps1` (shipped as a separate attachment alongside
  this RunBook, since it's an executable script, not prose) — a local
  Hyper-V lab-domain provisioner with no cloud-account dependency.

Each track below states, up front, what it proves and — just as
importantly — what it still does not prove. None of this is a substitute for
a real ATO. It substitutes for "an AI read the code and believes it's
correct."

```{=openxml}
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
```

# Day-2 Automation Kit — Live Validation: ServiceNow PDI

**Date Code:** 2026-07-30 11:16 ET · **Scope:** FedRAMP Moderate / GCC Moderate ·
**Audience:** the implementer, running the kit against a real instance for the
first time

## 0. Why this exists, and what it does not prove

Every fix in this kit so far — the P0-1..P0-7 and NEW-1..NEW-6 remediation
(`7d2423c74`), the ATF-drift correction (`0d452b75f`) — was verified by reading
code and by executing it against a **mock** ServiceNow harness (`gs`,
`GlideRecord`, `GlideDateTime`, `GlideDigest` stand-ins). That converges fast and
catches real defects, but it cannot catch anything that only exists in the real
platform: actual ACL enforcement, actual `sys_atf_test` execution semantics,
actual Scripted REST behavior, actual property/alias resolution. A **ServiceNow
Personal Developer Instance (PDI)** is a real instance — free, self-service,
~30 minutes to provision — and closes that specific gap.

**What a PDI validates:** every claim in this kit that is about the *platform*
— does the ACL actually block what it's supposed to, does the ATF suite
actually pass when run through the real Test Runner, does the Scripted REST
endpoint actually enforce its role.

**What a PDI does not validate:** anything downstream of the MID Server — a PDI
has no domain-joined MID and no reachable domain controller, so the AD leg's
`_dispatch` calls will queue an `ecc_queue` record that nothing ever picks up.
That's the [AD lab track](CURRENT-STATE-AD-LAB-VALIDATION.md) and the
`mid/Invoke-Day2AdAction.ps1` script directly. A PDI is also **not a FedRAMP-authorized boundary** — it's a personal
sandbox. Nothing here substitutes for a real ATO; it substitutes for "an AI
read the code and believes it's correct."

## 1. Request the PDI

1. Go to `developer.servicenow.com` and request an instance (free, no purchase,
   ~30 minutes to provision — you'll get an email when it's ready).
2. Pick the current standard release family (whatever `developer.servicenow.com`
   offers by default — this kit has no version-specific dependency called out
   in `KIT-VARIABLES-REFERENCE.md`).
3. PDIs auto-hibernate after a period of inactivity and are reclaimed after
   ~30 days idle. If you're spacing this work out, note the instance URL and
   admin credentials somewhere durable — a support case can wake a hibernated
   instance, but don't rely on that mid-task.

## 2. Build the scoped app for real

There is no shipped Update Set XML for `x_fed_day2_ops` — by design (see
`update-set/README.md`): "committing an unbuilt, untested update set would be
worse than none." You build it once, in the PDI, following the existing spec
docs, then export the XML for your own future re-imports:

| Step | Do | Reference |
|---|---|---|
| 1 | Scoped app + roles | `KIT-BUILD-SPEC.md` §1 |
| 2 | Tables (`x_fed_day2_ops_evidence`, `x_fed_day2_ops_integration`) | `KIT-BUILD-SPEC.md` §2 |
| 3 | Properties + Connection & Credential aliases | `KIT-VARIABLES-REFERENCE.md` |
| 4 | Import the Script Includes from `script-includes/*.js` verbatim | `KIT-BUILD-SPEC.md` §3 |
| 5 | Scripted REST API + ACLs | `KIT-BUILD-SPEC.md` §4, §5 |
| 6 | Catalog items + variable sets | `KIT-BUILD-SPEC.md` §6 |
| 7 | The "Governed Day-2 Request" Flow | `KIT-BUILD-SPEC.md` §7 |
| 8 | **The Current State delta** — `AdHybridClient`, the router, `hybrid_mode`/AD properties | `CURRENT-STATE-BUILD-DELTA.md` |

Set `x_fed_day2_ops.test_mode = true` and `x_fed_day2_ops.hybrid_mode = true`
from the start. Leave `x_fed_day2_ops.ad_mid_server` unset for this round — the
AD leg's `_dispatch` will refuse to actuate without it
(`'ad_mid_server not configured — refusing to actuate'`), which is correct;
you're not testing the AD transport here.

## 3. The step the build spec doesn't cover: the `ecc_queue` insert ACL

`KIT-BUILD-SPEC.md` §5 enumerates ACLs for the app's own tables
(`x_fed_day2_ops_evidence`, `x_fed_day2_ops_integration`) — it does not, and
structurally cannot, cover `ecc_queue`, because that's a global platform table
outside the scoped app's ownership. `CURRENT-STATE-BUILD-DELTA.md` §5 documents
why this matters: anyone who can insert a `topic = 'Command'` /
`agent = 'mid.server.<x>'` record into `ecc_queue` can drive AD writes directly,
bypassing the Flow, the PIM elevate clause, and the evidence write entirely.

This is the one item on the "not fixed" list from `7d2423c74` that a PDI *can*
actually resolve — it's a platform-configuration fact, not a code fix:

1. **System Security > Access Control (ACL)** — search for existing ACLs on
   `ecc_queue`, operation `create`. On a stock PDI there is likely no
   restrictive ACL here at all (the out-of-box posture tends to be
   permissive for admin-adjacent roles).
2. Add or tighten an ACL: operation `create`, table `ecc_queue`, condition
   scoped as tightly as the platform allows — ideally to a role held only by
   the identity that runs `AdHybridClient._dispatch` (the scoped app's
   execution context) and by platform/MID-management roles, never by
   `x_fed_day2_ops.operator` or `x_fed_day2_ops.approver`.
3. Write down what you find and what you changed — this is exactly the
   review BUILD-DELTA §5 calls "not a decision this kit should make
   implicitly." Whatever your target instance's actual posture turns out to
   be is the real finding; a PDI is a legitimate stand-in for exercising the
   *procedure*, but the production instance's ACL still needs its own review
   before go-live.

## 4. Run all 17 ATF specs for real

The mock-harness pass (`0d452b75f`) found and fixed 3 genuine test/code
mismatches by executing the real script against fixture data — but it is still
not the ATF Test Runner, and it does not exercise real `GlideRecord` query
semantics, real ACL enforcement during a test run, or real Flow execution.

1. Import the 17 `atf/*.xml` files as `sys_atf_test` records (Update Set import,
   or create each `sys_atf_test` + its steps by hand from the XML — whichever
   your PDI's import tooling handles cleanly for scoped-app records).
2. Build one Test Suite containing all 17.
3. Run the suite with `x_fed_day2_ops.test_mode = true`.
4. Expected result, per `atf/README.md`: **14 of 17 pass.**
   - `atf-negative-unreconciled-target.xml` is catalog/UI-only — confirm it
     actually runs to completion in the real Test Runner (this is exactly the
     kind of test the mock harness explicitly could not execute).
   - `atf-negative-verify-read-failure.xml` and
     `atf-negative-verify-wrong-state.xml` are expected to still fail (or not
     assert what they intend) — see §5 below.
5. If any of the other 14 fail against the real platform, that's a genuine new
   finding this round exists to catch — ACL interference, property resolution
   order, or Flow-Designer behavior that a mock `gs` object can't reproduce.

## 5. The design decision this kit needs from you: `verify()`'s test-mode failure contract

`atf-negative-verify-read-failure.xml` and `atf-negative-verify-wrong-state.xml`
inject fixture fields (`_forceReadFailure`, `observed`/`intended`) that no
version of `verify()` has ever read — confirmed by git blame to predate the
whole remediation effort. `verify()` checks `test_mode` first and returns a
synthetic pass before reaching any state-inspection logic, for any leg. That's
not a bug in the remediation; it's the original design, and fixing it requires
picking one of these:

**Option A — a named test-only failure hook.**
Add `Day2Env.testFixture('verify_force_read_failure', false)` and
`Day2Env.testFixture('verify_force_wrong_state', false)`, read by `verify()`
*after* the `test_mode` check, so `test_mode` can now simulate either a clean
pass or an injected failure, explicitly and by name. Smallest change; keeps the
short-circuit structure; the two ATF specs get rewritten to set these
properties instead of the unread legacy fields.

**Option B — test_mode fakes the read, not the result.**
Restructure `verify()` so `test_mode` swaps in a fixture-backed reader (a fake
`getUserAd`/Graph response) rather than skipping straight to a synthetic
verdict — the real branch logic (compare observed vs. intended, decide
ok/inconclusive) runs every time, against fake data under test, real data in
production. Larger lift (touches `_verifyAd` and `_verifyGraph` both), but it's
the only option that gives the ATF suite actual coverage of `verify()`'s
decision logic rather than a pass/fail toggle next to it.

**Option C — accept these two as PDI/live-only.**
Mark both specs `active: false` for CI/mock-harness purposes, document that
they're proven by the PDI's real Graph re-read failing naturally (feed
`verify()` a target `sys_id` that doesn't exist, or revoke the Connection alias
mid-run) instead of by fixture injection. Fastest, and consistent with this
runbook's premise that some things need real execution rather than more mock
sophistication — but it means these two properties are validated by hand each
time, not by an automated suite.

**Recommendation:** B if you want the ATF suite to mean something for these two
paths long-term; C if you'd rather spend that effort on the AD lab and M365
tracks instead and accept manual PDI verification here. This is flagged, not
decided, on purpose — pick one and note the choice in `atf/README.md`.

## 6. What this round proves, and what still doesn't

| Claim | Proven by this round? |
|---|---|
| ACLs on the app's own tables behave as specified | Yes — real platform |
| `ecc_queue` insert ACL reviewed and restricted | Yes, for this PDI; production instance still needs its own review |
| 14 of 17 ATF specs pass against real Test Runner semantics | Yes |
| The catalog/UI-only unreconciled-target path actually works | Yes — this is the one the mock harness structurally couldn't touch |
| `verify()`'s two open tests | Only after §5's decision is made and implemented |
| The AD leg's transport, real delegated rights, real domain writes | **No** — needs the AD lab track |
| SER-4 / per-tenant Graph scope wiring | **No** — needs the M365 tenant track |

## 7. Teardown

Nothing here is destructive to anything outside the PDI itself. When done,
either keep the instance (PDIs are free and long-lived if kept active) or let
it hibernate — there's no cleanup action required on your end.

```{=openxml}
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
```

# Day-2 Automation Kit — Live Validation: Active Directory Lab

**Date Code:** 2026-07-30 12:00 ET · **Scope:** FedRAMP Moderate / GCC Moderate ·
**Audience:** the implementer, exercising the AD leg (`AdHybridClient.js` +
`mid/Invoke-Day2AdAction.ps1`) against a real domain controller for the first
time

## 1. What this validates that the mock harness and a PDI both cannot

Every fix to the AD leg so far — the P0-1..P0-3 command-injection / target-
override / cleartext-password remediation (`7d2423c74`) and the ATF-drift
correction that followed (`0d452b75f`) — was verified two ways: reading the
code, and executing it against a **mock** ServiceNow harness (`gs`,
`GlideRecord`, `GlideDateTime` stand-ins) with fixture data standing in for
Active Directory. `CURRENT-STATE-SCRIPTS.md` §1 is explicit about what that
does and doesn't prove: *"a mock ServiceNow harness executed the real script
against fixture data, which is a different thing than a real MID dispatching
to a real DC. ... None of this has been exercised against a live domain
controller yet."*

A [ServiceNow PDI](./CURRENT-STATE-PDI-VALIDATION.md) closes a different gap —
real platform behavior (ACLs, the ATF Test Runner, Scripted REST) — but a PDI
has no domain-joined MID and no reachable domain controller, so anything past
`ecc_queue` is still untested there too (`CURRENT-STATE-PDI-VALIDATION.md` §0).

This lab is the one place that can close the remaining, structurally-different
gap: **real AD write behavior, real delegated-rights enforcement, and real
filter/attribute injection against a real directory** — specifically:

- Does `Invoke-Day2AdAction.ps1`'s parameter allowlist actually stop a hostile
  attribute *name* from reaching AD, or does the mock harness's fixture-shaped
  `$jobArgs` merely make it *look* like it would?
- Does the delegated service account's AD-native access control actually
  refuse everything outside the managed OUs/groups, independent of whatever
  the application-layer allowlist claims — i.e., is the delegation itself
  correct, which every remediation commit so far has flagged as **asserted,
  not verified** (`7d2423c74`'s "Not fixed" list: *"the AD delegation itself
  — every guard here is defense in depth on top of the MID service account's
  actual rights, still unverified"*)?
- Does `moveUserOuAd`'s managed-OU allowlist actually prevent a write from
  reaching AD when unset, or does `_isAllowedOu` just return the right boolean
  in a unit-test sense with nothing behind it?

None of that requires a cloud account, an Azure subscription, an O365 tenant,
or any signup — it's a local Hyper-V VM.

## 2. Running the lab

Provision with [`lab/New-Day2AdLab.ps1`](./lab/New-Day2AdLab.ps1) — read it
before running it; it is meant to be run by a human, one phase at a time, not
piped into automation. Three phases:

| Phase | What it does | Automatable? |
|---|---|---|
| 1 | Create the Internal virtual switch, VHDX, and Gen-2 VM; attach the ISO; start it | Fully scripted |
| — | Windows Setup (OOBE): edition choice, EULA, local Administrator password | **Manual** — no clean unattended path exists that doesn't trade "human types a password once" for "answer file carries a credential on disk"; the script deliberately does not attempt one |
| 2 | Guest network config, AD DS role install, `Install-ADDSForest` (forest promotion) | Scripted via PowerShell Direct; **the promotion reboot is a hard checkpoint** — the script polls for the VM to come back and then stops, it does not chain into Phase 3 |
| 3 | OU structure, delegated MID service account, test AD groups, `dsacls` delegation | Fully scripted via PowerShell Direct, once Phase 2's reboot is confirmed |

You supply the Windows Server evaluation ISO path yourself (Microsoft
Evaluation Center) — the script never downloads one. No password is
hardcoded anywhere in the script; the local Administrator credential, the
DSRM password, and the MID service account password are all `SecureString`
parameters that prompt interactively if you don't supply them.

At the end of Phase 3 the script prints the exact `x_fed_day2_ops.*` property
values this lab corresponds to (`ad_dc`, `ad_disabled_ou`, `ad_managed_ous`)
per `CURRENT-STATE-BUILD-DELTA.md` §2 / `CURRENT-STATE-SCRIPTS.md` §5.

**A judgment call worth double-checking:** the lab is a single DC VM, not a
separate domain-joined "MID Server" VM — sized for "a lone DC lab" per the
brief. That means there's no second box to naturally play the MID's role.
Sections 3-5 below use the **Hyper-V host itself**, reaching the lab DC over
the Internal switch's IP (`10.88.0.10` by default), as a stand-in MID: you run
`Invoke-Day2AdAction.ps1` on the host under the delegated service account's
identity (via `runas /netonly`, since the host is not domain-joined) rather
than on a truly domain-joined machine. That is a real scope simplification —
it proves the AD-write and delegation behavior, but it does not prove
"domain-joined MID reaching AD" as a network/trust configuration, since the
host is not domain-joined. If you want that specific configuration validated
too, join the Hyper-V host (or a second small VM) to `day2lab.test` before
running §3-5; nothing below requires it not to be.

## 3. The adversarial test plan: `Invoke-Day2AdAction.ps1` directly against the lab DC

This bypasses ServiceNow entirely. You are hand-constructing the same
structured JSON job that `AdHybridClient._dispatch` (script-includes/AdHybridClient.js)
would normally build and drop into `ecc_queue`, and feeding it to
`mid/Invoke-Day2AdAction.ps1` yourself:

```
schema: 1, action, identity, server, boundary, args{...}, requested_at
```

Run it as the delegated service account, not as yourself or as a Domain
Admin — that's the whole point:

```powershell
runas /netonly /user:DAY2LAB\svc-day2-mid powershell.exe
# then, inside that shell, from the lab/mid checkout:
$job = @{
    schema = 1; action = 'set-attributes'; identity = 'jdoe'
    server = '10.88.0.10'; boundary = 'gcc-moderate'
    args = @{ "X'; Add-ADGroupMember -Identity 'Domain Admins' -Members 'svc'; #" = 'value' }
    requested_at = (Get-Date).ToUniversalTime().ToString('o')
} | ConvertTo-Json -Compress
.\Invoke-Day2AdAction.ps1 -JobJson $job
```

(Create a throwaway `jdoe` test user in the managed OU first via Phase-3-style
`New-ADUser`, or via a legitimate `create-user` job, so these tests have a
real target that isn't a privileged account.)

Wrap the session in `Start-Transcript` before each run — one of the assertions
below is about what *never appears* in output, and a transcript is the honest
way to check that.

### Test A — hostile attribute name (the P0-1 payload, verbatim from `atf/atf-negative-ad-parameter-injection.xml`)

Payload: `args = { "X'; Add-ADGroupMember -Identity 'Domain Admins' -Members 'svc'; #": "value" }`
against `action: 'set-attributes'`.

- **PASS:** `Invoke-Day2AdAction.ps1` exits non-zero, JSON output has
  `"ok": false`, and `error` contains `"illegal parameter name"` (from
  `Assert-AllowedArgs`'s `^[A-Za-z][A-Za-z0-9]*$` check, which runs before the
  `switch` statement ever reaches `Set-ADUser`). Confirm independently:
  `Get-ADGroupMember "Domain Admins"` before and after the run shows **no
  change** — `svc` (or whatever principal was named in the payload) was never
  added.
- **FAIL:** exit 0 / `"ok": true`, or — the scenario this test exists to rule
  out — the hostile string is actually interpreted as PowerShell and `svc`
  lands in Domain Admins. This is the one test in this plan where a FAIL is a
  live Tier-0 compromise of the lab domain, not just a logic bug; if it fails,
  stop and treat it as a P0 regression, not a lab quirk.

### Test B — reserved-parameter-shaped override, at the layer that actually touches AD

`AdHybridClient.RESERVED` (`identity`, `server`, `credential`, `path`,
`confirm`, `reset`, `newpassword`, `passthru`, `authtype`, `partition`) is
enforced in `AdHybridClient.js`, which this test bypasses entirely — so this
is **not** a test of that array by name. What's actually being tested is
whether the defense-in-depth the PS1 header promises ("Parameter names are
re-validated against a server-side allowlist. ... neither trusts the other")
holds even when the JS layer isn't in the loop at all:

```powershell
$job = @{
    schema = 1; action = 'set-attributes'; identity = 'jdoe'
    server = '10.88.0.10'; boundary = 'gcc-moderate'
    args = @{ identity = 'Administrator'; title = 'x' }
    requested_at = (Get-Date).ToUniversalTime().ToString('o')
} | ConvertTo-Json -Compress
.\Invoke-Day2AdAction.ps1 -JobJson $job
```

- **PASS:** refused with `"parameter not permitted for set-attributes"` —
  `$Contracts['set-attributes']` in `Invoke-Day2AdAction.ps1` does not list
  `identity` (or any of `AdHybridClient.RESERVED`'s other names — verified by
  inspection that none of them appear in any action's allowed-parameter
  array), so the PS1-side allowlist rejects it independently of the JS-side
  check, for a different literal reason. `jdoe`'s `title` is unchanged and
  `Administrator` is untouched — confirm with `Get-ADUser Administrator
  -Properties title`.
- **FAIL:** the job succeeds, or — the specific thing P0-2 was about —
  `Set-ADUser` is actually invoked against `Administrator` instead of `jdoe`.

### Test C — `setPasswordAd` / `reset-password` never transports password material

Two angles, since this bypasses `AdHybridClient.setPasswordAd()`'s own refusal
(`opts.tempPassword` / `opts.password` / `opts.newPassword`) entirely:

1. Try to smuggle a password into the `reset-password` action's args anyway:
   `args = @{ tempPassword = 'Sup3rSecret!' }`.
   **PASS:** refused with `"parameter not permitted for reset-password"` —
   `$Contracts['reset-password']` only allows `mustChangeAtLogon` and
   `deliveryRef`. **FAIL:** accepted.
2. Run a **legitimate** `reset-password` job (no extra args) and inspect the
   transcript and the JSON stdout for the literal generated password.
   **PASS:** the JSON payload's `data.deliveryHandle` is `$null` (no
   `-DeliveryScript` configured in this lab) and grepping the transcript for
   anything resembling a password turns up nothing — `New-CompliantPassword`
   builds the `SecureString` character-by-character and the plaintext
   `$chars` array is cleared before `Write-Result` runs, so there should be no
   window where it existed as a plain `[string]` at all, not just no window
   where it was *printed*. **FAIL:** any plaintext password appears in stdout,
   in the transcript, or (check this too) in `Get-WinEvent` /
   PowerShell transcription logs on the guest if script block logging is on.

This is also structurally the strongest of the three tests: even if
`$Contracts['reset-password']` were accidentally widened to include
`tempPassword` tomorrow, the `'reset-password'` case in the `switch` statement
never reads `$jobArgs['tempPassword']` (or any password-shaped key) at all —
there is no code path from the args bag to `Set-ADAccountPassword`'s
`-NewPassword`. Confirm this by reading the `'reset-password'` branch, not
just by running the test once.

## 4. Testing the delegated-rights boundary itself

This is the item every remediation commit has flagged as open:
`7d2423c74`'s "Not fixed" list explicitly names *"the AD delegation itself —
every guard here is defense in depth on top of the MID service account's
actual rights, still unverified"*, and `CURRENT-STATE-SCRIPTS.md` §1 calls an
effective-permissions dump *"a pre-production must-do, not optional."* This
lab is the first place it can be verified for real, because it's the first
time `svc-day2-mid` exists as an object with real ACEs on real OUs.

Three complementary checks, in increasing order of how much they actually
prove:

1. **Enumerate the raw ACEs.** `dsacls.exe "OU=Day2ManagedUsers,DC=day2lab,DC=test"`
   and the same against the disabled-accounts OU and each test group's DN.
   Confirm the only ACEs naming `DAY2LAB\svc-day2-mid` are the ones Phase 3
   granted (`CCDC;user`, `CA;Reset Password;user`, the three `WP` property
   sets, and `WP;member` on the two named groups) — nothing broader, and
   nothing inherited from a parent container you didn't expect.
2. **The GUI effective-access view.** Active Directory Users and Computers →
   enable **View → Advanced Features** → right-click the managed OU →
   **Properties → Security → Advanced → Effective Access** → select
   `svc-day2-mid` → **View effective access**. This directly answers "can
   this principal do X" per-permission, including permissions it holds via
   nested group membership (it shouldn't hold any here, since it's not a
   member of anything) — a stronger statement than eyeballing raw ACEs.
3. **The functional proof — actually attempt every action as the service
   account, in and out of scope.** This is the one that matters: run
   `Invoke-Day2AdAction.ps1` (via `runas /netonly /user:DAY2LAB\svc-day2-mid`,
   as in §3) for the full action set, and confirm the boundary is enforced by
   **AD itself**, not by the application allowlist:
   - `create-user` targeting the managed OU → succeeds.
   - `disable-user` + the disable-time move to the disabled OU → succeeds.
   - `reset-password` → succeeds.
   - `set-attributes` on the allowed properties → succeeds.
   - `add-group-member` / `remove-group-member` on `Day2Test-Group1` →
     succeeds.
   - `add-group-member` targeting a group **not** delegated (create a throwaway
     `Day2Test-UndelegatedGroup` with no ACE for the service account) → AD
     itself refuses with an access-denied error surfaced through
     `Add-ADGroupMember`'s own exception — this is deliberately **not** the
     same refusal as `PrivilegeClassifier.classifyAdGroup`'s Tier-0 check
     (that check never runs here, since this test bypasses `AdHybridClient.js`)
     — it's proof that AD's own ACL is the backstop even if the application
     layer were bypassed or buggy.
   - `move-object` targeting an OU with no delegation (e.g., the domain's
     default `Users` container) → AD refuses at the `Move-ADObject` call.

   Anything in this list that **succeeds when it shouldn't**, or **fails when
   it shouldn't**, is a real delegation-configuration finding — not a mock, not
   an assertion, an actual AD access-control fact about this build.

## 5. `moveUserOuAd` fail-closed: allowlist unset, allowed, and disallowed

Unlike §3-4, `_isAllowedOu` — the fail-closed check `moveUserOuAd` and
`createUserAd` both call — lives in `AdHybridClient.js`, not in
`Invoke-Day2AdAction.ps1`. **Bypassing ServiceNow bypasses the exact code path
this test needs to exercise**, so hand-crafting a JSON job straight to the PS1
script (as in §3) cannot test this — the PS1 script's `move-object` handler
has no OU-allowlist check of its own at all; it will attempt a move to
whatever `targetOu` string it's given. That absence is itself worth noting:
the managed-OU allowlist is enforced exactly once, in the JS layer, with no
defense-in-depth copy in the PS1 layer the way the parameter allowlist has one
(§3 Test B). If `AdHybridClient.js` is ever bypassed by anything with direct
`ecc_queue` insert access (`CURRENT-STATE-BUILD-DELTA.md` §5's documented
exposure), `_isAllowedOu` provides no protection at all — this lab is a good
place to have confirmed that concretely rather than inferred it from reading
the code.

So this test needs `AdHybridClient.js` itself in the loop, without needing a
ServiceNow instance or any signup. A small local, offline `gs`/`GlideRecord`
shim — the same style of mock harness already used to verify `0d452b75f`, not
currently checked into this repo — run with `node` does this with no account
of any kind:

```javascript
// day2-ad-harness.js — run locally: node day2-ad-harness.js
const { execFileSync } = require('child_process');
const props = {}; // set per test case below
global.gs = {
  getProperty: (k, d) => (k in props ? props[k] : d),
  error: console.error, warn: console.warn, info: console.log
};
global.Class = { create: () => function () {} };
global.GlideDateTime = function () { this.getValue = () => new Date().toISOString(); };
global.x_fed_day2_ops = { Day2Env: function () {
  this.isTestMode = () => false; this.testFixture = (k, d) => d;
} };
Day2Env.scrub = (m) => m; // matches the real static helper's shape closely enough for logging calls
global.GlideRecord = function (table) {
  this._table = table; this._fields = {};
  this.initialize = () => {};
  this.setValue = (k, v) => { this._fields[k] = v; };
  this.insert = () => {
    if (this._table !== 'ecc_queue') return 'mock-sys-id';
    // THIS is the wiring that makes it real: the ecc_queue insert shells out
    // to the actual PS1 against the actual lab DC, instead of just recording
    // the JSON for an assertion to inspect.
    const out = execFileSync('powershell.exe', [
      '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
      '-File', 'mid/Invoke-Day2AdAction.ps1', '-JobJson', this._fields.payload
    ], { encoding: 'utf8' });
    console.log('MID result:', out);
    return 'live-dc-dispatch';
  };
};
// load the real file unmodified:
require('vm').runInThisContext(
  require('fs').readFileSync('script-includes/AdHybridClient.js', 'utf8')
);
const ad = new AdHybridClient();
console.log(ad.moveUserOuAd(process.argv[2], process.argv[3]));
```

Run this **as the delegated service account** (same `runas /netonly` context
as §3-4) so the shelled-out PS1 actually exercises AD under the account whose
delegation you're validating, not under your own or an elevated identity.

- **5a — `ad_managed_ous` unset/empty.** Leave `props['x_fed_day2_ops.ad_managed_ous']`
  unset. **PASS:** `moveUserOuAd` returns `{ ok: false, error: 'refused: ...' }`
  and the `GlideRecord.insert` override above is **never called** — confirm by
  adding a `console.log` guard or just noting no `MID result:` line printed —
  meaning no job ever reached AD at all. Read back the test user's OU in the
  lab DC afterward: unchanged. **FAIL:** the move dispatches (the PS1 runs)
  regardless of the empty property, or the object's OU changes.
- **5b — target OU on the allowlist.** Set
  `props['x_fed_day2_ops.ad_managed_ous'] = 'OU=Day2ManagedUsers,DC=day2lab,DC=test'`
  and move into that same OU. **PASS:** dispatches, the PS1 runs against the
  real DC, and `Get-ADUser <id> | Select DistinguishedName` confirms the
  object actually moved.
- **5c — target OU NOT on the allowlist.** Same property value as 5b, but
  target a DN not on the list (e.g. the domain's default `Users` container,
  or the disabled-accounts OU if it isn't also listed). **PASS:** refused
  before dispatch, same as 5a — no `MID result:` line, no PS1 invocation, and
  the object's OU is unchanged in the lab DC afterward (this is the detail a
  pure logic/unit check of `_isAllowedOu` can't give you: proof that a refused
  call leaves **zero** trace in AD, not just that the boolean came back
  false).

## 6. What remains unverified even after this lab

- **Production delegation may differ from the lab's.** The `dsacls` grants in
  `lab/New-Day2AdLab.ps1` Phase 3 are illustrative, matched to the actions the
  kit performs — they are not guaranteed to be the precise minimum for every
  attribute in `AttrParamMap`, and a real environment's OU naming, nesting,
  and existing delegation model will differ from this lab's flat structure.
  Re-run §4's functional proof against the real target OUs before go-live,
  not just this lab's.
- **Entra Connect sync behavior is entirely out of scope here.** This lab has
  no Entra tenant and no sync engine; the projection from an AD write to a
  synced Entra object (`CURRENT-STATE-SCRIPTS.md` §1's "sync-projection"
  concept, `atf-hybrid-verify-sync-projection.xml`) is cloud-side and needs
  the M365/Entra tenant track, not this one.
- **The `ecc_queue` insert-ACL exposure** (`CURRENT-STATE-BUILD-DELTA.md` §5)
  is a ServiceNow-platform configuration fact. This lab proves what happens
  once a job reaches the MID; it says nothing about who else, on a real
  instance, can insert one — that's the PDI/production-instance track.
  §5 above independently reinforces *why* that ACL matters: it's the only
  thing standing between "the JS-layer allowlist is bypassed" and
  `_isAllowedOu` providing zero protection.
- **The production transport is the Integration Hub AD spoke
  (`CURRENT-STATE-SCRIPTS.md` §7), not this skeleton script.** Everything
  above validates `Invoke-Day2AdAction.ps1` and `AdHybridClient.js` as
  written today; the spoke migration carries the same method surface forward
  but is a different transport with its own platform behavior to validate
  separately once built.
- **A single-DC lab doesn't exercise replication lag** or the
  `ad_dc`-pinning rationale (write and verify hitting the same DC to avoid a
  stale read from a different DC) — there's only one DC here to hit.
- **The two open `verify()` test-mode ATF specs**
  (`atf-negative-verify-read-failure.xml`, `atf-negative-verify-wrong-state.xml`,
  flagged in `CURRENT-STATE-PDI-VALIDATION.md` §5) are unrelated to the AD
  transport and are not touched by anything in this lab.
- **This lab used a Windows Server evaluation build** (see the script's
  header for which one you pointed it at) and a single flat OU structure —
  cmdlet behavior on a different Windows Server version, or against a deep
  multi-level OU tree, functional-level considerations, or an existing
  forest with legacy delegation already in place, is not exercised here.

## 7. Teardown

This is disposable infrastructure; nothing here is destructive to anything
outside itself, because the virtual switch is Internal (host-and-guest-only,
never bridged to a real network) and the domain (`day2lab.test`, a reserved
non-resolvable TLD per RFC 2606) has no trust relationship to anything real.

```powershell
Stop-VM -Name Day2AdLab-DC1 -TurnOff -Confirm:$false
Remove-VM -Name Day2AdLab-DC1 -Confirm:$false
Remove-Item -LiteralPath (Join-Path $PSScriptRoot 'lab\vhd\Day2AdLab-DC1.vhdx') -Force
Remove-VMSwitch -Name Day2AdLab-Internal -Confirm:$false
# If you assigned a static IP to the host's vEthernet adapter for this switch,
# it's removed automatically when the switch is removed.
```

If you joined a second machine (or the host) to `day2lab.test` per §2's note,
un-join or discard that machine too — it now trusts a domain that's about to
stop existing.

```{=openxml}
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
```

# `x_fed_compliance` — Live Validation: Microsoft 365 Developer Tenant

**Date Code:** 2026-07-30 11:34 ET · **Scope:** FedRAMP Moderate / GCC Moderate ·
**Audience:** the implementer validating `ComplianceGate._checkWriteScope`
(SER-4) against a real Entra tenant for the first time

## 0. Why this exists, and what it does not prove

SER-4 was, until now, a deliberate gap: `_checkWriteScope` returned
`'unverified'` unconditionally in production, with a `TODO(per-tenant)` where
the Graph read belonged. The commit that closed it (see this repo's history
for the `ComplianceGate.js` change implementing the Graph read) added the
actual `appRoleAssignments` / `oauth2PermissionGrants` read, a name-shape match
against `*.ReadWrite.*` and other write-shaped Graph permission strings, and
two `test_mode` ATF specs (`atf/atf-scope-check-confirmed-readonly.xml`,
`atf/atf-scope-check-holds-write.xml`) that exercise the matching logic against
fixture data. That fixture pass is real coverage of the *matching logic* — it
is **not** proof the code correctly reads a real tenant's real
`appRoleAssignments` shape, correctly resolves an `appRoleId` GUID to its
permission string via the resource service principal's `appRoles` collection,
or correctly walks a real `oauth2PermissionGrants` response. A fixture cannot
be wrong about Graph's actual response shape in the way a live tenant can.

**What this validation round proves:** that `_checkWriteScope`, pointed at a
real Entra tenant through the same MID-routed `sys_rest_message` /
credential-alias wiring `ComplianceIngest` already uses, correctly returns
`'confirmed-readonly'` for a registration that genuinely holds only
read-shaped Graph grants, and `'holds-write'` for one that holds a
write-shaped grant — using two real app registrations with real, admin-consented
permissions, not stand-ins.

**What it does not prove:** that scope stays clean over time on any tenant
whose configuration is not otherwise locked down, or that a registration
cannot be reconfigured to add a write scope *between* two ComplianceGate runs
without this check catching it mid-window. See §5.

**What this tenant is not:** a FedRAMP-authorized boundary. It's a free
developer sandbox for validating that the code path itself works against real
Graph responses. Nothing here substitutes for standing up the production
tenant wiring, which still needs its own scope_check_enabled rollout plan,
its own credential-alias review, and its own decision about which resource
(s) count as "governed surfaces" for this tenant.

## 1. Get a tenant: the Microsoft 365 Developer Program

This step is yours to do — the instructions below describe what to click, not
something already done on your behalf.

1. Go to `developer.microsoft.com/microsoft-365/dev-program` (or search
   "Microsoft 365 Developer Program") and sign up. It's free, self-service,
   and requires only a Microsoft account.
2. Choose the **instant sandbox** option when prompted. This provisions a
   full Microsoft 365 tenant (a `*.onmicrosoft.com` domain) pre-loaded with an
   E5 developer subscription, test users, and sample data — no credit card,
   no purchase.
3. You'll land in the Microsoft 365 admin center for your new tenant, plus
   access to the Entra admin center (`entra.microsoft.com`) for the same
   tenant. Note the tenant ID (Entra ID > Overview) — you'll need it for the
   REST message endpoint / credential alias configuration in §3.
4. The dev tenant has an inactivity reclamation policy (currently ~90 days of
   no sign-in) — sign in periodically if you're spacing this work out, the
   same caution `CURRENT-STATE-PDI-VALIDATION.md` gives for a ServiceNow PDI
   hibernating.

## 2. Register two test app registrations

You need two, so both verdicts get exercised against a real tenant's real
`appRoleAssignments`, not just one path proven and the other taken on faith.

### 2a. The read-only registration (expect `'confirmed-readonly'`)

1. Entra admin center → **App registrations** → **New registration**. Name it
   something unambiguous, e.g. `x-fed-compliance-scope-test-readonly`.
   Single-tenant is fine for this test.
2. **API permissions** → **Add a permission** → **Microsoft Graph** →
   **Application permissions** (not Delegated — `ComplianceIngest` and the
   scope check both care about the app-only grant a service identity holds,
   not a signed-in user's delegated rights). Add:
   - `Directory.Read.All`
   - `Policy.Read.All`
   - `SecurityEvents.Read.All`

   These are the exact three the app's own `rest/README.md` documents as the
   intended production grant set (`Policy.Read.All, Directory.Read.All,
   SecurityEvents.Read.All`).
3. **Grant admin consent** for the tenant — as the dev-tenant Global Admin
   (your own account), click **Grant admin consent for <tenant>** on the API
   permissions page. Without this, the permissions show as "not granted" and
   won't appear in `appRoleAssignments` at all, which would make the read
   look empty rather than read-only — a different thing.
4. **Certificates & secrets** → create a client secret (or certificate, if
   your credential-alias setup in §3 uses one) — needed for the REST message
   credential, not for this app's own logic.
5. Under **Overview**, note the **Application (client) ID**. Then go to
   **Enterprise applications** (this is where the app's *service principal*
   lives, not the app registration itself), find the same app by name, and
   note its **Object ID** — this is the `service_principal_id` value
   `_checkWriteScope` actually queries against (`/servicePrincipals/{id}/...`),
   distinct from the application object ID and the client ID. Confusing these
   three IDs is the single most common setup mistake here.

### 2b. The write-scoped registration (expect `'holds-write'`)

1. Repeat the same steps under a second registration, e.g.
   `x-fed-compliance-scope-test-writescoped`.
2. Grant **Application permissions**: `Directory.Read.All`, `Policy.Read.All`
   (kept, so the fixture isn't *only* about the one flagged grant), plus
   **`Directory.ReadWrite.All`** — the canonical write-shaped Graph
   permission, and the one named explicitly in `ComplianceGate.js`'s own
   comments as the thing this check exists to catch.
3. **Grant admin consent** the same way as 2a.
4. Note this registration's service principal **Object ID** the same way.

You now have two real, admin-consented registrations: one that should read
back as clean, one that should trip the write-shaped match.

## 3. Wire the instance

Do this in a ServiceNow PDI or sub-prod instance where you've already built
`x_fed_compliance` per `update-set/README.md` (Script Includes imported, the
`x_fed_compliance.graph` REST message created per `rest/README.md`). If you
haven't built it yet, do that first — this validation exercises the built
app, it doesn't build it for you.

1. **Credential alias** — point the `x_fed_compliance.graph` REST message's
   OAuth 2.0 credential (or Connection & Credential alias, depending on your
   platform version) at the dev tenant: tenant ID from §1, client ID +
   secret/certificate from whichever registration you're testing in a given
   run. Because `_checkWriteScope` only ever reads (`appRoleAssignments`,
   `oauth2PermissionGrants`), the credential itself needs no write scope of
   its own to exercise this test — but see the judgment call at the end of
   this section.
2. **MID Server** — either use an existing in-boundary MID (if this sub-prod
   instance has one reachable to the internet / to `graph.microsoft.com`) or,
   for this validation only, leave `x_fed_compliance.mid_server` unset so the
   call routes through the instance's own outbound connectivity. Note which
   you used — a MID-routed pass and a direct pass are both informative, but
   they're not the same test, and production is MID-routed only.
3. Set properties:
   - `x_fed_compliance.test_mode` = `false` (you are explicitly testing the
     production Graph-read path here, not the fixture path — leaving
     `test_mode` on would silently exercise `_checkWriteScopeFixture` instead
     and prove nothing about the live tenant).
   - `x_fed_compliance.scope_check_enabled` = `true`.
   - `x_fed_compliance.service_principal_id` = the **Enterprise
     application Object ID** from §2a (start with the read-only one).
4. Confirm `gate.preflight(...)`'s SoD checks are satisfied for whatever task
   record you use to trigger this — or, more directly, just call
   `_checkWriteScope()` on a `ComplianceGate` instance from a background
   script / scoped script include test, exactly as the two new ATF specs call
   it, since `preflight` is not itself under test here.

## 4. Run it against both registrations

1. With `service_principal_id` pointed at the **read-only** registration
   (§2a), invoke:
   ```javascript
   var gate = new x_fed_compliance.ComplianceGate();
   gs.info('verdict: ' + gate._checkWriteScope());
   ```
   **Expected:** `confirmed-readonly`. If you instead get `unverified`, check
   (in order): admin consent actually granted (§2a step 3), the credential
   alias actually authenticating (inspect the REST message's transaction log
   for a non-200), and that `service_principal_id` is the Enterprise
   Application object ID, not the Application (client) ID.
2. Re-point `service_principal_id` at the **write-scoped** registration
   (§2b) and re-run the same call. **Expected:** `holds-write`.
3. This is the actual "SER-4 validated against real infrastructure" proof:
   both verdicts produced by the real Graph read against real, admin-consented
   `appRoleAssignments` on a real tenant — not by the `test_mode` fixture
   path, which only proves the string-matching logic in isolation.
4. As a negative control, temporarily set `service_principal_id` to a random
   GUID that isn't a real service principal in the tenant. **Expected:**
   `unverified` (the `/servicePrincipals/{id}/appRoleAssignments` read
   returns a non-200, and `_graphGet` returns `null`, and `_checkWriteScope`
   treats that as an unresolvable read, not an empty/clean one). This
   specifically confirms the fail-closed contract from `ComplianceGate.js`'s
   own comments — an unreadable identity must never look the same as a
   verified-clean one.

## 5. What's still not covered even after this round

- **Scope drift between checks.** `_checkWriteScope` is a point-in-time read.
  Nothing here (or in `ComplianceGate` generally) re-checks continuously — if
  someone grants `Directory.ReadWrite.All` to the read-only registration's
  service principal an hour after a `'confirmed-readonly'` verdict, the next
  task's `preflight` will catch it on its own next call, but there is no
  standing monitor, alert, or drift-detection job watching the grant between
  gate invocations. A compliance program that runs `preflight` infrequently
  has a correspondingly wide blind window.
- **A compromised or reconfigured app registration between checks.** This
  check answers "does the identity hold write scope right now," not "has this
  identity's configuration, ownership, or credential been tampered with since
  the last check." An attacker (or an unrelated admin action) who adds a
  write-shaped grant and then removes it again between two `preflight` calls
  would produce two clean reads bracketing an unobserved write-capable window
  — this is a real gap, not addressed here, and would need something like a
  Graph audit-log-driven alert on `appRoleAssignments`/`oauth2PermissionGrants`
  changes to this specific service principal, which is future work.
- **The credential alias behind the REST message itself.** This validation
  confirms `_checkWriteScope`'s own read logic; it says nothing about whether
  the credential used to make that read is itself over-scoped, long-lived, or
  shared with another integration. `rest/README.md` documents the intended
  read-only grant for `ComplianceIngest`'s own credential, but nothing in this
  round independently re-verifies that credential's actual grant — arguably
  the same check ought to be run against the REST-message credential's own
  service principal too, not only against a purpose-built test registration.
- **Per-resource scoping of "write-shaped."** `_isWriteShaped` (in
  `ComplianceGate.js`) flags any `*.ReadWrite.*` / `*.Write.*` /
  `*.FullControl.*` / `*.Manage.*` grant on the identity, regardless of Graph
  resource — deliberately broader than "only over the surfaces this app
  governs" (see the judgment call in that method's own comment). Whether that
  breadth is correct for your tenant's actual risk model, versus scoping the
  check to just Directory/Policy/SecurityEvents-shaped permissions, is a
  decision worth revisiting once this is wired for real, not something this
  round settles.
- **`Directory.AccessAsUser.All`-shaped delegated permissions.** Name-shape
  matching does not catch delegated grants that carry no "Write" token but
  inherit the signed-in user's own rights (which could include write). This
  registration-test setup used application permissions throughout for
  exactly that reason; if your production integration ever adds a delegated
  flow, this gap needs its own follow-up.

## 6. Teardown

Nothing here is destructive outside the dev tenant itself.

- Entra admin center → **App registrations** → delete both test
  registrations (this also removes their service principals and any
  consented grants).
- Revert the sub-prod instance's properties (`test_mode`,
  `scope_check_enabled`, `service_principal_id`) to whatever your normal
  build/test baseline is, so a later, unrelated ATF run doesn't inherit a
  live-tenant credential alias by accident.
- The M365 Developer Program tenant itself can be kept (it's free and
  reusable for future validation rounds) or allowed to lapse — there's no
  cleanup action required against Microsoft's side beyond deleting the test
  registrations above.

```{=openxml}
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
```

# Appendix A — Where this lives in the repo

| Item | Path |
|---|---|
| ServiceNow PDI runbook | `docs/customer-documents/orgcomp-series/servicenow-day2/CURRENT-STATE-PDI-VALIDATION.md` |
| AD Lab runbook | `docs/customer-documents/orgcomp-series/servicenow-day2/CURRENT-STATE-AD-LAB-VALIDATION.md` |
| AD Lab provisioning script | `docs/customer-documents/orgcomp-series/servicenow-day2/lab/New-Day2AdLab.ps1` (shipped alongside this RunBook as a separate file — it's executable PowerShell, not prose, and is meant to be read before it's run) |
| M365 Tenant runbook | `docs/customer-documents/orgcomp-series/x_fed_compliance/LIVE-VALIDATION-M365-TENANT.md` |
| SER-4 code fix | `docs/customer-documents/orgcomp-series/x_fed_compliance/script-includes/ComplianceGate.js` (`_checkWriteScope` and helpers) |
| New ATF specs | `x_fed_compliance/atf/atf-scope-check-confirmed-readonly.xml`, `atf-scope-check-holds-write.xml` |

Everything above is committed on `main` at `84bdb28ca`. Nothing has been
pushed to a remote or merged beyond the local repository as part of producing
this RunBook.
