# main.tf
# ---------------------------------------------------------------------------
# Locals, module-managed freeform tags (contract §6), the dedicated DDI subnet
# in the hub VCN, the HARD-FAIL boundary guard for the universal_ddi (SaaS) path,
# and the OCI Vault secret reads.
#
# Resource layout across files:
#   main.tf          — locals, tags, subnet, boundary precondition, Vault secrets
#   security.tf      — NSG or Security List + rules (contract §4)
#   grid.tf          — vNIOS Grid members         (deployment_model="grid")
#   universal_ddi.tf — NIOS-X hosts + Portal join  (deployment_model="universal_ddi")
#   discovery.tf     — discovery identity (IAM) + policy (contract §5)
#   dns.tf           — OCI resolver endpoints + conditional forwarders (contract §8)
#   outputs.tf       — canonical outputs (contract §7)
# ---------------------------------------------------------------------------

locals {
  # --- Naming convention (contract §6): ${name_prefix}-<role>-<ad/fd/index> --
  subnet_name      = "${var.name_prefix}-subnet"
  nsg_name         = "${var.name_prefix}-nsg"
  seclist_name     = "${var.name_prefix}-seclist"
  disco_dg_name    = "${var.name_prefix}-disco-dg"
  disco_grp_name   = "${var.name_prefix}-disco-grp"
  disco_pol_name   = "${var.name_prefix}-disco-policy"
  member_base_name = "${var.name_prefix}-vnios" # grid members: ddi-vnios-ad1-fd1
  niosx_base_name  = "${var.name_prefix}-niosx" # uddi hosts:   ddi-niosx-1

  # --- Model / security flags ------------------------------------------
  is_grid    = var.deployment_model == "grid"
  is_uddi    = var.deployment_model == "universal_ddi"
  use_nsg    = var.security_model == "nsg"
  use_seclst = var.security_model == "security_list"

  # Place members over the provided ADs and FDs so each (AD, FD) pair is DISTINCT
  # up to len(ADs)*len(FDs): AD cycles fastest, FD advances once per AD-cycle.
  member_indexes = range(var.member_count)
  ad_len         = length(var.availability_domains)
  fd_len         = length(var.fault_domains)
  distinct_slots = local.ad_len * local.fd_len

  member_ad_idx = { for i in local.member_indexes : i => i % local.ad_len }
  member_fd_idx = { for i in local.member_indexes : i => floor(i / local.ad_len) % local.fd_len }

  member_ad_for = { for i in local.member_indexes : i => var.availability_domains[local.member_ad_idx[i]] }
  member_fd_for = { for i in local.member_indexes : i => var.fault_domains[local.member_fd_idx[i]] }

  # Per-member name label: ddi-vnios-ad1-fd1 (single-AD regions still get unique,
  # meaningful names via the FD index). When members exceed the distinct (AD,FD)
  # slots, the raw index is appended to keep OCI display names unique.
  member_label = {
    for i in local.member_indexes :
    i => (
      var.member_count <= local.distinct_slots
      ? format("ad%d-fd%d", local.member_ad_idx[i] + 1, local.member_fd_idx[i] + 1)
      : format("ad%d-fd%d-%d", local.member_ad_idx[i] + 1, local.member_fd_idx[i] + 1, i)
    )
  }

  # --- Module-managed freeform tags (contract §6) -----------------------
  # These keys are authoritative; caller tags merge UNDER them.
  managed_tags = {
    workload           = "infoblox-ddi"
    layer              = "connectivity-ddi"
    compliance_profile = var.compliance_profile
    deployment_model   = var.deployment_model
    managed_by         = "terraform"
    environment        = var.environment
  }
  freeform_tags = merge(var.freeform_tags, local.managed_tags)

  # --- Member VNIC IPs (populated by grid.tf OR universal_ddi.tf) -------
  # Exactly one collection is non-empty depending on deployment_model.
  member_dns_ips = local.is_grid ? (
    oci_core_instance.grid[*].private_ip
    ) : (
    oci_core_instance.niosx[*].private_ip
  )

  # Grid Master IP (grid only, contract §7). Supplied on-prem GM VIP is
  # authoritative; otherwise fall back to the first OCI member (lab/greenfield).
  grid_master_ip = local.is_grid ? try(
    coalesce(var.grid_master_vip, oci_core_instance.grid[0].private_ip),
    null
  ) : null

  # Preferred spoke resolver target is the anycast VIP; fall back to member IPs.
  effective_dns_target = var.ddi_anycast_vip != null ? [var.ddi_anycast_vip] : local.member_dns_ips
}

