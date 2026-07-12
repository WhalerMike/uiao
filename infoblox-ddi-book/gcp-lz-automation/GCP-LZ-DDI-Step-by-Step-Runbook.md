# Google Cloud Landing Zone + Infoblox DDI — Step-by-Step Deployment Runbook

> **Companion to** [`GCP-LZ-Infoblox-DDI-Automation-Guide.md`](./GCP-LZ-Infoblox-DDI-Automation-Guide.md).
> That guide explains *why* the architecture is shaped the way it is; this runbook
> is the **"do exactly this, then this"** operational sequence that deploys it with
> the IaC package in this directory. Every command, variable name, resource name,
> port, IAM role, and output below is taken from the real module and its
> [`_module-contract.md`](./_module-contract.md) — nothing is invented. Where a
> value is genuinely environment-specific (image, machine type, region, CIDR) the
> runbook says **"supply your own"** rather than guessing.
>
> **Posture (fixed):** GCC-Moderate-equivalent posture on **commercial Google
> Cloud**. Data residency / personnel controls are delivered by **Assured
> Workloads** folders (a Stage-1 concern) — not switched on here.
>
> **Default path:** `deployment_model = "grid"` (vNIOS Grid, control plane inside
> the ATO boundary). The `universal_ddi` (Infoblox Portal / SaaS) path is shown in
> clearly-marked **⚠ UNIVERSAL DDI** callout boxes and always honors the
> `acknowledge_saas_boundary` guard.
>
> **Status of the IaC:** a coherent starter skeleton — structurally correct and
> guardrail-bearing, *not* a certified production module. Pin your own versions,
> confirm the image, and test in a sandbox project first.

---

## Prerequisites checklist

Confirm **all** of these before Phase 0. Boxes map to the phases that consume them.

- [ ] **Stage-1 landing zone already deployed.** A Google Cloud foundation
      (Terraform Example Foundation or Cloud Foundation Fabric / FAST) exists — org
      hierarchy, org policy, projects, and a **Shared VPC** in a host project — and
      publishes outputs. This module is **Stage 2**; it never builds Stage 1.
- [ ] **Stage-1 outputs available:** `host_project_id`, `shared_vpc_network` (name
      or self-link), `region`, and (optional) a Cloud DNS inbound forwarder IP.
- [ ] **Roles.** You (or the pipeline identity) can create resources in the host
      project, create IAM bindings in the discovered projects, and add Secret
      Manager secret versions. Discovery uses a *separate, least-privileged* SA
      (Phase 4).
- [ ] **Tooling:** `gcloud` CLI (recent), Terraform ≥ 1.5 (the module requires
      `>= 1.5.0, < 2.0.0` for `precondition` blocks), `jq`, `dig`/`nslookup`.
- [ ] **A project with Secret Manager** enabled for the module secrets.
- [ ] **A free, non-overlapping CIDR** inside the host VPC address plan for the
      dedicated `ddi-subnet` (`ddi_subnet_cidr`).
- [ ] **Licensing/Marketplace:** vNIOS BYOL token or Universal DDI subscription,
      DNS/DHCP/Grid/Threat-Defense licenses, and access to the vNIOS image (accept
      the Marketplace listing terms in the console for the `infoblox` image).
- [ ] **Explicit CIDRs** for firewall scoping — mgmt, DNS clients (spokes/on-prem),
      Grid peers/GM, monitoring. **Never `0.0.0.0/0`** (the module hard-fails on it).

---

## Phase 0 — Decisions & inventory

### Step 0.1 — Choose the control-plane model

The single most consequential decision. It sets **where the control plane lives
relative to your ATO boundary**.

| | `deployment_model = "grid"` (default) | `deployment_model = "universal_ddi"` |
|---|---|---|
| Control plane | vNIOS **Grid**, self-operated in-project | Infoblox **Portal / CSP** (SaaS) |
| Vs. ATO boundary | **Inside** | **Outside** |
| Data-plane members | vNIOS DNS members | NIOS-X servers |
| Outbound dependency | Grid VPN `1194/udp` + `2114/tcp` | **outbound `443` to `csp.infoblox.com`** |
| GCC-Moderate fit | **Boundary-clean — recommended default** | Requires authorization review |
| Code guard | none | hard-fails unless `acknowledge_saas_boundary = true` |

**Decision:** For a boundary-clean GCC-Moderate landing zone, choose **`grid`**. Only
choose `universal_ddi` after completing the FedRAMP/authorization review for the SaaS
control-plane egress (and confirming the Portal region suits any Assured Workloads
requirement).

**Verify:** Write the chosen `deployment_model` value down; it must match across
Terraform `terraform.tfvars` and the pipeline env (`DEPLOYMENT_MODEL`).

> **⚠ UNIVERSAL DDI callout.** If you selected `universal_ddi`, you must also set
> `acknowledge_saas_boundary = true` **and** be able to justify the outbound-443
> dependency to `csp.infoblox.com`. Leaving the ack `false` (the default) is a
> deliberate hard-fail — see Phase 6.

### Step 0.2 — Gather Stage-1 outputs into shell variables

```bash
# Fill these from your Stage-1 foundation outputs.
export HOST_PROJECT_ID="hostproj-shared-vpc"        # host_project_id
export SHARED_VPC_NETWORK="vpc-hub"                  # shared_vpc_network (name or self-link)
export REGION="us-central1"                          # supply your own region
export DDI_SUBNET_CIDR="10.10.4.0/27"                # supply your own free, non-overlapping CIDR
export SECRET_PROJECT_ID="$HOST_PROJECT_ID"          # project holding Secret Manager secrets
export CLOUD_DNS_INBOUND_IP=""                        # optional — set after Phase 9.1
```

**Verify:** `gcloud compute networks describe "$SHARED_VPC_NETWORK" --project "$HOST_PROJECT_ID" --format='value(name)'`
prints the network name.

---

## Phase 1 — Tooling & auth

### Step 1.1 — Install and check tooling

```bash
gcloud version
terraform version          # expect >= 1.5.0, < 2.0.0
jq --version ; dig -v 2>&1 | head -1
```

**Verify:** `terraform version` prints a 1.5+ build; `gcloud version` prints the SDK.

### Step 1.2 — Log in and set the project

```bash
gcloud auth login
gcloud auth application-default login     # ADC for Terraform
gcloud config set project "$HOST_PROJECT_ID"
gcloud config get-value project
```

**Verify:** `gcloud config get-value project` echoes `$HOST_PROJECT_ID`.

### Step 1.3 — Enable required APIs

```bash
gcloud services enable compute.googleapis.com dns.googleapis.com \
  secretmanager.googleapis.com iam.googleapis.com --project "$HOST_PROJECT_ID"
```

**Verify:** `gcloud services list --enabled --project "$HOST_PROJECT_ID" --filter="config.name:(compute OR dns OR secretmanager)"`
lists the three APIs.

