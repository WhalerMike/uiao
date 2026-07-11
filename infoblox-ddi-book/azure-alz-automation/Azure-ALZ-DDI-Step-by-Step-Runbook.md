# Azure Landing Zone + Infoblox DDI — Step-by-Step Deployment Runbook

> **Companion to** [`Azure-ALZ-Infoblox-DDI-Automation-Guide.md`](./Azure-ALZ-Infoblox-DDI-Automation-Guide.md).
> That guide explains *why* the architecture is shaped the way it is; this runbook
> is the **"do exactly this, then this"** operational sequence that deploys it with
> the IaC package in this directory. Every command, variable name, resource name,
> port, IAM role, and output below is taken from the real module and its
> [`_module-contract.md`](./_module-contract.md) — nothing is invented. Where a
> value is genuinely environment-specific (image version, VM SKU, region, CIDR)
> the runbook says **"supply your own"** rather than guessing.
>
> **Posture (fixed):** GCC-Moderate operating posture on **commercial Azure
> (`.com` endpoints)** — `management.azure.com`, `login.microsoftonline.com`,
> `*.blob.core.windows.net`. **Not** Azure Government (`.us`). Do **not** set the
> `azurerm` provider `environment` to `usgovernment`.
>
> **Default path:** `deployment_model = "grid"` (vNIOS Grid, control plane inside
> the ATO boundary). The `universal_ddi` (Infoblox Portal / SaaS) path is shown in
> clearly-marked **⚠ UNIVERSAL DDI** callout boxes and always honors the
> `acknowledge_saas_boundary` guard.
>
> **Status of the IaC:** a coherent starter skeleton — structurally correct and
> guardrail-bearing, *not* a certified production module. Pin your own versions,
> confirm the Marketplace image, and test in a sandbox ALZ first.

---

## Prerequisites checklist

Confirm **all** of these before Phase 0. Boxes map to the phases that consume them.

- [ ] **Stage-1 ALZ already deployed.** The Microsoft ALZ Accelerator (management
      groups, policy, identity, and the Connectivity hub VNet with — ideally — an
      Azure DNS Private Resolver) exists and publishes outputs. This module is
      **Stage 2**; it never builds Stage 1.
- [ ] **Stage-1 outputs available:** `hub_vnet_id`, `hub_resource_group_name`,
      `connectivity_subscription_id`, `log_analytics_workspace_id`, and (optional)
      `firewall_private_ip` / the Private Resolver inbound endpoint IP.
- [ ] **Roles.** You (or the pipeline identity) can create resources in the hub
      resource group, create role assignments in the discovered subscriptions, and
      set Key Vault secrets. Discovery uses a *separate, least-privileged* identity
      (Phase 4).
- [ ] **Tooling:** `az` CLI ≥ 2.53, Terraform ≥ 1.5 (the module requires
      `>= 1.5.0, < 2.0.0` for `precondition`/`check` blocks), `jq`, `dig`/`nslookup`.
      Bicep path additionally needs `az bicep`.
- [ ] **An existing Key Vault** in (or reachable from) the hub subscription for the
      module secrets.
- [ ] **A free, non-overlapping CIDR** inside the hub VNet address space for the
      dedicated `ddi-subnet` (`ddi_subnet_address_prefix`).
- [ ] **Licensing/Marketplace:** vNIOS BYOL token or Universal DDI subscription,
      DNS/DHCP/Grid/Threat-Defense licenses, and acceptance of the Azure Marketplace
      plan for the `infoblox` publisher image.
- [ ] **Explicit CIDRs** for NSG scoping — mgmt, DNS clients (spokes/on-prem), Grid
      peers/GM, monitoring. **Never `0.0.0.0/0`** (the module hard-fails on it).

---

## Phase 0 — Decisions & inventory

### Step 0.1 — Choose the control-plane model

The single most consequential decision. It sets **where the control plane lives
relative to your ATO boundary**.

| | `deployment_model = "grid"` (default) | `deployment_model = "universal_ddi"` |
|---|---|---|
| Control plane | vNIOS **Grid**, self-operated in-tenant | Infoblox **Portal / CSP** (SaaS) |
| Vs. ATO boundary | **Inside** | **Outside** |
| Data-plane members | vNIOS DNS members | NIOS-X servers |
| Outbound dependency | Grid VPN `1194/udp` + `2114/tcp` | **outbound `443` to `csp.infoblox.com`** |
| GCC-Moderate fit | **Boundary-clean — recommended default** | Requires authorization review |
| Code guard | none | hard-fails unless `acknowledge_saas_boundary = true` |

**Decision:** For a boundary-clean GCC-Moderate landing zone, choose **`grid`**.
Only choose `universal_ddi` after completing the FedRAMP/authorization review for
the SaaS control-plane egress.

**Verify:** Write the chosen `deployment_model` value down; it must match across
Terraform `terraform.tfvars`, Bicep `main.bicepparam`, and the pipeline env
(`DEPLOYMENT_MODEL` / `deploymentModel`).

> **⚠ UNIVERSAL DDI callout.** If you selected `universal_ddi`, you must also set
> `acknowledge_saas_boundary = true` **and** be able to justify the outbound-443
> dependency to `csp.infoblox.com`. Leaving the ack `false` (the default) is a
> deliberate hard-fail — see Phase 6.

### Step 0.2 — Gather Stage-1 outputs into shell variables

```bash
# Fill these from your Stage-1 ALZ Accelerator outputs.
export HUB_RG="rg-connectivity-hub"                 # hub_resource_group_name
export HUB_VNET_ID="/subscriptions/<conn-sub>/resourceGroups/rg-connectivity-hub/providers/Microsoft.Network/virtualNetworks/vnet-hub-eastus"
export CONN_SUB="<connectivity_subscription_id>"    # bare GUID
export LAW_ID="/subscriptions/<mgmt-sub>/resourceGroups/rg-mgmt/providers/Microsoft.OperationalInsights/workspaces/law-alz"
export PR_INBOUND_IP="10.10.2.4"                     # Private Resolver inbound endpoint (Stage-1/existing)
export LOCATION="eastus"                             # supply your own region
export DDI_SUBNET_CIDR="10.10.4.0/27"                # supply your own free, non-overlapping CIDR
```

**Verify:** `echo "$HUB_VNET_ID"` matches the contract regex
`/subscriptions/.../virtualNetworks/<name>` — the module's `hub_vnet_id` validation
rejects anything else.

---

## Phase 1 — Tooling & auth

### Step 1.1 — Install and check tooling

```bash
az version
terraform version          # expect >= 1.5.0, < 2.0.0
jq --version ; dig -v 2>&1 | head -1
```

**Verify:** `terraform version` prints a 1.5+ build; `az version` prints the CLI
and installed extensions.

### Step 1.2 — Log in to commercial Azure and select the subscription

```bash
az cloud set --name AzureCloud          # commercial .com — NOT AzureUSGovernment
az login                                # opens login.microsoftonline.com
az account set --subscription "$CONN_SUB"
az account show --query '{name:name, id:id, cloud:environmentName}' -o table
```

**Verify:** `environmentName` is `AzureCloud` and `id` equals `$CONN_SUB`.

> **Troubleshooting — wrong cloud.** If `environmentName` shows
> `AzureUSGovernment`, run `az cloud set --name AzureCloud` and re-login. The `.us`
> boundary is explicitly out of scope for this deliverable.

### Step 1.3 — Create the Terraform remote-state backend (Azure Storage)

State lives in a commercial `*.blob.core.windows.net` account with locking.

