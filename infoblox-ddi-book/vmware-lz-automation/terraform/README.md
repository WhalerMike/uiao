# Terraform — Infoblox DDI on a VMware (VCF / vSphere / NSX-T) Landing Zone (Stage 2)

Starter Terraform module that adds an **Infoblox DDI + DNS-security layer** to the
**management/edge domain** of a VMware Cloud Foundation private cloud. It is **Stage 2**:
it consumes the vSphere/NSX inventory of an existing SDDC (**Stage 1**) and never builds
VCF domains, vCenter, the NSX-T fabric, or compute.

> **Read [`../_module-contract.md`](../_module-contract.md) first.** It is the single
> source of truth for variable names, ports, discovery scopes, naming, outputs, and the
> FedRAMP-Moderate boundary rule. This module conforms to it exactly.

## Boundary & compliance posture

Built for a **FedRAMP-Moderate operating posture on a self-contained VCF private cloud**
(air-gap-friendly — the Grid runs entirely inside the SDDC).

| `deployment_model` | Control plane | FedRAMP-Moderate fit |
|---|---|---|
| `grid` (default) | vNIOS Grid **inside** the SDDC/ATO boundary | Boundary-clean. The natural VMware fit. |
| `universal_ddi` | Infoblox Portal **SaaS, outside** the boundary (outbound 443) | **Hard-fails** unless `acknowledge_saas_boundary = true` (points at the FedRAMP/authorization review). |

The hard-fail lives in `main.tf` as a `precondition` on `terraform_data.boundary_guard`.

## The VMware differences (vs. the Azure package)

- **DHCP is Infoblox's job** — `enable_dhcp` defaults **true**; the module opens
  `67-68/udp` and wires an NSX **DHCP relay** to the members.
- **OVA/OVF, not a Marketplace image** — members deploy via `vsphere_virtual_machine`
  `ovf_deploy` from a **content library item** or a local `.ova`, with **VMXNET3** vNICs,
  thick/thin disk, and **DRS anti-affinity** across `esxi_hosts`.
- **No cloud KMS** — secrets (`admin_password`, `grid_shared_secret`, `saas_join_token`,
  vCenter/NSX passwords) are **sensitive variables from HashiCorp Vault / CI**, not a Key
  Vault.
- **Security = NSX-T DFW** — a member group + default-deny security policy, not a cloud NSG.
- **Discovery = CNA** — a least-privilege **read-only vCenter service account + NSX API
  user**; the module optionally manages the vSphere role, and the CNA job is an API handoff.

## What it creates

- An **NSX-T DFW** member group + default-deny security policy with exactly the contract §4
  ports (DNS, **DHCP by default**, Grid VPN/comms on grid, NTP, HTTPS/WAPI, optional
  SNMP/SSH, Portal-egress on universal_ddi) — sources scoped to CIDR variables, never
  `0.0.0.0/0`.
- **`deployment_model = "grid"`** → `member_count` vNIOS members from the OVA/OVF, spread
  across `esxi_hosts`, first-boot config (temp license + admin pw + static IP + grid-join)
  via OVF vApp properties, plus a DRS anti-affinity rule.
- **`deployment_model = "universal_ddi"`** → NIOS-X host VMs + a `null_resource`/local-exec
  **Portal-enrollment handoff** (the API seam).
- The optional read-only **discovery role/permission** for the vCenter service account
  (contract §5; the CNA vDiscovery job is a documented API handoff).
- **NSX DNS forwarder zone** → the DDI VIP, Infoblox **conditional forwarders** to on-prem
  AD DNS, and the **DHCP relay** to the members (contract §8).

## Files

