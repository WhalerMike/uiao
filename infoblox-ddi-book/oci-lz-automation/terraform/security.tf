# security.tf
# ---------------------------------------------------------------------------
# DDI subnet firewalling, EXACTLY per contract §4. Two interchangeable models,
# selected by var.security_model:
#
#   * "nsg"           -> oci_core_network_security_group + per-rule resources,
#                        attached per-VNIC in grid.tf / universal_ddi.tf.
#                        Preferred: finer-grained, follows the VNIC.
#   * "security_list" -> a single oci_core_security_list on the subnet.
#
#   Service      Port     Proto     Dir       When
#   DNS          53       tcp+udp   ingress   always (from dns_client_cidrs)
#   DHCP         67-68    udp       ingress   only if enable_dhcp (default OFF)
#   Grid VPN     1194     udp       in/out    deployment_model=grid
#   Grid comms   2114     tcp       in/out    deployment_model=grid
#   NTP          123      udp       egress    always
#   HTTPS mgmt   443      tcp       ingress   always (from mgmt_source_cidrs)
#   Portal sync  443      tcp       egress    deployment_model=universal_ddi only
#   SNMP         161      udp       ingress   optional (from monitoring_source_cidrs)
#   SSH          22       tcp       ingress   optional (enable_ssh, mgmt CIDR)
#
# OCI NSGs and Security Lists are STATEFUL and DEFAULT-DENY: anything not
# explicitly allowed is dropped, so there are no explicit "deny-all" rules to add
# (unlike Azure NSGs, which need an explicit Deny-All-Out to override the built-in
# internet-egress allow). Protocol numbers: TCP=6, UDP=17. mgmt/monitoring/client
# sources are scoped to explicit CIDR variables — never 0.0.0.0/0 (variables.tf).
# ---------------------------------------------------------------------------

locals {
  # Per-service source sets, emptied when NSG model is not selected or the rule
  # does not apply for this deployment_model. Each set drives a for_each so a rule
  # is created once per source CIDR (OCI rules take a single source).
  nsg_dns_src    = local.use_nsg ? toset(var.dns_client_cidrs) : toset([])
  nsg_mgmt_src   = local.use_nsg ? toset(var.mgmt_source_cidrs) : toset([])
  nsg_ssh_src    = local.use_nsg && var.enable_ssh ? toset(var.mgmt_source_cidrs) : toset([])
  nsg_snmp_src   = local.use_nsg && var.enable_snmp ? toset(var.monitoring_source_cidrs) : toset([])
  nsg_dhcp_src   = local.use_nsg && var.enable_dhcp ? toset(var.dns_client_cidrs) : toset([])
  nsg_grid_src   = local.use_nsg && local.is_grid ? toset(var.grid_peer_cidrs) : toset([])
  nsg_portal_dst = local.use_nsg && local.is_uddi ? toset(var.infoblox_portal_cidrs) : toset([])
}

# ===========================  NSG MODEL  ==============================

resource "oci_core_network_security_group" "ddi" {
  count          = local.use_nsg ? 1 : 0
  compartment_id = var.network_compartment_ocid
  vcn_id         = var.hub_vcn_ocid
  display_name   = local.nsg_name
  freeform_tags  = local.freeform_tags
  defined_tags   = var.defined_tags

  lifecycle {
    precondition {
      condition     = !local.is_grid || length(var.grid_peer_cidrs) > 0
      error_message = "deployment_model='grid' requires grid_peer_cidrs (Grid members/GM ranges) for the 1194/udp + 2114/tcp rules."
    }
    precondition {
      condition     = !var.enable_snmp || length(var.monitoring_source_cidrs) > 0
      error_message = "enable_snmp=true requires monitoring_source_cidrs (SNMP source range)."
    }
  }
}

# --- INGRESS ---------------------------------------------------------