```bash
export TFSTATE_RG="rg-tfstate"
export TFSTATE_SA="sttfstate$RANDOM"     # must be globally unique, lowercase
export TFSTATE_CONTAINER="tfstate"

az group create -n "$TFSTATE_RG" -l "$LOCATION"
az storage account create -g "$TFSTATE_RG" -n "$TFSTATE_SA" -l "$LOCATION" \
  --sku Standard_LRS --min-tls-version TLS1_2 --allow-blob-public-access false
az storage container create --account-name "$TFSTATE_SA" -n "$TFSTATE_CONTAINER" \
  --auth-mode login
```

**Verify:**
`az storage container show --account-name "$TFSTATE_SA" -n "$TFSTATE_CONTAINER" --auth-mode login`
returns the container. State-locking is automatic via blob leases.

---

## Phase 2 — Consume Stage-1 outputs

The module learns about the hub **only** through Stage-1 outputs — it never queries
or mutates Stage-1-owned resources. Two equivalent ways to fetch them:

### Step 2.1 — Option A: `terraform_remote_state` data source (preferred)

The `examples/hub-integration/main.tf` reads the ALZ Accelerator state directly:

```hcl
data "terraform_remote_state" "alz" {
  backend = "azurerm"
  config = {
    resource_group_name  = "rg-tfstate"
    storage_account_name = "sttfstateexample"      # supply your own
    container_name       = "tfstate"
    key                  = "alz-accelerator/connectivity.tfstate"
  }
}

# then, in the module block:
#   hub_resource_group_name = data.terraform_remote_state.alz.outputs.hub_resource_group_name
#   hub_vnet_id             = data.terraform_remote_state.alz.outputs.hub_vnet_id
#   key_vault_id            = data.terraform_remote_state.alz.outputs.connectivity_key_vault_id
```

**Verify:** `terraform console` → `data.terraform_remote_state.alz.outputs.hub_vnet_id`
prints the hub VNet ID.

### Step 2.2 — Option B: `az` lookups (provider-agnostic)

If Stage 1 does not share Terraform state, resolve the same facts with `az`:

```bash
# hub_vnet_id (already have HUB_RG + vnet name)
az network vnet show -g "$HUB_RG" -n vnet-hub-eastus --query id -o tsv

# connectivity_subscription_id
az account show --query id -o tsv

# log_analytics_workspace_id
az monitor log-analytics workspace show -g rg-mgmt -n law-alz --query id -o tsv

# Private Resolver inbound endpoint IP (Stage-1/existing)
az dns-resolver inbound-endpoint list -g "$HUB_RG" --resolver-name pdr-hub \
  --query "[0].ipConfigurations[0].privateIpAddress" -o tsv
```

**Verify:** each command prints a value; feed them into the tfvars/bicepparam in
Phase 5. These map to variables `hub_vnet_id`, `hub_resource_group_name`,
`private_resolver_inbound_ip`, and the diagnostic-settings target (`log_analytics_workspace_id`).

---

## Phase 3 — Secrets in Key Vault

The module **reads existing** Key Vault secrets (`data "azurerm_key_vault_secret"`);
it never creates them and never emits them as plaintext outputs. Create/confirm the
vault, then store the secrets under the names the module expects.

> **Secret-name defaults differ between Terraform and Bicep** — set them explicitly
> or override the `*_secret_name` variables to match your vault.
>
> | Purpose | Terraform default | Bicep default |
> |---|---|---|
> | Admin password | `ddi-vnios-admin-password` | `ddi-admin-password` |
> | Temp license (BYOL) | `ddi-vnios-temp-license` | `ddi-temp-license` |
> | Grid shared secret | `ddi-grid-shared-secret` | `ddi-grid-shared-secret` |
> | Portal join token (uddi) | `ddi-uddi-join-token` | *(supplied as secret URI)* |

### Step 3.1 — Reference (or create) the Key Vault

```bash
export KV_NAME="kv-ddi-hub"
az keyvault show -n "$KV_NAME" --query id -o tsv \
  || az keyvault create -g "$HUB_RG" -n "$KV_NAME" -l "$LOCATION" \
       --enable-rbac-authorization true
export KEY_VAULT_ID="$(az keyvault show -n "$KV_NAME" --query id -o tsv)"
```

**Verify:** `echo "$KEY_VAULT_ID"` matches
`/subscriptions/.../providers/Microsoft.KeyVault/vaults/...` (the `key_vault_id`
validation regex).

### Step 3.2 — Store the module secrets

```bash
# Admin password (bootstrapped into vNIOS/NIOS-X via cloud-init user-data).
az keyvault secret set --vault-name "$KV_NAME" \
  --name ddi-vnios-admin-password --value '<STRONG_ADMIN_PASSWORD>'

# vNIOS temporary license bundle for first boot.
az keyvault secret set --vault-name "$KV_NAME" \
  --name ddi-vnios-temp-license  --value 'vnios dns dhcp grid enterprise'

# Grid shared secret used to join Azure members to the Grid (grid path).
az keyvault secret set --vault-name "$KV_NAME" \
  --name ddi-grid-shared-secret  --value '<GRID_SHARED_SECRET>'
```

> **⚠ UNIVERSAL DDI callout.** For `universal_ddi`, also store the Portal join
> token (NIOS-X hosts phone home to `csp.infoblox.com` over 443 with it):
> ```bash
> az keyvault secret set --vault-name "$KV_NAME" \
>   --name ddi-uddi-join-token --value '<PORTAL_JOIN_TOKEN>'
> ```

**Verify:**
`az keyvault secret list --vault-name "$KV_NAME" --query "[].name" -o tsv`
lists the secret names you set.

> **Troubleshooting — RBAC vs. access policy.** With
> `--enable-rbac-authorization true`, granting yourself **Key Vault Secrets Officer**
> is required to `secret set`, and the deploy identity needs **Key Vault Secrets
> User** to read at apply time. A `Forbidden` on `secret set` means the role has not
> propagated yet — wait ~1 minute and retry.

---

## Phase 4 — Discovery identity + least-privilege roles

The Azure→Infoblox IPAM sync uses a **separate, least-privileged** identity
(`ddi-disco-mi`). Prefer a user-assigned managed identity; the module also supports
an existing service-principal object ID. Roles are scoped per contract §5 — **no
`Owner`, no subscription-level `Contributor`.**

| Role | Scope | When | Built-in role GUID |
|---|---|---|---|
| `Reader` | discovered subscription(s) | always | `acdd72a7-3385-48ef-bd42-f606fba81ae7` |
| `Private DNS Zone Contributor` | RG(s) holding private zones | only if `enable_record_write` | `b12aa53e-6015-4669-85d0-8515ebb3ae7f` |
| `Network Contributor` | spoke VNet(s) | only if `enable_spoke_dns_write` | `4d97b98b-1d4f-11e3-a3e1-000c298c8e0b` |

### Step 4.1 — Create the user-assigned managed identity

The Terraform module creates `ddi-disco-mi` for you when
`discovery_identity_type = "user_assigned_mi"`. If you want it pre-created (or you
are on the Bicep path, whose `discovery-identity.bicep` runs at RG scope), do:

```bash
az identity create -g "$HUB_RG" -n ddi-disco-mi -l "$LOCATION"
export DISCO_PRINCIPAL_ID="$(az identity show -g "$HUB_RG" -n ddi-disco-mi --query principalId -o tsv)"
export DISCO_CLIENT_ID="$(az identity show -g "$HUB_RG" -n ddi-disco-mi --query clientId -o tsv)"
```

**Verify:** `echo "$DISCO_PRINCIPAL_ID"` is a GUID. This becomes the module output
`discovery_identity_id`.

