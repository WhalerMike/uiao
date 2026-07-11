# dns.tf
# ---------------------------------------------------------------------------
# DNS integration (contract §8). Cloud DNS resolution is wired in BOTH
# directions — independent VPC-level constructs (03-gcp.md §7):
#
#   (a) INBOUND server policy  — google_dns_policy with enable_inbound_forwarding
#       on the host VPC. Cloud DNS allocates inbound forwarder IPs; the Infoblox
#       members (and on-prem) target those IPs to resolve Cloud DNS private-zone
#       and *.googleapis.com names.
#   (b) INFOBLOX conditional forwarders — infoblox_zone_forward for google-service
#       / Cloud DNS private domains -> the Cloud DNS inbound forwarder IP, so those
#       names resolve natively through the Infoblox fabric (grid path).
#   (c) OUTBOUND forwarding zones — google_dns_managed_zone (forwarding) for
#       enterprise/on-prem domains -> the Infoblox member IPs, so GCP VMs resolve
#       corp names via Infoblox.
#   (d) PEERING zones — google_dns_managed_zone (peering) so spoke_networks resolve
#       enterprise domains via the host VPC's forwarding config (split-horizon).
#
# ILLUSTRATIVE. Real object references (member name/view on the Infoblox side; the
# exact provider attribute names) are flagged where import / real IDs / a version
# check are needed.
# ---------------------------------------------------------------------------

# =====================================================================
# (a) INBOUND Cloud DNS server policy on the host VPC
# =====================================================================
# Turns on inbound forwarding for the whole VPC; Cloud DNS then allocates inbound
# forwarder IPs from the VPC's subnet ranges. Read them afterwards with:
#   gcloud dns policies describe <policy> --project <host-project>
# and feed one into var.cloud_dns_inbound_ip for the (b) forwarders below.
resource "google_dns_policy" "inbound" {
  count                     = var.inbound_forwarding_enabled ? 1 : 0
  project                   = var.host_project_id
  name                      = "${var.name_prefix}-inbound-policy"
  enable_inbound_forwarding = true
  # Query logging feeds AU-* controls.
  enable_logging = true

  networks {
    network_url = local.network_self_link
  }
}

# =====================================================================
# (b) Infoblox conditional forwarders: google-service names -> Cloud DNS inbound
# =====================================================================
# GRID path only (the provider drives the Grid control plane). For universal_ddi
# these forwarders are configured in the Infoblox Portal (CSP) instead — see the
# handoff note at the bottom of this file.
#
# The infobloxopen/infoblox provider exposes conditional forwarding via
# `infoblox_zone_forward` (verify the exact resource + attribute names against the
# version you pin — the provider's zone/forward surface has evolved across 2.x).
# Created once per domain in infoblox_forward_domains, each pointing at the Cloud
# DNS inbound forwarder IP.
resource "infoblox_zone_forward" "gcp_service" {
  for_each = (
    local.is_grid && var.cloud_dns_inbound_ip != null
    ? toset(var.infoblox_forward_domains)
    : toset([])
  )

  fqdn = each.value

  # Forward these Google-service / Cloud DNS private names to the Cloud DNS
  # inbound forwarder IP, which then resolves against Cloud DNS.
  forward_to {
    name    = "cloud-dns-inbound"
    address = var.cloud_dns_inbound_ip
  }

  # NOTE: which Grid member(s) serve this forward zone, and the network view, are
  # environment-specific — set forward_to per member or use forwarders_only
  # semantics as your Grid design requires. Confirm attribute names against the
  # pinned provider version; some builds nest forward_to differently.
}

