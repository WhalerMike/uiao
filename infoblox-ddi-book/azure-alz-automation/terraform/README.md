# Terraform — Infoblox DDI on an Azure Landing Zone (Stage 2)

Starter Terraform module that adds an **Infoblox DDI + DNS-security layer** to
the **Connectivity hub** of a Microsoft Azure Landing Zone. It is **Stage 2**: it
consumes the hub-network outputs of the **ALZ Accelerator (Stage 1)** and never
creates management groups, identity, or governance.

> **Read [`../_module-contract.md`](../_module-contract.md) first.** It is the
> single source of truth for variable names, ports, IAM scopes, naming, outputs,
> and the GCC-Moderate boundary rule. This module conforms to it exactly; the
> Bicep module mirrors the same surface.

## Boundary & compliance posture

Built for a **GCC-Moderate operating posture on COMMERCIAL Azure (`.com`
endpoints)** — **not** Azure Government (`.us`). The `azurerm` provider is left on
its default `public` environment on purpose; do not switch it to `usgovernment`.

| `deployment_model` | Control plane | GCC-Moderate fit |
|---|---|---|
| `grid` (default) | vNIOS Grid **inside** the tenant/ATO boundary | Boundary-clean. Recommended. |
| `universal_ddi` | Infoblox Portal **SaaS, outside** the boundary (outbound 443) | **Hard-fails** unless `acknowledge_saas_boundary = true` (points at the FedRAMP/authorization review). |

The hard-fail lives in `main.tf` as a `precondition` on `terraform_data.boundary_guard`.

## What it creates

- A dedicated **DDI subnet** in the Stage-1 hub VNet (`ddi-subnet`).
- An **NSG + rules** on that subnet, exactly per contract §4 (default-deny in
  *and* out; mgmt/monitoring scoped to CIDR variables, never `0.0.0.0/0`).
- **`deployment_model = "grid"`** → `azurerm_marketplace_agreement`, one NIC +
  `azurerm_linux_virtual_machine` per member (`member_count`, spread across
  `availability_zones`), first-boot config via vNIOS user-data (temp license +
  admin password + grid-join params, all from Key Vault).
- **`deployment_model = "universal_ddi"`** → lightweight NIOS-X host VMs + a
  `null_resource`/local-exec **Portal-enrollment handoff** (the API seam).
- A least-privilege **discovery identity** (user-assigned MI or existing SP) with
  scoped `Reader` / `Private DNS Zone Contributor` / `Network Contributor` role
  assignments (contract §5; write roles are opt-in).
- Infoblox **conditional forwarders** for Azure-service names → Private Resolver
  inbound endpoint, and the pattern for writing spoke `dns_servers` to the DDI
  VIP (contract §8).

## Files

| File | Purpose |
|---|---|
| `versions.tf` | Provider pins (`azurerm`, `infobloxopen/infoblox`, `random`, `tls`, `null`) + provider blocks. |
| `variables.tf` | Every contract §3 input + supporting inputs, with validation. |
| `main.tf` | Locals, tags (§6), DDI subnet, boundary hard-fail, Key Vault secret reads. |
| `nsg.tf` | NSG + rules (§4), conditional by `deployment_model`. |
| `grid.tf` | vNIOS Grid path (`deployment_model=grid`). |
| `universal_ddi.tf` | Universal DDI (SaaS) path + Portal enrollment handoff. |
| `discovery.tf` | Discovery identity + least-privilege RBAC (§5) + vDiscovery placeholder. |
| `dns.tf` | Conditional forwarders + spoke `dns_servers` write-through (§8). |
| `outputs.tf` | Canonical outputs (§7). |
| `examples/hub-integration/` | Realistic call wired to ALZ Accelerator remote state. |

## Inputs (canonical — contract §3)

| Name | Type | Default | Notes |
|---|---|---|---|
| `name_prefix` | string | `"ddi"` | Prefix for all resource names. |
| `location` | string | — | Azure region (commercial). |
| `environment` | string | `"prod"` | `dev`/`test`/`prod`. |
| `deployment_model` | string | `"grid"` | `grid` \| `universal_ddi`. |
| `acknowledge_saas_boundary` | bool | `false` | Must be `true` for `universal_ddi`. |
| `compliance_profile` | string | `"gcc-moderate"` | Tags + control mapping. |
| `hub_resource_group_name` | string | — | Stage-1 output. |
| `hub_vnet_id` | string | — | Stage-1 output; DDI subnet created here. |
| `ddi_subnet_address_prefix` | string | — | Dedicated DDI subnet CIDR. |
| `member_count` | number | `2` | vNIOS/UDDI hosts; ≥2 for HA. |
| `availability_zones` | list(string) | `["1","2"]` | Spread members across zones. |
| `vnios_vm_sku` | string | — | VM size; region/model-dependent — do not hard-code. |
| `vnios_image` | object | — | Marketplace publisher/offer/sku/version(+plan_name). |
| `key_vault_id` | string | — | Existing Key Vault for secrets. |
| `discovery_identity_type` | string | `"user_assigned_mi"` | `user_assigned_mi` \| `service_principal`. |
| `spoke_vnet_ids` | list(string) | `[]` | Spokes whose `dns_servers` point at the DDI VIP. |
| `tags` | map(string) | `{}` | Merged under module-managed tags. |

