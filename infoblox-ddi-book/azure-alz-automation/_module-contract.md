# Shared Module Contract — Azure ALZ + Infoblox DDI

> **Purpose.** This file is the single source of truth that keeps the Terraform module,
> the Bicep module, the pipelines, and the written guide **consistent** — identical
> variable names, ports, IAM scopes, resource-naming, and architectural decisions.
> Every artifact in `azure-alz-automation/` MUST conform to this contract. If a value
> is version/region-dependent, the artifact says so rather than hard-coding a guess.

## 1. Boundary & compliance profile (fixed for this deliverable)

- **Cloud boundary:** Commercial Azure, **`.com` endpoints** (`management.azure.com`,
  `login.microsoftonline.com`, `*.blob.core.windows.net`). **Not** Azure Government
  (`.us`). This matches a **GCC-Moderate** operating posture running on the commercial
  cloud.
- **Compliance profile:** `gcc-moderate` (FedRAMP Moderate-equivalent controls). Artifacts
  carry a `compliance_profile` variable defaulting to `"gcc-moderate"`.
- **Control-plane boundary rule (critical):**
  - `deployment_model = "grid"` → the vNIOS Grid control plane runs **inside the tenant /
    ATO boundary**. Boundary-clean; the default for GCC-Moderate.
  - `deployment_model = "universal_ddi"` → the Infoblox Portal (SaaS) control plane is
    **outside** the ATO boundary and requires outbound `443` to the Portal. Artifacts MUST
    emit a boundary/authorization caveat and gate this path behind an explicit
    `acknowledge_saas_boundary = true` variable (default `false`, which hard-fails the plan
    with a message pointing to the authorization review).

## 2. Layering model (how it sits on the ALZ Accelerator)

Three stages; this module is **Stage 2**. It never creates management groups, identity,
or governance — those are Stage 1 (the Microsoft ALZ Accelerator).

```
Stage 1  ALZ Accelerator (Bicep or Terraform, Azure Verified Modules)
         → outputs: hub_vnet_id, hub_resource_group_name, connectivity_subscription_id,
           log_analytics_workspace_id, firewall_private_ip (optional)
                     │  (remote state / module outputs consumed as inputs)
                     ▼
Stage 2  THIS MODULE — Infoblox DDI extension in the Connectivity hub
                     │  outputs: ddi_anycast_vip, dns_server_ips, grid_master_ip,
                     ▼            discovery_identity_id
Stage 3  Validation (pipeline gates: resolve a record, confirm discovery sync, conflict check)
```

## 3. Canonical input variables (identical names in TF and Bicep)

| Variable | Type | Default | Notes |
|---|---|---|---|
| `name_prefix` | string | `"ddi"` | Prefix for all resource names. |
| `location` | string | — | Azure region (commercial). |
| `environment` | string | `"prod"` | `dev`/`test`/`prod`; feeds tags + sizing. |
| `deployment_model` | string | `"grid"` | `grid` \| `universal_ddi`. |
| `acknowledge_saas_boundary` | bool | `false` | Must be `true` to allow `universal_ddi` (see §1). |
| `compliance_profile` | string | `"gcc-moderate"` | Drives tags + control mapping. |
| `hub_resource_group_name` | string | — | From Stage 1 output. |
| `hub_vnet_id` | string | — | From Stage 1 output. |
| `ddi_subnet_address_prefix` | string | — | Dedicated DDI subnet CIDR (created by this module in the hub VNet). |
| `member_count` | number | `2` | vNIOS members / UDDI hosts; ≥2 for HA. |
| `availability_zones` | list(string) | `["1","2"]` | Spread members across zones. |
| `vnios_vm_sku` | string | — | Azure VM size; region/model-dependent — do not hard-code, document sizing. |
| `vnios_image` | object | — | Marketplace publisher/offer/sku/version (BYOL or PAYG). |
| `key_vault_id` | string | — | Existing Key Vault for secrets (admin pw, join token, discovery creds). |
| `discovery_identity_type` | string | `"user_assigned_mi"` | `user_assigned_mi` \| `service_principal`. |
| `spoke_vnet_ids` | list(string) | `[]` | Spokes whose `dns_servers` should point at the DDI VIP (optional). |
| `tags` | map(string) | `{}` | Merged with module-managed tags. |

