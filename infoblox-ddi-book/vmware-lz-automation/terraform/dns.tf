# dns.tf
# ---------------------------------------------------------------------------
# DNS / DHCP integration (contract §8):
#   (a) NSX-T Tier-0/Tier-1 DNS FORWARDER -> Infoblox: tenant VMs resolve via the
#       gateway forwarder, which forwards upstream to the DDI member VIP. The Grid
#       is the single resolution brain for the private cloud.
#   (b) Infoblox -> on-prem AD DNS: the Grid CONDITIONALLY FORWARDS corp.example
#       (and reverse zones) to the on-prem AD DNS servers (the mirror of the Azure
#       forward-to-Private-Resolver path).
#   (c) DHCP served by Infoblox: NSX DHCP RELAY points tenant segments at the
#       vNIOS DHCP members (67-68/udp). DHCP is genuinely Infoblox's job on VMware.
#
# ILLUSTRATIVE. NSX policy DNS/DHCP object + attribute names are version-specific
# across nsxt 3.x; confirm against the provider docs for the version you pin:
#   https://registry.terraform.io/providers/vmware/nsxt/latest/docs
# and the Infoblox zone-forward surface against:
#   https://registry.terraform.io/providers/infobloxopen/infoblox/latest/docs
# ---------------------------------------------------------------------------

# =====================================================================
# (a) NSX-T DNS forwarder zone -> Infoblox DDI VIP
# =====================================================================
# The upstream (default) DNS zone points tenant resolution at the DDI members.
# Gate: only when workload Tier-1 gateways are provided AND the operator opted in.
# The zone must then be attached to the gateway DNS forwarder (per-gateway config);
# that attachment is gateway-specific — see the note below.
resource "nsxt_policy_dns_forwarder_zone" "ddi_upstream" {
  count        = var.enable_nsx_dns_forwarder && length(var.workload_tier1_ids) > 0 ? 1 : 0
  display_name = "${var.name_prefix}-upstream-to-infoblox"
  description  = "Default DNS forwarder zone -> Infoblox DDI VIP (contract §8)."

  # Upstream = the DDI anycast VIP (or the member IPs if no VIP is set).
  upstream_servers = local.effective_dns_target
}

# NOTE: attaching the forwarder zone to each workload Tier-1's DNS forwarder is a
# per-gateway step. In the policy provider this is the gateway DNS-forwarder
# configuration referencing the default_forwarder_zone_path above; the exact
# resource/attribute is version-specific (e.g. a gateway DNS forwarder resource
# per Tier-1 in var.workload_tier1_ids). Wire one per gateway:
#
#   # resource "nsxt_policy_dns_forwarder" "t1" {
#   #   for_each               = toset(var.workload_tier1_ids)
#   #   gateway_path           = each.value
#   #   listener_ip            = "<forwarder listener IP on the gateway>"
#   #   default_forwarder_zone_path = nsxt_policy_dns_forwarder_zone.ddi_upstream[0].path
#   # }
#
# Verify the resource name/fields against the nsxt provider docs for your version.

# =====================================================================
# (b) Infoblox conditional forwarders: AD zones -> on-prem AD DNS
# =====================================================================
# GRID path only (the provider drives the Grid control plane). For universal_ddi
# these forwarders are configured in the Infoblox Portal (CSP) instead — see the
# handoff note at the bottom. Created once per domain in ad_forward_domains, each
# pointing at the on-prem AD DNS servers. This keeps AD-integrated names resolving
# without making Infoblox authoritative for AD zones (contract §8).
resource "infoblox_zone_forward" "ad" {
  for_each = (
    local.is_grid && length(var.ad_dns_servers) > 0
    ? toset(var.ad_forward_domains)
    : toset([])
  )

  fqdn = each.value

  # Forward these AD-integrated names to the on-prem AD DNS servers.
  dynamic "forward_to" {
    for_each = { for idx, ip in var.ad_dns_servers : idx => ip }
    content {
      name    = "ad-dns-${forward_to.key}"
      address = forward_to.value
    }
  }

  # Which Grid member(s) serve this forward zone, and the network view, are
  # environment-specific — set forwarding_servers / view per your Grid design.
  # Confirm attribute names against the pinned provider version; some builds nest
  # forward_to differently or expose forwarders_only.
}

# =====================================================================
# (c) NSX DHCP relay -> Infoblox DHCP members  (DHCP is Infoblox's job)
# =====================================================================
# ON by default (enable_dhcp). The relay profile points tenant segments' DHCP at
# the vNIOS members; Infoblox allocates from the IPAM-authoritative range and can
# write the A/PTR record. Attach this relay profile to the tenant segments/Tier-1s
# (per-segment step, gateway/segment specific — see note).
resource "nsxt_policy_dhcp_relay" "ddi" {
  count           = var.enable_dhcp ? 1 : 0
  display_name    = "${var.name_prefix}-dhcp-relay-to-infoblox"
  description     = "NSX DHCP relay -> Infoblox DHCP members (contract §8)."
  server_addresses = length(var.member_ip_addresses) > 0 ? var.member_ip_addresses : (var.ddi_anycast_vip != null ? [var.ddi_anycast_vip] : [])
}

# NOTE: a DHCP relay profile must be ATTACHED to each tenant segment (or the
# Tier-1's DHCP config) to take effect — that attachment is segment-specific and
# frequently owned by the workload/platform team, so it is left as a documented
# step rather than assumed here. Reference nsxt_policy_dhcp_relay.ddi[0].path on
# the relevant nsxt_policy_segment.dhcp_config / gateway.

# =====================================================================
# Reverse direction & Universal DDI notes
# =====================================================================
# * Split-horizon: use Grid DNS Views to present internal answers to the private
#   cloud while public zones are served separately (../05-vmware.md §7).
# * Cross-cloud: where the Grid extends into a CSP, add conditional forwarders for
#   that cloud's private namespaces to its resolver — same infoblox_zone_forward
#   pattern as (b), targeting the CSP resolver inbound IP.
# * universal_ddi: the conditional forwarders in (b) are configured through the
#   Infoblox Portal (CSP) API/UI rather than the Grid provider. Drive them from
#   the same API-handoff seam as universal_ddi.tf's portal_enroll.
