# Day-2 Automation Kit — START HERE

> This kit provisions identities **cloud-native from the OPM-HRIT SSOT**, actuated
> directly in Entra Graph / Azure ARM (`x_fed_day2_ops.hybrid_mode = false`).

> The implementer's on-ramp. Read this first: it names the order of the steps,
> points at the document that details each one, states what these scripts are (and
> are not), gives you the debug levers, and sets the one rule that keeps you
> safe — **install into a sandbox / test environment first, never production.**

**Date Code:** 2026-07-22 12:00 ET · **Scope:** FedRAMP Moderate / GCC Moderate ·
**Audience:** the implementer standing this up for the first time

## 0. The one rule: sandbox first

**Your first install target is a non-production environment, with
`x_fed_day2_ops.test_mode = true` throughout.** Specifically:

- a **ServiceNow sub-production / developer instance** (not prod),
- a **test/dev Entra tenant** and **test Azure subscription**,
- a **test SailPoint IdentityIQ** (or an ISC sandbox), and
- an **in-boundary MID Server** that reaches only those test systems.

In `test_mode`, every client returns deterministic canned values and touches no
live estate — so you can build the whole app, run the ATF suite, and prove the
flow **before a single real credential is wired.** Only after the ATF suite is
green and the promotion checklist is satisfied do you set `test_mode = false` and
point the aliases at production. Do not skip this.

## 1. What this kit is (and is not)

**Is:** the deployable source + the complete specification for a governed
ServiceNow day-2 operations app (`x_fed_day2_ops`) that runs everyday identity
tasks under the MACD-R lifecycle — SSOT-originated, authorized, least-privilege /
just-in-time elevated, verified, and evidence-emitting — integrated with Entra/
Azure (Graph + ARM via the in-boundary MID) and SailPoint SAM (IdentityIQ push).

**Is not:** a one-click importable product. The Script Includes, the scripted REST
resource, the control maps, the ATF suites, one variable-set exemplar, and the
Flow blueprint ship as source. The **platform records** (tables, ACLs, roles, the
50-item catalog, the Flow, the update set) are **built on your instance from the
Build Specification and exported** — because a ServiceNow update-set / Flow / ATF
XML is a machine-serialized export, not authorable text. See the disclaimers in §4.

## 2. The install path (do these in order)

Each step names the document that details it. Build in the sandbox with
`test_mode = true`.

| # | Step | Read |
|---|---|---|
| 1 | Understand the shape: scoped app, the five MACD-R clauses, the closure-provenance rules | `README.md` |
| 2 | Learn the config contract — every property, alias, credential, and least-privilege scope, per tool | **`KIT-VARIABLES-REFERENCE`** |
| 3 | Build the platform records — tables (exact columns), roles, ACLs, the Scripted REST API, the 50-item catalog, the Flow, and the update-set export order | **`KIT-BUILD-SPEC`** |
| 4 | Stand it up phase by phase (import inert → Graph → ARM → PIM/PAG → SAM push → Flow → prove ATF → promote), with a checkpoint after each phase | **`KIT-IMPLEMENTATION-GUIDE`** |
| 5 | Know what each script does and how they compose | `KIT-SCRIPTS` |
| 6 | Operate it: the day-to-day catalog tasks | `KIT-USAGE-OPERATOR` |
| 7 | Operate the SAM (IdentityIQ-push) integration | `KIT-USAGE-SAM-INTEGRATION` |
| 8 | Plan expansion beyond the foundation lanes | `Kit Expansion Roadmap` |

**Shortest path to a working demo:** README → Variables Reference → Build
Specification → Implementation Guide Phases 0–5, all in `test_mode`. That gets you
one catalog request running end to end through all five MACD-R clauses with no
live estate. Then wire one real credential and do Implementation Guide Phase 6.

## 3. Prerequisites (have these before Step 3)

- ServiceNow **sub-prod** instance + an in-boundary **MID Server**.
- Entra tenant admin (app registrations, a Privileged Access Group, PIM policy).
- Azure subscription owner (a least-privilege custom RBAC role).
- SailPoint **IdentityIQ** admin (the ServiceNow SDIM + a least-privilege API
  client) — or an ISC admin for the secondary path.
- Python 3.12 to run the build-time gates (`check_actuator_coverage.py`,
  `check_l3_ceiling.py`, `catalog/contract_check.py`).

## 4. Disclaimers — read before you wire anything live

1. **Starter skeletons.** Every Script Include carries a header disclaimer:
   *"STARTER SKELETON — pin the API version and validate scopes against your
   tenant before production."* Pin `graph_version` / `arm_version` / the SAM API
   version, and validate the Graph scopes, the RBAC role, and the PIM-for-Groups
   API shape against **your** tenant before you rely on them.