### Step 1.4 — Create the Terraform remote-state backend (GCS)

```bash
export TFSTATE_BUCKET="tf-state-${HOST_PROJECT_ID}"
gcloud storage buckets create "gs://${TFSTATE_BUCKET}" \
  --project "$HOST_PROJECT_ID" --location "$REGION" \
  --uniform-bucket-level-access
gcloud storage buckets update "gs://${TFSTATE_BUCKET}" --versioning
```

**Verify:** `gcloud storage buckets describe "gs://${TFSTATE_BUCKET}" --format='value(versioning.enabled)'`
returns `True`. GCS provides state locking natively.

---

## Phase 2 — Consume Stage-1 outputs

The module learns about the host VPC **only** through Stage-1 outputs — it never
queries or mutates Stage-1-owned resources. Two equivalent ways to fetch them:

### Step 2.1 — Option A: `terraform_remote_state` data source (preferred)

The `examples/hub-integration/main.tf` reads the foundation state directly:

```hcl
data "terraform_remote_state" "lz" {
  backend = "gcs"
  config = {
    bucket = "tf-state-example"          # supply your own
    prefix = "landing-zone/networking"
  }
}

# then, in the module block:
#   host_project_id    = data.terraform_remote_state.lz.outputs.host_project_id
#   shared_vpc_network = data.terraform_remote_state.lz.outputs.shared_vpc_network
```

**Verify:** `terraform console` → `data.terraform_remote_state.lz.outputs.host_project_id`
prints the host project ID.

### Step 2.2 — Option B: `gcloud` lookups (provider-agnostic)

If Stage 1 does not share Terraform state, resolve the same facts with `gcloud`:

```bash
# shared_vpc_network self-link
gcloud compute networks describe "$SHARED_VPC_NETWORK" --project "$HOST_PROJECT_ID" \
  --format='value(selfLink)'

# confirm this project is the Shared VPC host
gcloud compute shared-vpc get-host-project "$HOST_PROJECT_ID" 2>/dev/null || \
  gcloud compute shared-vpc organizations list-host-projects 2>/dev/null | head

# subnets already in the VPC (to pick a non-overlapping ddi_subnet_cidr)
gcloud compute networks subnets list --project "$HOST_PROJECT_ID" \
  --filter="network:$SHARED_VPC_NETWORK" --format='table(name,region,ipCidrRange)'
```

**Verify:** each command prints a value; feed them into the tfvars in Phase 5. These
map to variables `host_project_id`, `shared_vpc_network`, and (for `ddi_subnet_cidr`)
a free range.

---

## Phase 3 — Secrets in Secret Manager

The module **reads existing** Secret Manager secret versions
(`data "google_secret_manager_secret_version"`); it never creates them and never
emits them as plaintext outputs. Create the secrets, then add versions.

### Step 3.1 — Create the secrets

```bash
for S in ddi-vnios-admin-password ddi-vnios-temp-license ddi-grid-shared-secret; do
  gcloud secrets create "$S" --project "$SECRET_PROJECT_ID" --replication-policy=automatic \
    || echo "$S exists"
done
```

### Step 3.2 — Add secret versions (the values)

```bash
# Admin password (bootstrapped into vNIOS/NIOS-X via the startup-script).
printf '%s' '<STRONG_ADMIN_PASSWORD>' | \
  gcloud secrets versions add ddi-vnios-admin-password --project "$SECRET_PROJECT_ID" --data-file=-

# vNIOS temporary license bundle for first boot.
printf '%s' 'vnios dns dhcp grid enterprise' | \
  gcloud secrets versions add ddi-vnios-temp-license --project "$SECRET_PROJECT_ID" --data-file=-

# Grid shared secret used to join GCP members to the Grid (grid path).
printf '%s' '<GRID_SHARED_SECRET>' | \
  gcloud secrets versions add ddi-grid-shared-secret --project "$SECRET_PROJECT_ID" --data-file=-
```

> **⚠ UNIVERSAL DDI callout.** For `universal_ddi`, also create + version the Portal
> join token (NIOS-X hosts phone home to `csp.infoblox.com` over 443 with it):
> ```bash
> gcloud secrets create ddi-uddi-join-token --project "$SECRET_PROJECT_ID" --replication-policy=automatic
> printf '%s' '<PORTAL_JOIN_TOKEN>' | \
>   gcloud secrets versions add ddi-uddi-join-token --project "$SECRET_PROJECT_ID" --data-file=-
> ```

**Verify:**
`gcloud secrets list --project "$SECRET_PROJECT_ID" --filter="name:ddi-"`
lists the secret ids you created.

> **Troubleshooting — permission denied on `versions add`.** You need
> `roles/secretmanager.admin` (or `secretVersionAdder`) on the secret/project. The
> identity running Terraform needs `roles/secretmanager.secretAccessor` to read at
> plan time. A `PERMISSION_DENIED` right after granting usually means the binding
> has not propagated — wait ~1 minute and retry.

---

## Phase 4 — Discovery service account + least-privilege roles

The GCP→Infoblox IPAM sync uses a **separate, least-privileged** service account
(`ddi-disco`). The Terraform module creates it when
`discovery_identity_type = "service_account"`; it also supports an existing SA email.
Roles are scoped per contract §5 — **no `owner`, no `editor`, no broad `viewer`.**

| Role | Scope | When |
|---|---|---|
| `roles/compute.networkViewer` | discovered project(s) | always |
| `roles/dns.reader` | discovered project(s) | always |
| `roles/dns.admin` | project(s) holding zones | only if `enable_record_write` |

### Step 4.1 — (Optional) pre-create the discovery SA

The module creates `ddi-disco` for you when
`discovery_identity_type = "service_account"`. If you want it pre-created (or you use
`existing_service_account`):

```bash
gcloud iam service-accounts create ddi-disco --project "$HOST_PROJECT_ID" \
  --display-name "Infoblox DDI discovery SA"
export DISCO_SA_EMAIL="ddi-disco@${HOST_PROJECT_ID}.iam.gserviceaccount.com"
```

**Verify:** `gcloud iam service-accounts describe "$DISCO_SA_EMAIL"` prints the SA.
This becomes the module output `discovery_service_account_email`.

### Step 4.2 — Read roles on each discovered project (always)

> On the **Terraform** path these are created for you from `discovered_project_ids`
> (resources `google_project_iam_member.disco_network_viewer` / `_dns_reader`) — you
> do not need the loop; just set the variable. Shown for the out-of-band / existing-SA case:

```bash
for P in "$HOST_PROJECT_ID" "<service-project-id-1>" "<service-project-id-2>"; do
  gcloud projects add-iam-policy-binding "$P" \
    --member "serviceAccount:$DISCO_SA_EMAIL" --role roles/compute.networkViewer
  gcloud projects add-iam-policy-binding "$P" \
    --member "serviceAccount:$DISCO_SA_EMAIL" --role roles/dns.reader
done
```

