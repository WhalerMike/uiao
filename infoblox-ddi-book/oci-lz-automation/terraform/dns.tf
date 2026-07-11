# dns.tf
# ---------------------------------------------------------------------------
# DNS integration (contract §8) — bidirectional split-horizon at the hub VCN
# OCI resolver:
#
#   (a) Infoblox -> OCI: Infoblox members CONDITIONALLY FORWARD OCI-owned names
#       (*.oraclevcn.com, OCI private zones) to the OCI resolver's LISTENING
#       endpoint. Expressed with infoblox_zone_forward (grid path).
#
#   (b) OCI -> Infoblox: the hub VCN resolver gets a FORWARDING endpoint + rules
#       sending enterprise domains (and a catch-all, if you choose) to the vNIOS
#       member IPs. Spokes reach enterprise names via associated private views or
#       a spoke->hub forwarding rule.
#
# ILLUSTRATIVE. The hub VCN's resolver is auto-created by OCI (one per VCN); this
# module ATTACHES endpoints + rules to it (oci_dns_resolver by resolver_id). It
# does not create the VCN or its base resolver.
# ---------------------------------------------------------------------------

locals {
  # Resolver OCID to attach endpoints/rules to. Supply hub_resolver_ocid, or look
  # it up from the hub VCN's resolver association (data source sketch below).
  hub_resolver_id = var.hub_resolver_ocid

  manage_resolvers = var.manage_resolver_endpoints
}

# Optional lookup of the hub VCN's auto-created resolver (uncomment + wire):
# data "oci_core_vcn_dns_resolver_association" "hub" {
#   vcn_id = var.hub_vcn_ocid
# }
# then: local.hub_resolver_id = coalesce(var.hub_resolver_ocid, data.oci_core_vcn_dns_resolver_association.hub.dns_resolver_id)

# =====================================================================
# OCI resolver endpoints (contract §8): LISTENING (1 IP) + FORWARDING (2 IPs)
# =====================================================================
# LISTENING endpoint — answers queries arriving FROM vNIOS (Infoblox conditional
# forwarders in (a) target this IP). Consumes 1 private IP in its subnet.
resource "oci_dns_resolver_endpoint" "listening" {
  count         = local.manage_resolvers ? 1 : 0
  resolver_id   = local.hub_resolver_id
  name          = "${var.name_prefix}-listen"
  scope         = "PRIVATE"
  subnet_id     = var.resolver_endpoint_subnet_ocid
  is_listening  = true
  is_forwarding = false

  lifecycle {
    precondition {
      condition     = !local.manage_resolvers || (local.hub_resolver_id != null && var.resolver_endpoint_subnet_ocid != null)
      error_message = "manage_resolver_endpoints=true requires hub_resolver_ocid and resolver_endpoint_subnet_ocid."
    }
  }
}

# FORWARDING endpoint — the source for the OCI->Infoblox forwarding rules in (b).
# Consumes 2 private IPs (one used, one reserved).
resource "oci_dns_resolver_endpoint" "forwarding" {
  count         = local.manage_resolvers ? 1 : 0
  resolver_id   = local.hub_resolver_id
  name          = "${var.name_prefix}-forward"
  scope         = "PRIVATE"
  subnet_id     = var.resolver_endpoint_subnet_ocid
  is_listening  = false
  is_forwarding = true
}

# =====================================================================
# (b) OCI -> Infoblox forwarding rules on the hub VCN resolver
# =====================================================================
# Attach FORWARD rules to the hub resolver: enterprise domains -> vNIOS member
# IPs (or the anycast VIP) via the FORWARDING endpoint. Also attach spoke private
# views so spokes resolve enterprise names through the hub (enable_spoke_dns_write).
resource "oci_dns_resolver" "hub" {
  count       = local.manage_resolvers ? 1 : 0
  resolver_id = local.hub_resolver_id
  scope       = "PRIVATE"

  dynamic "rules" {
    for_each = toset(var.enterprise_forward_domains)
    content {
      action                = "FORWARD"
      destination_addresses = local.effective_dns_target
      source_endpoint_name  = oci_dns_resolver_endpoint.forwarding[0].name
      qname_cover_conditions = [rules.value]
    }
  }

  # Attach spoke private views to the hub resolver so spokes resolve enterprise
  # names via these rules (only when opted-in and spokes are provided).
  attached_views {
    view_id = oci_dns_view.enterprise[0].id
  }

  freeform_tags = local.freeform_tags

  depends_on = [oci_dns_resolver_endpoint.forwarding]
}

# Optional private view holding delegated/enterprise reverse zones for OCI CIDRs
# (so PTRs can be served/forwarded consistently). One view, attached above.
resource "oci_dns_view" "enterprise" {
  count          = local.manage_resolvers ? 1 : 0
  compartment_id = var.network_compartment_ocid
  display_name   = "${var.name_prefix}-enterprise-view"
  scope          = "PRIVATE"
  freeform_tags  = local.freeform_tags
}

# =====================================================================
# (a) Infoblox -> OCI conditional forwarders (GRID path only)
# =====================================================================
# For universal_ddi these are configured in the Infoblox Portal (CSP) instead —
# see the handoff note at the bottom. The infobloxopen/infoblox provider exposes
# conditional forwarding via `infoblox_zone_forward` (verify the exact resource +
# attribute names against the version you pin). One per OCI-owned domain, each
# pointing at the OCI resolver LISTENING endpoint IP.
resource "infoblox_zone_forward" "oci_service" {
  for_each = (
    local.is_grid && var.oci_listening_endpoint_ip != null
    ? toset(var.oci_forward_domains)
    : toset([])
  )

  fqdn = each.value

  # Forward OCI-owned names to the OCI resolver LISTENING endpoint, which then
  # answers from the OCI private views / *.oraclevcn.com.
  forward_to {
    name    = "oci-resolver-listening"
    address = var.oci_listening_endpoint_ip
  }

  # NOTE: which Grid member(s) serve this forward zone, and the network view, are
  # environment-specific. Confirm attribute names against the pinned provider
  # version; some builds nest forward_to differently.
}

# =====================================================================
# Notes: reverse direction, spokes, and Universal DDI
# =====================================================================
# * Spokes: attach each spoke VCN's private view to the hub resolver
#   (attached_views above) OR add a spoke->hub forwarding rule, so spoke
#   workloads resolve enterprise/on-prem names via Infoblox over the DRG. The
#   spoke subnet DHCP options already point clients at the VCN resolver
#   (169.254.169.254); the resolver forwards per these rules. Gate real writes on
#   enable_spoke_dns_write + spoke_vcn_ocids (contract §5/§8).
#
# * Reverse zones: delegate OCI CIDR reverse zones (x.in-addr.arpa) to Infoblox so
#   PTRs live in the authoritative IPAM; add the delegation on the OCI side.
#
# * universal_ddi: the conditional forwarders in (a) are configured through the
#   Infoblox Portal (CSP) API/UI rather than the Grid provider. Drive them from
#   the same API-handoff seam as universal_ddi.tf's portal_enroll, or via the
#   CSP/BloxOne Terraform provider once wired.
