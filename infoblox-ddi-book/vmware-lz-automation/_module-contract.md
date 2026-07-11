# Shared Module Contract — VMware (VCF / vSphere / NSX-T) + Infoblox DDI

> **Purpose.** This file is the single source of truth that keeps the Terraform module,
> the pipeline, the validation scripts, and the written guide **consistent** — identical
> variable names, ports, discovery scopes, resource-naming, and architectural decisions.
> Every artifact in `vmware-lz-automation/` MUST conform to this contract. If a value
> is version/model-dependent (OVA build, appliance model, vCPU/RAM), the artifact says
> so rather than hard-coding a guess.
>
> **This is the on-prem / private-cloud anchor of the volume.** Unlike the hyperscaler
> packages, the Grid Master frequently lives *here*, in the VCF management domain, and
> **DHCP is genuinely Infoblox's job** — so DHCP `67-68/udp` is **ON by default**.

## 1. Boundary & compliance profile (fixed for this deliverable)

- **Cloud boundary:** the **VMware Cloud Foundation (VCF) private cloud** — self-contained
  vSphere + NSX-T inside your own datacenter / sovereign estate. There is no hyperscaler
  region and no cloud "Marketplace"; vNIOS deploys as an **OVA/OVF** from a vSphere
  **content library** (or a local `.ova` via `ovftool`). Because the Grid runs entirely
  inside VCF, the default posture is **air-gap-friendly**.
- **Compliance profile:** `fedramp-moderate` (FedRAMP Moderate-equivalent controls).
  Artifacts carry a `compliance_profile` variable defaulting to `"fedramp-moderate"`.
- **Control-plane boundary rule (critical):**
  - `deployment_model = "grid"` → the vNIOS Grid control plane runs **inside the SDDC /
    ATO boundary**. Boundary-clean; the default and the natural fit here (the Grid Master
    typically already lives in the management domain).
  - `deployment_model = "universal_ddi"` → the Infoblox Portal (SaaS) control plane is
    **outside** the ATO boundary and requires outbound `443` to the Portal. Artifacts MUST
    emit a boundary/authorization caveat and gate this path behind an explicit
    `acknowledge_saas_boundary = true` variable (default `false`, which hard-fails the plan
    with a message pointing to the authorization review).

## 2. Layering model (how it sits on VCF / the SDDC)

Three stages; this module is **Stage 2**. It never builds the SDDC, NSX-T fabric, or the
domain topology — those are Stage 1 (VMware Cloud Foundation / vSphere / NSX-T).

```
Stage 1  VCF / vSphere / NSX-T (SDDC Manager, vCenter, NSX Manager)
         → facts: vsphere_datacenter, compute_cluster, resource_pool, datastore,
           management_portgroup, nsx_manager, tier0/tier1 gateway ids
                     │  (Stage-1 inventory consumed as inputs — never re-created here)
                     ▼
Stage 2  THIS MODULE — Infoblox DDI in the management/edge domain
                     │  outputs: ddi_anycast_vip, dns_server_ips, grid_master_ip,
                     ▼            discovery_identity_id, ddi_member_vm_ids
Stage 3  Validation (pipeline gates: resolve a record, confirm discovery sync, conflict check)
```

**"Hub" ≡ the management/edge domain.** Where the Azure package says "Connectivity hub
VNet," the VMware package means the **VCF management (or a dedicated edge/services)
domain** — the vSphere cluster + management dvPortGroup where the Grid Master and the
primary DNS/DHCP members live, reachable across the NSX fabric by every workload domain.

## 3. Canonical input variables (mapped from the Azure package)

Canonical **names are preserved** where they carry the same meaning; infrastructure-shaped
inputs are renamed to their VMware equivalent. The **Azure → VMware** column makes the
mapping explicit so the two packages stay one-for-one.