**Verify:**
`gcloud projects get-iam-policy "$HOST_PROJECT_ID" --flatten=bindings --filter="bindings.members:$DISCO_SA_EMAIL" --format='table(bindings.role)'`
shows only `roles/compute.networkViewer` + `roles/dns.reader` (and `dns.admin` if opted in).

### Step 4.3 — (Opt-in) `roles/dns.admin` for record write-back

Only when Infoblox writes records into Cloud DNS (`enable_record_write = true`, scope =
the zone-holding project). On the Terraform path set `dns_admin_project_ids`. Manual:

```bash
gcloud projects add-iam-policy-binding "<dns-zone-project>" \
  --member "serviceAccount:$DISCO_SA_EMAIL" --role roles/dns.admin
```

> **Troubleshooting — discovery finds nothing.** The usual cause is
> `compute.networkViewer` missing on a target project (Step 4.2). If record write-back
> fails, the `dns.admin` binding (4.3) is missing or not yet propagated. Prefer a
> **custom role** (contract §5 / `discovery.tf`) for the tightest blast radius.

---

## Phase 5 — Configure the module (`terraform.tfvars`)

Start from `examples/hub-integration/main.tf`, then externalize the values into a
`terraform.tfvars` next to the Terraform module. Every variable below is real.

```hcl
# terraform.tfvars — Stage-2 Infoblox DDI (grid, commercial GCP, GCC-Moderate)

# --- Basics / boundary ---
name_prefix        = "ddi"                 # -> ddi-subnet, ddi-member-a, ddi-disco
region             = "us-central1"         # supply your own region
environment        = "prod"                # dev | test | prod
deployment_model   = "grid"                # boundary-clean default
compliance_profile = "gcc-moderate"
# acknowledge_saas_boundary left false — not needed for grid.

# --- From Stage-1 outputs ---
host_project_id    = "hostproj-shared-vpc"
shared_vpc_network = "vpc-hub"             # name or self-link
secret_project_id  = "hostproj-shared-vpc"

# --- Dedicated DDI subnet (must fit host VPC, not overlap) ---
ddi_subnet_cidr = "10.10.4.0/27"

# --- Members: 2 across zones a and b (HA) ---
member_count = 2
zones        = ["a", "b"]                  # -> us-central1-a, us-central1-b

# --- Machine type + image: supply your own (do NOT invent) ---
machine_type = "n1-standard-4"             # N1 series; verify model mapping + quota
vnios_image = {
  project = "<infoblox-image-project>"     # from `gcloud compute images list`
  family  = "<vnios-image-family>"         # OR: name = "<pinned-image>"
}

# --- Firewall source scoping (never 0.0.0.0/0) ---
mgmt_source_ranges = ["10.10.0.0/24"]                    # jump host/bastion subnet
dns_client_ranges  = ["10.20.0.0/16", "10.30.0.0/16"]   # service-project spokes
grid_peer_ranges   = ["10.10.4.0/27", "192.168.100.0/24"] # DDI subnet + on-prem GM (grid only)

# --- Grid join (usual pattern: join GCP members to the on-prem GM) ---
grid_name       = "CorpGrid"
grid_master_vip = "192.168.100.10"         # on-prem Grid Master VIP; null => first member is GM (lab only)

# --- DNS integration (§8) ---
inbound_forwarding_enabled = true
cloud_dns_inbound_ip       = "10.10.2.4"   # a Cloud DNS inbound forwarder IP (read after Phase 9.1)
enterprise_forward_domains = ["corp.example.com.", "10.in-addr.arpa."]
ddi_anycast_vip            = "10.10.4.10"  # advertised from both members
# infoblox_forward_domains defaults to ["googleapis.com","run.app"]

# --- Discovery SA + least-privilege IAM (§5) ---
discovery_identity_type = "service_account"
discovered_project_ids  = ["hostproj-shared-vpc", "<service-project-id-1>"]
enable_record_write     = false           # read-only discovery by default
# dns_admin_project_ids = [...]            # only if enable_record_write = true

# --- Spoke DNS peering (opt-in) ---
spoke_networks           = []              # e.g. ["projects/svc1/global/networks/vpc-svc1"]
enable_spoke_dns_peering = false

# --- Secret ids (match Phase 3) ---
admin_password_secret_id = "ddi-vnios-admin-password"
temp_license_secret_id   = "ddi-vnios-temp-license"
grid_shared_secret_id    = "ddi-grid-shared-secret"

labels = { owner = "network-platform", costcenter = "cc-1234" }
```

**What the key variables do (all real):**

- `deployment_model` / `acknowledge_saas_boundary` — the boundary switch + its guard.
- `shared_vpc_network` — normalized to a self-link; the `ddi-subnet` is created inside it.
- `member_count` + `zones` — members are round-robined over `${region}-${letter}`;
  ≤ one-zone-per-member yields the clean `ddi-member-a` / `ddi-member-b` names.
- `grid_peer_ranges` — **required for grid** (a `terraform_data.firewall_guard`
  precondition fails the plan if `grid` is selected and this is empty).
- `mgmt_source_ranges` / `dns_client_ranges` — enforced non-empty and **must not**
  contain `0.0.0.0/0` (variable `validation`).
- `ddi_anycast_vip` — becomes real only after Grid formation (Phase 7); until then
  outputs fall back to `dns_server_ips` (member internal IPs).

**Boundary-guard behavior (grid):** with `deployment_model = "grid"` the
`terraform_data.boundary_guard` precondition passes silently and no egress-443 Portal
rule is created.

> **⚠ UNIVERSAL DDI callout — tfvars deltas.** To run the SaaS path:
> ```hcl
> deployment_model          = "universal_ddi"
> acknowledge_saas_boundary = true            # REQUIRED — false hard-fails the plan
> saas_join_token_secret_id = "ddi-uddi-join-token"
> infoblox_portal_url       = "https://csp.infoblox.com"   # outbound 443 required
> # grid_master_vip / grid_shared_secret_id are unused on this path
> ```
> With ack `false`, `terraform plan` aborts with the `BOUNDARY VIOLATION` message
> pointing to the authorization review — resources `ddi-niosx-*` and
> `null_resource.portal_enroll` never plan.

---

## Phase 6 — Deploy

### Step 6.1 — Confirm the image and machine type

Discover the real image (never invent it), and accept the Marketplace listing terms
for the `infoblox` image in the console if required:

```bash
gcloud compute images list --filter="family~infoblox OR name~vnios" --show-deprecated \
  --format='table(name, family, selfLink.scope(projects):label=PROJECT)'
```

**Verify:** the output shows an image; set `vnios_image.project` + `family`/`name` and
`machine_type` accordingly in `terraform.tfvars`.

