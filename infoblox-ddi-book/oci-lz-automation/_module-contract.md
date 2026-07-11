# Shared Module Contract — OCI Landing Zone + Infoblox DDI

> **Purpose.** This file is the single source of truth that keeps the Terraform module,
> the pipelines, and the written guide **consistent** — identical variable names, ports,
> IAM scopes, resource-naming, and architectural decisions. Every artifact in
> `oci-lz-automation/` MUST conform to this contract. If a value is version/region/realm
> dependent, the artifact says so rather than hard-coding a guess.
>
> **Terraform-only.** Unlike the Azure package (which ships a parallel Bicep path), OCI's
> only first-class IaC is Terraform — the OCI **Resource Manager** service *is* Terraform.
> So there is one code path here (`terraform/`) and a Resource Manager note in `pipelines/`.

## 0. Candor up front — OCI is a thinner integration target

Be honest, mirroring how [`../04-oci.md`](../04-oci.md) handles it: OCI is a **later, thinner**
Infoblox integration than AWS/Azure/GCP. Two facts drive this contract:

- **No native Marketplace vNIOS listing.** You deploy vNIOS by **custom-image import** — pull
  the Infoblox OCI image (qcow2/VMDK) into an **Object Storage** bucket, then
  `oci compute image import` it into a reusable **custom image**. There is no
  `azurerm_marketplace_agreement` equivalent.
- **No deep, event-driven cloud-discovery connector.** Infoblox ships no OCI adapter
  equivalent to its AWS/Azure/GCP Cloud Network Automation connectors. IPAM synchronisation on
  OCI is **API/SDK/Terraform-driven** — a scheduled OCI-SDK job (or the Infoblox Terraform
  provider in the same pipeline that provisions the VCN) reconciles VCNs/subnets into IPAM.
  This module wires the **credential and the seam**, and says plainly that the sync itself is
  code you run, not a turnkey connector.

## 1. Boundary & compliance profile (fixed for this deliverable)

- **Cloud boundary:** Commercial OCI — the **OC1 realm**, `*.oraclecloud.com` endpoints. **Not**
  OCI Government (US Gov **OC2**, US DoD **OC3**) or **National Security** / EU Sovereign /
  dedicated-air-gapped realms. This matches a **FedRAMP Moderate-equivalent** operating posture
  running on the commercial realm.
- **Compliance profile:** `fedramp-moderate`. Artifacts carry a `compliance_profile` variable
  defaulting to `"fedramp-moderate"`.
- **Control-plane boundary rule (critical):**
  - `deployment_model = "grid"` → the vNIOS Grid control plane runs **inside the tenancy /
    ATO boundary**. Boundary-clean; the default.
  - `deployment_model = "universal_ddi"` → the Infoblox Portal (SaaS) control plane is
    **outside** the ATO boundary and requires outbound `443` to the Portal. Artifacts MUST
    emit a boundary/authorization caveat and gate this path behind an explicit
    `acknowledge_saas_boundary = true` variable (default `false`, which hard-fails the plan
    with a message pointing to the authorization review).
- **Sovereign / gov realms.** In OC2/OC3/National-Security realms, **vNIOS Grid** keeps the
  entire control plane inside the tenancy (the air-gap-friendly choice). **Universal DDI needs
  outbound 443 to the Infoblox Portal**, which sovereign/air-gapped realms typically disallow —
  so there, default to Grid. Confirm vNIOS custom-image availability in the specific realm first.

## 2. Layering model (how it sits on the CIS Landing Zone)

Three stages; this module is **Stage 2**. It never creates the tenancy, compartments, IAM
foundations, or the hub network fabric — those are Stage 1 (the OCI CIS / Core Landing Zone).

```
Stage 1  OCI CIS Landing Zone (Terraform, oracle-quickstart) / OCI Core Landing Zone
         → outputs: hub_vcn_ocid, drg_ocid, network_compartment_ocid,
           hub_subnet_ocid (mgmt), vault_ocid, (optional) service_gateway_ocid
                     │  (remote state / stack outputs consumed as inputs)
                     ▼
Stage 2  THIS MODULE — Infoblox DDI extension in the hub VCN (+ DRG hub-spoke)
                     │  outputs: ddi_anycast_vip, dns_server_ips, grid_master_ip,
                     ▼            discovery_identity_id, ddi_subnet_id
Stage 3  Validation (pipeline gates: resolve a record, confirm discovery sync, conflict check)
```

