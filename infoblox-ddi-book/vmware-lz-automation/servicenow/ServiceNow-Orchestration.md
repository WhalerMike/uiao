# ServiceNow Orchestration — VMware (VCF / vSphere / NSX-T) DDI

> **Starter skeleton.** This folder is the **VMware-specific wiring** of the
> volume-level pattern in
> [`../../07-servicenow-orchestration.md`](../../07-servicenow-orchestration.md).
> Read that chapter first for the three-systems loop, the certified pieces (CPG
> Terraform Connector, Service Graph Connector for Infoblox, IntegrationHub REST,
> MID Server), and the GCC-Moderate governance frame. This file maps that pattern
> onto **this package's** Terraform module ([`../terraform`](../terraform)),
> validation scripts ([`../validation`](../validation)), and the
> [`_module-contract.md`](../_module-contract.md). It is illustrative-but-coherent,
> not a certified production configuration.

## Why VMware is the natural fit

VMware is the **on-prem / private-cloud anchor** of the volume, and that changes
the ServiceNow story in three concrete ways:

1. **The MID Server is in-boundary by construction.** The whole SDDC lives inside
   your datacenter / ATO boundary, so the MID Server that runs Terraform, the WAPI
   callouts, and the validation gates sits in the same boundary as the Grid Master
   it talks to. No hyperscaler egress question — the natural GCC-Moderate posture.
2. **DHCP is genuinely Infoblox's job here** (contract §4/§8, `enable_dhcp = true`
   by default), so DHCP scope/lease/reservation actions are first-class catalog
   items — see the fixed-address / range actions in
   [`integrationhub-actions.md`](./integrationhub-actions.md) §3.
3. **There is a provisioning-time IPAM path VMware has and the hyperscalers don't:**
   the **Infoblox IPAM plug-in for VMware Aria Automation**. ServiceNow can drive
   Terraform *or* call Aria, or go direct to WAPI — all three are described below.

---

## 1. Catalog → tfvars mapping

The Service Catalog item collects a governed request; the CPG Terraform Connector
turns the answers into the `*.tfvars` handed to [`../terraform`](../terraform). The
variable names below are the **exact** inputs from
[`../terraform/variables.tf`](../terraform/variables.tf) (canonical contract
variables + the supporting connection/DFW/secret inputs). Secrets are **never**
catalog fields — they resolve from the MID Server credential store / HashiCorp
Vault / CI at apply time (contract §9).

### Connection & placement (vCenter / NSX / cluster / datastore / port group)

| Catalog input | Terraform variable | Notes |
|---|---|---|
| Environment | `environment` | `dev` \| `test` \| `prod`; drives SoD routing + tags. |
| Compliance profile | `compliance_profile` | Default `fedramp-moderate`. |
| Name prefix | `name_prefix` | e.g. `ddi` → `ddi-vnios-h1`. |
| vCenter Server | `vsphere_server` | vCenter FQDN for the `vsphere` provider. |
| vSphere datacenter | `vsphere_datacenter` | Datacenter holding the mgmt/edge domain. |
| Compute cluster | `compute_cluster` | Target vSphere cluster (mgmt/edge domain). |
| Resource pool | `resource_pool` | Optional; null = cluster root pool. |
| Datastore | `datastore` | Member OS/DB disk datastore. |
| Management port group | `management_portgroup` | Management dvPortGroup for member vNICs. |
| ESXi hosts | `esxi_hosts` | List; members round-robined with anti-affinity. |
| NSX-T Manager | `nsx_manager` | NSX Manager FQDN for the `nsxt` provider. |
| vCenter user (deploy) | `vsphere_user` | Deploy-scope; **password is a secret, not a field**. |
| NSX-T user | `nsx_user` | Creates DFW / DNS forwarder / DHCP relay. |
| Allow unverified SSL | `allow_unverified_ssl` | Default **false**; keep false in prod. |

### DDI sizing, model & IP addressing

