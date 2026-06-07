// Key Vault for per-tenant secrets (client secrets / certs) + the
// "Key Vault Secrets User" role for the SaaS identity (RBAC mode).
@description('Short workload name.')
param workload string
param environmentName string
param location string
param tags object

@description('Principal ID granted secret read (the SaaS managed identity).')
param readerPrincipalId string

var vaultName = take(toLower('${workload}${environmentName}kv${uniqueString(resourceGroup().id)}'), 24)
// "Key Vault Secrets User" built-in role.
var secretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'

resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: vaultName
  location: location
  tags: tags
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enablePurgeProtection: true
    publicNetworkAccess: 'Enabled'
  }
}

resource secretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(vault.id, readerPrincipalId, secretsUserRoleId)
  scope: vault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', secretsUserRoleId)
    principalId: readerPrincipalId
    principalType: 'ServicePrincipal'
  }
}

output vaultUri string = vault.properties.vaultUri
output vaultId string = vault.id
output vaultName string = vault.name
