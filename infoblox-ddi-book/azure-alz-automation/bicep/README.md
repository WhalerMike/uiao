# Bicep — Infoblox DDI extension for an Azure Landing Zone (Stage 2)

Parallel Bicep implementation of the Infoblox DDI layer, mirroring the Terraform
module one-for-one via the shared [`_module-contract.md`](../_module-contract.md)
(identical param names, ports, IAM scopes, naming, and outputs). It layers on the
Microsoft **ALZ Accelerator** (Stage 1) and adds the **DDI + DNS-security layer
inside the Connectivity hub** — nothing else.

> **Status: coherent starter skeleton, NOT a certified production module.** It
> encodes the right structure, variables, resources, and guardrails, but you must
> pin your own Marketplace image + VM SKU (region/model-dependent — never
> hard-coded here), supply CIDRs, and test in a sandbox ALZ first.

Commercial Azure **`.com`** endpoints only (GCC-Moderate posture on commercial
cloud). **Not** Azure Government (`.us`).

---

## Files

| File | Purpose |
|---|---|
| `main.bicep` | Entry point. Params per contract §3; creates the DDI subnet, wires the NSG module, enforces the SaaS **boundary guard**, and selects the `grid` vs `universal_ddi` member module. |
| `main.bicepparam` | Example parameter file (`deployment_model='grid'`, commercial values). |
| `modules/nsg.bicep` | NSG + security rules per contract §4 (conditional by model; DHCP off by default; default-deny; mgmt/monitoring source CIDRs). |
| `modules/vnios-grid.bicep` | `member_count` vNIOS VMs across AZs; NICs on the DDI subnet; `customData`/cloud-init carrying admin pw + temp license + grid-join (secrets from Key Vault). |
| `modules/universal-ddi.bicep` | Lightweight UDDI host VMs + a `deploymentScripts` (Azure CLI) that performs Portal enrollment via REST — the clearly-marked SaaS API handoff. |
| `modules/discovery-identity.bicep` | User-assigned MI (or SP handoff) + role assignments (Reader / Private DNS Zone Contributor / Network Contributor) per contract §5. |
| `modules/role-assignment.bicep` | Small helper: one built-in role assignment at RG or VNet scope (used for cross-scope grants). |

---

## Parameters (contract §3)

| Param | Type | Default | Notes |
|---|---|---|---|
| `name_prefix` | string | `ddi` | Prefix for all resource names. |
| `location` | string | hub RG location | Azure region (commercial). |
| `environment` | string | `prod` | `dev`/`test`/`prod`; feeds tags. |
| `deployment_model` | string | `grid` | `grid` \| `universal_ddi`. |
| `acknowledge_saas_boundary` | bool | `false` | Must be `true` to allow `universal_ddi` (see boundary guard). |
| `compliance_profile` | string | `gcc-moderate` | Drives tags + control mapping. |
| `hub_resource_group_name` | string | — | Stage-1 output. |
| `hub_vnet_id` | string | — | Stage-1 output; DDI subnet is added to it. |
| `ddi_subnet_address_prefix` | string | — | Dedicated DDI subnet CIDR. |
| `member_count` | int | `2` | vNIOS members / UDDI hosts; ≥2 for HA. |
| `availability_zones` | array | `["1","2"]` | Spread members across zones. |
| `vnios_vm_sku` | string | — | VM size; region/model-dependent — **do not hard-code**. |
| `vnios_image` | object | — | Marketplace `publisher/offer/sku/version` (+ `plan` for BYOL/PAYG). |
| `key_vault_id` | string | — | Existing Key Vault for secrets. |
| `discovery_identity_type` | string | `user_assigned_mi` | `user_assigned_mi` \| `service_principal`. |
| `spoke_vnet_ids` | array | `[]` | Spokes whose `dns_servers` point at the DDI VIP (opt-in). |
| `tags` | object | `{}` | Merged with module-managed tags. |
| `admin_password_secret_name` / `grid_shared_secret_name` / `temp_license_secret_name` | string | see param | Key Vault **secret names** (values pulled at deploy via `getSecret`). |
| `dns_client_prefixes` / `mgmt_source_prefix` / `monitoring_source_prefix` / `grid_peer_prefixes` | | | NSG source scoping (§4). Never `0.0.0.0/0`. |
| `enable_dhcp` / `enable_snmp` | bool | `false` | Optional NSG rules. |

**Outputs (§7):** `ddi_subnet_id`, `dns_server_ips`, `ddi_anycast_vip`, `grid_master_ip`
(grid only), `discovery_identity_id`. *(The anycast VIP / GM IP are Grid-runtime
facts; the skeleton stands them in with member-1's NIC IP until the Grid is formed
via the Infoblox API — see handoff below.)*