| Catalog input | Terraform variable | Notes |
|---|---|---|
| Deployment model | `deployment_model` | `grid` (default, in-boundary) \| `universal_ddi`. |
| Acknowledge SaaS boundary | `acknowledge_saas_boundary` | Must be `true` to allow `universal_ddi`; hard-fails otherwise. |
| Member count | `member_count` | 1–8; ≥2 for HA. |
| DDI management network CIDR | `ddi_mgmt_network_cidr` | Maps from Azure `ddi_subnet_address_prefix`; DFW scope + static-IP sanity. |
| Member static IPs | `member_ip_addresses` | One per member, inside the mgmt CIDR (OVF vApp props). |
| Member netmask / gateway | `member_netmask` / `member_gateway` | Member mgmt network. |
| Anycast VIP | `ddi_anycast_vip` | DNS/DHCP/forwarder service VIP; Stage-3 `DDI_VIP`. |
| vNIOS appliance model | `vnios_appliance_model` | Model / OVF deployment option (do not hard-code). |
| vNIOS OVA source | `vnios_ovf` | Content-library item **or** local `.ova` path. |
| CPU / memory / disk overrides | `vnios_num_cpus` / `vnios_memory_mb` / `vnios_disk_gb` | Model-dependent; leave null for OVA default. |
| Thin provisioning | `disk_thin_provisioned` | Default false (thick eager-zeroed for DB perf). |
| Tags | `tags` | Merged with module-managed vSphere tags. |

### DFW / segment source CIDRs (contract §4 — never `0.0.0.0/0`)

| Catalog input | Terraform variable | Notes |
|---|---|---|
| Management / WAPI source CIDRs | `mgmt_source_cidrs` | Admins, Aria plug-in, CNA; **non-empty, never `0.0.0.0/0`**. |
| DNS client CIDRs | `dns_client_cidrs` | Tenant segments + NSX forwarder ranges (53 tcp/udp). |
| DHCP relay source CIDRs | `dhcp_relay_cidrs` | NSX DHCP relay sources (67–68/udp); used when `enable_dhcp`. |
| Grid peer CIDRs | `grid_peer_cidrs` | Grid members/GM (1194/udp + 2114/tcp); `grid` model. |
| Monitoring source CIDRs | `monitoring_source_cidrs` | SNMP 161/udp when `enable_snmp`. |
| Enable DHCP | `enable_dhcp` | **ON by default** on VMware. |
| Enable SNMP / SSH / NSX DNS forwarder | `enable_snmp` / `enable_ssh` / `enable_nsx_dns_forwarder` | Optional toggles. |
| Workload Tier-1 IDs | `workload_tier1_ids` | Tier-1 gateways whose DNS forwarder points at the DDI VIP. |

### DNS integration & discovery

| Catalog input | Terraform variable | Notes |
|---|---|---|
| AD DNS servers | `ad_dns_servers` | Conditional-forward targets (contract §8). |
| AD forward domains | `ad_forward_domains` | e.g. `corp.example` + reverse zones. |
| Discovery identity type | `discovery_identity_type` | Only `vcenter_service_account` on VMware. |
| Manage discovery role | `manage_discovery_role` | Optionally create the read-only vSphere role. |
| Discovery vCenter / NSX user | `discovery_vcenter_user` / `discovery_nsx_user` | Least-privilege read-only identities (contract §5). |
| Grid name / Grid Master VIP | `grid_name` / `grid_master_vip` | `grid` model join parameters. |
| Portal URL | `infoblox_portal_url` | `universal_ddi` enrollment host. |

### Secrets — resolved from Vault / CI, **never catalog fields** (contract §9)

`vsphere_password`, `nsx_password`, `admin_password`, `temp_license`,
`grid_shared_secret` (grid), `saas_join_token` (universal_ddi). On VMware there is
no cloud Key Vault; these sensitive Terraform variables are injected at apply time
from **HashiCorp Vault or the CI secret store** and carried into OVF vApp
properties / Portal enrollment. They are never emitted as outputs.

---

## 2. The Flow Designer flow

![VMware DDI ServiceNow closed loop: a Service Catalog request is approved with a separation-of-duties gate in Flow Designer, the CPG Terraform Connector plans and applies this package's terraform module on an in-boundary MID Server (optionally driving Aria Automation's Infoblox IPAM plug-in for provisioning-time allocation), IntegrationHub REST calls the Infoblox WAPI for IPAM/DNS/DHCP, the MID Server runs the three validation scripts as a gate, the Service Graph Connector for Infoblox syncs IPAM truth into the CMDB, and the request closes with a full audit trail — a non-zero validation gate returns to approval](../figs/vmware-sn-01-catalog-flow.png)

