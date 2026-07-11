# Terraform — Infoblox DDI on an OCI Landing Zone (Stage 2)

Starter Terraform module that adds an **Infoblox DDI + DNS-security layer** to the
**hub VCN** of an OCI landing zone (the connectivity compartment of the CIS / Core
Landing Zone). It is **Stage 2**: it consumes the hub-network outputs of the **CIS
Landing Zone (Stage 1)** and never creates the tenancy, compartments, IAM
foundations, or the hub network fabric.

> **Read [`../_module-contract.md`](../_module-contract.md) first.** It is the
> single source of truth for variable names, ports, IAM scopes, naming, outputs,
> and the FedRAMP-Moderate boundary rule. This module conforms to it exactly.

> ### Terraform is the only path (and OCI's story is thinner — candidly)
> OCI's only first-class IaC is Terraform (OCI **Resource Manager** *is* Terraform),
> so there is no parallel Bicep-style path. Two OCI realities shape this module and
> are stated plainly:
> - **No Marketplace vNIOS listing** — you deploy by **custom-image import** from
>   Object Storage (`vnios_image_ocid`, or `import_image=true` + `image_source_uri`).
> - **No native discovery connector** — OCI→IPAM sync is **API/SDK/Terraform-driven**;
>   `discovery.tf` grants the identity and marks the sync as an explicit handoff.

## Boundary & compliance posture

Built for a **FedRAMP Moderate-equivalent posture on COMMERCIAL OCI (the OC1 realm,
`*.oraclecloud.com`)** — **not** OCI Government (OC2/OC3) or National-Security realms.

| `deployment_model` | Control plane | FedRAMP-Moderate fit |
|---|---|---|
| `grid` (default) | vNIOS Grid **inside** the tenancy/ATO boundary | Boundary-clean. Recommended. |
| `universal_ddi` | Infoblox Portal **SaaS, outside** the boundary (outbound 443) | **Hard-fails** unless `acknowledge_saas_boundary = true` (points at the authorization review). |

The hard-fail lives in `main.tf` as a `precondition` on `terraform_data.boundary_guard`.

## What it creates

- A dedicated **DDI subnet** in the Stage-1 hub VCN (`ddi-subnet`, private).
- **NSG or Security List** on that subnet (per `security_model`), exactly per
  contract §4 — OCI's default-deny stance means only the allow rules are declared;
  mgmt/monitoring/client sources scoped to CIDR variables, never `0.0.0.0/0`.
- **`deployment_model = "grid"`** → optional **custom-image import**
  (`oci_core_image`), one **`oci_core_instance`** per member (`member_count`, spread
  across `availability_domains` / `fault_domains`), first-boot config via metadata
  `user_data` (temp license + admin password + grid-join params, all from OCI Vault),
  optional vNIOS data block volume.
- **`deployment_model = "universal_ddi"`** → NIOS-X host instances + a
  `null_resource`/local-exec **Portal-enrollment handoff** (the API seam).
- A least-privilege **discovery identity** — an **instance-principal dynamic group**
  (preferred) or an **IAM user + group** — with a scoped read policy
  (`read virtual-network-family` / `read dns` / `inspect tag-namespaces`), `manage dns`
  only when `enable_record_write` (contract §5).
- **OCI resolver endpoints** (LISTENING + FORWARDING) and forwarding rules, plus
  Infoblox **conditional forwarders** (`infoblox_zone_forward`) for OCI-owned names
  → the OCI resolver LISTENING endpoint (contract §8).

## Files

