# VMware (VCF / vSphere / NSX-T) + Infoblox DDI — Step-by-Step Deployment Runbook

> **Companion to** [`VMware-LZ-Infoblox-DDI-Automation-Guide.md`](./VMware-LZ-Infoblox-DDI-Automation-Guide.md).
> That guide explains *why* the architecture is shaped the way it is; this runbook
> is the **"do exactly this, then this"** operational sequence that deploys it with
> the IaC package in this directory. Every command, variable name, resource name,
> port, and output below is taken from the real module and its
> [`_module-contract.md`](./_module-contract.md) — nothing is invented. Where a
> value is genuinely environment-specific (OVA build, appliance model, vCPU/RAM,
> CIDR) the runbook says **"supply your own"** rather than guessing.
>
> **Posture (fixed):** FedRAMP-Moderate on a **self-contained VCF private cloud**
> — the Grid runs inside the SDDC (air-gap-friendly). There is no cloud KMS and no
> cloud OIDC; secrets come from **HashiCorp Vault / CI**.
>
> **Default path:** `deployment_model = "grid"` (vNIOS Grid, control plane inside
> the SDDC/ATO boundary). The `universal_ddi` (Infoblox Portal / SaaS) path is
> shown in clearly-marked **⚠ UNIVERSAL DDI** callout boxes and always honors the
> `acknowledge_saas_boundary` guard.
>
> **The VMware difference:** **DHCP is genuinely Infoblox's job** — `enable_dhcp`
> defaults **true** and the module wires an NSX DHCP relay to the members.
>
> **Status of the IaC:** a coherent starter skeleton — structurally correct and
> guardrail-bearing, *not* a certified production module. Pin your own versions,
> supply your own OVA/model, and test in a sandbox vSphere cluster first.

---

## Prerequisites checklist

Confirm **all** of these before Phase 0. Boxes map to the phases that consume them.

- [ ] **Stage-1 SDDC already deployed.** A VMware Cloud Foundation instance (vCenter,
      NSX Manager, SDDC Manager) with a **management (or edge/services) domain** and
      one or more **workload domains**. This module is **Stage 2**; it never builds
      the SDDC.
- [ ] **SDDC inventory available:** datacenter name, the management/edge **cluster**,
      a **datastore**, the management **dvPortGroup**, the ESXi host names, and the
      workload **Tier-1 gateway** paths.
- [ ] **NSX reachable** and the ability to configure **DFW rules**, a **DNS forwarder**,
      and **DHCP relay** profiles.
- [ ] **Permissions.** A vCenter/NSX **deploy** account (create VMs, DFW, forwarder,
      relay) and a **separate, least-privileged read-only** vCenter service account +
      NSX API user for discovery (Phase 4).
- [ ] **Tooling:** `terraform` ≥ 1.5 (the module requires `>= 1.5.0, < 2.0.0`),
      `govc` **and/or** PowerCLI, `ovftool` (for local OVA deploy), `jq`, `dig`/`nslookup`.
- [ ] **A secret store** — HashiCorp Vault or your CI secret store — for the vNIOS
      admin password, temp license, Grid shared secret (or Portal join token), and the
      vCenter/NSX passwords. **There is no Key Vault on-prem.**
- [ ] **The vNIOS `.ova`** for your NIOS release, downloaded from the Infoblox
      support/download portal, and (preferred) uploaded to a vSphere **content library**.
- [ ] **A free, non-overlapping management CIDR** and **static IPs** for the members
      inside it.
- [ ] **Explicit CIDRs** for DFW scoping — mgmt, DNS clients (tenant segments/forwarder),
      DHCP relay sources, Grid peers/GM, monitoring. **Never `0.0.0.0/0`** (the module
      hard-fails on it).

---

## Phase 0 — Decisions & inventory

### Step 0.1 — Choose the control-plane model

The single most consequential decision. It sets **where the control plane lives
relative to your ATO boundary**.

| | `deployment_model = "grid"` (default) | `deployment_model = "universal_ddi"` |
|---|---|---|
| Control plane | vNIOS **Grid**, self-operated in the SDDC | Infoblox **Portal / CSP** (SaaS) |
| Vs. ATO boundary | **Inside** (the natural VMware fit) | **Outside** |
| Data-plane members | vNIOS DNS/DHCP members | NIOS-X hosts |
| Outbound dependency | Grid VPN `1194/udp` + `2114/tcp` | **outbound `443` to the Infoblox Portal** |
| FedRAMP-Moderate fit | **Boundary-clean — recommended default** | Requires authorization review; often disallowed on sovereign VCF |
| Code guard | none | hard-fails unless `acknowledge_saas_boundary = true` |

**Decision:** For a boundary-clean VCF landing zone, choose **`grid`** — the Grid Master
usually already lives in the management domain. Only choose `universal_ddi` after completing
the FedRAMP/authorization review for the SaaS control-plane egress.

**Verify:** Write the chosen `deployment_model` value down; it must match across
`terraform.tfvars` and the pipeline env (`DEPLOYMENT_MODEL`).

> **⚠ UNIVERSAL DDI callout.** If you selected `universal_ddi`, you must also set
> `acknowledge_saas_boundary = true` **and** be able to justify the outbound-443
> dependency to the Infoblox Portal. Leaving the ack `false` (the default) is a
> deliberate hard-fail — see Phase 7.

### Step 0.2 — Gather SDDC inventory into shell variables

```bash
# Fill these from your VCF SDDC (management/edge domain).
export VSPHERE_SERVER="vcenter.corp.example"
export VSPHERE_DATACENTER="DC1"
export COMPUTE_CLUSTER="MgmtCluster"
export DATASTORE="DS-SSD-01"
export MGMT_PG="MGMT-dvPG"                    # management dvPortGroup
export DDI_MGMT_CIDR="10.20.10.0/24"          # supply your own free, non-overlapping CIDR
export MEMBER_IPS="10.20.10.11 10.20.10.12"   # static member IPs (one per member)
export DDI_VIP="10.20.10.10"                   # VRRP/anycast VIP
export NSX_MANAGER="nsx.corp.example"
```

**Verify:** `echo "$DDI_MGMT_CIDR"` is a valid CIDR and the member IPs fall inside it — the
module's `ddi_mgmt_network_cidr` validation and the member-IP-count precondition reject
anything else.

---

## Phase 1 — Tooling & auth

### Step 1.1 — Install and check tooling

```bash
terraform version          # expect >= 1.5.0, < 2.0.0
govc version               # VMware CLI (or use PowerCLI, below)
ovftool --version          # only needed for local .ova deploy
jq --version ; dig -v 2>&1 | head -1
```

**Verify:** `terraform version` prints a 1.5+ build; `govc version` prints the CLI.

### Step 1.2 — Connect to vCenter and NSX (creds from Vault/CI)

