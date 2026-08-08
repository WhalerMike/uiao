# Day-2 Automation Kit — Variables Reference

> The configuration contract every script in this kit compiles against. One
> row per variable, per tool, with where it is stored, its format, its
> purpose, and the control it serves. **De-branded**: substitute your own
> environment's identifiers where a value shows `<...>`. Nothing here is a
> secret — secrets live in the platforms named below (ServiceNow Credential
> records, the MID Server, Azure Key Vault, the SAM secret store) and are
> referenced by alias, never written into scripts or this document.

**Date Code:** 2026-07-21 15:40 ET · **Scope:** FedRAMP Moderate / Microsoft GCC Moderate

## The integration chain these variables wire together

```
 SailPoint SAM (IGA)  ──approval + RITM──▶  ServiceNow ITSM  ──MID/Graph──▶  Entra ID
 (Systems Access Mgmt)                      (x_fed_day2_ops)  ──MID/ARM────▶  Azure + PIM/PAG
      the access DECISION                    the WORKFLOW          the ESTATE actuated
      and its authorization                  and its evidence      just-in-time, least privilege
```

- **SAM** originates the higher-tier access decision (Tier 1/2, privileged) and
  fires a ServiceNow request item (RITM). It is the authoritative approval
  origin — MACD-R clause 2. **Primary implementation: SailPoint IdentityIQ**
  (on-prem, inside the boundary; LCM originates the request, its ServiceNow SDIM
  raises the RITM). **Secondary: Identity Security Cloud (SaaS)** over the same
  contract.
- **ServiceNow** (`x_fed_day2_ops` scoped app) receives the RITM (or raises the
  lower-tier request itself), routes the approval the control requires, actuates
  through the in-boundary MID Server, and writes the evidence — MACD-R clauses
  1, 3, 4, 5.
- **Entra ID / Azure** are the estate actuated, never an origination surface.
- **Microsoft PIM / PAG** supplies the just-in-time scoped elevation — MACD-R
  clause 3. No standing admin.

Every variable below belongs to exactly one of these tools. A script that needs
a value it cannot resolve from these named locations must **fail closed**, never
fall back to a default credential or a standing admin.

---

## 1. ServiceNow — `x_fed_day2_ops` scoped app

### 1a. System properties (`sys_properties`, scope `x_fed_day2_ops`)

| Property | Format / example | Purpose | Control |
|---|---|---|---|
| `x_fed_day2_ops.mid_server` | MID server name, `<mid-inboundary-01>` | In-boundary MID that executes every Graph/ARM call; execution never leaves the ATO boundary | SC-7 |
| `x_fed_day2_ops.boundary` | `gcc-moderate` | Which boundary the evidence records were produced under; also selects the correct Graph/ARM host | CA-2 |
| `x_fed_day2_ops.graph_version` | `v1.0` | Pinned Microsoft Graph API version | CM-2 |
| `x_fed_day2_ops.test_mode` | `true` \| `false` | When `true`, clients return deterministic canned values so ATF suites run in sub-prod with **no** live connectivity. **Never `true` in production.** | CM-3 |
| `x_fed_day2_ops.tbl_evidence` | scoped table name, `x_fed_day2_ops_evidence` | Where closure/evidence records are written | AU-2 |
| `x_fed_day2_ops.tbl_integration` | scoped table name, `x_fed_day2_ops_integration` | Integration/correlation records (RITM ↔ estate object ↔ SAM request) | AU-2 |
| `x_fed_day2_ops.arm_subscription` | GUID, `<azure-subscription-id>` | Default Azure subscription for ARM actuation | CM-8 |
| `x_fed_day2_ops.arm_version` | `2022-04-01` | Pinned ARM API version | CM-2 |
| `x_fed_day2_ops.sam_flavor` | `identityiq` (primary) \| `isc` (secondary) | Selects the SAM API dialect the `sam` client speaks | CM-2 |
| `x_fed_day2_ops.sam_base_url` | IIQ: `https://<iiq-host>/identityiq` · ISC: `https://<tenant>.api.identitynow.com` | SAM/IGA API base for correlation callbacks and status | AC-2 |
| `x_fed_day2_ops.sam_source_id` | IIQ Application name/id for the Entra connector · ISC source id | Ties a SAM request back to the Entra object it governs | AC-2 |
| `x_fed_day2_ops.iiq_verify_endpoint` | IIQ (or ISC) IdentityRequest/access-request status path, or any non-empty marker your build resolves | Gates the pull-verify branch of `verifyWithSam()` — with this **and** `sam_jws_public_key` unset, the SAM inbound endpoint refuses every push (fail closed, intended default) | AC-3 |
| `x_fed_day2_ops.sam_jws_public_key` | PEM/JWK public key material | Signature key for the optional signed-push (JWS) verification mode — the alternative to pull-verify | AC-3 |
| `x_fed_day2_ops.nonprod_instances` | comma-separated instance names, `<subprod-instance-01>,<subprod-instance-02>` | The environment allowlist `Day2Env` checks before honouring `test_mode` — a `test_mode=true` instance NOT on this list is refused, not silently trusted (P0-5) | CM-3 |
| `x_fed_day2_ops.acme` | Connection & Credential alias | ACME cert-issuance client (credential lifecycle) | IA-5 |
| `x_fed_day2_ops.acme_directory` | ACME directory URL | ACME endpoint | IA-5 |
| `x_fed_day2_ops.acme_default_days` | integer, `90` | Default cert validity | IA-5 |
| `x_fed_day2_ops.cpg_endpoint` | Terraform CPG endpoint | Landing-zone provisioning (Lane D) | CM-2 |
| `x_fed_day2_ops.cpg_workspace_prefix` | string | CPG workspace naming | CM-2 |

