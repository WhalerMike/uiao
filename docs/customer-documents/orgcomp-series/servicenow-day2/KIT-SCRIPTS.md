# Day-2 Automation Kit — Scripts Manifest

> The scripts that turn the [Operator Runbook](../OrgComp_Operator_Runbook_Day2_Compliant.qmd)
> into a governed, scripted ServiceNow flow — ServiceNow ↔ Entra/Azure, and
> ServiceNow ↔ SailPoint SAM (IdentityIQ primary, ISC secondary). Every script
> reads its configuration from the [Variables Reference](./KIT-VARIABLES-REFERENCE.md);
> none holds a secret. This manifest is the map; the step-by-step install lives in
> the Implementation Guide and per-task use in the Usage docs.

**Date Code:** 2026-07-21 16:05 ET · **Scope:** FedRAMP Moderate / GCC Moderate

## What each script is, and which MACD-R clause it serves

| Script | Kind | MACD-R clause | Reads |
|---|---|---|---|
| `scripted-rest/sam_inbound_ritm.js` | Scripted REST resource | 1 Origin + 2 Authorize | the `sam_inbound` role; `sam_flavor`; the integration table |
| `script-includes/SamCorrelationClient.js` | Script Include | 1 Origin (correlate) + 5 Evidence | `sam` alias; `sam_flavor`; `sam_base_url`; `sam_source_id` |
| `script-includes/EntraHelpdeskGate.js` *(existing)* | Script Include | 2 Authorize + 4 Verify | `graph` alias |
| `script-includes/PimActivationClient.js` | Script Include | 3 Elevate (JIT) | `pag_object_id`; `pim_activation_max_minutes` |
| `script-includes/EntraHelpdeskClient.js` *(existing)* | Script Include | 4 Actuate (identity) | `graph` alias; `graph_version`; `mid_server` |
| `script-includes/AzureArmClient.js` | Script Include | 4 Actuate (resource) | `arm` alias; `arm_subscription`; `arm_version`; `mid_server` |
| `script-includes/MacdrOrchestrator.js` | Script Include | 1→5 (threads all) | `tbl_evidence`; composes the clients above |

Existing lane actuators (`Day2NativeActuator`, `EntraAppRegClient`,
`EntraSaasClient`, `AcmeCredentialClient`, `TeamsTelephonyClient`,
`TerraformCpgClient`) are unchanged; the four new scripts add the **resource
plane (ARM)**, the **JIT elevation (PIM/PAG)**, the **SAM decision origin**, and
the **five-clause orchestration** that the identity-plane client already had no
home for.

## The end-to-end flow (IIQ-push)

```
 IdentityIQ LCM approves a Tier-1/2 access request
        │  IIQ SDIM PUSHes  →  POST /api/x_fed_day2_ops/sam/ritm
        ▼
 sam_inbound_ritm.js         clause 1–2  create+correlate the RITM (fail closed on
   → SamCorrelationClient                 auth, missing keys, unresolved identity);
       .validateInboundPush               write SAM↔RITM↔subject lineage (AU-2)
       .recordLineage
        ▼
 "Governed Day-2 Request" Flow  calls  MacdrOrchestrator.run(request, actuate, verifyArgs)
        │
        ├─ clause 2  EntraHelpdeskGate.preflight     SoD + least-privilege expiry (fail closed)
        ├─ clause 3  PimActivationClient.activate    JIT PAG; NO activation id → NO actuation
        ├─ clause 4  actuate()                       EntraHelpdeskClient / AzureArmClient (MID→Graph/ARM)
        │            EntraHelpdeskGate.verify        re-read state; a 2xx is not closure
        └─ clause 5  MacdrOrchestrator._writeEvidence request+approver+PIM id+result+verdict (CM-3/AU-2)
        ▼
 Vol VII Book 04 attestation reads the closure stream → OSCAL / KSI evidence
```

