# Day-2 Automation Kit — Live Validation: the MID Server Bridge

**Date Code:** 2026-08-31 17:05 ET · **Scope:** FedRAMP Moderate / GCC Moderate ·
**Audience:** the implementer joining a real ServiceNow instance to a real
domain controller for the first time

## 0. What this closes, and what it does not

Two live-validation tracks already exist, and each proves something the other
structurally cannot:

| Track | Proves | Cannot prove |
|---|---|---|
| [ServiceNow PDI](./CURRENT-STATE-PDI-VALIDATION.md) | Real platform behaviour — ACL enforcement, the ATF Test Runner, Scripted REST role checks | Anything past `ecc_queue`. A PDI has no domain-joined MID and no reachable DC |
| [AD lab](./CURRENT-STATE-AD-LAB-VALIDATION.md) | Real AD writes, real delegated-rights enforcement, real attribute/filter injection behaviour | Anything about ServiceNow. It invokes `mid/Invoke-Day2AdAction.ps1` directly, from a shell on the lab host |

**Neither exercises the seam between them.** `AdHybridClient._dispatch` inserts
an `ecc_queue` row and returns `{ ok, dispatched, ecc_sys_id }`; every write
method's closure then depends on `resolveDispatch` reading a *response* row back.
In the PDI track nothing ever picks that row up. In the AD lab track no row is
ever written. The transport itself — ServiceNow → ECC → MID → PowerShell → AD →
ECC → `resolveDispatch` — is the one part of the AD leg that no test in this kit
has ever executed end to end.

This document builds that bridge and runs one round trip through it.

**What it does not prove.** A PDI is a personal commercial sandbox, not a
FedRAMP-authorized boundary, and `day2lab.test` is a throwaway domain. This
proves the *mechanism* works. It substitutes for "we believe the ECC contract is
consistent on both sides"; it substitutes for nothing in an ATO.

**Safety boundary, stated once.** The MID Server you build here holds credentials
for a ServiceNow instance and sits on a network with a domain controller that
grants it delegated write rights. Build it on throwaway infrastructure, point it
only at the lab domain, and delete it afterwards (§8). Never register a lab MID
against a production instance, and never point a lab MID at a real domain.

## 1. The contract the bridge has to carry

Read from `script-includes/AdHybridClient.js` `_dispatch()` — this is what
ServiceNow actually writes, not a description of what it ought to write:

| `ecc_queue` field | Value |
|---|---|
| `agent` | `mid.server.` + the `x_fed_day2_ops.ad_mid_server` property |
| `topic` | `Command` |
| `name` | `Invoke-Day2AdAction` |
| `source` | `x_fed_day2_ops.AdHybridClient` |
| `queue` | `output` |
| `payload` | `JSON.stringify(job)` — see below |

The `job` object, again from the source:

```json
{
  "schema": 1,
  "action": "get-user",
  "identity": "<resolved by the class, never caller-supplied>",
  "server": "<x_fed_day2_ops.ad_dc, or null>",
  "boundary": "gcc-moderate",
  "args": { "properties": ["..."] },
  "requested_at": "<GlideDateTime>"
}
```

`resolveDispatch()` then expects a **response row**: `queue = input`,
`response_to = <the dispatch sys_id>`, and a `payload` that parses to
`{ ok: true, data: {...}, dc, observed_at }`. It **fails closed** — a missing,
errored, or unparseable response is `ok:false`, never an assumed success. That
property is what you are here to confirm survives a real transport.

### 1.1 The payload-shape question — resolve this first

`_dispatch` writes **raw JSON** into `payload`. The stock ECC `Command` probe
convention is an XML `<parameters>` document, and `mid/Invoke-Day2AdAction.ps1`
documents its own entry contract as:

```
powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass `
    -File Invoke-Day2AdAction.ps1 -JobJson $env:DAY2_JOB_JSON