## 4. Ports (NSG rules the module creates on the DDI subnet)

| Service | Port | Proto | Direction | When |
|---|---|---|---|---|
| DNS | 53 | tcp+udp | inbound from spokes/on-prem | always |
| DHCP | 67–68 | udp | inbound | only if module serves DHCP (Azure DHCP is platform-managed; off by default) |
| Grid VPN | 1194 | udp | in/out to Grid members/GM | `deployment_model=grid` |
| Grid comms | 2114 | tcp | in/out | `deployment_model=grid` |
| NTP | 123 | udp | outbound | always |
| HTTPS mgmt | 443 | tcp | inbound (mgmt CIDR) | always |
| Portal sync | 443 | tcp | **outbound to Infoblox Portal** | `deployment_model=universal_ddi` only |
| SNMP | 161 | udp | inbound (monitoring CIDR) | optional |

Default-deny everything else; scope mgmt/monitoring sources to explicit CIDR variables,
never `0.0.0.0/0`.

## 5. Least-privilege discovery identity (Azure → Infoblox IPAM sync)

Prefer a **user-assigned managed identity**; fall back to an app-registration service
principal. Role assignments (scope = the subscriptions/RGs to be discovered):

| Role | Scope | Why |
|---|---|---|
| `Reader` | discovered subscription(s) | enumerate VNets, subnets, NICs, tags |
| `Private DNS Zone Contributor` | RG(s) holding private zones | only if Infoblox syncs/writes records into Azure Private DNS |
| `Network Contributor` | spoke VNet(s) | only if the module writes `dns_servers` on spokes |

No `Owner`, no `Contributor` at subscription scope. Record-write role is opt-in.

## 6. Resource-naming convention

`${name_prefix}-<role>-<zone/index>` e.g. `ddi-vnios-z1`, `ddi-nsg`, `ddi-subnet`,
`ddi-disco-mi`. All resources tagged: `workload=infoblox-ddi`, `layer=connectivity-ddi`,
`compliance_profile=<value>`, `deployment_model=<value>`, `managed_by=terraform|bicep`.

## 7. Canonical outputs (identical names in TF and Bicep)

`ddi_anycast_vip`, `dns_server_ips` (list), `grid_master_ip` (grid only),
`discovery_identity_id`, `ddi_subnet_id`.

## 8. DNS integration contract

- Infoblox members are authoritative for enterprise zones and **conditionally forward**
  Azure-service names (`*.privatelink.*`, `*.azure.com` private) to the **Azure DNS Private
  Resolver inbound endpoint** (Stage-1/existing).
- Spokes/hub `dns_servers` set to `ddi_anycast_vip` (or `dns_server_ips`) — module writes
  this only when `spoke_vnet_ids` provided and `Network Contributor` granted.
- Reverse the direction with an Azure Private Resolver **outbound** ruleset forwarding the
  enterprise domain to the DDI VIP (documented in the guide; not all deployments automate it).

## 9. Style for code artifacts

- Terraform: pin `azurerm` and `infobloxopen/infoblox` providers in `versions.tf`; every
  variable documented; skeleton is **illustrative-but-coherent** (labeled as a starter, not
  a certified production module). Guard the SaaS path per §1.
- Bicep: mirror the same variables as `param`s; where no Bicep-native Infoblox resource
  exists, use a `deploymentScript` (Azure CLI/REST) or clearly mark the API/Ansible handoff.
- Never invent Marketplace image versions or VM SKUs — parameterize and point to the doc.