### Step 4.2 — Reader on each discovered subscription (always)

Because the Bicep module runs at **resource-group** scope, the subscription-scoped
`Reader` grant is emitted out-of-band (a Bicep module cannot widen RG→subscription).
Run it explicitly for every subscription to be discovered:

```bash
for SUB in "$CONN_SUB" "<spoke-sub-guid-1>" "<spoke-sub-guid-2>"; do
  az role assignment create \
    --assignee-object-id "$DISCO_PRINCIPAL_ID" \
    --assignee-principal-type ServicePrincipal \
    --role "Reader" \
    --scope "/subscriptions/$SUB"
done
```

> On the **Terraform** path these are created for you from
> `discovered_subscription_ids` (resource `azurerm_role_assignment.reader`) — you do
> not need to run the loop; just set the variable.

**Verify:**
`az role assignment list --assignee "$DISCO_PRINCIPAL_ID" --role Reader --all -o table`
shows one Reader row per discovered subscription.

### Step 4.3 — (Opt-in) Private DNS Zone Contributor for record write-back

Only when Infoblox writes records into Azure Private DNS
(`enable_record_write = true`, scope = the private-zone RG):

```bash
az role assignment create \
  --assignee-object-id "$DISCO_PRINCIPAL_ID" --assignee-principal-type ServicePrincipal \
  --role "Private DNS Zone Contributor" \
  --scope "/subscriptions/$CONN_SUB/resourceGroups/rg-private-dns-zones"
```

### Step 4.4 — (Opt-in) Network Contributor on spokes for `dns_servers` write

Only when the module writes `dns_servers` on spokes (`enable_spoke_dns_write = true`
+ `spoke_vnet_ids` set). Scope to the **specific VNet**, never subscription-wide:

```bash
az role assignment create \
  --assignee-object-id "$DISCO_PRINCIPAL_ID" --assignee-principal-type ServicePrincipal \
  --role "Network Contributor" \
  --scope "/subscriptions/<spoke-sub>/resourceGroups/<spoke-rg>/providers/Microsoft.Network/virtualNetworks/<spoke-vnet>"
```

**Verify:**
`az role assignment list --assignee "$DISCO_PRINCIPAL_ID" --all -o table` shows only
the roles you intended — no `Owner`, no subscription `Contributor`.

> **Troubleshooting — discovery identity missing a role.** If Infoblox discovery
> enumerates nothing, the usual cause is Reader missing on a target subscription
> (Step 4.2). If record write-back or spoke `dns_servers` writes fail with `403`,
> the opt-in role (4.3/4.4) is missing or not yet propagated.

---

## Phase 5 — Configure the module (`terraform.tfvars`)

Start from `examples/hub-integration/main.tf`, then externalize the values into a
`terraform.tfvars` next to the Terraform module. Every variable below is real.

```hcl
# terraform.tfvars — Stage-2 Infoblox DDI (grid, commercial .com, GCC-Moderate)

# --- Basics / boundary ---
name_prefix        = "ddi"                 # -> ddi-subnet, ddi-nsg, ddi-vnios-z1, ddi-disco-mi
location           = "eastus"              # supply your own region
environment        = "prod"                # dev | test | prod
deployment_model   = "grid"                # boundary-clean default
compliance_profile = "gcc-moderate"
# acknowledge_saas_boundary left false — not needed for grid.

# --- From Stage-1 outputs ---
hub_resource_group_name = "rg-connectivity-hub"
hub_vnet_id             = "/subscriptions/<conn-sub>/resourceGroups/rg-connectivity-hub/providers/Microsoft.Network/virtualNetworks/vnet-hub-eastus"
key_vault_id            = "/subscriptions/<conn-sub>/resourceGroups/rg-connectivity-hub/providers/Microsoft.KeyVault/vaults/kv-ddi-hub"

# --- Dedicated DDI subnet (must fit hub VNet, not overlap) ---
ddi_subnet_address_prefix = "10.10.4.0/27"

# --- Members: 2 across zones 1 and 2 (HA) ---
member_count       = 2
availability_zones = ["1", "2"]

# --- VM SKU + Marketplace image: supply your own (do NOT invent versions) ---
vnios_vm_sku = "Standard_E4s_v5"           # Esv5 for NIOS 9.0.5+; verify supported list + quota
vnios_image = {
  publisher = "infoblox"
  offer     = "infoblox_nios_on_azure"
  sku       = "<your-plan-sku>"            # from `az vm image list --publisher infoblox --all`
  version   = "<tested-version>"           # pin a build in prod; "latest" only in labs
  # plan_name = optional; defaults to sku
}

# --- NSG source scoping (never 0.0.0.0/0) ---
mgmt_source_cidrs = ["10.10.0.0/24"]                 # jumpbox/bastion subnet
dns_client_cidrs  = ["10.20.0.0/16", "10.30.0.0/16"] # spoke ranges permitted to query 53
grid_peer_cidrs   = ["10.10.4.0/27", "192.168.100.0/24"] # DDI subnet + on-prem GM (grid only)

# --- Grid join (usual pattern: join Azure members to the on-prem GM) ---
grid_name       = "CorpGrid"
grid_master_vip = "192.168.100.10"        # on-prem Grid Master VIP; null => first member is GM (lab only)

# --- DNS integration (§8) ---
private_resolver_inbound_ip = "10.10.2.4"  # Stage-1 Private Resolver inbound endpoint
ddi_anycast_vip             = "10.10.4.10"  # advertised from both members
# azure_service_forward_domains defaults to privatelink.blob/database/vaultcore + azure.com

# --- Discovery identity + least-privilege RBAC (§5) ---
discovery_identity_type     = "user_assigned_mi"
discovered_subscription_ids = ["<spoke-sub-guid-1>"]
enable_record_write         = false        # read-only discovery by default
# private_dns_zone_rg_ids   = [...]         # only if enable_record_write = true

# --- Spoke dns_servers write-through (opt-in; needs Network Contributor) ---
spoke_vnet_ids         = []                 # e.g. ["/subscriptions/.../virtualNetworks/spoke-a"]
enable_spoke_dns_write = false

# --- Secret names (match Phase 3) ---
admin_password_secret_name = "ddi-vnios-admin-password"
temp_license_secret_name   = "ddi-vnios-temp-license"
grid_shared_secret_name    = "ddi-grid-shared-secret"

tags = { owner = "network-platform", costcenter = "cc-1234" }
```

**What the key variables do (all real):**

- `deployment_model` / `acknowledge_saas_boundary` — the boundary switch + its guard.
- `hub_vnet_id` — parsed by the module to derive `hub_vnet_name` and
  `hub_subscription_id`; the `ddi-subnet` is created *inside* this VNet.
- `member_count` + `availability_zones` — members are round-robined over zones;
  ≤ one-zone-per-member yields the clean `ddi-vnios-z1` / `ddi-vnios-z2` names.
- `grid_peer_cidrs` — **required for grid** (an `azurerm_network_security_group`
  precondition fails the plan if `grid` is selected and this is empty).
- `mgmt_source_cidrs` / `dns_client_cidrs` — enforced non-empty and **must not**
  contain `0.0.0.0/0` (variable `validation`).
- `ddi_anycast_vip` — becomes real only after Grid formation (Phase 7); until then
  outputs fall back to `dns_server_ips` (member NIC IPs).

**Boundary-guard behavior (grid):** with `deployment_model = "grid"` the
`terraform_data.boundary_guard` precondition passes silently and no outbound-443
Portal rule is created.

