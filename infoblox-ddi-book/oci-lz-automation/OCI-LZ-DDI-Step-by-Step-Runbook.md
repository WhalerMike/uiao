# OCI Landing Zone + Infoblox DDI — Step-by-Step Deployment Runbook

> **Companion to** [`OCI-LZ-Infoblox-DDI-Automation-Guide.md`](./OCI-LZ-Infoblox-DDI-Automation-Guide.md).
> That guide explains *why* the architecture is shaped the way it is; this runbook
> is the **"do exactly this, then this"** operational sequence that deploys it with
> the Terraform package in this directory. Every command, variable name, resource
> name, port, IAM statement, and output below is taken from the real module and its
> [`_module-contract.md`](./_module-contract.md) — nothing is invented. Where a
> value is genuinely environment-specific (image OCID, shape, region, CIDR, AD
> name) the runbook says **"supply your own"** rather than guessing.
>
> **Posture (fixed):** FedRAMP Moderate-equivalent on **commercial OCI (the OC1
> realm, `*.oraclecloud.com`)**. **Not** OCI Government (OC2/OC3) or
> National-Security realms.
>
> **Default path:** `deployment_model = "grid"` (vNIOS Grid, control plane inside
> the ATO boundary). The `universal_ddi` (Infoblox Portal / SaaS) path is shown in
> clearly-marked **⚠ UNIVERSAL DDI** callout boxes and always honors the
> `acknowledge_saas_boundary` guard.
>
> **Status of the IaC:** a coherent starter skeleton — structurally correct and
> guardrail-bearing, *not* a certified production module. Pin your own versions,
> import your own vNIOS custom image, and test in a sandbox landing zone first.

---

## Prerequisites checklist

Confirm **all** of these before Phase 0.

- [ ] **Stage-1 CIS Landing Zone already deployed.** Compartments, IAM, logging, and
      the connectivity hub (**hub VCN + DRG**, and ideally the hub VCN's OCI DNS
      resolver) exist and publish outputs. This module is **Stage 2**; it never
      builds Stage 1.
- [ ] **Stage-1 outputs available:** `network_compartment_ocid`, `hub_vcn_ocid`,
      `drg_ocid`, `vault_ocid`, and (ideally) the hub resolver OCID + a resolver
      endpoint subnet OCID.
- [ ] **Permissions.** You (or the pipeline identity) can create network/compute/DNS
      resources in the network compartment, create IAM dynamic groups/policies in
      the tenancy, and create OCI Vault secrets. Discovery uses a *separate,
      least-privileged* identity (Phase 4).
- [ ] **Tooling:** `oci` CLI (current), Terraform ≥ 1.5 (`>= 1.5.0, < 2.0.0` for
      `precondition` blocks), `jq`, `dig`/`nslookup`.
- [ ] **An existing OCI Vault** (+ a key) in the network compartment for the secrets.
- [ ] **A free, non-overlapping CIDR** inside the hub VCN for the `ddi-subnet`.
- [ ] **The vNIOS OCI image** (qcow2/VMDK) from Infoblox Support, ready to upload to
      Object Storage and import (Phase 5). **No Marketplace listing exists.**
- [ ] **Explicit CIDRs** for security scoping — mgmt/bastion, DNS clients
      (spokes/on-prem), Grid peers/GM, monitoring. **Never `0.0.0.0/0`** (the module
      hard-fails on it).

---

## Phase 0 — Decisions & inventory

### Step 0.1 — Choose the control-plane model

The single most consequential decision. It sets **where the control plane lives
relative to your ATO boundary**.

| | `deployment_model = "grid"` (default) | `deployment_model = "universal_ddi"` |
|---|---|---|
| Control plane | vNIOS **Grid**, self-operated in-tenancy | Infoblox **Portal / CSP** (SaaS) |
| Vs. ATO boundary | **Inside** | **Outside** |
| Data-plane members | vNIOS DNS members (CP-2205) | NIOS-X servers |
| Outbound dependency | Grid VPN `1194/udp` + `2114/tcp` over the DRG | **outbound `443` to `csp.infoblox.com`** |
| FedRAMP-Moderate fit | **Boundary-clean — recommended default** | Requires authorization review |
| Gov / sovereign realm | Works | Portal typically unreachable — do not use |
| Code guard | none | hard-fails unless `acknowledge_saas_boundary = true` |

**Decision:** For a boundary-clean FedRAMP-Moderate landing zone, choose **`grid`**.
Only choose `universal_ddi` after completing the authorization review for the SaaS
control-plane egress — and never in an OC2/OC3/air-gapped realm.

**Verify:** Write the chosen `deployment_model` down; it must match across
`terraform.tfvars` and the pipeline env (`DEPLOYMENT_MODEL`).

> **⚠ UNIVERSAL DDI callout.** If you selected `universal_ddi`, you must also set
> `acknowledge_saas_boundary = true` **and** justify the outbound-443 dependency to
> `csp.infoblox.com`. Leaving the ack `false` (default) is a deliberate hard-fail.

### Step 0.2 — Gather Stage-1 outputs into shell variables

```bash
# Fill these from your Stage-1 CIS Landing Zone outputs.
export TENANCY_OCID="ocid1.tenancy.oc1..____"
export NETWORK_COMPARTMENT_OCID="ocid1.compartment.oc1..____"   # network_compartment_ocid
export HUB_VCN_OCID="ocid1.vcn.oc1..____"                       # hub_vcn_ocid
export DRG_OCID="ocid1.drg.oc1..____"                           # drg_ocid
export VAULT_OCID="ocid1.vault.oc1..____"                       # vault_ocid
export VAULT_KEY_OCID="ocid1.key.oc1..____"                     # a key in the Vault (for secret encryption)
export HUB_RESOLVER_OCID="ocid1.dnsresolver.oc1..____"          # hub VCN resolver
export REGION="us-ashburn-1"                                    # supply your own OC1 region
export DDI_SUBNET_CIDR="10.10.4.0/27"                           # supply your own free CIDR
```

**Verify:** `echo "$HUB_VCN_OCID"` matches `ocid1.vcn.` — the module's `hub_vcn_ocid`
validation rejects anything else.

---

## Phase 1 — Tooling & auth

### Step 1.1 — Install and check tooling

```bash
oci --version
terraform version          # expect >= 1.5.0, < 2.0.0
jq --version ; dig -v 2>&1 | head -1
```

**Verify:** `terraform version` prints a 1.5+ build; `oci --version` prints the CLI.

### Step 1.2 — Configure OCI auth (commercial OC1)

