// =============================================================================
// modules/universal-ddi.bicep — Universal DDI hosts (deployment_model=universal_ddi)
// -----------------------------------------------------------------------------
// Lightweight host VMs + a Microsoft.Resources/deploymentScripts (Azure CLI) that
// performs Infoblox Portal (SaaS) enrollment via REST. This is the CLEARLY-MARKED
// API HANDOFF: there is no Bicep-native Infoblox resource, so the enrollment /
// join call is done by the deployment script against the Portal API.
//
// !! BOUNDARY !! This path only runs because main.bicep's boundary guard already
// required acknowledge_saas_boundary=true. The Portal control plane is OUTSIDE the
// ATO boundary (outbound 443 to csp.infoblox.com). Keep the FedRAMP/authorization
// review current.
//
// The REST specifics (base URL, join-token exchange, payload shape) are Infoblox
// Portal API details that are ENVIRONMENT/VERSION-specific and are left as clearly
// labelled placeholders — do not treat them as verified API contracts.
// =============================================================================

@description('Resource-name prefix, e.g. "ddi".')
param name_prefix string

@description('Azure region.')
param location string

@description('Tags to apply.')
param tags object

@description('Number of UDDI hosts (>=2 for HA).')
@minValue(1)
param member_count int

@description('Availability zones to spread hosts across.')
param availability_zones array

@description('VM size — region/model-dependent, supplied by caller.')
param vnios_vm_sku string

@description('Marketplace image object for the UDDI host: { publisher, offer, sku, version, plan? }.')
param vnios_image object

@description('Resource ID of the DDI subnet the NICs attach to.')
param subnet_id string

@description('Host admin password (from Key Vault).')
@secure()
param admin_password string

@description('Resource ID of the discovery user-assigned identity — reused to run the enrollment script.')
param discovery_identity_id string

// ---- Portal enrollment placeholders (SaaS API handoff) ----
@description('Infoblox Portal (CSP) API base URL. Commercial SaaS endpoint — verify per your tenant.')
param portal_api_base_url string = 'https://csp.infoblox.com'

@description('Key Vault SECRET NAME (resolved by the script via managed identity) holding the Portal join token. The token is NOT passed in plaintext here.')
param portal_join_token_secret_uri string = ''

var hasPlan = contains(vnios_image, 'plan')

resource nic 'Microsoft.Network/networkInterfaces@2023-11-01' = [for i in range(0, member_count): {
  name: '${name_prefix}-uddi-nic-${i + 1}'
  location: location
  tags: tags
  properties: {
    ipConfigurations: [
      {
        name: 'ipconfig1'
        properties: {
          subnet: {
            id: subnet_id
          }
          privateIPAllocationMethod: 'Dynamic'
        }
      }
    ]
  }
}]

resource uddi 'Microsoft.Compute/virtualMachines@2023-09-01' = [for i in range(0, member_count): {
  name: '${name_prefix}-uddi-z${availability_zones[i % length(availability_zones)]}-${i + 1}'
  location: location
  tags: tags
  zones: [ availability_zones[i % length(availability_zones)] ]
  plan: hasPlan ? {
    name: vnios_image.plan.name
    publisher: vnios_image.plan.publisher
    product: vnios_image.plan.product
  } : null
  properties: {
    hardwareProfile: {
      vmSize: vnios_vm_sku
    }
    storageProfile: {
      imageReference: {
        publisher: vnios_image.publisher
        offer: vnios_image.offer
        sku: vnios_image.sku
        version: vnios_image.version
      }
      osDisk: {
        createOption: 'FromImage'
        managedDisk: {
          storageAccountType: 'Premium_LRS'
        }
      }
    }
    osProfile: {
      computerName: '${name_prefix}-uddi-${i + 1}'
      adminUsername: 'ddiadmin'
      adminPassword: admin_password
      // UDDI host bootstrap (illustrative — confirm per Infoblox UDDI host docs).
      customData: base64('''#cloud-config
# Infoblox Universal DDI host bootstrap (placeholder).
# The host registers to the Portal; the deploymentScript below performs the
# Portal-side enrollment/join via REST.
''')
    }
    networkProfile: {
      networkInterfaces: [
        {
          id: nic[i].id
        }
      ]
    }
  }
}]

// ---------------------------------------------------------------------------
// Portal enrollment — Azure CLI deploymentScript (the API handoff).
// Runs under the discovery user-assigned identity. Uses `az keyvault secret show`
// to fetch the join token at runtime (never passed in as a template parameter),
// then calls the Portal REST API to enroll the hosts.
// ---------------------------------------------------------------------------
resource enroll 'Microsoft.Resources/deploymentScripts@2023-08-01' = {
  name: '${name_prefix}-uddi-portal-enroll'
  location: location
  tags: tags
  kind: 'AzureCLI'
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${discovery_identity_id}': {}
    }
  }
  properties: {
    azCliVersion: '2.53.0'
    timeout: 'PT30M'
    retentionInterval: 'PT1H'
    cleanupPreference: 'OnSuccess'
    environmentVariables: [
      { name: 'PORTAL_API_BASE_URL', value: portal_api_base_url }
      { name: 'JOIN_TOKEN_SECRET_URI', value: portal_join_token_secret_uri }
      { name: 'GRID_NAME', value: '${name_prefix}-uddi' }
    ]
    // NOTE: REST calls below are PLACEHOLDERS for the Infoblox Portal enrollment
    // API. Confirm the real endpoints/payloads against Portal API docs. The script
    // is written to FAIL LOUDLY if the token or endpoint is missing, so an
    // incomplete config does not silently "succeed".
    scriptContent: '''
      set -euo pipefail
      echo "== Infoblox Portal enrollment (SaaS handoff) =="
      if [ -z "${JOIN_TOKEN_SECRET_URI:-}" ]; then
        echo "ERROR: JOIN_TOKEN_SECRET_URI not set. Supply the Key Vault secret URI for the Portal join token." >&2
        exit 1
      fi
      # Fetch the join token via managed identity (least privilege: KV secret get).
      JOIN_TOKEN="$(az keyvault secret show --id "${JOIN_TOKEN_SECRET_URI}" --query value -o tsv)"
      if [ -z "${JOIN_TOKEN}" ]; then
        echo "ERROR: empty join token from Key Vault." >&2
        exit 1
      fi
      echo "Enrolling grid '${GRID_NAME}' with Portal at ${PORTAL_API_BASE_URL} ..."
      # PLACEHOLDER REST call — replace path/payload with the verified Portal API.
      #   curl -sS -X POST "${PORTAL_API_BASE_URL}/api/uddi/v1/enroll" \
      #        -H "Authorization: Token ${JOIN_TOKEN}" \
      #        -H "Content-Type: application/json" \
      #        -d "{\"name\":\"${GRID_NAME}\"}"
      echo "PLACEHOLDER: Portal enrollment REST call not executed (see comments)."
      echo "{\"status\":\"handoff-required\",\"grid\":\"${GRID_NAME}\"}" > "${AZ_SCRIPTS_OUTPUT_PATH}"
    '''
  }
}

output host_private_ips array = [for i in range(0, member_count): nic[i].properties.ipConfigurations[0].properties.privateIPAddress]
output enrollment_status object = enroll.properties.outputs
