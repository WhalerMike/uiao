// =============================================================================
// modules/nsg.bicep — DDI subnet NSG + security rules (contract §4)
// -----------------------------------------------------------------------------
// Implements EXACTLY the port table in _module-contract.md §4:
//   - DNS 53 tcp+udp inbound            (always)
//   - DHCP 67-68 udp inbound            (only if enable_dhcp; Azure DHCP is
//                                        platform-managed, so OFF by default)
//   - Grid VPN 1194 udp in/out          (deployment_model=grid)
//   - Grid comms 2114 tcp in/out        (deployment_model=grid)
//   - NTP 123 udp outbound              (always)
//   - HTTPS mgmt 443 tcp inbound        (mgmt CIDR, always)
//   - Portal sync 443 tcp OUTBOUND      (deployment_model=universal_ddi only)
//   - SNMP 161 udp inbound              (optional, monitoring CIDR)
// Default-deny everything else. Mgmt/monitoring sources are scoped to explicit
// CIDR params — NEVER 0.0.0.0/0.
// =============================================================================

@description('Resource-name prefix, e.g. "ddi".')
param name_prefix string

@description('Azure region.')
param location string

@description('Tags to apply.')
param tags object

@description('grid | universal_ddi — toggles Grid-comms vs Portal-sync rules.')
@allowed([ 'grid', 'universal_ddi' ])
param deployment_model string

@description('Source prefixes allowed to query DNS (spokes / on-prem).')
param dns_client_prefixes array

@description('Source prefix for HTTPS Grid management. REQUIRED, never 0.0.0.0/0.')
param mgmt_source_prefix string

@description('Source prefix for SNMP monitoring (empty disables the SNMP source).')
param monitoring_source_prefix string = ''

@description('Grid peer prefixes (other members / GM) for 1194/udp + 2114/tcp.')
param grid_peer_prefixes array = []

@description('Serve DHCP from vNIOS (67-68/udp inbound).')
param enable_dhcp bool = false

@description('Enable inbound SNMP (161/udp).')
param enable_snmp bool = false

var isGrid = deployment_model == 'grid'
var isUniversal = deployment_model == 'universal_ddi'
var hasMonitoring = enable_snmp && !empty(monitoring_source_prefix)
var hasGridPeers = isGrid && !empty(grid_peer_prefixes)

// ---------------------------------------------------------------------------
// Rule set assembled by concatenating conditional fragments. Priorities are
// spaced by 10 within inbound (100+) and outbound (100+) ranges. Because a rule
// is either single-source or multi-source, we use sourceAddressPrefix or
// sourceAddressPrefixes accordingly.
// ---------------------------------------------------------------------------

// ---- INBOUND: DNS 53 (tcp + udp) — always ----
var ruleDnsTcp = {
  name: 'Allow-DNS-TCP-In'
  properties: {
    priority: 100
    direction: 'Inbound'
    access: 'Allow'
    protocol: 'Tcp'
    sourcePortRange: '*'
    destinationPortRange: '53'
    sourceAddressPrefixes: dns_client_prefixes
    destinationAddressPrefix: '*'
    description: 'DNS query (TCP) from spokes/on-prem.'
  }
}
var ruleDnsUdp = {
  name: 'Allow-DNS-UDP-In'
  properties: {
    priority: 110
    direction: 'Inbound'
    access: 'Allow'
    protocol: 'Udp'
    sourcePortRange: '*'
    destinationPortRange: '53'
    sourceAddressPrefixes: dns_client_prefixes
    destinationAddressPrefix: '*'
    description: 'DNS query (UDP) from spokes/on-prem.'
  }
}

// ---- INBOUND: HTTPS mgmt 443 — always, scoped to mgmt CIDR ----
var ruleMgmtHttps = {
  name: 'Allow-HTTPS-Mgmt-In'
  properties: {
    priority: 120
    direction: 'Inbound'
    access: 'Allow'
    protocol: 'Tcp'
    sourcePortRange: '*'
    destinationPortRange: '443'
    sourceAddressPrefix: mgmt_source_prefix
    destinationAddressPrefix: '*'
    description: 'Grid Manager / API HTTPS from the management CIDR only.'
  }
}

// ---- INBOUND: DHCP 67-68 udp — only if enabled ----
var ruleDhcp = enable_dhcp ? [ {
  name: 'Allow-DHCP-In'
  properties: {
    priority: 130
    direction: 'Inbound'
    access: 'Allow'
    protocol: 'Udp'
    sourcePortRange: '*'
    destinationPortRanges: [ '67', '68' ]
    sourceAddressPrefixes: dns_client_prefixes
    destinationAddressPrefix: '*'
    description: 'DHCP served by vNIOS (opt-in; Azure DHCP is platform-managed).'
  }
} ] : []

