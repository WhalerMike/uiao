// =============================================================================
// modules/role-assignment.bicep — single built-in role assignment helper
// -----------------------------------------------------------------------------
// Assigns ONE built-in role to a principal, at the scope this module is deployed
// into (set via the caller's `scope:` property). Two target shapes:
//   scope_type = 'resourceGroup'   -> assignment at the resource-group scope
//   scope_type = 'virtualNetwork'  -> assignment narrowed to a specific VNet
//
// The caller invokes this cross-RG / cross-subscription with, e.g.:
//   module x 'role-assignment.bicep' = { scope: resourceGroup(subId, rgName) ... }
// (resourceGroup -> resourceGroup is a supported Bicep module scope transition;
//  resourceGroup -> subscription is NOT — subscription-scoped Reader is handled
//  out-of-band, see discovery-identity.bicep + README.)
// =============================================================================

targetScope = 'resourceGroup'

@description('Object ID of the principal receiving the role.')
param principal_id string

@description('Principal type — ServicePrincipal covers managed identities and app SPs.')
@allowed([ 'ServicePrincipal', 'User', 'Group' ])
param principal_type string = 'ServicePrincipal'

@description('Built-in role definition GUID (not the full resource ID).')
param role_definition_guid string

@description('resourceGroup | virtualNetwork — narrows the assignment scope.')
@allowed([ 'resourceGroup', 'virtualNetwork' ])
param scope_type string = 'resourceGroup'

@description('VNet name when scope_type=virtualNetwork (must exist in this RG).')
param target_vnet_name string = ''

// Resolve the role definition ID within the TARGET subscription.
var roleDefId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', role_definition_guid)

// ---- RG-scoped assignment ----
resource rgAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (scope_type == 'resourceGroup') {
  name: guid(resourceGroup().id, principal_id, role_definition_guid)
  properties: {
    principalId: principal_id
    principalType: principal_type
    roleDefinitionId: roleDefId
  }
}

// ---- VNet-scoped assignment (narrower — one per VNet, no name collisions) ----
resource targetVnet 'Microsoft.Network/virtualNetworks@2023-11-01' existing = if (scope_type == 'virtualNetwork') {
  name: target_vnet_name
}

resource vnetAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (scope_type == 'virtualNetwork') {
  name: guid(targetVnet.id, principal_id, role_definition_guid)
  scope: targetVnet
  properties: {
    principalId: principal_id
    principalType: principal_type
    roleDefinitionId: roleDefId
  }
}