```bash
oci setup config          # writes ~/.oci/config with tenancy/user/fingerprint/region + API key
oci iam region list --query "data[?contains(name,'us-')].name" -o table
oci iam compartment get --compartment-id "$NETWORK_COMPARTMENT_OCID" \
  --query 'data.name' -o table
```

**Verify:** the compartment name prints. Confirm the config `region` is a commercial
OC1 region (e.g. `us-ashburn-1`), **not** an OC2/OC3 gov region.

> **Troubleshooting — wrong realm.** If `oci iam region-subscription list` shows only
> a Government realm, you are in the wrong tenancy for this deliverable (OC1 only).

### Step 1.3 — Create the Terraform remote-state backend (OCI Object Storage)

State lives in an OCI Object Storage bucket via the S3-compatible backend.

```bash
export NAMESPACE="$(oci os ns get --query data -r "$REGION" | tr -d '"')"
export STATE_BUCKET="tfstate-ddi"
oci os bucket create -c "$NETWORK_COMPARTMENT_OCID" --name "$STATE_BUCKET" \
  --namespace "$NAMESPACE"
```

**Verify:** `oci os bucket get --name "$STATE_BUCKET" --namespace "$NAMESPACE"`
returns the bucket. Generate an S3-compat **Customer Secret Key** on your user for
the backend's `access_key`/`secret_key` (Identity → your user → Customer Secret Keys).

---

## Phase 2 — Consume Stage-1 outputs

The module learns about the hub **only** through Stage-1 outputs — it never queries or
mutates Stage-1-owned resources.

### Step 2.1 — Option A: `terraform_remote_state` (preferred)

`examples/hub-integration/main.tf` reads the CIS Landing Zone state directly (S3-compat
backend). Adjust the backend coordinates to wherever Stage 1 stored its state.

**Verify:** `terraform console` →
`data.terraform_remote_state.lz.outputs.hub_vcn_ocid` prints the hub VCN OCID.

### Step 2.2 — Option B: `oci` lookups (provider-agnostic)

If Stage 1 does not share Terraform state, resolve the same facts with `oci`:

```bash
# hub VCN (by display name within the network compartment)
oci network vcn list -c "$NETWORK_COMPARTMENT_OCID" \
  --query "data[?contains(\"display-name\",'hub')].id | [0]" -o tsv

# DRG
oci network drg list -c "$NETWORK_COMPARTMENT_OCID" --query "data[0].id" -o tsv

# hub VCN resolver (via the VCN's DNS resolver association)
oci dns resolver list -c "$NETWORK_COMPARTMENT_OCID" --scope PRIVATE \
  --query "data[0].id" -o tsv
```

**Verify:** each command prints an OCID; feed them into the tfvars in Phase 6.

---

## Phase 3 — Secrets in OCI Vault

The module **reads existing** OCI Vault secrets (`data "oci_secrets_secretbundle"`); it
never creates them and never emits them as plaintext outputs. Create the secrets, then
pass their OCIDs to the module.

| Purpose | Suggested secret name | Applies to |
|---|---|---|
| Admin password | `ddi-admin-password` | both |
| Temp license (BYOL) | `ddi-temp-license` | both |
| Grid shared secret | `ddi-grid-shared-secret` | `grid` |
| Portal join token | `ddi-uddi-join-token` | `universal_ddi` |

### Step 3.1 — Create the secrets (`oci vault secret`)

OCI Vault stores secret content base64-encoded; `create-base64` takes the base64 form.

```bash
b64() { printf '%s' "$1" | base64 | tr -d '\n'; }

oci vault secret create-base64 -c "$NETWORK_COMPARTMENT_OCID" \
  --vault-id "$VAULT_OCID" --key-id "$VAULT_KEY_OCID" \
  --secret-name ddi-admin-password \
  --secret-content-content "$(b64 '<STRONG_ADMIN_PASSWORD>')"

oci vault secret create-base64 -c "$NETWORK_COMPARTMENT_OCID" \
  --vault-id "$VAULT_OCID" --key-id "$VAULT_KEY_OCID" \
  --secret-name ddi-temp-license \
  --secret-content-content "$(b64 'vnios dns dhcp grid enterprise')"

# Grid path only:
oci vault secret create-base64 -c "$NETWORK_COMPARTMENT_OCID" \
  --vault-id "$VAULT_OCID" --key-id "$VAULT_KEY_OCID" \
  --secret-name ddi-grid-shared-secret \
  --secret-content-content "$(b64 '<GRID_SHARED_SECRET>')"
```

> **⚠ UNIVERSAL DDI callout.** For `universal_ddi`, also create the Portal join token
> (NIOS-X hosts phone home to `csp.infoblox.com` over 443 with it):
> ```bash
> oci vault secret create-base64 -c "$NETWORK_COMPARTMENT_OCID" \
>   --vault-id "$VAULT_OCID" --key-id "$VAULT_KEY_OCID" \
>   --secret-name ddi-uddi-join-token \
>   --secret-content-content "$(b64 '<PORTAL_JOIN_TOKEN>')"
> ```

### Step 3.2 — Capture the secret OCIDs

```bash
export ADMIN_PW_SECRET_OCID="$(oci vault secret list -c "$NETWORK_COMPARTMENT_OCID" \
  --vault-id "$VAULT_OCID" --name ddi-admin-password --query 'data[0].id' -o tsv)"
export LICENSE_SECRET_OCID="$(oci vault secret list -c "$NETWORK_COMPARTMENT_OCID" \
  --vault-id "$VAULT_OCID" --name ddi-temp-license --query 'data[0].id' -o tsv)"
export GRID_SECRET_OCID="$(oci vault secret list -c "$NETWORK_COMPARTMENT_OCID" \
  --vault-id "$VAULT_OCID" --name ddi-grid-shared-secret --query 'data[0].id' -o tsv)"
```

**Verify (read-back):**
```bash
oci secrets secret-bundle get --secret-id "$ADMIN_PW_SECRET_OCID" \
  --query 'data."secret-bundle-content".content' -o tsv | base64 -d | head -c 3
```
prints the first characters of the stored password.

> **Troubleshooting — Forbidden on secret create.** You need
> `manage secret-family` / `use keys` in the network compartment. The deploy/module
> identity needs `read secret-bundles` to fetch at apply time — wait ~1 min for
> policy propagation and retry.

---

## Phase 4 — Discovery identity + least-privilege policy

The OCI→Infoblox IPAM sync uses a **separate, least-privileged** identity. Prefer an
**instance principal** (a dynamic group); fall back to an **IAM user + API signing key**.
Policy is scoped per contract §5 — **no `manage` of network/compute, no tenancy-admin.**

