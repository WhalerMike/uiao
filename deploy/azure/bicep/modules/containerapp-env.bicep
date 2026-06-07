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

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${namePrefix}-cae'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsCustomerId
        sharedKey: logAnalyticsSharedKey
      }
    }
    zoneRedundant: false
  }
}

output environmentId string = environment.id
output environmentName string = environment.name