```bash
# vCenter (govc). Password from Vault/CI, NOT typed inline in production.
export GOVC_URL="$VSPHERE_SERVER"
export GOVC_USERNAME="svc-tf@vsphere.local"
export GOVC_PASSWORD="$(vault kv get -field=pw secret/vsphere)"   # or CI secret
export GOVC_INSECURE=0                                            # verify TLS (do NOT disable in prod)
govc about
```

PowerCLI equivalent:

```powershell
Connect-VIServer -Server $env:VSPHERE_SERVER -User 'svc-tf@vsphere.local' -Password $pw
```

**Verify:** `govc about` prints the vCenter version and build; `Connect-VIServer` returns a
session. If TLS fails, install the vCenter CA rather than setting `GOVC_INSECURE=1`.

> **Troubleshooting — TLS verification.** The module's `allow_unverified_ssl` defaults to
> `false` for exactly this reason. Import your vCenter/NSX CA into the runner's trust store;
> do not disable verification for a FedRAMP-Moderate posture.

### Step 1.3 — Create the Terraform remote-state backend (shared, on-prem)

There is no cloud object store here. Use a backend your SDDC already runs — e.g. an
S3-compatible store (MinIO), an HTTP backend, Consul, or Terraform Enterprise — and configure
the matching `backend` block in `terraform/`. Example (MinIO/S3-compatible):

```bash
export TFSTATE_BUCKET="tfstate"
export TFSTATE_ENDPOINT="https://minio.corp.example"
# Create the bucket with your object-store CLI, enable versioning + locking.
```

**Verify:** the backend is reachable from the runner and supports **state locking**.

---

## Phase 2 — Consume Stage-1 SDDC inventory

The module learns about the SDDC **only** through these facts — it never creates the
datacenter, cluster, datastore, or port group. Resolve them with `govc`:

```bash
# Cluster + datastore + port group + hosts
govc ls "/$VSPHERE_DATACENTER/host/$COMPUTE_CLUSTER"
govc ls "/$VSPHERE_DATACENTER/datastore" | grep "$DATASTORE"
govc ls "/$VSPHERE_DATACENTER/network"   | grep "$MGMT_PG"
govc find "/$VSPHERE_DATACENTER/host/$COMPUTE_CLUSTER" -type h   # ESXi host names
```

NSX Tier-1 gateway paths (for the DNS forwarder target) come from NSX Manager:

```bash
# via the NSX policy API (or the NSX UI). Example path form:
#   /infra/tier-1s/<t1-id>
curl -fsS -u "$NSX_USER:$NSX_PASSWORD" "https://$NSX_MANAGER/policy/api/v1/infra/tier-1s" | jq -r '.results[].path'
```

**Verify:** each command prints a value; feed them into the tfvars in Phase 6. They map to
variables `vsphere_datacenter`, `compute_cluster`, `datastore`, `management_portgroup`,
`esxi_hosts`, and `workload_tier1_ids`.

---

## Phase 3 — Secrets in Vault / CI

The module reads secret **values** as **sensitive variables** (`admin_password`,
`temp_license`, `grid_shared_secret`, `saas_join_token`, `vsphere_password`, `nsx_password`);
it never creates them and never emits them as plaintext outputs. **There is no Key Vault** —
store them in HashiCorp Vault or the CI secret store and inject via `TF_VAR_*`.

### Step 3.1 — Store the module secrets in Vault

```bash
vault kv put secret/vsphere      pw='<VCENTER_DEPLOY_PASSWORD>'
vault kv put secret/nsx          pw='<NSX_DEPLOY_PASSWORD>'
vault kv put secret/vnios-admin  pw='<STRONG_ADMIN_PASSWORD>'
vault kv put secret/grid         secret='<GRID_SHARED_SECRET>'      # grid path
# temp license is not really secret but is stored the same way for consistency:
vault kv put secret/vnios-license value='nios dns dhcp grid cloud'
```

> **⚠ UNIVERSAL DDI callout.** For `universal_ddi`, also store the Portal join token
> (NIOS-X hosts phone home to the Portal over 443 with it):
> ```bash
> vault kv put secret/portal-join token='<PORTAL_JOIN_TOKEN>'
> ```

### Step 3.2 — Export them as `TF_VAR_*` at apply time

```bash
export TF_VAR_vsphere_password="$(vault kv get -field=pw secret/vsphere)"
export TF_VAR_nsx_password="$(vault kv get -field=pw secret/nsx)"
export TF_VAR_admin_password="$(vault kv get -field=pw secret/vnios-admin)"
export TF_VAR_grid_shared_secret="$(vault kv get -field=secret secret/grid)"
export TF_VAR_temp_license="$(vault kv get -field=value secret/vnios-license)"
# universal_ddi only:
# export TF_VAR_saas_join_token="$(vault kv get -field=token secret/portal-join)"
```

**Verify:** `env | grep -c '^TF_VAR_.*password'` shows the expected count; none of these
values is ever written to `terraform.tfvars` or committed. The module marks them `sensitive`,
so they do not appear in plan output or state as plaintext.

> **Troubleshooting — missing model secret.** The `boundary_guard` precondition hard-fails
> the plan if `deployment_model='grid'` and `grid_shared_secret` is unset (or `universal_ddi`
> and `saas_join_token` is unset). Export the right one for your model.

---

## Phase 4 — Discovery credentials + least-privilege role

The vCenter/NSX → Infoblox IPAM sync uses a **separate, least-privileged** identity: a
**read-only** vCenter service account and an NSX API user. Roles are scoped per contract §5 —
**no vCenter Administrator, no NSX Enterprise Admin.**

### Step 4.1 — Create the read-only vCenter service account (SSO/AD)

This is an SSO/AD task, not Terraform. Create `svc-infoblox-disco@vsphere.local` (or an AD
service account) and note it for the tfvars (`discovery_vcenter_user`).

### Step 4.2 — Grant it a read-only role (optionally via the module)

The module can create the read-only vSphere **role + permission** for you when
`manage_discovery_role = true` (resources `vsphere_role.discovery_readonly` +
`vsphere_entity_permissions.discovery`). If you prefer to do it by hand, create a role with
read-only privileges and assign it at the datacenter with **propagate**:

```bash
# govc sketch (privilege ids are version-specific — confirm in vCenter > Roles):
govc role.create infoblox-disco-ro System.Anonymous System.View System.Read
govc permissions.set -principal 'svc-infoblox-disco@vsphere.local' -role infoblox-disco-ro \
  -propagate=true "/$VSPHERE_DATACENTER"
```

**Verify:** `govc permissions.ls "/$VSPHERE_DATACENTER"` shows the read-only role bound to the
discovery SA and **nothing broader**.

### Step 4.3 — Create the NSX API user (read)

In NSX Manager, create an API user (`svc-infoblox-nsx`) with **read** on segments/gateways.
Note it for the tfvars (`discovery_nsx_user`). Read/write is only needed if NSX is to *create*
networks/records via Infoblox (the "Register Infoblox NIOS DDI with NSX" flow).