The Terraform module creates these for you (`ddi-disco-dg` dynamic group / `ddi-disco-grp`
group + `ddi-disco-policy`). If you want them pre-created or are reviewing the exact
statements, they are:

```
Allow dynamic-group ddi-disco-dg to read virtual-network-family in compartment id <net>
Allow dynamic-group ddi-disco-dg to read dns                    in compartment id <net>
Allow dynamic-group ddi-disco-dg to read instance-family        in compartment id <net>
Allow dynamic-group ddi-disco-dg to inspect tag-namespaces      in tenancy
# opt-in record write (enable_record_write=true) only:
Allow dynamic-group ddi-disco-dg to manage dns                  in compartment id <net>
```

### Step 4.1 — (Optional) pre-create the dynamic group

```bash
oci iam dynamic-group create --name ddi-disco-dg \
  --description "Infoblox discovery instance principal" \
  --matching-rule "instance.compartment.id = '$NETWORK_COMPARTMENT_OCID'"
```

**Verify:** `oci iam dynamic-group list --name ddi-disco-dg --query 'data[0].id' -o tsv`
returns an OCID. This becomes the module output `discovery_identity_id`.

> On the **api_key_user** path, pre-create the user's API signing key and pass
> `discovery_user_ocid`; the module adds it to `ddi-disco-grp`.

**Verify:** after apply, `oci iam policy get --policy-id <ddi-disco-policy-ocid>` shows
exactly the statements above — no `manage` of `virtual-network-family`, no admin.

> **Troubleshooting — discovery enumerates nothing.** Usually the dynamic-group
> matching rule doesn't match the instance running the sync, or policy hasn't
> propagated. Confirm the instance's compartment matches the rule.

---

## Phase 5 — Import the vNIOS custom image (no Marketplace)

OCI has **no Marketplace vNIOS listing** — you import a custom image once, then reuse it.

### Step 5.1 — Upload the image to Object Storage

```bash
export IMG_BUCKET="vnios-images"
oci os bucket create -c "$NETWORK_COMPARTMENT_OCID" --name "$IMG_BUCKET" \
  --namespace "$NAMESPACE" || true
oci os object put -bn "$IMG_BUCKET" --namespace "$NAMESPACE" \
  --file ./vnios-<ver>.qcow2 --name vnios-<ver>.qcow2
```

### Step 5.2 — Import as a custom image (paravirtualized)

```bash
oci compute image import from-object -c "$NETWORK_COMPARTMENT_OCID" \
  --namespace "$NAMESPACE" --bucket-name "$IMG_BUCKET" --name vnios-<ver>.qcow2 \
  --source-image-type QCOW2 --launch-mode PARAVIRTUALIZED \
  --display-name ddi-vnios-<ver>
```

Poll until the image state is `AVAILABLE`, then capture the OCID:

```bash
export VNIOS_IMAGE_OCID="$(oci compute image list -c "$NETWORK_COMPARTMENT_OCID" \
  --display-name ddi-vnios-<ver> --query 'data[0].id' -o tsv)"
```

**Verify:**
`oci compute image get --image-id "$VNIOS_IMAGE_OCID" --query 'data."lifecycle-state"' -o tsv`
returns `AVAILABLE`.

> **Alternative — let Terraform import.** Set `import_image = true` and
> `image_source_uri` to the Object Storage URI; the module's `oci_core_image` resource
> drives the import. Either way, **never invent an image OCID.**

> **Troubleshooting — import stuck / fails.** Confirm the object exists
> (`oci os object head -bn "$IMG_BUCKET" --name vnios-<ver>.qcow2`) and the source
> type matches the file (QCOW2 vs VMDK). Large images take several minutes.

---

## Phase 6 — Configure the module (`terraform.tfvars`)

Start from `examples/hub-integration/main.tf`, then externalize values into a
`terraform.tfvars` next to the module. Every variable below is real.

```hcl
# terraform.tfvars — Stage-2 Infoblox DDI (grid, commercial OC1, FedRAMP-Moderate)

# --- Basics / boundary ---
name_prefix        = "ddi"                 # -> ddi-subnet, ddi-nsg, ddi-vnios-ad1-fd1, ddi-disco-dg
region             = "us-ashburn-1"        # supply your own OC1 region
environment        = "prod"                # dev | test | prod
deployment_model   = "grid"                # boundary-clean default
compliance_profile = "fedramp-moderate"
# acknowledge_saas_boundary left false — not needed for grid.

# --- From Stage-1 outputs ---
tenancy_ocid             = "ocid1.tenancy.oc1..____"
network_compartment_ocid = "ocid1.compartment.oc1..____"
hub_vcn_ocid             = "ocid1.vcn.oc1..____"
drg_ocid                 = "ocid1.drg.oc1..____"
vault_ocid               = "ocid1.vault.oc1..____"

# --- Dedicated DDI subnet (must fit hub VCN, not overlap) ---
ddi_subnet_cidr = "10.10.4.0/27"

# --- Members: 2 across ADs and FDs (HA) ---
member_count         = 2
availability_domains = ["Uocm:US-ASHBURN-AD-1", "Uocm:US-ASHBURN-AD-2"]
fault_domains        = ["FAULT-DOMAIN-1", "FAULT-DOMAIN-2"]

# --- Shape + imported CUSTOM IMAGE: supply your own (no Marketplace) ---
vnios_shape      = "VM.Standard.E4.Flex"   # confirm against the vNIOS-for-OCI spec
vnios_ocpus      = 4
vnios_memory_gbs = 32
vnios_image_ocid = "ocid1.image.oc1..____" # from Phase 5 (or import_image=true + image_source_uri)

# --- Security source scoping (never 0.0.0.0/0) ---
security_model    = "nsg"                              # or "security_list"
mgmt_source_cidrs = ["10.10.0.0/24"]                   # bastion/mgmt subnet
dns_client_cidrs  = ["10.20.0.0/16", "10.30.0.0/16"]   # spokes over the DRG
grid_peer_cidrs   = ["10.10.4.0/27", "192.168.100.0/24"] # DDI subnet + on-prem GM (grid only)

# --- Grid join (usual pattern: join OCI members to the on-prem GM over the DRG) ---
grid_name       = "CorpGrid"
grid_master_vip = "192.168.100.10"        # on-prem Grid Master VIP; null => first member is GM (lab only)

# --- DNS integration (§9) ---
manage_resolver_endpoints     = true
hub_resolver_ocid             = "ocid1.dnsresolver.oc1..____"
resolver_endpoint_subnet_ocid = "ocid1.subnet.oc1..____"   # resolver endpoint subnet
oci_listening_endpoint_ip     = "10.10.4.20"               # OCI resolver LISTENING endpoint IP
ddi_anycast_vip               = "10.10.4.10"               # advertised from both members
# oci_forward_domains defaults to ["oraclevcn.com"]; enterprise_forward_domains -> Infoblox

# --- OCI Vault secret OCIDs (from Phase 3) ---
admin_password_secret_ocid = "ocid1.vaultsecret.oc1..____"
temp_license_secret_ocid   = "ocid1.vaultsecret.oc1..____"
grid_shared_secret_ocid    = "ocid1.vaultsecret.oc1..____"

# --- Discovery identity + least-privilege IAM (§5) ---
discovery_identity_type      = "instance_principal"
discovered_compartment_ocids = ["ocid1.compartment.oc1..____"]  # compartments to read
enable_record_write          = false       # read-only discovery by default

freeform_tags = { owner = "network-platform", costcenter = "cc-1234" }
```

