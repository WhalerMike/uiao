# ServiceNow Orchestration — Azure ALZ Infoblox DDI

> **This is the Azure-specific wiring** beneath the shared
> [Chapter 7 — ServiceNow Orchestration](../../07-servicenow-orchestration.md).
> Read Chapter 7 first for the certified pieces (CPG Terraform Connector, Service
> Graph Connector for Infoblox, IntegrationHub REST, MID Server), the closed-loop
> model, and the control-family mapping. **This file does not repeat those
> concepts** — it specializes them for *this* package: it maps the Service
> Catalog form to the exact Azure module `tfvars`, defines the Flow Designer flow
> against `../terraform`, and points at the concrete Infoblox request bodies and
> the MID Server validation gate that live alongside it.

Everything here is a **labeled starter skeleton**, consistent with the rest of
`azure-alz-automation/` — it encodes the right structure and mappings, not a
certified production integration.

## Contents

- [Catalog item → tfvars mapping](#catalog-item--tfvars-mapping)
- [Flow Designer flow (Azure)](#flow-designer-flow-azure)
- [IntegrationHub REST actions](#integrationhub-rest-actions)
- [Service Graph Connector CMDB mapping](#service-graph-connector-cmdb-mapping)
- [GCC-Moderate notes](#gcc-moderate-notes)

---

## Catalog item → tfvars mapping

The Service Catalog item is the front door for **Stage 2** (this module). Each
form field maps to one canonical variable in
[`../terraform/variables.tf`](../terraform/variables.tf); the CPG Terraform
Connector renders them into the `tfvars` it plans/applies. Fields sourced from
**Stage 1 (ALZ Accelerator)** outputs should be pre-populated (reference
variables / a lookup) rather than free-typed, so requesters can't invent hub
identifiers.

**Required** = no module default; the catalog item must collect it (mark the
variable mandatory). **Defaulted** = the module has a safe default; expose it as
an optional/advanced field or omit it and let the default stand.

| Catalog form field | Module variable | Req/Default | Source / notes |
|---|---|---|---|
| Azure region | `location` | **Required** | Commercial `.com` region. No default. |
| Hub resource group | `hub_resource_group_name` | **Required** | Stage-1 output — pre-populate, don't free-type. |
| Hub VNet (resource ID) | `hub_vnet_id` | **Required** | Stage-1 output; full VNet resource ID (validated). |
| DDI subnet CIDR | `ddi_subnet_address_prefix` | **Required** | Must fit the hub VNet, no overlap (see conflict gate). |
| VM size | `vnios_vm_sku` | **Required** | Region/NIOS-version dependent; pick-list from approved SKUs. |
| Marketplace image | `vnios_image` | **Required** | publisher/offer/sku/version object; pick-list, don't hard-code. |
| Key Vault (resource ID) | `key_vault_id` | **Required** | Existing KV holding all module secrets (validated). |
| Mgmt source CIDRs | `mgmt_source_cidrs` | **Required** | Non-empty, **never `0.0.0.0/0`** (form-validate). |
| DNS client CIDRs | `dns_client_cidrs` | **Required** | Spoke/on-prem ranges permitted to query DNS. |
| Resource name prefix | `name_prefix` | Default `ddi` | 2–11 chars, lowercase; advanced field. |
| Environment | `environment` | Default `prod` | `dev`/`test`/`prod` choice → drives tags/sizing + SoD tier. |
| Deployment model | `deployment_model` | Default `grid` | `grid` (in-boundary) \| `universal_ddi` (SaaS). |
| Acknowledge SaaS boundary | `acknowledge_saas_boundary` | Default `false` | **Must be `true`** to allow `universal_ddi`; drives an extra approval. |
| Compliance profile | `compliance_profile` | Default `gcc-moderate` | Tags + control mapping. |
| Member count | `member_count` | Default `2` | 1–8; ≥2 for HA. |
| Availability zones | `availability_zones` | Default `["1","2"]` | Members round-robined across zones. |
| Discovery identity type | `discovery_identity_type` | Default `user_assigned_mi` | `user_assigned_mi` \| `service_principal`. |
| Discovered subscriptions | `discovered_subscription_ids` | Default `[]` | Bare GUIDs; Reader scope for discovery. |
| Spoke VNet IDs | `spoke_vnet_ids` | Default `[]` | Spokes whose `dns_servers` point at the DDI VIP. |
| Write spoke DNS | `enable_spoke_dns_write` | Default `false` | Needs Network Contributor; only with `spoke_vnet_ids`. |
| Monitoring source CIDRs | `monitoring_source_cidrs` | Default `[]` | SNMP sources when `enable_snmp=true`; never `0.0.0.0/0`. |
| Grid peer CIDRs | `grid_peer_cidrs` | Default `[]` | Grid VPN/comms peers; `grid` model only. |
| Private Resolver inbound IP | `private_resolver_inbound_ip` | Default `null` | Enables Azure conditional-forwarding. |
| Extra tags | `tags` | Default `{}` | Merged with module-managed tags. |

Secrets are **not** catalog fields. The admin password, grid shared secret,
join token, and discovery credentials live in the Key Vault referenced by
`key_vault_id`, named via the module's `*_secret_name` variables
(`admin_password_secret_name`, `grid_shared_secret_name`,
`saas_join_token_secret_name`, …). The catalog item collects only the Key Vault
reference, never the secret values.

---

## Flow Designer flow (Azure)

![Azure ServiceNow closed loop for Infoblox DDI: a Service Catalog request carrying the Azure module tfvars is approved (with an extra SoD gate for prod and for the SaaS boundary), the CPG Terraform Connector plans and applies ../terraform on an in-boundary MID Server, IntegrationHub REST calls allocate the next available IP and register the A/PTR records over Infoblox WAPI/Universal DDI, the MID Server runs midserver-validate.sh (DNS, discovery-sync, IPAM-conflict) as a pass/fail gate, the Service Graph Connector reconciles the result into cmdb_ci_ip_network/subnet, and the request closes with a full audit trail — a failed gate routes back to approval](../figs/azure-sn-01-catalog-flow.png)

The flow specializes Chapter 7 §7.1's loop for this package:

1. **Intake.** Requester submits the catalog item; the form fields map to the
   Azure module `tfvars` per the table above. Stage-1-sourced fields
   (`hub_vnet_id`, `hub_resource_group_name`) are pre-populated.
2. **Approval / SoD gate.** Route on `environment` (a `prod` request needs the
   change-advisory approval) and on `deployment_model` — selecting
   `universal_ddi` requires `acknowledge_saas_boundary = true` and an **extra
   approval** because the Portal control plane sits outside the ATO boundary.
   Separation-of-duties: requester ≠ approver (Chapter 7 → AC-5/AC-6).
3. **Terraform apply.** The **CPG Terraform Connector** runs a speculative
   `plan` of [`../terraform`](../terraform) on the in-boundary MID Server, posts
   the plan for approval, then `apply`. Key Vault secret references resolve on
   the MID Server; no secret is stored in ServiceNow.
4. **IPAM/DNS calls.** After apply, **IntegrationHub REST** actions call Infoblox
   to allocate the next available IP from the DDI/spoke network and create the
   A/PTR records — see [IntegrationHub REST actions](#integrationhub-rest-actions).
5. **Validation gate.** The MID Server runs
   [`midserver-validate.sh`](./midserver-validate.sh), which executes the
   package's three checks (`../validation/dns-validation.sh`,
   `discovery-sync-check.sh`, `ipam-conflict-check.sh`) and emits a single JSON
   result. The flow parses it into work-notes; **any non-zero exit fails the
   change and routes back to step 2** (the dashed "fail" edge in the figure).
6. **CMDB reconcile.** The **Service Graph Connector for Infoblox** syncs the
   new/updated networks and records into the CMDB — see
   [Service Graph Connector CMDB mapping](#service-graph-connector-cmdb-mapping).
7. **Close.** The request closes with the plan, approvals, validation JSON, and
   CMDB reconcile all recorded (Chapter 7 → AU-2/AU-6/AU-12, CM-3/CM-5).

A **retirement** catalog item mirrors this in reverse: approve → `terraform
destroy` of `../terraform` → IntegrationHub delete-on-reclaim → CMDB
retire-CI (Chapter 7 → CM-8 accurate inventory).

---

## IntegrationHub REST actions

The active Infoblox calls the flow makes (step 4 above) for Azure are:

- **Allocate next available IP** from a network — NIOS
  `POST network/<ref>?_function=next_available_ip`, or the Universal DDI
  `ipam/address?_nextavailable=1` equivalent.
- **Create host/A record (+ PTR)** for the allocated address, tagged with the
  ServiceNow `sys_id` and the Azure `Tenant`/`environment` extensible
  attributes.
- **Delete on reclaim** for the retirement flow.

The concrete method, path, and JSON body for each — and the NIOS WAPI vs
Universal DDI differences — are in
[`integrationhub-actions.md`](./integrationhub-actions.md). Credentials come
from the Key Vault referenced by `key_vault_id`; all calls run on the
in-boundary MID Server.

---

## Service Graph Connector CMDB mapping

The **Service Graph Connector for Infoblox** keeps IPAM as the source of truth
and reflects it into the CMDB. For this package the mapping is:

| Infoblox object | CMDB class | Notes |
|---|---|---|
| IPAM `network` / container (the DDI subnet, spoke ranges) | `cmdb_ci_ip_network` | One CI per Infoblox network; `ddi_subnet_address_prefix` appears here after discovery. |
| IPAM subnet / child network | `cmdb_ci_ip_network_subnet` | Child-of relationship to the parent `cmdb_ci_ip_network`. |
| Extensible attributes (Azure tags → EAs) | CI attributes / custom columns | `Tenant`, `environment`, `deployment_model`, `compliance_profile`, and `servicenow_sys_id` map onto CI fields for correlation. |
| Host/A record IPs | `cmdb_ci_ip_address` (as available) | Correlated back to the catalog request via `servicenow_sys_id`. |

Because Azure **cloud discovery** (contract §5) syncs VNets/subnets/NICs into
Infoblox IPAM first, the CMDB reconcile reflects **Azure reality via Infoblox**,
not a guess — the same "IPAM is the system of record" discipline as Chapter 7
§7.1. The `discovered_subscription_ids` on the catalog form scope what discovery
(and therefore the CMDB) sees.

---

## GCC-Moderate notes

Specializing Chapter 7 §7.4 for this Azure package (commercial `.com`,
GCC-Moderate posture per [`../_module-contract.md`](../_module-contract.md) §1):

- **MID Server in-boundary.** Register the MID Server that runs the Terraform
  apply, the IntegrationHub REST callouts, and `midserver-validate.sh` **inside
  the tenant/ATO boundary**, alongside the DDI subnet. The execution and
  credential path never leaves the boundary — the same discipline the module's
  NSG scoping (§4, never `0.0.0.0/0`) applies to the network.
- **Secrets stay in Azure Key Vault.** No Infoblox/WAPI credential is stored in
  ServiceNow. The catalog item collects only `key_vault_id`; the MID Server
  resolves the actual secrets from that vault (`admin_password_secret_name`,
  `grid_shared_secret_name`, `saas_join_token_secret_name`, and the WAPI/CSP
  credentials) at run time. ServiceNow holds references, not secret material.
- **Universal DDI SaaS caveat.** With `deployment_model = "grid"` (the default),
  every Infoblox call is **WAPI-to-Grid, in-boundary** — boundary-clean. With
  `deployment_model = "universal_ddi"`, the IntegrationHub calls and the
  discovery-sync check target the Infoblox **Portal (CSP) API, which is outside
  the boundary**; that path is gated by `acknowledge_saas_boundary = true`
  (default `false` hard-fails the plan) and, in this flow, an **extra approval**
  at step 2. Keep the SaaS path an explicit, reviewed exception — not the
  default.
- **Control mapping** is inherited from Chapter 7 §7.4 (AC-5/AC-6 approval+SoD,
  AU-2/AU-6/AU-12 + CM-3/CM-5 audit trail, CM-6 validation gates, CM-8 reclaim);
  this package supplies the Azure-specific evidence (the tfvars-mapped catalog
  item, the plan/approval records, and the `midserver-validate.sh` JSON).

---

*See also:* [`integrationhub-actions.md`](./integrationhub-actions.md) ·
[`midserver-validate.sh`](./midserver-validate.sh) ·
[`../_module-contract.md`](../_module-contract.md) ·
[`../../07-servicenow-orchestration.md`](../../07-servicenow-orchestration.md)
