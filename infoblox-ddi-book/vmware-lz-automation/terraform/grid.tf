# grid.tf
# ---------------------------------------------------------------------------
# vNIOS GRID path (deployment_model = "grid").
# Boundary-clean: the Grid control plane stays INSIDE the SDDC / ATO boundary.
#
# Creates, gated on local.is_grid:
#   * vsphere_virtual_machine (ovf_deploy)  — member_count members from the vNIOS
#                                              OVA/OVF (content library or local),
#                                              VMXNET3, thick/thin disk, spread
#                                              across esxi_hosts. First-boot config
#                                              (temp license + admin pw + static IP
#                                              + grid-join) via OVF vApp properties.
#   * vsphere_compute_cluster_anti_affinity_rule — keep the HA pair on separate
#                                              ESXi hosts (contract §9).
#
# All resources here have count = 0 when deployment_model = "universal_ddi".
#
# DO NOT hard-code the OVA build or appliance model — both come from variables
# (vnios_ovf / vnios_appliance_model). Download the .ova for your NIOS release
# from the Infoblox support/download portal; supply your own model/size.
# ---------------------------------------------------------------------------

locals {
  grid_member_count = local.is_grid ? var.member_count : 0

  # vNIOS first-boot OVF vApp properties. These are consumed by the appliance on
  # first boot to: install the temp license, set the admin password, apply the
  # static management IP, and (member) join the Grid to the Grid Master over
  # 1194/udp + 2114/tcp. Secrets come from Vault/CI (var.*, sensitive) and are
  # NEVER committed. The exact PROPERTY KEYS are OVA/NIOS-version dependent —
  # verify against the "vNIOS for VMware" install guide / your .ova's OVF
  # descriptor before relying on them.
  grid_vapp_properties = {
    for i in local.member_indexes : i => merge(
      {
        "default_admin_password" = var.admin_password
        "temp_license"           = var.temp_license
        "remote_console_enabled" = "True"
        # Static management addressing (from member_ip_addresses etc.).
        "lan1-v4_addr"    = try(var.member_ip_addresses[i], "")
        "lan1-v4_netmask" = coalesce(var.member_netmask, "")
        "lan1-v4_gw"      = coalesce(var.member_gateway, "")
      },
      # Grid-join parameters. Usual pattern: an existing GM (grid_master_vip);
      # the members join as Grid members. If grid_master_vip is null the first
      # member is treated as the Grid Master (lab/greenfield only).
      var.grid_master_vip != null ? {
        "gridmaster_ip"            = var.grid_master_vip
        "grid_name"                = var.grid_name
        "gridmaster_shared_secret" = var.grid_shared_secret
      } : {
        "grid_name"                = var.grid_name
        "gridmaster_shared_secret" = var.grid_shared_secret
      }
    )
  }
}

# --- Content-library lookups (when deploying from a content library) ---------
data "vsphere_content_library" "lib" {
  count = local.is_grid && try(var.vnios_ovf.content_library, null) != null ? 1 : 0
  name  = var.vnios_ovf.content_library
}

data "vsphere_content_library_item" "vnios" {
  count      = local.is_grid && try(var.vnios_ovf.content_library_item, null) != null ? 1 : 0
  name       = var.vnios_ovf.content_library_item
  type       = "ovf"
  library_id = data.vsphere_content_library.lib[0].id
}

# --- vNIOS member VMs (OVA/OVF deploy) ---------------------------------------
resource "vsphere_virtual_machine" "grid" {
  count            = local.grid_member_count
  name             = "${local.member_base_name}-${local.member_label[count.index]}"
  resource_pool_id = data.vsphere_resource_pool.pool.id
  datastore_id     = data.vsphere_datastore.ds.id

  # Explicit host placement for anti-affinity when esxi_hosts is provided;
  # otherwise leave to DRS (the anti-affinity rule below still separates them).
  host_system_id = length(var.esxi_hosts) > 0 ? data.vsphere_host.hosts[local.member_host_for[count.index]].id : null

  # Sizing overrides (model-dependent). Leave null to inherit the OVA/model
  # defaults selected via vnios_ovf.deployment_option / vnios_appliance_model.
  num_cpus = var.vnios_num_cpus
  memory   = var.vnios_memory_mb

  # VMXNET3 vNIC on the management port group (contract §9). The OVA default is
  # VMXNET3; adapter_type is set explicitly so it is never silently E1000.
  network_interface {
    network_id   = data.vsphere_network.mgmt.id
    adapter_type = "vmxnet3"
  }

  # Deploy from the vNIOS OVA/OVF — content-library item OR local path.
  ovf_deploy {
    allow_unverified_ssl_cert = var.allow_unverified_ssl
    content_library_item_id   = try(var.vnios_ovf.content_library_item, null) != null ? data.vsphere_content_library_item.vnios[0].id : null
    local_ovf_path            = try(var.vnios_ovf.local_ovf_path, null)
    deployment_option         = try(var.vnios_ovf.deployment_option, var.vnios_appliance_model)
    disk_provisioning         = var.disk_thin_provisioned ? "thin" : "eagerZeroedThick"

    # Map the OVA's network(s) to the management port group. The OVA network
    # label ("lan1"/"LAN1"/"Network 1") is OVA-specific — verify and adjust.
    ovf_network_map = {
      "lan1" = data.vsphere_network.mgmt.id
    }
  }

  # First-boot vNIOS configuration via OVF vApp properties (license + admin pw
  # + static IP + grid join). Property KEYS are OVA-version specific — verify.
  vapp {
    properties = local.grid_vapp_properties[count.index]
  }

  lifecycle {
    # vApp property changes would force replacement; ignore post-bootstrap so a
    # secret rotation in Vault/CI doesn't silently recreate running members.
    # Remove this if you WANT re-bootstrap on property change.
    ignore_changes = [vapp]
  }

  # vSphere tags (contract §6) — the module-managed labels defined in main.tf.
  tags = [for t in vsphere_tag.ddi : t.id]

  depends_on = [terraform_data.boundary_guard]
}

# --- DRS VM-VM anti-affinity: keep the HA pair on separate ESXi hosts --------
# Requires >=2 members; contract §9. A single-member (lab) deploy skips it.
resource "vsphere_compute_cluster_anti_affinity_rule" "ddi" {
  count               = local.grid_member_count >= 2 ? 1 : 0
  name                = "${var.name_prefix}-anti-affinity"
  compute_cluster_id  = data.vsphere_compute_cluster.cluster.id
  virtual_machine_ids = vsphere_virtual_machine.grid[*].id
  enabled             = true
  mandatory           = true
}
