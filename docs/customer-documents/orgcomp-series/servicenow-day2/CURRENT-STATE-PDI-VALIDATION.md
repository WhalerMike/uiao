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