**Verify:** the NSX user can `GET` `/policy/api/v1/infra/segments` but cannot modify.

> **Troubleshooting — discovery enumerates nothing.** The usual cause is the vCenter role not
> propagating to the datacenter (Step 4.2) or the NSX user lacking read on the workload
> domains. Confirm both before blaming CNA.

---

## Phase 5 — Stage the vNIOS OVA (content library)

There is no Marketplace on VMware. Download the vNIOS `.ova` for your NIOS release and upload
it to a vSphere **content library** (preferred, repeatable):

```bash
# Create a content library (once) and import the OVA:
govc library.create infoblox
govc library.import infoblox /path/to/nios-<release>.ova
govc library.ls /infoblox/*
```

Note the library name and item name for the tfvars (`vnios_ovf.content_library` /
`content_library_item`). For a one-off local deploy you can instead set
`vnios_ovf.local_ovf_path`.

**Verify:** `govc library.info /infoblox/nios-<release>` shows the imported OVF item.

> **Do NOT invent the OVA build or appliance model.** The model (CP-V805 / TE-V825 /
> TE-V1425 …) sets vCPU/RAM; confirm the current model list and figures against the Infoblox
> vNIOS-for-VMware install guide for your release (`../05-vmware.md §9`).

---

## Phase 6 — Configure the module (`terraform.tfvars`)

Start from `examples/hub-integration/main.tf`, then externalize the values into a
`terraform.tfvars` next to the module. **Secrets stay in Vault/CI (Phase 3), not here.**

```hcl
# terraform.tfvars — Stage-2 Infoblox DDI (grid, self-contained VCF, FedRAMP-Moderate)

# --- Basics / boundary ---
name_prefix        = "ddi"                 # -> ddi-vnios-h1, ddi-mgmt-group, ddi-disco-role
environment        = "prod"                # dev | test | prod
deployment_model   = "grid"                # boundary-clean default
compliance_profile = "fedramp-moderate"
# acknowledge_saas_boundary left false — not needed for grid.

# --- Stage-1 SDDC inventory ---
vsphere_datacenter    = "DC1"
compute_cluster       = "MgmtCluster"
resource_pool         = "MgmtCluster/Resources/infoblox"  # optional
datastore             = "DS-SSD-01"
management_portgroup  = "MGMT-dvPG"
ddi_mgmt_network_cidr = "10.20.10.0/24"

# --- Members: 2 across two ESXi hosts (HA, anti-affinity) ---
member_count = 2
esxi_hosts   = ["esxi-01.corp.example", "esxi-02.corp.example"]

# --- Static addressing (from the IPAM plan) ---
member_ip_addresses = ["10.20.10.11", "10.20.10.12"]
member_netmask      = "255.255.255.0"
member_gateway      = "10.20.10.1"
ddi_anycast_vip     = "10.20.10.10"

# --- OVA + model: supply your own (do NOT invent) ---
vnios_appliance_model = "TE-V1425"         # confirm the model list for your NIOS release
vnios_ovf = {
  content_library      = "infoblox"
  content_library_item = "nios-9.0.x"      # your uploaded OVA item
  # or: local_ovf_path = "/opt/ova/nios.ova"
}
disk_thin_provisioned = false              # thick eager-zeroed for DNS/DHCP DB performance

# --- DFW source scoping (never 0.0.0.0/0) ---
mgmt_source_cidrs = ["10.20.0.0/24"]                 # admin/bastion + Aria + CNA
dns_client_cidrs  = ["10.30.0.0/16"]                 # tenant segments / NSX forwarder
dhcp_relay_cidrs  = ["10.30.0.0/16"]                 # NSX DHCP relay sources (DHCP is ON)
grid_peer_cidrs   = ["10.20.10.0/24", "192.168.100.0/24"] # mgmt net + on-prem GM

# --- Grid join (usual pattern: join members to an existing GM) ---
grid_name       = "CorpGrid"
grid_master_vip = "192.168.100.10"         # existing Grid Master VIP; null => first member is GM (lab only)

# --- DNS / DHCP integration (§8) ---
ad_dns_servers           = ["192.168.100.5", "192.168.100.6"]  # on-prem AD DNS
ad_forward_domains       = ["corp.example"]
enable_dhcp              = true            # DHCP is Infoblox's job on VMware (default)
enable_nsx_dns_forwarder = true
workload_tier1_ids       = ["/infra/tier-1s/t1-workload-a"]

# --- Discovery (least-privilege read-only) ---
discovery_identity_type = "vcenter_service_account"
discovery_vcenter_user  = "svc-infoblox-disco@vsphere.local"
discovery_nsx_user      = "svc-infoblox-nsx"
manage_discovery_role   = true

# --- Connection (passwords via TF_VAR_* from Vault/CI, NOT here) ---
vsphere_server = "vcenter.corp.example"
vsphere_user   = "svc-tf@vsphere.local"
nsx_manager    = "nsx.corp.example"
nsx_user       = "svc-tf-nsx"

tags = { owner = "network-platform", costcenter = "cc-1234" }
```

**What the key variables do (all real):**

- `deployment_model` / `acknowledge_saas_boundary` — the boundary switch + its guard.
- `member_ip_addresses` — static IPs carried into the OVF **vApp properties**; they become
  the `dns_server_ips` output (must equal `member_count` in length).
- `esxi_hosts` — members are round-robined over the hosts; a DRS **anti-affinity** rule keeps
  the HA pair on separate hosts.
- `grid_peer_cidrs` — **required for grid** (a `nsxt_policy_security_policy` precondition fails
  the plan if `grid` is selected and this is empty).
- `dhcp_relay_cidrs` — **required when `enable_dhcp = true`** (the default) — a precondition
  enforces it.
- `mgmt_source_cidrs` / `dns_client_cidrs` — enforced non-empty and **must not** contain
  `0.0.0.0/0` (variable `validation`).

> **⚠ UNIVERSAL DDI callout — tfvars deltas.** To run the SaaS path:
> ```hcl
> deployment_model          = "universal_ddi"
> acknowledge_saas_boundary = true            # REQUIRED — false hard-fails the plan
> infoblox_portal_url       = "csp.infoblox.com"   # outbound 443 required
> # grid_master_vip / grid_shared_secret are unused; set TF_VAR_saas_join_token instead
> ```
> With ack `false`, `terraform plan` aborts with the `BOUNDARY VIOLATION` message pointing to
> the authorization review — the `ddi-niosx-*` VMs and `null_resource.portal_enroll` never plan.

---

## Phase 7 — Deploy

### Step 7.1 — `init` with the shared backend

```bash
cd infoblox-ddi-book/vmware-lz-automation/terraform
terraform init \
  -backend-config="bucket=$TFSTATE_BUCKET" \
  -backend-config="endpoint=$TFSTATE_ENDPOINT" \
  -backend-config="key=vmware-ddi-prod.tfstate"
```

