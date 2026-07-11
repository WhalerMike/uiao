# dns.tf
# ---------------------------------------------------------------------------
# DNS integration (contract §8):
#   (a) Infoblox members are authoritative for enterprise zones and CONDITIONALLY
#       FORWARD AWS-service names (amazonaws.com, <region>.compute.internal, and
#       Route 53 private-hosted-zone domains) to the Route 53 Resolver INBOUND
#       endpoint (Stage-1/existing).
#   (b) Spoke VPC DHCP option sets point domain-name-servers at the DDI anycast
#       VIP (or member LAN1 IPs) — the module writes this ONLY when spoke_vpc_ids
#       is set AND enable_spoke_dns_write=true.
#
# ILLUSTRATIVE where noted. The Infoblox provider needs a reachable Grid/NIOS WAPI
# endpoint, so the conditional-forwarder resources typically apply in a SECOND
# phase after the members are up and Grid-joined (use -target or a dependent module).
# ---------------------------------------------------------------------------

# =====================================================================
# (a) Conditional forwarders: AWS-service zones -> Resolver inbound
# =====================================================================
# GRID path only (provider drives the Grid control plane). For the universal_ddi
# path these forwarders are configured in the Infoblox Portal (CSP) instead —
# see the handoff note at the bottom of this file.
#
# The infobloxopen/infoblox provider exposes conditional forwarding via
# `infoblox_zone_forward` (verify the exact resource + attribute names against the
# version you pin — the provider's zone/forward surface has evolved across 2.x).
# Created once per domain in aws_service_forward_domains, each pointing at the
# Route 53 Resolver inbound endpoint IP.
resource "infoblox_zone_forward" "aws_service" {
  for_each = (
    local.is_grid && var.r53_resolver_inbound_ip != null
    ? toset(var.aws_service_forward_domains)
    : toset([])
  )

  fqdn = each.value

  # Forward these AWS-service names to the Route 53 Resolver inbound endpoint,
  # which then resolves against Route 53 (private hosted zones, amazonaws.com,
  # <region>.compute.internal, etc.).
  forward_to {
    name    = "r53-resolver-inbound"
    address = var.r53_resolver_inbound_ip
  }

  # NOTE: which Grid member(s) serve this forward zone, and the network view, are
  # environment-specific. Confirm attribute names against the pinned provider
  # version; some builds nest forward_to differently or expose forwarders_only.
}

# =====================================================================
# (b) Point spoke VPC DHCP option sets at the DDI resolver
# =====================================================================
# Gate: only when we have spokes AND the operator opted into writing them.
locals {
  write_spoke_dns   = var.enable_spoke_dns_write && length(var.spoke_vpc_ids) > 0
  spoke_dns_targets = local.effective_dns_target
}

# One DHCP option set carrying the DDI resolver as domain-name-servers. Unlike
# Azure (where dns_servers is a VNet attribute), AWS uses a DHCP option set
# associated with each VPC. NOTE: associating this set REPLACES AmazonProvidedDNS
# for the spoke — instances pick it up on DHCP lease renewal. The identity running
# Terraform needs ec2:CreateDhcpOptions / ec2:AssociateDhcpOptions on the spokes.
resource "aws_vpc_dhcp_options" "ddi" {
  count               = local.write_spoke_dns ? 1 : 0
  domain_name_servers = local.spoke_dns_targets
  tags                = merge(local.tags, { Name = "${var.name_prefix}-dhcp-options" })
}

resource "aws_vpc_dhcp_options_association" "spoke" {
  for_each        = local.write_spoke_dns ? toset(var.spoke_vpc_ids) : toset([])
  vpc_id          = each.value
  dhcp_options_id = aws_vpc_dhcp_options.ddi[0].id

  # Members/VIP must exist before we point spokes at them.
  depends_on = [
    aws_instance.grid,
    aws_instance.niosx,
  ]
}

# =====================================================================
# Reverse direction, VPC IPAM & Universal DDI notes
# =====================================================================
# * AWS -> Infoblox (outbound): create a Route 53 Resolver OUTBOUND endpoint plus
#   forwarding RULES (one per domain, e.g. corp.example) targeting the DDI VIP /
#   member LAN1 IPs on 53, and share the rules across accounts via AWS RAM. Not all
#   deployments automate this (the platform team may own the resolver, contract §8,
#   ../02-aws.md §7). If you do automate it, add:
#     aws_route53_resolver_endpoint          (direction = "OUTBOUND")
#     aws_route53_resolver_rule              (rule_type = "FORWARD", target_ip = DDI IPs)
#     aws_route53_resolver_rule_association   (per spoke VPC)
#     aws_ram_resource_share / _association   (cross-account rule sharing)
#   pointing target_ip at local.effective_dns_target.
#
# * VPC IPAM coexistence (contract §8): in the visibility model Infoblox discovers
#   VPC CIDRs and stays authoritative IPAM. In the 2025 Amazon VPC IPAM <-> Infoblox
#   authoritative model you designate Infoblox as the management authority for a VPC
#   IPAM PRIVATE scope and, via BYOIP, pull non-overlapping CIDRs from Infoblox
#   Universal IPAM into the top-level AWS IPAM pool. Private scopes only — not public.
#
# * universal_ddi: the conditional forwarders in (a) are configured through the
#   Infoblox Portal (CSP) API/UI rather than the Grid provider. Drive them from the
#   same API-handoff seam as universal_ddi.tf's portal_enroll, or via the CSP/BloxOne
#   Terraform provider once wired.
