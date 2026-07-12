# Terraform — Infoblox DDI on a Google Cloud Landing Zone (Stage 2)

Starter Terraform module that adds an **Infoblox DDI + DNS-security layer** to the
**Shared VPC host project** of a Google Cloud landing zone. It is **Stage 2**: it
consumes the host-network outputs of the **landing-zone foundation (Stage 1)** —
**Terraform Example Foundation** or **Cloud Foundation Fabric / FAST** — and never
creates the org hierarchy, projects, org policy, or the Shared VPC itself.

> **Read [`../_module-contract.md`](../_module-contract.md) first.** It is the
> single source of truth for variable names, ports, IAM scopes, naming, outputs,
> and the GCC-Moderate boundary rule. This module conforms to it exactly.

## Boundary & compliance posture

Built for a **GCC-Moderate-equivalent posture on COMMERCIAL Google Cloud**. Data
residency / personnel controls on GCP are delivered by **Assured Workloads** folders
(a Stage-1 concern); this module targets commercial projects and does not switch
endpoints.

| `deployment_model` | Control plane | GCC-Moderate fit |
|---|---|---|
| `grid` (default) | vNIOS Grid **inside** the project/ATO boundary | Boundary-clean. Recommended. |
| `universal_ddi` | Infoblox Portal **SaaS, outside** the boundary (outbound 443 to `csp.infoblox.com`) | **Hard-fails** unless `acknowledge_saas_boundary = true` (points at the FedRAMP/authorization review). |

The hard-fail lives in `main.tf` as a `precondition` on `terraform_data.boundary_guard`.

## What it creates

- A dedicated **DDI subnet** in the Stage-1 host VPC (`ddi-subnet`), with Private
  Google Access + flow logs.
- **VPC firewall rules** scoped by the `ddi-member` network tag, exactly per
  contract §4 (default-deny in *and* out — GCP's implied egress is allow-all, so an
  explicit deny-all egress is added; mgmt/monitoring sources scoped to CIDR
  variables, never `0.0.0.0/0`; metadata-server `169.254.169.254` egress kept open).
- **`deployment_model = "grid"`** → one reserved internal IP +
  `google_compute_instance` per member (`member_count`, spread across `zones`),
  first-boot config via the vNIOS startup-script (temp license + admin password +
  grid-join params, all from Secret Manager). **One NIC per VPC.**
- **`deployment_model = "universal_ddi"`** → lightweight NIOS-X host instances + a
  `null_resource`/local-exec **Portal-enrollment handoff** (the API seam).
- A least-privilege **discovery service account** (`ddi-disco`, or an existing SA)
  with scoped `roles/compute.networkViewer` + `roles/dns.reader` (and opt-in
  `roles/dns.admin`) bindings (contract §5).
- Cloud DNS **inbound server policy**, **forwarding zones** (enterprise domains →
  Infoblox members), **peering zones** (spokes → hub), and Infoblox **conditional
  forwarders** (`*.googleapis.com` → Cloud DNS inbound IP) (contract §8).

## Files

| File | Purpose |
|---|---|
| `versions.tf` | Provider pins (`google`, `infobloxopen/infoblox`, `null`) + provider blocks. |
| `variables.tf` | Every contract §3 input + supporting inputs, with validation. |
| `main.tf` | Locals, labels (§6), DDI subnet, boundary hard-fail, member SA, Secret Manager reads. |
| `firewall.tf` | VPC firewall rules (§4), conditional by `deployment_model`, default-deny in+out. |
| `grid.tf` | vNIOS Grid path (`deployment_model=grid`). |
| `universal_ddi.tf` | Universal DDI (SaaS) path + Portal enrollment handoff. |
| `discovery.tf` | Discovery SA + least-privilege IAM (§5) + vDiscovery placeholder. |
| `dns.tf` | Inbound policy, forwarding/peering zones, Infoblox conditional forwarders (§8). |
| `outputs.tf` | Canonical outputs (§7). |
| `examples/hub-integration/` | Realistic call wired to landing-zone foundation remote state. |

## Inputs (canonical — contract §3)

