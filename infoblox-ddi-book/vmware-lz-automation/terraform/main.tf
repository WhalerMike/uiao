# main.tf
# ---------------------------------------------------------------------------
# Locals, module-managed vSphere tags (contract §6), the Stage-1 SDDC data
# lookups (cluster / resource pool / datastore / port group / hosts), and the
# HARD-FAIL boundary guard for the universal_ddi (SaaS) path.
#
# Resource layout across files:
#   main.tf          — locals, tags, SDDC data sources, boundary precondition
#   firewall.tf      — NSX-T DFW group + rules (contract §4), default-deny
#   grid.tf          — vNIOS Grid members (OVA/OVF)   deployment_model="grid"
#   universal_ddi.tf — NIOS-X hosts + Portal enroll    deployment_model="universal_ddi"
#   discovery.tf     — vCenter read-only role + NSX API user + CNA handoff (§5)
#   dns.tf           — NSX DNS forwarder + AD conditional forwarders + DHCP relay (§8)
#   outputs.tf       — canonical outputs (contract §7)
# ---------------------------------------------------------------------------

locals {
  # --- Naming convention (contract §6): ${name_prefix}-<role>-<host/index> --
  member_base_name = "${var.name_prefix}-vnios" # grid members: ddi-vnios-h1...
  niosx_base_name  = "${var.name_prefix}-niosx" # uddi hosts:   ddi-niosx-1...
  dfw_group_name   = "${var.name_prefix}-mgmt-group"
  disco_role_name  = "${var.name_prefix}-disco-role"

  # --- Model flags ------------------------------------------------------
  is_grid = var.deployment_model == "grid"
  is_uddi = var.deployment_model == "universal_ddi"

  # Round-robin members over the provided ESXi hosts (anti-affinity spread).
  # Index i -> host. If esxi_hosts is empty, host placement is left to DRS and
  # the anti-affinity rule still keeps the pair apart.
  member_indexes = range(var.member_count)
  member_host_for = length(var.esxi_hosts) > 0 ? {
    for i in local.member_indexes :
    i => var.esxi_hosts[i % length(var.esxi_hosts)]
  } : {}

  # Per-member label. One host per member yields the clean ddi-vnios-h1 /
  # ddi-vnios-h2 form (contract §6); if members outnumber hosts, append index.
  member_label = {
    for i in local.member_indexes :
    i => (
      length(var.esxi_hosts) == 0
      ? format("h%d", i + 1)
      : (var.member_count <= length(var.esxi_hosts)
        ? format("h%d", i + 1)
        : format("h%d-%d", (i % length(var.esxi_hosts)) + 1, i))
    )
  }

  # --- Module-managed tags (contract §6) --------------------------------
  # These keys are authoritative; caller tags are merged UNDER them so the
  # governance-relevant keys can't be silently overridden.
  managed_tags = {
    workload           = "infoblox-ddi"
    layer              = "mgmt-domain-ddi"
    compliance_profile = var.compliance_profile
    deployment_model   = var.deployment_model
    managed_by         = "terraform"
    environment        = var.environment
  }
  tags = merge(var.tags, local.managed_tags)
  # vSphere tags are flat labels inside a category; render each pair as "key=value".
  tag_labels = [for k, v in local.tags : "${k}=${v}"]

  # --- DNS server IP handling (contract §7/§8) --------------------------
  # Members get STATIC IPs via OVF vApp properties, so we know them up front
  # (unlike Azure's dynamic NIC IPs). Preferred resolver target is the anycast
  # VIP; fall back to the members' individual IPs (dns_server_ips).
  member_dns_ips       = var.member_ip_addresses
  effective_dns_target = var.ddi_anycast_vip != null ? [var.ddi_anycast_vip] : local.member_dns_ips

  # Grid Master IP (grid only, contract §7). If an existing Grid Master VIP is
  # supplied that is authoritative; otherwise fall back to the first member
  # (lab/greenfield where the first member is the GM).
  grid_master_ip = local.is_grid ? try(
    coalesce(var.grid_master_vip, element(concat(var.member_ip_addresses, [null]), 0)),
    null
  ) : null
}