### 1b. Connection & Credential aliases (`sys_alias` / `sys_connection`)

Aliases hold the endpoint + credential together; scripts name the alias, never the secret.

| Alias | Points at | Credential type | Purpose |
|---|---|---|---|
| `x_fed_day2_ops.graph` | `https://graph.microsoft.com` (GCC-Moderate) | OAuth2 client-credentials (certificate preferred) | All Entra Graph actuation |
| `x_fed_day2_ops.arm` | `https://management.azure.com` | OAuth2 client-credentials (managed identity or cert) | Azure ARM actuation |
| `x_fed_day2_ops.sam` | `x_fed_day2_ops.sam_base_url` | IIQ: API-Client OAuth2 or Basic (least-priv service account) · ISC: OAuth2 PAT | ServiceNow ↔ SAM correlation/status API |

### 1c. Platform objects the kit expects to exist

| Object | Example | Purpose |
|---|---|---|
| MID Server | `<mid-inboundary-01>` | In-boundary execution host (matches `mid_server` property) |
| Scoped role — operator | `x_fed_day2_ops.operator` | Who may submit catalog items |
| Scoped role — approver | `x_fed_day2_ops.approver` | Who may approve (enforced ≠ requester) |
| Catalog + variable sets | `variable-set-helpdesk-identity` | The typed request forms (the "form is the contract") |
| Flow(s) | "Governed Day-2 Request" | Intake → approve → actuate → verify → evidence |

---

## 2. Entra ID — Microsoft Graph app registration

One least-privilege app registration behind the `x_fed_day2_ops.graph` alias.
Values are configured in Entra and stored in the ServiceNow Credential record; the
kit reads them only through the alias.

| Variable | Format / example | Where stored | Purpose |
|---|---|---|---|
| `tenant_id` | GUID, `<entra-tenant-id>` | Credential record | The directory actuated |
| `client_id` | GUID, `<graph-app-registration-id>` | Credential record | The kit's service principal |
| credential | **client certificate** (preferred) or client secret | ServiceNow Credential + MID; private key on MID only | App authentication — cert over secret (IA-5) |
| `authority` | `https://login.microsoftonline.com/<tenant_id>` | Alias/endpoint | Token authority (commercial, serves GCC-Moderate) |
| `graph_host` | `graph.microsoft.com` | Alias endpoint | Graph host for the Moderate boundary |

### 2a. Least-privilege application Graph permissions (per operation)

Grant **only** the scopes the enabled catalog items use — never `Directory.ReadWrite.All`.

| Operation (catalog item) | Graph permission | Control |
|---|---|---|
| Joiner / create user | `User.ReadWrite.All` | AC-2 |
| Leaver / disable + revoke sessions | `User.ReadWrite.All`, `User.RevokeSessions.All` | AC-2 |
| Password reset | `User-PasswordProfile.ReadWrite.All` | IA-5 |
| MFA method reset | `UserAuthenticationMethod.ReadWrite.All` | IA-5 |
| Group membership | `GroupMember.ReadWrite.All` | AC-6 |
| License assignment | `User.ReadWrite.All`, `Directory.Read.All` (read SKUs) | AC-2 |
| Guest / B2B invite | `User.Invite.All` | AC-2 |
| App-role / enterprise-app group assignment | `AppRoleAssignment.ReadWrite.All` | AC-6 |
| Reconciliation / evidence reads (read-only) | `Directory.Read.All`, `AuditLog.Read.All` | AU-6 |