### Supporting inputs (not in §3, required by the implementation)

Scoping/behaviour knobs — see `variables.tf` for full descriptions and defaults:
`mgmt_source_cidrs`, `monitoring_source_cidrs`, `dns_client_cidrs`,
`grid_peer_cidrs`, `enable_ssh`, `enable_dhcp` (default **off**), `enable_snmp`,
`enable_accelerated_networking`, `private_resolver_inbound_ip`,
`azure_service_forward_domains`, `ddi_anycast_vip`, `enable_spoke_dns_write`,
`discovered_subscription_ids`, `private_dns_zone_rg_ids`, `enable_record_write`,
`existing_service_principal_object_id`, the Key Vault `*_secret_name` set,
`grid_name`, `grid_master_vip`, `infoblox_portal_url`,
`accept_marketplace_agreement`, `admin_username`.

## Outputs (contract §7)

`ddi_anycast_vip`, `dns_server_ips` (list), `grid_master_ip` (grid only),
`discovery_identity_id`, `ddi_subnet_id`.

## Example invocation

See [`examples/hub-integration/main.tf`](./examples/hub-integration/main.tf) for
the full version. Minimal shape:

```hcl
module "infoblox_ddi" {
  source = "../.." # or your module registry path

  location                  = "eastus"
  deployment_model          = "grid"           # boundary-clean default
  hub_resource_group_name   = data.terraform_remote_state.alz.outputs.hub_resource_group_name
  hub_vnet_id               = data.terraform_remote_state.alz.outputs.hub_vnet_id
  ddi_subnet_address_prefix = "10.10.4.0/27"

  vnios_vm_sku = "Standard_E4s_v5"              # confirm per NIOS version/region
  vnios_image  = { publisher = "infoblox", offer = "infoblox_nios_on_azure", sku = "nios-byol", version = "latest" }
  key_vault_id = data.terraform_remote_state.alz.outputs.connectivity_key_vault_id

  mgmt_source_cidrs = ["10.10.0.0/24"]
  dns_client_cidrs  = ["10.20.0.0/16"]
  grid_peer_cidrs   = ["10.10.4.0/27", "192.168.100.0/24"]
  grid_master_vip   = "192.168.100.10"

  discovered_subscription_ids = ["<connectivity-sub-guid>"]
}
```

## Stage-1 → Stage-2 wiring

```
Stage 1  ALZ Accelerator (AVM)  ── outputs ──▶  Stage 2 (this module) ── outputs ──▶ Stage 3 (validation)
   hub_vnet_id                     hub_vnet_id           ddi_anycast_vip
   hub_resource_group_name    ──▶  hub_resource_group_name   dns_server_ips
   connectivity_subscription_id    (provider subscription)   grid_master_ip
   (existing Key Vault, Private     key_vault_id +            discovery_identity_id
    Resolver inbound endpoint)      private_resolver_inbound_ip   ddi_subnet_id
```

Consume Stage-1 outputs via `terraform_remote_state` (shown in the example) or
pass them as plain variables/tfvars if you don't share state across stages. Feed
`dns_server_ips` / `ddi_anycast_vip` into Stage-3 validation (resolve a record,
confirm discovery sync, conflict check).

## Before you deploy

- **Verify provider versions** in `versions.tf` against the registry.
- **Discover the Marketplace image + VM SKU** (`az vm image list --publisher
  infoblox --all -o table`); never trust the example values.
- **Pre-create the Key Vault secrets** named by the `*_secret_name` variables.
- **Scope every CIDR** — the module refuses `0.0.0.0/0` on management sources.
- For `universal_ddi`, complete the authorization review and set
  `acknowledge_saas_boundary = true`.

---

> ## ⚠️ Starter skeleton — not a certified production module
>
> This is a **coherent starter skeleton**, explicitly labeled as such. It encodes
> the right structure, variables, resources, and guardrails, but it is **not a
> certified production module**. Several resources are **illustrative** and marked
> in-code where real IDs, an `azapi`/`restapi`/CSP provider, an `import`, or a
> control-plane API handoff is required (notably: Infoblox conditional forwarders,
> vDiscovery jobs, spoke `dns_servers` write-through, and Universal DDI Portal
> enrollment). Pin your own provider/module versions, supply your Marketplace
> image and VM SKU, and **test in a sandbox ALZ first**.
