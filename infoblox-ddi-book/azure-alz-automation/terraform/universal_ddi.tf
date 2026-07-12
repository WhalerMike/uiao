# universal_ddi.tf
# ---------------------------------------------------------------------------
# UNIVERSAL DDI (SaaS) path (deployment_model = "universal_ddi").
#
# BOUNDARY WARNING: this path enrolls lightweight NIOS-X hosts into the Infoblox
# Portal (CSP), whose control plane is SaaS and sits OUTSIDE the ATO/GCC-Moderate
# boundary. It requires OUTBOUND 443 to the Portal (nsg.tf out_portal_sync) and
# is HARD-GATED behind acknowledge_saas_boundary=true (main.tf boundary_guard).
# Do not enable without completing the authorization review (contract §1).
#
# Creates, gated on local.is_uddi:
#   * azurerm_network_interface       — one NIC per NIOS-X host on the DDI subnet
#   * azurerm_linux_virtual_machine   — member_count NIOS-X hosts, across zones
#   * null_resource (local-exec)      — PORTAL ENROLLMENT HANDOFF placeholder:
#                                        joins each host to the Portal with the
#                                        join token. This is the API seam — swap
#                                        for the real CSP REST call / provider.
#
# All resources here have count = 0 when deployment_model = "grid".
# ---------------------------------------------------------------------------

locals {
  uddi_member_count = local.is_uddi ? var.member_count : 0

  # NIOS-X first-boot user-data. The join token (from Key Vault) enrolls the
  # host into the Portal over outbound 443. Exact schema is release-dependent —
  # verify against the current NIOS-X / Infoblox Cloud Services docs.
  uddi_user_data = local.is_uddi ? (<<-EOT
    #infoblox-config

    default_admin_password: ${data.azurerm_key_vault_secret.admin_password.value}
    remote_console_enabled: y

    # Portal (CSP) enrollment. The host phones home to infoblox_portal_url over
    # 443 and registers using the join token.
    join_token: ${data.azurerm_key_vault_secret.saas_join_token[0].value}
    csp_url: ${var.infoblox_portal_url}
  EOT
  ) : null
}

# --- NIOS-X host NICs on the DDI subnet -------------------------------
resource "azurerm_network_interface" "niosx" {
  count                          = local.uddi_member_count
  name                           = "${local.niosx_base_name}-${count.index + 1}-nic"
  location                       = var.location
  resource_group_name            = var.hub_resource_group_name
  accelerated_networking_enabled = var.enable_accelerated_networking
  tags                           = local.tags

  ip_configuration {
    name                          = "lan1"
    subnet_id                     = azurerm_subnet.ddi.id
    private_ip_address_allocation = "Dynamic"
  }
}

# --- Marketplace agreement (NIOS-X image) -----------------------------
# NIOS-X server images ship from the same Infoblox Marketplace publisher; accept
# the plan terms for the image supplied in vnios_image.
resource "azurerm_marketplace_agreement" "niosx" {
  count     = local.is_uddi && var.accept_marketplace_agreement ? 1 : 0
  publisher = var.vnios_image.publisher
  offer     = var.vnios_image.offer
  plan      = local.vnios_plan_name
}

# --- NIOS-X host VMs ---------------------------------------------------
resource "azurerm_linux_virtual_machine" "niosx" {
  count               = local.uddi_member_count
  name                = "${local.niosx_base_name}-${count.index + 1}"
  computer_name       = "${local.niosx_base_name}-${count.index + 1}"
  location            = var.location
  resource_group_name = var.hub_resource_group_name
  size                = var.vnios_vm_sku
  zone                = local.member_zone_for[count.index]
  admin_username      = var.admin_username
  tags                = local.tags

  network_interface_ids = [azurerm_network_interface.niosx[count.index].id]

  disable_password_authentication = true
  admin_ssh_key {
    username   = var.admin_username
    public_key = tls_private_key.niosx_placeholder[0].public_key_openssh
  }

  custom_data = base64encode(local.uddi_user_data)

  os_disk {
    name                 = "${local.niosx_base_name}-${count.index + 1}-osdisk"
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
  }

  source_image_reference {
    publisher = var.vnios_image.publisher
    offer     = var.vnios_image.offer
    sku       = var.vnios_image.sku
    version   = var.vnios_image.version
  }

  plan {
    name      = local.vnios_plan_name
    publisher = var.vnios_image.publisher
    product   = var.vnios_image.offer
  }

  depends_on = [azurerm_marketplace_agreement.niosx]

  lifecycle {
    ignore_changes = [custom_data]
  }
}

resource "tls_private_key" "niosx_placeholder" {
  count     = local.uddi_member_count > 0 ? 1 : 0
  algorithm = "RSA"
  rsa_bits  = 4096
}

# =====================================================================
# PORTAL ENROLLMENT — API HANDOFF PLACEHOLDER
# =====================================================================
# There is no Bicep/Terraform-native "join NIOS-X to the Portal" resource; in
# most deployments the host self-enrolls from custom_data above, and any Portal-
# side configuration (DNS/DHCP service assignment, host groups) is done through
# the Infoblox Portal (CSP) REST API or the Infoblox CSP Terraform provider.
#
# This null_resource is the explicit SEAM for that handoff. Replace the local-
# exec sketch with a real CSP API call (curl/az rest/SDK) or a provider resource.
# It is triggered per host and re-runs if the host id changes.
resource "null_resource" "portal_enroll" {
  count = local.uddi_member_count

  triggers = {
    host_id      = azurerm_linux_virtual_machine.niosx[count.index].id
    portal_url   = var.infoblox_portal_url
    # token value intentionally NOT put in triggers (would leak into state diff)
  }

  # Guard: never let this path run unacknowledged, even if reached directly.
  lifecycle {
    precondition {
      condition     = var.acknowledge_saas_boundary
      error_message = "Portal enrollment requires acknowledge_saas_boundary=true (SaaS control plane is outside the boundary — contract §1)."
    }
  }

  provisioner "local-exec" {
    # >>> API HANDOFF <<< illustrative only. In reality you would:
    #   1) confirm the host registered (poll the CSP inventory API), and
    #   2) assign it to a DNS/DHCP service + host group.
    # Pass the join token via env, not argv, so it isn't captured in logs.
    interpreter = ["/bin/bash", "-c"]
    environment = {
      CSP_URL    = var.infoblox_portal_url
      JOIN_TOKEN = data.azurerm_key_vault_secret.saas_join_token[0].value
      HOST_NAME  = azurerm_linux_virtual_machine.niosx[count.index].name
    }
    command = <<-EOC
      echo "[PLACEHOLDER] Would confirm Portal enrollment of $HOST_NAME at $CSP_URL"
      echo "[PLACEHOLDER] Replace with a real CSP REST call, e.g.:"
      echo "  curl -sS -H 'Authorization: Token '\"$JOIN_TOKEN\" \\"
      echo "       $CSP_URL/api/infra/v1/hosts?_filter=display_name=='$HOST_NAME'"
      # Real handoff options:
      #   * Infoblox CSP/BloxOne Terraform provider resources, or
      #   * az rest / curl against csp.infoblox.com, or
      #   * an Ansible play invoked here.
    EOC
  }

  depends_on = [terraform_data.boundary_guard]
}