# ---------------------------------------------------------------------------
# BOUNDARY GUARD (contract §1) — HARD FAIL.
# deployment_model="universal_ddi" routes the control plane through the Infoblox
# Portal (SaaS), which sits OUTSIDE the ATO boundary and needs outbound 443.
# That path is only permitted with an explicit acknowledge_saas_boundary=true.
# A precondition on this resource fails the PLAN (not just apply).
# ---------------------------------------------------------------------------
resource "terraform_data" "boundary_guard" {
  input = var.deployment_model

  lifecycle {
    precondition {
      condition = !(var.deployment_model == "universal_ddi" && var.acknowledge_saas_boundary == false)
      error_message = join("\n", [
        "BOUNDARY VIOLATION: deployment_model = \"universal_ddi\" selects the Infoblox",
        "Portal (SaaS) control plane, which is OUTSIDE the ATO / FedRAMP-Moderate boundary",
        "and requires OUTBOUND 443 to the Infoblox Portal (contract §1).",
        "",
        "This path is disabled until it is explicitly authorized. To proceed you MUST:",
        "  1. Complete the FedRAMP/authorization review for the SaaS control-plane egress,",
        "     and confirm the Portal SaaS offering's authorization status is acceptable",
        "     for this system's boundary; then",
        "  2. Set  acknowledge_saas_boundary = true.",
        "",
        "For a boundary-clean deployment, use deployment_model = \"grid\" (the default),",
        "which keeps the vNIOS Grid control plane INSIDE the tenancy/ATO boundary.",
        "In OCI Government (OC2/OC3) / National-Security realms the Portal is typically",
        "unreachable — use grid there.",
      ])
    }
  }
}

# ---------------------------------------------------------------------------
# Dedicated DDI subnet, created by THIS module inside the Stage-1 hub VCN.
# The hub VCN itself and the DRG are NOT created here (Stage-1 / existing).
# Naming: ddi-subnet (contract §6). Attach the NSG per-VNIC (security.tf) or the
# Security List here, depending on security_model.
# ---------------------------------------------------------------------------
resource "oci_core_subnet" "ddi" {
  compartment_id = var.network_compartment_ocid
  vcn_id         = var.hub_vcn_ocid
  cidr_block     = var.ddi_subnet_cidr
  display_name   = local.subnet_name
  dns_label      = replace(var.name_prefix, "-", "")

  # Private subnet — DDI members are reached over the DRG (spokes/on-prem), not
  # from the internet. Public IPs are prohibited on this subnet.
  prohibit_public_ip_on_vnic = true

  # Subnet-wide Security List enforcement when security_model="security_list";
  # for the NSG model this stays empty and rules live on the per-VNIC NSG.
  security_list_ids = local.use_seclst ? [oci_core_security_list.ddi[0].id] : []

  freeform_tags = local.freeform_tags
  defined_tags  = var.defined_tags
}

# ---------------------------------------------------------------------------
# OCI Vault secret reads. Values are passed into cloud-init/user_data (grid.tf)
# and the Portal join (universal_ddi.tf). These read EXISTING secrets by OCID —
# the module does not create them. secret_bundle_content.content is base64.
# ---------------------------------------------------------------------------
data "oci_secrets_secretbundle" "admin_password" {
  secret_id = var.admin_password_secret_ocid
}

data "oci_secrets_secretbundle" "temp_license" {
  secret_id = var.temp_license_secret_ocid
}

# Grid shared secret is only meaningful for the grid path.
data "oci_secrets_secretbundle" "grid_shared_secret" {
  count     = local.is_grid && var.grid_shared_secret_ocid != null ? 1 : 0
  secret_id = var.grid_shared_secret_ocid
}

# Portal join token is only meaningful for the universal_ddi path.
data "oci_secrets_secretbundle" "saas_join_token" {
  count     = local.is_uddi && var.saas_join_token_secret_ocid != null ? 1 : 0
  secret_id = var.saas_join_token_secret_ocid
}

locals {
  # Decoded secret values (OCI Vault stores/returns base64 content).
  admin_password_value = base64decode(data.oci_secrets_secretbundle.admin_password.secret_bundle_content[0].content)
  temp_license_value   = base64decode(data.oci_secrets_secretbundle.temp_license.secret_bundle_content[0].content)
  grid_shared_value    = local.is_grid && var.grid_shared_secret_ocid != null ? base64decode(data.oci_secrets_secretbundle.grid_shared_secret[0].secret_bundle_content[0].content) : ""
  saas_join_value      = local.is_uddi && var.saas_join_token_secret_ocid != null ? base64decode(data.oci_secrets_secretbundle.saas_join_token[0].secret_bundle_content[0].content) : ""
}
