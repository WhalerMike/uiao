# universal_ddi.tf
# ---------------------------------------------------------------------------
# UNIVERSAL DDI (SaaS) path (deployment_model = "universal_ddi").
#
# BOUNDARY WARNING: this path enrolls lightweight NIOS-X hosts into the Infoblox
# Portal (CSP), whose control plane is SaaS and sits OUTSIDE the SDDC / ATO /
# FedRAMP-Moderate boundary. It requires OUTBOUND 443 to the Portal (firewall.tf
# Allow-InfobloxPortal-Out) and is HARD-GATED behind acknowledge_saas_boundary=true
# (main.tf boundary_guard). On a sovereign / air-gapped VCF this egress is often
# disallowed — prefer the grid path. Do not enable without the authorization
# review (contract §1).
#
# Creates, gated on local.is_uddi:
#   * vsphere_virtual_machine (ovf_deploy) — member_count NIOS-X hosts from the
#                                            OVA/OVF, VMXNET3, across esxi_hosts.
#   * null_resource (local-exec)           — PORTAL ENROLLMENT HANDOFF placeholder:
#                                            confirm each host joined the Portal
#                                            with the join token. The API seam —
#                                            swap for the real CSP REST call.
#
# All resources here have count = 0 when deployment_model = "grid".
# ---------------------------------------------------------------------------

locals {
  uddi_member_count = local.is_uddi ? var.member_count : 0

  # NIOS-X first-boot OVF vApp properties. The join token (from Vault/CI) enrolls
  # the host into the Portal over outbound 443. Property KEYS are release-specific
  # — verify against the current NIOS-X / Infoblox Cloud Services docs and your
  # .ova's OVF descriptor.
  uddi_vapp_properties = {
    for i in local.member_indexes : i => {
      "default_admin_password" = var.admin_password
      "remote_console_enabled" = "True"
      "lan1-v4_addr"           = try(var.member_ip_addresses[i], "")
      "lan1-v4_netmask"        = coalesce(var.member_netmask, "")
      "lan1-v4_gw"             = coalesce(var.member_gateway, "")
      # Portal (CSP) enrollment: the host phones home to infoblox_portal_url over
      # 443 and registers using the join token.
      "join_token" = var.saas_join_token
      "csp_url"    = var.infoblox_portal_url
    }
  }
}

# --- Content-library lookups (NIOS-X image) ----------------------------------
data "vsphere_content_library" "niosx_lib" {
  count = local.is_uddi && try(var.vnios_ovf.content_library, null) != null ? 1 : 0
  name  = var.vnios_ovf.content_library
}

data "vsphere_content_library_item" "niosx" {
  count      = local.is_uddi && try(var.vnios_ovf.content_library_item, null) != null ? 1 : 0
  name       = var.vnios_ovf.content_library_item
  type       = "ovf"
  library_id = data.vsphere_content_library.niosx_lib[0].id
}

# --- NIOS-X host VMs ---------------------------------------------------------
resource "vsphere_virtual_machine" "niosx" {
  count            = local.uddi_member_count
  name             = "${local.niosx_base_name}-${count.index + 1}"
  resource_pool_id = data.vsphere_resource_pool.pool.id
  datastore_id     = data.vsphere_datastore.ds.id

  host_system_id = length(var.esxi_hosts) > 0 ? data.vsphere_host.hosts[local.member_host_for[count.index]].id : null

  num_cpus = var.vnios_num_cpus
  memory   = var.vnios_memory_mb

  network_interface {
    network_id   = data.vsphere_network.mgmt.id
    adapter_type = "vmxnet3"
  }

  ovf_deploy {
    allow_unverified_ssl_cert = var.allow_unverified_ssl
    content_library_item_id   = try(var.vnios_ovf.content_library_item, null) != null ? data.vsphere_content_library_item.niosx[0].id : null
    local_ovf_path            = try(var.vnios_ovf.local_ovf_path, null)
    deployment_option         = try(var.vnios_ovf.deployment_option, var.vnios_appliance_model)
    disk_provisioning         = var.disk_thin_provisioned ? "thin" : "eagerZeroedThick"

    ovf_network_map = {
      "lan1" = data.vsphere_network.mgmt.id
    }
  }

  vapp {
    properties = local.uddi_vapp_properties[count.index]
  }

  lifecycle {
    ignore_changes = [vapp]
  }

  tags = [for t in vsphere_tag.ddi : t.id]

  depends_on = [terraform_data.boundary_guard]
}

# --- DRS anti-affinity for NIOS-X hosts (keep the pair on separate hosts) -----
resource "vsphere_compute_cluster_anti_affinity_rule" "niosx" {
  count               = local.uddi_member_count >= 2 ? 1 : 0
  name                = "${var.name_prefix}-niosx-anti-affinity"
  compute_cluster_id  = data.vsphere_compute_cluster.cluster.id
  virtual_machine_ids = vsphere_virtual_machine.niosx[*].id
  enabled             = true
  mandatory           = true
}

# =====================================================================
# PORTAL ENROLLMENT — API HANDOFF PLACEHOLDER
# =====================================================================
# There is no Terraform-native "join NIOS-X to the Portal" resource; in most
# deployments the host self-enrolls from the vApp join_token above, and any
# Portal-side configuration (DNS/DHCP service assignment, host groups) is done
# through the Infoblox Portal (CSP) REST API or the Infoblox CSP Terraform
# provider.
#
# This null_resource is the explicit SEAM for that handoff. Replace the local-
# exec sketch with a real CSP API call (curl/SDK) or a provider resource.
resource "null_resource" "portal_enroll" {
  count = local.uddi_member_count

  triggers = {
    host_id    = vsphere_virtual_machine.niosx[count.index].id
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
      JOIN_TOKEN = var.saas_join_token
      HOST_NAME  = vsphere_virtual_machine.niosx[count.index].name
    }
    command = <<-EOC
      echo "[PLACEHOLDER] Would confirm Portal enrollment of $HOST_NAME at $CSP_URL"
      echo "[PLACEHOLDER] Replace with a real CSP REST call, e.g.:"
      echo "  curl -sS -H 'Authorization: Token '\"$JOIN_TOKEN\" \\"
      echo "       \"$CSP_URL/api/infra/v1/hosts?_filter=display_name=='$HOST_NAME'\""
      # Real handoff options:
      #   * Infoblox CSP/BloxOne Terraform provider resources, or
      #   * curl against the Portal (csp.infoblox.com), or
      #   * an Ansible play invoked here.
    EOC
  }

  depends_on = [terraform_data.boundary_guard]
}
