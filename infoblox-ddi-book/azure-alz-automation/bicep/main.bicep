// =============================================================================
// main.bicep — Infoblox DDI extension for an Azure Landing Zone (Stage 2)
// -----------------------------------------------------------------------------
// Layers on top of the Microsoft ALZ Accelerator (Stage 1). Consumes the Stage-1
// hub-network outputs (hub_vnet_id, hub_resource_group_name, ...) and adds the
// DDI + DNS-security layer *inside the Connectivity hub*: a dedicated DDI subnet,
// an NSG, the vNIOS Grid (or Universal DDI host) members, and a least-privilege
// discovery identity.
//
// Parameter names, ports, IAM scopes, naming and outputs are held IDENTICAL to
// the Terraform module by the shared contract:  ../_module-contract.md
//
// SCOPE: deploy this at RESOURCE GROUP scope, into the Connectivity/hub resource
//        group that actually holds `hub_vnet_id` (so the DDI subnet can be created
//        as a child of the existing hub VNet).  Example:
//          az deployment group create \
//            --resource-group <hub_resource_group_name> \
//            --template-file main.bicep --parameters main.bicepparam
//
// STATUS: coherent STARTER SKELETON — not a certified production module. Pin your
//         own image/SKU, supply CIDRs, and test in a sandbox ALZ first.
// =============================================================================

targetScope = 'resourceGroup'

// ---------------------------------------------------------------------------
// §3 Canonical input variables (same names as the Terraform variables)
// ---------------------------------------------------------------------------

@description('Prefix for all resource names, e.g. "ddi" -> ddi-nsg, ddi-subnet, ddi-vnios-z1.')
param name_prefix string = 'ddi'

@description('Azure region (commercial `.com` cloud). Defaults to the hub RG location.')
param location string = resourceGroup().location

@description('Environment: dev | test | prod. Feeds tags + (optionally) sizing.')
@allowed([ 'dev', 'test', 'prod' ])
param environment string = 'prod'

@description('Control-plane model. grid = vNIOS Grid inside the ATO boundary (default, boundary-clean). universal_ddi = Infoblox Portal SaaS control plane OUTSIDE the boundary.')
@allowed([ 'grid', 'universal_ddi' ])
param deployment_model string = 'grid'

@description('MUST be true to allow deployment_model=universal_ddi. Default false hard-fails the deployment (see §1 / boundary guard below).')
param acknowledge_saas_boundary bool = false

@description('Compliance profile — drives tags + control mapping. GCC-Moderate on commercial Azure.')
param compliance_profile string = 'gcc-moderate'

@description('Stage-1 output: name of the Connectivity/hub resource group.')
param hub_resource_group_name string

@description('Stage-1 output: full resource ID of the hub VNet. This module adds the DDI subnet to it.')
param hub_vnet_id string

@description('Dedicated DDI subnet CIDR, created by this module inside the hub VNet, e.g. 10.100.8.0/26.')
param ddi_subnet_address_prefix string

@description('vNIOS members / UDDI hosts. >=2 for HA.')
@minValue(1)
param member_count int = 2

@description('Availability zones to spread members across, e.g. ["1","2","3"].')
param availability_zones array = [ '1', '2' ]

@description('Azure VM size for vNIOS/UDDI hosts. REGION/MODEL-DEPENDENT — do not hard-code; see the vNIOS-on-Azure sizing docs. e.g. Standard_D8s_v5.')
param vnios_vm_sku string

@description('Marketplace image for vNIOS (publisher/offer/sku/version + optional plan for BYOL/PAYG). NEVER invent versions — supply from `az vm image list --publisher infoblox` and accept terms first.')
param vnios_image object

@description('Resource ID of an EXISTING Key Vault holding secrets (admin pw, join token, temp license, discovery creds).')
param key_vault_id string

@description('Discovery identity model: user_assigned_mi (preferred) | service_principal.')
@allowed([ 'user_assigned_mi', 'service_principal' ])
param discovery_identity_type string = 'user_assigned_mi'

@description('Optional: spoke VNet resource IDs whose dns_servers should point at the DDI VIP. Grants Network Contributor when set (opt-in, §5).')
param spoke_vnet_ids array = []

@description('Free-form tags, merged with the module-managed tags (§6).')
param tags object = {}

// ---- Secure secret names (values are pulled from Key Vault, see main.bicepparam) ----
@description('Key Vault SECRET NAME for the vNIOS/UDDI admin password.')
param admin_password_secret_name string = 'ddi-admin-password'

