# Day-2 Automation Kit — Implementation Guide

> Step-by-step stand-up of the ServiceNow ↔ Entra/Azure ↔ SailPoint SAM
> automation kit, in the order that keeps you fail-closed at every stage: nothing
> can actuate the estate until the safety machinery is in place. Build in
> **sub-production with `test_mode` on**, prove the flow and the fail-closed
> behavior against the ATF suite, then promote. Every value you set is defined in
> the [Variables Reference](./KIT-VARIABLES-REFERENCE.md); every script is
> described in the [Scripts Manifest](./KIT-SCRIPTS.md).

**Date Code:** 2026-07-21 16:30 ET · **Scope:** FedRAMP Moderate / GCC Moderate ·
**Audience:** ServiceNow platform admin + Entra/Azure admin + SAM (IdentityIQ) admin

## Prerequisites

- A ServiceNow **sub-production** instance you can import the scoped app into.
- An in-boundary **MID Server** reachable from that instance.
- Entra tenant admin able to create app registrations, a Privileged Access Group,
  and PIM policy.
- Azure subscription owner able to define a custom RBAC role.
- SailPoint **IdentityIQ** admin able to configure the ServiceNow SDIM and an API
  client (or, for the secondary path, an ISC admin).
- The scoped app `x_fed_day2_ops` and its Script Includes imported (this kit's
  four new scripts included).

## Phase 0 — Import and confirm the app is inert

1. Import the `x_fed_day2_ops` update set (or the repo's `update-set/` build).
2. Set `x_fed_day2_ops.test_mode = true`. **Confirm it before anything else** —
   every client returns canned values in this mode, so nothing you do next can
   touch a live tenant by accident.
3. Verify the four new Script Includes resolve: `PimActivationClient`,
   `AzureArmClient`, `SamCorrelationClient`, `MacdrOrchestrator`.

> **Checkpoint 0.** In a background script, `new x_fed_day2_ops.MacdrOrchestrator()`
> constructs without error. You are safe to proceed — nothing is wired to an
> estate yet.

## Phase 1 — Entra ID: the Graph app registration (identity plane)

1. Create an app registration for the kit. Record `tenant_id` and `client_id`
   (Variables Reference §2).
2. Add a **client certificate** (preferred over a secret); keep the private key
   for the MID Server only.
3. Grant **only** the least-privilege application Graph permissions for the
   catalog items you will enable (Variables Reference §2a) — never
   `Directory.ReadWrite.All`. Admin-consent them.
4. In ServiceNow, create the Connection & Credential alias `x_fed_day2_ops.graph`
   pointing at `https://graph.microsoft.com`, using the certificate credential,
   and bind it to the MID Server.
5. Set `x_fed_day2_ops.mid_server`, `x_fed_day2_ops.graph_version` (`v1.0`),
   `x_fed_day2_ops.boundary` (`gcc-moderate`).

> **Checkpoint 1.** With `test_mode = false` *temporarily*, run a read-only Graph
> call through `EntraHelpdeskClient._graph('GET','/organization',null)` — expect a
> 2xx from your tenant, routed via the MID. Set `test_mode = true` again.

## Phase 2 — Azure ARM: the resource plane

1. Create a **least-privilege custom RBAC role** (only the resource actions the
   enabled items need — never Owner/Contributor at subscription scope).
2. Assign it to the kit's ARM principal (managed identity or the app registration)
   at the narrowest scope that works.
3. Create the alias `x_fed_day2_ops.arm` → `https://management.azure.com`, bound
   to the MID Server.
4. Set `x_fed_day2_ops.arm_subscription` and `x_fed_day2_ops.arm_version`
   (`2022-04-01`).

> **Checkpoint 2.** `AzureArmClient.getResource('/subscriptions/<sub>')` returns a
> 2xx read via the MID.

## Phase 3 — PIM for Groups: just-in-time elevation

1. Create the helpdesk **Privileged Access Group (PAG)** and make it PIM-eligible.
   Record its object id.
2. Configure the PIM policy on the PAG (Variables Reference §3b): time-box
   (`pim_activation_max_minutes`), **require approval**, **require MFA**, **require
   justification**.
3. Set `x_fed_day2_ops.pag_object_id` and `x_fed_day2_ops.pim_activation_max_minutes`.
4. Make the operator identities *eligible* (not active) members of the PAG. No
   standing membership.

> **Checkpoint 3.** With `test_mode = true`, `PimActivationClient.activate(<id>,'test')`
> returns an activation id. With it briefly `false`, a real `activate` produces a
> PIM request you can see in the Entra PIM audit — and `MacdrOrchestrator` refuses
> to actuate if it comes back without an id.

## Phase 4 — SAM (SailPoint IdentityIQ): the decision origin, IIQ-push

**Primary path — IdentityIQ (on-prem, inside the boundary).**

1. Set `x_fed_day2_ops.sam_flavor = identityiq`, `x_fed_day2_ops.sam_base_url =
   https://<iiq-host>/identityiq`, and `x_fed_day2_ops.sam_source_id` to the IIQ
   **Application** name for the Entra connector.
2. In IIQ, create a **least-privilege API client / service account** (SCIM + LCM
   scope only — never `spadmin`). Create the ServiceNow alias `x_fed_day2_ops.sam`
   with its credential, bound to the MID (the callback path is intra-boundary but
   keeps the single audited egress discipline).
3. In ServiceNow, create the **Scripted REST API** `x_fed_day2_ops/sam`, resource
   `POST /ritm`, script = `scripted-rest/sam_inbound_ritm.js`. Restrict its ACL to
   a new role `x_fed_day2_ops.sam_inbound`; grant that role **only** to the IIQ
   integration user.
4. Configure the IIQ **ServiceNow Service Desk Integration Module (SDIM)** to
   **push** an approved access request to `POST /api/x_fed_day2_ops/sam/ritm`, with
   the field map in the endpoint's header comment (`sam_request_id`, `access_item`,
   `requested_for`, `approval_authority`, `risk_tier`, `justification`). Set the
   SDIM to write the returned RITM number back onto the IIQ `IdentityRequest`
   (`externalTicketId`) so the correlation is bidirectional.

