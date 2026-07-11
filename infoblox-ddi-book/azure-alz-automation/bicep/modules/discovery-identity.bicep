// =============================================================================
// modules/discovery-identity.bicep — least-privilege discovery identity (§5)
// -----------------------------------------------------------------------------
// The identity Infoblox uses to discover Azure IPAM (VNets/subnets/NICs/tags) and,
// optionally, to write records into Azure Private DNS and dns_servers onto spokes.
//
// PREFERRED: user-assigned managed identity (discovery_identity_type=user_assigned_mi).
// FALLBACK : service_principal — an app registration / SP cannot be created in
//            Bicep (that is a Microsoft Entra ID / Graph operation), so this module
//            takes its principal ID as input and only wires the role assignments.
//            Create the SP with `az ad sp create-for-rbac` (or Terraform azuread).
//
// Role assignments (§5, scope = the subscriptions/RGs being discovered):
//   Reader                       -> discovered subscription(s)   [always]
//   Private DNS Zone Contributor -> RG(s) holding private zones  [record-write, opt-in]
//   Network Contributor          -> spoke VNet(s)                [spoke-write, opt-in]
// NO Owner, NO Contributor at subscription scope.
//
// SCOPE LIMITATION (honest): this module runs at RESOURCE GROUP scope (deployed by
// main.bicep into the hub RG). Bicep cannot WIDEN a module from RG scope up to
// SUBSCRIPTION scope, so the subscription-level **Reader** grant is emitted as a
// ready-to-run snippet (see README "Reader at subscription scope") rather than
// applied here. The record-write and spoke-write grants ARE applied here via the
// role-assignment helper (RG->RG module scope, which IS supported).
// =============================================================================

targetScope = 'resourceGroup'

@description('Resource-name prefix, e.g. "ddi".')
param name_prefix string

@description('Azure region.')
param location string

@description('Tags to apply.')
param tags object

@description('user_assigned_mi (create a UAMI here) | service_principal (pass sp_principal_id).')
@allowed([ 'user_assigned_mi', 'service_principal' ])
param discovery_identity_type string = 'user_assigned_mi'

@description('Object ID of a pre-created service principal (required only when discovery_identity_type=service_principal).')
param sp_principal_id string = ''

// ---- record-write (Private DNS Zone Contributor) — opt-in ----
@description('Grant Private DNS Zone Contributor so Infoblox can write records into Azure Private DNS.')
param enable_record_write bool = false

@description('Subscription ID holding the private DNS zones (for the record-write grant).')
param private_dns_zone_subscription_id string = ''

@description('Resource group holding the private DNS zones (for the record-write grant).')
param private_dns_zone_resource_group string = ''

// ---- spoke-write (Network Contributor) — opt-in ----
@description('Grant Network Contributor on spokes so the module can set dns_servers on them.')
param manage_spoke_dns bool = false

@description('Spoke VNet resource IDs — Network Contributor is granted per VNet (narrow scope).')
param spoke_vnet_ids array = []

// ---------------------------------------------------------------------------
// Built-in role definition GUIDs (stable, well-known).
// ---------------------------------------------------------------------------
var roleReader = 'acdd72a7-3385-48ef-bd42-f606fba81ae7'
var rolePrivateDnsZoneContributor = 'b12aa53e-6015-4669-85d0-8515ebb3ae7f'
var roleNetworkContributor = '4d97b98b-1d4f-11e3-a3e1-000c298c8e0b'

// ---------------------------------------------------------------------------
// User-assigned managed identity (preferred path).
// ---------------------------------------------------------------------------
resource uami 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = if (discovery_identity_type == 'user_assigned_mi') {
  name: '${name_prefix}-disco-mi'
  location: location
  tags: tags
}

// Effective principal ID: UAMI principal, or the supplied SP object ID.
var discoveryPrincipalId = discovery_identity_type == 'user_assigned_mi' ? uami.properties.principalId : sp_principal_id

// Effective identity resource ID (UAMI id, or the SP object id as an opaque handle).
var discoveryIdentityId = discovery_identity_type == 'user_assigned_mi' ? uami.id : sp_principal_id

// ---------------------------------------------------------------------------
// record-write: Private DNS Zone Contributor on the private-zone RG (opt-in).
// Cross-RG module scope (RG -> RG) is supported.
// ---------------------------------------------------------------------------
module recordWrite 'role-assignment.bicep' = if (enable_record_write && !empty(private_dns_zone_resource_group)) {
  name: '${name_prefix}-ra-privatedns'
  scope: resourceGroup(private_dns_zone_subscription_id, private_dns_zone_resource_group)
  params: {
    principal_id: discoveryPrincipalId
    role_definition_guid: rolePrivateDnsZoneContributor
    scope_type: 'resourceGroup'
  }
}

// ---------------------------------------------------------------------------
// spoke-write: Network Contributor per spoke VNet (opt-in), narrowed to the VNet.
// Each spoke ID is parsed into subscription / RG / name and the helper is deployed
// into that spoke's RG, assigning the role at the VNet scope.
// ---------------------------------------------------------------------------
module spokeWrite 'role-assignment.bicep' = [for spokeId in spoke_vnet_ids: if (manage_spoke_dns) {
  name: 'ra-spoke-${uniqueString(spokeId)}'
  scope: resourceGroup(split(spokeId, '/')[2], split(spokeId, '/')[4])
  params: {
    principal_id: discoveryPrincipalId
    role_definition_guid: roleNetworkContributor
    scope_type: 'virtualNetwork'
    target_vnet_name: last(split(spokeId, '/'))
  }
}]

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------
output discovery_identity_id string = discoveryIdentityId
output discovery_principal_id string = discoveryPrincipalId
@description('Client ID for UAMI (empty for the SP path). Use it in the Infoblox Azure discovery config.')
output discovery_client_id string = discovery_identity_type == 'user_assigned_mi' ? uami.properties.clientId : ''
@description('Reminder: grant Reader at subscription scope out-of-band (see README).')
output reader_role_guid string = roleReader
