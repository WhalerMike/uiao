// Azure Database for PostgreSQL Flexible Server — the tenant registry
// (saas_tenants) plus per-tenant evidence state. The SaaS data namespace
// isolates tenants (schema/row scoping); see uiao.saas.pg_repository.
@description('Resource name prefix.')
param namePrefix string
param location string
param tags object

@description('Administrator login.')
param adminLogin string

@description('Administrator password.')
@secure()
param adminPassword string

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
    administratorLogin: adminLogin
    administratorLoginPassword: adminPassword
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

// Allow Azure services (Container Apps egress) to reach the server. Tighten
// to a VNet / private endpoint for production hardening.
resource allowAzure 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2024-08-01' = {
  parent: server
  name: 'AllowAllAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

output fqdn string = server.properties.fullyQualifiedDomainName
output serverName string = server.name
output databaseName string = databaseName
// SQLAlchemy async URL consumed by uiao.saas (UIAO_SAAS_DATABASE_URL).
// Password is injected separately as a Container Apps secret, so it is not
// embedded here — the app composes the final DSN from env at runtime.
output sqlAlchemyUrl string = 'postgresql+asyncpg://${adminLogin}@${server.properties.fullyQualifiedDomainName}:5432/${databaseName}'