# DNS 53/tcp
resource "oci_core_network_security_group_security_rule" "in_dns_tcp" {
  for_each                  = local.nsg_dns_src
  network_security_group_id = oci_core_network_security_group.ddi[0].id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = each.value
  source_type               = "CIDR_BLOCK"
  description               = "Allow-DNS-TCP-In"
  tcp_options {
    destination_port_range {
      min = 53
      max = 53
    }
  }
}

# DNS 53/udp
resource "oci_core_network_security_group_security_rule" "in_dns_udp" {
  for_each                  = local.nsg_dns_src
  network_security_group_id = oci_core_network_security_group.ddi[0].id
  direction                 = "INGRESS"
  protocol                  = "17"
  source                    = each.value
  source_type               = "CIDR_BLOCK"
  description               = "Allow-DNS-UDP-In"
  udp_options {
    destination_port_range {
      min = 53
      max = 53
    }
  }
}

# HTTPS mgmt / WAPI 443/tcp
resource "oci_core_network_security_group_security_rule" "in_https_mgmt" {
  for_each                  = local.nsg_mgmt_src
  network_security_group_id = oci_core_network_security_group.ddi[0].id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = each.value
  source_type               = "CIDR_BLOCK"
  description               = "Allow-HTTPS-Mgmt-In"
  tcp_options {
    destination_port_range {
      min = 443
      max = 443
    }
  }
}

# SSH 22/tcp (optional)
resource "oci_core_network_security_group_security_rule" "in_ssh" {
  for_each                  = local.nsg_ssh_src
  network_security_group_id = oci_core_network_security_group.ddi[0].id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = each.value
  source_type               = "CIDR_BLOCK"
  description               = "Allow-SSH-Mgmt-In"
  tcp_options {
    destination_port_range {
      min = 22
      max = 22
    }
  }
}

# SNMP 161/udp (optional)
resource "oci_core_network_security_group_security_rule" "in_snmp" {
  for_each                  = local.nsg_snmp_src
  network_security_group_id = oci_core_network_security_group.ddi[0].id
  direction                 = "INGRESS"
  protocol                  = "17"
  source                    = each.value
  source_type               = "CIDR_BLOCK"
  description               = "Allow-SNMP-Monitoring-In"
  udp_options {
    destination_port_range {
      min = 161
      max = 161
    }
  }
}

# DHCP 67-68/udp ingress (optional; on-prem/extranet relay clients)
resource "oci_core_network_security_group_security_rule" "in_dhcp" {
  for_each                  = local.nsg_dhcp_src
  network_security_group_id = oci_core_network_security_group.ddi[0].id
  direction                 = "INGRESS"
  protocol                  = "17"
  source                    = each.value
  source_type               = "CIDR_BLOCK"
  description               = "Allow-DHCP-In"
  udp_options {
    destination_port_range {
      min = 67
      max = 68
    }
  }
}

# Grid VPN 1194/udp ingress — grid only
resource "oci_core_network_security_group_security_rule" "in_grid_vpn" {
  for_each                  = local.nsg_grid_src
  network_security_group_id = oci_core_network_security_group.ddi[0].id
  direction                 = "INGRESS"
  protocol                  = "17"
  source                    = each.value
  source_type               = "CIDR_BLOCK"
  description               = "Allow-GridVPN-In"
  udp_options {
    destination_port_range {
      min = 1194
      max = 1194
    }
  }
}

# Grid comms 2114/tcp ingress — grid only
resource "oci_core_network_security_group_security_rule" "in_grid_comms" {
  for_each                  = local.nsg_grid_src
  network_security_group_id = oci_core_network_security_group.ddi[0].id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = each.value
  source_type               = "CIDR_BLOCK"
  description               = "Allow-GridComms-In"
  tcp_options {
    destination_port_range {
      min = 2114
      max = 2114
    }
  }
}

# --- EGRESS ----------------------------------------------------------