| File | Purpose |
|---|---|
| `versions.tf` | Provider pins (`vsphere`, `nsxt`, `infobloxopen/infoblox`, `null`) + provider blocks. |
| `variables.tf` | Every contract §3 input + supporting inputs, with validation. |
| `main.tf` | Locals, tags (§6), Stage-1 SDDC data lookups, boundary hard-fail, secret preconditions. |
| `firewall.tf` | NSX-T DFW group + default-deny security policy (§4), conditional by `deployment_model`. |
| `grid.tf` | vNIOS Grid path — OVA/OVF deploy + anti-affinity (`deployment_model=grid`). |
| `universal_ddi.tf` | Universal DDI (SaaS) path + Portal enrollment handoff. |
| `discovery.tf` | Read-only vCenter role/permission (§5) + CNA vDiscovery handoff. |
| `dns.tf` | NSX DNS forwarder + AD conditional forwarders + DHCP relay (§8). |
| `outputs.tf` | Canonical outputs (§7). |
| `examples/hub-integration/` | Realistic call wired to a vSphere/NSX inventory, `deployment_model="grid"`. |

## Inputs (canonical — contract §3)

| Name | Type | Default | Notes |
|---|---|---|---|
| `name_prefix` | string | `"ddi"` | Prefix for all resource names. |
| `vsphere_datacenter` | string | — | vSphere datacenter (maps from Azure `location`). |
| `environment` | string | `"prod"` | `dev`/`test`/`prod`. |
| `deployment_model` | string | `"grid"` | `grid` \| `universal_ddi`. |
| `acknowledge_saas_boundary` | bool | `false` | Must be `true` for `universal_ddi`. |
| `compliance_profile` | string | `"fedramp-moderate"` | Tags + control mapping. |
| `compute_cluster` | string | — | Target vSphere cluster (maps from `hub_resource_group_name`). |
| `datastore` | string | — | Datastore for member disks. |
| `management_portgroup` | string | — | Management dvPortGroup (maps from `hub_vnet_id`). |
| `ddi_mgmt_network_cidr` | string | — | Mgmt network CIDR (maps from `ddi_subnet_address_prefix`). |
| `member_count` | number | `2` | vNIOS/NIOS-X members; ≥2 for HA. |
| `esxi_hosts` | list(string) | `[]` | Hosts to spread members across (maps from `availability_zones`). |
| `vnios_appliance_model` | string | — | vNIOS model/OVF option (maps from `vnios_vm_sku`); do not hard-code. |
| `vnios_ovf` | object | — | Content-library item or local `.ova` (maps from `vnios_image`). |
| `discovery_identity_type` | string | `"vcenter_service_account"` | Least-priv discovery model. |
| `workload_tier1_ids` | list(string) | `[]` | Tier-1s whose DNS forwarder points at the DDI VIP (maps from `spoke_vnet_ids`). |
| `tags` | map(string) | `{}` | Merged under module-managed vSphere tags. |

### Supporting inputs (not in §3, required by the implementation)

vCenter/NSX connection (`vsphere_server/user/password`, `nsx_manager/user/password`,
`allow_unverified_ssl`); DFW scoping (`mgmt_source_cidrs`, `dns_client_cidrs`,
`dhcp_relay_cidrs`, `grid_peer_cidrs`, `monitoring_source_cidrs`); toggles (`enable_dhcp`
**default true**, `enable_snmp`, `enable_ssh`, `enable_nsx_dns_forwarder`,
`manage_discovery_role`); sizing (`vnios_num_cpus`, `vnios_memory_mb`, `vnios_disk_gb`,
`disk_thin_provisioned`); addressing (`member_ip_addresses`, `member_netmask`,
`member_gateway`, `ddi_anycast_vip`); DNS (`ad_dns_servers`, `ad_forward_domains`);
discovery identities (`discovery_vcenter_user`, `discovery_nsx_user`); grid join
(`grid_name`, `grid_master_vip`); Portal (`infoblox_portal_url`); and the **secrets from
Vault/CI** (`admin_password`, `temp_license`, `grid_shared_secret`, `saas_join_token`).
See `variables.tf` for full descriptions and defaults.

## Outputs (contract §7)

`ddi_anycast_vip`, `dns_server_ips` (list), `grid_master_ip` (grid only),
`discovery_identity_id`, `ddi_member_vm_ids`.

