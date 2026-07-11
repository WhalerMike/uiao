# firewall.tf
# ---------------------------------------------------------------------------
# VPC firewall rules for the DDI members, EXACTLY per contract §4. Rules are
# scoped by the network tag ${name_prefix}-member on the member instances (the
# GCP analog of scoping to a subnet/NSG).
#
#   Service      Port     Proto     Dir       When
#   DNS          53       tcp+udp   ingress   always (from dns_client_ranges)
#   DHCP         67-68    udp       ingress   only if enable_dhcp (default OFF)
#   Grid VPN     1194     udp       in/out    deployment_model=grid
#   Grid comms   2114     tcp       in/out    deployment_model=grid
#   NTP          123      udp       egress    always
#   HTTPS mgmt   443      tcp       ingress   always (from mgmt_source_ranges)
#   Portal sync  443      tcp       egress    deployment_model=universal_ddi only
#   SNMP         161      udp       ingress   optional (from monitoring_source_ranges)
#   (SSH         22       tcp       ingress   optional, enable_ssh, mgmt ranges)
#
# GCP denies INGRESS by default, but its implied EGRESS is ALLOW-ALL — so we add
# an explicit deny-all egress (priority 65534) plus a low-precedence deny-all
# ingress for auditability, and keep an explicit egress allow to the metadata
# server 169.254.169.254 (platform DNS/metadata). Sources are explicit CIDR
# variables — never 0.0.0.0/0 (enforced in variables.tf).
# ---------------------------------------------------------------------------

locals {
  fw_prefix    = "${var.name_prefix}-fw"
  member_tags  = [local.member_tag]
}

# Fail early (like the Azure NSG precondition) if grid is selected without peer
# ranges, or SNMP without a monitoring source.
resource "terraform_data" "firewall_guard" {
  input = "${var.deployment_model}-${var.enable_snmp}"

  lifecycle {
    precondition {
      condition     = !local.is_grid || length(var.grid_peer_ranges) > 0
      error_message = "deployment_model='grid' requires grid_peer_ranges (Grid members/GM ranges) for the 1194/udp + 2114/tcp rules."
    }
    precondition {
      condition     = !var.enable_snmp || length(var.monitoring_source_ranges) > 0
      error_message = "enable_snmp=true requires monitoring_source_ranges (SNMP source range)."
    }
  }
}

# ===========================  INGRESS  ================================

# DNS 53 tcp+udp — always, from client ranges (spokes/on-prem).
resource "google_compute_firewall" "in_dns" {
  name          = "${local.fw_prefix}-dns-in"
  project       = var.host_project_id
  network       = local.network_self_link
  direction     = "INGRESS"
  priority      = 1000
  source_ranges = var.dns_client_ranges
  target_tags   = local.member_tags

  allow {
    protocol = "tcp"
    ports    = ["53"]
  }
  allow {
    protocol = "udp"
    ports    = ["53"]
  }

  log_config {
    metadata = "INCLUDE_ALL_METADATA"
  }
}

# HTTPS management 443/tcp ingress — always, from mgmt ranges only.
resource "google_compute_firewall" "in_https_mgmt" {
  name          = "${local.fw_prefix}-https-mgmt-in"
  project       = var.host_project_id
  network       = local.network_self_link
  direction     = "INGRESS"
  priority      = 1010
  source_ranges = var.mgmt_source_ranges
  target_tags   = local.member_tags

  allow {
    protocol = "tcp"
    ports    = ["443"]
  }
}

# SSH 22/tcp ingress — optional, mgmt ranges only (prefer IAP / serial console).
resource "google_compute_firewall" "in_ssh" {
  count         = var.enable_ssh ? 1 : 0
  name          = "${local.fw_prefix}-ssh-mgmt-in"
  project       = var.host_project_id
  network       = local.network_self_link
  direction     = "INGRESS"
  priority      = 1020
  source_ranges = var.mgmt_source_ranges
  target_tags   = local.member_tags

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}

# SNMP 161/udp ingress — optional, monitoring ranges only.
resource "google_compute_firewall" "in_snmp" {
  count         = var.enable_snmp ? 1 : 0
  name          = "${local.fw_prefix}-snmp-in"
  project       = var.host_project_id
  network       = local.network_self_link
  direction     = "INGRESS"
  priority      = 1030
  source_ranges = var.monitoring_source_ranges
  target_tags   = local.member_tags

  allow {
    protocol = "udp"
    ports    = ["161"]
  }
}

# DHCP 67-68/udp ingress — only if we serve DHCP from vNIOS (default OFF; GCP
# subnet DHCP is platform-managed via 169.254.169.254).
resource "google_compute_firewall" "in_dhcp" {
  count         = var.enable_dhcp ? 1 : 0
  name          = "${local.fw_prefix}-dhcp-in"
  project       = var.host_project_id
  network       = local.network_self_link
  direction     = "INGRESS"
  priority      = 1040
  source_ranges = var.dns_client_ranges
  target_tags   = local.member_tags

  allow {
    protocol = "udp"
    ports    = ["67", "68"]
  }
}