The numbered loop (matching the figure):

1. **Intake — Service Catalog item.** The requester fills the form in §1; the CPG
   Terraform Connector renders it to `*.tfvars` for [`../terraform`](../terraform).
2. **Approval + SoD gate — Flow Designer.** Environment-based routing; the approver
   is not the requester (AC-5/AC-6). A speculative `terraform plan` is attached for
   review (the CPG native plan→approve→apply pattern).
3. **CPG Terraform apply — in-boundary MID Server.** On approval the MID Server runs
   `terraform apply` against [`../terraform`](../terraform). Optionally this step
   drives **Aria Automation** so its **Infoblox IPAM plug-in** does provisioning-time
   allocation (see §3); otherwise IPAM is done directly in step 4.
4. **IntegrationHub IPAM/DNS/DHCP.** REST steps call the Infoblox WAPI for
   next-available-IP, A/PTR, and (VMware-specific) fixed-address / DHCP reservation
   — bodies in [`integrationhub-actions.md`](./integrationhub-actions.md).
5. **MID Server validation gate.** [`midserver-validate.sh`](./midserver-validate.sh)
   runs the three [`../validation`](../validation) scripts, captures exit codes, and
   emits one JSON result. **Non-zero fails the change and returns to approval** (the
   dotted path in the figure); the JSON is posted to work-notes.
6. **Service Graph Connector → CMDB.** The Infoblox Service Graph Connector reconciles
   IPAM/DNS truth into the CMDB (§4), so ServiceNow reflects reality.
7. **Close + audit trail.** The change closes with an immutable record
   (AU-2/AU-6/AU-12, CM-3/CM-5). Retirement is the mirror image: `terraform destroy`
   + IPAM reclaim + record/fixed-address delete (see the delete action).

---

## 3. Provisioning-time IPAM: Aria plug-in vs. direct WAPI (both supported)

VMware uniquely offers **two** places the IP can be allocated, and ServiceNow can
use either — or both:

- **Direct WAPI from IntegrationHub (default here).** The flow allocates and
  registers via REST (step 4) straight to the Grid. Simplest, keeps ServiceNow as
  the single orchestrator, works identically to the hyperscaler packages. See
  [`integrationhub-actions.md`](./integrationhub-actions.md).
- **Via the Infoblox IPAM plug-in for VMware Aria Automation** (complement).
  Registered in Aria as an **external IPAM provider**, the plug-in allocates the
  next free IP and writes A/PTR at *blueprint deploy time*, EA-steered by
  environment / tenant / zone, and reclaims on VM delete. This is the path drawn in
  [`../figs/vmware-02-aria-ipam-provisioning.mmd`](../figs/vmware-02-aria-ipam-provisioning.mmd).
  ServiceNow drives it by calling the **Aria Automation** catalog/blueprint API from
  the flow instead of (or in addition to) the direct WAPI step — governance and
  approval stay in ServiceNow, allocation moves to Aria/plug-in.

Choose direct WAPI when ServiceNow owns the whole lifecycle; add the Aria plug-in
when tenants also self-serve VMs through Aria and you want IPAM enforced at deploy
time regardless of entry point.

---

## 4. IntegrationHub REST (summary)

The active IPAM/DNS/DHCP calls the flow makes, all over the in-boundary MID Server.
Full method/path/JSON bodies (with `<grid-master>` / `$GRID_MASTER` placeholders,
**no scheme**) live in [`integrationhub-actions.md`](./integrationhub-actions.md):