> **⚠ UNIVERSAL DDI callout — tfvars deltas.** To run the SaaS path:
> ```hcl
> deployment_model          = "universal_ddi"
> acknowledge_saas_boundary = true            # REQUIRED — false hard-fails the plan
> saas_join_token_secret_name = "ddi-uddi-join-token"
> infoblox_portal_url       = "https://csp.infoblox.com"   # outbound 443 required
> # grid_master_vip / grid_shared_secret_name are unused on this path
> ```
> With ack `false`, `terraform plan` aborts with the `BOUNDARY VIOLATION` message
> pointing to the authorization review — resources `ddi-niosx-*` and
> `null_resource.portal_enroll` never plan.

---

## Phase 6 — Deploy

### Terraform path (primary)

#### Step 6.1 — Accept the Marketplace terms

Discover the real plan, then accept it (a VM deploy fails otherwise):

```bash
az vm image list --publisher infoblox --all -o table
# Take the urn: <publisher>:<offer>:<sku>:<version>, then:
az vm image terms accept --urn infoblox:infoblox_nios_on_azure:<sku>:<version>
```

> The module also manages this via `azurerm_marketplace_agreement.vnios`
> (`accept_marketplace_agreement = true` by default). If the plan is already
> accepted subscription-wide, set `accept_marketplace_agreement = false` to skip it.

**Verify:**
`az vm image terms show --urn infoblox:infoblox_nios_on_azure:<sku>:<version> --query accepted`
returns `true`.

#### Step 6.2 — `init` with the remote backend

```bash
cd infoblox-ddi-book/azure-alz-automation/terraform
terraform init \
  -backend-config="resource_group_name=$TFSTATE_RG" \
  -backend-config="storage_account_name=$TFSTATE_SA" \
  -backend-config="container_name=$TFSTATE_CONTAINER" \
  -backend-config="key=ddi-prod.tfstate"
```

**Verify:** `Terraform has been successfully initialized!` and the `azurerm`,
`infobloxopen/infoblox`, `tls`, and `null` providers resolve (per `versions.tf`).

#### Step 6.3 — `plan` (guards are evaluated here)

```bash
terraform plan -input=false -out=tfplan
```

**Expected:** the plan creates `ddi-subnet`, `ddi-nsg` + rules, `ddi-vnios-z1` /
`ddi-vnios-z2` (NICs + VMs), the `ddi-disco-mi` identity + Reader role
assignment(s), the `infoblox_zone_forward` objects (if `private_resolver_inbound_ip`
set), and the marketplace agreement. The boundary guard and NSG CIDR scoping are
checked at **plan** time, not apply.

**Verify:** plan summary shows the expected adds and **no** `0.0.0.0/0` sources.

#### Step 6.4 — `apply`

```bash
terraform apply -input=false -auto-approve tfplan
```

**Expected outputs (contract §7):**

```bash
terraform output
# ddi_subnet_id         = "/subscriptions/.../subnets/ddi-subnet"
# dns_server_ips        = ["10.10.4.4", "10.10.4.5"]   # member NIC IPs
# ddi_anycast_vip       = "10.10.4.10"                  # null until Grid advertises it
# grid_master_ip        = "192.168.100.10"              # on-prem GM (grid only)
# discovery_identity_id = "/subscriptions/.../userAssignedIdentities/ddi-disco-mi"
```

**Cross-AZ members:** confirm the two members landed in different zones:

```bash
az vm list -g "$HUB_RG" --query "[?starts_with(name,'ddi-vnios')].{name:name, zone:zones[0]}" -o table
```

**Verify:** `ddi-vnios-z1` shows zone `1`, `ddi-vnios-z2` shows zone `2`.

> **Troubleshooting — Marketplace terms not accepted.** Apply fails with *"the
> subscription has not accepted the legal terms"* → run Step 6.1 (or ensure
> `accept_marketplace_agreement = true`).
>
> **Troubleshooting — grid plan fails immediately.** *"deployment_model='grid'
> requires grid_peer_cidrs"* → set `grid_peer_cidrs` (Grid members/GM ranges).
>
> **Troubleshooting — DNS-object apply fails.** `infoblox_zone_forward` needs a
> reachable Grid/NIOS WAPI endpoint. Members are not yet Grid-joined at first apply;
> either configure the `infoblox` provider `server` to the on-prem GM, or run the
> DNS-object resources in a **second phase** after Phase 7 (use `-target` or a
> dependent module). This ordering is by design.

### ⚠ Bicep path (parallel alternative — pick one, never both)

Deploy at **resource-group** scope into the hub RG.

#### Step 6.B1 — Fill `main.bicepparam`

Replace the `REPLACE_ME_*` placeholders (`vnios_vm_sku`, `vnios_image` incl. the
`plan` block, `hub_vnet_id`, `key_vault_id`, CIDRs). Note the Bicep secret-name
defaults (`ddi-admin-password`, `ddi-temp-license`, `ddi-grid-shared-secret`) and
that `mgmt_source_prefix` is **required** and never `0.0.0.0/0`.

#### Step 6.B2 — Validate & deploy

```bash
cd infoblox-ddi-book/azure-alz-automation/bicep
az deployment group validate -g "$HUB_RG" -f main.bicep -p main.bicepparam
az deployment group create   -g "$HUB_RG" -f main.bicep -p main.bicepparam
```

**Expected outputs:** `ddi_subnet_id`, `dns_server_ips` (member NIC IPs as a
stand-in), `ddi_anycast_vip`, `grid_master_ip`, `discovery_identity_id`, plus the
`boundary_guard_note`.

**Verify:**
`az deployment group show -g "$HUB_RG" -n main --query properties.outputs -o json`

> **Boundary guard (Bicep) — div-by-zero.** With `deployment_model = 'universal_ddi'`
> and `acknowledge_saas_boundary = false`, `saasBoundaryViolation` is `true`,
> `boundaryGuardDivisor` becomes `0`, and `1 / boundaryGuardDivisor` aborts the whole
> deployment with a division-by-zero evaluation error **before any resource is
> created**. Because the divisor is derived from runtime params, Bicep does not
> constant-fold it. Set `acknowledge_saas_boundary = true` (post-review) to proceed.
>
> **Bicep DDI-object limitation.** There is no Bicep-native Infoblox resource. The
> `universal-ddi.bicep` module runs a `Microsoft.Resources/deploymentScripts`
> (Azure CLI) under `ddi-disco-mi` that fetches the join token from Key Vault and
> calls the Portal API (placeholder). Conditional forwarders and IPAM on the grid
> path are an **API/Ansible/Terraform-provider handoff** — see Phases 7–9.

---

## Phase 7 — Grid formation / Universal DDI onboarding

The VMs exist, but the **control plane is not yet formed**. `ddi_anycast_vip` and
`grid_master_ip` become operationally real only after this phase.

### Step 7.1 — Grid path: form / join the Grid

Each member booted with `custom_data` (`#infoblox-config`) carrying the temp
license, admin password, and grid-join parameters from Key Vault. Complete
formation on the members:

- **Usual Azure pattern:** the on-prem Grid Master (`grid_master_vip`) is
  authoritative; the Azure members join as **Grid members** over `1194/udp` +
  `2114/tcp`. Confirm each member appears in the Grid Manager UI under your
  `grid_name` (e.g. `CorpGrid`).
- **Lab/greenfield:** if `grid_master_vip = null`, the first member (`ddi-vnios-z1`)
  initializes the Grid as GM; the second joins it.
- **Assign the anycast VIP** (`ddi_anycast_vip`, e.g. `10.10.4.10`) as a shared DNS
  service address advertised from both members, so spokes use one stable resolver.

**Verify (WAPI, from a mgmt host):**

