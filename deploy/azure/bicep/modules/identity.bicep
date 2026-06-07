// User-assigned managed identity — the SaaS "governance principal".
// ACR pull, Key Vault read, and Storage access are granted to this identity
// by the respective modules. It is also the workload identity the
// multi-tenant app federates from to acquire per-tenant Graph / ARM tokens.
@description('Resource name prefix.')
param namePrefix string
param location string
param tags object

resource uami 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${namePrefix}-id'
  location: location
  tags: tags
}

output identityId string = uami.id
output principalId string = uami.properties.principalId
output clientId string = uami.properties.clientId
output name string = uami.name