2. **`test_mode` is sandbox-only.** In `test_mode = true` clients return canned
   values and touch nothing. **Production must have `test_mode = false`** — the
   ATF negative suite asserts this. Never enable `test_mode` in production, and
   never trust a "success" seen while it is on.
3. **No secrets in the scripts.** Nothing here contains a credential. Secrets live
   in ServiceNow Credential records, the MID Server, Azure Key Vault, or the SAM
   secret store, and are named by alias. Do not add a secret to a script or a
   catalog variable — `contract_check.py` fails the build if a secret is a form
   field.
4. **Least privilege is your responsibility to enforce.** Grant only the Graph
   scopes the enabled items use (never `Directory.ReadWrite.All`), only the custom
   RBAC role (never Owner/Contributor at subscription scope), and make operators
   PIM-*eligible*, never standing members of the PAG.
5. **Actuation ceiling (L3).** By default a human approves before anything writes
   to the estate (ADR-092). `check_l3_ceiling.py` fails the build if an item
   claims autonomous write without a Governance-Plane decision behind it. Do not
   flip an item to `approval: automated` for a writing operation without that
   decision.
6. **SAM/IGA canon status.** The SAM (SailPoint IGA) integration is a distinct
   surface from the reserved `sailpoint-nerm` slot (ADR-059); activating it as a
   conformance adapter needs its own slot and ADR. Treat the variable and push
   contracts as the integration spec; the canon designation is a follow-up.
7. **Not legal/authorization advice.** Control mappings (NIST 800-53, FedRAMP
   Moderate, KSIs) are the series' engineering interpretation. Validate closure
   claims with your ISSO and your independent assessor before relying on them for
   an authorization decision.
8. **No warranty.** This is reference implementation material. Test it in a
   sandbox, review it, and own the result before production use.

## 5. Debug options

When something does not behave, in rough order of use:

- **`test_mode`** — set `x_fed_day2_ops.test_mode = true` to isolate whether a
  problem is in the flow logic (still fails in test_mode) or in a live
  integration (only fails with test_mode off).
- **Scoped logs** — every client logs to the system log with a
  `[x_fed_day2_ops.<ClientName>]` prefix (e.g.
  `[x_fed_day2_ops.EntraHelpdeskClient]`). Filter the system log on
  `x_fed_day2_ops` to see exactly which client and call failed.
- **Fail-closed reason strings** — a stopped request returns the *clause* it
  stopped at (`authorize` / `elevate` / `actuate` / `verify`) and a reason
  string. Read it; it names the check that refused (SoD, missing expiry, no PIM
  activation id, a verify re-read that disagreed). See `KIT-USAGE-OPERATOR.md`
  "When a request stops."
- **The evidence record** — every task, *including a refused one*, writes an
  evidence row with the full MACD-R `trail` (JSON). Open the row to see the
  clause-by-clause result.
- **The ATF negative suites** — `atf/atf-negative-*.xml` are the fastest way to
  confirm the safety machinery still refuses the right things (self-approve,
  standing-privilege, unreconciled target, verify-wrong-state, etc.).
- **The build-time gates** — run `python check_actuator_coverage.py` (every map
  item names a real method or a declared gap), `python check_l3_ceiling.py` (no
  undeclared autonomous write), and `python catalog/contract_check.py` (the form
  supplies what the client + gate require). These catch drift before a request
  ever runs.
- **The Implementation Guide checkpoints** — each phase ends with a concrete
  checkpoint (e.g. a read-only Graph call returns 2xx via the MID). Work the
  checkpoints in order; the first one that fails localizes the problem.

### Common gotchas

- **MID Server** — the alias must be bound to the in-boundary MID, and the MID
  must reach the target (Graph/ARM/SAM). A hanging call is usually MID reachability
  or a missing MID binding on the alias.
- **Certificate rotation** — the Graph app's client certificate lives on the MID;
  a rotation that updates Entra but not the MID (or vice versa) fails auth.
- **PIM activation** — if `activate` returns no activation id, elevation was
  denied or the PAG is misconfigured; the orchestrator then refuses to actuate.
  That is correct — do not work around it.
- **GCC Moderate hosts** — this kit targets `graph.microsoft.com` /
  `management.azure.com` (commercial, which serves GCC Moderate). GCC High / DoD
  use different hosts and are out of scope here.
- **Graph throttling** — bulk operations can hit Graph rate limits; honor
  `Retry-After` rather than hammering.

## 6. Where to go next

- Stuck on the integration → `KIT-USAGE-SAM-INTEGRATION.md` troubleshooting table.
- Stuck on a task → `KIT-USAGE-OPERATOR.md` "When a request stops."
- Building the platform records → `KIT-BUILD-SPEC.md`.
- The doctrine behind it all → Vol 0 Book 00 (MACD-R + SSOT Registry), Vol IX
  Books 01 / 05 / 06.
