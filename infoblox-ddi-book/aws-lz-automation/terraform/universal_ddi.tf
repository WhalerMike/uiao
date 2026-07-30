# universal_ddi.tf
# ---------------------------------------------------------------------------
# UNIVERSAL DDI (SaaS) path (deployment_model = "universal_ddi").
#
# BOUNDARY WARNING: this path enrolls lightweight NIOS-X hosts into the Infoblox
# Portal (CSP), whose control plane is SaaS and sits OUTSIDE the ATO/GCC-Moderate
# boundary. It requires OUTBOUND 443 to the Portal (securitygroups.tf egress) and
# is HARD-GATED behind acknowledge_saas_boundary=true (main.tf boundary_guard).
# Do not enable without completing the authorization review (contract §1).
#
# Creates, gated on local.is_uddi:
#   * aws_network_interface  — MGMT + LAN1 ENIs per NIOS-X host on the DDI subnets
#   * aws_instance           — member_count NIOS-X hosts, across AZs
#   * null_resource          — PORTAL ENROLLMENT HANDOFF placeholder: the API seam
#                              that joins each host to the Portal with the join token
#
# All resources here have count = 0 when deployment_model = "grid".
# ---------------------------------------------------------------------------

locals {
  uddi_member_count = local.is_uddi ? var.member_count : 0

  # NIOS-X first-boot user-data. The join token (from Secrets Manager/SSM) enrolls
  # the host into the Portal over outbound 443. Exact schema is release-dependent —
  # verify against the current NIOS-X / Infoblox Cloud Services docs.
  uddi_user_data = local.is_uddi ? (<<-EOT
    #infoblox-config

    default_admin_password: ${local.admin_password}
    remote_console_enabled: y

    # Portal (CSP) enrollment. The host phones home to infoblox_portal_url over
    # 443 and registers using the join token.
    join_token: ${local.saas_join_token}
    csp_url: ${var.infoblox_portal_url}
  EOT
  ) : null
}

# --- MGMT ENIs (ENI0) --------------------------------------------------
resource "aws_network_interface" "niosx_mgmt" {
  count             = local.uddi_member_count
  subnet_id         = aws_subnet.ddi[local.member_zone_for[count.index]].id
  security_groups   = [aws_security_group.ddi.id]
  source_dest_check = true
  description       = "${local.niosx_base_name}-${count.index + 1} MGMT"
  tags              = merge(local.tags, { Name = "${local.niosx_base_name}-${count.index + 1}-mgmt" })
}

# --- LAN1 ENIs (ENI1) --------------------------------------------------
resource "aws_network_interface" "niosx_lan1" {
  count             = local.uddi_member_count
  subnet_id         = aws_subnet.ddi[local.member_zone_for[count.index]].id
  security_groups   = [aws_security_group.ddi.id]
  source_dest_check = var.enable_source_dest_check
  description       = "${local.niosx_base_name}-${count.index + 1} LAN1"
  tags              = merge(local.tags, { Name = "${local.niosx_base_name}-${count.index + 1}-lan1" })
}

# --- NIOS-X host instances ---------------------------------------------
resource "aws_instance" "niosx" {
  count         = local.uddi_member_count
  ami           = var.vnios_ami_id
  instance_type = var.vnios_instance_type
  key_name      = var.ssh_key_name

  iam_instance_profile = local.member_instance_profile_name

  network_interface {
    network_interface_id = aws_network_interface.niosx_mgmt[count.index].id
    device_index         = 0
  }
  network_interface {
    network_interface_id = aws_network_interface.niosx_lan1[count.index].id
    device_index         = 1
  }

  user_data_base64 = base64encode(local.uddi_user_data)

  # SER-2 Fix 1: require IMDSv2 -- see grid.tf's aws_instance.grid for the
  # full rationale (same fix, same reasoning, applied to the NIOS-X host).
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
    instance_metadata_tags      = "disabled"
  }

  root_block_device {
    encrypted   = true
    volume_type = "gp3"
  }

  tags = merge(local.tags, {
    Name = "${local.niosx_base_name}-${count.index + 1}"
    role = "niosx-host"
  })

  lifecycle {
    ignore_changes = [user_data_base64]
  }

  depends_on = [terraform_data.boundary_guard]
}

# =====================================================================
# PORTAL ENROLLMENT — API HANDOFF PLACEHOLDER
# =====================================================================
# There is no Terraform-native "join NIOS-X to the Portal" resource; in most
# deployments the host self-enrolls from user-data above, and any Portal-side
# configuration (DNS/DHCP service assignment, host groups) is done through the
# Infoblox Portal (CSP) REST API or the Infoblox CSP Terraform provider.
#
# This null_resource is the explicit SEAM for that handoff. Replace the local-
# exec sketch with a real CSP API call (curl/SDK) or a provider resource.
resource "null_resource" "portal_enroll" {
  count = local.uddi_member_count

  triggers = {
    host_id    = aws_instance.niosx[count.index].id
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
    interpreter = ["/bin/bash", "-c"]
    environment = {
      CSP_URL    = var.infoblox_portal_url
      JOIN_TOKEN = local.saas_join_token
      HOST_NAME  = aws_instance.niosx[count.index].tags["Name"]
    }
    command = <<-EOC
      echo "[PLACEHOLDER] Would confirm Portal enrollment of $HOST_NAME at $CSP_URL"
      echo "[PLACEHOLDER] Replace with a real CSP REST call, e.g.:"
      echo "  curl -sS -H 'Authorization: Token '\"$JOIN_TOKEN\" \\"
      echo "       $CSP_URL/api/infra/v1/hosts?_filter=display_name=='$HOST_NAME'"
      # Real handoff options:
      #   * Infoblox CSP/BloxOne Terraform provider resources, or
      #   * curl against csp.infoblox.com, or
      #   * an Ansible play invoked here.
    EOC
  }

  depends_on = [terraform_data.boundary_guard]
}
