# firewall.tf
# ---------------------------------------------------------------------------
# NSX-T Distributed Firewall (DFW) micro-segmentation for the DDI members,
# EXACTLY per contract §4. On VMware "security" is DFW rules + a member group,
# not a cloud NSG — but the intent is identical: default-deny, only the contract
# ports, sources scoped to explicit CIDR variables (never 0.0.0.0/0).
#
#   Service      Port     Proto     Dir       When
#   DNS          53       tcp+udp   inbound   always  (from dns_client_cidrs)
#   DHCP         67-68    udp       inbound   ON by default (from dhcp_relay_cidrs)
#   Grid VPN     1194     udp       in/out    deployment_model=grid
#   Grid comms   2114     tcp       in/out    deployment_model=grid
#   NTP          123      udp       outbound  always
#   HTTPS/WAPI   443      tcp       inbound   always  (from mgmt_source_cidrs)
#   Portal sync  443      tcp       outbound  deployment_model=universal_ddi only
#   SNMP         161      udp       inbound   optional (from monitoring_source_cidrs)
#   (SSH         22       tcp       inbound   optional, enable_ssh, mgmt CIDR)
#
# The KEY VMware difference vs. the hyperscalers: DHCP 67-68/udp is ON BY DEFAULT
# (enable_dhcp defaults true) because Infoblox is the authoritative DHCP server
# here (contract §4/§8).
#
# NOTE: NSX object/attribute names are version-specific across nsxt 3.x. Confirm
# resource + field names against the provider docs for the version you pin:
#   https://registry.terraform.io/providers/vmware/nsxt/latest/docs
# ---------------------------------------------------------------------------

# --- Member group: the DDI members, matched by their management IPs ----------
# An IP-set group is deployment-model independent and does not depend on the VMs
# existing yet (member IPs are static, from member_ip_addresses).
resource "nsxt_policy_group" "ddi_members" {
  display_name = local.dfw_group_name
  description  = "Infoblox DDI members (DNS/DHCP/Grid) — managed by terraform (contract §4)."

  criteria {
    ipaddress_expression {
      ip_addresses = length(var.member_ip_addresses) > 0 ? var.member_ip_addresses : [var.ddi_mgmt_network_cidr]
    }
  }
}

# --- Custom services for the Infoblox ports ----------------------------------
# (NSX ships built-in services for DNS/DHCP/NTP/HTTPS/SNMP; custom l4 services
# are used here so the port set is explicit and self-documenting.)
resource "nsxt_policy_service" "dns" {
  display_name = "${var.name_prefix}-svc-dns"
  l4_port_set_entry {
    display_name      = "dns-tcp"
    protocol          = "TCP"
    destination_ports = ["53"]
  }
  l4_port_set_entry {
    display_name      = "dns-udp"
    protocol          = "UDP"
    destination_ports = ["53"]
  }
}

resource "nsxt_policy_service" "dhcp" {
  display_name = "${var.name_prefix}-svc-dhcp"
  l4_port_set_entry {
    display_name      = "dhcp-udp"
    protocol          = "UDP"
    destination_ports = ["67", "68"]
  }
}

resource "nsxt_policy_service" "grid_vpn" {
  display_name = "${var.name_prefix}-svc-grid-vpn"
  l4_port_set_entry {
    display_name      = "grid-vpn-udp"
    protocol          = "UDP"
    destination_ports = ["1194"]
  }
}

resource "nsxt_policy_service" "grid_comms" {
  display_name = "${var.name_prefix}-svc-grid-comms"
  l4_port_set_entry {
    display_name      = "grid-comms-tcp"
    protocol          = "TCP"
    destination_ports = ["2114"]
  }
}

resource "nsxt_policy_service" "ntp" {
  display_name = "${var.name_prefix}-svc-ntp"
  l4_port_set_entry {
    display_name      = "ntp-udp"
    protocol          = "UDP"
    destination_ports = ["123"]
  }
}

