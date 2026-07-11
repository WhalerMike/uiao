# grid.tf
# ---------------------------------------------------------------------------
# vNIOS GRID path (deployment_model = "grid").
# Boundary-clean: the Grid control plane stays INSIDE the tenant/ATO boundary.
#
# Creates, gated on local.is_grid:
#   * azurerm_marketplace_agreement  — accept the vNIOS Marketplace plan terms
#   * azurerm_network_interface      — one NIC per member on the DDI subnet
#   * azurerm_linux_virtual_machine  — member_count members, spread across zones,
#                                       first-boot config via custom_data (vNIOS
#                                       user-data: temp_license + default admin
#                                       password + grid-join params from Key Vault)
#
# All resources here have count = 0 when deployment_model = "universal_ddi".
#
# DO NOT hard-code the image version or VM SKU — both come from variables
# (vnios_image / vnios_vm_sku). Discover the current plan with:
#   az vm image list --publisher infoblox --all -o table
# ---------------------------------------------------------------------------

locals {
  grid_member_count = local.is_grid ? var.member_count : 0

  # Marketplace plan name defaults to the image sku when not explicitly set.
  vnios_plan_name = coalesce(try(var.vnios_image.plan_name, null), var.vnios_image.sku)

  # vNIOS first-boot user-data ("#infoblox-config" YAML). This is passed as
  # custom_data (base64) and consumed by the appliance on first boot to:
  #   - install the temporary license bundle,
  #   - set the default admin password, and
  #   - (member) join the Grid to the Grid Master over 1194/udp + 2114/tcp.
  # Secrets are pulled from Key Vault (see main.tf data sources) and NEVER
  # committed. The exact schema is NIOS-version dependent — verify against the
  # "vNIOS for Azure" deployment guide for your build before relying on it.
  grid_user_data = local.is_grid ? {
    for i in local.member_indexes : i => <<-EOT
      #infoblox-config

      temp_license: ${data.azurerm_key_vault_secret.temp_license.value}
      default_admin_password: ${data.azurerm_key_vault_secret.admin_password.value}
      remote_console_enabled: y

      # Grid-join parameters. For the usual Azure pattern the Grid Master lives
      # on-prem (grid_master_vip); the Azure members join as Grid members. If
      # grid_master_vip is null the first member is treated as the Grid Master
      # (lab/greenfield only).
      %{if var.grid_master_vip != null~}
      gridmaster:
        ip_addr: ${var.grid_master_vip}
        grid_name: ${var.grid_name}
        shared_secret: ${data.azurerm_key_vault_secret.grid_shared_secret[0].value}
      %{else~}
      # This member (index ${i}) initializes the Grid as Grid Master:
      gridmaster:
        grid_name: ${var.grid_name}
        shared_secret: ${data.azurerm_key_vault_secret.grid_shared_secret[0].value}
      %{endif~}
    EOT
  } : {}
}

# --- Marketplace agreement --------------------------------------------
# Accept the plan terms so the VM can deploy the Marketplace image. Safe to
# leave enabled; if the agreement is already accepted subscription-wide, set
# accept_marketplace_agreement=false to skip managing it here.
resource "azurerm_marketplace_agreement" "vnios" {
  count     = local.is_grid && var.accept_marketplace_agreement ? 1 : 0
  publisher = var.vnios_image.publisher
  offer     = var.vnios_image.offer
  plan      = local.vnios_plan_name
}

# --- Member NICs on the DDI subnet ------------------------------------
resource "azurerm_network_interface" "grid" {
  count                          = local.grid_member_count
  name                           = "${local.member_base_name}-${local.member_label[count.index]}-nic"
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

# --- vNIOS member VMs --------------------------------------------------
# Spread across availability_zones via local.member_zone_for. Premium LRS OS
# disk per ../01-azure.md §4 sizing guidance (add a separate data disk for the
# NIOS database / reporting members in a real deployment).
resource "azurerm_linux_virtual_machine" "grid" {
  count               = local.grid_member_count
  name                = "${local.member_base_name}-${local.member_label[count.index]}"
  computer_name       = "${local.member_base_name}-${local.member_label[count.index]}"
  location            = var.location
  resource_group_name = var.hub_resource_group_name
  size                = var.vnios_vm_sku
  zone                = local.member_zone_for[count.index]
  admin_username      = var.admin_username
  tags                = local.tags

  network_interface_ids = [azurerm_network_interface.grid[count.index].id]

  # vNIOS is administered via its own admin account + user-data, not SSH keys,
  # but Azure's Linux VM contract requires either a key or password auth to be
  # configured. We attach an ephemeral key so password auth can stay disabled;
  # the appliance's own admin password comes from Key Vault via custom_data.
  disable_password_authentication = true
  admin_ssh_key {
    username   = var.admin_username
    public_key = tls_private_key.vnios_placeholder[0].public_key_openssh
  }

  # First-boot vNIOS configuration (temp_license + admin pw + grid join).
  custom_data = base64encode(local.grid_user_data[count.index])

  os_disk {
    name                 = "${local.member_base_name}-${local.member_label[count.index]}-osdisk"
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
  }

  # Marketplace image — publisher/offer/sku/version come from vnios_image.
  # NEVER hard-code the version; "latest" or a pinned build is supplied by var.
  source_image_reference {
    publisher = var.vnios_image.publisher
    offer     = var.vnios_image.offer
    sku       = var.vnios_image.sku
    version   = var.vnios_image.version
  }

  # Marketplace VMs require a matching plan block.
  plan {
    name      = local.vnios_plan_name
    publisher = var.vnios_image.publisher
    product   = var.vnios_image.offer
  }

  # Ensure the Marketplace terms are accepted before the VM is created.
  depends_on = [azurerm_marketplace_agreement.vnios]

  lifecycle {
    # custom_data changes would force replacement; ignore post-bootstrap so a
    # secret rotation in Key Vault doesn't silently recreate running members.
    # Remove this if you WANT re-bootstrap on user-data change.
    ignore_changes = [custom_data]
  }
}

# Ephemeral SSH key so we can keep password auth disabled on the Azure VM
# object without committing a key. vNIOS' own admin comes from Key Vault.
resource "tls_private_key" "vnios_placeholder" {
  count     = local.grid_member_count > 0 ? 1 : 0
  algorithm = "RSA"
  rsa_bits  = 4096
}