| Name | Type | Default | Notes |
|---|---|---|---|
| `name_prefix` | string | `"ddi"` | Prefix for all resource names. |
| `region` | string | — | GCP region (commercial). |
| `environment` | string | `"prod"` | `dev`/`test`/`prod`. |
| `deployment_model` | string | `"grid"` | `grid` \| `universal_ddi`. |
| `acknowledge_saas_boundary` | bool | `false` | Must be `true` for `universal_ddi`. |
| `compliance_profile` | string | `"gcc-moderate"` | Labels + control mapping. |
| `host_project_id` | string | — | Stage-1 output (Shared VPC host project). |
| `shared_vpc_network` | string | — | Stage-1 output; DDI subnet created here. |
| `ddi_subnet_cidr` | string | — | Dedicated DDI subnet CIDR. |
| `member_count` | number | `2` | vNIOS/NIOS-X hosts; ≥2 for HA. |
| `zones` | list(string) | `["a","b"]` | Zone letters within `region`. |
| `machine_type` | string | — | N1 machine type; model/version dependent — do not hard-code. |
| `vnios_image` | object | — | `{project, family?, name?}` (Marketplace/custom image). |
| `secret_project_id` | string | — | Project holding Secret Manager secrets. |
| `discovery_identity_type` | string | `"service_account"` | `service_account` \| `existing_service_account`. |
| `spoke_networks` | list(string) | `[]` | Service-project VPCs to peer at the DDI resolver. |
| `labels` | map(string) | `{}` | Merged under module-managed labels. |

### Supporting inputs (not in §3, required by the implementation)

See `variables.tf` for full descriptions and defaults: `mgmt_source_ranges`,
`monitoring_source_ranges`, `dns_client_ranges`, `grid_peer_ranges`, `enable_ssh`,
`enable_dhcp` (default **off**), `enable_snmp`, `inbound_forwarding_enabled`,
`cloud_dns_inbound_ip`, `infoblox_forward_domains`, `enterprise_forward_domains`,
`ddi_anycast_vip`, `enable_spoke_dns_peering`, `discovered_project_ids`,
`dns_admin_project_ids`, `enable_record_write`, `existing_service_account_email`,
the Secret Manager `*_secret_id` set, `grid_name`, `grid_master_vip`,
`infoblox_portal_url`.

## Outputs (contract §7)

`ddi_anycast_vip`, `dns_server_ips` (list), `grid_master_ip` (grid only),
`discovery_service_account_email`, `ddi_subnet_id`.

## Example invocation

See [`examples/hub-integration/main.tf`](./examples/hub-integration/main.tf) for the
full version. Minimal shape:

```hcl
module "infoblox_ddi" {
  source = "../.." # or your module registry path

  region             = "us-central1"
  deployment_model   = "grid"          # boundary-clean default
  host_project_id    = data.terraform_remote_state.lz.outputs.host_project_id
  shared_vpc_network = data.terraform_remote_state.lz.outputs.shared_vpc_network
  ddi_subnet_cidr    = "10.10.4.0/27"

  machine_type = "n1-standard-4"        # confirm per NIOS model/version
  vnios_image  = { project = "<infoblox-image-project>", family = "<vnios-image-family>" }
  secret_project_id = data.terraform_remote_state.lz.outputs.host_project_id

  mgmt_source_ranges = ["10.10.0.0/24"]
  dns_client_ranges  = ["10.20.0.0/16"]
  grid_peer_ranges   = ["10.10.4.0/27", "192.168.100.0/24"]
  grid_master_vip    = "192.168.100.10"

  discovered_project_ids = ["<host-project-id>", "<service-project-id>"]
}
```

## Stage-1 → Stage-2 wiring

```
Stage 1  Foundation (Example Foundation / Fabric FAST)  ── outputs ──▶  Stage 2 (this module) ── outputs ──▶ Stage 3 (validation)
   shared_vpc_network                   shared_vpc_network         ddi_anycast_vip
   host_project_id                 ──▶  host_project_id            dns_server_ips
   region                               region                     grid_master_ip
   (existing Secret Manager,            secret_project_id +        discovery_service_account_email
    Cloud DNS inbound IP)               cloud_dns_inbound_ip        ddi_subnet_id
```

Consume Stage-1 outputs via `terraform_remote_state` (shown in the example) or pass
them as plain variables/tfvars if you don't share state across stages. Feed
`dns_server_ips` / `ddi_anycast_vip` into Stage-3 validation (resolve a record,
confirm discovery sync, conflict check).

## Before you deploy

- **Verify provider versions** in `versions.tf` against the registry.
- **Discover the image + machine type** (`gcloud compute images list
  --filter="family~infoblox OR name~vnios"`); never trust the example values.
- **Pre-create the Secret Manager secrets** named by the `*_secret_id` variables.
- **Scope every CIDR** — the module refuses `0.0.0.0/0` on management/DNS sources.
- For `universal_ddi`, complete the authorization review and set
  `acknowledge_saas_boundary = true`.

---

> ## ⚠️ Starter skeleton — not a certified production module
>
> This is a **coherent starter skeleton**, explicitly labeled as such. It encodes
> the right structure, variables, resources, and guardrails, but it is **not a
> certified production module**. Several resources are **illustrative** and marked
> in-code where real IDs, a `restapi`/CSP provider, an `import`, or a control-plane
> API handoff is required (notably: Infoblox conditional forwarders, vDiscovery
> jobs, and Universal DDI Portal enrollment). Pin your own provider/module
> versions, supply your image and machine type, and **test in a sandbox project
> first**.
