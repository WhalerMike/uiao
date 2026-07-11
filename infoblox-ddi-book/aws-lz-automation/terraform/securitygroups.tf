# securitygroups.tf
# ---------------------------------------------------------------------------
# Security Group on the DDI members, EXACTLY per contract §4.
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
# Security Groups are DEFAULT-DENY ingress by AWS design. Because AWS adds an
# implicit allow-all EGRESS rule on SG creation, we declare the egress set INLINE
# here — declaring any egress makes Terraform manage the FULL egress rule set, so
# the allow-all default is replaced by exactly the rules below = default-deny out.
# Sources are scoped to explicit CIDR variables — never 0.0.0.0/0 (enforced in
# variables.tf). Rules are built as data and rendered via dynamic blocks so the
# conditional (grid / uddi / optional) rows drop out cleanly.
# ---------------------------------------------------------------------------

locals {
  # NTP egress targets: on-prem/enterprise NTP typically reachable over TGW.
  # Scope to grid peers + DNS clients (adjust to your dedicated NTP servers).
  ntp_egress_cidrs = distinct(concat(var.grid_peer_cidrs, var.dns_client_cidrs))

  # DNS egress: members recurse / conditionally forward to the Resolver inbound
  # endpoint and to on-prem/upstream. Include the resolver inbound IP /32 if set.
  dns_egress_cidrs = distinct(concat(
    var.dns_client_cidrs,
    var.grid_peer_cidrs,
    var.r53_resolver_inbound_ip != null ? ["${var.r53_resolver_inbound_ip}/32"] : [],
  ))

  # ---- INGRESS rule set (rows with empty cidr_blocks are filtered out) ----
  ingress_rules_raw = concat(
    [
      { description = "DNS 53/tcp from clients", protocol = "tcp", from_port = 53, to_port = 53, cidr_blocks = var.dns_client_cidrs },
      { description = "DNS 53/udp from clients", protocol = "udp", from_port = 53, to_port = 53, cidr_blocks = var.dns_client_cidrs },
      { description = "HTTPS 443 mgmt (Grid Manager UI/API)", protocol = "tcp", from_port = 443, to_port = 443, cidr_blocks = var.mgmt_source_cidrs },
    ],
    var.enable_ssh ? [{ description = "SSH 22 mgmt", protocol = "tcp", from_port = 22, to_port = 22, cidr_blocks = var.mgmt_source_cidrs }] : [],
    var.enable_snmp ? [{ description = "SNMP 161/udp monitoring", protocol = "udp", from_port = 161, to_port = 161, cidr_blocks = var.monitoring_source_cidrs }] : [],
    var.enable_dhcp ? [{ description = "DHCP 67-68/udp", protocol = "udp", from_port = 67, to_port = 68, cidr_blocks = var.dns_client_cidrs }] : [],
    local.is_grid ? [
      { description = "Grid VPN 1194/udp from Grid peers/GM", protocol = "udp", from_port = 1194, to_port = 1194, cidr_blocks = var.grid_peer_cidrs },
      { description = "Grid comms 2114/tcp from Grid peers/GM", protocol = "tcp", from_port = 2114, to_port = 2114, cidr_blocks = var.grid_peer_cidrs },
    ] : [],
  )
  ingress_rules = [for r in local.ingress_rules_raw : r if length(r.cidr_blocks) > 0]

  # ---- EGRESS rule set (default-deny except these) ----
  egress_rules_raw = concat(
    [
      { description = "NTP 123/udp (time sync)", protocol = "udp", from_port = 123, to_port = 123, cidr_blocks = local.ntp_egress_cidrs },
      { description = "DNS 53/tcp recurse/forward", protocol = "tcp", from_port = 53, to_port = 53, cidr_blocks = local.dns_egress_cidrs },
      { description = "DNS 53/udp recurse/forward", protocol = "udp", from_port = 53, to_port = 53, cidr_blocks = local.dns_egress_cidrs },
    ],
    local.is_grid ? [
      { description = "Grid VPN 1194/udp to Grid peers/GM", protocol = "udp", from_port = 1194, to_port = 1194, cidr_blocks = var.grid_peer_cidrs },
      { description = "Grid comms 2114/tcp to Grid peers/GM", protocol = "tcp", from_port = 2114, to_port = 2114, cidr_blocks = var.grid_peer_cidrs },
    ] : [],
    # Portal sync 443 egress — universal_ddi ONLY. This is the SaaS-boundary
    # egress gated by acknowledge_saas_boundary (see main.tf boundary_guard).
    # 0.0.0.0/0 is used because the Portal has no fixed IP range; TIGHTEN to the
    # Portal's published ranges (csp.infoblox.com) when you have them. There is
    # deliberately NO 443 egress on the grid path — grid stays in-boundary.
    local.is_uddi ? [{ description = "Infoblox Portal (CSP) sync 443/tcp", protocol = "tcp", from_port = 443, to_port = 443, cidr_blocks = ["0.0.0.0/0"] }] : [],
  )
  egress_rules = [for r in local.egress_rules_raw : r if length(r.cidr_blocks) > 0]
}

resource "aws_security_group" "ddi" {
  name        = local.sg_name
  description = "Infoblox DDI members — contract §4 port set (default-deny in/out)"
  vpc_id      = var.hub_vpc_id
  tags        = merge(local.tags, { Name = local.sg_name })

  dynamic "ingress" {
    for_each = local.ingress_rules
    content {
      description = ingress.value.description
      protocol    = ingress.value.protocol
      from_port   = ingress.value.from_port
      to_port     = ingress.value.to_port
      cidr_blocks = ingress.value.cidr_blocks
    }
  }

  dynamic "egress" {
    for_each = local.egress_rules
    content {
      description = egress.value.description
      protocol    = egress.value.protocol
      from_port   = egress.value.from_port
      to_port     = egress.value.to_port
      cidr_blocks = egress.value.cidr_blocks
    }
  }

  lifecycle {
    # Grid path needs Grid peer/GM CIDRs for the 1194/udp + 2114/tcp rules.
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