# ---------------------------------------------------------------------------
# BOUNDARY GUARD (contract §1) — HARD FAIL.
# deployment_model="universal_ddi" routes the control plane through the Infoblox
# Portal (SaaS), which sits OUTSIDE the SDDC/ATO boundary and needs outbound 443.
# That path is only permitted with an explicit acknowledge_saas_boundary=true.
# A precondition on this resource fails the PLAN (not just apply) with a message
# pointing to the authorization review. It ALSO enforces that the model's required
# secret (grid_shared_secret for grid, saas_join_token for uddi) is present.
# ---------------------------------------------------------------------------
resource "terraform_data" "boundary_guard" {
  input = var.deployment_model

  lifecycle {
    precondition {
      condition = !(var.deployment_model == "universal_ddi" && var.acknowledge_saas_boundary == false)
      error_message = join("\n", [
        "BOUNDARY VIOLATION: deployment_model = \"universal_ddi\" selects the Infoblox",
        "Portal (SaaS) control plane, which is OUTSIDE the SDDC / ATO / FedRAMP-Moderate",
        "boundary and requires OUTBOUND 443 to the Infoblox Portal (contract §1). On a",
        "sovereign / air-gapped VCF this egress is frequently disallowed.",
        "",
        "This path is disabled until it is explicitly authorized. To proceed you MUST:",
        "  1. Complete the FedRAMP/authorization review for the SaaS control-plane egress,",
        "     and confirm the Portal SaaS offering's authorization status is acceptable",
        "     for this system's boundary; then",
        "  2. Set  acknowledge_saas_boundary = true.",
        "",
        "For a boundary-clean deployment, use deployment_model = \"grid\" (the default),",
        "which keeps the vNIOS Grid control plane INSIDE the SDDC (the natural VMware fit).",
      ])
    }

    precondition {
      condition     = !local.is_grid || var.grid_shared_secret != null
      error_message = "deployment_model='grid' requires grid_shared_secret (inject from Vault/CI) to join the members to the Grid."
    }

    precondition {
      condition     = !local.is_uddi || var.saas_join_token != null
      error_message = "deployment_model='universal_ddi' requires saas_join_token (inject from Vault/CI) to enroll NIOS-X to the Portal."
    }

    # Member static-IP count must match member_count when supplied.
    precondition {
      condition     = length(var.member_ip_addresses) == 0 || length(var.member_ip_addresses) == var.member_count
      error_message = "member_ip_addresses, when set, must contain exactly member_count entries (one static IP per member)."
    }
  }
}

# ---------------------------------------------------------------------------
# Stage-1 SDDC lookups. These READ existing vSphere/NSX inventory (the VCF
# management/edge domain) — the module never creates the datacenter, cluster,
# datastore, or port group. Maps the Azure "consume Stage-1 hub outputs" pattern.
# ---------------------------------------------------------------------------
data "vsphere_datacenter" "dc" {
  name = var.vsphere_datacenter
}

data "vsphere_compute_cluster" "cluster" {
  name          = var.compute_cluster
  datacenter_id = data.vsphere_datacenter.dc.id
}

data "vsphere_resource_pool" "pool" {
  # If no resource_pool given, fall back to the cluster's root pool ("<cluster>/Resources").
  name          = coalesce(var.resource_pool, "${var.compute_cluster}/Resources")
  datacenter_id = data.vsphere_datacenter.dc.id
}

data "vsphere_datastore" "ds" {
  name          = var.datastore
  datacenter_id = data.vsphere_datacenter.dc.id
}

data "vsphere_network" "mgmt" {
  name          = var.management_portgroup
  datacenter_id = data.vsphere_datacenter.dc.id
}

# ESXi hosts for explicit per-member placement (anti-affinity). Only looked up
# when esxi_hosts is provided; otherwise DRS places the VMs and the anti-affinity
# rule still enforces host separation.
data "vsphere_host" "hosts" {
  for_each      = toset(var.esxi_hosts)
  name          = each.value
  datacenter_id = data.vsphere_datacenter.dc.id
}

# ---------------------------------------------------------------------------
# vSphere tags (contract §6) applied to the member VMs. One category holds the
# module-managed labels ("workload=infoblox-ddi", etc.) plus any caller tags.
# ---------------------------------------------------------------------------
resource "vsphere_tag_category" "ddi" {
  name        = "${var.name_prefix}-managed"
  cardinality = "MULTIPLE"
  associable_types = ["VirtualMachine"]
}

resource "vsphere_tag" "ddi" {
  for_each    = toset(local.tag_labels)
  name        = each.value
  category_id = vsphere_tag_category.ddi.id
}
