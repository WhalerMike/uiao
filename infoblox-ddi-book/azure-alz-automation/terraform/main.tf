# main.tf
# ---------------------------------------------------------------------------
# Locals, module-managed tags (contract §6), the dedicated DDI subnet in the
# hub VNet, and the HARD-FAIL boundary guard for the universal_ddi (SaaS) path.
#
# Resource layout across files:
#   main.tf          — locals, tags, subnet, boundary precondition, KV secrets
#   nsg.tf           — NSG + rules (contract §4) and subnet association
#   grid.tf          — vNIOS Grid members         (deployment_model="grid")
#   universal_ddi.tf — NIOS-X hosts + Portal join  (deployment_model="universal_ddi")
#   discovery.tf     — discovery identity + RBAC   (contract §5)
#   dns.tf           — conditional forwarders + spoke dns_servers (contract §8)
#   outputs.tf       — canonical outputs (contract §7)
# ---------------------------------------------------------------------------

locals {
  # --- Name parsing from the Stage-1 hub VNet id -------------------------
  # hub_vnet_id looks like:
  #   /subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.Network/virtualNetworks/<name>
  hub_vnet_name = reverse(split("/", var.hub_vnet_id))[0]
  # The subscription that owns the hub VNet (where the subnet/NSG/VMs land).
  hub_subscription_id = split("/", var.hub_vnet_id)[2]

  # --- Naming convention (contract §6): ${name_prefix}-<role>-<zone/index> --
  subnet_name      = "${var.name_prefix}-subnet"
  nsg_name         = "${var.name_prefix}-nsg"
  disco_mi_name    = "${var.name_prefix}-disco-mi"
  member_base_name = "${var.name_prefix}-vnios"   # grid members: ddi-vnios-z1...
  niosx_base_name  = "${var.name_prefix}-niosx"   # uddi hosts:   ddi-niosx-1...

  # --- Model flags ------------------------------------------------------
  is_grid = var.deployment_model == "grid"
  is_uddi = var.deployment_model == "universal_ddi"

  # Round-robin members over the provided zones. Index i -> zone. Also used to
  # build the per-member name suffix (z<zone> for grid, plain index for uddi).
  member_indexes = range(var.member_count)
  member_zone_for = {
    for i in local.member_indexes :
    i => var.availability_zones[i % length(var.availability_zones)]
  }
  # Per-member name label. When there is one zone per member you get the clean
  # ddi-vnios-z1 / ddi-vnios-z2 form (contract §6); if members outnumber zones,
  # the index is appended to keep Azure resource names unique.
  member_label = {
    for i in local.member_indexes :
    i => (
      var.member_count <= length(var.availability_zones)
      ? "z${local.member_zone_for[i]}"
      : format("z%s-%d", local.member_zone_for[i], i)
    )
  }

  # --- Module-managed tags (contract §6) --------------------------------
  # These keys are authoritative; caller tags are merged UNDER them so the
  # governance-relevant keys can't be silently overridden.
  managed_tags = {
    workload           = "infoblox-ddi"
    layer              = "connectivity-ddi"
    compliance_profile = var.compliance_profile
    deployment_model   = var.deployment_model
    managed_by         = "terraform"
    environment        = var.environment
  }
  tags = merge(var.tags, local.managed_tags)

  # --- Member NIC IPs (populated by grid.tf OR universal_ddi.tf) --------
  # Exactly one of these resource collections is non-empty depending on
  # deployment_model; the other has count=0 and yields an empty list.
  member_dns_ips = local.is_grid ? (
    azurerm_network_interface.grid[*].private_ip_address
    ) : (
    azurerm_network_interface.niosx[*].private_ip_address
  )

  # Grid Master IP (grid only, contract §7). If an existing (usually on-prem)
  # Grid Master VIP is supplied, that is authoritative; otherwise fall back to
  # the first Azure member (lab/greenfield where the first member is the GM).
  grid_master_ip = local.is_grid ? try(
    coalesce(var.grid_master_vip, azurerm_network_interface.grid[0].private_ip_address),
    null
  ) : null

  # --- DNS server IP handling (contract §7/§8) --------------------------
  # Preferred spoke resolver address is the anycast VIP; fall back to the
  # members' individual NIC IPs (dns_server_ips).
  effective_dns_target = var.ddi_anycast_vip != null ? [var.ddi_anycast_vip] : local.member_dns_ips
}

