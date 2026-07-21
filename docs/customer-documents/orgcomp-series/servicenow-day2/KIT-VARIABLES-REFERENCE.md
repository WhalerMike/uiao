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
  origin — MACD-R clause 2.
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
| `x_fed_day2_ops.sam_base_url` | `https://<sam-tenant>.api.identitynow.com` (or on-prem IGA base URL) | SAM/IGA API base for correlation callbacks and status | AC-2 |
| `x_fed_day2_ops.sam_source_id` | SAM source/correlation id for the Entra source | Ties a SAM request back to the Entra object it governs | AC-2 |
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
| `x_fed_day2_ops.sam` | `x_fed_day2_ops.sam_base_url` | OAuth2 client-credentials or PAT | ServiceNow ↔ SAM correlation/status API |

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

> **Canon status.** The SailPoint slot in the adapter registry today is
> `sailpoint-nerm` (Non-Employee Risk Management), reserved as a FedRAMP-Moderate
> commercial-exception carve-out (ADR-059). The **SAM (IGA) access-governance
> integration** below is documented in the Help Desk operations guide but is a
> *distinct* SailPoint surface; activating it as a conformance adapter needs its
> own slot and ADR (an ISC/IGA boundary-expansion decision). Treat the variable
> names below as the integration contract; hold the canon designation for the
> follow-up ADR.

### 4a. SAM API connection (behind `x_fed_day2_ops.sam`)

| Variable | Format / example | Where stored | Purpose |
|---|---|---|---|
| `sam_base_url` | `https://<sam-tenant>.api.identitynow.com` (or on-prem IGA URL) | `sam_base_url` property | SAM API base |
| `sam_client_id` | client id / PAT id | Credential record | ServiceNow ↔ SAM auth |
| `sam_client_secret` | secret / PAT secret | ServiceNow Credential (never in script) | ServiceNow ↔ SAM auth |
| `sam_token_url` | `<sam_base_url>/oauth/token` | Alias/endpoint | OAuth2 token endpoint |
| `sam_api_version` | e.g. `v3` | Alias | Pinned SAM API version |

### 4b. Correlation + approval mapping

| Variable | Format / example | Purpose | Control |
|---|---|---|---|
| `sam_source_id` | SAM source id for the Entra source | Correlate a SAM identity/request to the Entra object | AC-2 |
| `sam_access_profile_id(s)` | id(s) | The access profile(s) a request grants — maps to Entra group(s)/app role(s) | AC-6 |
| `sam_request_correlation_key` | RITM number ↔ SAM request id | Ties the ServiceNow RITM to the SAM request end to end (evidence lineage) | AU-2 |
| approval authority map | IGO → Level 1; App Owner → Level 3; Dept Owner → Level 4 | The SAM approval chain depth by Risk Tier | AC-2, AC-5 |
| `sam_event_channel` | webhook URL or scheduled pull config | How a SAM-approved request fires the ServiceNow RITM | AC-2 |

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
