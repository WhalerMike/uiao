// =====================================================================
// UIAO Azure SaaS — root deployment (ADR-096)
// =====================================================================
// Resource-group-scoped. Stamps the shared SaaS platform:
//   Log Analytics + App Insights · Azure Container Registry ·
//   user-assigned managed identity · Key Vault · PostgreSQL Flexible
//   Server · Storage account · Container Apps environment · the SaaS
//   Container App (data plane + control plane, uiao.saas.asgi:app).
//
// The managed identity is the "behind-the-scenes" governance principal:
// it pulls from ACR, reads Key Vault secrets, and is the federated
// identity the multi-tenant app uses to acquire per-tenant Graph / ARM
// tokens once a customer grants admin consent.
//
// Deploy:
//   az deployment group create -g <rg> \
//     -f deploy/azure/bicep/main.bicep \
//     -p deploy/azure/bicep/main.bicepparam
// =====================================================================

targetScope = 'resourceGroup'

@description('Short workload name; used as a prefix for resource names.')
param workload string = 'uiao'

@description('Deployment environment (dev | test | prod).')
@allowed([ 'dev', 'test', 'prod' ])
param environmentName string = 'dev'

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Container image reference (registry/repo:tag). Set by CI after build/push.')
param containerImage string = ''

@description('Sovereign cloud the SaaS authenticates against.')
@allowed([ 'commercial', 'gcc-high', 'dod' ])
param cloud string = 'commercial'

@description('UIAO multi-tenant app registration (client) ID.')
param appClientId string = ''

@description('Publisher (home) tenant GUID that owns the control plane.')
param publisherTenantId string = subscription().tenantId

@description('API audience (Application ID URI) inbound tokens must carry.')
param apiAudience string = 'api://uiao'

@description('Minimum Container App replicas (0 = scale to zero).')
param minReplicas int = 1

@description('Maximum Container App replicas.')
param maxReplicas int = 10

@description('Deploy a VNet and run Postgres + the Container Apps env privately (ADR-119). Default off keeps the public-access deployment.')
param enablePrivateNetworking bool = false

var tags = {
  workload: workload
  environment: environmentName
  managedBy: 'bicep'
  component: 'uiao-saas'
  adr: 'adr-096'
}

var namePrefix = '${workload}-${environmentName}'

// ---------------------------------------------------------------------
// Observability
// ---------------------------------------------------------------------
module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring'
  params: {
    namePrefix: namePrefix
    location: location
    tags: tags
  }
}

// ---------------------------------------------------------------------
// Identity (user-assigned) — the governance principal
// ---------------------------------------------------------------------
module identity 'modules/identity.bicep' = {
  name: 'identity'
  params: {
    namePrefix: namePrefix
    location: location
    tags: tags
  }
}

// ---------------------------------------------------------------------
// Container registry
// ---------------------------------------------------------------------
module registry 'modules/registry.bicep' = {
  name: 'registry'
  params: {
    workload: workload
    environmentName: environmentName
    location: location
    tags: tags
    pullPrincipalId: identity.outputs.principalId
  }
}

// ---------------------------------------------------------------------
// Secrets store
// ---------------------------------------------------------------------
module keyvault 'modules/keyvault.bicep' = {
  name: 'keyvault'
  params: {
    workload: workload
    environmentName: environmentName
    location: location
    tags: tags
    readerPrincipalId: identity.outputs.principalId
  }
}

// ---------------------------------------------------------------------
// Private networking (ADR-119) — VNet + delegated subnets + private DNS.
// Deployed only when enablePrivateNetworking; the default keeps public access.
// ---------------------------------------------------------------------
module network 'modules/network.bicep' = if (enablePrivateNetworking) {
  name: 'network'
  params: {
    namePrefix: namePrefix
    location: location
    tags: tags
  }
}

// ---------------------------------------------------------------------
// Tenant registry + evidence state
// ---------------------------------------------------------------------
// Passwordless (ADR-116): the managed identity is bound as the server's Entra
// administrator; the app authenticates with an Entra token, no DB password.
// Private (ADR-119): VNet-integrated when enablePrivateNetworking.
module postgres 'modules/postgres.bicep' = {
  name: 'postgres'
  params: {
    namePrefix: namePrefix
    location: location
    tags: tags
    entraAdminObjectId: identity.outputs.principalId
    entraAdminName: identity.outputs.name
    delegatedSubnetId: enablePrivateNetworking ? network.outputs.postgresSubnetId : ''
    privateDnsZoneId: enablePrivateNetworking ? network.outputs.privateDnsZoneId : ''
  }
}

// ---------------------------------------------------------------------
// Evidence-bundle storage
// ---------------------------------------------------------------------
module storage 'modules/storage.bicep' = {
  name: 'storage'
  params: {
    workload: workload
    environmentName: environmentName
    location: location
    tags: tags
    contributorPrincipalId: identity.outputs.principalId
  }
}

// ---------------------------------------------------------------------
// Container Apps environment
// ---------------------------------------------------------------------
module containerEnv 'modules/containerapp-env.bicep' = {
  name: 'container-env'
  params: {
    namePrefix: namePrefix
    location: location
    tags: tags
    logAnalyticsCustomerId: monitoring.outputs.customerId
    logAnalyticsSharedKey: monitoring.outputs.sharedKey
    infrastructureSubnetId: enablePrivateNetworking ? network.outputs.infraSubnetId : ''
  }
}

// ---------------------------------------------------------------------
// The SaaS Container App
// ---------------------------------------------------------------------
module saasApp 'modules/containerapp.bicep' = {
  name: 'saas-app'
  params: {
    namePrefix: namePrefix
    location: location
    tags: tags
    environmentId: containerEnv.outputs.environmentId
    identityId: identity.outputs.identityId
    identityClientId: identity.outputs.clientId
    registryLoginServer: registry.outputs.loginServer
    containerImage: empty(containerImage) ? '${registry.outputs.loginServer}/uiao-saas:latest' : containerImage
    minReplicas: minReplicas
    maxReplicas: maxReplicas
    cloud: cloud
    appClientId: appClientId
    publisherTenantId: publisherTenantId
    apiAudience: apiAudience
    keyVaultUri: keyvault.outputs.vaultUri
    storageAccountUrl: storage.outputs.blobEndpoint
    // Passwordless DSN (no embedded secret) + Entra-auth toggle: the app
    // mints a short-lived Entra token as the connection password at runtime
    // (uiao.saas.pg_auth), connecting as the managed identity.
    databaseUrl: postgres.outputs.sqlAlchemyUrl
    databaseUseEntraAuth: true
    databaseEntraUser: postgres.outputs.entraAdminName
  }
}

// ---------------------------------------------------------------------
// Alert rules (App Insights)
// ---------------------------------------------------------------------
module alerts 'modules/alerts.bicep' = {
  name: 'alerts'
  params: {
    namePrefix: namePrefix
    location: location
    tags: tags
    appInsightsId: monitoring.outputs.appInsightsId
  }
}

output containerAppFqdn string = saasApp.outputs.fqdn
output managedIdentityClientId string = identity.outputs.clientId
output registryLoginServer string = registry.outputs.loginServer
output keyVaultUri string = keyvault.outputs.vaultUri
output postgresHost string = postgres.outputs.fqdn
