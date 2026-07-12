# discovery.tf
# ---------------------------------------------------------------------------
# Least-privilege discovery service account for GCP -> Infoblox IPAM sync (§5).
#
# Prefer a module-created SERVICE ACCOUNT (discovery_identity_type =
# "service_account", resource ddi-disco); or bind roles to an existing SA
# (discovery_identity_type = "existing_service_account" + existing_service_account_email).
#
# IAM role bindings (contract §5) — scoped per project, opt-in for anything that
# writes:
#   roles/compute.networkViewer -> each discovered project   (always)
#   roles/dns.reader            -> each discovered project   (always)
#   roles/dns.admin             -> dns_admin_project_ids      (only if enable_record_write)
# NO roles/owner, NO roles/editor, NO broad roles/viewer.
#
# Prefer a CUSTOM ROLE scoped to the exact compute.networks/subnetworks/
# instances/addresses .list/.get and dns.*.list/.get permissions over the two
# predefined read roles; the predefined roles are used here for clarity — see
# the commented custom-role sketch at the bottom.
# ---------------------------------------------------------------------------

# --- Module-created discovery service account (preferred) -------------
resource "google_service_account" "disco" {
  count        = var.discovery_identity_type == "service_account" ? 1 : 0
  project      = var.host_project_id
  account_id   = local.disco_sa_id
  display_name = "Infoblox DDI discovery SA (${var.environment})"
}

locals {
  # Email used for role bindings + as the canonical output, regardless of mode.
  disco_sa_email = (
    var.discovery_identity_type == "service_account"
    ? try(google_service_account.disco[0].email, null)
    : var.existing_service_account_email
  )
  disco_member = local.disco_sa_email == null ? null : "serviceAccount:${local.disco_sa_email}"

  # Build binding sets only when we actually have an SA to bind to, so an
  # existing_service_account deployment that forgot the email fails cleanly
  # rather than producing half-formed bindings.
  netviewer_bindings = local.disco_member == null ? toset([]) : toset(var.discovered_project_ids)
  dnsreader_bindings = local.disco_member == null ? toset([]) : toset(var.discovered_project_ids)
  dnsadmin_bindings = (local.disco_member == null || !var.enable_record_write) ? toset([]) : toset(
    var.dns_admin_project_ids
  )
}

# --- roles/compute.networkViewer on each discovered project (always) --
# Enumerate VPCs, subnets, instances, addresses for IPAM sync (read-only).
resource "google_project_iam_member" "disco_network_viewer" {
  for_each = local.netviewer_bindings
  project  = each.value
  role     = "roles/compute.networkViewer"
  member   = local.disco_member
}

# --- roles/dns.reader on each discovered project (always) -------------
# Read Cloud DNS zones/records for DNS discovery (read-only).
resource "google_project_iam_member" "disco_dns_reader" {
  for_each = local.dnsreader_bindings
  project  = each.value
  role     = "roles/dns.reader"
  member   = local.disco_member
}

# --- roles/dns.admin on record-write projects (opt-in) ----------------
# Granted ONLY when Infoblox writes records back into Cloud DNS.
resource "google_project_iam_member" "disco_dns_admin" {
  for_each = local.dnsadmin_bindings
  project  = each.value
  role     = "roles/dns.admin"
  member   = local.disco_member
}

# =====================================================================
# INFOBLOX vDISCOVERY / CLOUD NETWORK AUTOMATION — CONFIG PLACEHOLDER
# =====================================================================
# The GCP IAM above grants the SA; the Infoblox SIDE of discovery is configured
# on the control plane, not in GCP. There is no first-class
# "infoblox_vdiscovery_job" resource in the infobloxopen/infoblox provider
# today, so this is an explicit API/UI handoff:
#
#   * vNIOS Grid  -> Cloud Network Automation "GCP vDiscovery job" pointed at the
#                    org/folder/project scope, authenticating with the discovery
#                    SA (a service-account key, or a workload-identity binding
#                    where supported). Configured via WAPI (POST
#                    /wapi/vX/vdiscoverytask) or the Grid UI. See 03-gcp.md §6/§8.
#   * Universal   -> Portal "Universal Cloud" GCP source using the same SA
#                    credential; configured through the CSP API/UI.
#
# Sketch of the WAPI handoff (uncomment + wire real values / a restapi provider):
#
# resource "null_resource" "vdiscovery_job" {
#   triggers = { projects = join(",", var.discovered_project_ids) }
#   provisioner "local-exec" {
#     command = "curl -k -u \"$IB_USER:$IB_PASS\" -X POST \\
#       https://$GRID_MASTER/wapi/v2.12/vdiscoverytask \\
#       -d 'name=gcp-disco&member=infoblox.localdomain&credential_type=GCP&...' "
#   }
# }
#
# The discovery SA's key (or a workload-identity federation credential) is stored
# in Secret Manager and handed to Infoblox as the discovery credential — never
# committed.
#
# Custom-role alternative to the two predefined read roles (contract §5):
#
# resource "google_organization_iam_custom_role" "disco_readonly" {
#   org_id      = var.discovery_org_id
#   role_id     = "infobloxDdiDiscoveryReadonly"
#   title       = "Infoblox DDI discovery (read-only)"
#   permissions = [
#     "compute.networks.list", "compute.networks.get",
#     "compute.subnetworks.list", "compute.subnetworks.get",
#     "compute.instances.list", "compute.instances.get",
#     "compute.addresses.list", "compute.addresses.get",
#     "dns.managedZones.list", "dns.managedZones.get",
#     "dns.resourceRecordSets.list",
#   ]
# }