# NTP 123/udp egress — always. Scope destination to your NTP servers where
# possible; 0.0.0.0/0 shown as a placeholder.
resource "oci_core_network_security_group_security_rule" "out_ntp" {
  for_each                  = local.use_nsg ? toset(var.ntp_egress_cidrs) : toset([])
  network_security_group_id = oci_core_network_security_group.ddi[0].id
  direction                 = "EGRESS"
  protocol                  = "17"
  destination               = each.value
  destination_type          = "CIDR_BLOCK"
  description               = "Allow-NTP-Out"
  udp_options {
    destination_port_range {
      min = 123
      max = 123
    }
  }
}

# DNS 53/tcp egress — members recurse / conditionally forward.
resource "oci_core_network_security_group_security_rule" "out_dns_tcp" {
  for_each                  = local.use_nsg ? toset(var.dns_upstream_cidrs) : toset([])
  network_security_group_id = oci_core_network_security_group.ddi[0].id
  direction                 = "EGRESS"
  protocol                  = "6"
  destination               = each.value
  destination_type          = "CIDR_BLOCK"
  description               = "Allow-DNS-TCP-Out"
  tcp_options {
    destination_port_range {
      min = 53
      max = 53
    }
  }
}

# DNS 53/udp egress
resource "oci_core_network_security_group_security_rule" "out_dns_udp" {
  for_each                  = local.use_nsg ? toset(var.dns_upstream_cidrs) : toset([])
  network_security_group_id = oci_core_network_security_group.ddi[0].id
  direction                 = "EGRESS"
  protocol                  = "17"
  destination               = each.value
  destination_type          = "CIDR_BLOCK"
  description               = "Allow-DNS-UDP-Out"
  udp_options {
    destination_port_range {
      min = 53
      max = 53
    }
  }
}

# Grid VPN 1194/udp egress — grid only
resource "oci_core_network_security_group_security_rule" "out_grid_vpn" {
  for_each                  = local.nsg_grid_src
  network_security_group_id = oci_core_network_security_group.ddi[0].id
  direction                 = "EGRESS"
  protocol                  = "17"
  destination               = each.value
  destination_type          = "CIDR_BLOCK"
  description               = "Allow-GridVPN-Out"
  udp_options {
    destination_port_range {
      min = 1194
      max = 1194
    }
  }
}

# Grid comms 2114/tcp egress — grid only
resource "oci_core_network_security_group_security_rule" "out_grid_comms" {
  for_each                  = local.nsg_grid_src
  network_security_group_id = oci_core_network_security_group.ddi[0].id
  direction                 = "EGRESS"
  protocol                  = "6"
  destination               = each.value
  destination_type          = "CIDR_BLOCK"
  description               = "Allow-GridComms-Out"
  tcp_options {
    destination_port_range {
      min = 2114
      max = 2114
    }
  }
}

# Portal sync 443/tcp EGRESS to the Infoblox Portal — universal_ddi ONLY.
# The SaaS-boundary egress gated by acknowledge_saas_boundary (main.tf
# boundary_guard). There is deliberately NO 443 egress for the grid path.
resource "oci_core_network_security_group_security_rule" "out_portal_sync" {
  for_each                  = local.nsg_portal_dst
  network_security_group_id = oci_core_network_security_group.ddi[0].id
  direction                 = "EGRESS"
  protocol                  = "6"
  destination               = each.value
  destination_type          = "CIDR_BLOCK"
  description               = "Allow-InfobloxPortal-Out"
  tcp_options {
    destination_port_range {
      min = 443
      max = 443
    }
  }
}