**Verify:** `Terraform has been successfully initialized!` and the `vsphere`, `nsxt`,
`infobloxopen/infoblox`, and `null` providers resolve (per `versions.tf`).

### Step 7.2 — `plan` (guards are evaluated here)

```bash
terraform plan -input=false -out=tfplan
```

**Expected:** the plan creates the NSX-T DFW member group + default-deny policy + rules
(including **DHCP by default**), `ddi-vnios-h1` / `ddi-vnios-h2` (from the OVA), the DRS
anti-affinity rule, the optional read-only discovery role/permission, the NSX DNS forwarder
zone + DHCP relay, and the `infoblox_zone_forward` objects (if `ad_dns_servers` set). The
boundary guard, the model-secret checks, and the DFW CIDR scoping are checked at **plan** time.

**Verify:** plan summary shows the expected adds and **no** `0.0.0.0/0` sources.

### Step 7.3 — `apply`

```bash
terraform apply -input=false -auto-approve tfplan
```

**Expected outputs (contract §7):**

```bash
terraform output
# ddi_anycast_vip       = "10.20.10.10"
# dns_server_ips        = ["10.20.10.11", "10.20.10.12"]
# grid_master_ip        = "192.168.100.10"          # existing GM (grid only)
# discovery_identity_id = "<vsphere role id or the discovery SA>"
# ddi_member_vm_ids     = ["vm-1234", "vm-1235"]
```

**Cross-host members:** confirm the two members landed on different ESXi hosts:

```bash
govc vm.info -json "ddi-vnios-h1" "ddi-vnios-h2" | jq -r '.virtualMachines[] | "\(.name) -> \(.runtime.host)"'
```

**Verify:** the two members show different host IDs; the anti-affinity rule keeps them apart.

> **Troubleshooting — grid plan fails immediately.** *"deployment_model='grid' requires
> grid_peer_cidrs"* → set `grid_peer_cidrs` (Grid members/GM ranges).
>
> **Troubleshooting — DHCP precondition.** *"enable_dhcp=true … requires dhcp_relay_cidrs"* →
> set `dhcp_relay_cidrs` (the NSX DHCP relay sources), or set `enable_dhcp = false` if this
> deployment truly does not serve DHCP (uncommon on VMware).
>
> **Troubleshooting — OVF property mismatch.** If the appliance boots but ignores the static
> IP or license, the OVF **vApp property KEYS** differ for your OVA build. Inspect the
> descriptor: `govc library.info` / `ovftool --hideEula nios.ova` and adjust the property keys
> in `grid.tf` (`local.grid_vapp_properties`).
>
> **Troubleshooting — DNS-object apply fails.** `infoblox_zone_forward` needs a reachable
> Grid/NIOS WAPI endpoint. Members are not yet Grid-joined at first apply; either point the
> `infoblox` provider `server` at an existing GM, or run the DNS-object resources in a **second
> phase** after Phase 8 (use `-target` or a dependent module). This ordering is by design.

---

## Phase 8 — Grid formation / Universal DDI onboarding

The VMs exist, but the **control plane is not yet formed**. `ddi_anycast_vip` and
`grid_master_ip` become operationally real only after this phase.

### Step 8.1 — Grid path: form / join the Grid

Each member booted with the OVF vApp properties carrying the temp license, admin password,
static IP, and grid-join parameters from Vault/CI. Complete formation:

- **Usual pattern:** an existing Grid Master (`grid_master_vip`) is authoritative; the new
  members join as **Grid members** over `1194/udp` + `2114/tcp`. Confirm each member appears in
  the Grid Manager UI under your `grid_name` (e.g. `CorpGrid`).
- **Lab/greenfield:** if `grid_master_vip = null`, the first member (`ddi-vnios-h1`)
  initializes the Grid as GM; the second joins it.
- Deploy a **Grid Master Candidate** (a third member on a different host) for control-plane HA.
- **Assign the VRRP/anycast VIP** (`ddi_anycast_vip`) as a shared DNS/DHCP service address so
  the NSX forwarder/relay target one stable address.

**Verify (WAPI, from a mgmt host):**

```bash
export GRID_MASTER="192.168.100.10"                 # your Grid Master (grid_master_ip)
export INFOBLOX_USERNAME="admin"
export INFOBLOX_PASSWORD="$(vault kv get -field=pw secret/vnios-admin)"
curl -fsS -u "$INFOBLOX_USERNAME:$INFOBLOX_PASSWORD" \
  "https://$GRID_MASTER/wapi/v2.12/member?_return_fields%2B=host_name,service_status"
```

Both new members show `service_status` running for DNS (and DHCP). Confirm the exact WAPI
object/field names against `<grid-master>/wapidoc/` for your NIOS version.

> **⚠ UNIVERSAL DDI callout — enroll NIOS-X to the Portal.** Instead of Grid formation, each
> `ddi-niosx-*` host self-enrolls to the Portal over 443 using the join token from the vApp
> properties. The `null_resource.portal_enroll` is the explicit API seam — replace its
> placeholder with the real CSP REST call, then confirm in the Portal inventory:
> ```bash
> curl -fsS -H "Authorization: Token $INFOBLOX_CSP_TOKEN" \
>   "https://csp.infoblox.com/api/infra/v1/hosts?_filter=display_name=='ddi-niosx-1'"
> ```

**Verify:** members/hosts report healthy in the Grid Manager UI or the Portal, and the VIP
answers (tested in Phase 12).

---

## Phase 9 — Cloud discovery adapter (CNA)

vSphere/NSX RBAC (Phase 4) grants the read-only identity; the **Infoblox side** of discovery
is configured on the control plane — there is no `infoblox_vdiscovery_job` provider resource,
so this is an explicit API/UI handoff (the module documents the seam in `discovery.tf`).

### Step 9.1 — Grid path: create a VMware vDiscovery job (WAPI)

Point Cloud Network Automation at vCenter (and NSX), authenticating with the read-only service
account. Illustrative WAPI handoff:

```bash
curl -fsS -u "$INFOBLOX_USERNAME:$INFOBLOX_PASSWORD" \
  -X POST "https://$GRID_MASTER/wapi/v2.12/vdiscoverytask" \
  -H 'Content-Type: application/json' \
  -d '{"name":"vmware-disco","member":"infoblox.localdomain","credential_type":"VMWARE"}'
```

Schedule it on a cadence (e.g. hourly) so IPAM tracks vSphere reality. Confirm the exact
object/fields against `<grid-master>/wapidoc/` for your NIOS version.

> **⚠ UNIVERSAL DDI callout.** Configure a Portal cloud source for vCenter using the same
> read-only credential via the CSP API/UI; the discovery job lives in the SaaS control plane.

**Verify:** run the Stage-3 discovery check (Phase 12) — it asserts the job exists, is not in
`ERROR`/`WARNING`, and ran within `STALE_THRESHOLD_MIN`.