```bash
export GRID_MASTER="<gm-mgmt-ip-or-fqdn>"          # your Grid Master (grid_master_ip)
export INFOBLOX_USERNAME="admin"                    # WAPI user
export INFOBLOX_PASSWORD="<from-key-vault>"         # ddi-vnios-admin-password / WAPI cred
curl -fsS -u "$INFOBLOX_USERNAME:$INFOBLOX_PASSWORD" \
  "https://$GRID_MASTER/wapi/v2.12/member?_return_fields%2B=host_name,service_status"
```

Both Azure members show `service_status` running for DNS. Confirm the exact WAPI
object/field names against `<grid-master>/wapidoc/` (over HTTPS) for your NIOS
version.

> **⚠ UNIVERSAL DDI callout — enroll NIOS-X to the Portal.** Instead of Grid
> formation, each `ddi-niosx-*` host self-enrolls to `csp.infoblox.com` over 443
> using the join token from `custom_data`. The `null_resource.portal_enroll`
> (Terraform) / `deploymentScripts` enroll (Bicep) is the explicit API seam —
> replace its placeholder with the real CSP REST call, then confirm in the Portal
> inventory:
> ```bash
> curl -fsS -H "Authorization: Token $INFOBLOX_CSP_TOKEN" \
>   "https://csp.infoblox.com/api/infra/v1/hosts?_filter=display_name=='ddi-niosx-1'"
> ```

**Verify:** members/hosts report healthy in the Grid Manager UI or the Portal, and
the anycast VIP answers (tested in Phase 11).

---

## Phase 8 — Cloud discovery adapter

Azure RBAC (Phase 4) grants the identity; the **Infoblox side** of discovery is
configured on the control plane — there is no `infoblox_vdiscovery_job` provider
resource, so this is an explicit API/UI handoff (the module documents the seam in
`discovery.tf`).

### Step 8.1 — Grid path: create a vDiscovery job (WAPI)

Point Cloud Network Automation at each subscription, authenticating with the
`ddi-disco-mi` identity (tenant/client ID; a federated cred for the MI, or the SP
secret from Key Vault). Illustrative WAPI handoff:

```bash
curl -fsS -u "$INFOBLOX_USERNAME:$INFOBLOX_PASSWORD" \
  -X POST "https://$GRID_MASTER/wapi/v2.12/vdiscoverytask" \
  -H 'Content-Type: application/json' \
  -d '{"name":"azure-disco","member":"infoblox.localdomain","credential_type":"AZURE"}'
```

Schedule it to run on a cadence (e.g. hourly) so IPAM tracks Azure reality. Confirm
the exact object/fields against `<grid-master>/wapidoc/` for your NIOS version.

> **⚠ UNIVERSAL DDI callout.** Configure a Portal **Universal Cloud** Azure source
> using the same `ddi-disco-mi` credential via the CSP API/UI; the discovery job
> lives in the SaaS control plane.

**Verify:** run the Stage-3 discovery check (Phase 11) — it asserts the job exists,
is not in `ERROR`/`WARNING`, and ran within `STALE_THRESHOLD_MIN`.

---

## Phase 9 — DNS integration

Two conditional-forwarding paths meet at the Azure DNS Private Resolver.

### Step 9.1 — Infoblox → Azure (inbound): conditional forwarders

`dns.tf` creates one `infoblox_zone_forward` per domain in
`azure_service_forward_domains` (default: `privatelink.blob.core.windows.net`,
`privatelink.database.windows.net`, `privatelink.vaultcore.azure.net`, `azure.com`),
each pointing `forward_to.address` at `private_resolver_inbound_ip`. This runs only
when `deployment_model = "grid"` **and** `private_resolver_inbound_ip != null`.

**Verify (after the DNS-object phase applies):**

```bash
curl -fsS -u "$INFOBLOX_USERNAME:$INFOBLOX_PASSWORD" \
  "https://$GRID_MASTER/wapi/v2.12/zone_forward?fqdn=privatelink.blob.core.windows.net"
```

Returns the forward zone targeting the inbound endpoint IP.

### Step 9.2 — Azure → Infoblox (outbound): spoke `dns_servers`

Point spoke/hub VNet `dns_servers` at the DDI resolver. The module writes this
**only** when `spoke_vnet_ids` is non-empty **and** `enable_spoke_dns_write = true`
(which requires the Network Contributor grant from Step 4.4). Otherwise it emits the
VIP as output and leaves the write to the platform team. Manual equivalent:

```bash
az network vnet update --ids "<spoke-vnet-id>" --dns-servers 10.10.4.10   # ddi_anycast_vip
```

**Verify:**
`az network vnet show --ids "<spoke-vnet-id>" --query "dhcpOptions.dnsServers" -o tsv`
returns the anycast VIP (or the `dns_server_ips`).

### Step 9.3 — (Optional) Reverse direction: Private Resolver outbound ruleset

Forward the enterprise domain back to the DDI members (not all deployments automate
this — the platform team may own the resolver):

```bash
az dns-resolver forwarding-rule create -g "$HUB_RG" --ruleset-name rs-corp -n corp \
  --domain-name "corp.example." --forwarding-rule-state Enabled \
  --target-dns-servers '[{"ip-address":"10.10.4.10","port":53}]'
```

**Verify:** from an Azure spoke VM, a `corp.example` name resolves via the DDI VIP
(tested in Phase 11).

> **Troubleshooting — NSG blocking 53/1194/2114.** If DNS times out or Grid members
> won't converge, confirm the `ddi-nsg` rules exist and sources match your CIDRs:
> `Allow-DNS-TCP-In`(100)/`Allow-DNS-UDP-In`(110) from `dns_client_cidrs`,
> `Allow-GridVPN-In`(160, 1194/udp) + `Allow-GridComms-In`(170, 2114/tcp) from
> `grid_peer_cidrs`, and the explicit `Deny-All-Out`(4096) that overrides Azure's
> default internet egress — so NTP(`Allow-NTP-Out`) and DNS-out must be present.
> List with:
> `az network nsg rule list -g "$HUB_RG" --nsg-name ddi-nsg -o table`.

---

## Phase 10 — IPAM automation

Because discovery imports Azure **tags as extensible attributes (EAs)**, IPAM
becomes an API the platform consumes.

### Step 10.1 — Onboard subscriptions & confirm networks appear

vDiscovery walks subscriptions → VNets → subnets and populates Infoblox IPAM as
networks/containers with discovered VMs as records.

**Verify:**

```bash
curl -fsS -u "$INFOBLOX_USERNAME:$INFOBLOX_PASSWORD" \
  "https://$GRID_MASTER/wapi/v2.12/network?_return_fields%2B=network,comment&network_view=default"
```

Azure VNet/subnet CIDRs (including `ddi_subnet` `10.10.4.0/27`) appear as `network`
objects.

### Step 10.2 — Tag-driven allocation & reclaim-on-delete

Keyed on `environment` / `owner` / `costcenter` EAs, provisioning pipelines can carve
the next free subnet from the correct container (via WAPI `nextavailablenetwork` or
the `infoblox_ipv4_network`/`infoblox_network_view` provider resources) and feed that
CIDR into the workload's own IaC. Schedule discovery so a subnet deleted in Azure is
reconciled (reclaimed) on the next sync rather than lingering.

**Verify:** the IPAM conflict gate (Phase 11) reports no overlaps after a sync.

---

## Phase 11 — Validation gates

Run each `validation/*.sh` with its env-var contract. Any non-zero exit fails the
Stage-3 pipeline gate.

### Step 11.1 — DNS resolution (`dns-validation.sh`)

