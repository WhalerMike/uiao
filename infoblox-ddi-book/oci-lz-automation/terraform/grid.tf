# grid.tf
# ---------------------------------------------------------------------------
# vNIOS GRID path (deployment_model = "grid").
# Boundary-clean: the Grid control plane stays INSIDE the tenancy/ATO boundary.
#
# Creates, gated on local.is_grid:
#   * oci_core_image (optional)   — CUSTOM-IMAGE IMPORT from Object Storage, when
#                                    import_image=true (OCI has NO Marketplace
#                                    vNIOS listing — see the note below).
#   * oci_core_instance           — member_count members, spread across ADs/FDs,
#                                    first-boot config via metadata user_data
#                                    (vNIOS user-data: temp_license + default admin
#                                    password + grid-join params from OCI Vault)
#   * oci_core_volume (+attach)   — optional vNIOS data block volume per model spec
#
# All resources here have count = 0 when deployment_model = "universal_ddi".
#
# DO NOT hard-code an image OCID or a shape — both come from variables
# (vnios_image_ocid / vnios_shape / vnios_ocpus / vnios_memory_gbs).
# ---------------------------------------------------------------------------

locals {
  grid_member_count = local.is_grid ? var.member_count : 0

  # Effective image OCID: the module-imported custom image if import_image=true,
  # otherwise the pre-imported OCID you supply in vnios_image_ocid.
  effective_image_ocid = var.import_image ? try(oci_core_image.vnios[0].id, null) : var.vnios_image_ocid

  # NSG list attached per-VNIC when security_model="nsg"; empty for the
  # security-list model (rules ride on the subnet's Security List instead).
  member_nsg_ids = local.use_nsg ? [oci_core_network_security_group.ddi[0].id] : []

  # vNIOS first-boot user-data ("#infoblox-config" YAML), passed as metadata
  # user_data (base64) and consumed on first boot to: install the temp license,
  # set the default admin password, and join the Grid over 1194/udp + 2114/tcp.
  # Secrets come from OCI Vault (main.tf) and are NEVER committed. The exact
  # schema is NIOS-version dependent — verify against the vNIOS-for-OCI guide.
  grid_user_data = local.is_grid ? {
    for i in local.member_indexes : i => <<-EOT
      #infoblox-config

      temp_license: ${local.temp_license_value}
      default_admin_password: ${local.admin_password_value}
      remote_console_enabled: y

      # Grid-join parameters. For the usual OCI pattern the Grid Master lives
      # on-prem (grid_master_vip), reached over FastConnect/IPSec via the DRG;
      # the OCI members join as Grid members. If grid_master_vip is null the
      # first member is treated as the Grid Master (lab/greenfield only).
      %{if var.grid_master_vip != null~}
      gridmaster:
        ip_addr: ${var.grid_master_vip}
        grid_name: ${var.grid_name}
        shared_secret: ${local.grid_shared_value}
      %{else~}
      # This member (index ${i}) initializes the Grid as Grid Master:
      gridmaster:
        grid_name: ${var.grid_name}
        shared_secret: ${local.grid_shared_value}
      %{endif~}
    EOT
  } : {}
}

# =====================================================================
# CUSTOM-IMAGE IMPORT — no Marketplace listing on OCI.
# =====================================================================
# OCI has no first-class Marketplace vNIOS image. You obtain the vNIOS OCI image
# (qcow2/VMDK) from Infoblox Support, upload it to an Object Storage bucket, and
# import it as a reusable custom image. This module can drive that import when
# import_image=true; otherwise supply a pre-imported vnios_image_ocid.
#
# CLI equivalent / handoff:
#   oci os object put -bn <bucket> --file vnios-<ver>.qcow2 --name vnios-<ver>.qcow2
#   oci compute image import from-object -c <compartment> \
#     --namespace <ns> --bucket-name <bucket> --name vnios-<ver>.qcow2 \
#     --source-image-type QCOW2 --launch-mode PARAVIRTUALIZED \
#     --display-name ddi-vnios-<ver>
resource "oci_core_image" "vnios" {
  # Not gated on deployment_model — both grid and universal_ddi launch from the
  # same imported custom image (local.effective_image_ocid).
  count          = var.import_image ? 1 : 0
  compartment_id = var.network_compartment_ocid
  display_name   = "${var.name_prefix}-vnios-image"
  launch_mode    = "PARAVIRTUALIZED"
  freeform_tags  = local.freeform_tags

  image_source_details {
    source_type       = "objectStorageUri"
    source_uri        = var.image_source_uri # supply your own; see variables.tf
    source_image_type = "QCOW2"              # or "VMDK" per the image you received
  }

  lifecycle {
    precondition {
      condition     = !var.import_image || var.image_source_uri != null
      error_message = "import_image=true requires image_source_uri (Object Storage URI of the uploaded vNIOS qcow2/VMDK)."
    }
  }
}

