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