```

So there are two open questions, and **they are the substance of this track** —
everything else here is assembly:

1. Does the probe your instance dispatches hand the raw `payload` string to the
   script, or does it expect the XML parameter shape?
2. If the latter, which side changes — the ServiceNow side (`_dispatch` emits
   the conventional shape) or the MID side (a MID Server script that reads the
   raw payload and sets `DAY2_JOB_JSON` before invoking the script)?

**Do not guess this from documentation.** Determine it empirically in §5, where
a single dispatch tells you exactly what arrived. Whichever way it resolves,
record it in `CURRENT-STATE-BUILD-DELTA.md` — it is a build-affecting fact, not
a lab detail.

The honest status today: **the two sides of this contract have never been
observed agreeing.** The mock harness supplies fixture-shaped `$jobArgs`
directly, which is precisely the kind of convergence that can look correct on
both sides while the seam between them does not fit.

## 2. Topology, and the one constraint that shapes it

`lab/New-Day2AdLab.ps1` creates a Hyper-V **Internal** switch on purpose: the
lab DC runs DNS and Kerberos for `day2lab.test`, and an Internal switch keeps
that off your physical LAN where it could collide with real DHCP, DNS, or
Kerberos realms. The script's own header is explicit that changing it to
External is a consequence you must understand first.

But a MID Server must reach the ServiceNow instance over outbound HTTPS. A
PDI is on the public internet. So:

```
   physical LAN / internet
            │
            │  outbound HTTPS 443 only
            ▼
   ┌──────────────────┐        ┌────────────────────────┐
   │  MID VM          │        │  ServiceNow PDI        │
   │  (domain-joined) │───────▶│  devNNNNN.service-now  │
   │                  │        └────────────────────────┘
   │  NIC 1: Default  │
   │          Switch  │  ← NAT to the internet
   │  NIC 2: Day2Ad-  │
   │      Lab-Internal│  ← the lab segment only
   └────────┬─────────┘
            │  LDAP / Kerberos to 10.88.0.10
            ▼
   ┌──────────────────┐
   │  Lab DC          │   day2lab.test
   │  10.88.0.10      │   Internal switch ONLY — never dual-homed
   └──────────────────┘
```

**The MID VM is the only machine that is dual-homed, and the DC must never be.**
That single asymmetry is what lets a cloud instance drive a private domain
without exposing the domain. If you find yourself adding a second NIC to the DC,
stop — you have moved the lab onto your real network.

## 3. Prerequisites

- The AD lab from `CURRENT-STATE-AD-LAB-VALIDATION.md`, built and reachable —
  DC at `10.88.0.10`, domain `day2lab.test`, the `svc-day2-mid` delegated
  service account, and the `Day2ManagedUsers` / `Day2DisabledAccounts` OUs.
- A ServiceNow PDI with the scoped app built per `CURRENT-STATE-PDI-VALIDATION.md`.
- A second Windows Server evaluation VM for the MID host. Do **not** install the
  MID on the domain controller: it would collapse the delegation model this kit
  exists to prove, since anything running on a DC has effective rights far beyond
  `svc-day2-mid`'s.
- Java is bundled with current MID installers; if your release requires a
  separate JRE, the instance's MID download page states it.

## 4. Build and register the MID host

1. **Create the VM** with both NICs — the NAT/Default switch and
   `Day2AdLab-Internal`. Give the internal NIC a static address on the lab
   subnet (e.g. `10.88.0.20/24`) and point its DNS at `10.88.0.10`. Leave the
   external NIC on DHCP. Do **not** set a default gateway on the internal NIC.
2. **Join it to `day2lab.test`.** Confirm `nltest /dsgetdc:day2lab.test`
   resolves and that `Resolve-DnsName devNNNNN.service-now.com` still works —
   both legs must function simultaneously, and a mis-ordered NIC binding is the
   usual reason one stops.
3. **Run the MID service as `svc-day2-mid`**, not as LocalSystem and not as a
   domain admin. This is the whole point: the MID's AD rights must be exactly
   the delegated rights the kit assumes, so that a defect in the application-layer
   allowlist is *contained* by the directory's own access control. Running it as
   anything more privileged means a green result here proves nothing about
   production.
4. **Install and validate.** Download the installer from the instance
   (**System Definition → MID Servers → Download MID Server**), install it,
   then in the instance validate the MID record and confirm it reports **Up**.
5. **Install RSAT ActiveDirectory** on the MID host —
   `Invoke-Day2AdAction.ps1` imports it and will fail immediately without it:
   `Install-WindowsFeature RSAT-AD-PowerShell`.
6. **Stage the script.** Copy `mid/Invoke-Day2AdAction.ps1` to a fixed path on
   the MID host (e.g. `C:\Day2\Invoke-Day2AdAction.ps1`). Record that path — §5
   needs it, and it belongs in `CURRENT-STATE-BUILD-DELTA.md`.

Then set the instance properties the client reads
(`gs.getProperty` calls in `AdHybridClient.js`):

| Property | Lab value |
|---|---|
| `x_fed_day2_ops.ad_mid_server` | the MID record's **Name** (the client prefixes `mid.server.`) |
| `x_fed_day2_ops.ad_dc` | `dc1.day2lab.test` |
| `x_fed_day2_ops.ad_managed_ous` | the `Day2ManagedUsers` / `Day2ManagedGroups` DNs |
| `x_fed_day2_ops.ad_disabled_ou` | the `Day2DisabledAccounts` DN |
| `x_fed_day2_ops.ad_await_ms` | leave default (15000) for the smoke test |

`_dispatch` refuses outright when `ad_mid_server` is empty
(*"ad_mid_server not configured — refusing to actuate"*), so a blank property is
a refusal, not a silent no-op. Confirm you can see that refusal before you fix
it — it is one of the fail-closed behaviours worth observing once.

## 5. The instrumented first dispatch — answer §1.1 empirically

Do this **before** attempting a round trip. Pick `get-user`: it is the only
action that is purely a read, so a mis-shaped payload costs nothing.

1. In a background script, dispatch one read:

   ```javascript
   var c = new AdHybridClient();
   var r = c.getUserAd('svc-day2-mid', ['samAccountName', 'distinguishedName']);
   gs.info('dispatch: ' + JSON.stringify(r));
   ```

2. Open the `ecc_queue` row by the returned `ecc_sys_id` and read its `payload`
   **as stored**. Confirm it is the JSON from §1 and note whether `agent`
   matches your MID's name exactly — a mismatch here means the MID never sees
   the row at all, and it presents as silence rather than as an error.

3. On the MID host, watch the agent log while the row is picked up. What you
   are looking for is the single fact that decides §1.1: **what the probe passed
   to the command line.** Three outcomes, each with a different next step:

   | What you observe | What it means | Next step |
   |---|---|---|
   | The script ran and `-JobJson` received the JSON | The contract already fits | Go to §6 |
   | The script ran but `$JobJson` was empty, or the probe passed XML | Shape mismatch, as §1.1 anticipates | Add a MID-side wrapper that reads the raw payload into `DAY2_JOB_JSON`, or change `_dispatch` to the conventional shape. Record the choice |
   | Nothing was picked up at all | Routing, not shape | Check `agent` exactly matches `mid.server.<Name>`, the MID is **Up**, and its capabilities permit the probe |

4. Whatever you find, **write it down in `CURRENT-STATE-BUILD-DELTA.md` before
   continuing.** This is the fact the kit currently does not know, and the next
   implementer should not have to rediscover it.

## 6. The round trip

With the shape resolved, run the full path and assert on the *return*, which is
the half that has never executed:

```javascript
var c = new AdHybridClient();
var d = c.getUserAd('svc-day2-mid', ['samAccountName', 'distinguishedName']);
gs.info('dispatched: ' + JSON.stringify(d));

