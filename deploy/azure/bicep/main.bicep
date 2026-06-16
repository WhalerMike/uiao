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

@description('PostgreSQL administrator login.')
param pgAdminLogin string = 'uiaoadmin'

@description('PostgreSQL administrator password.')
@secure()
param pgAdminPassword string

@description('Minimum Container App replicas (0 = scale to zero).')
param minReplicas int = 1

@description('Maximum Container App replicas.')
param maxReplicas int = 10

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
// Tenant registry + evidence state
// ---------------------------------------------------------------------
module postgres 'modules/postgres.bicep' = {
  name: 'postgres'
  params: {
    namePrefix: namePrefix
    location: location
    tags: tags
    adminLogin: pgAdminLogin
    adminPassword: pgAdminPassword
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
    // Compose the password-bearing DSN here (kept out of postgres outputs
    // so the secret never lands in deployment outputs). Passed to the
    // container module as a @secure() param → Container Apps secret.
    databaseUrl: 'postgresql+asyncpg://${pgAdminLogin}:${pgAdminPassword}@${postgres.outputs.fqdn}:5432/${postgres.outputs.databaseName}'
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
