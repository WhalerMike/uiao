# Shared Module Contract — Google Cloud LZ + Infoblox DDI

> **Purpose.** This file is the single source of truth that keeps the Terraform module,
> the pipelines, the validation scripts, and the written guide **consistent** — identical
> variable names, ports, IAM scopes, resource-naming, and architectural decisions.
> Every artifact in `gcp-lz-automation/` MUST conform to this contract. If a value is
> version/region-dependent, the artifact says so rather than hard-coding a guess.
>
> This is the **Google Cloud** sibling of `azure-alz-automation/`. It mirrors that
> package one-for-one (same canonical variables, same boundary rule, same port set),
> adapted to Google Cloud primitives: **Shared VPC host project** instead of the Azure
> Connectivity hub VNet, a **service account** instead of a managed identity, **VPC
> firewall rules** instead of an NSG, **Secret Manager** instead of Key Vault, and
> **Cloud DNS server policies / forwarding zones** instead of the Azure DNS Private
> Resolver. Terraform-only — there is no Bicep/Deployment-Manager sibling.

## 1. Boundary & compliance profile (fixed for this deliverable)

- **Cloud boundary:** **commercial Google Cloud** (`googleapis.com`, `csp.infoblox.com`).
  This matches a **GCC-Moderate-equivalent operating posture** (FedRAMP Moderate controls)
  running on the commercial cloud. For data-residency / personnel controls, Google Cloud's
  mechanism is **Assured Workloads** folders — noted where relevant, but this package
  targets commercial projects and does not itself provision Assured Workloads.
- **Compliance profile:** `gcc-moderate` (FedRAMP Moderate-equivalent controls). Artifacts
  carry a `compliance_profile` variable defaulting to `"gcc-moderate"`.
- **Control-plane boundary rule (critical):**
  - `deployment_model = "grid"` → the vNIOS Grid control plane runs **inside the project /
    ATO boundary**. Boundary-clean; the default for GCC-Moderate.
  - `deployment_model = "universal_ddi"` → the Infoblox Portal (SaaS) control plane is
    **outside** the ATO boundary and requires outbound `443` to the Portal
    (`csp.infoblox.com`). Artifacts MUST emit a boundary/authorization caveat and gate this
    path behind an explicit `acknowledge_saas_boundary = true` variable (default `false`,
    which hard-fails the plan with a message pointing to the authorization review).

## 2. Layering model (how it sits on the Google Cloud landing zone)

Three stages; this module is **Stage 2**. It never creates the org hierarchy, projects,
org policy, or the Shared VPC itself — those are **Stage 1**, the Google Cloud landing-zone
foundation (**Terraform Example Foundation** or **Cloud Foundation Fabric / FAST**).

```
Stage 1  Google Cloud landing zone (Terraform Example Foundation / Fabric FAST)
         → outputs: host_project_id, shared_vpc_network (self-link/name), region,
           logging_project_id (optional), cloud_dns_inbound_ip (optional)
                     │  (remote state / module outputs consumed as inputs)
                     ▼
Stage 2  THIS MODULE — Infoblox DDI extension in the Shared VPC host project
                     │  outputs: ddi_anycast_vip, dns_server_ips, grid_master_ip,
                     ▼            discovery_service_account_email, ddi_subnet_id
Stage 3  Validation (pipeline gates: resolve a record, confirm discovery sync, conflict check)
```

## 3. Canonical input variables (the module's public surface)

Names mirror the Azure package; where an Azure name has no natural GCP meaning it is mapped
to the GCP primitive (noted in the last column).

| Variable | Type | Default | Notes (Azure analog) |
|---|---|---|---|
| `name_prefix` | string | `"ddi"` | Prefix for all resource names. |
| `region` | string | — | GCP region (commercial). *(location)* |
| `environment` | string | `"prod"` | `dev`/`test`/`prod`; feeds labels + sizing. |
| `deployment_model` | string | `"grid"` | `grid` \| `universal_ddi`. |
| `acknowledge_saas_boundary` | bool | `false` | Must be `true` to allow `universal_ddi` (see §1). |
| `compliance_profile` | string | `"gcc-moderate"` | Drives labels + control mapping. |
| `host_project_id` | string | — | Shared VPC **host project**. *(hub_resource_group_name)* |
| `shared_vpc_network` | string | — | Host VPC network name or self-link; the DDI subnet is created in it. *(hub_vnet_id)* |
| `ddi_subnet_cidr` | string | — | Dedicated DDI subnet CIDR (created by this module in the host VPC). *(ddi_subnet_address_prefix)* |
| `member_count` | number | `2` | vNIOS members / NIOS-X hosts; ≥2 for HA. |
| `zones` | list(string) | `["a","b"]` | Zone **letters** within `region`; members round-robin over `${region}-${letter}`. *(availability_zones)* |
| `machine_type` | string | — | GCP machine type (N1 family); model/NIOS-version dependent — do not hard-code. *(vnios_vm_sku)* |
| `vnios_image` | object | — | Compute image reference `{project, family?, name?}` (Marketplace/custom image). *(vnios_image)* |
| `secret_project_id` | string | — | Project holding the Secret Manager secrets. *(key_vault_id)* |
| `discovery_identity_type` | string | `"service_account"` | `service_account` (module creates one) \| `existing_service_account`. *(discovery_identity_type)* |
| `spoke_networks` | list(string) | `[]` | Service-project VPC self-links to point at the DDI resolver (via peering zones / server policy). *(spoke_vnet_ids)* |
| `labels` | map(string) | `{}` | Merged with module-managed labels. *(tags)* |

## 4. Ports (VPC firewall rules the module creates for the DDI members)