var res = c.awaitDispatch(d.ecc_sys_id);   // bounded, capped at 60s
gs.info('resolved: ' + JSON.stringify(res));
```

Confirm all four, and treat any one of them failing as the track not passing:

1. **A response row exists** — `queue = input`, `response_to` = the dispatch
   `sys_id`.
2. **`resolveDispatch` returns `ok:true`** with `data` carrying the observed
   attributes, plus `dc` and `observed_at`.
3. **The observed state is real** — the `distinguishedName` is the lab's actual
   DN for `svc-day2-mid`, not an echo of the request.
4. **The negative case fails closed.** Stop the MID service and dispatch again.
   `awaitDispatch` must return `ok:false` with *"timed out waiting for MID
   response … inconclusive, not closed"* — **not** a success and not a silent
   pass. A read that cannot complete must never look like a clean result; this
   is the specific property `resolveDispatch` was written to hold, and this is
   the first time it can be observed against a real transport.

Then run one **write** — `add-group-member` against `Day2Test-Group1` — and
verify with `isGroupMemberAd` that the post-state read-back reflects it. That
exercises the same seam in the direction that changes the directory, and it is
the pattern every governed catalog item ultimately depends on.

## 7. Evidence to record

For `CURRENT-STATE-PILOT-ROLLOUT.md` §0 and for the next implementer:

- MID release, host OS build, and the account the service runs as.
- The §1.1 resolution — which side changed, and the diff.
- The four §6 assertions, each pass/fail, with the `ecc_sys_id` values.
- The stopped-MID negative result, quoted verbatim.
- An effective-permissions dump for `svc-day2-mid` against `Day2ManagedUsers`.
  The delegation has been **asserted, not verified** in every commit so far; a
  working bridge is the first context in which it can be measured rather than
  claimed.

## 8. Teardown

Delete the MID record in the instance **before** destroying the VM — an
orphaned MID record leaves a stale, permanently-down agent that later
dispatches will silently queue against. Then remove the VM and its VHDX, and
revoke the `svc-day2-mid` credentials from the instance's Connection &
Credential aliases.

## 9. Still unproven after this track

Stated plainly, so nobody reads a green round trip as more than it is:

- **This is not a boundary.** A PDI is a commercial sandbox; `day2lab.test` is
  disposable. Nothing here is FedRAMP evidence.
- **One DC, one domain, no replication.** Multi-DC convergence, cross-domain
  identity, and replication latency are untested.
- **No Entra Connect.** The hybrid *projection* half of the VERIFY clause
  (`EntraHelpdeskGate._projectionNote`) still has no sync to observe, so
  cloud-side post-state remains mock-proven only.
- **Scale and concurrency.** One dispatch at a time says nothing about ECC
  behaviour under a real queue depth.
