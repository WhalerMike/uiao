# ATF test — provision happy path

An **Automated Test Framework** test for the DDI front door: it drives a real request
end-to-end (order → approve → allocate → register → gate → close) and asserts each stage,
so a regression in the catalog item, the Flow, or the Script Includes fails a test instead
of a production request.

| Test | File | Proves |
|---|---|---|
| Happy path | [`atf-provision-happy-path.xml`](./atf-provision-happy-path.xml) | order → approve → allocate → register → gate pass → CMDB → closed complete |
| Negative: gate fail | [`atf-negative-gate-fail.xml`](./atf-negative-gate-fail.xml) | a failed validation gate routes back to approval and does **not** close (CM-6) |
| Negative: SaaS boundary | [`atf-negative-saas-boundary.xml`](./atf-negative-saas-boundary.xml) | `universal_ddi` without `acknowledge_saas_boundary` is blocked, never provisions |
| Negative: self-approve | [`atf-negative-self-approve.xml`](./atf-negative-self-approve.xml) | the requester cannot approve their own request (AC-5/AC-6 SoD) |

> **Starter skeleton.** ATF tests are `sys_atf_test` + `sys_atf_step` records whose steps
> reference built-in step configs by an instance/version-specific `sys_id` and carry an
> opaque encoded `inputs` field — neither is authorable outside an instance. The XML names
> each step's config by **title** and gives its inputs/assertion script in readable form;
> **rebuild it in the ATF Test Designer** (or resolve the step-config sys_ids on import),
> then run it. This is the test *specification*, made as close to importable as a repo can.

## What makes it runnable without Infoblox: `test_mode`

The provisioning Flow calls out to Infoblox (allocate IP, register DNS) and runs the
validation gate on a MID Server — none of which exist in a sub-prod test instance. So the
Script Includes honor a property:

```
x_infoblox_ddi.test_mode = 'true'
```

In test mode ([`../script-includes/InfobloxDDIClient.js`](../script-includes/InfobloxDDIClient.js),
[`InfobloxDDIGate.js`](../script-includes/InfobloxDDIGate.js)) the calls return
**deterministic canned values** instead of hitting Infoblox/the MID Server:

| Call | test_mode result |
|---|---|
| `nextAvailableIp(...)` | `x_infoblox_ddi.test_ip` (default `10.10.8.12`) |
| `createHostRecord(...)` | `record:host/TEST:<fqdn>` |
| `deleteObject(...)` | `true` |
| `InfobloxDDIGate.runGate(...)` | `{ overall: 'pass', … }` — or `overall: 'fail'` when `x_infoblox_ddi.test_force_gate_fail = 'true'` (drives the negative gate-fail test) |

So the Flow runs its full shape — approval, allocate, register, gate **pass**, close — with
no live dependency. **Never enable `test_mode` in production.**

## The scenario (steps 1–9)

1. **Impersonate the requester** (a non-admin test user) — so separation-of-duties is real.
2. **Open** the "Request a DDI-backed subnet" catalog item.
3. **Set the variables** to the Azure exemplar values (mirrors
   [`../../azure-alz-automation/terraform/terraform.tfvars.example`](../../azure-alz-automation/terraform/terraform.tfvars.example)).
4. **Submit** (Order Now) — capture the generated RITM.
5. **Impersonate the approver** (a *different* user) — the SoD gate.
6. **Approve** the pending approval (asserts requester ≠ approver first).
7. **Assert the Flow ran** — the allocated IP (`test_ip`) and a gate **pass** appear in the
   request's work notes.
8. **Assert the CMDB CI** *(optional)* — a `cmdb_ci_ip_network` for `10.10.8.0/27`. The
   Service Graph import does not run in test_mode, so seed a CI fixture or skip this one.
9. **Assert closed complete** — the RITM reaches state 3.

ATF rolls back everything the test created on completion.

## Prerequisites to run it

- The scoped app imported and the catalog item / Flow built (see the
  [build playbook](../PLAYBOOK-servicenow-led-build.md)).
- Two test users (requester + approver), the approver in the network/DDI group.
- `x_infoblox_ddi.test_mode = 'true'` on the sub-prod instance.
- `sn_atf.runner.enabled = true` (ATF is off by default; never enable on production).

## Caveats (honest)

- **Async Flow.** The provisioning Flow is asynchronous; step 7 asserts the *recorded*
  results. In a real build, either wait for the Flow (an ATF wait/retry on the RITM stage)
  or assert on the completed context — the README's step notes call this out.
- **Negative tests included** (gate-fail, SaaS-boundary, self-approve — see the table above).
  They assert the *controls*, not just the happy path. Like the happy path, they are starter
  skeletons: the step configs are rebuilt in the ATF Designer, and the SaaS-boundary test
  assumes the Flow implements the early boundary guard.
- Still a **starter**: it proves the shape and the assertions; a green run on a real
  sub-prod instance is the evidence to capture in
  [`../../azure-alz-automation/GOLD-EXEMPLAR.md`](../../azure-alz-automation/GOLD-EXEMPLAR.md).

---

*See also:* [`../README.md`](../README.md) ·
[`../PLAYBOOK-servicenow-led-build.md`](../PLAYBOOK-servicenow-led-build.md) ·
[`../../07-servicenow-orchestration.md`](../../07-servicenow-orchestration.md)