### Step 6.2 — `init` with the remote backend

```bash
cd infoblox-ddi-book/gcp-lz-automation/terraform
terraform init \
  -backend-config="bucket=$TFSTATE_BUCKET" \
  -backend-config="prefix=infoblox-ddi/prod"
```

**Verify:** `Terraform has been successfully initialized!` and the `google`,
`infobloxopen/infoblox`, and `null` providers resolve (per `versions.tf`).

### Step 6.3 — `plan` (guards are evaluated here)

```bash
terraform plan -input=false -out=tfplan
```

**Expected:** the plan creates `ddi-subnet`, the VPC firewall rules, `ddi-member-a` /
`ddi-member-b` (reserved IPs + instances), the `ddi-disco` SA + read bindings, the
inbound Cloud DNS policy, the enterprise forwarding zones, and the
`infoblox_zone_forward` objects (if `cloud_dns_inbound_ip` set). The boundary guard,
the grid-peer precondition, and firewall CIDR scoping are checked at **plan** time.

**Verify:** plan summary shows the expected adds and **no** `0.0.0.0/0` sources on the
allow rules (the deny-all rules use `0.0.0.0/0` deliberately).

### Step 6.4 — `apply`

```bash
terraform apply -input=false -auto-approve tfplan
```

**Expected outputs (contract §7):**

```bash
terraform output
# ddi_subnet_id                   = "projects/.../subnetworks/ddi-subnet"
# dns_server_ips                  = ["10.10.4.4", "10.10.4.5"]   # member internal IPs
# ddi_anycast_vip                 = "10.10.4.10"                  # null until Grid advertises it
# grid_master_ip                  = "192.168.100.10"             # on-prem GM (grid only)
# discovery_service_account_email = "ddi-disco@hostproj-shared-vpc.iam.gserviceaccount.com"
```

**Cross-zone members:** confirm the two members landed in different zones:

```bash
gcloud compute instances list --project "$HOST_PROJECT_ID" \
  --filter="name~ddi-member" --format='table(name, zone, networkInterfaces[0].networkIP)'
```

**Verify:** `ddi-member-a` shows zone `…-a`, `ddi-member-b` shows zone `…-b`.

> **Troubleshooting — grid plan fails immediately.** *"deployment_model='grid'
> requires grid_peer_ranges"* → set `grid_peer_ranges` (Grid members/GM ranges).
>
> **Troubleshooting — image not found / access denied.** Confirm the image project +
> family/name from Step 6.1 and that your identity can read the image project. For a
> Marketplace image, accept the listing terms in the console first.
>
> **Troubleshooting — DNS-object apply fails.** `infoblox_zone_forward` needs a
> reachable Grid/NIOS WAPI endpoint. Members are not yet Grid-joined at first apply;
> either configure the `infoblox` provider `server` to the on-prem GM, or run the
> DNS-object resources in a **second phase** after Phase 7 (use `-target` or a
> dependent module). This ordering is by design.

---

## Phase 7 — Grid formation / Universal DDI onboarding

The instances exist, but the **control plane is not yet formed**. `ddi_anycast_vip`
and `grid_master_ip` become operationally real only after this phase.

### Step 7.1 — Grid path: form / join the Grid

Each member booted with a startup-script (`#infoblox-config`) carrying the temp
license, admin password, and grid-join parameters from Secret Manager. Complete
formation on the members:

- **Usual GCP pattern:** the on-prem Grid Master (`grid_master_vip`) is authoritative;
  the GCP members join as **Grid members** over `1194/udp` + `2114/tcp` (across
  Interconnect/HA VPN). Confirm each member appears in the Grid Manager UI under your
  `grid_name` (e.g. `CorpGrid`).
- **Lab/greenfield:** if `grid_master_vip = null`, the first member (`ddi-member-a`)
  initializes the Grid as GM; the second joins it.
- **Assign the anycast VIP** (`ddi_anycast_vip`, e.g. `10.10.4.10`) as a shared DNS
  service address advertised from both members, so spokes use one stable resolver.

**Verify (WAPI, from a mgmt host):**

```bash
export GRID_MASTER="<gm-mgmt-ip-or-fqdn>"          # your Grid Master (grid_master_ip)
export INFOBLOX_USERNAME="admin"                    # WAPI user
export INFOBLOX_PASSWORD="<from-secret-manager>"    # ddi-vnios-admin-password / WAPI cred
curl -fsS -u "$INFOBLOX_USERNAME:$INFOBLOX_PASSWORD" \
  "https://$GRID_MASTER/wapi/v2.12/member?_return_fields%2B=host_name,service_status"
```

Both GCP members show `service_status` running for DNS. Confirm the exact WAPI
object/field names against `<grid-master>/wapidoc/` (over HTTPS) for your NIOS version.

> **⚠ UNIVERSAL DDI callout — enroll NIOS-X to the Portal.** Instead of Grid
> formation, each `ddi-niosx-*` host self-enrolls to `csp.infoblox.com` over 443 using
> the join token from its startup-script. The `null_resource.portal_enroll`
> (Terraform) is the explicit API seam — replace its placeholder with the real CSP
> REST call, then confirm in the Portal inventory:
> ```bash
> curl -fsS -H "Authorization: Token $INFOBLOX_CSP_TOKEN" \
>   "https://csp.infoblox.com/api/infra/v1/hosts?_filter=display_name=='ddi-niosx-1'"
> ```

**Verify:** members/hosts report healthy in the Grid Manager UI or the Portal, and the
anycast VIP answers (tested in Phase 11).

---

## Phase 8 — Cloud discovery adapter

GCP IAM (Phase 4) grants the SA; the **Infoblox side** of discovery is configured on
the control plane — there is no `infoblox_vdiscovery_job` provider resource, so this is
an explicit API/UI handoff (the module documents the seam in `discovery.tf`).

### Step 8.1 — Grid path: create a GCP vDiscovery job (WAPI)

Point Cloud Network Automation at the org/folder/project scope, authenticating with the
`ddi-disco` SA (a service-account key stored in Secret Manager, or a workload-identity
binding where supported). Illustrative WAPI handoff:

```bash
curl -fsS -u "$INFOBLOX_USERNAME:$INFOBLOX_PASSWORD" \
  -X POST "https://$GRID_MASTER/wapi/v2.12/vdiscoverytask" \
  -H 'Content-Type: application/json' \
  -d '{"name":"gcp-disco","member":"infoblox.localdomain","credential_type":"GCP"}'
```

Schedule it to run on a cadence (e.g. hourly) so IPAM tracks GCP reality. Confirm the
exact object/fields against `<grid-master>/wapidoc/` for your NIOS version.

> **⚠ UNIVERSAL DDI callout.** Configure a Portal **Universal Cloud** GCP source using
> the same `ddi-disco` credential via the CSP API/UI; the discovery job lives in the
> SaaS control plane.