| Variable | Type | Default | Azure → VMware mapping / notes |
|---|---|---|---|
| `name_prefix` | string | `"ddi"` | *(same)* Prefix for all names → `ddi-vnios-h1`, `ddi-mgmt-group`, `ddi-disco-role`. |
| `vsphere_datacenter` | string | — | `location` → the vSphere **datacenter** name. |
| `environment` | string | `"prod"` | *(same)* `dev`/`test`/`prod`; feeds tags + sizing. |
| `deployment_model` | string | `"grid"` | *(same)* `grid` \| `universal_ddi`. |
| `acknowledge_saas_boundary` | bool | `false` | *(same)* Must be `true` to allow `universal_ddi` (see §1). |
| `compliance_profile` | string | `"fedramp-moderate"` | *(same, new default)* Drives tags + control mapping. |
| `compute_cluster` | string | — | `hub_resource_group_name` → target **vSphere cluster** in the mgmt/edge domain. |
| `resource_pool` | string | `null` | *(new/optional)* resource pool for the member VMs. |
| `datastore` | string | — | *(new)* datastore for member OS/DB disks. |
| `management_portgroup` | string | — | `hub_vnet_id` → the management **dvPortGroup** the member vNICs attach to. |
| `ddi_mgmt_network_cidr` | string | — | `ddi_subnet_address_prefix` → CIDR of that management network; used for DFW scoping + static-IP sanity. |
| `member_count` | number | `2` | *(same)* vNIOS members / NIOS-X hosts; ≥2 for HA. |
| `esxi_hosts` | list(string) | `[]` | `availability_zones` → ESXi hosts to spread members across (anti-affinity). |
| `vnios_appliance_model` | string | — | `vnios_vm_sku` → vNIOS **model / OVF deployment option** (CP-V/TE-V…); model-dependent — do not hard-code, document sizing. |
| `vnios_ovf` | object | — | `vnios_image` → **content-library item** or **local `.ova` path** (never invent a build). |
| `discovery_identity_type` | string | `"vcenter_service_account"` | *(same key)* the least-priv discovery credential model (§5). |
| `workload_tier1_ids` | list(string) | `[]` | `spoke_vnet_ids` → Tier-1 gateways whose DNS forwarder points at the DDI VIP. |
| `tags` | map(string) | `{}` | *(same)* Merged with module-managed **vSphere tags**. |

**Secrets — the key VMware difference.** There is **no cloud KMS / Key Vault** here, so the
Azure `key_vault_id` + `*_secret_name` inputs have **no VMware analog**. Instead the secret
*values* (`admin_password`, `temp_license`, `grid_shared_secret`, `saas_join_token`,
plus the `vsphere_password` / `nsx_password` connection creds) are passed as **sensitive
Terraform variables sourced from HashiCorp Vault or the CI secret store** at apply time —
never committed, never emitted as plaintext outputs. See §9.

## 4. Ports (NSX-T DFW rules / segment security the module creates)

Same port set as the Azure package, **plus DHCP is ON by default** (on VMware you own the
data path, so Infoblox is the authoritative DHCP server via NSX DHCP relay).

| Service | Port | Proto | Direction | When |
|---|---|---|---|---|
| DNS | 53 | tcp+udp | inbound from tenant/NSX forwarder | always |
| DHCP | 67–68 | udp | inbound from **NSX DHCP relay** | **ON by default** (`enable_dhcp = true`) |
| Grid VPN | 1194 | udp | in/out to Grid members/GM | `deployment_model = grid` |
| Grid comms | 2114 | tcp | in/out | `deployment_model = grid` |
| NTP | 123 | udp | outbound | always |
| HTTPS mgmt / WAPI | 443 | tcp | inbound (mgmt CIDR; admins, Aria plug-in, CNA) | always |
| Portal sync | 443 | tcp | **outbound to Infoblox Portal** | `deployment_model = universal_ddi` only |
| SNMP | 161 | udp | inbound (monitoring CIDR) | optional |

Default-deny everything else via an explicit **DFW drop rule**; scope every source to an
explicit CIDR/group variable, **never `0.0.0.0/0`** (rejected in `variables.tf`).

## 5. Least-privilege discovery identity (vCenter/NSX → Infoblox IPAM sync)