---

## Phase 10 — DNS / DHCP integration

### Step 10.1 — NSX-T DNS forwarder → Infoblox

`dns.tf` creates `nsxt_policy_dns_forwarder_zone.ddi_upstream` with
`upstream_servers = the DDI VIP` when `enable_nsx_dns_forwarder = true` and
`workload_tier1_ids` is set. **Attach** that zone to each workload Tier-1's DNS forwarder (a
per-gateway step — see the note in `dns.tf`). Tenant VMs then use the gateway forwarder IP as
their resolver.

**Verify:** from a tenant VM, `dig app.corp.example @<NSX-forwarder-IP>` returns an answer that
traces back to a vNIOS member.

### Step 10.2 — Infoblox → on-prem AD (conditional forwarders)

`dns.tf` creates one `infoblox_zone_forward` per domain in `ad_forward_domains`, each pointing
`forward_to.address` at `ad_dns_servers`. This runs only when `deployment_model = "grid"` and
`ad_dns_servers` is non-empty.

**Verify (after the DNS-object phase applies):**

```bash
curl -fsS -u "$INFOBLOX_USERNAME:$INFOBLOX_PASSWORD" \
  "https://$GRID_MASTER/wapi/v2.12/zone_forward?fqdn=corp.example"
```

Returns the forward zone targeting the on-prem AD DNS servers.

### Step 10.3 — DHCP relay → Infoblox (DHCP is Infoblox's job)

`dns.tf` creates `nsxt_policy_dhcp_relay.ddi` with `server_addresses = member IPs` when
`enable_dhcp = true` (the default). **Attach** the relay profile to each tenant segment / the
Tier-1's DHCP config (a per-segment step — often owned by the workload team).

**Verify:** boot a VM on a segment with the relay attached; confirm it receives an address from
the Infoblox range and an A/PTR record appears in IPAM:

```bash
curl -fsS -u "$INFOBLOX_USERNAME:$INFOBLOX_PASSWORD" \
  "https://$GRID_MASTER/wapi/v2.12/lease?address=10.30.5.50"
```

> **Troubleshooting — DFW blocking 53/67-68/1194/2114.** If DNS/DHCP times out or Grid members
> won't converge, confirm the DFW rules exist and their source groups match your CIDRs:
> `Allow-DNS-In` (dns_client_cidrs), `Allow-DHCP-In` (dhcp_relay_cidrs), `Allow-GridVPN` +
> `Allow-GridComms` (grid_peer_cidrs), and the `Deny-All-DDI` drop at the end. Inspect the
> policy in NSX Manager (Security → Distributed Firewall) or via the policy API.

---

## Phase 11 — IPAM automation & the Aria plug-in

Because discovery imports vSphere metadata as **extensible attributes (EAs)**, IPAM becomes an
API the platform consumes.

### Step 11.1 — Confirm networks appear

vDiscovery walks vCenter → clusters → VMs → port groups and populates Infoblox IPAM as
networks/containers with discovered VMs as records.

**Verify:**

```bash
curl -fsS -u "$INFOBLOX_USERNAME:$INFOBLOX_PASSWORD" \
  "https://$GRID_MASTER/wapi/v2.12/network?_return_fields%2B=network,comment&network_view=default"
```

vSphere segment CIDRs (including the mgmt network `10.20.10.0/24`) appear as `network` objects.

### Step 11.2 — Register the Infoblox IPAM plug-in in Aria Automation

Follow [`pipelines/aria-automation-ipam-vmware.md`](./pipelines/aria-automation-ipam-vmware.md):
download the provider package (VMware Marketplace / Infoblox), register Infoblox as an
**external IPAM provider** with the Grid address + a scoped admin credential (Aria 8.9.1+,
plug-in 1.5+, WAPI v2.7+). In blueprints, network/machine resources then request IPs from
Infoblox; on deploy the plug-in **allocates the IP, creates the A/PTR record, and injects
gateway/netmask/DNS into the VM**; on delete it **reclaims the IP and records**.

**Verify:** deploy a catalog item → the VM gets an Infoblox-allocated IP + DNS record; delete
it → the IP and records are reclaimed (the IPAM conflict gate in Phase 12 then reports no
orphans/overlaps).

---

## Phase 12 — Validation gates

Run each `validation/*.sh` with its env-var contract. Any non-zero exit fails the Stage-3
pipeline gate.

### Step 12.1 — DNS resolution (`dns-validation.sh`)

```bash
cd infoblox-ddi-book/vmware-lz-automation/validation
export DDI_VIP="10.20.10.10"                     # ddi_anycast_vip (or NSX forwarder IP)
export TEST_FQDN="app01.corp.example"            # enterprise A record
export EXPECTED_IP="10.30.5.10"                  # its expected answer
export AD_FQDN="dc01.corp.example"               # optional — AD conditional-forward test
bash dns-validation.sh
```

**Proves:** the DDI VIP answers an enterprise A record with `EXPECTED_IP`, and an AD-integrated
name resolves through the conditional-forward path to a **private** answer. **Verify:** ends
with `All DNS validation checks passed.`

### Step 12.2 — Discovery-sync freshness (`discovery-sync-check.sh`)

```bash
export DDI_API_FLAVOR="nios"                # grid default; "universal_ddi" for SaaS
export GRID_MASTER="192.168.100.10"
export INFOBLOX_USERNAME="admin"
export INFOBLOX_PASSWORD="$(vault kv get -field=pw secret/vnios-admin)"
export STALE_THRESHOLD_MIN="1440"           # 24h
bash discovery-sync-check.sh
```

**Proves:** the VMware vDiscovery task completed successfully and recently. **Verify:** ends
with `Discovery-sync freshness check passed.`

> **⚠ UNIVERSAL DDI callout.** Set `DDI_API_FLAVOR=universal_ddi` and provide
> `INFOBLOX_CSP_TOKEN` (from Vault); the check queries the Portal cloud-discovery jobs. Only
> exercise this when `acknowledge_saas_boundary = true`.

### Step 12.3 — IPAM conflict (`ipam-conflict-check.sh`)

```bash
export GRID_MASTER="192.168.100.10"
export INFOBLOX_USERNAME="admin"
export INFOBLOX_PASSWORD="$(vault kv get -field=pw secret/vnios-admin)"
export NETWORK_VIEW="default"
# optional: export CANDIDATE_NETWORK="10.30.6.0/24"   # test a new segment before enabling its DHCP relay
bash ipam-conflict-check.sh
```

**Proves:** no overlapping/duplicate `network` objects — and therefore no ambiguous DHCP scope.
**Verify:** ends with `IPAM conflict check passed.`

> **Troubleshooting — VRRP not converging.** If `dns-validation.sh` intermittently fails, the
> VRRP VIP may not be advertised from both members yet (Phase 8), or a member is unhealthy.
> Confirm both members answer directly: `dig +short @10.20.10.11 app01.corp.example` and
> `@10.20.10.12` before blaming the VIP.