```bash
cd infoblox-ddi-book/azure-alz-automation/validation
export DDI_VIP="10.10.4.10"                                  # ddi_anycast_vip
export TEST_FQDN="app01.corp.example.com"                    # enterprise A record
export EXPECTED_IP="10.20.5.10"                              # its expected answer
export PRIVATELINK_FQDN="mystorage.privatelink.blob.core.windows.net"  # optional
bash dns-validation.sh
```

**Proves:** the DDI VIP answers an enterprise A record with `EXPECTED_IP`, and a
`privatelink.*` name resolves through the conditional-forward path to a **private**
(RFC1918) IP. **Fails when** no/wrong answer, or a privatelink name returns a public
IP (forward path bypassed). **Verify:** ends with `All DNS validation checks passed.`

### Step 11.2 — Discovery-sync freshness (`discovery-sync-check.sh`)

```bash
export DDI_API_FLAVOR="nios"                # grid default; "universal_ddi" for SaaS
export GRID_MASTER="<grid-master>"          # WAPI host (grid_master_ip)
export INFOBLOX_USERNAME="admin"            # from Key Vault
export INFOBLOX_PASSWORD="<from-key-vault>"
export STALE_THRESHOLD_MIN="1440"           # 24h
bash discovery-sync-check.sh
```

**Proves:** the vDiscovery task completed successfully and recently. **Fails when** a
task is `ERROR`/`WARNING`/`FAILED` or the last success is older than the threshold.
**Verify:** ends with `Discovery-sync freshness check passed.`

> **⚠ UNIVERSAL DDI callout.** Set `DDI_API_FLAVOR=universal_ddi` and provide
> `INFOBLOX_CSP_TOKEN` (from Key Vault); the check queries `csp.infoblox.com` cloud-
> discovery jobs. Only exercise this when `acknowledge_saas_boundary = true`.

### Step 11.3 — IPAM conflict (`ipam-conflict-check.sh`)

```bash
export GRID_MASTER="<grid-master>"
export INFOBLOX_USERNAME="admin"
export INFOBLOX_PASSWORD="<from-key-vault>"
export NETWORK_VIEW="default"
# optional: export CANDIDATE_NETWORK="10.10.4.0/27"   # test one CIDR for overlap
bash ipam-conflict-check.sh
```

**Proves:** no overlapping/duplicate `network` objects (server-side candidate query
or whole-view pairwise scan). **Fails when** any overlap is found. **Verify:** ends
with `IPAM conflict check passed.`

> **Troubleshooting — anycast not converging.** If `dns-validation.sh` intermittently
> fails, the anycast VIP may not be advertised from both members yet (Phase 7), or a
> member is unhealthy. Confirm both members answer directly:
> `dig +short @10.10.4.4 app01.corp.example.com` and `@10.10.4.5` (the two
> `dns_server_ips`) before blaming the VIP.

---

## Phase 12 — Wire into GitOps

Both pipelines (`pipelines/github-actions-alz-ddi.yml`,
`pipelines/azure-pipelines-alz-ddi.yml`) run the same three stages —
**ALZ (read Stage-1) → DDI (Stage-2 apply) → Validate (Stage-3)** — with **OIDC /
workload-identity federation** and **no stored client secret**.

### Step 12.1 — Create the workload identity + federated credential (GitHub)

```bash
# App registration used by the pipeline (identifier, not a secret).
az ad app create --display-name "alz-ddi-oidc"
export APP_ID="$(az ad app list --display-name alz-ddi-oidc --query '[0].appId' -o tsv)"
az ad sp create --id "$APP_ID"

# Federated credential trusting the repo/environment (no secret to store).
az ad app federated-credential create --id "$APP_ID" --parameters '{
  "name": "alz-ddi-prod",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:<org>/<repo>:environment:prod",
  "audiences": ["api://AzureADTokenExchange"]
}'
```

Grant the app least-privilege RBAC on the deploy scope (create the DDI subnet/
resources; read Stage-1 state storage) — this is a **separate, more-privileged**
identity than the discovery `ddi-disco-mi`.

**Verify:**
`az ad app federated-credential list --id "$APP_ID" -o table` shows the
`repo:<org>/<repo>:environment:prod` subject.

### Step 12.2 — Store non-secret identifiers & wire variables

Set repo/environment **secrets** `AZURE_CLIENT_ID` (=`$APP_ID`), `AZURE_TENANT_ID`,
`AZURE_SUBSCRIPTION_ID` (identifiers — the token is fetched via OIDC), plus vars
`TFSTATE_RG/SA/CONTAINER`, `KEY_VAULT_NAME`/`KEY_VAULT_ID`, and the DNS test inputs.
The job sets `permissions: id-token: write`; `ARM_USE_OIDC=true` tells the `azurerm`
provider and backend to auth via OIDC. Infoblox WAPI creds come from Key Vault
(`infoblox-wapi-username`/`infoblox-wapi-password`) at run time.

> **Azure DevOps:** create an **Azure Resource Manager service connection** using
> **"Workload Identity federation (automatic)"** named `sc-alz-ddi-wif`, and a
> Key-Vault-linked variable group `alz-ddi-secrets`.

### Step 12.3 — The boundary gate & promotion flow

Both pipelines carry `DEPLOYMENT_MODEL` (`grid`) and `ACKNOWLEDGE_SAAS_BOUNDARY`
(`false`). A gate step **hard-fails before init** if
`deployment_model = universal_ddi` and the ack is not `true` — so the SaaS path is
never even planned without a review (the Terraform/Bicep guards enforce it again).

Promotion: **PR → plan-only** (validate skipped); **dev sandbox →** `workflow_dispatch`
with `apply=true` + full validation; **test →** same with environment approval;
**prod →** required reviewers / approval checks gate entry. Each env uses a distinct
state key `ddi-<env>.tfstate`.

**Verify:** open a PR touching `terraform/**` — the `ddi` job runs `plan` only and
`validate` is skipped; merge to `main` (or dispatch `apply=true`) runs `apply` then
the three validation scripts.

> **Troubleshooting — boundary guard tripping in CI.** A red "Enforce SaaS boundary
> acknowledgement" step means `DEPLOYMENT_MODEL=universal_ddi` with
> `ACKNOWLEDGE_SAAS_BOUNDARY!=true`. This is intended — complete the authorization
> review and set the ack, or switch back to `grid`.

---

## Phase 13 — Day-2 & rollback

- **Upgrades.** Patch NIOS/NIOS-X on the vendor cadence; in a Grid, **upgrade the
  on-prem Grid Master before the Azure members**. Universal DDI scales by adding
  NIOS-X hosts behind the same service (raise `member_count`, re-apply).
- **GMC failover game-day.** Exercise Grid Master Candidate promotion; confirm the
  anycast VIP keeps answering when one member is stopped/deallocated:
  `az vm deallocate -g "$HUB_RG" -n ddi-vnios-z1` then re-run `dns-validation.sh`
  against the VIP. Restart with `az vm start`.
- **Drift detection.** A scheduled pipeline re-runs `terraform plan`; any non-empty
  plan is drift (a hand-made subnet, an edited NSG rule, a forwarder changed in the
  Grid UI) and raises a reconcile PR. Because Git is the source of record,
  remediation is "revert to desired state."
- **Secret rotation.** Rotate the admin password / temp license in Key Vault after
  first Grid setup. Note `grid.tf`/`universal_ddi.tf` set
  `lifecycle { ignore_changes = [custom_data] }`, so a Key Vault rotation does **not**
  silently recreate running members — re-bootstrap is a deliberate action.
