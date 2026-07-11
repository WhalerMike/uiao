# dns.tf
# ---------------------------------------------------------------------------
# DNS integration (contract §8):
#   (a) Infoblox members are authoritative for enterprise zones and CONDITIONALLY
#       FORWARD Azure-service names (privatelink.*, azure.com private) to the
#       Azure DNS Private Resolver INBOUND endpoint (Stage-1/existing).
#   (b) Spoke/hub dns_servers point at the DDI anycast VIP (or member IPs) — the
#       module writes this ONLY when spoke_vnet_ids is set AND Network Contributor
#       was granted (enable_spoke_dns_write, see discovery.tf).
#
# ILLUSTRATIVE. Real object references (member name/view on the Infoblox side,
# and the fact that azurerm has no single-attribute "set VNet dns_servers"
# resource) mean the concrete wiring is marked where import / real IDs / an
# azapi provider are needed.
# ---------------------------------------------------------------------------

# =====================================================================
# (a) Conditional forwarders: Azure-service zones -> Private Resolver inbound
# =====================================================================
# GRID path only (provider drives the Grid control plane). For the universal_ddi
# path these forwarders are configured in the Infoblox Portal (CSP) instead —
# see the handoff note at the bottom of this file.
#
# The infobloxopen/infoblox provider exposes conditional forwarding via
# `infoblox_zone_forward` (verify the exact resource + attribute names against
# the version you pin — the provider's zone/forward surface has evolved across
# 2.x). Created once per domain in azure_service_forward_domains, each pointing
# at the Private Resolver inbound endpoint IP.
resource "infoblox_zone_forward" "azure_service" {
  for_each = (
    local.is_grid && var.private_resolver_inbound_ip != null
    ? toset(var.azure_service_forward_domains)
    : toset([])
  )

  fqdn = each.value

  # Forward these Azure-service names to the Private Resolver inbound endpoint,
  # which then resolves against Azure Private DNS (privatelink.* etc.).
  forward_to {
    name    = "azure-private-resolver-inbound"
    address = var.private_resolver_inbound_ip
  }

  # The DNS view / member serving the forward zone is deployment-specific.
  # comment = "..."  # EAs/comment optional
  # NOTE: which Grid member(s) serve this forward zone, and the network view,
  # are environment-specific — set forward_to per member or use forwarders_only
  # semantics as your Grid design requires. Confirm attribute names against the
  # pinned provider version; some builds nest forward_to differently.
}

# =====================================================================
# (b) Point spoke VNet dns_servers at the DDI resolver
# =====================================================================
# Gate: only when we have spokes AND the operator opted into writing dns_servers
# (which is what the Network Contributor grant in discovery.tf authorizes).
locals {
  write_spoke_dns = var.enable_spoke_dns_write && length(var.spoke_vnet_ids) > 0

  # The resolver address written onto spokes: anycast VIP if provided, else the
  # concrete member NIC IPs (dns_server_ips). Rendered as a comma list for the
  # az-cli sketch below.
  spoke_dns_targets = local.effective_dns_target
}

# azurerm has NO resource that patches ONLY a VNet's dns_servers without owning
# the whole azurerm_virtual_network. Spokes here are pre-existing (Stage-1 /
# workload teams), so we do NOT import + manage them. Two honest options:
#
#   OPTION 1 (shown): a null_resource local-exec `az network vnet update` that
#            PATCHes dns_servers. Simple, but imperative and not drift-tracked.
#   OPTION 2 (preferred for real use): the azapi provider ->
#            resource "azapi_update_resource" "spoke_dns" {
#              type = "Microsoft.Network/virtualNetworks@2023-11-01"
#              resource_id = each.value
#              body = { properties = { dhcpOptions = { dnsServers = local.spoke_dns_targets } } }
#            }
#            (add azapi to versions.tf). This IS drift-tracked.
#
# Either way the identity running Terraform (or the discovery MI) needs Network
# Contributor on the spoke — that is the opt-in grant in discovery.tf.
resource "null_resource" "spoke_dns_servers" {
  for_each = local.write_spoke_dns ? toset(var.spoke_vnet_ids) : toset([])

  triggers = {
    vnet_id     = each.value
    dns_servers = join(",", local.spoke_dns_targets)
  }

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    command     = <<-EOC
      set -euo pipefail
      # >>> Illustrative: patch spoke dns_servers to the DDI resolver. <<<
      # Requires 'az' logged in with Network Contributor on the spoke (see §5).
      az network vnet update --ids "${each.value}" \
        --dns-servers ${join(" ", local.spoke_dns_targets)}
      echo "Set dns_servers on ${each.value} -> ${join(",", local.spoke_dns_targets)}"
    EOC
  }

  # Members/VIP must exist before we point spokes at them.
  depends_on = [
    azurerm_linux_virtual_machine.grid,
    azurerm_linux_virtual_machine.niosx,
  ]
}

# =====================================================================
# Reverse direction (Azure -> Infoblox) & Universal DDI notes
# =====================================================================
# * Azure -> Infoblox (outbound): the Private Resolver OUTBOUND endpoint carries
#   a forwarding ruleset whose rule for the enterprise domain (corp.example.)
#   targets the DDI VIP/member IPs on 53. That ruleset + rule live on the Azure
#   side; not all deployments automate it (contract §8, ../01-azure.md §7). If you
#   do automate it, add azurerm_private_dns_resolver_forwarding_rule / _ruleset
#   resources here pointing target_dns_servers at local.effective_dns_target.
#
# * universal_ddi: the conditional forwarders in (a) are configured through the
#   Infoblox Portal (CSP) API/UI rather than the Grid provider. Drive them from
#   the same API-handoff seam as universal_ddi.tf's portal_enroll, or via the
#   CSP/BloxOne Terraform provider once wired.