**What the key variables do (all real):**

- `deployment_model` / `acknowledge_saas_boundary` — the boundary switch + its guard.
- `availability_domains` + `fault_domains` — members round-robined over ADs then FDs;
  single-AD regions still get unique `ddi-vnios-ad1-fd1` / `ad1-fd2` names.
- `grid_peer_cidrs` — **required for grid** (an NSG/Security-List precondition fails the
  plan if `grid` is selected and this is empty).
- `mgmt_source_cidrs` / `dns_client_cidrs` — enforced non-empty and **must not** contain
  `0.0.0.0/0` (variable `validation`).
- `vnios_image_ocid` — the imported custom image (Phase 5); OCI has no Marketplace.

> **⚠ UNIVERSAL DDI callout — tfvars deltas.**
> ```hcl
> deployment_model            = "universal_ddi"
> acknowledge_saas_boundary   = true                 # REQUIRED — false hard-fails the plan
> saas_join_token_secret_ocid = "ocid1.vaultsecret.oc1..____"
> infoblox_portal_url         = "csp.infoblox.com"   # outbound 443 required
> # grid_master_vip / grid_shared_secret_ocid are unused on this path
> ```
> With ack `false`, `terraform plan` aborts with the `BOUNDARY VIOLATION` message —
> `ddi-niosx-*` and `null_resource.portal_enroll` never plan.

---

## Phase 7 — Deploy

### Step 7.1 — `init` with the remote backend

```bash
cd infoblox-ddi-book/oci-lz-automation/terraform
terraform init \
  -backend-config="bucket=$STATE_BUCKET" \
  -backend-config="key=ddi-prod.tfstate" \
  -backend-config="region=$REGION" \
  -backend-config="endpoints={s3=\"https://$NAMESPACE.compat.objectstorage.$REGION.oraclecloud.com\"}" \
  -backend-config="skip_region_validation=true" \
  -backend-config="skip_credentials_validation=true" \
  -backend-config="skip_requesting_account_id=true"
```

**Verify:** `Terraform has been successfully initialized!` and the `oci`,
`infobloxopen/infoblox`, `tls`, and `null` providers resolve (per `versions.tf`).

### Step 7.2 — `plan` (guards are evaluated here)

```bash
terraform plan -input=false -out=tfplan
```

**Expected:** the plan creates `ddi-subnet`, the `ddi-nsg` (or Security List) + rules,
`ddi-vnios-ad1-fd1` / `ddi-vnios-ad1-fd2` (instances), the `ddi-disco-dg` dynamic group +
`ddi-disco-policy`, the OCI resolver endpoints + rules, and the `infoblox_zone_forward`
objects (if `oci_listening_endpoint_ip` set). The boundary guard and CIDR scoping are
checked at **plan** time.

**Verify:** plan summary shows the expected adds and **no** `0.0.0.0/0` sources.

### Step 7.3 — `apply`

```bash
terraform apply -input=false -auto-approve tfplan
terraform output
# ddi_subnet_id         = "ocid1.subnet.oc1..."
# dns_server_ips        = ["10.10.4.4", "10.10.4.5"]   # member VNIC IPs
# ddi_anycast_vip       = "10.10.4.10"                  # null until advertised
# grid_master_ip        = "192.168.100.10"             # on-prem GM (grid only)
# discovery_identity_id = "ocid1.dynamicgroup.oc1..."
```

**Cross-AD/FD members:** confirm the two members landed in different fault domains:

```bash
oci compute instance list -c "$NETWORK_COMPARTMENT_OCID" \
  --query "data[?contains(\"display-name\",'ddi-vnios')].{name:\"display-name\", ad:\"availability-domain\", fd:\"fault-domain\"}" -o table
```

**Verify:** the two members show different `fault-domain` (and AD in multi-AD regions).

> **Troubleshooting — no image OCID.** *"No vNIOS image OCID available"* → set
> `vnios_image_ocid` (Phase 5) or `import_image = true` + `image_source_uri`.
>
> **Troubleshooting — grid plan fails immediately.** *"deployment_model='grid'
> requires grid_peer_cidrs"* → set `grid_peer_cidrs`.
>
> **Troubleshooting — DNS-object apply fails.** `infoblox_zone_forward` needs a
> reachable Grid/NIOS WAPI endpoint. Members are not yet Grid-joined at first apply;
> either configure the `infoblox` provider `server` to the on-prem GM, or run the
> DNS-object resources in a **second phase** after Phase 8 (use `-target` or a
> dependent module). This ordering is by design.

---

## Phase 8 — Grid formation / Universal DDI onboarding

The instances exist, but the **control plane is not yet formed**. `ddi_anycast_vip` and
`grid_master_ip` become operationally real only after this phase.

### Step 8.1 — Grid path: form / join the Grid

Each member booted with `user_data` (`#infoblox-config`) carrying the temp license, admin
password, and grid-join parameters from OCI Vault. Complete formation:

- **Usual OCI pattern:** the on-prem Grid Master (`grid_master_vip`) is authoritative,
  reached over FastConnect/IPSec via the DRG; the OCI members join as **Grid members**
  over `1194/udp` + `2114/tcp`. Confirm each member appears in the Grid Manager UI under
  your `grid_name` (e.g. `CorpGrid`).
- **Lab/greenfield:** if `grid_master_vip = null`, the first member initializes the Grid.
- **Assign the anycast VIP** (`ddi_anycast_vip`) — advertise a `/32` service address via
  BGP over the DRG from both members, or front them with an **OCI Load Balancer** VIP.

