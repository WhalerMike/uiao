// Storage account + Blob container for tenant-scoped evidence bundles,
// plus "Storage Blob Data Contributor" for the SaaS identity.
@description('Short workload name.')
param workload string
param environmentName string
param location string
param tags object

@description('Principal ID granted blob data contributor (SaaS identity).')
param contributorPrincipalId string

var accountName = take(toLower('${workload}${environmentName}st${uniqueString(resourceGroup().id)}'), 24)
// "Storage Blob Data Contributor" built-in role.
var blobContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'

resource account 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: accountName
  location: location
  tags: tags
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: account
  name: 'default'
}

resource evidenceContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'evidence'
  properties: { publicAccess: 'None' }
}

resource blobContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(account.id, contributorPrincipalId, blobContributorRoleId)
  scope: account
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', blobContributorRoleId)
    principalId: contributorPrincipalId
    principalType: 'ServicePrincipal'
  }
}

output accountName string = account.name
output blobEndpoint string = account.properties.primaryEndpoints.blob