---

## Phase 13 — Wire into GitOps

The pipeline (`pipelines/github-actions-vmware-ddi.yml`) runs the same three stages —
**inventory (read SDDC) → DDI (Stage-2 apply) → validate (Stage-3)** — with **username/password
auth from secrets (no cloud OIDC)** and remote state on a shared backend.

### Step 13.1 — Store secrets + wire variables

Set repo/environment **secrets** `VSPHERE_PASSWORD`, `NSX_PASSWORD`, `VNIOS_ADMIN_PASSWORD`,
`GRID_SHARED_SECRET` (and `SAAS_JOIN_TOKEN` for universal_ddi), plus `INFOBLOX_USERNAME` /
`INFOBLOX_PASSWORD` for validation — ideally fronted by HashiCorp Vault via a self-hosted
runner in the management network. Set **variables** `VSPHERE_SERVER`/`VSPHERE_USER`/
`NSX_MANAGER`/`NSX_USER`, `TFSTATE_BUCKET`/`TFSTATE_ENDPOINT`, the SDDC inventory
(`VSPHERE_DATACENTER`/`COMPUTE_CLUSTER`/`DATASTORE`/`MGMT_PG`), and the DNS test inputs
(`TEST_FQDN`/`EXPECTED_IP`/`AD_FQDN`).

### Step 13.2 — The boundary gate & promotion flow

The pipeline carries `DEPLOYMENT_MODEL` (`grid`) and `ACKNOWLEDGE_SAAS_BOUNDARY` (`false`). A
gate step **hard-fails before init** if `deployment_model = universal_ddi` and the ack is not
`true` — so the SaaS path is never even planned without a review (the Terraform guard enforces
it again).

Promotion: **PR → plan-only** (validate skipped); **dev sandbox →** `workflow_dispatch` with
`apply=true` + full validation; **test →** same with environment approval; **prod →** required
reviewers gate entry. Each env uses a distinct state key `vmware-ddi-<env>.tfstate`.

**Verify:** open a PR touching `terraform/**` — the `ddi` job runs `plan` only and `validate`
is skipped; merge to `main` (or dispatch `apply=true`) runs `apply` then the three validation
scripts.

> **Troubleshooting — boundary guard tripping in CI.** A red "Enforce SaaS boundary
> acknowledgement" step means `DEPLOYMENT_MODEL=universal_ddi` with
> `ACKNOWLEDGE_SAAS_BOUNDARY!=true`. This is intended — complete the authorization review and
> set the ack, or switch back to `grid`.

---

## Phase 14 — Day-2 & rollback

- **Upgrades.** Patch NIOS/NIOS-X on the vendor cadence via the Grid (rolling, GM-coordinated);
  **snapshot / back up the Grid DB first**. Universal DDI scales by adding NIOS-X hosts (raise
  `member_count`, re-apply).
- **Failover game-day.** Power off the active HA member; confirm VRRP moves the VIP and DNS/DHCP
  continue, and that DRS anti-affinity kept the pair on separate hosts:
  `govc vm.power -off ddi-vnios-h1` then re-run `dns-validation.sh` against the VIP; restart
  with `govc vm.power -on ddi-vnios-h1`.
- **Drift detection.** A scheduled pipeline re-runs `terraform plan`; any non-empty plan is
  drift (a member reconfigured by hand, a DFW rule edited in NSX, a forwarder changed in the
  Grid UI) and raises a reconcile PR. Because Git is the source of record, remediation is
  "revert to desired state."
- **Secret rotation.** Rotate the admin password / Grid shared secret in Vault after first Grid
  setup. Note `grid.tf`/`universal_ddi.tf` set `lifecycle { ignore_changes = [vapp] }`, so a
  Vault rotation does **not** silently recreate running members — re-bootstrap is deliberate.
- **Teardown cautions.** `terraform destroy` removes the members, the DFW policy/group, the
  forwarder/relay, and the discovery role. **Before destroying:** revert any NSX DNS forwarder /
  DHCP relay pointed at the members (Phase 10) or those segments lose resolution/leases; drain
  the members from the Grid first so the GM does not flag missing members; and confirm no
  workload still depends on the VIP. Destroy is scoped to Stage-2 only — it must **never** touch
  the Stage-1 SDDC.

---

## End-to-end validation checklist

Run top-to-bottom after Phase 12; every item should pass before calling the layer
production-ready.

- [ ] `terraform output` shows `ddi_anycast_vip`, `dns_server_ips`, `grid_master_ip` (grid),
      `discovery_identity_id`, `ddi_member_vm_ids`.
- [ ] Members `ddi-vnios-h1` / `ddi-vnios-h2` are on **different ESXi hosts** (anti-affinity)
      and Grid-joined (or NIOS-X hosts enrolled to the Portal).
- [ ] The DFW policy carries exactly the contract ports (incl. **DHCP by default**); no source
      is `0.0.0.0/0`; `Deny-All-DDI` drop present.
- [ ] The discovery SA holds a **read-only** vSphere role and the NSX user is read-only —
      nothing broader (no vCenter Administrator, no NSX Enterprise Admin).
- [ ] Secrets (admin pw, temp license, grid shared secret / join token, vCenter/NSX pw) live in
      **Vault/CI** — none in Terraform state as plaintext.
- [ ] `dns-validation.sh` passes (enterprise A + AD conditional-forward path).
- [ ] `discovery-sync-check.sh` passes (job fresh, not errored).
- [ ] `ipam-conflict-check.sh` passes (no overlapping CIDRs / DHCP scopes).
- [ ] DHCP: a VM on an NSX-relayed segment gets an Infoblox lease + A/PTR record.
- [ ] Aria: a catalog deploy allocates + registers, and delete reclaims the IP/records.
- [ ] Failover: powering off one member leaves the VRRP VIP answering.
- [ ] Pipeline: PR = plan-only; merge/apply = apply + validate; prod behind approval.
- [ ] `universal_ddi` selected? — `acknowledge_saas_boundary = true`, the authorization review
      is on file, and outbound 443 to the Infoblox Portal is documented (and permitted on this
      sovereign VCF).

---

## Appendix A — Variable Worksheets (fill-in forms)

Copy each block, replace every `____` with your value, and keep the rest. Fields marked
**REQUIRED** have no default — the plan/deploy fails without them. The trailing comment gives
the **source** of each value:

- **you choose** — a design decision (CIDRs, names, model)
- **Stage-1 fact** — comes from the SDDC (Phase 2)
- **generated** — a command produces it (`govc …`) or a Stage-2 output does (Phase 7)
- **existing** — an already-provisioned resource (e.g. your content library, AD DNS)

### A.1 Terraform — `terraform/terraform.tfvars`