| Action | Method | WAPI object |
|---|---|---|
| Next-available-IP | `POST` | `network?_function=next_available_ip` |
| Create A / PTR (or host) | `POST` | `record:a`, `record:ptr`, `record:host` |
| Fixed-address / DHCP reservation | `POST` | `fixedaddress` (VMware — DHCP is Infoblox's job) |
| Create DHCP range | `POST` | `range` |
| Delete (reclaim) | `DELETE` | `$OBJECT_REF` |

For `deployment_model = universal_ddi`, each has a Universal DDI / Portal REST
equivalent (also in that file) — but that endpoint is **outside** the boundary and
is gated on `acknowledge_saas_boundary` (see §6).

---

## 5. Service Graph Connector — CMDB mapping

The **Service Graph Connector for Infoblox** imports IPAM into the CMDB so the
network CIs reflect Infoblox truth rather than a guess. VMware-relevant mapping:

| Infoblox object | CMDB class | Notes |
|---|---|---|
| `network` (IPAM subnet) | `cmdb_ci_ip_network` / `cmdb_ci_ip_network_subnet` | Includes CNA-discovered vSphere segment CIDRs. |
| IP address / `fixedaddress` / lease | `cmdb_ci_ip_address` | Static + DHCP reservations (DHCP is authoritative here). |
| DNS zone / `record:*` | `cmdb_ci_dns_name` | Forward/reverse records created by the flow. |
| Extensible attributes (env/tenant/zone) | CI attributes / relationships | The same EAs that steer the Aria plug-in. |
| Discovered vSphere VM ↔ IP | relationship to `cmdb_ci_vmware_instance` | Ties the tenant VM (`ddi_member_vm_ids` / discovered VMs) to its allocation. |

Reconcile the connector import against the `ipam-conflict-check.sh` gate: the CMDB
should never show an overlap the validation gate would have failed on.

---

## 6. GCC-Moderate notes

- **MID Server in-boundary — the natural fit.** Because VMware is the on-prem anchor,
  the MID Server, the Grid Master, and the SDDC are already in the same ATO boundary;
  the execution + credential path never leaves it. Use a **FedRAMP-authorized
  ServiceNow (GovCloud) instance** for the system of engagement.
- **Secrets in Vault / CI, never a cloud KMS.** There is no Key Vault on VMware
  (contract §9). `vsphere_password`, `nsx_password`, `admin_password`,
  `grid_shared_secret`, `saas_join_token`, WAPI creds — all injected at apply/call
  time from HashiCorp Vault or the CI secret store, never catalog fields, never
  outputs.
- **DHCP is Infoblox's job → DHCP as a catalog action.** DHCP scope/lease/reservation
  is in-scope for ServiceNow here (unlike the hyperscalers): a "reserve DHCP address"
  or "create DHCP range" catalog action maps to `fixedaddress` / `range`
  (see [`integrationhub-actions.md`](./integrationhub-actions.md) §3), gated by
  `ipam-conflict-check.sh` before the NSX DHCP relay is pointed at the scope.
- **Universal DDI SaaS caveat still holds.** `deployment_model = grid` keeps every
  WAPI call in-boundary. `universal_ddi` reaches the Infoblox Portal (CSP) over
  outbound 443 **outside** the boundary; the flow must honour
  `acknowledge_saas_boundary = true` (which the module hard-fails without), exactly
  as the Terraform plan and the validation scripts do.
- **Control-family mapping** (as in the parent chapter): catalog approval + SoD →
  **AC-5/AC-6**; change record + immutable audit → **AU-2/AU-6/AU-12**, **CM-3/CM-5**;
  validation gates → **CM-6**; reclaim-on-delete → **CM-8**.

---

## Files in this folder

| File | What it is |
|---|---|
| `ServiceNow-Orchestration.md` | This file — VMware catalog→tfvars mapping, Flow Designer flow, Aria vs. WAPI, SGC CMDB mapping, GCC-Moderate notes. |
| [`midserver-validate.sh`](./midserver-validate.sh) | MID Server gate: runs the three `../validation/*.sh`, captures exit codes, emits one JSON result, non-zero on any failure. |
| [`integrationhub-actions.md`](./integrationhub-actions.md) | Infoblox WAPI / Universal DDI REST bodies for next-available-IP, A/PTR, fixed-address/DHCP, delete. |
| [`../figs/vmware-sn-01-catalog-flow.mmd`](../figs/vmware-sn-01-catalog-flow.mmd) | Mermaid source for the closed-loop figure above (rendered to `.png` by `render-figs.sh`). |