**Verify (WAPI, from a mgmt host):**

```bash
export GRID_MASTER="<gm-mgmt-ip-or-fqdn>"          # your Grid Master (grid_master_ip)
export INFOBLOX_USERNAME="admin"
export INFOBLOX_PASSWORD="<from-oci-vault>"
curl -fsS -u "$INFOBLOX_USERNAME:$INFOBLOX_PASSWORD" \
  "https://$GRID_MASTER/wapi/v2.12/member?_return_fields%2B=host_name,service_status"
```

Both OCI members show `service_status` running for DNS. Confirm exact WAPI object/field
names against `<grid-master>/wapidoc/` for your NIOS version.

> **⚠ UNIVERSAL DDI callout — enroll NIOS-X to the Portal.** Instead of Grid formation,
> each `ddi-niosx-*` host self-enrolls to `csp.infoblox.com` over 443 using the join
> token from `user_data`. The `null_resource.portal_enroll` is the explicit API seam —
> replace its placeholder with the real CSP REST call, then confirm in the Portal
> inventory.

**Verify:** members/hosts report healthy in the Grid Manager UI or the Portal, and the
anycast VIP answers (tested in Phase 12).

---

## Phase 9 — Cloud discovery adapter (API/SDK-driven)

**Candid:** OCI has no native Infoblox discovery connector. Phase 4 granted the identity;
the **sync itself is code you run** (contract §0/§5, guide §7).

### Step 9.1 — Grid path: run the OCI→IPAM sync

A scheduled OCI-SDK job (under the instance principal) lists VCNs/subnets in each
onboarded compartment and pushes them into Infoblox IPAM as networks/containers via WAPI,
tagging each with the compartment/VCN OCID. Illustrative shape:

```bash
# oci network vcn list -c "$NETWORK_COMPARTMENT_OCID" --all \
#   | ./oci-to-infoblox-sync.py --grid-master "$GRID_MASTER" --view default
```

Schedule it (e.g. hourly) so IPAM tracks OCI reality. Alternatively, drive allocation at
**pipeline time** with the `infoblox` provider (`infoblox_ipv4_network` / next-available)
so records exist *before* the OCI VNIC is attached.

> **⚠ UNIVERSAL DDI callout.** Configure a Portal Universal Cloud OCI source using the
> same identity via the CSP API/UI; the discovery job lives in the SaaS control plane.

**Verify:** run the Stage-3 discovery check (Phase 12) — it asserts the sync/job exists,
is not errored, and ran within `STALE_THRESHOLD_MIN`.

---

## Phase 10 — DNS integration

Two conditional-forwarding paths meet at the hub VCN OCI resolver.

### Step 10.1 — Infoblox → OCI (conditional forwarders)

`dns.tf` creates one `infoblox_zone_forward` per domain in `oci_forward_domains` (default
`oraclevcn.com`), each pointing `forward_to.address` at `oci_listening_endpoint_ip`. Runs
only when `deployment_model = "grid"` **and** `oci_listening_endpoint_ip != null`.

**Verify (after the DNS-object phase applies):**

```bash
curl -fsS -u "$INFOBLOX_USERNAME:$INFOBLOX_PASSWORD" \
  "https://$GRID_MASTER/wapi/v2.12/zone_forward?fqdn=oraclevcn.com"
```

Returns the forward zone targeting the LISTENING endpoint IP.

### Step 10.2 — OCI → Infoblox (resolver forwarding rules)

The module attaches a FORWARDING endpoint + rules on the hub resolver
(`oci_dns_resolver` + `oci_dns_resolver_endpoint`) sending `enterprise_forward_domains` to
`dns_server_ips`/the VIP. Manual equivalent for a spoke resolver rule:

```bash
oci dns resolver update --resolver-id "$HUB_RESOLVER_OCID" --scope PRIVATE \
  --rules '[{"action":"FORWARD","destinationAddresses":["10.10.4.10"],"sourceEndpointName":"ddi-forward","qnameCoverConditions":["corp.example"]}]'
```

**Verify:** from an OCI spoke instance, a `corp.example` name resolves via the DDI VIP
(tested in Phase 12).

> **Troubleshooting — NSG/SL blocking 53/1194/2114.** If DNS times out or Grid members
> won't converge, confirm the rules exist and sources match your CIDRs:
> `oci network nsg rule list --nsg-id <ddi-nsg-ocid>` (or
> `oci network security-list get --security-list-id <ocid>`). Remember OCI is
> default-deny — a missing allow silently drops the traffic.

---

## Phase 11 — IPAM automation

Because the sync imports OCI **defined tags as extensible attributes (EAs)**, IPAM becomes
an API the platform consumes.

### Step 11.1 — Onboard compartments & confirm networks appear

The §9 sync walks compartments → VCNs → subnets and populates Infoblox IPAM.

**Verify:**

```bash
curl -fsS -u "$INFOBLOX_USERNAME:$INFOBLOX_PASSWORD" \
  "https://$GRID_MASTER/wapi/v2.12/network?_return_fields%2B=network,comment&network_view=default"
```

OCI VCN/subnet CIDRs (including `ddi-subnet` `10.10.4.0/27`) appear as `network` objects.

### Step 11.2 — Tag-driven allocation & reclaim-on-delete

Keyed on `environment` / `owner` / `costcenter` EAs (from OCI defined tags), provisioning
pipelines carve the next free subnet (`infoblox_ipv4_network` / WAPI `nextavailablenetwork`)
and feed that CIDR into the workload's IaC. Schedule the sync so a subnet deleted in OCI is
reconciled on the next run.

**Verify:** the IPAM conflict gate (Phase 12) reports no overlaps after a sync.

---

## Phase 12 — Validation gates

Run each `validation/*.sh` with its env-var contract. Any non-zero exit fails the Stage-3
pipeline gate.

### Step 12.1 — DNS resolution (`dns-validation.sh`)

```bash
cd infoblox-ddi-book/oci-lz-automation/validation
export DDI_VIP="10.10.4.10"                          # ddi_anycast_vip
export TEST_FQDN="app01.corp.example"               # enterprise A record
export EXPECTED_IP="10.20.5.10"                      # its expected answer
export OCI_FQDN="app.subnet.hubvcn.oraclevcn.com"   # optional: OCI-owned name via forward path
bash dns-validation.sh
```

**Proves:** the DDI VIP answers an enterprise A record with `EXPECTED_IP`, and an
`*.oraclevcn.com` name resolves through the conditional-forward path to a private IP.
**Verify:** ends with `All DNS validation checks passed.`