# ---------------------------------------------------------------------------
# BOUNDARY GUARD (contract §1) — HARD FAIL.
# deployment_model="universal_ddi" routes the control plane through the Infoblox
# Portal (SaaS), which sits OUTSIDE the ATO boundary and needs outbound 443.
# That path is only permitted with an explicit acknowledge_saas_boundary=true.
# A precondition on this resource fails the PLAN (not just apply) with a message
# pointing to the authorization review.
# ---------------------------------------------------------------------------
resource "terraform_data" "boundary_guard" {
  # Nothing to create; this exists solely to host the precondition.
  input = var.deployment_model

  lifecycle {
    precondition {
      condition = !(var.deployment_model == "universal_ddi" && var.acknowledge_saas_boundary == false)
      error_message = join("\n", [
        "BOUNDARY VIOLATION: deployment_model = \"universal_ddi\" selects the Infoblox",
        "Portal (SaaS) control plane, which is OUTSIDE the ATO / GCC-Moderate boundary",
        "and requires OUTBOUND 443 to the Infoblox Portal (contract §1).",
        "",
        "This path is disabled until it is explicitly authorized. To proceed you MUST:",
        "  1. Complete the FedRAMP/authorization review for the SaaS control-plane egress,",
        "     and confirm the Portal SaaS offering's authorization status is acceptable",
        "     for this system's boundary; then",
        "  2. Set  acknowledge_saas_boundary = true.",
        "",
        "For a boundary-clean deployment, use deployment_model = \"grid\" (the default),",
        "which keeps the vNIOS Grid control plane INSIDE the tenant/ATO boundary.",
      ])
    }
  }
}

# ---------------------------------------------------------------------------
# Dedicated DDI subnet, created by THIS module inside the Stage-1 hub VNet.
# The hub VNet itself and the Private Resolver /28 subnets are NOT created here
# (they are Stage-1 / existing). Naming: ddi-subnet (contract §6).
# ---------------------------------------------------------------------------
resource "azurerm_subnet" "ddi" {
  name                 = local.subnet_name
  resource_group_name  = var.hub_resource_group_name
  virtual_network_name = local.hub_vnet_name
  address_prefixes     = [var.ddi_subnet_address_prefix]

  # NOTE: azurerm_subnet does not carry tags (Azure subnets are untaggable);
  # tags live on the NSG, NICs, VMs, and identity instead.

  # If you ever serve DHCP from vNIOS you may need service endpoints/policies;
  # left default here since Azure DHCP is platform-managed (enable_dhcp default off).
}

# ---------------------------------------------------------------------------
# Data sources for the module secrets in the existing Key Vault. Values are
# passed into cloud-init/user-data (grid.tf) and the Portal join (universal_ddi.tf).
# These read EXISTING secrets — the module does not create them.
# ---------------------------------------------------------------------------
data "azurerm_key_vault_secret" "admin_password" {
  name         = var.admin_password_secret_name
  key_vault_id = var.key_vault_id
}

data "azurerm_key_vault_secret" "temp_license" {
  name         = var.temp_license_secret_name
  key_vault_id = var.key_vault_id
}

# Grid shared secret is only meaningful for the grid path.
data "azurerm_key_vault_secret" "grid_shared_secret" {
  count        = local.is_grid ? 1 : 0
  name         = var.grid_shared_secret_name
  key_vault_id = var.key_vault_id
}

# Portal join token is only meaningful for the universal_ddi path.
data "azurerm_key_vault_secret" "saas_join_token" {
  count        = local.is_uddi ? 1 : 0
  name         = var.saas_join_token_secret_name
  key_vault_id = var.key_vault_id
}