**Verify:** run the Stage-3 discovery check (Phase 11) — it asserts the job exists, is
not in `ERROR`/`WARNING`, and ran within `STALE_THRESHOLD_MIN`.

---

## Phase 9 — DNS integration

Two conditional paths meet at Cloud DNS (independent VPC-level constructs).

### Step 9.1 — Inbound Cloud DNS server policy + forwarder IPs

`dns.tf` creates a `google_dns_policy` with `enable_inbound_forwarding` on the host
VPC (when `inbound_forwarding_enabled = true`). Cloud DNS then allocates inbound
forwarder IPs from the subnet ranges. Read one and feed it back as
`cloud_dns_inbound_ip`:

```bash
gcloud dns policies describe ddi-inbound-policy --project "$HOST_PROJECT_ID" \
  --format='value(networks)'    # then inspect the allocated inbound forwarder IPs
# Alternatively list the forwarding IPs from the subnet/policy in the console.
```

**Verify:** you have an inbound forwarder IP; set `cloud_dns_inbound_ip` in tfvars so
the `infoblox_zone_forward` objects (Infoblox → Cloud DNS for `googleapis.com`) apply.

### Step 9.2 — Outbound: forwarding zones (enterprise → Infoblox)

`dns.tf` creates one `google_dns_managed_zone` (forwarding) per domain in
`enterprise_forward_domains`, each with `target_name_servers` = the DDI resolver
(anycast VIP or member IPs). GCP VMs then resolve corp/on-prem names via Infoblox while
`*.googleapis.com` and Cloud DNS private zones keep resolving natively.

**Verify:**

```bash
gcloud dns managed-zones list --project "$HOST_PROJECT_ID" --filter="name~ddi-fwd" \
  --format='table(name, dnsName, forwardingConfig.targetNameServers[].ipv4Address)'
```

Returns the forwarding zones targeting the DDI members.

> **Type-2 return route.** For private routing to members reached over Interconnect/HA
> VPN, the VPC must **return-route `35.199.192.0/19`** back through the same VPC. This
> is a Stage-1 network concern; confirm it exists, or corp names will time out.

### Step 9.3 — Split-horizon: peering zones for spokes (opt-in)

When `enable_spoke_dns_peering = true` and `spoke_networks` is set, `dns.tf` creates
`google_dns_managed_zone` (peering) so service-project VPCs resolve enterprise domains
via the host VPC's forwarding config. On the Infoblox side, matching conditional
forwarders (`infoblox_zone_forward`) send Google-service names back to the inbound IPs.

**Verify:**
`gcloud dns managed-zones list --project "$HOST_PROJECT_ID" --filter="name~ddi-peer"`
lists the peering zones.

> **Troubleshooting — firewall blocking 53/1194/2114.** If DNS times out or Grid
> members won't converge, confirm the firewall rules exist and sources match your
> ranges:
> `gcloud compute firewall-rules list --project "$HOST_PROJECT_ID" --filter="name~ddi-fw" --format='table(name,direction,priority,sourceRanges.list(),allowed[].map().firewall_rule().list())'`.
> The explicit `ddi-fw-deny-all-out` (priority 65534) overrides GCP's implied
> allow-all egress — so the `ddi-fw-ntp-dns-out` and `ddi-fw-metadata-out` allows must
> be present for time sync / recursion / metadata DNS.

---

## Phase 10 — IPAM automation

Because discovery imports GCP **labels/tags as extensible attributes (EAs)**, IPAM
becomes an API the platform consumes.

### Step 10.1 — Onboard projects & confirm networks appear

vDiscovery walks the scope → VPCs → subnets and populates Infoblox IPAM as
networks/containers, with discovered instances as records. In a Shared VPC the subnets
are defined in the **host project** but consumed by **service projects** — discover the
host project for the address space and the service projects for the workloads.

**Verify:**

```bash
curl -fsS -u "$INFOBLOX_USERNAME:$INFOBLOX_PASSWORD" \
  "https://$GRID_MASTER/wapi/v2.12/network?_return_fields%2B=network,comment&network_view=default"
```

GCP VPC/subnet CIDRs (including `ddi_subnet` `10.10.4.0/27`) appear as `network` objects.

### Step 10.2 — Label-driven allocation & reclaim-on-delete

Keyed on `env` / `owner` / `app` labels mapped to network views / EAs, provisioning
pipelines can carve the next free subnet from the correct container (via WAPI
`nextavailablenetwork`) and feed that CIDR into the workload's own IaC. Because DHCP for
most GCP subnets is Google-managed, IPAM tracks those as discovered/leased-by-platform
while Infoblox stays authoritative for allocations, reservations, and DNS. Schedule
discovery so a subnet deleted in GCP is reconciled on the next sync.

**Verify:** the IPAM conflict gate (Phase 11) reports no overlaps after a sync.

---

## Phase 11 — Validation gates

Run each `validation/*.sh` with its env-var contract. Any non-zero exit fails the
Stage-3 pipeline gate.

### Step 11.1 — DNS resolution (`dns-validation.sh`)

```bash
cd infoblox-ddi-book/gcp-lz-automation/validation
export DDI_VIP="10.10.4.10"                                  # ddi_anycast_vip
export TEST_FQDN="app01.corp.example.com"                    # enterprise A record
export EXPECTED_IP="10.20.5.10"                              # its expected answer
export PRIVATELINK_FQDN="db.internal.corp.example.com"       # optional: a Cloud DNS private name
bash dns-validation.sh
```

**Proves:** the DDI VIP answers an enterprise A record with `EXPECTED_IP`, and a
Google-service / Cloud DNS private name resolves through the conditional-forward path to
a **private** (RFC1918) IP. **Fails when** no/wrong answer, or that name returns a
public IP (forward path bypassed). **Verify:** ends with `All DNS validation checks passed.`

### Step 11.2 — Discovery-sync freshness (`discovery-sync-check.sh`)

```bash
export DDI_API_FLAVOR="nios"                # grid default; "universal_ddi" for SaaS
export GRID_MASTER="<grid-master>"          # WAPI host (grid_master_ip)
export INFOBLOX_USERNAME="admin"            # from Secret Manager
export INFOBLOX_PASSWORD="<from-secret-manager>"
export STALE_THRESHOLD_MIN="1440"           # 24h
bash discovery-sync-check.sh
```

**Proves:** the vDiscovery task completed successfully and recently. **Fails when** a
task is `ERROR`/`WARNING`/`FAILED` or the last success is older than the threshold.
**Verify:** ends with `Discovery-sync freshness check passed.`

> **⚠ UNIVERSAL DDI callout.** Set `DDI_API_FLAVOR=universal_ddi` and provide
> `INFOBLOX_CSP_TOKEN` (from Secret Manager); the check queries `csp.infoblox.com`
> cloud-discovery jobs. Only exercise this when `acknowledge_saas_boundary = true`.

