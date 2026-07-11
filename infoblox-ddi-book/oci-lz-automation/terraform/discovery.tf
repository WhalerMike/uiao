# discovery.tf
# ---------------------------------------------------------------------------
# Least-privilege discovery identity for OCI -> Infoblox IPAM sync (§5).
#
# Prefer an INSTANCE PRINCIPAL: a dynamic group matching the automation/vNIOS
# instances, granted read policies — no long-lived key stored. Fall back to an
# IAM USER + API SIGNING KEY (supply an existing discovery_user_ocid; this module
# adds it to a group and grants the same read policies).
#
# Policy statements (contract §5) — read-only for discovery, write opt-in:
#   read virtual-network-family  -> discovered compartment(s)   (always)
#   read dns                     -> discovered compartment(s)   (always)
#   read instance-family         -> discovered compartment(s)   (always, optional map)
#   inspect tag-namespaces       -> tenancy                     (read defined tags)
#   manage dns                   -> discovered compartment(s)   (only if enable_record_write)
# NO manage of network/compute. NO tenancy-admin.
#
# CANDID: these policies only GRANT the identity. There is NO native, event-driven
# OCI discovery connector in Infoblox. The actual OCI->IPAM sync is API/SDK/
# Terraform-driven (see the handoff at the bottom of this file and contract §0/§5).
# ---------------------------------------------------------------------------

locals {
  # Compartments the identity may read; defaults to the hub network compartment.
  discovered_compartments = length(var.discovered_compartment_ocids) > 0 ? var.discovered_compartment_ocids : [var.network_compartment_ocid]

  use_instance_principal = var.discovery_identity_type == "instance_principal"
  use_api_key_user       = var.discovery_identity_type == "api_key_user"

  # Policy principal phrase referencing the created dynamic group / group.
  disco_principal = local.use_instance_principal ? "dynamic-group ${local.disco_dg_name}" : "group ${local.disco_grp_name}"

  # Default dynamic-group matching rule: instances in the network compartment.
  dg_matching_rule = coalesce(
    var.discovery_dynamic_group_matching_rule,
    "instance.compartment.id = '${var.network_compartment_ocid}'"
  )

  # Read statements, one set per discovered compartment.
  read_statements = flatten([
    for c in local.discovered_compartments : [
      "Allow ${local.disco_principal} to read virtual-network-family in compartment id ${c}",
      "Allow ${local.disco_principal} to read dns in compartment id ${c}",
      "Allow ${local.disco_principal} to read instance-family in compartment id ${c}",
    ]
  ])

  # Tag read at tenancy scope (defined tags drive allocation / EAs).
  tag_statement = ["Allow ${local.disco_principal} to inspect tag-namespaces in tenancy"]

  # Opt-in record write: manage dns in the discovered compartment(s).
  write_statements = var.enable_record_write ? [
    for c in local.discovered_compartments :
    "Allow ${local.disco_principal} to manage dns in compartment id ${c}"
  ] : []

  disco_statements = concat(local.read_statements, local.tag_statement, local.write_statements)
}

# --- Instance-principal dynamic group (preferred) ---------------------
resource "oci_identity_dynamic_group" "disco" {
  count          = local.use_instance_principal ? 1 : 0
  compartment_id = var.tenancy_ocid # dynamic groups live in the tenancy (root)
  name           = local.disco_dg_name
  description    = "Infoblox discovery instance principal — read VCNs/subnets/DNS (contract §5)."
  matching_rule  = local.dg_matching_rule
  freeform_tags  = local.freeform_tags
}

# --- IAM group + membership (api_key_user fallback) -------------------
resource "oci_identity_group" "disco" {
  count          = local.use_api_key_user ? 1 : 0
  compartment_id = var.tenancy_ocid
  name           = local.disco_grp_name
  description    = "Infoblox discovery group — read VCNs/subnets/DNS (contract §5)."
  freeform_tags  = local.freeform_tags
}

resource "oci_identity_user_group_membership" "disco" {
  count    = local.use_api_key_user && var.discovery_user_ocid != null ? 1 : 0
  group_id = oci_identity_group.disco[0].id
  user_id  = var.discovery_user_ocid

  lifecycle {
    precondition {
      condition     = !local.use_api_key_user || var.discovery_user_ocid != null
      error_message = "discovery_identity_type='api_key_user' requires discovery_user_ocid (an existing IAM user to add to the discovery group)."
    }
  }
}

# --- Least-privilege policy (both identity types) ---------------------
# Policies are created in the tenancy (root) so they may reference compartment
# OCIDs anywhere in the discovered set. Keep the statement list to §5 exactly.
resource "oci_identity_policy" "disco" {
  compartment_id = var.tenancy_ocid
  name           = local.disco_pol_name
  description    = "Infoblox DDI discovery least-privilege (read VCNs/subnets/DNS; write only if enable_record_write). Contract §5."
  statements     = local.disco_statements
  freeform_tags  = local.freeform_tags

  depends_on = [
    oci_identity_dynamic_group.disco,
    oci_identity_group.disco,
  ]
}

# =====================================================================
# INFOBLOX DISCOVERY / IPAM SYNC — API/SDK-DRIVEN HANDOFF (no connector)
# =====================================================================
# Unlike AWS/Azure/GCP, Infoblox ships NO deep, event-driven OCI discovery
# connector. The IAM policy above only grants the identity; the OCI->IPAM sync is
# a job YOU run. Two supported patterns (contract §0/§5, ../04-oci.md §6/§8):
#
#   * Scheduled OCI-SDK job (instance principal): a small program using the OCI
#     SDK lists VCNs/subnets/VNICs in each discovered compartment and pushes them
#     into Infoblox IPAM as networks/network-containers via WAPI (grid) or the
#     Universal DDI API (SaaS), tagging each with the VCN/compartment OCID.
#
#   * Pipeline-time reconciliation (Terraform): the infobloxopen/infoblox
#     provider allocates the next free IP and creates the A/PTR record in the SAME
#     `terraform apply` that provisions the OCI VCN/instance — closing the
#     IPAM-to-cloud gap without a connector.
#
# Sketch of the SDK-job seam (uncomment + wire real values / a container image):
#
# resource "null_resource" "oci_ipam_sync" {
#   count = 0 # enable when you wire a real sync job/image
#   triggers = { compartments = join(",", local.discovered_compartments) }
#   provisioner "local-exec" {
#     interpreter = ["/bin/bash", "-c"]
#     command = <<-EOC
#       # oci network vcn list -c <compartment> --all | \
#       #   ./oci-to-infoblox-sync.py --grid-master "$GRID_MASTER" --view default
#       echo "[PLACEHOLDER] Run the OCI-SDK -> Infoblox IPAM reconciliation here."
#     EOC
#   }
# }
