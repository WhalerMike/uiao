# nsg.tf
# ---------------------------------------------------------------------------
# Network Security Group + rules on the DDI subnet, EXACTLY per contract §4.
#
#   Service      Port     Proto     Dir       When
#   DNS          53       tcp+udp   inbound   always (from dns_client_cidrs)
#   DHCP         67-68    udp       inbound   only if enable_dhcp (default OFF)
#   Grid VPN     1194     udp       in/out    deployment_model=grid
#   Grid comms   2114     tcp       in/out    deployment_model=grid
#   NTP          123      udp       outbound  always
#   HTTPS mgmt   443      tcp       inbound   always (from mgmt_source_cidrs)
#   Portal sync  443      tcp       outbound  deployment_model=universal_ddi only
#   SNMP         161      udp       inbound   optional (from monitoring_source_cidrs)
#   (SSH         22       tcp       inbound   optional, enable_ssh, mgmt CIDR)
#
# Default-deny everything else: Azure already denies inbound by default; we ALSO
# add an explicit DenyAll OUTBOUND so egress is default-deny (Azure's built-in
# default ALLOWS internet egress, which we do not want). mgmt/monitoring sources
# are scoped to explicit CIDR variables — never 0.0.0.0/0 (enforced in variables.tf).
# Rules are separate resources (not inline) so they can be conditionally counted.
# ---------------------------------------------------------------------------

resource "azurerm_network_security_group" "ddi" {
  name                = local.nsg_name
  location            = var.location
  resource_group_name = var.hub_resource_group_name
  tags                = local.tags

  lifecycle {
    # Grid path needs Grid peer/GM CIDRs for the 1194/udp + 2114/tcp rules;
    # Azure rejects an empty source/destination list, so fail early and clearly.
    precondition {
      condition     = !local.is_grid || length(var.grid_peer_cidrs) > 0
      error_message = "deployment_model='grid' requires grid_peer_cidrs (Grid members/GM ranges) for the 1194/udp + 2114/tcp rules."
    }
    # SNMP rule needs a monitoring source when enabled.
    precondition {
      condition     = !var.enable_snmp || length(var.monitoring_source_cidrs) > 0
      error_message = "enable_snmp=true requires monitoring_source_cidrs (SNMP source range)."
    }
  }
}

resource "azurerm_subnet_network_security_group_association" "ddi" {
  subnet_id                 = azurerm_subnet.ddi.id
  network_security_group_id = azurerm_network_security_group.ddi.id
}

# ===========================  INBOUND  ================================

# DNS 53/tcp — always, from spoke/on-prem client CIDRs.
resource "azurerm_network_security_rule" "in_dns_tcp" {
  name                        = "Allow-DNS-TCP-In"
  priority                    = 100
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "53"
  source_address_prefixes     = var.dns_client_cidrs
  destination_address_prefix  = var.ddi_subnet_address_prefix
  resource_group_name         = var.hub_resource_group_name
  network_security_group_name = azurerm_network_security_group.ddi.name
}

# DNS 53/udp — always.
resource "azurerm_network_security_rule" "in_dns_udp" {
  name                        = "Allow-DNS-UDP-In"
  priority                    = 110
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Udp"
  source_port_range           = "*"
  destination_port_range      = "53"
  source_address_prefixes     = var.dns_client_cidrs
  destination_address_prefix  = var.ddi_subnet_address_prefix
  resource_group_name         = var.hub_resource_group_name
  network_security_group_name = azurerm_network_security_group.ddi.name
}

# HTTPS management 443/tcp inbound — always, from mgmt CIDRs only.
resource "azurerm_network_security_rule" "in_https_mgmt" {
  name                        = "Allow-HTTPS-Mgmt-In"
  priority                    = 120
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "443"
  source_address_prefixes     = var.mgmt_source_cidrs
  destination_address_prefix  = var.ddi_subnet_address_prefix
  resource_group_name         = var.hub_resource_group_name
  network_security_group_name = azurerm_network_security_group.ddi.name
}

# SSH 22/tcp inbound — optional, mgmt CIDRs only (prefer Bastion/serial console).
resource "azurerm_network_security_rule" "in_ssh" {
  count                       = var.enable_ssh ? 1 : 0
  name                        = "Allow-SSH-Mgmt-In"
  priority                    = 130
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "22"
  source_address_prefixes     = var.mgmt_source_cidrs
  destination_address_prefix  = var.ddi_subnet_address_prefix
  resource_group_name         = var.hub_resource_group_name
  network_security_group_name = azurerm_network_security_group.ddi.name
}

# SNMP 161/udp inbound — optional, monitoring CIDRs only.
resource "azurerm_network_security_rule" "in_snmp" {
  count                       = var.enable_snmp ? 1 : 0
  name                        = "Allow-SNMP-Monitoring-In"
  priority                    = 140
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Udp"
  source_port_range           = "*"
  destination_port_range      = "161"
  source_address_prefixes     = var.monitoring_source_cidrs
  destination_address_prefix  = var.ddi_subnet_address_prefix
  resource_group_name         = var.hub_resource_group_name
  network_security_group_name = azurerm_network_security_group.ddi.name
}

# DHCP 67-68/udp inbound — only if we serve DHCP from vNIOS (default OFF).
resource "azurerm_network_security_rule" "in_dhcp" {
  count                        = var.enable_dhcp ? 1 : 0
  name                         = "Allow-DHCP-In"
  priority                     = 150
  direction                    = "Inbound"
  access                       = "Allow"
  protocol                     = "Udp"
  source_port_range            = "*"
  destination_port_ranges      = ["67", "68"]
  source_address_prefixes      = var.dns_client_cidrs
  destination_address_prefix   = var.ddi_subnet_address_prefix
  resource_group_name          = var.hub_resource_group_name
  network_security_group_name  = azurerm_network_security_group.ddi.name
}