| File | Purpose |
|---|---|
| `versions.tf` | Provider pins (`oracle/oci`, `infobloxopen/infoblox`, `tls`, `null`) + provider blocks. |
| `variables.tf` | Every contract §3 input + supporting inputs, with validation. |
| `main.tf` | Locals, freeform tags (§6), DDI subnet, boundary hard-fail, OCI Vault secret reads. |
| `security.tf` | NSG **or** Security List + rules (§4), conditional by `deployment_model`. |
| `grid.tf` | vNIOS Grid path + custom-image import (`deployment_model=grid`). |
| `universal_ddi.tf` | Universal DDI (SaaS) path + Portal enrollment handoff. |
| `discovery.tf` | Discovery identity (dynamic group / IAM user) + least-privilege policy (§5) + API/SDK sync handoff. |
| `dns.tf` | OCI resolver endpoints + forwarding rules + Infoblox conditional forwarders (§8). |
| `outputs.tf` | Canonical outputs (§7). |
| `examples/hub-integration/` | Realistic call wired to CIS Landing Zone remote state. |

## Inputs (canonical — contract §3)

| Name | Type | Default | Notes |
|---|---|---|---|
| `name_prefix` | string | `"ddi"` | Prefix for all resource names. |
| `region` | string | — | OCI region (commercial OC1). |
| `environment` | string | `"prod"` | `dev`/`test`/`prod`. |
| `deployment_model` | string | `"grid"` | `grid` \| `universal_ddi`. |
| `acknowledge_saas_boundary` | bool | `false` | Must be `true` for `universal_ddi`. |
| `compliance_profile` | string | `"fedramp-moderate"` | Tags + control mapping. |
| `tenancy_ocid` | string | — | Root compartment; for IAM identity/policy. |
| `network_compartment_ocid` | string | — | Stage-1 output; where DDI resources land. |
| `hub_vcn_ocid` | string | — | Stage-1 output; DDI subnet created here. |
| `drg_ocid` | string | `null` | Hub-spoke DRG (Stage-1) reachability reference. |
| `ddi_subnet_cidr` | string | — | Dedicated DDI subnet CIDR. |
| `member_count` | number | `2` | vNIOS/UDDI hosts; ≥2 for HA. |
| `availability_domains` | list(string) | — | ADs to spread members across. |
| `fault_domains` | list(string) | `["FAULT-DOMAIN-1","FAULT-DOMAIN-2"]` | Spread members across FDs. |
| `vnios_shape` / `vnios_ocpus` / `vnios_memory_gbs` | string/number | — / `4` / `32` | Flexible shape — model/region-dependent. |
| `vnios_image_ocid` | string | `null` | Imported custom image OCID (no Marketplace). |
| `vault_ocid` | string | — | Existing OCI Vault for secrets. |
| `discovery_identity_type` | string | `"instance_principal"` | `instance_principal` \| `api_key_user`. |
| `spoke_vcn_ocids` | list(string) | `[]` | Spokes whose resolver forwards to the DDI VIP. |
| `freeform_tags` / `defined_tags` | map(string) | `{}` | Merged under module-managed tags. |

### Supporting inputs (not in §3, required by the implementation)

Scoping/behaviour knobs — see `variables.tf` for full descriptions and defaults:
`security_model` (`nsg`\|`security_list`), `mgmt_source_cidrs`, `monitoring_source_cidrs`,
`dns_client_cidrs`, `grid_peer_cidrs`, `enable_ssh`, `enable_dhcp` (default **off**),
`enable_snmp`, `manage_resolver_endpoints`, `hub_resolver_ocid`,
`resolver_endpoint_subnet_ocid`, `oci_listening_endpoint_ip`, `oci_forward_domains`,
`enterprise_forward_domains`, `ddi_anycast_vip`, `enable_spoke_dns_write`,
`discovered_compartment_ocids`, `enable_record_write`, `discovery_user_ocid`,
`discovery_dynamic_group_matching_rule`, the OCI Vault `*_secret_ocid` set,
`grid_name`, `grid_master_vip`, `infoblox_portal_url`, `import_image`,
`image_source_uri`, `data_volume_size_gbs`, `admin_username`.

## Outputs (contract §7)

`ddi_anycast_vip`, `dns_server_ips` (list), `grid_master_ip` (grid only),
`discovery_identity_id`, `ddi_subnet_id`.

