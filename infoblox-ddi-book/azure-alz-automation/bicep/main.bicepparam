// =============================================================================
// main.bicepparam — EXAMPLE parameters (deployment_model = 'grid', commercial)
// -----------------------------------------------------------------------------
// Deploy:
//   az deployment group create \
//     --resource-group <hub_resource_group_name> \
//     --template-file main.bicep \
//     --parameters main.bicepparam
//
// The Marketplace image and VM SKU below are PLACEHOLDERS (REPLACE_ME). Never
// treat them as verified — pull real values with:
//   az vm image list --publisher infoblox --all -o table
//   az vm image terms accept --urn <publisher:offer:sku:version>
// and size per the vNIOS-on-Azure sizing guidance for your model/region.
// =============================================================================

using './main.bicep'

param name_prefix = 'ddi'
param location = 'eastus'
param environment = 'prod'

// --- Boundary: grid stays inside the ATO boundary; SaaS ack not required. ---
param deployment_model = 'grid'
param acknowledge_saas_boundary = false
param compliance_profile = 'gcc-moderate'

// --- Stage-1 (ALZ Accelerator) hub outputs feed in here. ---
param hub_resource_group_name = 'rg-connectivity-hub'
param hub_vnet_id = '/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-connectivity-hub/providers/Microsoft.Network/virtualNetworks/vnet-hub-eastus'

// --- Dedicated DDI subnet created inside the hub VNet. ---
param ddi_subnet_address_prefix = '10.100.8.0/26'

// --- Members / HA spread. ---
param member_count = 2
param availability_zones = [ '1', '2' ]

// --- VM sizing + image: REPLACE_ME with verified values. ---
param vnios_vm_sku = 'REPLACE_ME_Standard_Dxs_v5'
param vnios_image = {
  publisher: 'infoblox'
  offer: 'REPLACE_ME_infoblox-vnios'
  sku: 'REPLACE_ME_byol_or_payg_sku'
  version: 'REPLACE_ME_exact_version'
  // BYOL/PAYG Marketplace images require a plan block (must match the image).
  plan: {
    name: 'REPLACE_ME_plan_name'
    publisher: 'infoblox'
    product: 'REPLACE_ME_plan_product'
  }
}

// --- Existing Key Vault + secret names (values live in Key Vault, not here). ---
param key_vault_id = '/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-connectivity-hub/providers/Microsoft.KeyVault/vaults/kv-ddi-hub'
param admin_password_secret_name = 'ddi-admin-password'
param grid_shared_secret_name = 'ddi-grid-shared-secret'
param temp_license_secret_name = 'ddi-temp-license'

// --- Discovery identity. ---
param discovery_identity_type = 'user_assigned_mi'

// --- NSG source scoping (never 0.0.0.0/0). ---
param dns_client_prefixes = [ '10.0.0.0/8' ]
param mgmt_source_prefix = '10.100.0.0/24'
param monitoring_source_prefix = '10.100.1.0/24'
param grid_peer_prefixes = [ '10.100.8.0/26' ]
param enable_dhcp = false
param enable_snmp = false

// --- Optional spoke DNS wiring (Network Contributor granted only when set). ---
param spoke_vnet_ids = []

// --- Extra tags merged with module-managed tags. ---
param tags = {
  costCenter: 'network-core'
  owner: 'ddi-platform-team'
}