// ---- INBOUND: Grid VPN 1194 udp + Grid comms 2114 tcp — grid only ----
var ruleGridVpnIn = hasGridPeers ? [ {
  name: 'Allow-Grid-VPN-In'
  properties: {
    priority: 140
    direction: 'Inbound'
    access: 'Allow'
    protocol: 'Udp'
    sourcePortRange: '*'
    destinationPortRange: '1194'
    sourceAddressPrefixes: grid_peer_prefixes
    destinationAddressPrefix: '*'
    description: 'Grid VPN from other Grid members / Grid Master.'
  }
} ] : []
var ruleGridCommsIn = hasGridPeers ? [ {
  name: 'Allow-Grid-Comms-In'
  properties: {
    priority: 150
    direction: 'Inbound'
    access: 'Allow'
    protocol: 'Tcp'
    sourcePortRange: '*'
    destinationPortRange: '2114'
    sourceAddressPrefixes: grid_peer_prefixes
    destinationAddressPrefix: '*'
    description: 'Grid communications (2114/tcp) between members.'
  }
} ] : []

// ---- INBOUND: SNMP 161 udp — optional, monitoring CIDR ----
var ruleSnmp = hasMonitoring ? [ {
  name: 'Allow-SNMP-In'
  properties: {
    priority: 160
    direction: 'Inbound'
    access: 'Allow'
    protocol: 'Udp'
    sourcePortRange: '*'
    destinationPortRange: '161'
    sourceAddressPrefix: monitoring_source_prefix
    destinationAddressPrefix: '*'
    description: 'SNMP polling from the monitoring CIDR only.'
  }
} ] : []

// ---- INBOUND: default-deny (explicit, below platform default 65500) ----
var ruleDenyAllIn = {
  name: 'Deny-All-In'
  properties: {
    priority: 4096
    direction: 'Inbound'
    access: 'Deny'
    protocol: '*'
    sourcePortRange: '*'
    destinationPortRange: '*'
    sourceAddressPrefix: '*'
    destinationAddressPrefix: '*'
    description: 'Default-deny all other inbound.'
  }
}

// ---- OUTBOUND: NTP 123 udp — always ----
var ruleNtpOut = {
  name: 'Allow-NTP-Out'
  properties: {
    priority: 100
    direction: 'Outbound'
    access: 'Allow'
    protocol: 'Udp'
    sourcePortRange: '*'
    destinationPortRange: '123'
    sourceAddressPrefix: '*'
    destinationAddressPrefix: '*'
    description: 'NTP time sync outbound.'
  }
}

// ---- OUTBOUND: Grid VPN 1194 + Grid comms 2114 — grid only ----
var ruleGridVpnOut = hasGridPeers ? [ {
  name: 'Allow-Grid-VPN-Out'
  properties: {
    priority: 110
    direction: 'Outbound'
    access: 'Allow'
    protocol: 'Udp'
    sourcePortRange: '*'
    destinationPortRange: '1194'
    sourceAddressPrefixes: grid_peer_prefixes
    destinationAddressPrefix: '*'
    description: 'Grid VPN to other Grid members / Grid Master.'
  }
} ] : []
var ruleGridCommsOut = hasGridPeers ? [ {
  name: 'Allow-Grid-Comms-Out'
  properties: {
    priority: 120
    direction: 'Outbound'
    access: 'Allow'
    protocol: 'Tcp'
    sourcePortRange: '*'
    destinationPortRange: '2114'
    sourceAddressPrefixes: grid_peer_prefixes
    destinationAddressPrefix: '*'
    description: 'Grid communications (2114/tcp) to other members.'
  }
} ] : []

// ---- OUTBOUND: Portal sync 443 — universal_ddi ONLY (SaaS boundary crossing) ----
var rulePortalSync = isUniversal ? [ {
  name: 'Allow-Portal-Sync-Out'
  properties: {
    priority: 130
    direction: 'Outbound'
    access: 'Allow'
    protocol: 'Tcp'
    sourcePortRange: '*'
    destinationPortRange: '443'
    sourceAddressPrefix: '*'
    // Scope to the Infoblox Portal (csp.infoblox.com) egress via your firewall/
    // service tag. '*' here is a placeholder — narrow to the Portal's ranges or
    // route through Azure Firewall with an FQDN rule. SaaS boundary crossing.
    destinationAddressPrefix: 'Internet'
    description: 'Outbound 443 to the Infoblox Portal (universal_ddi SaaS control plane).'
  }
} ] : []

// ---- OUTBOUND: default-deny ----
var ruleDenyAllOut = {
  name: 'Deny-All-Out'
  properties: {
    priority: 4096
    direction: 'Outbound'
    access: 'Deny'
    protocol: '*'
    sourcePortRange: '*'
    destinationPortRange: '*'
    sourceAddressPrefix: '*'
    destinationAddressPrefix: '*'
    description: 'Default-deny all other outbound.'
  }
}

// Assemble in priority order.
var securityRules = concat(
  [ ruleDnsTcp, ruleDnsUdp, ruleMgmtHttps ],
  ruleDhcp,
  ruleGridVpnIn,
  ruleGridCommsIn,
  ruleSnmp,
  [ ruleDenyAllIn ],
  [ ruleNtpOut ],
  ruleGridVpnOut,
  ruleGridCommsOut,
  rulePortalSync,
  [ ruleDenyAllOut ]
)

resource nsg 'Microsoft.Network/networkSecurityGroups@2023-11-01' = {
  name: '${name_prefix}-nsg'
  location: location
  tags: tags
  properties: {
    securityRules: securityRules
  }
}

output nsgId string = nsg.id
output nsgName string = nsg.name
