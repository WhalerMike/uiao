# discovery.tf
# ---------------------------------------------------------------------------
# Least-privilege discovery for vCenter/NSX -> Infoblox IPAM sync (contract §5).
#
# On VMware, discovery is Cloud Network Automation (CNA) connecting to vCenter
# (and NSX Manager). Unlike Azure — where the module CREATES a managed identity
# and role assignments — the credentials here are:
#
#   * a vCenter READ-ONLY service account   (created in vCenter SSO / AD), and
#   * an NSX-T API user with READ on segments/gateways (created in NSX Manager).
#
# Creating those principals is an SSO/AD/NSX task, NOT a Terraform resource. What
# the module CAN optionally do (manage_discovery_role=true) is create a scoped
# read-only vSphere ROLE and grant it to the discovery service account on the
# datacenter — a convenience so the least-privilege intent is captured in code.
#
# The CNA vDiscovery JOB itself (the Infoblox side) is an explicit API/UI HANDOFF:
# there is no first-class provider resource for it. See the note at the bottom.
# ---------------------------------------------------------------------------

# --- (Optional) read-only vSphere role for the discovery SA ------------------
# A minimal read-only role: enumerate clusters, hosts, VMs, port groups, and
# their IPs — enough for CNA to sync the virtual estate into IPAM. NO write.
# The exact privilege ids are vSphere-version specific; "System.*" + "System.Read"
# equivalents give read-only. Adjust to your vCenter's privilege catalog.
resource "vsphere_role" "discovery_readonly" {
  count = var.manage_discovery_role ? 1 : 0
  name  = local.disco_role_name

  # Read-only privilege set. These ids exist across current vSphere releases;
  # confirm against your vCenter (Administration > Roles) before relying on them.
  role_privileges = [
    "System.Anonymous",
    "System.View",
    "System.Read",
  ]
}

# Grant the read-only role to the discovery service account at the datacenter,
# so CNA can enumerate the whole management/edge domain (and workload domains it
# should see) but write nothing.
resource "vsphere_entity_permissions" "discovery" {
  count       = var.manage_discovery_role && var.discovery_vcenter_user != null ? 1 : 0
  entity_id   = data.vsphere_datacenter.dc.id
  entity_type = "Datacenter"

  permissions {
    user_or_group = var.discovery_vcenter_user # e.g. "CORP\\svc-infoblox-disco" or "svc-infoblox-disco@vsphere.local"
    propagate     = true
    is_group      = false
    role_id       = vsphere_role.discovery_readonly[0].id
  }
}

# =====================================================================
# INFOBLOX CLOUD NETWORK AUTOMATION (CNA) DISCOVERY — CONFIG PLACEHOLDER
# =====================================================================
# The vCenter role above scopes the read-only SA; the Infoblox SIDE of discovery
# is configured on the Grid control plane, not in vSphere/NSX. There is no
# first-class "infoblox_vdiscovery_job" resource in the infobloxopen/infoblox
# provider today, so this is an explicit API/UI handoff:
#
#   * vNIOS Grid (deployment_model=grid) -> Cloud Network Automation, a vCenter
#       (VMware) discovery job pointed at vCenter (and NSX Manager), authenticating
#       with the READ-ONLY service account (var.discovery_vcenter_user) and the
#       NSX API user (var.discovery_nsx_user). Configured via WAPI
#       (POST /wapi/vX/vdiscoverytask, member=<cloud-platform member>) or the Grid
#       UI. It discovers clusters/hosts, VMs, port groups/segments, and assigned
#       IPs into Infoblox networks/tenants. See ../05-vmware.md §6.
#   * Universal DDI -> configure a Portal cloud source for vCenter using the same
#       read-only credential; the discovery job lives in the SaaS control plane.
#
# The Infoblox admin used by the adapter needs a CUSTOM admin group with cloud-API
# access and IPAM + DNS + DHCP + Grid (+ Tenant when CNA is licensed) rights
# (contract §5). For NSX to CONSUME Infoblox for IPAM/DNS (the "Register Infoblox
# NIOS DDI with NSX" flow in VCF 9.x), that group also needs Extensible-Attribute
# rights so NSX can create/delete networks, allocate/release IPs, and manage host
# records over WAPI/443.
#
# Sketch of the WAPI handoff (uncomment + wire real values / a restapi provider):
#
# resource "null_resource" "vdiscovery_job" {
#   triggers = { vcenter = var.vsphere_server }
#   provisioner "local-exec" {
#     command = "curl -fsS -u \"$IB_USER:$IB_PASS\" -X POST \\
#       https://$GRID_MASTER/wapi/v2.12/vdiscoverytask \\
#       -d 'name=vmware-disco&member=infoblox.localdomain&credential_type=VMWARE&...' "
#   }
# }