- **Teardown cautions.** `terraform destroy` will remove the members, the
  `ddi-subnet`, the `ddi-nsg`, and `ddi-disco-mi`. **Before destroying:** revert any
  spoke `dns_servers` you pointed at the VIP (Phase 9.2) or those spokes lose
  resolution; drain the members from the Grid first so the GM does not flag missing
  members; and confirm no workload still depends on the anycast VIP. Destroy is
  scoped to Stage-2 only — it must **never** touch Stage-1 hub/identity resources.

---

## End-to-end validation checklist

Run top-to-bottom after Phase 11; every item should pass before calling the layer
production-ready.

- [ ] `terraform output` shows `ddi_subnet_id`, `dns_server_ips`, `ddi_anycast_vip`,
      `grid_master_ip` (grid), `discovery_identity_id`.
- [ ] Members `ddi-vnios-z1` / `ddi-vnios-z2` are in **different Availability Zones**
      and Grid-joined (or NIOS-X hosts enrolled to the Portal).
- [ ] `ddi-nsg` carries exactly the contract ports; no source is `0.0.0.0/0`;
      `Deny-All-In` / `Deny-All-Out` at priority 4096 present.
- [ ] `ddi-disco-mi` holds `Reader` on each discovered subscription and **nothing**
      broader (no `Owner`, no subscription `Contributor`).
- [ ] Key Vault holds the admin password, temp license, grid shared secret (and Portal
      join token for uddi) — none in Terraform state as plaintext.
- [ ] `dns-validation.sh` passes (enterprise A + privatelink forward path).
- [ ] `discovery-sync-check.sh` passes (job fresh, not errored).
- [ ] `ipam-conflict-check.sh` passes (no overlapping CIDRs).
- [ ] Failover: deallocating one member leaves the anycast VIP answering.
- [ ] Pipeline: PR = plan-only; merge/apply = apply + validate; prod behind approval.
- [ ] `universal_ddi` selected? — `acknowledge_saas_boundary = true`, the authorization
      review is on file, and outbound 443 to `csp.infoblox.com` is documented.

---

## Appendix A — Variable Worksheets (fill-in forms)

Copy each block, replace every `____` (and any `REPLACE_ME…`) with your value, and
keep the rest. Fields marked **REQUIRED** have no default — the plan/deploy fails
without them. The trailing comment gives the **source** of each value:

- **you choose** — a design decision (region, CIDRs, names)
- **Stage-1 output** — comes from the ALZ Accelerator (Phase 2)
- **generated** — a command produces it (`az …`) or a Stage-2 output does (Phase 6)
- **existing** — an already-provisioned resource (e.g. your Key Vault)

### A.1 Terraform — `terraform/terraform.tfvars`

```hcl
# ---- REQUIRED (no default) ----
location                  = "____"   # you choose — Azure region, .com (e.g. eastus)
hub_resource_group_name   = "____"   # Stage-1 output: hub_resource_group_name
hub_vnet_id               = "____"   # Stage-1 output: hub_vnet_id (/subscriptions/.../virtualNetworks/<name>)
ddi_subnet_address_prefix = "____"   # you choose — from the IPAM plan (e.g. 10.100.8.0/26)
key_vault_id              = "____"   # existing — /subscriptions/.../vaults/<kv>
vnios_vm_sku              = "____"   # you choose — per NIOS version/region (+ vCPU quota)
vnios_image = {                      # generated — az vm image list --publisher infoblox --all -o table
  publisher = "infoblox"
  offer     = "____"
  sku       = "____"
  version   = "latest"               # or pin a build
  # plan_name = "____"               # only if the Marketplace plan name differs from sku
}
mgmt_source_cidrs = ["____"]         # you choose — jumpbox/bastion/mgmt CIDRs (NEVER 0.0.0.0/0)
dns_client_cidrs  = ["____"]         # you choose — spoke + on-prem CIDRs allowed to query DNS (53)

# ---- OPTIONAL (defaults shown — change as needed) ----
name_prefix               = "ddi"
environment               = "prod"          # dev | test | prod
deployment_model          = "grid"          # grid | universal_ddi
acknowledge_saas_boundary = false           # MUST be true if deployment_model = "universal_ddi"
compliance_profile        = "gcc-moderate"
member_count              = 2               # >= 2 for HA
availability_zones        = ["1", "2"]
discovery_identity_type   = "user_assigned_mi"   # or "service_principal"
tags                      = {}

# NSG / networking
monitoring_source_cidrs       = []          # REQUIRED only if enable_snmp = true
grid_peer_cidrs               = ["____"]    # grid only — on-prem GM subnet + DDI subnet (1194/udp, 2114/tcp)
enable_ssh                    = false
enable_dhcp                   = false
enable_snmp                   = false
enable_accelerated_networking = true

# DNS integration
private_resolver_inbound_ip   = null        # Stage-1/existing — Private Resolver inbound IP (null = skip forwarders)
azure_service_forward_domains = ["privatelink.blob.core.windows.net", "azure.com"]
ddi_anycast_vip               = null        # set once you own the anycast VIP
enable_spoke_dns_write        = false       # true needs Network Contributor on spokes
spoke_vnet_ids                = []          # spokes to point at the DDI VIP

# Discovery scoping
discovered_subscription_ids          = ["____"]  # subscriptions to grant Reader for discovery
enable_record_write                  = false     # true grants Private DNS Zone Contributor
private_dns_zone_rg_ids              = []        # RG IDs of Private DNS zones (only if enable_record_write)
existing_service_principal_object_id = null      # only if discovery_identity_type = "service_principal"

# Key Vault secret NAMES (defaults usually fine; the VALUES go into Key Vault — see A.3)
admin_password_secret_name  = "ddi-vnios-admin-password"
temp_license_secret_name    = "ddi-vnios-temp-license"
grid_shared_secret_name     = "ddi-grid-shared-secret"
saas_join_token_secret_name = "ddi-uddi-join-token"

# Grid join (deployment_model = "grid")
grid_name       = "Infoblox"
grid_master_vip = "____"                    # on-prem GM VIP (null only for a lab where the first member IS the GM)

# Universal DDI (deployment_model = "universal_ddi")
infoblox_portal_url = "https://csp.infoblox.com"

# Marketplace
accept_marketplace_agreement = true
admin_username               = "azinfoblox"
```

### A.2 Bicep — `bicep/main.bicepparam`

Same variable names as A.1. Fill the required params; the rest mirror the tfvars
defaults. Note two Bicep secret-name defaults differ from Terraform's — set them
explicitly to match your Key Vault (A.3):

```bicep
param location                  = '____'   // REQUIRED — you choose
param hub_resource_group_name   = '____'   // REQUIRED — Stage-1 output
param hub_vnet_id               = '____'   // REQUIRED — Stage-1 output
param ddi_subnet_address_prefix = '____'   // REQUIRED — you choose
param key_vault_id              = '____'   // REQUIRED — existing
param vnios_vm_sku              = '____'   // REQUIRED — you choose
param vnios_image = { publisher: 'infoblox', offer: '____', sku: '____', version: 'latest' }  // generated
param deployment_model          = 'grid'        // grid | universal_ddi
param acknowledge_saas_boundary = false         // true required for universal_ddi
param member_count              = 2
param availability_zones        = [ '1', '2' ]
// secret names — align with the Key Vault you populate in A.3
param admin_password_secret_name = 'ddi-admin-password'
param grid_shared_secret_name    = 'ddi-grid-shared-secret'
param temp_license_secret_name   = 'ddi-temp-license'
```

### A.3 Key Vault secrets (the values referenced by A.1/A.2)