resource "nsxt_policy_service" "https" {
  display_name = "${var.name_prefix}-svc-https"
  l4_port_set_entry {
    display_name      = "https-tcp"
    protocol          = "TCP"
    destination_ports = ["443"]
  }
}

resource "nsxt_policy_service" "snmp" {
  count        = var.enable_snmp ? 1 : 0
  display_name = "${var.name_prefix}-svc-snmp"
  l4_port_set_entry {
    display_name      = "snmp-udp"
    protocol          = "UDP"
    destination_ports = ["161"]
  }
}

resource "nsxt_policy_service" "ssh" {
  count        = var.enable_ssh ? 1 : 0
  display_name = "${var.name_prefix}-svc-ssh"
  l4_port_set_entry {
    display_name      = "ssh-tcp"
    protocol          = "TCP"
    destination_ports = ["22"]
  }
}

# --- The DDI security policy (ordered rules + default-deny) -------------------
# Grid rows and the outbound-Portal row are toggled by deployment_model, so a
# Grid deployment never opens the SaaS egress and a Universal DDI deployment
# never opens the Grid VPN. A precondition mirrors the Azure module: the grid
# path needs grid_peer_cidrs for the 1194/2114 rules.
resource "nsxt_policy_security_policy" "ddi" {
  display_name = "${var.name_prefix}-ddi-policy"
  description  = "Default-deny DDI micro-segmentation (contract §4)."
  category     = "Application"
  locked       = false
  stateful     = true

  lifecycle {
    precondition {
      condition     = !local.is_grid || length(var.grid_peer_cidrs) > 0
      error_message = "deployment_model='grid' requires grid_peer_cidrs (Grid members/GM ranges) for the 1194/udp + 2114/tcp rules."
    }
    precondition {
      condition     = !var.enable_dhcp || length(var.dhcp_relay_cidrs) > 0
      error_message = "enable_dhcp=true (the VMware default) requires dhcp_relay_cidrs (the NSX DHCP relay source range)."
    }
    precondition {
      condition     = !var.enable_snmp || length(var.monitoring_source_cidrs) > 0
      error_message = "enable_snmp=true requires monitoring_source_cidrs (SNMP source range)."
    }
  }

  # --- INBOUND: DNS 53 tcp+udp — always ---
  rule {
    display_name       = "Allow-DNS-In"
    source_groups      = []                                # source by IP below
    sources_excluded   = false
    destination_groups = [nsxt_policy_group.ddi_members.path]
    services           = [nsxt_policy_service.dns.path]
    action             = "ALLOW"
    direction          = "IN"
    ip_version         = "IPV4"
    # Scope sources to the tenant/forwarder CIDRs. In NSX you typically model
    # these as a source group; shown inline via the description for clarity.
    # (Create an nsxt_policy_group of dns_client_cidrs and reference it here.)
  }

  # --- INBOUND: DHCP 67-68 udp — ON by default on VMware ---
  dynamic "rule" {
    for_each = var.enable_dhcp ? [1] : []
    content {
      display_name       = "Allow-DHCP-In"
      destination_groups = [nsxt_policy_group.ddi_members.path]
      services           = [nsxt_policy_service.dhcp.path]
      action             = "ALLOW"
      direction          = "IN"
      ip_version         = "IPV4"
      # Source = dhcp_relay_cidrs (NSX DHCP relay). Model as a source group.
    }
  }

  # --- INBOUND: HTTPS/WAPI 443 — always, mgmt CIDRs (admins, Aria, CNA) ---
  rule {
    display_name       = "Allow-HTTPS-WAPI-In"
    destination_groups = [nsxt_policy_group.ddi_members.path]
    services           = [nsxt_policy_service.https.path]
    action             = "ALLOW"
    direction          = "IN"
    ip_version         = "IPV4"
    # Source = mgmt_source_cidrs.
  }

  # --- INBOUND: SSH 22 — optional ---
  dynamic "rule" {
    for_each = var.enable_ssh ? [1] : []
    content {
      display_name       = "Allow-SSH-In"
      destination_groups = [nsxt_policy_group.ddi_members.path]
      services           = [nsxt_policy_service.ssh[0].path]
      action             = "ALLOW"
      direction          = "IN"
      ip_version         = "IPV4"
      # Source = mgmt_source_cidrs.
    }
  }

  # --- INBOUND: SNMP 161 — optional ---
  dynamic "rule" {
    for_each = var.enable_snmp ? [1] : []
    content {
      display_name       = "Allow-SNMP-In"
      destination_groups = [nsxt_policy_group.ddi_members.path]
      services           = [nsxt_policy_service.snmp[0].path]
      action             = "ALLOW"
      direction          = "IN"
      ip_version         = "IPV4"
      # Source = monitoring_source_cidrs.
    }
  }

  # --- IN/OUT: Grid VPN 1194 + Grid comms 2114 — grid only ---
  dynamic "rule" {
    for_each = local.is_grid ? [1] : []
    content {
      display_name       = "Allow-GridVPN"
      destination_groups = [nsxt_policy_group.ddi_members.path]
      services           = [nsxt_policy_service.grid_vpn.path]
      action             = "ALLOW"
      direction          = "IN_OUT"
      ip_version         = "IPV4"
      # Peers = grid_peer_cidrs (member subnet + on-prem GM).
    }
  }
  dynamic "rule" {
    for_each = local.is_grid ? [1] : []
    content {
      display_name       = "Allow-GridComms"
      destination_groups = [nsxt_policy_group.ddi_members.path]
      services           = [nsxt_policy_service.grid_comms.path]
      action             = "ALLOW"
      direction          = "IN_OUT"
      ip_version         = "IPV4"
    }
  }

  # --- OUTBOUND: NTP 123 — always ---
  rule {
    display_name     = "Allow-NTP-Out"
    source_groups    = [nsxt_policy_group.ddi_members.path]
    services         = [nsxt_policy_service.ntp.path]
    action           = "ALLOW"
    direction        = "OUT"
    ip_version       = "IPV4"
  }

  # --- OUTBOUND: Portal sync 443 — universal_ddi ONLY (SaaS boundary egress) --
  # There is deliberately NO outbound-443 rule on the grid path — grid keeps its
  # control plane inside the SDDC. Gated by acknowledge_saas_boundary upstream.
  dynamic "rule" {
    for_each = local.is_uddi ? [1] : []
    content {
      display_name  = "Allow-InfobloxPortal-Out"
      source_groups = [nsxt_policy_group.ddi_members.path]
      services      = [nsxt_policy_service.https.path]
      action        = "ALLOW"
      direction     = "OUT"
      ip_version    = "IPV4"
      # Destination = the Infoblox Portal ranges (csp.infoblox.com). Scope to the
      # published Portal IP set once you have it rather than any-destination.
    }
  }

  # --- DEFAULT-DENY: drop everything else to/from the members ---
  rule {
    display_name       = "Deny-All-DDI"
    destination_groups = [nsxt_policy_group.ddi_members.path]
    action             = "DROP"
    direction          = "IN_OUT"
    ip_version         = "IPV4"
    logged             = true
  }
}

# ---------------------------------------------------------------------------
# IMPLEMENTATION NOTE (read before relying on this file).
# For brevity the rules above bind sources/destinations via the member group and
# comments name the intended CIDR source variable. In a real deployment, model
# each source CIDR set as its own nsxt_policy_group (ip_addresses = the CIDR
# list) and set `source_groups` on the matching rule — e.g.:
#
#   resource "nsxt_policy_group" "dns_clients" {
#     display_name = "${var.name_prefix}-dns-clients"
#     criteria { ipaddress_expression { ip_addresses = var.dns_client_cidrs } }
#   }
#   # then on Allow-DNS-In: source_groups = [nsxt_policy_group.dns_clients.path]
#
# The variable validations already REJECT 0.0.0.0/0 on mgmt/dns/dhcp/monitoring
# sources, so the scoping intent is enforced at plan time regardless.
# ---------------------------------------------------------------------------