# =====================================================================
# (c) OUTBOUND Cloud DNS forwarding zones: enterprise domains -> Infoblox members
# =====================================================================
# One forwarding managed zone per domain in enterprise_forward_domains, each with
# target_name_servers set to the DDI resolver (anycast VIP or member IPs). VMs in
# the host VPC then resolve corp/on-prem names via Infoblox while *.googleapis.com
# and Cloud DNS private zones keep resolving natively.
#
# For Type-2 private routing to members reached over Interconnect/HA VPN, the VPC
# must return-route 35.199.192.0/19 (03-gcp.md §7) — that route is a Stage-1 /
# network concern, not created here.
resource "google_dns_managed_zone" "enterprise_forward" {
  for_each = toset(var.enterprise_forward_domains)

  project     = var.host_project_id
  name        = "${var.name_prefix}-fwd-${replace(trimsuffix(each.value, "."), ".", "-")}"
  dns_name    = each.value
  description = "Infoblox DDI forwarding zone for ${each.value} (managed_by=terraform)"
  visibility  = "private"
  labels      = local.labels

  private_visibility_config {
    networks {
      network_url = local.network_self_link
    }
  }

  forwarding_config {
    dynamic "target_name_servers" {
      for_each = toset(local.effective_dns_target)
      content {
        ipv4_address = target_name_servers.value
        # "private" keeps queries on the RFC1918/VPC path (Type 1/2). Use
        # "default" only for a non-RFC-1918 target reached over the internet.
        forwarding_path = "private"
      }
    }
  }
}

# =====================================================================
# (d) PEERING zones: spoke VPCs resolve enterprise domains via the hub VPC
# =====================================================================
# Gate: only when we have spokes AND the operator opted into peering. Each spoke
# network gets a peering zone whose target is the host VPC, so every project
# funnels corp/on-prem queries through the hub's forwarding zones (c) to Infoblox.
locals {
  peer_spokes = var.enable_spoke_dns_peering ? toset(var.spoke_networks) : toset([])

  # Peering is per (spoke-network x enterprise-domain). Flatten to a map keyed by
  # a stable id so for_each is deterministic.
  peer_zone_map = {
    for pair in setproduct(tolist(local.peer_spokes), var.enterprise_forward_domains) :
    "${reverse(split("/", pair[0]))[0]}--${replace(trimsuffix(pair[1], "."), ".", "-")}" => {
      spoke_network = pair[0]
      dns_name      = pair[1]
    }
  }
}

resource "google_dns_managed_zone" "spoke_peering" {
  for_each = local.peer_zone_map

  project     = var.host_project_id
  name        = "${var.name_prefix}-peer-${each.key}"
  dns_name    = each.value.dns_name
  description = "Cloud DNS peering ${each.value.dns_name} from spoke to hub (managed_by=terraform)"
  visibility  = "private"
  labels      = local.labels

  private_visibility_config {
    networks {
      network_url = each.value.spoke_network
    }
  }

  peering_config {
    target_network {
      network_url = local.network_self_link
    }
  }

  # Members/VIP + hub forwarding zone must exist before spokes peer to them.
  depends_on = [google_dns_managed_zone.enterprise_forward]
}

# =====================================================================
# Alternative outbound path & Universal DDI notes
# =====================================================================
# * OUTBOUND SERVER POLICY (broad alternative to (c)): instead of per-domain
#   forwarding zones you can point the WHOLE VPC's resolution at the Infoblox
#   members with a google_dns_policy `alternative_name_server_config`. That
#   overrides all resolution for the VPC, so it is heavier than surgical
#   forwarding zones — offered as an option, not the default:
#
#   resource "google_dns_policy" "outbound" {
#     name    = "${var.name_prefix}-outbound-policy"
#     project = var.host_project_id
#     networks { network_url = local.network_self_link }
#     alternative_name_server_config {
#       dynamic "target_name_servers" {
#         for_each = toset(local.effective_dns_target)
#         content { ipv4_address = target_name_servers.value; forwarding_path = "private" }
#       }
#     }
#   }
#
# * universal_ddi: the Infoblox-side conditional forwarders in (b) are configured
#   through the Infoblox Portal (CSP) API/UI rather than the Grid provider. Drive
#   them from the same API-handoff seam as universal_ddi.tf's portal_enroll, or via
#   the CSP/Universal DDI Terraform provider once wired. The Cloud DNS resources
#   (a/c/d) apply identically on both paths.
</content>