@description('Key Vault SECRET NAME for the Grid shared secret / join token.')
param grid_shared_secret_name string = 'ddi-grid-shared-secret'

@description('Key Vault SECRET NAME for the vNIOS temporary license string (BYOL).')
param temp_license_secret_name string = 'ddi-temp-license'

// ---- NSG source scoping (§4 — never 0.0.0.0/0) ----
@description('Source prefixes allowed to query DNS (spokes / on-prem).')
param dns_client_prefixes array = [ '10.0.0.0/8' ]

@description('Source prefix for HTTPS Grid management (mgmt jump hosts). REQUIRED, never 0.0.0.0/0.')
param mgmt_source_prefix string

@description('Source prefix for SNMP monitoring collectors.')
param monitoring_source_prefix string = ''

@description('Grid peer prefixes (other Grid members / GM) for VPN 1194/udp + 2114/tcp. grid model only.')
param grid_peer_prefixes array = []

@description('Serve DHCP from vNIOS (67-68/udp). Off by default — Azure DHCP is platform-managed.')
param enable_dhcp bool = false

@description('Enable inbound SNMP (161/udp) from monitoring_source_prefix.')
param enable_snmp bool = false

// ---------------------------------------------------------------------------
// §6 Module-managed tags (merged with caller tags)
// ---------------------------------------------------------------------------
var moduleTags = union(tags, {
  workload: 'infoblox-ddi'
  layer: 'connectivity-ddi'
  compliance_profile: compliance_profile
  deployment_model: deployment_model
  managed_by: 'bicep'
  environment: environment
})

// ===========================================================================
// §1 SAAS BOUNDARY GUARD  (control-plane boundary rule — CRITICAL)
// ---------------------------------------------------------------------------
// deployment_model=universal_ddi routes the Infoblox Portal (SaaS) control plane
// OUTSIDE the tenant / ATO boundary (outbound 443 to the Portal). For a
// GCC-Moderate posture that requires a FedRAMP / authorization review, so we
// HARD-FAIL the deployment unless the operator has explicitly set
// acknowledge_saas_boundary=true.
//
// Implementation is an "assert-style trick" that works on STABLE Bicep with no
// experimental flags: the divisor becomes 0 only when the boundary is violated,
// and ARM aborts the whole deployment with a division-by-zero evaluation error.
// Because the divisor is derived from runtime params, Bicep does NOT constant-fold
// it at compile time (a literal `1/0` would fail to compile even when unused).
//
// The guard value is consumed while computing the subnet prefix (below), which
// forces ARM to evaluate it BEFORE creating any resource.
//
// Cleaner alternative when you enable the `assertions` experimental feature in
// bicepconfig.json (see the commented bicepconfig snippet in README.md):
//     assert saasBoundaryAcknowledged = !(deployment_model == 'universal_ddi' && !acknowledge_saas_boundary)
// ---------------------------------------------------------------------------
var saasBoundaryViolation = deployment_model == 'universal_ddi' && !acknowledge_saas_boundary

// Human-readable reason surfaced when the SaaS boundary guard trips.
var boundaryReviewMessage = 'DEPLOYMENT BLOCKED: deployment_model=universal_ddi routes the Infoblox Portal (SaaS) control plane OUTSIDE the ATO boundary (outbound 443). Set acknowledge_saas_boundary=true ONLY after completing the FedRAMP / authorization review. See _module-contract.md section 1.'

// divisor: 1 when allowed, 0 when the boundary is violated -> div-by-zero abort.
var boundaryGuardDivisor = saasBoundaryViolation ? 0 : 1
var boundaryGuardEvaluated = 1 / boundaryGuardDivisor

// The ternary below is a no-op on the value; its ONLY purpose is to consume
// boundaryGuardEvaluated so ARM evaluates the guard up-front (and so Bicep does
// not prune it). When allowed, the caller's prefix passes through unchanged.
var ddiSubnetPrefixGuarded = boundaryGuardEvaluated == 1 ? ddi_subnet_address_prefix : ddi_subnet_address_prefix

// ---------------------------------------------------------------------------
// Existing Stage-1 references
// ---------------------------------------------------------------------------
var hubVnetName = last(split(hub_vnet_id, '/'))

// The hub VNet lives in this deployment's resource group (see SCOPE note above).
resource hubVnet 'Microsoft.Network/virtualNetworks@2023-11-01' existing = {
  name: hubVnetName
}

// Existing Key Vault — used to source secrets into secure module params via getSecret().
var keyVaultName = last(split(key_vault_id, '/'))
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