## 3. Canonical input variables

Names are mapped 1:1 from the Azure package where a concept exists; OCI-specific names replace
Azure-specific ones (region for location, OCIDs for resource IDs, ADs/FDs for zones, shape for
VM SKU, custom image OCID for Marketplace image, Vault for Key Vault).

| Variable | Type | Default | Notes (Azure analogue) |
|---|---|---|---|
| `name_prefix` | string | `"ddi"` | Prefix for all resource names. (`name_prefix`) |
| `region` | string | — | OCI region identifier, e.g. `us-ashburn-1` (commercial OC1). (`location`) |
| `environment` | string | `"prod"` | `dev`/`test`/`prod`; feeds tags + sizing. (`environment`) |
| `deployment_model` | string | `"grid"` | `grid` \| `universal_ddi`. (same) |
| `acknowledge_saas_boundary` | bool | `false` | Must be `true` to allow `universal_ddi` (see §1). (same) |
| `compliance_profile` | string | `"fedramp-moderate"` | Drives tags + control mapping. (`gcc-moderate`) |
| `network_compartment_ocid` | string | — | Compartment holding the hub VCN (Stage-1 output). (`hub_resource_group_name`) |
| `hub_vcn_ocid` | string | — | Hub VCN OCID; the DDI subnet is created inside it. (`hub_vnet_id`) |
| `drg_ocid` | string | — | Hub-spoke DRG (Stage-1). Route/attachment reference for spoke + on-prem reachability. (new — OCI hub-spoke) |
| `ddi_subnet_cidr` | string | — | Dedicated DDI subnet CIDR (created by this module in the hub VCN). (`ddi_subnet_address_prefix`) |
| `member_count` | number | `2` | vNIOS members / UDDI hosts; ≥2 for HA. (same) |
| `availability_domains` | list(string) | — | ADs to spread members across (many regions are single-AD). (`availability_zones`) |
| `fault_domains` | list(string) | `["FAULT-DOMAIN-1","FAULT-DOMAIN-2"]` | Always spread members across FDs within an AD. (new — OCI) |
| `vnios_shape` | string | — | Flexible shape, e.g. `VM.Standard.E4.Flex`; model/region-dependent — do not hard-code. (`vnios_vm_sku`) |
| `vnios_ocpus` / `vnios_memory_gbs` | number | — | OCPU + memory for the flexible shape, matched to the vNIOS model spec. (part of SKU) |
| `vnios_image_ocid` | string | — | OCID of the **imported custom image** (no Marketplace). Supply your own after `oci compute image import`. (`vnios_image`) |
| `vault_ocid` | string | — | OCI Vault holding secrets (admin pw, temp license, grid secret, join token, discovery key). (`key_vault_id`) |
| `discovery_identity_type` | string | `"instance_principal"` | `instance_principal` (dynamic group) \| `api_key_user`. (`discovery_identity_type`) |
| `spoke_vcn_ocids` | list(string) | `[]` | Spokes whose resolver forwarding should point at the DDI VIP (optional). (`spoke_vnet_ids`) |
| `freeform_tags` | map(string) | `{}` | Merged with module-managed freeform tags. (`tags`) |
| `defined_tags` | map(string) | `{}` | Optional OCI defined tags (namespace.key = value). (new — OCI) |

## 4. Ports (Security-List / NSG rules the module creates on the DDI subnet)

| Service | Port | Proto | Direction | When |
|---|---|---|---|---|
| DNS | 53 | tcp+udp | ingress from spokes/on-prem | always |
| DHCP | 67–68 | udp | ingress | only if module serves DHCP (OCI VCN DHCP is platform-managed; off by default) |
| Grid VPN | 1194 | udp | in/out to Grid members/GM | `deployment_model=grid` |
| Grid comms | 2114 | tcp | in/out | `deployment_model=grid` |
| NTP | 123 | udp | egress | always |
| HTTPS mgmt / WAPI | 443 | tcp | ingress (mgmt CIDR) | always |
| Portal sync | 443 | tcp | **egress to Infoblox Portal** | `deployment_model=universal_ddi` only |
| SNMP | 161 | udp | ingress (monitoring CIDR) | optional |
| SSH | 22 | tcp | ingress (mgmt CIDR) | optional (`enable_ssh`; prefer bastion) |