```hcl
# ---- REQUIRED (no default) ----
vsphere_datacenter    = "____"   # Stage-1 fact — vSphere datacenter
compute_cluster       = "____"   # Stage-1 fact — mgmt/edge cluster
datastore             = "____"   # Stage-1 fact — member disk datastore
management_portgroup  = "____"   # Stage-1 fact — management dvPortGroup
ddi_mgmt_network_cidr = "____"   # you choose — mgmt network CIDR (e.g. 10.20.10.0/24)
vnios_appliance_model = "____"   # you choose — vNIOS model (per NIOS release; do not invent)
vnios_ovf = {                    # existing — your uploaded OVA (or a local path)
  content_library      = "____"
  content_library_item = "____"
  # or: local_ovf_path = "____"
  # deployment_option  = "____"
}
mgmt_source_cidrs = ["____"]     # you choose — admin/Aria/CNA CIDRs (NEVER 0.0.0.0/0)
dns_client_cidrs  = ["____"]     # you choose — tenant/forwarder CIDRs allowed to query DNS
# connection (passwords via TF_VAR_* from Vault/CI — see A.3):
vsphere_server = "____"          # vCenter FQDN
vsphere_user   = "____"          # deploy account
nsx_manager    = "____"          # NSX Manager FQDN
nsx_user       = "____"          # deploy account (NSX)

# ---- OPTIONAL (defaults shown — change as needed) ----
name_prefix               = "ddi"
environment               = "prod"            # dev | test | prod
deployment_model          = "grid"            # grid | universal_ddi
acknowledge_saas_boundary = false             # MUST be true if deployment_model = "universal_ddi"
compliance_profile        = "fedramp-moderate"
member_count              = 2                  # >= 2 for HA
resource_pool             = null              # optional
esxi_hosts                = ["____", "____"]   # anti-affinity spread
tags                      = {}

# Sizing (model-dependent — leave null to inherit OVA/model defaults)
vnios_num_cpus        = null
vnios_memory_mb       = null
vnios_disk_gb         = null
disk_thin_provisioned = false                 # thick eager-zeroed recommended for prod

# Static addressing (carried into OVF vApp properties)
member_ip_addresses = ["____", "____"]        # one per member, inside ddi_mgmt_network_cidr
member_netmask      = "255.255.255.0"
member_gateway      = "____"
ddi_anycast_vip     = "____"                  # VRRP/anycast VIP

# DFW scoping (never 0.0.0.0/0)
dhcp_relay_cidrs        = ["____"]            # REQUIRED when enable_dhcp = true (default)
grid_peer_cidrs         = ["____"]            # grid only — mgmt net + on-prem GM (1194/udp, 2114/tcp)
monitoring_source_cidrs = []                  # REQUIRED only if enable_snmp = true
enable_dhcp             = true                # DHCP is Infoblox's job on VMware (default)
enable_snmp             = false
enable_ssh             = false

# DNS integration
ad_dns_servers           = ["____"]           # on-prem AD DNS (empty = skip conditional forwarders)
ad_forward_domains       = ["corp.example"]
enable_nsx_dns_forwarder = false              # true wires the NSX DNS forwarder zone
workload_tier1_ids       = ["____"]           # Tier-1 gateway paths for the forwarder

# Discovery (least-privilege read-only)
discovery_identity_type = "vcenter_service_account"
discovery_vcenter_user  = "____"              # read-only vCenter SA (Phase 4)
discovery_nsx_user      = "____"              # read-only NSX API user
manage_discovery_role   = false              # true = module creates the read-only vSphere role/permission

# Grid join (deployment_model = "grid")
grid_name       = "Infoblox"
grid_master_vip = "____"                      # existing GM VIP (null only for a lab where the first member IS the GM)

# Universal DDI (deployment_model = "universal_ddi")
infoblox_portal_url = "csp.infoblox.com"
```

### A.2 Secret store (values referenced by A.1, NOT in tfvars)

These are **sensitive variables** injected via `TF_VAR_*` from HashiCorp Vault / CI — never in
`terraform.tfvars`, never committed. There is **no Key Vault** on-prem.

| TF variable | Content | Source | Applies to |
|---|---|---|---|
| `vsphere_password` | vCenter deploy account password | your SSO/AD | both |
| `nsx_password` | NSX deploy account password | NSX | both |
| `admin_password` | vNIOS `admin` password set at first boot | you choose (strong) | both |
| `temp_license` | temp license, e.g. `nios dns dhcp grid cloud` | Infoblox licensing | both |
| `grid_shared_secret` | Grid shared secret to join members | your Grid config | `grid` |
| `saas_join_token` | Infoblox Portal (CSP) join token | Infoblox Portal | `universal_ddi` |

```bash
# Store in Vault (Phase 3), then export as TF_VAR_* at apply time:
export TF_VAR_vsphere_password="$(vault kv get -field=pw secret/vsphere)"
export TF_VAR_nsx_password="$(vault kv get -field=pw secret/nsx)"
export TF_VAR_admin_password="$(vault kv get -field=pw secret/vnios-admin)"
export TF_VAR_temp_license="$(vault kv get -field=value secret/vnios-license)"
export TF_VAR_grid_shared_secret="$(vault kv get -field=secret secret/grid)"       # grid
# export TF_VAR_saas_join_token="$(vault kv get -field=token secret/portal-join)"  # universal_ddi only
```

### A.3 Validation scripts — environment forms

**`validation/dns-validation.sh`**

```bash
export DDI_VIP="____"                 # REQUIRED — VRRP/anycast VIP or NSX forwarder IP (output ddi_anycast_vip)
export TEST_FQDN="____"               # REQUIRED — an authoritative A record (e.g. app01.corp.example)
export EXPECTED_IP="____"             # REQUIRED — the IP TEST_FQDN must resolve to
export DNS_PORT="53"                  # default 53
export DNS_TIMEOUT="5"                # default 5 (seconds)
export AD_FQDN="____"                 # optional — an AD-integrated name (conditional-forward test)
export AD_EXPECTED_IP="____"          # optional — expected IP for AD_FQDN
```

**`validation/discovery-sync-check.sh`**

```bash
export DDI_API_FLAVOR="nios"          # nios | universal_ddi (default nios)
export STALE_THRESHOLD_MIN="1440"     # default 1440 (24h)
# --- NIOS (deployment_model = grid) ---
export GRID_MASTER="____"             # REQUIRED (nios) — Grid Master host/IP
export INFOBLOX_USERNAME="____"       # REQUIRED (nios)
export INFOBLOX_PASSWORD="____"       # REQUIRED (nios) — inject from Vault/CI, not literal
export WAPI_VERSION="v2.12"           # default v2.12
export WAPI_CA_BUNDLE="____"          # optional — CA bundle path for TLS verification
export DISCOVERY_TASK_NAME="____"     # optional — filter to a named vDiscovery task
# --- Universal DDI (deployment_model = universal_ddi) ---
export INFOBLOX_CSP_URL="https://csp.infoblox.com"  # default
export INFOBLOX_CSP_TOKEN="____"      # REQUIRED (universal_ddi) — Portal API token
```

