# universal_ddi.tf
# ---------------------------------------------------------------------------
# UNIVERSAL DDI (SaaS) path (deployment_model = "universal_ddi").
#
# BOUNDARY WARNING: this path enrolls lightweight NIOS-X hosts into the Infoblox
# Portal (CSP), whose control plane is SaaS and sits OUTSIDE the ATO/FedRAMP-
# Moderate boundary. It requires OUTBOUND 443 to the Portal (security.tf
# out_portal_sync) and is HARD-GATED behind acknowledge_saas_boundary=true
# (main.tf boundary_guard). Do not enable without completing the authorization
# review (contract §1). In OCI Government / National-Security realms the Portal
# is typically unreachable — use the grid path there.
#
# Creates, gated on local.is_uddi:
#   * oci_core_instance      — member_count NIOS-X hosts, spread across ADs/FDs,
#                              from the SAME imported custom image (no Marketplace)
#   * null_resource          — PORTAL ENROLLMENT HANDOFF placeholder: joins each
#                              host to the Portal with the join token. This is the
#                              API seam — swap for the real CSP REST call / provider.
#
# All resources here have count = 0 when deployment_model = "grid".
# ---------------------------------------------------------------------------

locals {
  uddi_member_count = local.is_uddi ? var.member_count : 0

  # NIOS-X first-boot user-data. The join token (from OCI Vault) enrolls the host
  # into the Portal over outbound 443. Exact schema is release-dependent — verify
  # against the current NIOS-X / Infoblox Cloud Services docs.
  uddi_user_data = local.is_uddi ? <<-EOT
    #infoblox-config

    default_admin_password: ${local.admin_password_value}
    remote_console_enabled: y

    # Portal (CSP) enrollment. The host phones home to infoblox_portal_url over
    # 443 and registers using the join token.
    join_token: ${local.saas_join_value}
    csp_host: ${var.infoblox_portal_url}
  EOT
  : null
}

# --- NIOS-X host instances — spread across ADs / FDs ------------------
resource "oci_core_instance" "niosx" {
  count               = local.uddi_member_count
  availability_domain = local.member_ad_for[count.index]
  fault_domain        = local.member_fd_for[count.index]
  compartment_id      = var.network_compartment_ocid
  display_name        = "${local.niosx_base_name}-${count.index + 1}"
  shape               = var.vnios_shape

  shape_config {
    ocpus         = var.vnios_ocpus
    memory_in_gbs = var.vnios_memory_gbs
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.ddi.id
    assign_public_ip = false
    nsg_ids          = local.member_nsg_ids
    display_name     = "lan1"
    hostname_label   = "${var.name_prefix}-niosx-${count.index + 1}"
  }

  source_details {
    source_type = "image"
    source_id   = local.effective_image_ocid # same imported custom image as grid
  }

  metadata = {
    user_data           = base64encode(local.uddi_user_data)
    ssh_authorized_keys = tls_private_key.niosx_placeholder[0].public_key_openssh
  }

  launch_options {
    boot_volume_type                    = "PARAVIRTUALIZED"
    network_type                        = "PARAVIRTUALIZED"
    is_pv_encryption_in_transit_enabled = true
  }

  freeform_tags = local.freeform_tags
  defined_tags  = var.defined_tags

  lifecycle {
    ignore_changes = [metadata["user_data"]]

    precondition {
      condition     = local.effective_image_ocid != null
      error_message = "No NIOS-X image OCID available: set vnios_image_ocid (pre-imported) OR import_image=true with image_source_uri."
    }
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
# There is no Terraform-native "join NIOS-X to the Portal" resource; in most
# deployments the host self-enrolls from user_data above, and any Portal-side
# configuration (DNS/DHCP service assignment, host groups) is done through the
# Infoblox Portal (CSP) REST API or the Infoblox CSP Terraform provider.
#
# This null_resource is the explicit SEAM for that handoff. Replace the local-
# exec sketch with a real CSP API call (curl/SDK) or a provider resource.
resource "null_resource" "portal_enroll" {
  count = local.uddi_member_count

  triggers = {
    host_id    = oci_core_instance.niosx[count.index].id
    portal_url = var.infoblox_portal_url
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
    # NOTE: endpoints use no https:// scheme here; the scheme is added at runtime.
    interpreter = ["/bin/bash", "-c"]
    environment = {
      CSP_HOST   = var.infoblox_portal_url
      JOIN_TOKEN = local.saas_join_value
      HOST_NAME  = oci_core_instance.niosx[count.index].display_name
    }
    command = <<-EOC
      echo "[PLACEHOLDER] Would confirm Portal enrollment of $HOST_NAME at $CSP_HOST"
      echo "[PLACEHOLDER] Replace with a real CSP REST call, e.g.:"
      echo "  curl -sS -H 'Authorization: Token '\"$JOIN_TOKEN\" \\"
      echo "       \"https://$CSP_HOST/api/infra/v1/hosts?_filter=display_name=='$HOST_NAME'\""
      # Real handoff options:
      #   * Infoblox CSP/BloxOne Terraform provider resources, or
      #   * curl against csp.infoblox.com, or
      #   * an Ansible play invoked here.
    EOC
  }

  depends_on = [terraform_data.boundary_guard]
}
