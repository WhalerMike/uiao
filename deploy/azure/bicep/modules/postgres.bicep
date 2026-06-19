// Azure Database for PostgreSQL Flexible Server — the tenant registry
// (saas_tenants) plus per-tenant evidence state. The SaaS data namespace
// isolates tenants (schema/row scoping); see uiao.saas.pg_repository.
//
// Authentication is **passwordless** (ADR-116): Microsoft Entra-only, with the
// SaaS managed identity bound as the server's Entra administrator. The app
// presents a short-lived Entra access token as the connection password
// (uiao.saas.pg_auth), so there is no long-lived database password anywhere in
// the deployment.
@description('Resource name prefix.')
param namePrefix string
param location string
param tags object

@description('Entra tenant the server authenticates against.')
param tenantId string = subscription().tenantId

@description('Object (principal) ID of the Entra administrator — the SaaS managed identity.')
param entraAdminObjectId string

@description('Display name of the Entra administrator principal (the connection username).')
param entraAdminName string

@description('Entra principal type of the administrator.')
@allowed([ 'ServicePrincipal', 'User', 'Group' ])
param entraAdminPrincipalType string = 'ServicePrincipal'

@description('Compute tier SKU.')
param skuName string = 'Standard_B1ms'

@description('Storage size (GB).')
param storageSizeGB int = 32

@description('Initial database name.')
param databaseName string = 'uiao'

@description('PostgreSQL major version.')
param postgresVersion string = '16'

var serverName = take(toLower('${namePrefix}-pg-${uniqueString(resourceGroup().id)}'), 63)

resource server 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: serverName
  location: location
  tags: tags
  sku: {
    name: skuName
    tier: 'Burstable'
  }
  properties: {
    version: postgresVersion
    // Passwordless: Entra-only authentication. With password auth disabled the
    // Entra administrator (bound below) is the only path in — no admin login or
    // password is provisioned.
    authConfig: {
      activeDirectoryAuth: 'Enabled'
      passwordAuth: 'Disabled'
      tenantId: tenantId
    }
    storage: { storageSizeGB: storageSizeGB }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: { mode: 'Disabled' }
    network: { publicNetworkAccess: 'Enabled' }
  }
}

resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: server
  name: databaseName
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// Bind the SaaS managed identity as the server's Entra administrator. This is
// the principal the app authenticates as (token-as-password). Entra admin
// writes cannot run concurrently with other server operations, so serialise
// after the database create.
resource entraAdmin 'Microsoft.DBforPostgreSQL/flexibleServers/administrators@2024-08-01' = {
  parent: server
  name: entraAdminObjectId
  properties: {
    principalType: entraAdminPrincipalType
    principalName: entraAdminName
    tenantId: tenantId
  }
  dependsOn: [ database ]
}

// Allow Azure services (Container Apps egress) to reach the server. Tighten
// to a VNet / private endpoint for production hardening (deferred follow-up).
resource allowAzure 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2024-08-01' = {
  parent: server
  name: 'AllowAllAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
  dependsOn: [ entraAdmin ]
}

output fqdn string = server.properties.fullyQualifiedDomainName
output serverName string = server.name
output databaseName string = databaseName
// The Entra principal name the app connects as (UIAO_SAAS_DATABASE_ENTRA_USER).
output entraAdminName string = entraAdminName
// Passwordless SQLAlchemy async URL — NO password. The app supplies a
// short-lived Entra token as the password at connect time
// (UIAO_SAAS_DATABASE_USE_ENTRA_AUTH=true; uiao.saas.pg_auth).
output sqlAlchemyUrl string = 'postgresql+asyncpg://${entraAdminName}@${server.properties.fullyQualifiedDomainName}:5432/${databaseName}'
