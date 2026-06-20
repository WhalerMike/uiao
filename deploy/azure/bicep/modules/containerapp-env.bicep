// Azure Container Apps managed environment, wired to Log Analytics.
@description('Resource name prefix.')
param namePrefix string
param location string
param tags object

@description('Log Analytics workspace customer (workspace) ID.')
param logAnalyticsCustomerId string

@description('Log Analytics shared key.')
@secure()
param logAnalyticsSharedKey string

@description('Infrastructure subnet id for VNet injection. Empty = no VNet (ADR-119).')
param infrastructureSubnetId string = ''

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${namePrefix}-cae'
  location: location
  tags: tags
  // VNet-inject the environment when an infrastructure subnet is supplied;
  // union keeps the property absent otherwise.
  properties: union({
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsCustomerId
        sharedKey: logAnalyticsSharedKey
      }
    }
    zoneRedundant: false
  }, empty(infrastructureSubnetId) ? {} : {
    vnetConfiguration: {
      infrastructureSubnetId: infrastructureSubnetId
    }
  })
}

output environmentId string = environment.id
output environmentName string = environment.name