# ========================  SECURITY-LIST MODEL  ======================
# Single subnet-wide Security List carrying the identical §4 rule set, built with
# dynamic blocks over the same CIDR variables. Attached to the subnet in main.tf
# (oci_core_subnet.ddi.security_list_ids) when security_model="security_list".
resource "oci_core_security_list" "ddi" {
  count          = local.use_seclst ? 1 : 0
  compartment_id = var.network_compartment_ocid
  vcn_id         = var.hub_vcn_ocid
  display_name   = local.seclist_name
  freeform_tags  = local.freeform_tags
  defined_tags   = var.defined_tags

  lifecycle {
    precondition {
      condition     = !local.is_grid || length(var.grid_peer_cidrs) > 0
      error_message = "deployment_model='grid' requires grid_peer_cidrs for the 1194/udp + 2114/tcp rules."
    }
  }

  # --- INGRESS ---
  dynamic "ingress_security_rules" {
    for_each = var.dns_client_cidrs
    content {
      protocol = "6" # DNS TCP
      source   = ingress_security_rules.value
      tcp_options {
        min = 53
        max = 53
      }
    }
  }
  dynamic "ingress_security_rules" {
    for_each = var.dns_client_cidrs
    content {
      protocol = "17" # DNS UDP
      source   = ingress_security_rules.value
      udp_options {
        min = 53
        max = 53
      }
    }
  }
  dynamic "ingress_security_rules" {
    for_each = var.mgmt_source_cidrs
    content {
      protocol = "6" # HTTPS mgmt/WAPI
      source   = ingress_security_rules.value
      tcp_options {
        min = 443
        max = 443
      }
    }
  }
  dynamic "ingress_security_rules" {
    for_each = var.enable_ssh ? var.mgmt_source_cidrs : []
    content {
      protocol = "6" # SSH
      source   = ingress_security_rules.value
      tcp_options {
        min = 22
        max = 22
      }
    }
  }
  dynamic "ingress_security_rules" {
    for_each = var.enable_snmp ? var.monitoring_source_cidrs : []
    content {
      protocol = "17" # SNMP
      source   = ingress_security_rules.value
      udp_options {
        min = 161
        max = 161
      }
    }
  }
  dynamic "ingress_security_rules" {
    for_each = var.enable_dhcp ? var.dns_client_cidrs : []
    content {
      protocol = "17" # DHCP relay
      source   = ingress_security_rules.value
      udp_options {
        min = 67
        max = 68
      }
    }
  }
  dynamic "ingress_security_rules" {
    for_each = local.is_grid ? var.grid_peer_cidrs : []
    content {
      protocol = "17" # Grid VPN
      source   = ingress_security_rules.value
      udp_options {
        min = 1194
        max = 1194
      }
    }
  }
  dynamic "ingress_security_rules" {
    for_each = local.is_grid ? var.grid_peer_cidrs : []
    content {
      protocol = "6" # Grid comms
      source   = ingress_security_rules.value
      tcp_options {
        min = 2114
        max = 2114
      }
    }
  }

  # --- EGRESS ---
  dynamic "egress_security_rules" {
    for_each = toset(var.ntp_egress_cidrs)
    content {
      protocol    = "17" # NTP
      destination = egress_security_rules.value
      udp_options {
        min = 123
        max = 123
      }
    }
  }
  dynamic "egress_security_rules" {
    for_each = toset(var.dns_upstream_cidrs)
    content {
      protocol    = "6" # DNS TCP out
      destination = egress_security_rules.value
      tcp_options {
        min = 53
        max = 53
      }
    }
  }
  dynamic "egress_security_rules" {
    for_each = toset(var.dns_upstream_cidrs)
    content {
      protocol    = "17" # DNS UDP out
      destination = egress_security_rules.value
      udp_options {
        min = 53
        max = 53
      }
    }
  }
  dynamic "egress_security_rules" {
    for_each = local.is_grid ? var.grid_peer_cidrs : []
    content {
      protocol    = "17" # Grid VPN out
      destination = egress_security_rules.value
      udp_options {
        min = 1194
        max = 1194
      }
    }
  }
  dynamic "egress_security_rules" {
    for_each = local.is_grid ? var.grid_peer_cidrs : []
    content {
      protocol    = "6" # Grid comms out
      destination = egress_security_rules.value
      tcp_options {
        min = 2114
        max = 2114
      }
    }
  }
  dynamic "egress_security_rules" {
    for_each = local.is_uddi ? var.infoblox_portal_cidrs : []
    content {
      protocol    = "6" # Portal sync out (universal_ddi only)
      destination = egress_security_rules.value
      tcp_options {
        min = 443
        max = 443
      }
    }
  }
}