## Example invocation

See [`examples/hub-integration/main.tf`](./examples/hub-integration/main.tf) for the full
version. Minimal shape:

```hcl
module "infoblox_ddi" {
  source = "../.." # or your module registry path

  vsphere_datacenter    = "DC1"
  compute_cluster       = "MgmtCluster"
  datastore             = "DS-SSD-01"
  management_portgroup  = "MGMT-dvPG"
  ddi_mgmt_network_cidr = "10.20.10.0/24"

  deployment_model = "grid" # boundary-clean default

  vnios_appliance_model = "TE-V1425" # confirm per NIOS version
  vnios_ovf = {
    content_library      = "infoblox"
    content_library_item = "nios-9.0.x" # your uploaded OVA item
  }

  member_count        = 2
  esxi_hosts          = ["esxi-01.corp.example", "esxi-02.corp.example"]
  member_ip_addresses = ["10.20.10.11", "10.20.10.12"]
  member_netmask      = "255.255.255.0"
  member_gateway      = "10.20.10.1"
  ddi_anycast_vip     = "10.20.10.10"

  mgmt_source_cidrs = ["10.20.0.0/24"]
  dns_client_cidrs  = ["10.30.0.0/16"]
  dhcp_relay_cidrs  = ["10.30.0.0/16"]
  grid_peer_cidrs   = ["10.20.10.0/24", "192.168.100.0/24"]
  grid_master_vip   = "192.168.100.10"

  ad_dns_servers = ["192.168.100.5", "192.168.100.6"]

  # connection + secrets from Vault/CI (see variables.tf)
  vsphere_server = "vcenter.corp.example"
  vsphere_user   = "svc-tf@vsphere.local"
  # vsphere_password / nsx_* / admin_password / grid_shared_secret via TF_VAR_* from Vault/CI
}
```

## Stage-1 → Stage-2 wiring

```
Stage 1  VCF / vSphere / NSX-T  ── inventory ──▶  Stage 2 (this module) ── outputs ──▶ Stage 3 (validation)
  vsphere_datacenter                vsphere_datacenter        ddi_anycast_vip
  compute_cluster / datastore  ──▶  compute_cluster           dns_server_ips
  management_portgroup              management_portgroup      grid_master_ip
  tier1 gateway ids                 workload_tier1_ids        discovery_identity_id
  (read-only SA, NSX API user)      discovery_vcenter_user    ddi_member_vm_ids
```

Feed `dns_server_ips` / `ddi_anycast_vip` into Stage-3 validation (resolve a record,
confirm discovery sync, conflict check).

## Before you deploy

- **Verify provider versions** in `versions.tf` against the registry.
- **Supply your own vNIOS OVA build + appliance model + vCPU/RAM** — never trust the example
  values; download the `.ova` from the Infoblox portal.
- **Inject every secret from Vault/CI** (`TF_VAR_vsphere_password`, `TF_VAR_admin_password`,
  `TF_VAR_grid_shared_secret`, …); never commit them.
- **Scope every CIDR** — the module refuses `0.0.0.0/0` on management/DNS/DHCP/monitoring
  sources.
- For `universal_ddi`, complete the authorization review and set
  `acknowledge_saas_boundary = true`.

---

> ## ⚠️ Starter skeleton — not a certified production module
>
> This is a **coherent starter skeleton**, explicitly labeled as such. It encodes the right
> structure, variables, resources, and guardrails, but is **not a certified production
> module**. Several resources are **illustrative** and marked in-code where real object
> paths, per-gateway attachments, an NSX source group, an `import`, or a control-plane API
> handoff is required (notably: NSX DNS-forwarder/DHCP-relay attachment, Infoblox conditional
> forwarders, the CNA vDiscovery job, and Universal DDI Portal enrollment). OVF vApp property
> keys and NSX/vSphere object attributes are version-specific — verify against your OVA and
> provider versions. Pin your own versions, supply your OVA/model, and **test in a sandbox
> vSphere cluster first**.
