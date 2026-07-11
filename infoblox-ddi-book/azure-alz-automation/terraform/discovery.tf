# discovery.tf
# ---------------------------------------------------------------------------
# Least-privilege discovery identity for Azure -> Infoblox IPAM sync (§5).
#
# Prefer a USER-ASSIGNED MANAGED IDENTITY; fall back to an existing Entra app
# registration's SERVICE PRINCIPAL (this module does NOT create app registrations
# — supply existing_service_principal_object_id).
#
# Role assignments (contract §5) — scoped, opt-in for anything that writes:
#   Reader                       -> each discovered subscription   (always)
#   Private DNS Zone Contributor -> RG(s) with private zones       (only if enable_record_write)
#   Network Contributor          -> spoke VNet(s)                  (only if enable_spoke_dns_write)
# NO Owner. NO Contributor at subscription scope.
# ---------------------------------------------------------------------------

# --- User-assigned managed identity (preferred) -----------------------
resource "azurerm_user_assigned_identity" "disco" {
  count               = var.discovery_identity_type == "user_assigned_mi" ? 1 : 0
  name                = local.disco_mi_name
  location            = var.location
  resource_group_name = var.hub_resource_group_name
  tags                = local.tags
}

locals {
  # Principal (object) id used for role assignments, regardless of identity type.
  disco_principal_id = (
    var.discovery_identity_type == "user_assigned_mi"
    ? try(azurerm_user_assigned_identity.disco[0].principal_id, null)
    : var.existing_service_principal_object_id
  )

  # Canonical identity id emitted as output discovery_identity_id (§7): the MI
  # resource id, or the SP object id when using a service principal.
  disco_identity_id = (
    var.discovery_identity_type == "user_assigned_mi"
    ? try(azurerm_user_assigned_identity.disco[0].id, null)
    : var.existing_service_principal_object_id
  )

  # Build scope sets only when we actually have a principal to bind to, so a
  # service_principal deployment that forgot the object id fails cleanly rather
  # than producing half-formed role assignments.
  reader_scopes = local.disco_principal_id == null ? toset([]) : toset([
    for s in var.discovered_subscription_ids : "/subscriptions/${s}"
  ])

  pdns_scopes = (local.disco_principal_id == null || !var.enable_record_write) ? toset([]) : toset(
    var.private_dns_zone_rg_ids
  )

  spoke_netcontrib_scopes = (local.disco_principal_id == null || !var.enable_spoke_dns_write) ? toset([]) : toset(
    var.spoke_vnet_ids
  )
}

# --- Reader on each discovered subscription (always) ------------------
resource "azurerm_role_assignment" "reader" {
  for_each             = local.reader_scopes
  scope                = each.value
  role_definition_name = "Reader"
  principal_id         = local.disco_principal_id
  principal_type       = "ServicePrincipal"

  description = "Infoblox discovery: enumerate VNets/subnets/NICs/tags (read-only, contract §5)."
}

# --- Private DNS Zone Contributor on private-zone RGs (opt-in) ---------
# Granted ONLY when Infoblox writes records back into Azure Private DNS.
resource "azurerm_role_assignment" "private_dns_zone_contributor" {
  for_each             = local.pdns_scopes
  scope                = each.value
  role_definition_name = "Private DNS Zone Contributor"
  principal_id         = local.disco_principal_id
  principal_type       = "ServicePrincipal"

  description = "Infoblox record write-back into Azure Private DNS (opt-in via enable_record_write, contract §5)."
}

# --- Network Contributor on spoke VNets (opt-in) ----------------------
# Required for the module to write dns_servers on spokes (dns.tf); scope kept to
# the specific spoke VNets, never subscription-wide.
resource "azurerm_role_assignment" "spoke_network_contributor" {
  for_each             = local.spoke_netcontrib_scopes
  scope                = each.value
  role_definition_name = "Network Contributor"
  principal_id         = local.disco_principal_id
  principal_type       = "ServicePrincipal"

  description = "Write dns_servers on spoke VNets (opt-in via enable_spoke_dns_write, contract §5/§8)."
}

# =====================================================================
# INFOBLOX vDISCOVERY / UNIVERSAL CLOUD DISCOVERY — CONFIG PLACEHOLDER
# =====================================================================
# The Azure RBAC above grants the identity; the Infoblox SIDE of discovery is
# configured on the control plane, not in Azure. There is no first-class
# "infoblox_vdiscovery_job" resource in the infobloxopen/infoblox provider
# today, so this is an explicit API/UI handoff:
#
#   * vNIOS Grid  -> Cloud Network Automation "vDiscovery job" pointed at each
#                    subscription, authenticating with the identity's tenant/
#                    client id (+ secret for SP, or federated cred for MI).
#                    Configured via WAPI (POST /wapi/vX/vdiscoverytask) or the
#                    Grid UI. See ../01-azure.md §6/§8.
#   * Universal   -> Portal "Universal Cloud" Azure source using the same
#                    credential; configured through the CSP API/UI.
#
# Sketch of the WAPI handoff (uncomment + wire real values / a restapi provider):
#
# resource "null_resource" "vdiscovery_job" {
#   triggers = { subs = join(",", var.discovered_subscription_ids) }
#   provisioner "local-exec" {
#     command = "curl -k -u \"$IB_USER:$IB_PASS\" -X POST \\
#       https://$GRID_MASTER/wapi/v2.12/vdiscoverytask \\
#       -d 'name=azure-disco&member=infoblox.localdomain&...' "
#   }
# }
#
# For a service_principal identity, the app's client secret/cert is stored in
# Key Vault and handed to Infoblox as the discovery credential; a user-assigned
# MI uses a federated credential / managed-identity auth where supported.