**`validation/ipam-conflict-check.sh`**

```bash
export GRID_MASTER="____"             # REQUIRED — Grid Master host/IP
export INFOBLOX_USERNAME="____"       # REQUIRED
export INFOBLOX_PASSWORD="____"       # REQUIRED — inject from a secret
export WAPI_VERSION="v2.12"           # default v2.12
export WAPI_CA_BUNDLE="____"          # optional — CA bundle path
export NETWORK_VIEW="____"            # optional — limit to a network view
export CANDIDATE_NETWORK="____"       # optional — pre-check one CIDR before enabling its DHCP relay
```

### A.4 Pipeline — GitHub Actions (`pipelines/github-actions-vmware-ddi.yml`)

Set under **Settings → Secrets and variables → Actions** (or a repo Environment). No cloud
OIDC — the providers use username/password, so passwords are **secrets** (ideally Vault-backed).

**Secrets:**

| Secret | Value | Source |
|---|---|---|
| `VSPHERE_PASSWORD` / `NSX_PASSWORD` | deploy account passwords | Vault |
| `VNIOS_ADMIN_PASSWORD` / `GRID_SHARED_SECRET` | vNIOS admin pw / Grid shared secret | Vault |
| `SAAS_JOIN_TOKEN` | Portal join token (universal_ddi) | Infoblox Portal / Vault |
| `INFOBLOX_USERNAME` / `INFOBLOX_PASSWORD` | WAPI creds (validation) | Vault |

**Variables (`vars.*`):**

| Variable | Value | Source |
|---|---|---|
| `VSPHERE_SERVER` / `VSPHERE_USER` / `NSX_MANAGER` / `NSX_USER` | connection identifiers | you choose |
| `TFSTATE_BUCKET` / `TFSTATE_ENDPOINT` | shared remote-state backend | you create (Phase 1) |
| `VSPHERE_DATACENTER` / `COMPUTE_CLUSTER` / `DATASTORE` / `MGMT_PG` | SDDC inventory | Stage-1 (Phase 2) |
| `DEPLOYMENT_MODEL` / `ACKNOWLEDGE_SAAS_BOUNDARY` | `grid` / `false` | you choose |
| `TEST_FQDN` / `EXPECTED_IP` / `AD_FQDN` | validation inputs (A.3) | you choose |

> Never put `VSPHERE_PASSWORD`, `INFOBLOX_PASSWORD`, `SAAS_JOIN_TOKEN`, or the vNIOS admin
> password in plain pipeline variables — reference them from **secrets / Vault** so they are
> injected at run time only, ideally on a self-hosted runner inside the management network.

### A.5 Aria Automation IPAM plug-in — config values

Set when registering Infoblox as an external IPAM provider in Aria Automation (see
[`pipelines/aria-automation-ipam-vmware.md`](./pipelines/aria-automation-ipam-vmware.md)).

```text
Grid / WAPI address     : ____   # generated — module output grid_master_ip (or the DDI VIP)
Plug-in admin username  : ____   # existing — scoped Infoblox admin group (NOT a superuser)
Plug-in admin password  : ____   # from Vault/CI — do not store in the blueprint
WAPI version            : v2.12  # your NIOS release (>= v2.7 required)
Default network view    : default  # or a tenant-specific view
EA / property keys       : environment, tenant, zone   # align with CNA discovery EAs
Aria Automation version : ____   # existing — 8.9.1+ required
IPAM plug-in version    : ____   # existing — 1.5+ required
```

> The plug-in package is distributed via the VMware Marketplace and the Infoblox download site.
> The deep Broadcom/VMware TechDocs pages gate/redirect — search their docs for "download and
> deploy an external IPAM provider package" and "Infoblox external IPAM integration".

---

## Sources

- [Infoblox — `infobloxopen/infoblox` Terraform provider (Registry)](https://registry.terraform.io/providers/infobloxopen/infoblox/latest/docs)
- [Infoblox — terraform-provider-infoblox (GitHub)](https://github.com/infobloxopen/terraform-provider-infoblox)
- [Infoblox Docs — About Infoblox NIOS Virtual Appliance for VMware](https://docs.infoblox.com/space/NVIG/35786250/About+Infoblox+NIOS+Virtual+Appliance+for+VMware)
- [Infoblox Docs — Installing the NIOS Virtual or Reporting Virtual Appliance](https://docs.infoblox.com/space/NVIG/35483668/Installing+the+NIOS+Virtual+or+Reporting+Virtual+Appliance)
- [Infoblox Docs — Introduction, IPAM Plug-In for VMware (Aria/vRA)](https://docs.infoblox.com/space/ipamvmware8x/52048987/Introduction)
- [Infoblox Docs — Installing Infoblox IPAM Plug-In for VMware](https://docs.infoblox.com/space/ipamvmware8x/52593807/Installing+Infoblox+IPAM+Plug-In+for+VMware)
- [Infoblox Docs — Cloud Network Automation (NIOS 9.0)](https://docs.infoblox.com/space/nios90/280407487)
- [Infoblox — Firewall Requirements for Infoblox Cloud Services (NIOS-X / 443)](https://docs.infoblox.com/space/BloxOneInfrastructure/873660456/Firewall+Requirements+for+Infoblox+Cloud+Services)
- [Terraform Registry — hashicorp/vsphere provider docs](https://registry.terraform.io/providers/hashicorp/vsphere/latest/docs)
- [Terraform Registry — vmware/nsxt provider docs](https://registry.terraform.io/providers/vmware/nsxt/latest/docs)
- Module contract: [`_module-contract.md`](./_module-contract.md)
- Architecture guide: [`VMware-LZ-Infoblox-DDI-Automation-Guide.md`](./VMware-LZ-Infoblox-DDI-Automation-Guide.md)
- Deploy chapter (OVA/CLI mechanics): [`../05-vmware.md`](../05-vmware.md)

---

## Optional: run this runbook through ServiceNow (governed path)

Every manual step here can be driven from a **ServiceNow Service Catalog item** instead of a shell: request → approval / separation-of-duties gate → **CPG Terraform Connector** apply of [`terraform/`](./terraform/README.md) on an in-boundary MID Server → **IntegrationHub REST** allocate/register over Infoblox WAPI/Universal DDI → the [`validation/`](./validation/README.md) scripts run by the MID Server as a **pass/fail gate** → **Service Graph Connector** CMDB reconcile → close with a full audit trail. Wire it per [`servicenow/ServiceNow-Orchestration.md`](./servicenow/ServiceNow-Orchestration.md) and stand up the importable records from [`servicenow-app/`](../servicenow-app/README.md); the model and control mapping are in [Chapter 7](../07-servicenow-orchestration.md). Secrets stay in a vault; the MID Server and credential path stay inside the ATO boundary.