### Step 11.3 — IPAM conflict (`ipam-conflict-check.sh`)

```bash
export GRID_MASTER="<grid-master>"
export INFOBLOX_USERNAME="admin"
export INFOBLOX_PASSWORD="<from-secret-manager>"
export NETWORK_VIEW="default"
# optional: export CANDIDATE_NETWORK="10.10.4.0/27"   # test one CIDR for overlap
bash ipam-conflict-check.sh
```

**Proves:** no overlapping/duplicate `network` objects (server-side candidate query or
whole-view pairwise scan). **Fails when** any overlap is found. **Verify:** ends with
`IPAM conflict check passed.`

> **Troubleshooting — anycast not converging.** If `dns-validation.sh` intermittently
> fails, the anycast VIP may not be advertised from both members yet (Phase 7), or a
> member is unhealthy. Confirm both members answer directly:
> `dig +short @10.10.4.4 app01.corp.example.com` and `@10.10.4.5` (the two
> `dns_server_ips`) before blaming the VIP.

---

## Phase 12 — Wire into GitOps

Both CI renderings (`pipelines/github-actions-gcp-ddi.yml`,
`pipelines/cloudbuild-gcp-ddi.md`) run the same three stages —
**Foundation (read Stage-1) → DDI (Stage-2 apply) → Validate (Stage-3)** — with
**Workload Identity Federation** and **no exported service-account key**.

### Step 12.1 — Create the Workload Identity Pool + Provider (GitHub)

```bash
# Pool + provider trusting the GitHub OIDC issuer.
gcloud iam workload-identity-pools create gh-pool \
  --project "$HOST_PROJECT_ID" --location global --display-name "GitHub OIDC pool"

gcloud iam workload-identity-pools providers create-oidc gh-provider \
  --project "$HOST_PROJECT_ID" --location global --workload-identity-pool gh-pool \
  --display-name "GitHub provider" \
  --issuer-uri "https://token.actions.githubusercontent.com" \
  --attribute-mapping "google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition "assertion.repository=='<org>/<repo>'"

# Deploy SA the pipeline impersonates (separate from ddi-disco; more-privileged).
gcloud iam service-accounts create ddi-deploy --project "$HOST_PROJECT_ID" \
  --display-name "Infoblox DDI pipeline deploy SA"

# Let the WIF principal impersonate the deploy SA.
export POOL_ID="$(gcloud iam workload-identity-pools describe gh-pool --project "$HOST_PROJECT_ID" --location global --format='value(name)')"
gcloud iam service-accounts add-iam-policy-binding \
  "ddi-deploy@${HOST_PROJECT_ID}.iam.gserviceaccount.com" \
  --role roles/iam.workloadIdentityUser \
  --member "principalSet://iam.googleapis.com/${POOL_ID}/attribute.repository/<org>/<repo>"
```

Grant `ddi-deploy` least-privilege IAM on the deploy scope (create the DDI subnet /
firewall / instances; read Stage-1 state bucket; `secretAccessor` on the Infoblox
secrets) — **separate and more-privileged** than the discovery `ddi-disco` SA.

**Verify:**
`gcloud iam workload-identity-pools providers describe gh-provider --project "$HOST_PROJECT_ID" --location global --workload-identity-pool gh-pool`
prints the provider with your repo condition.

### Step 12.2 — Wire pipeline vars

Set repo/environment **vars** `WIF_PROVIDER` (the provider resource name),
`DEPLOY_SA_EMAIL` (`ddi-deploy@…`), `TFSTATE_BUCKET`, `SECRET_PROJECT_ID`,
`LZ_STATE_BUCKET`/`LZ_STATE_PREFIX`, and the DNS test inputs. The job sets
`permissions: id-token: write`. Infoblox WAPI creds come from Secret Manager
(`infoblox-wapi-username`/`infoblox-wapi-password`) at run time.

> **Cloud Build:** run the build as the deploy SA and gate `prod` with a manual
> approval on the trigger. See `pipelines/cloudbuild-gcp-ddi.md`.

### Step 12.3 — The boundary gate & promotion flow

Both pipelines carry `DEPLOYMENT_MODEL` (`grid`) and `ACKNOWLEDGE_SAAS_BOUNDARY`
(`false`). A gate step **hard-fails before init** if `deployment_model = universal_ddi`
and the ack is not `true` — so the SaaS path is never even planned without a review
(the Terraform guard enforces it again).

Promotion: **PR → plan-only** (validate skipped); **dev sandbox →** `workflow_dispatch`
with `apply=true` + full validation; **test →** same with environment approval;
**prod →** required reviewers / manual approval gate entry. Each env uses a distinct
state prefix `infoblox-ddi/<env>`.

**Verify:** open a PR touching `terraform/**` — the `ddi` job runs `plan` only and
`validate` is skipped; merge to `main` (or dispatch `apply=true`) runs `apply` then the
three validation scripts.

> **Troubleshooting — boundary guard tripping in CI.** A red "Enforce SaaS boundary
> acknowledgement" step means `DEPLOYMENT_MODEL=universal_ddi` with
> `ACKNOWLEDGE_SAAS_BOUNDARY!=true`. This is intended — complete the authorization
> review and set the ack, or switch back to `grid`.

---

## Phase 13 — Day-2 & rollback

- **Upgrades.** Patch NIOS/NIOS-X on the vendor cadence; in a Grid, **upgrade the Grid
  Master before the GCP members** (rolling, zone by zone). Universal DDI scales by
  adding NIOS-X hosts behind the same service (raise `member_count`, re-apply).
- **GMC failover game-day.** Exercise Grid Master Candidate promotion; confirm the
  anycast VIP keeps answering when one member is stopped:
  `gcloud compute instances stop ddi-member-a --zone "${REGION}-a" --project "$HOST_PROJECT_ID"`
  then re-run `dns-validation.sh` against the VIP. Restart with `gcloud compute instances start`.
- **Drift detection.** A scheduled pipeline re-runs `terraform plan`; any non-empty plan
  is drift (a hand-made subnet, an edited firewall rule, a forwarding zone changed in the
  console) and raises a reconcile PR. Because Git is the source of record, remediation is
  "revert to desired state."
- **Secret rotation.** Rotate the admin password / temp license by adding a new Secret
  Manager version. Note `grid.tf`/`universal_ddi.tf` set
  `lifecycle { ignore_changes = [metadata["startup-script"], metadata["user-data"]] }`,
  so a rotation does **not** silently re-bootstrap running members — re-bootstrap is a
  deliberate action.
- **Teardown cautions.** `terraform destroy` will remove the members, `ddi-subnet`, the
  firewall rules, the Cloud DNS policy/zones, and `ddi-disco`. **Before destroying:**
  remove any spoke peering/forwarding you pointed at the VIP (Phase 9) or those spokes
  lose resolution; drain the members from the Grid first so the GM does not flag missing
  members; and confirm no workload still depends on the anycast VIP. Destroy is scoped to
  Stage-2 only — it must **never** touch Stage-1 host/Shared-VPC resources.