// ---------------------------------------------------------------------------
// Naming (§6)
// ---------------------------------------------------------------------------
var ddiSubnetName = '${name_prefix}-subnet'

// ===========================================================================
// NSG (module) — §4 ports, conditional on deployment_model, default-deny
// ===========================================================================
module nsg 'modules/nsg.bicep' = {
  name: '${name_prefix}-nsg-deploy'
  params: {
    name_prefix: name_prefix
    location: location
    tags: moduleTags
    deployment_model: deployment_model
    dns_client_prefixes: dns_client_prefixes
    mgmt_source_prefix: mgmt_source_prefix
    monitoring_source_prefix: monitoring_source_prefix
    grid_peer_prefixes: grid_peer_prefixes
    enable_dhcp: enable_dhcp
    enable_snmp: enable_snmp
  }
}

// ===========================================================================
// DDI subnet — created inside the hub VNet, associated with the NSG
// ===========================================================================
// NOTE: a standalone child subnet is used here. If the hub VNet is managed by
// Stage-1 IaC that also enumerates subnets, coordinate ownership to avoid drift
// (see README "Stage-1 -> Stage-2 wiring").
resource ddiSubnet 'Microsoft.Network/virtualNetworks/subnets@2023-11-01' = {
  parent: hubVnet
  name: ddiSubnetName
  properties: {
    addressPrefix: ddiSubnetPrefixGuarded // guarded value (boundary check consumed here)
    networkSecurityGroup: {
      id: nsg.outputs.nsgId
    }
  }
}

// ===========================================================================
// Discovery identity (module) — §5 least-privilege Azure -> Infoblox sync
// ===========================================================================
module discovery 'modules/discovery-identity.bicep' = {
  name: '${name_prefix}-disco-deploy'
  params: {
    name_prefix: name_prefix
    location: location
    tags: moduleTags
    discovery_identity_type: discovery_identity_type
    // Record-write / spoke-write are OPT-IN (§5). Toggle + supply targets in params.
    spoke_vnet_ids: spoke_vnet_ids
  }
}

// ===========================================================================
// Control-plane members — grid vs universal_ddi selected by param
// ===========================================================================
module grid 'modules/vnios-grid.bicep' = if (deployment_model == 'grid') {
  name: '${name_prefix}-grid-deploy'
  params: {
    name_prefix: name_prefix
    location: location
    tags: moduleTags
    member_count: member_count
    availability_zones: availability_zones
    vnios_vm_sku: vnios_vm_sku
    vnios_image: vnios_image
    subnet_id: ddiSubnet.id
    // Secrets sourced from Key Vault at deploy time (never hard-coded).
    admin_password: keyVault.getSecret(admin_password_secret_name)
    grid_shared_secret: keyVault.getSecret(grid_shared_secret_name)
    temp_license: keyVault.getSecret(temp_license_secret_name)
  }
}

module universal 'modules/universal-ddi.bicep' = if (deployment_model == 'universal_ddi') {
  name: '${name_prefix}-uddi-deploy'
  params: {
    name_prefix: name_prefix
    location: location
    tags: moduleTags
    member_count: member_count
    availability_zones: availability_zones
    vnios_vm_sku: vnios_vm_sku
    vnios_image: vnios_image
    subnet_id: ddiSubnet.id
    admin_password: keyVault.getSecret(admin_password_secret_name)
    // Portal enrollment (SaaS handoff) — only reachable because the boundary guard
    // above already required acknowledge_saas_boundary=true to get here.
    discovery_identity_id: discovery.outputs.discovery_identity_id
  }
}

// ===========================================================================
// §7 Canonical outputs (same names as Terraform)
// ===========================================================================
// NOTE: ddi_anycast_vip / dns_server_ips / grid_master_ip are runtime facts of the
// Infoblox Grid (assigned during Grid setup), not raw Azure NIC IPs. This skeleton
// surfaces the member NIC private IPs as a stand-in; wire the real VIP once the
// Grid/anycast is configured via the Infoblox API/Ansible (see README handoff).
output ddi_subnet_id string = ddiSubnet.id
output dns_server_ips array = deployment_model == 'grid' ? grid.outputs.member_private_ips : universal.outputs.host_private_ips
output ddi_anycast_vip string = deployment_model == 'grid' ? grid.outputs.suggested_anycast_vip : ''
output grid_master_ip string = deployment_model == 'grid' ? grid.outputs.grid_master_ip : ''
output discovery_identity_id string = discovery.outputs.discovery_identity_id

@description('Echoes the boundary-guard reason (also enforced as a hard fail before any resource is created).')
output boundary_guard_note string = boundaryReviewMessage