### Step 12.2 — Discovery-sync freshness (`discovery-sync-check.sh`)

```bash
export DDI_API_FLAVOR="nios"                # grid default; "universal_ddi" for SaaS
export GRID_MASTER="<grid-master>"          # WAPI host (grid_master_ip)
export INFOBLOX_USERNAME="admin"            # from OCI Vault
export INFOBLOX_PASSWORD="<from-oci-vault>"
export STALE_THRESHOLD_MIN="1440"           # 24h
bash discovery-sync-check.sh
```

**Proves:** the OCI→IPAM sync completed successfully and recently. **Verify:** ends with
`Discovery-sync freshness check passed.`

> **⚠ UNIVERSAL DDI callout.** Set `DDI_API_FLAVOR=universal_ddi` and provide
> `INFOBLOX_CSP_TOKEN` (from OCI Vault); the check queries `csp.infoblox.com` cloud-
> discovery jobs. Only exercise this when `acknowledge_saas_boundary = true`.

### Step 12.3 — IPAM conflict (`ipam-conflict-check.sh`)

```bash
export GRID_MASTER="<grid-master>"
export INFOBLOX_USERNAME="admin"
export INFOBLOX_PASSWORD="<from-oci-vault>"
export NETWORK_VIEW="default"
# optional: export CANDIDATE_NETWORK="10.10.4.0/27"   # test one CIDR for overlap
bash ipam-conflict-check.sh
```

**Proves:** no overlapping/duplicate `network` objects. **Verify:** ends with
`IPAM conflict check passed.`

> **Troubleshooting — anycast not converging.** If `dns-validation.sh` intermittently
> fails, the anycast VIP may not be advertised from both members yet (Phase 8), or a
> member is unhealthy. Confirm both members answer directly:
> `dig +short @10.10.4.4 app01.corp.example` and `@10.10.4.5` (the two `dns_server_ips`).

---

## Phase 13 — Wire into GitOps

The pipeline (`pipelines/github-actions-oci-ddi.yml`) runs the same three stages —
**LZ (read Stage-1) → DDI (Stage-2 apply) → Validate (Stage-3)** — with OCI auth assembled
from GitHub secrets (OCI's OIDC-to-GitHub federation is limited; see the honest comment in
the workflow), remote state in **OCI Object Storage**, and secrets from **OCI Vault**.

### Step 13.1 — Store the OCI API-key config as GitHub secrets

Set repo/environment **secrets** `OCI_CLI_USER`, `OCI_CLI_TENANCY`, `OCI_CLI_FINGERPRINT`,
`OCI_CLI_REGION`, and `OCI_CLI_KEY_CONTENT` (the PEM private key). The workflow assembles
`~/.oci/config` from these. Grant that user least-privilege: create the DDI resources; read
Stage-1 state bucket. This is a **separate, more-privileged** identity than the discovery
`ddi-disco-dg`.

> **OCI Resource Manager alternative (cleaner).** As a managed Terraform service, RM
> injects credentials automatically — no key in CI. See
> [`pipelines/resource-manager-oci-ddi.md`](./pipelines/resource-manager-oci-ddi.md).

### Step 13.2 — The boundary gate & promotion flow

The pipeline carries `DEPLOYMENT_MODEL` (`grid`) and `ACKNOWLEDGE_SAAS_BOUNDARY` (`false`).
A gate step **hard-fails before init** if `deployment_model = universal_ddi` and the ack is
not `true` — so the SaaS path is never even planned without a review (the Terraform guard
enforces it again).

Promotion: **PR → plan-only**; **dev sandbox →** dispatch with `apply=true` + validation;
**test →** same with environment approval; **prod →** required reviewers gate entry. Each
env uses a distinct state key `ddi-<env>.tfstate`.

**Verify:** open a PR touching `terraform/**` — the `ddi` job runs `plan` only and
`validate` is skipped; merge to `main` (or dispatch `apply=true`) runs `apply` then the
three validation scripts.

---

## Phase 14 — Day-2 & rollback

- **Upgrades.** Patch NIOS/NIOS-X on the vendor cadence; in a Grid, **upgrade the on-prem
  Grid Master before the OCI members** (rolling), during a window; snapshot boot/block
  volumes first. Universal DDI scales by adding NIOS-X hosts (raise `member_count`,
  re-apply).
- **Failover game-day.** Confirm the anycast/LB path keeps answering when one member is
  stopped: `oci compute instance action --instance-id <ddi-vnios-ad1-fd1-ocid> --action STOP`
  then re-run `dns-validation.sh` against the VIP. Restart with `--action START`.
- **Drift detection.** A scheduled pipeline re-runs `terraform plan`; any non-empty plan is
  drift (a hand-made subnet, an edited NSG rule, a forwarder changed in the Grid UI) and
  raises a reconcile PR. Because Git is the source of record, remediation is "revert to
  desired state."
- **Secret rotation.** Rotate the admin password / temp license in OCI Vault after first
  Grid setup. `grid.tf`/`universal_ddi.tf` set
  `lifecycle { ignore_changes = [metadata["user_data"]] }`, so a Vault rotation does **not**
  silently recreate running members — re-bootstrap is a deliberate action.
- **Teardown cautions.** `terraform destroy` removes the members, `ddi-subnet`, the NSG/SL,
  the discovery identity, and the resolver endpoints. **Before destroying:** revert any
  spoke resolver rules you pointed at the VIP (Phase 10) or those spokes lose resolution;
  drain the members from the Grid first; confirm no workload still depends on the VIP.
  Destroy is scoped to Stage-2 only — it must **never** touch Stage-1 hub/IAM resources.

---

## End-to-end validation checklist

- [ ] `terraform output` shows `ddi_subnet_id`, `dns_server_ips`, `ddi_anycast_vip`,
      `grid_master_ip` (grid), `discovery_identity_id`.
- [ ] Members `ddi-vnios-ad1-fd1` / `ddi-vnios-ad1-fd2` are in **different fault domains**
      (and ADs where multi-AD) and Grid-joined (or NIOS-X hosts enrolled to the Portal).
- [ ] The NSG/Security List carries exactly the contract ports; no source is `0.0.0.0/0`.
- [ ] `ddi-disco-dg` / `ddi-disco-policy` grants only read (+ `manage dns` if opted in) —
      no `manage` of network/compute, no tenancy-admin.
- [ ] OCI Vault holds the admin password, temp license, grid shared secret (and Portal
      join token for uddi) — none in Terraform state as plaintext.