---

## Deploy

Deploy at **resource-group scope**, into the Connectivity/hub RG that holds
`hub_vnet_id` (so the DDI subnet can be created as a child of the existing hub VNet):

```bash
az deployment group create \
  --resource-group <hub_resource_group_name> \
  --template-file main.bicep \
  --parameters main.bicepparam
```

Before deploying a Marketplace vNIOS image, accept its terms once:

```bash
az vm image list --publisher infoblox --all -o table
az vm image terms accept --urn <publisher:offer:sku:version>
```

---

## Boundary guard (contract §1 — critical)

`deployment_model = universal_ddi` routes the Infoblox **Portal (SaaS)** control
plane **outside** the ATO boundary (outbound 443). `main.bicep` **hard-fails** the
deployment unless `acknowledge_saas_boundary = true`, with a message pointing to
the FedRAMP / authorization review.

The guard uses a stable-Bicep "assert-style" trick (a runtime division-by-zero that
aborts the deployment only when the boundary is violated — see the heavily
commented block in `main.bicep`). If you prefer the native `assert` keyword, enable
the experimental feature and replace the guard:

```jsonc
// bicepconfig.json
{
  "experimentalFeaturesEnabled": { "assertions": true }
}
```
```bicep
assert saasBoundaryAcknowledged = !(deployment_model == 'universal_ddi' && !acknowledge_saas_boundary)
```

`grid` (the default) is boundary-clean and needs no acknowledgement.

---

## Stage-1 → Stage-2 wiring

The Stage-1 **ALZ Accelerator** outputs become Stage-2 inputs:

| Stage-1 output | Stage-2 param |
|---|---|
| `hub_vnet_id` | `hub_vnet_id` |
| hub RG name | `hub_resource_group_name` |
| (existing) Key Vault | `key_vault_id` |
| (existing) Private DNS Resolver inbound endpoint | conditional-forwarder target (see §8, configured via Infoblox API) |

Pipe them straight from Stage-1 outputs into `main.bicepparam` (or a CI variable
group). Because the DDI subnet is created here as a child of the **existing** hub
VNet, coordinate subnet ownership with any Stage-1 IaC that also enumerates hub
subnets, to avoid drift.

### Reader at subscription scope (§5)

`main.bicep` runs at **resource-group** scope, and Bicep cannot widen a module from
RG up to **subscription** scope. So the discovery identity's RG/VNet grants
(Private DNS Zone Contributor, Network Contributor) are applied by the module, but
the **subscription-level Reader** grant is applied out-of-band. Grant it with a tiny
subscription-scoped deployment (or have the platform team apply it):

```bash
# principalId = output 'discovery_principal_id' from the discovery module
az role assignment create \
  --assignee-object-id <discovery_principal_id> \
  --assignee-principal-type ServicePrincipal \
  --role Reader \
  --scope /subscriptions/<discovered_sub_id>
```

No `Owner`, no `Contributor` at subscription scope. Record-write and spoke-write are
strictly opt-in (`enable_record_write`, `manage_spoke_dns`).

---

## Where Bicep hands off to the Infoblox API / Ansible / Terraform provider

There is **no Bicep-native Infoblox resource**. Bicep builds the Azure substrate —
subnet, NSG, VMs, identity, and (for `universal_ddi`) the Portal-enrollment
`deploymentScript`. Everything that configures **DDI objects inside Infoblox** must
be done through the Infoblox **WAPI / Ansible collection / Terraform provider**
(`infobloxopen/infoblox`) after the VMs are up:

- **Grid formation / licensing / anycast VIP** — join members to the Grid Master,
  apply licenses, assign the DDI anycast VIP (then feed the real VIP back into
  `ddi_anycast_vip` / spoke `dns_servers`).
- **DNS views, authoritative zones, and conditional forwarders** (§8) — forward
  `*.privatelink.*` / Azure private names to the **Azure DNS Private Resolver inbound
  endpoint**; optionally add a Private Resolver **outbound** ruleset forwarding the
  enterprise domain back to the DDI VIP.
- **Discovery jobs** — configure the Azure discovery job in Infoblox to use the
  discovery identity's **client ID** (`discovery_client_id` output) for IPAM sync.
- **Spoke `dns_servers`** — writing the VIP onto spokes is gated on `spoke_vnet_ids`
  + the Network Contributor grant; the record write itself is an Azure op you can do
  in Bicep/Terraform, but the DDI-side records/zones are Infoblox API objects.

See the package guide (`../Azure-ALZ-Infoblox-DDI-Automation-Guide.md`) and the
`validation/` scripts for the Stage-3 gates (resolve a record, confirm discovery
sync, conflict check).

---

*Independent of UIAO governance canon; vendor-integration documentation.*
