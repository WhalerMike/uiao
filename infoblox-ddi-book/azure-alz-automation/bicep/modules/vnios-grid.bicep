// =============================================================================
// modules/vnios-grid.bicep — vNIOS Grid members (deployment_model=grid)
// -----------------------------------------------------------------------------
// Deploys `member_count` vNIOS VMs spread across `availability_zones`, each with
// a NIC on the DDI subnet. The Grid control plane runs INSIDE the tenant / ATO
// boundary (boundary-clean, GCC-Moderate default).
//
// Bootstrap is via VM `customData` (cloud-init / vNIOS "#infoblox-config"), which
// carries the admin password, temp license (BYOL), and Grid-join parameters. The
// three secrets arrive as @secure() params sourced from Key Vault by main.bicep
// (`keyVault.getSecret(...)`), so nothing is hard-coded.
//
// !! HONEST CAVEAT !!
//  - `customData` is base64 and is STORED on the VM. Embedding secrets there is
//    inherent to unattended VM bootstrap; source them from Key Vault (as here) and
//    rotate the temp license / admin password after first Grid setup.
//  - The exact vNIOS cloud-init KEY SCHEMA is version-specific. The block below is
//    ILLUSTRATIVE. Confirm the keys (temp_license, remote_console_enabled, gridmaster,
//    default_admin_password, etc.) against your vNIOS version's deployment guide.
//    Marketplace vNIOS also requires a `plan` block + prior terms acceptance
//    (`az vm image terms accept`).
//  - Grid formation itself (join to GM, license apply, anycast VIP) completes via
//    the Infoblox WAPI/GM — see README "handoff to Infoblox API/Ansible".
// =============================================================================

@description('Resource-name prefix, e.g. "ddi".')
param name_prefix string

@description('Azure region.')
param location string

@description('Tags to apply.')
param tags object

@description('Number of vNIOS members (>=2 for HA).')
@minValue(1)
param member_count int

@description('Availability zones to spread members across, e.g. ["1","2","3"].')
param availability_zones array

@description('VM size — region/model-dependent, supplied by caller.')
param vnios_vm_sku string

@description('Marketplace image object: { publisher, offer, sku, version, plan? }. Caller-supplied; never invented here.')
param vnios_image object

@description('Resource ID of the DDI subnet the NICs attach to.')
param subnet_id string

@description('vNIOS admin password (from Key Vault).')
@secure()
param admin_password string

@description('Grid shared secret / join token (from Key Vault).')
@secure()
param grid_shared_secret string

@description('vNIOS temporary license string, BYOL (from Key Vault).')
@secure()
param temp_license string

// Detect whether the Marketplace image carries a `plan` (BYOL/PAYG images do).
var hasPlan = contains(vnios_image, 'plan')

// ---------------------------------------------------------------------------
// vNIOS bootstrap (cloud-init / #infoblox-config). ILLUSTRATIVE schema — verify
// keys per your vNIOS version. Built per-member because member 1 is treated as
// the Grid Master candidate here (adjust to your Grid design).
// ---------------------------------------------------------------------------
// Note: string() on @secure() params is unavoidable to materialise customData.
// This is why the secrets must come from Key Vault and be rotated post-setup.
resource nic 'Microsoft.Network/networkInterfaces@2023-11-01' = [for i in range(0, member_count): {
  name: '${name_prefix}-vnios-nic-${i + 1}'
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
    // vNIOS commonly needs IP forwarding for anycast/HA scenarios.
    enableIPForwarding: true
  }
}]

resource vnios 'Microsoft.Compute/virtualMachines@2023-09-01' = [for i in range(0, member_count): {
  name: '${name_prefix}-vnios-z${availability_zones[i % length(availability_zones)]}-${i + 1}'
  location: location
  tags: tags
  // Zone spread: member i -> availability_zones[i % zoneCount]
  zones: [ availability_zones[i % length(availability_zones)] ]
  // Marketplace BYOL/PAYG images require the matching plan block.
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
      computerName: '${name_prefix}-vnios-${i + 1}'
      adminUsername: 'admin' // vNIOS uses its own appliance auth; placeholder for Azure agent.
      adminPassword: admin_password
      // ---- vNIOS bootstrap payload ----
      // ILLUSTRATIVE #infoblox-config; confirm keys per vNIOS version docs.
      customData: base64('''#infoblox-config

temp_license: ${string(temp_license)}
remote_console_enabled: true
default_admin_password: ${string(admin_password)}
# Grid-join parameters (member ${i + 1}).
# Member 1 is treated as the Grid Master candidate; others join to it.
grid_master_candidate: ${i == 0}
grid_name: ${name_prefix}-grid
grid_shared_secret: ${string(grid_shared_secret)}
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
// Outputs — member NIC private IPs. The REAL DDI anycast VIP / Grid Master IP are
// assigned during Grid setup (Infoblox WAPI/GM), not here. `suggested_anycast_vip`
// and `grid_master_ip` echo member-1's NIC IP as a coherent stand-in until the
// Grid is formed — replace with the actual VIP via the API/Ansible handoff.
// ---------------------------------------------------------------------------
output member_private_ips array = [for i in range(0, member_count): nic[i].properties.ipConfigurations[0].properties.privateIPAddress]
output grid_master_ip string = nic[0].properties.ipConfigurations[0].properties.privateIPAddress
output suggested_anycast_vip string = nic[0].properties.ipConfigurations[0].properties.privateIPAddress