# Grid VPN 1194/udp + Grid comms 2114/tcp ingress — grid only, from Grid peers/GM.
resource "google_compute_firewall" "in_grid" {
  count         = local.is_grid ? 1 : 0
  name          = "${local.fw_prefix}-grid-in"
  project       = var.host_project_id
  network       = local.network_self_link
  direction     = "INGRESS"
  priority      = 1050
  source_ranges = var.grid_peer_ranges
  target_tags   = local.member_tags

  allow {
    protocol = "udp"
    ports    = ["1194"]
  }
  allow {
    protocol = "tcp"
    ports    = ["2114"]
  }
}

# Explicit default-deny INGRESS (GCP denies by default; this makes intent
# auditable and sits just above the implied deny at 65535).
resource "google_compute_firewall" "in_deny_all" {
  name          = "${local.fw_prefix}-deny-all-in"
  project       = var.host_project_id
  network       = local.network_self_link
  direction     = "INGRESS"
  priority      = 65534
  source_ranges = ["0.0.0.0/0"] # match everything so the DENY is auditable
  target_tags   = local.member_tags

  deny {
    protocol = "all"
  }

  log_config {
    metadata = "INCLUDE_ALL_METADATA"
  }
}

# ===========================  EGRESS  ================================
# GCP's implied egress is ALLOW-ALL; the deny-all-out below makes egress
# default-deny, and the allows above it are the only permitted egress.

# Metadata / platform DNS egress to 169.254.169.254 — always. VMs (incl. the
# members) reach Cloud DNS via the metadata resolver; keep this open under
# default-deny (contract §4).
resource "google_compute_firewall" "out_metadata" {
  name               = "${local.fw_prefix}-metadata-out"
  project            = var.host_project_id
  network            = local.network_self_link
  direction          = "EGRESS"
  priority           = 1000
  destination_ranges = ["169.254.169.254/32"]
  target_tags        = local.member_tags

  allow {
    protocol = "tcp"
    ports    = ["53", "80", "443"]
  }
  allow {
    protocol = "udp"
    ports    = ["53"]
  }
}

# NTP 123/udp + DNS 53 egress — always. Time sync + recursion/conditional
# forwarding. Scope to the VPC + on-prem client ranges where possible.
resource "google_compute_firewall" "out_ntp_dns" {
  name               = "${local.fw_prefix}-ntp-dns-out"
  project            = var.host_project_id
  network            = local.network_self_link
  direction          = "EGRESS"
  priority           = 1010
  destination_ranges = concat([var.ddi_subnet_cidr], var.dns_client_ranges, var.grid_peer_ranges)
  target_tags        = local.member_tags

  allow {
    protocol = "udp"
    ports    = ["123", "53"]
  }
  allow {
    protocol = "tcp"
    ports    = ["53"]
  }
}

# Grid VPN 1194/udp + Grid comms 2114/tcp egress — grid only, to Grid peers/GM.
resource "google_compute_firewall" "out_grid" {
  count              = local.is_grid ? 1 : 0
  name               = "${local.fw_prefix}-grid-out"
  project            = var.host_project_id
  network            = local.network_self_link
  direction          = "EGRESS"
  priority           = 1020
  destination_ranges = var.grid_peer_ranges
  target_tags        = local.member_tags

  allow {
    protocol = "udp"
    ports    = ["1194"]
  }
  allow {
    protocol = "tcp"
    ports    = ["2114"]
  }
}

# Portal sync 443/tcp EGRESS to the Infoblox Portal — universal_ddi ONLY.
# This is the SaaS-boundary egress gated by acknowledge_saas_boundary (see
# main.tf boundary_guard). Destination 0.0.0.0/0 is broad; tighten to the
# Portal's published ranges (csp.infoblox.com) when you have them. There is
# deliberately NO 443 egress rule for the grid path — grid keeps its control
# plane inside the boundary.
resource "google_compute_firewall" "out_portal_sync" {
  count              = local.is_uddi ? 1 : 0
  name               = "${local.fw_prefix}-portal-out"
  project            = var.host_project_id
  network            = local.network_self_link
  direction          = "EGRESS"
  priority           = 1030
  destination_ranges = ["0.0.0.0/0"] # TODO: scope to Infoblox Portal ranges
  target_tags        = local.member_tags

  allow {
    protocol = "tcp"
    ports    = ["443"]
  }
}

# Explicit default-deny EGRESS. The important one: overrides GCP's implied
# allow-all egress so egress is default-deny except the allows above.
resource "google_compute_firewall" "out_deny_all" {
  name               = "${local.fw_prefix}-deny-all-out"
  project            = var.host_project_id
  network            = local.network_self_link
  direction          = "EGRESS"
  priority           = 65534
  destination_ranges = ["0.0.0.0/0"]
  target_tags        = local.member_tags

  deny {
    protocol = "all"
  }

  log_config {
    metadata = "INCLUDE_ALL_METADATA"
  }
}
</content>