- [ ] `dns-validation.sh` passes (enterprise A + `oraclevcn.com` forward path).
- [ ] `discovery-sync-check.sh` passes (sync fresh, not errored).
- [ ] `ipam-conflict-check.sh` passes (no overlapping CIDRs).
- [ ] Failover: stopping one member leaves the anycast/LB VIP answering.
- [ ] Pipeline: PR = plan-only; merge/apply = apply + validate; prod behind approval.
- [ ] `universal_ddi` selected? — `acknowledge_saas_boundary = true`, the authorization
      review is on file, and outbound 443 to `csp.infoblox.com` is documented.

---

## Appendix A — Variable Worksheets (fill-in forms)

Copy each block, replace every `____` with your value, and keep the rest. Fields marked
**REQUIRED** have no default — the plan/deploy fails without them. The trailing comment
gives the **source** of each value:

- **you choose** — a design decision (region, CIDRs, names)
- **Stage-1 output** — comes from the CIS Landing Zone (Phase 2)
- **generated** — a command produces it (`oci …`) or a Stage-2 output does (Phase 7)
- **existing** — an already-provisioned resource (e.g. your Vault)

### A.1 Terraform — `terraform/terraform.tfvars`

```hcl
# ---- REQUIRED (no default) ----
region                     = "____"   # you choose — OCI region, OC1 (e.g. us-ashburn-1)
tenancy_ocid               = "____"   # Stage-1/existing — ocid1.tenancy...
network_compartment_ocid   = "____"   # Stage-1 output — ocid1.compartment...
hub_vcn_ocid               = "____"   # Stage-1 output — ocid1.vcn...
ddi_subnet_cidr            = "____"   # you choose — from the IPAM plan (e.g. 10.100.8.0/26)
vault_ocid                 = "____"   # existing — ocid1.vault...
vnios_shape                = "____"   # you choose — flexible shape per NIOS model/region
availability_domains       = ["____"] # you choose — AD name(s) (single-AD regions: one)
admin_password_secret_ocid = "____"   # generated — Phase 3 (ocid1.vaultsecret...)
temp_license_secret_ocid   = "____"   # generated — Phase 3
mgmt_source_cidrs          = ["____"] # you choose — bastion/mgmt CIDRs (NEVER 0.0.0.0/0)
dns_client_cidrs           = ["____"] # you choose — spoke + on-prem CIDRs for DNS (NEVER 0.0.0.0/0)

# Image: EITHER supply a pre-imported OCID, OR drive the import here.
vnios_image_ocid = "____"             # generated — Phase 5 (oci compute image import)
# import_image   = true               # alternative: let Terraform import
# image_source_uri = "____"           #   Object Storage URI of the uploaded qcow2/VMDK

# ---- OPTIONAL (defaults shown — change as needed) ----
name_prefix               = "ddi"
environment               = "prod"          # dev | test | prod
deployment_model          = "grid"          # grid | universal_ddi
acknowledge_saas_boundary = false           # MUST be true if deployment_model = "universal_ddi"
compliance_profile        = "fedramp-moderate"
member_count              = 2               # >= 2 for HA
fault_domains             = ["FAULT-DOMAIN-1", "FAULT-DOMAIN-2"]
vnios_ocpus               = 4
vnios_memory_gbs          = 32
data_volume_size_gbs      = 0               # >0 attaches a vNIOS data block volume
discovery_identity_type   = "instance_principal"   # or "api_key_user"
security_model            = "nsg"           # or "security_list"
freeform_tags             = {}
defined_tags              = {}

# Security / networking
drg_ocid                  = null            # Stage-1 output — hub-spoke DRG
monitoring_source_cidrs   = []              # REQUIRED only if enable_snmp = true
grid_peer_cidrs           = ["____"]        # grid only — on-prem GM subnet + DDI subnet
enable_ssh                = false
enable_dhcp               = false
enable_snmp               = false

# DNS integration
manage_resolver_endpoints     = true
hub_resolver_ocid             = "____"      # Stage-1 output — hub VCN resolver OCID
resolver_endpoint_subnet_ocid = "____"      # existing — resolver endpoint subnet OCID
oci_listening_endpoint_ip     = null        # OCI resolver LISTENING IP (null = skip forwarders)
oci_forward_domains           = ["oraclevcn.com"]
enterprise_forward_domains    = ["corp.example"]
ddi_anycast_vip               = null        # set once you own the anycast VIP
enable_spoke_dns_write        = false
spoke_vcn_ocids               = []

# Discovery scoping
discovered_compartment_ocids  = ["____"]    # compartments to grant read for discovery
enable_record_write           = false       # true grants 'manage dns'
discovery_user_ocid           = null        # only if discovery_identity_type = "api_key_user"
discovery_dynamic_group_matching_rule = null # override the default instance-match rule

# OCI Vault secret OCIDs (VALUES go into Vault — see A.3)
grid_shared_secret_ocid       = "____"      # grid only
saas_join_token_secret_ocid   = null        # universal_ddi only

# Grid join (deployment_model = "grid")
grid_name       = "Infoblox"
grid_master_vip = "____"                    # on-prem GM VIP (null only for a lab)

# Universal DDI (deployment_model = "universal_ddi")
infoblox_portal_url = "csp.infoblox.com"    # scheme added at runtime
```

### A.2 OCI Vault secrets (the values referenced by A.1)

| Secret (suggested name) | Content to store | Source | Applies to |
|---|---|---|---|
| `ddi-admin-password` | vNIOS `admin` password to set at first boot | you choose (strong) | both |
| `ddi-temp-license` | temp license string, e.g. `vnios dns dhcp grid enterprise` | Infoblox licensing | both |
| `ddi-grid-shared-secret` | Grid shared secret used to join members | your Grid config | `grid` |
| `ddi-uddi-join-token` | Infoblox Portal (CSP) join token | Infoblox Portal | `universal_ddi` |

```bash
b64() { printf '%s' "$1" | base64 | tr -d '\n'; }
NET=____   # network_compartment_ocid
VAULT=____ # vault_ocid
KEY=____   # a key OCID inside the vault

oci vault secret create-base64 -c "$NET" --vault-id "$VAULT" --key-id "$KEY" \
  --secret-name ddi-admin-password  --secret-content-content "$(b64 '____')"
oci vault secret create-base64 -c "$NET" --vault-id "$VAULT" --key-id "$KEY" \
  --secret-name ddi-temp-license    --secret-content-content "$(b64 '____')"
oci vault secret create-base64 -c "$NET" --vault-id "$VAULT" --key-id "$KEY" \
  --secret-name ddi-grid-shared-secret --secret-content-content "$(b64 '____')"   # grid
oci vault secret create-base64 -c "$NET" --vault-id "$VAULT" --key-id "$KEY" \
  --secret-name ddi-uddi-join-token --secret-content-content "$(b64 '____')"      # universal_ddi

# capture OCIDs -> the *_secret_ocid vars in A.1
oci vault secret list -c "$NET" --vault-id "$VAULT" --name ddi-admin-password \
  --query 'data[0].id' -o tsv
# read a secret back (verify):
oci secrets secret-bundle get --secret-id "____" \
  --query 'data."secret-bundle-content".content' -o tsv | base64 -d
```