For a **lower-tier (A0/A1) task** with no SAM decision (a password reset, an
account unlock) the request is raised directly in the catalog and enters at the
Flow step — clauses 2–5 are identical; only the origin differs.

## Task → script mapping (the eight runbook tasks)

| Runbook task | Origin | Actuator method | Verify |
|---|---|---|---|
| Password reset | catalog / self-service | `EntraHelpdeskClient.resetPassword` | gate.verify (credential state) |
| MFA reset | catalog (servicedesk+verify) | `EntraHelpdeskClient.resetMfaMethod` | gate.verify (method removed) |
| Admin consent | Lane F (Book 05) | `Day2NativeActuator.recordAuthorizationVerdict` → `EntraSaasClient` | verdict + endpoint decl |
| Tenant account (joiner) | HR event | `EntraHelpdeskClient.createUser` | gate.verify `createUser` |
| Leaver | HR event | `EntraHelpdeskClient.disableUser` | gate.verify `disableUser` |
| Group / RBAC grant | SAM decision (Tier-1/2) | `EntraHelpdeskClient.addGroupMember` / `AzureArmClient.assignRbacRole` | gate.verify / `getRbacRole` |
| Scripted/bulk change | catalog (typed params) | pre-approved Script Include (never free-form) | gate.verify |
| Morning check / logs | scheduled probe | read-only clients → evidence table | n/a (read) |

Every privileged row runs through `PimActivationClient.activate` first (clause 3)
and `MacdrOrchestrator` stamps the activation id into the closure record.

## Fail-closed guarantees (asserted by the ATF negative suite)

- **No SoD** — `preflight` refuses requester == approver, or either missing.
- **No standing privilege** — `activate` refuses to return success without a PIM
  activation id; the orchestrator refuses to actuate without one.
- **No unverified closure** — `verify` re-reads; a 2xx write is not closure.
- **No un-correlated SAM push** — the inbound endpoint refuses a payload missing
  the SAM request id / access item / requested-for / approval authority, or an
  identity that does not resolve.
- **No secret in code** — every transport names an alias (`graph`, `arm`, `sam`).
- **test_mode is sub-prod only** — clients return canned values; production must
  set `x_fed_day2_ops.test_mode = false`.

## New platform config these scripts require

Beyond the [Variables Reference](./KIT-VARIABLES-REFERENCE.md):

1. **Scripted REST API** `x_fed_day2_ops/sam`, resource `POST /ritm`, script =
   `scripted-rest/sam_inbound_ritm.js`; ACL restricted to role
   `x_fed_day2_ops.sam_inbound` (the IIQ integration user).
2. **Connection & Credential aliases** `x_fed_day2_ops.arm` and
   `x_fed_day2_ops.sam` (the `graph` alias already exists).
3. **System properties** `arm_subscription`, `arm_version`, `pag_object_id`,
   `pim_activation_max_minutes`, `sam_flavor`, `sam_base_url`, `sam_source_id`.
4. **PIM for Groups** configured on the helpdesk PAG (eligible role, approval,
   MFA-on-activation, time-box) — the kit activates it; PIM policy is set in Entra.

## Cross-references

- `KIT-VARIABLES-REFERENCE.md` — the configuration contract every script reads.
- `KIT-IMPLEMENTATION-GUIDE.md` — step-by-step stand-up (sub-prod → ATF → promote).
- `KIT-USAGE-OPERATOR.md` — running the catalog tasks day to day.
- `KIT-USAGE-SAM-INTEGRATION.md` — operating the IIQ-push integration.
- `README.md` — the scoped-app overview and the closure-provenance rules.
- `../OrgComp_Operator_Runbook_Day2_Compliant.qmd` — the eight tasks these scripts automate.
- `atf/` — the happy-path + negative ATF suites the fail-closed guarantees are asserted by.
- Vol IX Book 01 / 05 / 06; Vol 0 Book 00 (MACD-R + SSOT Registry).