---

## 3. Azure — ARM + Microsoft PIM / PAG

Behind the `x_fed_day2_ops.arm` alias for resource actuation, plus the PIM/PAG
objects that supply just-in-time elevation for every privileged task.

### 3a. ARM actuation

| Variable | Format / example | Where stored | Purpose |
|---|---|---|---|
| `subscription_id` | GUID, `<azure-subscription-id>` | `arm_subscription` property | Target subscription |
| `tenant_id` | GUID (same as Entra) | Credential record | Directory |
| `arm_endpoint` | `https://management.azure.com` | `x_fed_day2_ops.arm` alias | ARM host (Moderate) |
| `arm_version` | `2022-04-01` | `arm_version` property | Pinned ARM API version |
| RBAC custom role | `<custom-role-definition-id>` | Azure RBAC | The least-privilege role the ARM principal holds — never Owner/Contributor at subscription scope |
| managed identity / SP client_id | GUID | Credential record | The ARM actuation identity |

### 3b. PIM / Privileged Access Group (just-in-time elevation — MACD-R clause 3)

| Variable | Format / example | Purpose | Control |
|---|---|---|---|
| `pag_object_id` | GUID, `<helpdesk-PAG-object-id>` | The Privileged Access Group the operator activates into | AC-6 |
| `pag_eligible_role` | e.g. `User Administrator` (scoped) | The role the PAG confers on activation | AC-6 |
| `pim_activation_max_minutes` | integer, `60` | Time-box on elevation | AC-6 |
| `pim_requires_approval` | `true` | Second-party approval on activation | AC-5 |
| `pim_approver_group` | GUID, `<PIM-approver-group>` | Who approves activation | AC-5 |
| `pim_requires_justification` | `true` | Justification captured into the activation record (evidence) | AU-2 |
| `pim_requires_mfa` | `true` | Re-auth on activation | IA-2 |

The **PIM activation id** produced at elevation is written into the task's
evidence record — it binds *who could act* to *what was done* (the MACD-R
least-privilege clause made auditable).

---

## 4. SailPoint SAM — the IGA (access decision + RITM origin)

SAM is the authoritative origin for higher-tier access (Tier 1/2, privileged) and
the approval authority chain (IGO / Application Owner / Departmental Owner). It
does not actuate the estate — it **decides and requests**; ServiceNow executes.

> **Primary: SailPoint IdentityIQ (on-prem IGA).** SAM is implemented on
> **IdentityIQ** first — an on-premises IGA that already sits **inside the ATO
> boundary** (agency data center), which is why its integration needs no MID hop
> for egress: the ServiceNow MID and the IIQ host are on the same protected
> network. IdentityIQ's Lifecycle Manager (LCM) originates the access request and
> its approval chain; its **ServiceNow Service Desk Integration Module (SDIM)**
> raises and tracks the RITM. **Secondary: Identity Security Cloud (ISC / SaaS)**
> — the same integration contract over ISC's cloud API, offered as the alternate
> `sam_flavor`. The kit's `sam` client branches on `sam_flavor`.
>
> **Canon status.** The SailPoint slot in the adapter registry today is
> `sailpoint-nerm` (Non-Employee Risk Management), reserved as a FedRAMP-Moderate
> commercial-exception carve-out (ADR-059). This **SAM/IGA access-governance
> integration** (IdentityIQ primary, ISC secondary) is a *distinct* SailPoint
> surface; activating it as a conformance adapter needs its own slot and ADR.
> Treat the variable names below as the integration contract; hold the canon
> designation for the follow-up ADR.

### 4a-P. IdentityIQ (PRIMARY) — API connection behind `x_fed_day2_ops.sam`

| Variable | Format / example | Where stored | Purpose |
|---|---|---|---|
| `sam_base_url` | `https://<iiq-host>/identityiq` | `sam_base_url` property | IIQ application base URL |
| `iiq_scim_base` | `<sam_base_url>/scim/v2` | derived | SCIM 2.0 resource API (`/Users`, `/Entitlements`, `/Roles`) |
| `iiq_rest_base` | `<sam_base_url>/rest` | derived | IIQ custom REST (LCM requests, workflows) |
| auth mode | **API Client (OAuth2 client-credentials)** preferred; Basic (least-priv service account) fallback | Credential record | ServiceNow ↔ IIQ auth (IIQ 8.x API Client) |
| `iiq_client_id` / `iiq_client_secret` | API Client id + secret | ServiceNow Credential (never in script) | OAuth2 client-credentials |
| `iiq_token_url` | `<sam_base_url>/oauth2/token` | Alias/endpoint | IIQ OAuth2 token endpoint |
| `iiq_service_account` | least-privilege IIQ identity (SCIM/LCM scope only) | IIQ | The identity the integration acts as — never `spadmin` |