---

## End-to-end validation checklist

Run top-to-bottom after Phase 11; every item should pass before calling the layer
production-ready.

- [ ] `terraform output` shows `ddi_subnet_id`, `dns_server_ips`, `ddi_anycast_vip`,
      `grid_master_ip` (grid), `discovery_service_account_email`.
- [ ] Members `ddi-member-a` / `ddi-member-b` are in **different zones** and Grid-joined
      (or NIOS-X hosts enrolled to the Portal).
- [ ] Firewall rules carry exactly the contract ports; no allow source is `0.0.0.0/0`;
      `ddi-fw-deny-all-in` / `ddi-fw-deny-all-out` at priority 65534 present; metadata
      egress open.
- [ ] `ddi-disco` holds `compute.networkViewer` + `dns.reader` on each discovered
      project and **nothing** broader (no `owner`/`editor`/broad `viewer`).
- [ ] Secret Manager holds the admin password, temp license, grid shared secret (and
      Portal join token for uddi) — none in Terraform state as plaintext.
- [ ] `dns-validation.sh` passes (enterprise A + Cloud DNS forward path).
- [ ] `discovery-sync-check.sh` passes (job fresh, not errored).
- [ ] `ipam-conflict-check.sh` passes (no overlapping CIDRs).
- [ ] Failover: stopping one member leaves the anycast VIP answering.
- [ ] The `35.199.192.0/19` return route exists for Type-2 private forwarding.
- [ ] Pipeline: PR = plan-only; merge/apply = apply + validate; prod behind approval.
- [ ] `universal_ddi` selected? — `acknowledge_saas_boundary = true`, the authorization
      review is on file, and outbound 443 to `csp.infoblox.com` is documented.

---

## Appendix A — Variable Worksheets (fill-in forms)

Copy each block, replace every `____` (and any `<placeholder>`) with your value, and
keep the rest. Fields marked **REQUIRED** have no default — the plan/deploy fails
without them. The trailing comment gives the **source** of each value:

- **you choose** — a design decision (region, CIDRs, names)
- **Stage-1 output** — comes from the foundation (Phase 2)
- **generated** — a command produces it (`gcloud …`) or a Stage-2 output does (Phase 6)
- **existing** — an already-provisioned resource (e.g. your secret project)

### A.1 Terraform — `terraform/terraform.tfvars`

```hcl
# ---- REQUIRED (no default) ----
region             = "____"   # you choose — GCP region (e.g. us-central1)
host_project_id    = "____"   # Stage-1 output: host_project_id (Shared VPC host)
shared_vpc_network = "____"   # Stage-1 output: shared_vpc_network (name or self-link)
ddi_subnet_cidr    = "____"   # you choose — from the IPAM plan (e.g. 10.100.8.0/26)
secret_project_id  = "____"   # existing — project holding Secret Manager secrets
machine_type       = "____"   # you choose — N1 series per NIOS model (+ vCPU quota)
vnios_image = {               # generated — gcloud compute images list --filter="family~infoblox OR name~vnios"
  project = "____"
  family  = "____"            # OR: name = "____"  (pin a build for prod)
}
mgmt_source_ranges = ["____"] # you choose — jump host/bastion/mgmt CIDRs (NEVER 0.0.0.0/0)
dns_client_ranges  = ["____"] # you choose — spoke + on-prem CIDRs allowed to query DNS (53)

# ---- OPTIONAL (defaults shown — change as needed) ----
name_prefix               = "ddi"
environment               = "prod"          # dev | test | prod
deployment_model          = "grid"          # grid | universal_ddi
acknowledge_saas_boundary = false           # MUST be true if deployment_model = "universal_ddi"
compliance_profile        = "gcc-moderate"
member_count              = 2               # >= 2 for HA
zones                     = ["a", "b"]      # zone letters within region
discovery_identity_type   = "service_account"  # or "existing_service_account"
labels                    = {}

# Firewall / networking
monitoring_source_ranges  = []              # REQUIRED only if enable_snmp = true
grid_peer_ranges          = ["____"]        # grid only — on-prem GM subnet + DDI subnet (1194/udp, 2114/tcp)
enable_ssh                = false
enable_dhcp               = false
enable_snmp               = false

# DNS integration
inbound_forwarding_enabled = true
cloud_dns_inbound_ip       = null           # generated (Phase 9.1) — null = skip infoblox forwarders
infoblox_forward_domains   = ["googleapis.com", "run.app"]
enterprise_forward_domains = []             # e.g. ["corp.example.com.","10.in-addr.arpa."]
ddi_anycast_vip            = null           # set once you own the anycast VIP
enable_spoke_dns_peering   = false
spoke_networks             = []             # service-project VPC self-links to peer

# Discovery scoping
discovered_project_ids         = ["____"]   # projects to grant read for discovery
enable_record_write            = false      # true grants roles/dns.admin
dns_admin_project_ids          = []         # projects holding Cloud DNS zones (only if enable_record_write)
existing_service_account_email = null       # only if discovery_identity_type = "existing_service_account"

# Secret Manager secret IDs (defaults usually fine; VALUES go into Secret Manager — see A.2)
admin_password_secret_id  = "ddi-vnios-admin-password"
temp_license_secret_id    = "ddi-vnios-temp-license"
grid_shared_secret_id     = "ddi-grid-shared-secret"
saas_join_token_secret_id = "ddi-uddi-join-token"

# Grid join (deployment_model = "grid")
grid_name       = "Infoblox"
grid_master_vip = "____"                    # on-prem GM VIP (null only for a lab where the first member IS the GM)

# Universal DDI (deployment_model = "universal_ddi")
infoblox_portal_url = "https://csp.infoblox.com"
```

### A.2 Secret Manager secrets (the values referenced by A.1)

| Secret (default id) | Content to store | Source | Applies to |
|---|---|---|---|
| `ddi-vnios-admin-password` | vNIOS `admin` password to set at first boot | you choose (strong) | both |
| `ddi-vnios-temp-license` | temp license string, e.g. `vnios dns dhcp grid enterprise` | Infoblox licensing | both |
| `ddi-grid-shared-secret` | Grid shared secret used to join members | your Grid config | `grid` |
| `ddi-uddi-join-token` | Infoblox Portal (CSP) join token | Infoblox Portal | `universal_ddi` |