Default-deny everything else; scope mgmt/monitoring/client sources to explicit CIDR variables,
never `0.0.0.0/0`. Enforcement is either an **NSG** (`oci_core_network_security_group` + rules,
per-VNIC, preferred) or a **Security List** (`oci_core_security_list`, subnet-wide), selected by
`security_model`. The Grid rows and the outbound-Portal row are toggled by `deployment_model`.

## 5. Least-privilege discovery identity (OCI → Infoblox IPAM sync)

Prefer an **instance principal**: put the automation/vNIOS instance in a **dynamic group** and
grant that group read policies — no long-lived key stored. Fall back to an **IAM user + API
signing key** (public key on the user, private key held by the sync job). Policy statements
(scope = the network compartment(s) to be discovered):

| Verb / resource | Scope | Why |
|---|---|---|
| `read virtual-network-family` | compartment `network` | enumerate VCNs, subnets, CIDRs, VNICs |
| `read dns` (inspect dns-zones, read dns-views) | compartment `network` | read private views/zones for reconciliation |
| `read instance-family` | compartment `network` | map instances/IPs to records (optional) |
| `use tag-namespaces` (read) | tenancy | read defined tags that drive allocation |

No `manage`, no tenancy-admin. Grant `manage dns-*` only if Infoblox is to **write** OCI zones
(record-write is opt-in via `enable_record_write`).

**Discovery is API/SDK-driven (candid).** The policy above only *grants* the identity. The
actual OCI→IPAM sync is a scheduled OCI-SDK job or the Infoblox Terraform provider run in the
same pipeline — there is no `infoblox_vdiscovery_job` OCI connector. `discovery.tf` creates the
identity + policy and marks the sync as an explicit API/SDK handoff.

## 6. Resource-naming convention

`${name_prefix}-<role>-<ad/fd/index>` e.g. `ddi-vnios-ad1-fd1`, `ddi-nsg`, `ddi-subnet`,
`ddi-disco-dg` (dynamic group), `ddi-disco-policy`. All resources carry `freeform_tags`:
`workload=infoblox-ddi`, `layer=connectivity-ddi`, `compliance_profile=<value>`,
`deployment_model=<value>`, `managed_by=terraform`, `environment=<value>`.

## 7. Canonical outputs (names kept identical to the Azure package for cross-cloud parity)

`ddi_anycast_vip`, `dns_server_ips` (list), `grid_master_ip` (grid only),
`discovery_identity_id`, `ddi_subnet_id`.

## 8. DNS integration contract

- Infoblox members are authoritative for enterprise zones and **conditionally forward**
  OCI-owned names (`*.oraclevcn.com` and OCI private zones) to the **hub VCN OCI resolver's
  LISTENING endpoint** (created by this module or existing).
- OCI → Infoblox: the hub VCN resolver gets a **FORWARDING endpoint** + forwarding rules
  sending corporate domains and a catch-all to the vNIOS member IPs; spokes reach enterprise
  names via **associated private views** or a spoke→hub forwarding rule over the DRG.
- Spokes' subnet **DHCP options** resolve to the VCN resolver (`169.254.169.254`); the resolver
  forwards to Infoblox. The module writes forwarding rules only when `spoke_vcn_ocids` provided.
- Delegate reverse zones for OCI CIDRs to Infoblox so PTRs live in the authoritative IPAM.

## 9. Style for code artifacts

- Terraform: pin `oracle/oci` and `infobloxopen/infoblox` providers in `versions.tf`; every
  variable documented; skeleton is **illustrative-but-coherent** (labeled as a starter, not a
  certified production module). Guard the SaaS path per §1.
- vNIOS deploy = **custom image import**: never invent an image OCID or a shape — parameterise
  (`vnios_image_ocid`, `vnios_shape`/`vnios_ocpus`/`vnios_memory_gbs`) and point to the import
  step. Include the `oci compute image import` handoff (an optional `oci_core_image` import
  resource plus a clear note).
- Secrets live in **OCI Vault**; referenced by secret OCID and read via `oci_secrets_secretbundle`
  — never hard-coded and never emitted as plaintext outputs.
- Placeholders / API endpoints in code use **no `https://` scheme** (`<grid-master>/wapi/...`,
  `$GRID_MASTER`, `csp.infoblox.com`); real hosts are supplied at runtime.