Firewall rules are scoped by a **network tag** on the member instances
(`${name_prefix}-member`) — the GCP analog of scoping to a subnet. Sources are explicit CIDR
variables, **never `0.0.0.0/0`**.

| Service | Port | Proto | Direction | When |
|---|---|---|---|---|
| DNS | 53 | tcp+udp | ingress from clients/on-prem | always |
| DHCP | 67–68 | udp | ingress | only if module serves DHCP (GCP DHCP is platform-managed; off by default) |
| Grid VPN | 1194 | udp | in/out to Grid members/GM | `deployment_model=grid` |
| Grid comms | 2114 | tcp | in/out | `deployment_model=grid` |
| NTP | 123 | udp | egress | always |
| HTTPS mgmt | 443 | tcp | ingress (mgmt CIDR) | always |
| Portal sync | 443 | tcp | **egress to Infoblox Portal** | `deployment_model=universal_ddi` only |
| SNMP | 161 | udp | ingress (monitoring CIDR) | optional |

Default-deny everything else: GCP already denies ingress by default, but its **implied
egress is allow-all**, so the module adds an explicit **deny-all egress** rule (high priority
number = low precedence) plus a low-precedence deny-all ingress for auditability. Two GCP
facts the rules account for:

- **Metadata server `169.254.169.254`.** VMs resolve DNS via the metadata resolver, which
  fronts Cloud DNS. The Infoblox members themselves need egress to `169.254.169.254`
  (metadata + platform DNS); the module keeps that egress open even under default-deny.
- **One NIC per VPC.** A GCP network interface binds to exactly one VPC network. A member
  serving a single Shared VPC uses **one NIC**; a member that must touch two VPCs uses **two
  NICs on two VPCs**. The firewall/instances honor this (single-NIC by default).

## 5. Least-privilege discovery identity (GCP → Infoblox IPAM sync)

The discovery credential is a **service account** (`${name_prefix}-disco`). IAM role bindings
are scoped to the projects/folder/org actually discovered:

| Role | Scope | Why |
|---|---|---|
| `roles/compute.networkViewer` | discovered project(s) | enumerate VPCs, subnets, instances, addresses |
| `roles/dns.reader` | discovered project(s) | read Cloud DNS zones/records for DNS discovery |
| `roles/dns.admin` | project(s) holding zones | **only if** Infoblox writes records into Cloud DNS (opt-in) |

No `roles/owner`, no `roles/editor`, no broad `roles/viewer`. Prefer a **custom role** scoped
to the exact `compute.networks.*` / `compute.subnetworks.*` / `compute.instances.*` /
`compute.addresses.*` (list/get) and `dns.*.list/get` permissions over the two predefined
read roles; the module uses the two predefined roles for clarity and notes the custom-role
option. In a Shared VPC, grant read on the **host project** (shared networks/subnets) *and*
each **service project** you want VM-level discovery for. Record-write role is opt-in.

## 6. Resource-naming convention

`${name_prefix}-<role>-<zone/index>` e.g. `ddi-member-a`, `ddi-fw-dns`, `ddi-subnet`,
`ddi-disco` (service account). All resources carry labels: `workload=infoblox-ddi`,
`layer=connectivity-ddi`, `compliance_profile=<value>`, `deployment_model=<value>`,
`managed_by=terraform`, `environment=<value>`. (GCP label values are lowercase; the module
normalizes them.)

## 7. Canonical outputs

`ddi_anycast_vip`, `dns_server_ips` (list), `grid_master_ip` (grid only),
`discovery_service_account_email` *(Azure `discovery_identity_id`)*, `ddi_subnet_id`.

## 8. DNS integration contract

Cloud DNS name resolution is wired in **both directions** — they are independent VPC-level
constructs (03-gcp.md §7):

- **Inbound (Cloud DNS reachable from Infoblox):** an **inbound DNS server policy**
  (`google_dns_policy` with `enable_inbound_forwarding`) on the Shared VPC network. Cloud DNS
  then allocates **inbound forwarder IPs** from the VPC's subnet ranges; the Infoblox members
  (and on-prem) target those IPs to resolve Cloud DNS private-zone / `*.googleapis.com` names.
- **Outbound (VMs resolve via Infoblox):** **Cloud DNS forwarding zones**
  (`google_dns_managed_zone`, `forwarding` type) for enterprise/on-prem domains (e.g.
  `corp.example.com.`, reverse zones) whose `target_name_servers` are the Infoblox member IPs
  — or, more broadly, an **outbound server policy with alternative name servers**. For Type-2
  private routing to members reached over Interconnect/HA VPN, the VPC must return-route
  **`35.199.192.0/19`**.
- **Split-horizon & scale-out:** service-project VPCs consume the hub's resolution via
  **peering zones** (`google_dns_managed_zone`, `peering` type) so every project funnels
  corp/on-prem queries through the hub to the Infoblox members. On the Infoblox side,
  matching **conditional forwarders** (`infoblox_zone_forward`) send `*.googleapis.com` /
  Cloud DNS private names back to the Cloud DNS inbound forwarder IPs.

## 9. Style for code artifacts

- Terraform: pin `hashicorp/google` and `infobloxopen/infoblox` providers in `versions.tf`;
  every variable documented; skeleton is **illustrative-but-coherent** (labeled as a starter,
  not a certified production module). Guard the SaaS path per §1.
- Where no first-class Terraform-native Infoblox resource exists (vDiscovery jobs, Portal
  enrollment), the module uses a clearly-marked **API/Ansible handoff** (`null_resource` /
  local-exec seam), never a silent guess.
- Never invent Marketplace image names, machine types, or Portal endpoints — parameterize and
  point at `gcloud compute images list` / the deployment guide.
</invoke>