| Secret (default name) | Content to store | Source | Applies to |
|---|---|---|---|
| `ddi-vnios-admin-password` | vNIOS `admin` password to set at first boot | you choose (strong) | both |
| `ddi-vnios-temp-license` | temp license string, e.g. `vnios dns dhcp grid enterprise` | Infoblox licensing | both |
| `ddi-grid-shared-secret` | Grid shared secret used to join members | your Grid config | `grid` |
| `ddi-uddi-join-token` | Infoblox Portal (CSP) join token | Infoblox Portal | `universal_ddi` |

```bash
KV=____   # your Key Vault NAME (not the resource ID)
az keyvault secret set --vault-name "$KV" --name ddi-vnios-admin-password --value '____'
az keyvault secret set --vault-name "$KV" --name ddi-vnios-temp-license   --value '____'
az keyvault secret set --vault-name "$KV" --name ddi-grid-shared-secret   --value '____'   # grid
az keyvault secret set --vault-name "$KV" --name ddi-uddi-join-token      --value '____'   # universal_ddi only
```

### A.4 Validation scripts — environment forms

**`validation/dns-validation.sh`**

```bash
export DDI_VIP="____"                 # REQUIRED — anycast VIP or a member IP (Stage-2 output ddi_anycast_vip)
export TEST_FQDN="____"               # REQUIRED — an authoritative A record (e.g. host.corp.example)
export EXPECTED_IP="____"             # REQUIRED — the IP TEST_FQDN must resolve to
export DNS_PORT="53"                  # default 53
export DNS_TIMEOUT="5"                # default 5 (seconds)
export RESOLVER="____"                # optional — override resolver (default: DDI_VIP)
export PRIVATELINK_FQDN="____"        # optional — e.g. <acct>.privatelink.blob.core.windows.net
export PRIVATELINK_EXPECTED_IP="____" # optional — expected private IP for the privatelink name
```

**`validation/discovery-sync-check.sh`**

```bash
export DDI_API_FLAVOR="nios"          # nios | universal_ddi (default nios)
export STALE_THRESHOLD_MIN="1440"     # default 1440 (24h)
# --- NIOS (deployment_model = grid) ---
export GRID_MASTER="____"             # REQUIRED (nios) — Grid Master host/IP
export INFOBLOX_USERNAME="____"       # REQUIRED (nios)
export INFOBLOX_PASSWORD="____"       # REQUIRED (nios) — inject from Key Vault / CI secret, not literal
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

### A.5 Pipeline — GitHub Actions (`pipelines/github-actions-alz-ddi.yml`)

Set under **Settings → Secrets and variables → Actions** (or a repo Environment).

**Secrets** (OIDC — no passwords stored):

| Secret | Value | Source |
|---|---|---|
| `AZURE_CLIENT_ID` | client ID of the federated app/MI | generated (Phase 12) |
| `AZURE_TENANT_ID` | your Entra tenant ID | you choose |
| `AZURE_SUBSCRIPTION_ID` | target subscription | you choose |

**Variables** (`vars.*`):

| Variable | Value | Source |
|---|---|---|
| `TFSTATE_RG` / `TFSTATE_SA` / `TFSTATE_CONTAINER` | Stage-2 Terraform remote-state backend | you create (Phase 1) |
| `ALZ_STATE_RG` / `ALZ_STATE_SA` / `ALZ_STATE_CONTAINER` / `ALZ_STATE_KEY` | Stage-1 state location | Stage-1 |
| `KEY_VAULT_ID` / `KEY_VAULT_NAME` | your Key Vault | existing |
| `DEPLOYMENT_MODEL` / `ACKNOWLEDGE_SAAS_BOUNDARY` | `grid` / `false` | you choose |
| `TEST_FQDN` / `EXPECTED_IP` / `PRIVATELINK_FQDN` | validation inputs (A.4) | you choose |
| `DDI_VIP` / `GRID_MASTER` | Stage-2 outputs | generated (Phase 6) |

### A.6 Pipeline — Azure DevOps (`pipelines/azure-pipelines-alz-ddi.yml`)

Set in a **variable group** (link a Key Vault for secrets) and pipeline variables:

| Variable | Value |
|---|---|
| `azureServiceConnection` | name of the workload-identity ARM service connection |
| `TFSTATE_RG` / `TFSTATE_SA` / `TFSTATE_CONTAINER` | Terraform backend |
| `ALZ_STATE_SA` / `ALZ_STATE_CONTAINER` | Stage-1 state location |
| `KEY_VAULT_ID` / `KEY_VAULT_NAME` | your Key Vault |
| `deploymentModel` / `acknowledgeSaasBoundary` | `grid` / `false` |
| `hub_vnet_id` / `hub_resource_group_name` | Stage-1 outputs |
| `DDI_VIP` / `GRID_MASTER` / `TEST_FQDN` / `EXPECTED_IP` / `PRIVATELINK_FQDN` | validation inputs |
| `tfVersion` / `tfWorkingDir` / `validationDir` | pipeline config |

> Never put `INFOBLOX_PASSWORD`, `INFOBLOX_CSP_TOKEN`, or the vNIOS admin password
> in plain pipeline variables — reference them from Key Vault (linked variable group
> / `AzureKeyVault@2`) so they are injected at run time only.

---

## Sources

- [Azure Landing Zones — repository (accelerator + docs)](https://github.com/Azure/Azure-Landing-Zones)
- [Azure Landing Zones — Terraform accelerator (starter modules)](https://github.com/Azure/alz-terraform-accelerator)
- [Azure Landing Zones Accelerators for Bicep and Terraform — GA announcement](https://techcommunity.microsoft.com/blog/azuretoolsblog/azure-landing-zones-accelerators-for-bicep-and-terraform-announcing-general-avai/4029866)
- [Microsoft — What is an Azure landing zone? (CAF)](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/landing-zone/)
- [Microsoft — Azure DNS Private Resolver overview](https://learn.microsoft.com/en-us/azure/dns/dns-private-resolver-overview)
- [Microsoft — Private Resolver endpoints and rulesets](https://learn.microsoft.com/en-us/azure/dns/private-resolver-endpoints-rulesets)
- [Microsoft — Resolve Azure and on-premises domains (hybrid DNS)](https://learn.microsoft.com/en-us/azure/dns/private-resolver-hybrid-dns)
- [Microsoft — Private Link and DNS integration at scale (CAF)](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/azure-best-practices/private-link-and-dns-integration-at-scale)
- [Microsoft — Configure a GitHub Actions workflow to authenticate with OIDC / azure/login](https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure-openid-connect)
- [Microsoft — Workload identity federation](https://learn.microsoft.com/en-us/entra/workload-id/workload-identity-federation)
- [Infoblox — `infobloxopen/infoblox` Terraform provider (Registry)](https://registry.terraform.io/providers/infobloxopen/infoblox/latest/docs)
- [Infoblox — terraform-provider-infoblox (GitHub)](https://github.com/infobloxopen/terraform-provider-infoblox)
- [Infoblox — Deploying vNIOS for Azure from the Marketplace](https://docs.infoblox.com/space/vniosazure/37486729/Deploying+vNIOS+for+Azure+from+the+Marketplace)
- [Infoblox — Firewall Requirements for Infoblox Cloud Services (NIOS-X / 443)](https://docs.infoblox.com/space/BloxOneInfrastructure/873660456/Firewall+Requirements+for+Infoblox+Cloud+Services)
- Module contract: [`_module-contract.md`](./_module-contract.md)
- Architecture guide: [`Azure-ALZ-Infoblox-DDI-Automation-Guide.md`](./Azure-ALZ-Infoblox-DDI-Automation-Guide.md)
- Deploy chapter (click/CLI mechanics): [`../01-azure.md`](../01-azure.md)