```bash
SP=____   # your secret_project_id
for S in ddi-vnios-admin-password ddi-vnios-temp-license ddi-grid-shared-secret; do
  gcloud secrets create "$S" --project "$SP" --replication-policy=automatic || true
done
printf '%s' '____' | gcloud secrets versions add ddi-vnios-admin-password --project "$SP" --data-file=-
printf '%s' '____' | gcloud secrets versions add ddi-vnios-temp-license   --project "$SP" --data-file=-
printf '%s' '____' | gcloud secrets versions add ddi-grid-shared-secret   --project "$SP" --data-file=-   # grid
# universal_ddi only:
gcloud secrets create ddi-uddi-join-token --project "$SP" --replication-policy=automatic || true
printf '%s' '____' | gcloud secrets versions add ddi-uddi-join-token --project "$SP" --data-file=-
```

### A.3 Validation scripts — environment forms

**`validation/dns-validation.sh`**

```bash
export DDI_VIP="____"                 # REQUIRED — anycast VIP or a member IP (Stage-2 output ddi_anycast_vip)
export TEST_FQDN="____"               # REQUIRED — an authoritative A record (e.g. host.corp.example)
export EXPECTED_IP="____"             # REQUIRED — the IP TEST_FQDN must resolve to
export DNS_PORT="53"                  # default 53
export DNS_TIMEOUT="5"                # default 5 (seconds)
export PRIVATELINK_FQDN="____"        # optional — a Cloud DNS private / googleapis name via the forward path
export PRIVATELINK_EXPECTED_IP="____" # optional — expected private IP for that name
```

**`validation/discovery-sync-check.sh`**

```bash
export DDI_API_FLAVOR="nios"          # nios | universal_ddi (default nios)
export STALE_THRESHOLD_MIN="1440"     # default 1440 (24h)
# --- NIOS (deployment_model = grid) ---
export GRID_MASTER="____"             # REQUIRED (nios) — Grid Master host/IP
export INFOBLOX_USERNAME="____"       # REQUIRED (nios)
export INFOBLOX_PASSWORD="____"       # REQUIRED (nios) — inject from Secret Manager / CI secret, not literal
export WAPI_VERSION="v2.12"           # default v2.12
export WAPI_CA_BUNDLE="____"          # optional — path to CA bundle for TLS verification
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
export CANDIDATE_NETWORK="____"       # optional — pre-check one CIDR before allocating (e.g. 10.100.9.0/24)
```

### A.4 Pipeline — GitHub Actions (`pipelines/github-actions-gcp-ddi.yml`)

Set under **Settings → Secrets and variables → Actions** (or a repo Environment). WIF
means **no exported keys** — the values below are identifiers.

**Variables** (`vars.*`):

| Variable | Value | Source |
|---|---|---|
| `WIF_PROVIDER` | Workload Identity Provider resource name | generated (Phase 12) |
| `DEPLOY_SA_EMAIL` | `ddi-deploy@<host-project>.iam.gserviceaccount.com` | generated (Phase 12) |
| `TFSTATE_BUCKET` | Stage-2 Terraform remote-state GCS bucket | you create (Phase 1) |
| `LZ_STATE_BUCKET` / `LZ_STATE_PREFIX` | Stage-1 state location | Stage-1 |
| `SECRET_PROJECT_ID` | project holding the Infoblox secrets | existing |
| `DEPLOYMENT_MODEL` / `ACKNOWLEDGE_SAAS_BOUNDARY` | `grid` / `false` | you choose |
| `TEST_FQDN` / `EXPECTED_IP` / `PRIVATELINK_FQDN` | validation inputs (A.3) | you choose |

Infoblox WAPI creds (`infoblox-wapi-username`/`infoblox-wapi-password`) and, for
`universal_ddi`, `infoblox-csp-token` live in **Secret Manager** and are fetched at run
time — never plain pipeline variables.

### A.5 Pipeline — Cloud Build (`pipelines/cloudbuild-gcp-ddi.md`)

Set as **substitutions** on the trigger (or in the `cloudbuild.yaml`):

| Substitution | Value |
|---|---|
| `_ENVIRONMENT` | `dev` \| `test` \| `prod` |
| `_DEPLOYMENT_MODEL` / `_ACKNOWLEDGE_SAAS_BOUNDARY` | `grid` / `false` |
| `_APPLY` | `false` (plan-only) or `true` |
| `_TFSTATE_BUCKET` | Terraform backend bucket |
| `_HOST_PROJECT_ID` / `_SHARED_VPC_NETWORK` / `_REGION` | Stage-1 outputs |
| `_SECRET_PROJECT_ID` | Secret Manager project |
| `_TEST_FQDN` / `_EXPECTED_IP` | validation inputs |

> Never put `INFOBLOX_PASSWORD`, `INFOBLOX_CSP_TOKEN`, or the vNIOS admin password in
> plain substitutions — reference them from Secret Manager (`availableSecrets`) so
> they are injected at run time only.

---

## Sources

- [Terraform Example Foundation (Google Cloud landing zone)](https://github.com/terraform-google-modules/terraform-example-foundation)
- [Cloud Foundation Fabric / FAST](https://github.com/GoogleCloudPlatform/cloud-foundation-fabric)
- [HashiCorp — `hashicorp/google` provider (Registry)](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [Infoblox — `infobloxopen/infoblox` Terraform provider (Registry)](https://registry.terraform.io/providers/infobloxopen/infoblox/latest/docs)
- [Infoblox — terraform-provider-infoblox (GitHub)](https://github.com/infobloxopen/terraform-provider-infoblox)
- [Infoblox — Firewall Requirements for Infoblox Cloud Services (NIOS-X / 443)](https://docs.infoblox.com/space/BloxOneInfrastructure/873660456/Firewall+Requirements+for+Infoblox+Cloud+Services)
- [Google Cloud — Cloud DNS documentation](https://docs.cloud.google.com/dns/docs/server-policies-overview)
- Module contract: [`_module-contract.md`](./_module-contract.md)
- Architecture guide: [`GCP-LZ-Infoblox-DDI-Automation-Guide.md`](./GCP-LZ-Infoblox-DDI-Automation-Guide.md)
- Deploy chapter (click/CLI mechanics): [`../03-gcp.md`](../03-gcp.md)

---

## Optional: run this runbook through ServiceNow (governed path)

Every manual step here can be driven from a **ServiceNow Service Catalog item** instead of a shell: request → approval / separation-of-duties gate → **CPG Terraform Connector** apply of [`terraform/`](./terraform/README.md) on an in-boundary MID Server → **IntegrationHub REST** allocate/register over Infoblox WAPI/Universal DDI → the [`validation/`](./validation/README.md) scripts run by the MID Server as a **pass/fail gate** → **Service Graph Connector** CMDB reconcile → close with a full audit trail. Wire it per [`servicenow/ServiceNow-Orchestration.md`](./servicenow/ServiceNow-Orchestration.md) and stand up the importable records from [`servicenow-app/`](../servicenow-app/README.md); the model and control mapping are in [Chapter 7](../07-servicenow-orchestration.md). Secrets stay in Secret Manager; the MID Server and credential path stay inside the ATO boundary.