**Secondary path — ISC (SaaS).** Set `sam_flavor = isc`, `sam_base_url =
https://<tenant>.api.identitynow.com`, use a PAT-based credential, and fire the
RITM from an ISC event trigger/webhook to the same endpoint.

> **Checkpoint 4.** POST a **sample** IIQ payload to the endpoint (still
> `test_mode = true`): a well-formed body returns a created RITM + lineage record;
> a body missing `sam_request_id` returns **400**; a caller without the
> `sam_inbound` role returns **403**; an unresolved `requested_for` returns **422**.
> The fail-closed contract is proven before any live push.

## Phase 5 — The Governed Day-2 Request Flow

1. Confirm the "Governed Day-2 Request" Flow (from `flow/flow-blueprint.md`) is
   present, and that its actuation step calls
   `MacdrOrchestrator.run(request, actuate, verifyArgs)` — passing the requester,
   approver, control/KSI, and verb from the catalog variables.
2. Confirm the catalog items and the `variable-set-helpdesk-identity` are loaded,
   and that the approver field enforces **requester ≠ approver**.
3. For privileged items, confirm the Flow routes through
   `PimActivationClient.activate` before actuation.

> **Checkpoint 5.** Submit one catalog request end to end in `test_mode`. The
> orchestrator trail shows all five clauses (`authorize → elevate → actuate →
> verify → closed`) and writes one evidence record.

## Phase 6 — Prove fail-closed, then promote

1. Run the **ATF suites** in `atf/` — the happy path plus every negative
   (self-approve, standing-privilege, unreconciled target, verify-wrong-state,
   SoD-indeterminate, verify-read-failure). All must pass with `test_mode = true`.
2. Run the repo gates for the kit directory:
   `python check_actuator_coverage.py`, `python check_l3_ceiling.py`.
3. **Promotion checklist — do not skip:**
   - [ ] `x_fed_day2_ops.test_mode = false` in production.
   - [ ] Every alias (`graph`, `arm`, `sam`) uses a production credential bound to
         the in-boundary MID.
   - [ ] The Graph app holds only the least-privilege scopes actually used.
   - [ ] The ARM principal holds only the custom RBAC role.
   - [ ] Operators are PIM-*eligible*, never standing members of the PAG.
   - [ ] The `sam_inbound` role is held only by the IIQ integration user.
   - [ ] A live IIQ-push test creates a correctly correlated RITM.
4. Turn on the scheduled read-only probes (morning check, log collection) and
   confirm they emit to the evidence table and feed KSI-MLA.

> **Checkpoint 6 (production readiness).** One real low-tier task (a password
> reset) and one SAM-originated Tier-2 task complete end to end, each producing a
> closure record carrying the PIM activation id and the verify verdict, and each
> appearing in the Vol VII Book 04 attestation stream.

## Rollback

Set `x_fed_day2_ops.test_mode = true` — every client immediately stops touching
the estate and returns canned values. Disable the Scripted REST API to stop
inbound SAM pushes. Neither action loses evidence already written.

## Cross-references

- `KIT-VARIABLES-REFERENCE.md` — every value referenced above.
- `KIT-SCRIPTS.md` — what each script does and how they compose.
- `KIT-USAGE-OPERATOR.md` — running the catalog tasks day to day.
- `KIT-USAGE-SAM-INTEGRATION.md` — operating and troubleshooting the IIQ-push integration.
- `atf/README.md` — the test suites Phase 6 runs.