# =====================================================================
# vNIOS member instances — spread across ADs / FDs.
# =====================================================================
resource "oci_core_instance" "grid" {
  count               = local.grid_member_count
  availability_domain = local.member_ad_for[count.index]
  fault_domain        = local.member_fd_for[count.index]
  compartment_id      = var.network_compartment_ocid
  display_name        = "${local.member_base_name}-${local.member_label[count.index]}"
  shape               = var.vnios_shape

  shape_config {
    ocpus         = var.vnios_ocpus
    memory_in_gbs = var.vnios_memory_gbs
  }

  # Primary service VNIC on the DDI subnet. Add a second VNIC (below, commented)
  # if you separate MGMT (LAN0) from the service/LAN1 interface.
  create_vnic_details {
    subnet_id        = oci_core_subnet.ddi.id
    assign_public_ip = false
    nsg_ids          = local.member_nsg_ids
    display_name     = "lan1"
    hostname_label   = "${var.name_prefix}-vnios-${count.index + 1}"
  }

  source_details {
    source_type = "image"
    source_id   = local.effective_image_ocid
  }

  # First-boot vNIOS configuration + an ephemeral SSH key so OCI's metadata
  # contract is satisfied. vNIOS' own admin account comes from OCI Vault via
  # user_data; SSH is not the admin path.
  metadata = {
    user_data           = base64encode(local.grid_user_data[count.index])
    ssh_authorized_keys = tls_private_key.vnios_placeholder[0].public_key_openssh
  }

  # Paravirtualized launch matches the PARAVIRTUALIZED import mode above.
  launch_options {
    boot_volume_type        = "PARAVIRTUALIZED"
    network_type            = "PARAVIRTUALIZED"
    is_pv_encryption_in_transit_enabled = true
  }

  freeform_tags = local.freeform_tags
  defined_tags  = var.defined_tags

  lifecycle {
    # user_data changes would force replacement; ignore post-bootstrap so a
    # Vault secret rotation doesn't silently recreate running members. Remove
    # this if you WANT re-bootstrap on user-data change.
    ignore_changes = [metadata["user_data"]]

    precondition {
      condition     = local.effective_image_ocid != null
      error_message = "No vNIOS image OCID available: set vnios_image_ocid (pre-imported) OR import_image=true with image_source_uri."
    }
  }
}

# --- Optional vNIOS data block volume (per the model's disk requirement) ----
# The vNIOS DB/reporting disk. Sized by data_volume_size_gbs; skipped when 0.
resource "oci_core_volume" "vnios_data" {
  count               = local.grid_member_count > 0 && var.data_volume_size_gbs > 0 ? var.member_count : 0
  availability_domain = local.member_ad_for[count.index]
  compartment_id      = var.network_compartment_ocid
  display_name        = "${local.member_base_name}-${local.member_label[count.index]}-data"
  size_in_gbs         = var.data_volume_size_gbs
  freeform_tags       = local.freeform_tags
}

resource "oci_core_volume_attachment" "vnios_data" {
  count           = local.grid_member_count > 0 && var.data_volume_size_gbs > 0 ? var.member_count : 0
  attachment_type = "paravirtualized"
  instance_id     = oci_core_instance.grid[count.index].id
  volume_id       = oci_core_volume.vnios_data[count.index].id
}

# Ephemeral SSH key so OCI's metadata contract is satisfied without committing a
# key. vNIOS' own admin comes from OCI Vault.
resource "tls_private_key" "vnios_placeholder" {
  count     = local.grid_member_count > 0 ? 1 : 0
  algorithm = "RSA"
  rsa_bits  = 4096
}