## Example invocation

See [`examples/hub-integration/main.tf`](./examples/hub-integration/main.tf) for
the full version. Minimal shape:

```hcl
module "infoblox_ddi" {
  source = "../.." # or your module registry path

  region                   = "us-ashburn-1"
  deployment_model         = "grid"          # boundary-clean default
  tenancy_ocid             = var.tenancy_ocid
  network_compartment_ocid = data.terraform_remote_state.lz.outputs.network_compartment_ocid
  hub_vcn_ocid             = data.terraform_remote_state.lz.outputs.hub_vcn_ocid
  ddi_subnet_cidr          = "10.10.4.0/27"

  vnios_shape      = "VM.Standard.E4.Flex"   # confirm per NIOS model/region
  vnios_ocpus      = 4
  vnios_memory_gbs = 32
  vnios_image_ocid = "ocid1.image.oc1..<your-imported-custom-image>"
  vault_ocid       = data.terraform_remote_state.lz.outputs.vault_ocid

  admin_password_secret_ocid = "ocid1.vaultsecret.oc1..<admin-pw>"
  temp_license_secret_ocid   = "ocid1.vaultsecret.oc1..<temp-license>"
  grid_shared_secret_ocid    = "ocid1.vaultsecret.oc1..<grid-secret>"

  availability_domains = ["Uocm:US-ASHBURN-AD-1", "Uocm:US-ASHBURN-AD-2"]
  mgmt_source_cidrs    = ["10.10.0.0/24"]
  dns_client_cidrs     = ["10.20.0.0/16"]
  grid_peer_cidrs      = ["10.10.4.0/27", "192.168.100.0/24"]
  grid_master_vip      = "192.168.100.10"

  discovered_compartment_ocids = ["ocid1.compartment.oc1..<spoke-net>"]
}
```

## Stage-1 → Stage-2 wiring

```
Stage 1  CIS Landing Zone (Terraform)  ── outputs ──▶  Stage 2 (this module) ── outputs ──▶ Stage 3
   hub_vcn_ocid                          hub_vcn_ocid          ddi_anycast_vip
   network_compartment_ocid         ──▶  network_compartment_ocid   dns_server_ips
   drg_ocid                              drg_ocid              grid_master_ip
   vault_ocid                            vault_ocid            discovery_identity_id
   (hub resolver OCID / subnet)          hub_resolver_ocid     ddi_subnet_id
```

Consume Stage-1 outputs via `terraform_remote_state` (shown in the example) or
pass them as plain variables/tfvars. Feed `dns_server_ips` / `ddi_anycast_vip` /
`grid_master_ip` into Stage-3 validation.

## Before you deploy

- **Verify provider versions** in `versions.tf` against the registry.
- **Import the vNIOS custom image** (`oci compute image import …`) and supply
  `vnios_image_ocid`, or set `import_image=true` + `image_source_uri`. Never invent
  an image OCID.
- **Choose a flexible shape + OCPU/memory** per the vNIOS model spec — do not
  hard-code; the module has no default `vnios_shape`.
- **Pre-create the OCI Vault secrets** and pass their OCIDs.
- **Scope every CIDR** — the module refuses `0.0.0.0/0` on management/client/grid
  sources.
- For `universal_ddi`, complete the authorization review and set
  `acknowledge_saas_boundary = true`.

---

> ## ⚠️ Starter skeleton — not a certified production module
>
> This is a **coherent starter skeleton**, explicitly labeled as such. It encodes
> the right structure, variables, resources, and guardrails, but is **not a
> certified production module**. Several resources are **illustrative** and marked
> in-code where real OCIDs, a lookup, or a control-plane API/SDK handoff is required
> (notably: the custom-image import, Infoblox conditional forwarders, the OCI→IPAM
> discovery sync, spoke resolver wiring, and Universal DDI Portal enrollment). Pin
> your own provider versions, supply your imported image and shape, and **test in a
> sandbox landing zone first**.