### 4a-S. Identity Security Cloud (SECONDARY / SaaS) — same contract, cloud dialect

| Variable | Format / example | Where stored | Purpose |
|---|---|---|---|
| `sam_base_url` | `https://<tenant>.api.identitynow.com` | `sam_base_url` property | ISC API base |
| `isc_scim_base` | `<sam_base_url>/v2` | derived | ISC SCIM/v2 (`/Sources`, `/access-profiles`, `/roles`) |
| `isc_client_id` / `isc_client_secret` | Personal Access Token id + secret | ServiceNow Credential | OAuth2 client-credentials |
| `isc_token_url` | `<sam_base_url>/oauth/token` | Alias/endpoint | ISC OAuth2 token endpoint |
| `isc_api_version` | `v3` | Alias | Pinned ISC API version |

### 4b. Correlation + approval mapping (both flavors)

| Variable | IdentityIQ | ISC | Purpose · Control |
|---|---|---|---|
| access-request id | IIQ **IdentityRequest** id | ISC **access-request** id | The SAM-side request key · AU-2 |
| RITM correlation | `IdentityRequest.externalTicketId` ↔ RITM number (set by SDIM) | ISC request id ↔ RITM number | End-to-end lineage SAM ↔ ServiceNow ↔ estate · AU-2 |
| source / connector | `sam_source_id` = IIQ **Application** (Entra connector) name | ISC **source** id | Correlate the request to the Entra object · AC-2 |
| grantable access | IIQ **Role** / **Entitlement** (ManagedAttribute) → Entra group/app role | ISC **access profile** / **role** → Entra group/app role | What the request grants · AC-6 |
| approval authority map | IGO → Level 1 (final); App Owner → Level 3; Dept Owner → Level 4 | (same authority model) | Chain depth by Risk Tier · AC-2, AC-5 |
| `sam_event_channel` | IIQ **SDIM** raises the RITM (workflow → ServiceNow); status polled back | ISC event trigger / webhook fires the RITM | How a SAM-approved request reaches ServiceNow · AC-2 |

### 4c. Risk-tier → approval-depth (drives which chain a request travels)

| Risk Tier | Approval chain (SAM-originated) | Certification cadence |
|---|---|---|
| Tier 1 / High | Dept Owner → App Owner → **IGO (final)** | Quarterly |
| Tier 2 / Moderate | Dept Owner → App Owner | Semi-annual |
| Tier 3 / Low | Dept Owner | Semi-annual |

---

## 5. Fail-closed rules (apply to every variable above)

1. **No default credential.** A script that cannot resolve its alias/credential
   raises the request to error — it never falls back to a standing admin or an
   embedded secret.
2. **No secret in code or catalog variable.** Secrets live in ServiceNow
   Credential records, the MID Server, Key Vault, or the SAM secret store, and
   are referenced by alias. `tempPassword`-class values are MID-resolved, never a
   form field.
3. **`test_mode` is sub-prod only.** Production must have
   `x_fed_day2_ops.test_mode = false`; the ATF negative suite asserts this.
4. **Least privilege is the default.** Grant only the Graph scopes, the RBAC
   role, and the PAG the enabled items require; PIM elevation is time-boxed,
   approved, MFA-gated, and its activation id is captured as evidence.
5. **SSOT-origin or it does not validate.** A request that resolves against no
   HR record (person), no SAM access decision (privileged access), or no NHI
   registry record (service account) is an exception state, flagged — not a
   silent fulfillment.

## Cross-references

- `README.md` — the scoped-app overview and closure-provenance rules.
- `helpdesk-control-map.json`, `saas-control-map.json`, `appreg-control-map.json`
  — the per-item control bindings the scripts actuate.
- Vol IX Book 01 / Book 05 / Book 06 — the catalog, the SaaS gate, the identity
  governance layer.
- Vol 0 Book 00 — the MACD-R Lifecycle and the per-class SSOT Registry.
- The Help Desk operations guides — the SAM / ServiceNow / PIM authority model.