### A.3 Validation scripts — environment forms

**`validation/dns-validation.sh`**

```bash
export DDI_VIP="____"                 # REQUIRED — anycast VIP or member IP (Stage-2 ddi_anycast_vip)
export TEST_FQDN="____"               # REQUIRED — an authoritative A record (e.g. host.corp.example)
export EXPECTED_IP="____"             # REQUIRED — the IP TEST_FQDN must resolve to
export DNS_PORT="53"                  # default 53
export DNS_TIMEOUT="5"                # default 5 (seconds)
export OCI_FQDN="____"                # optional — an OCI-owned name (e.g. app.<subnet>.<vcn>.oraclevcn.com)
export OCI_EXPECTED_IP="____"         # optional — expected private IP for OCI_FQDN
```

**`validation/discovery-sync-check.sh`**

```bash
export DDI_API_FLAVOR="nios"          # nios | universal_ddi (default nios)
export STALE_THRESHOLD_MIN="1440"     # default 1440 (24h)
# --- NIOS (deployment_model = grid) ---
export GRID_MASTER="____"             # REQUIRED (nios) — Grid Master host/IP
export INFOBLOX_USERNAME="____"       # REQUIRED (nios)
export INFOBLOX_PASSWORD="____"       # REQUIRED (nios) — inject from OCI Vault / CI secret
export WAPI_VERSION="v2.12"           # default v2.12
export WAPI_CA_BUNDLE="____"          # optional — CA bundle for TLS verification
export DISCOVERY_TASK_NAME="____"     # optional — filter to a named sync task
# --- Universal DDI (deployment_model = universal_ddi) ---
export INFOBLOX_CSP_URL="csp.infoblox.com"  # default host (scheme added at runtime)
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
export CANDIDATE_NETWORK="____"       # optional — pre-check one CIDR before allocating
```

### A.4 Pipeline — GitHub Actions (`pipelines/github-actions-oci-ddi.yml`)

Set under **Settings → Secrets and variables → Actions** (or a repo Environment).

**Secrets** (OCI API-key config — OIDC-to-GitHub is limited on OCI):

| Secret | Value | Source |
|---|---|---|
| `OCI_CLI_USER` | user OCID for the pipeline | you choose |
| `OCI_CLI_TENANCY` | tenancy OCID | Stage-1 |
| `OCI_CLI_FINGERPRINT` | API key fingerprint | generated |
| `OCI_CLI_KEY_CONTENT` | API private key (PEM) | generated |
| `OCI_CLI_REGION` | region, e.g. us-ashburn-1 | you choose |
| `TF_BACKEND_ACCESS_KEY` / `TF_BACKEND_SECRET_KEY` | S3-compat Customer Secret Key for state | generated |

**Variables** (`vars.*`):

| Variable | Value | Source |
|---|---|---|
| `STATE_BUCKET` / `STATE_NAMESPACE` | Object Storage state backend | you create (Phase 1) |
| `LZ_STATE_BUCKET` / `LZ_STATE_KEY` | Stage-1 state location | Stage-1 |
| `VAULT_OCID` | your OCI Vault | existing |
| `DEPLOYMENT_MODEL` / `ACKNOWLEDGE_SAAS_BOUNDARY` | `grid` / `false` | you choose |
| `TEST_FQDN` / `EXPECTED_IP` / `OCI_FQDN` | validation inputs (A.3) | you choose |
| `DDI_VIP` / `GRID_MASTER` | Stage-2 outputs | generated (Phase 7) |

> Never put `INFOBLOX_PASSWORD`, `INFOBLOX_CSP_TOKEN`, or the vNIOS admin password in
> plain pipeline variables — reference them from **OCI Vault** so they are injected at
> run time only.

---

## Sources

- [OCI CIS Landing Zone quickstart (Terraform)](https://github.com/oracle-quickstart/oci-cis-landingzone-quickstart)
- [Oracle — OCI Terraform provider (Registry docs)](https://registry.terraform.io/providers/oracle/oci/latest/docs)
- [Oracle — OCI DNS (private views, resolvers, endpoints)](https://docs.oracle.com/en-us/iaas/Content/DNS/Tasks/privatedns.htm)
- [Infoblox — `infobloxopen/infoblox` Terraform provider (Registry docs)](https://registry.terraform.io/providers/infobloxopen/infoblox/latest/docs)
- [Infoblox — terraform-provider-infoblox (GitHub)](https://github.com/infobloxopen/terraform-provider-infoblox)
- [Infoblox — Firewall Requirements for Infoblox Cloud Services (NIOS-X / 443)](https://docs.infoblox.com/space/BloxOneInfrastructure/873660456/Firewall+Requirements+for+Infoblox+Cloud+Services)
- Module contract: [`_module-contract.md`](./_module-contract.md)
- Architecture guide: [`OCI-LZ-Infoblox-DDI-Automation-Guide.md`](./OCI-LZ-Infoblox-DDI-Automation-Guide.md)
- Deploy chapter (click/CLI mechanics): [`../04-oci.md`](../04-oci.md)

---

## Optional: run this runbook through ServiceNow (governed path)

Every manual step here can be driven from a **ServiceNow Service Catalog item** instead of a shell: request → approval / separation-of-duties gate → **CPG Terraform Connector** apply of [`terraform/`](./terraform/README.md) on an in-boundary MID Server → **IntegrationHub REST** allocate/register over Infoblox WAPI/Universal DDI → the [`validation/`](./validation/README.md) scripts run by the MID Server as a **pass/fail gate** → **Service Graph Connector** CMDB reconcile → close with a full audit trail. Wire it per [`servicenow/ServiceNow-Orchestration.md`](./servicenow/ServiceNow-Orchestration.md) and stand up the importable records from [`servicenow-app/`](../servicenow-app/README.md); the model and control mapping are in [Chapter 7](../07-servicenow-orchestration.md). Secrets stay in OCI Vault; the MID Server and credential path stay inside the ATO boundary.