# Grid VPN 1194/udp inbound — grid only, from Grid peers/GM.
resource "azurerm_network_security_rule" "in_grid_vpn" {
  count                       = local.is_grid ? 1 : 0
  name                        = "Allow-GridVPN-In"
  priority                    = 160
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Udp"
  source_port_range           = "*"
  destination_port_range      = "1194"
  source_address_prefixes     = var.grid_peer_cidrs
  destination_address_prefix  = var.ddi_subnet_address_prefix
  resource_group_name         = var.hub_resource_group_name
  network_security_group_name = azurerm_network_security_group.ddi.name
}

# Grid comms 2114/tcp inbound — grid only (CRAM auth precedes VPN).
resource "azurerm_network_security_rule" "in_grid_comms" {
  count                       = local.is_grid ? 1 : 0
  name                        = "Allow-GridComms-In"
  priority                    = 170
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "2114"
  source_address_prefixes     = var.grid_peer_cidrs
  destination_address_prefix  = var.ddi_subnet_address_prefix
  resource_group_name         = var.hub_resource_group_name
  network_security_group_name = azurerm_network_security_group.ddi.name
}

# Explicit default-deny inbound (Azure denies by default; this makes intent
# auditable and sits just above the platform default at 65500).
resource "azurerm_network_security_rule" "in_deny_all" {
  name                        = "Deny-All-In"
  priority                    = 4096
  direction                   = "Inbound"
  access                      = "Deny"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "*"
  destination_address_prefix  = "*"
  resource_group_name         = var.hub_resource_group_name
  network_security_group_name = azurerm_network_security_group.ddi.name
}

# ===========================  OUTBOUND  ===============================

# NTP 123/udp outbound — always. Time sync. Scope to your NTP servers where
# possible; VirtualNetwork target assumes an in-VNet/hub NTP source.
resource "azurerm_network_security_rule" "out_ntp" {
  name                        = "Allow-NTP-Out"
  priority                    = 100
  direction                   = "Outbound"
  access                      = "Allow"
  protocol                    = "Udp"
  source_port_range           = "*"
  destination_port_range      = "123"
  source_address_prefix       = var.ddi_subnet_address_prefix
  destination_address_prefix  = "VirtualNetwork"
  resource_group_name         = var.hub_resource_group_name
  network_security_group_name = azurerm_network_security_group.ddi.name
}

# DNS 53 outbound (tcp+udp) — members recurse / conditionally forward to the
# Private Resolver inbound endpoint and to upstream/on-prem. Scoped to the VNet.
resource "azurerm_network_security_rule" "out_dns" {
  name                        = "Allow-DNS-Out"
  priority                    = 110
  direction                   = "Outbound"
  access                      = "Allow"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "53"
  source_address_prefix       = var.ddi_subnet_address_prefix
  destination_address_prefix  = "VirtualNetwork"
  resource_group_name         = var.hub_resource_group_name
  network_security_group_name = azurerm_network_security_group.ddi.name
}

# Grid VPN 1194/udp outbound — grid only.
resource "azurerm_network_security_rule" "out_grid_vpn" {
  count                       = local.is_grid ? 1 : 0
  name                        = "Allow-GridVPN-Out"
  priority                    = 120
  direction                   = "Outbound"
  access                      = "Allow"
  protocol                    = "Udp"
  source_port_range           = "*"
  destination_port_range      = "1194"
  source_address_prefix       = var.ddi_subnet_address_prefix
  destination_address_prefixes = var.grid_peer_cidrs
  resource_group_name         = var.hub_resource_group_name
  network_security_group_name = azurerm_network_security_group.ddi.name
}

# Grid comms 2114/tcp outbound — grid only.
resource "azurerm_network_security_rule" "out_grid_comms" {
  count                       = local.is_grid ? 1 : 0
  name                        = "Allow-GridComms-Out"
  priority                    = 130
  direction                   = "Outbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "2114"
  source_address_prefix       = var.ddi_subnet_address_prefix
  destination_address_prefixes = var.grid_peer_cidrs
  resource_group_name         = var.hub_resource_group_name
  network_security_group_name = azurerm_network_security_group.ddi.name
}

# Portal sync 443/tcp OUTBOUND to the Infoblox Portal — universal_ddi ONLY.
# This is the SaaS-boundary egress gated by acknowledge_saas_boundary (see
# main.tf boundary_guard). Destination "Internet" is broad; tighten to the
# Portal's published service tag/IP ranges (csp.infoblox.com / csp.eu.infoblox.com)
# when you have them. There is deliberately NO outbound 443 rule for the grid
# path — grid keeps its control plane inside the boundary.
resource "azurerm_network_security_rule" "out_portal_sync" {
  count                       = local.is_uddi ? 1 : 0
  name                        = "Allow-InfobloxPortal-Out"
  priority                    = 140
  direction                   = "Outbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "443"
  source_address_prefix       = var.ddi_subnet_address_prefix
  destination_address_prefixes = var.infoblox_portal_cidrs
  resource_group_name         = var.hub_resource_group_name
  network_security_group_name = azurerm_network_security_group.ddi.name
}

# Explicit default-deny OUTBOUND. This is the important one: it overrides
# Azure's built-in AllowInternetOutBound so egress is default-deny except the
# allows above.
resource "azurerm_network_security_rule" "out_deny_all" {
  name                        = "Deny-All-Out"
  priority                    = 4096
  direction                   = "Outbound"
  access                      = "Deny"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "*"
  destination_address_prefix  = "*"
  resource_group_name         = var.hub_resource_group_name
  network_security_group_name = azurerm_network_security_group.ddi.name
}
