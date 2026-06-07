// Azure Container Registry + AcrPull role for the SaaS identity.
@description('Short workload name (registry names are alphanumeric only).')
param workload string
param environmentName string
param location string
param tags object

@description('Principal ID granted AcrPull (the SaaS managed identity).')
param pullPrincipalId string

var registryName = toLower('${workload}${environmentName}acr${uniqueString(resourceGroup().id)}')
// AcrPull built-in role.
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

resource acr 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: take(registryName, 50)
  location: location
  tags: tags
  sku: { name: 'Standard' }
  properties: {
    adminUserEnabled: false
    anonymousPullEnabled: false
  }
}

resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, pullPrincipalId, acrPullRoleId)
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: pullPrincipalId
    principalType: 'ServicePrincipal'
  }
}

output loginServer string = acr.properties.loginServer
output registryId string = acr.id
output registryName string = acr.name
