// Private networking for the SaaS plane (ADR-119), deployed only when
// enablePrivateNetworking is set on the root template.
//
// A VNet with two delegated subnets — one for the Container Apps environment
// (VNet injection) and one for the VNet-integrated Postgres Flexible Server —
// plus the private DNS zone that resolves the integrated Postgres FQDN inside
// the VNet. With this in place the database has public network access disabled
// and is reachable only from the VNet.
@description('Resource name prefix.')
param namePrefix string
param location string
param tags object

@description('VNet address space.')
param vnetAddressPrefix string = '10.20.0.0/16'

@description('Subnet for the Container Apps environment (requires at least /23).')
param infraSubnetPrefix string = '10.20.0.0/23'

@description('Subnet delegated to the Postgres flexible server.')
param postgresSubnetPrefix string = '10.20.4.0/24'

resource vnet 'Microsoft.Network/virtualNetworks@2023-11-01' = {
  name: '${namePrefix}-vnet'
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [ vnetAddressPrefix ]
    }
    subnets: [
      {
        name: 'aca-infra'
        properties: {
          addressPrefix: infraSubnetPrefix
          delegations: [
            {
              name: 'aca-delegation'
              properties: {
                serviceName: 'Microsoft.App/environments'
              }
            }
          ]
        }
      }
      {
        name: 'postgres'
        properties: {
          addressPrefix: postgresSubnetPrefix
          delegations: [
            {
              name: 'pg-delegation'
              properties: {
                serviceName: 'Microsoft.DBforPostgreSQL/flexibleServers'
              }
            }
          ]
        }
      }
    ]
  }
}

// Private DNS zone for the VNet-integrated Postgres FQDN.
resource pgDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.postgres.database.azure.com'
  location: 'global'
  tags: tags
}

resource pgDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: pgDnsZone
  name: '${namePrefix}-pg-vnet-link'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: vnet.id
    }
  }
}

output infraSubnetId string = resourceId('Microsoft.Network/virtualNetworks/subnets', vnet.name, 'aca-infra')
output postgresSubnetId string = resourceId('Microsoft.Network/virtualNetworks/subnets', vnet.name, 'postgres')
output privateDnsZoneId string = pgDnsZone.id
output vnetId string = vnet.id
