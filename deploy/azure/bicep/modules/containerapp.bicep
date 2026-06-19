// The UIAO SaaS Container App — data plane + control plane.
// Runs uiao.saas.asgi:app; pulls from ACR and reads secrets via the
// user-assigned managed identity. External ingress with platform TLS;
// /healthz backs the liveness probe; /readyz (registry reachable) backs
// the readiness probe (ADR-115).
@description('Resource name prefix.')
param namePrefix string
param location string
param tags object

param environmentId string
param identityId string
param identityClientId string
param registryLoginServer string
param containerImage string

param minReplicas int = 1
param maxReplicas int = 10

@allowed([ 'commercial', 'gcc-high', 'dod' ])
param cloud string = 'commercial'
param appClientId string = ''
param publisherTenantId string = ''
param apiAudience string = 'api://uiao'
param keyVaultUri string = ''
param storageAccountUrl string = ''

@description('SQLAlchemy async DSN (passwordless under Entra auth; stored as a secret).')
@secure()
param databaseUrl string

@description('Authenticate to Postgres with a Microsoft Entra token (passwordless, ADR-116).')
param databaseUseEntraAuth bool = false

@description('Entra principal name to connect to Postgres as (the managed identity name).')
param databaseEntraUser string = ''

@description('Container target/ingress port.')
param targetPort int = 8000

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-saas'
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${identityId}': {} }
  }
  properties: {
    managedEnvironmentId: environmentId
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: targetPort
        transport: 'auto'
        allowInsecure: false
        traffic: [ { latestRevision: true, weight: 100 } ]
      }
      registries: [
        {
          server: registryLoginServer
          identity: identityId
        }
      ]
      secrets: [
        {
          name: 'database-url'
          value: databaseUrl
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'uiao-saas'
          image: containerImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            { name: 'PORT', value: string(targetPort) }
            { name: 'UIAO_SAAS_CLOUD', value: cloud }
            { name: 'UIAO_SAAS_APP_CLIENT_ID', value: appClientId }
            { name: 'UIAO_SAAS_PUBLISHER_TENANT_ID', value: publisherTenantId }
            { name: 'UIAO_SAAS_API_AUDIENCE', value: apiAudience }
            { name: 'UIAO_SAAS_KEY_VAULT_URI', value: keyVaultUri }
            { name: 'UIAO_SAAS_STORAGE_ACCOUNT_URL', value: storageAccountUrl }
            { name: 'UIAO_SAAS_PROVISIONING_ENABLED', value: 'true' }
            { name: 'UIAO_SAAS_DATABASE_URL', secretRef: 'database-url' }
            { name: 'UIAO_SAAS_DATABASE_USE_ENTRA_AUTH', value: string(databaseUseEntraAuth) }
            { name: 'UIAO_SAAS_DATABASE_ENTRA_USER', value: databaseEntraUser }
            // The managed identity client id the app uses for Graph / ARM
            // token acquisition (DefaultAzureCredential / MSAL managed id), and
            // for the Postgres Entra token (uiao.saas.pg_auth).
            { name: 'AZURE_CLIENT_ID', value: identityClientId }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: { path: '/healthz', port: targetPort }
              initialDelaySeconds: 10
              periodSeconds: 30
            }
            {
              // /readyz confirms the tenant registry is reachable before the
              // revision is added to the ingress pool (ADR-115).
              type: 'Readiness'
              httpGet: { path: '/readyz', port: targetPort }
              initialDelaySeconds: 5
              periodSeconds: 15
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http-scale'
            http: { metadata: { concurrentRequests: '50' } }
          }
        ]
      }
    }
  }
}

output fqdn string = app.properties.configuration.ingress.fqdn
output appName string = app.name