Discovery on VMware is **Cloud Network Automation (CNA)** connecting to vCenter (and NSX
Manager). The credentials must be least-privilege:

| Credential | Where | Least-privilege permission |
|---|---|---|
| vCenter service account | vCenter SSO | a **read-only** role scoped to the datacenter/cluster objects — enumerate clusters, VMs, port groups, IPs. **No write.** |
| NSX-T API user | NSX Manager | **read** of segments/gateways (read/write only if NSX is to *create* networks/records via Infoblox). |
| Infoblox admin group (for CNA/plug-in) | Grid | a **custom admin group** with cloud-API access and IPAM + DNS + DHCP + Grid (+ Tenant when CNA is licensed) rights on the relevant objects. |

No vCenter Administrator role; no NSX Enterprise Admin. The record/network-write rights are
opt-in, granted only when NSX or Aria actually writes back.

**This is config/role, not cloud IAM.** Creating the vCenter service account is an SSO/AD
task; the module may **optionally** create the read-only **vSphere role + permission**
(`manage_discovery_role = true`) as a convenience, but the **CNA vDiscovery job itself is an
API/UI handoff** on the Grid — there is no first-class Terraform resource for it.

## 6. Resource-naming convention

`${name_prefix}-<role>-<host/index>` e.g. `ddi-vnios-h1`, `ddi-vnios-h2`, `ddi-mgmt-group`
(DFW group), `ddi-disco-role`, `ddi-niosx-1`. All member VMs carry **vSphere tags**:
`workload=infoblox-ddi`, `layer=mgmt-domain-ddi`, `compliance_profile=<value>`,
`deployment_model=<value>`, `managed_by=terraform`, `environment=<value>`.

## 7. Canonical outputs (mapped from the Azure package)

`ddi_anycast_vip`, `dns_server_ips` (list), `grid_master_ip` (grid only),
`discovery_identity_id`, and `ddi_member_vm_ids` (maps from Azure `ddi_subnet_id` — the
Stage-2 objects handed to Stage-3 validation).

## 8. DNS / DHCP integration contract

- **NSX-T DNS forwarder → Infoblox.** Tier-0/Tier-1 gateway **DNS forwarder** points its
  upstream at the DDI member VIP; tenant VMs resolve via the forwarder, which forwards to
  the Grid. The Grid is the single resolution brain for the private cloud.
- **Infoblox → on-prem AD DNS (conditional forwarding).** The Grid **conditionally forwards**
  `corp.example` (and reverse zones) to the **on-prem AD DNS** servers, so AD-integrated
  names resolve without Infoblox being authoritative for AD zones. (This is the mirror of
  the Azure package's forward-to-Private-Resolver path.)
- **DHCP served by Infoblox.** NSX **DHCP relay** on tenant segments points at the vNIOS
  DHCP members (67-68/udp); Infoblox allocates from the IPAM-authoritative range and can
  write the A/PTR record. DHCP is ON by default (§4).
- **Cross-forward to other clouds.** Where the Grid extends into a CSP, the private cloud
  cross-forwards CSP-private namespaces to that cloud's resolver (documented, not always
  automated here).

## 9. Style for code artifacts

- Terraform: pin `hashicorp/vsphere`, `vmware/nsxt`, and `infobloxopen/infoblox` in
  `versions.tf`; every variable documented; skeleton is **illustrative-but-coherent**
  (labeled a starter, not a certified production module). Guard the SaaS path per §1.
- **OVA/OVF, not Marketplace.** Members deploy with `vsphere_virtual_machine` +
  `ovf_deploy` (content-library item or local OVF), **VMXNET3** vNICs, **anti-affinity**
  across `esxi_hosts`, thick or thin disk. First-boot config (admin pw, temp license,
  grid-join / portal-join, static IP) is carried in the OVF **vApp properties**.
- **Secrets from Vault/CI**, never a cloud KMS — sensitive variables injected at apply
  time; never in state as plaintext, never in outputs.
- Never invent an OVA build, appliance-model SKU, vCPU/RAM figure, or provider version —
  parameterize and point to the Infoblox vNIOS-for-VMware install guide.
