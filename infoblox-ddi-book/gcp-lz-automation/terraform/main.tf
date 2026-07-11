# main.tf
# ---------------------------------------------------------------------------
# Locals, module-managed labels (contract §6), the dedicated DDI subnet in the
# Shared VPC host project, and the HARD-FAIL boundary guard for the
# universal_ddi (SaaS) path.
#
# Resource layout across files:
#   main.tf          — locals, labels, subnet, boundary precondition, secret reads
#   firewall.tf      — VPC firewall rules (contract §4)
#   grid.tf          — vNIOS Grid members         (deployment_model="grid")
#   universal_ddi.tf — NIOS-X hosts + Portal join  (deployment_model="universal_ddi")
#   discovery.tf     — discovery service account + IAM   (contract §5)
#   dns.tf           — inbound policy + forwarding/peering zones (contract §8)
#   outputs.tf       — canonical outputs (contract §7)
# ---------------------------------------------------------------------------

locals {
  # --- Network self-link handling --------------------------------------
  # shared_vpc_network may be a bare name or a full self-link. Normalize a name
  # to the projects/.../global/networks/<name> form; pass a self-link through.
  network_self_link = (
    can(regex("^https?://|^projects/", var.shared_vpc_network))
    ? var.shared_vpc_network
    : "projects/${var.host_project_id}/global/networks/${var.shared_vpc_network}"
  )
  network_name = reverse(split("/", local.network_self_link))[0]

  # --- Naming convention (contract §6): ${name_prefix}-<role>-<zone/index> --
  subnet_name    = "${var.name_prefix}-subnet"
  disco_sa_id    = "${var.name_prefix}-disco"          # service account account_id
  member_tag     = "${var.name_prefix}-member"          # firewall target tag on members
  member_base    = "${var.name_prefix}-member"          # grid members: ddi-member-a...
  niosx_base     = "${var.name_prefix}-niosx"           # uddi hosts:   ddi-niosx-1...

  # --- Model flags ------------------------------------------------------
  is_grid = var.deployment_model == "grid"
  is_uddi = var.deployment_model == "universal_ddi"

  # Round-robin members over the provided zone letters. Index i -> zone letter,
  # then to a full zone "<region>-<letter>". Also builds the per-member suffix.
  member_indexes = range(var.member_count)
  member_letter = {
    for i in local.member_indexes :
    i => var.zones[i % length(var.zones)]
  }
  member_zone = {
    for i in local.member_indexes :
    i => "${var.region}-${local.member_letter[i]}"
  }
  # Per-member name label. When there is one zone per member you get the clean
  # ddi-member-a / ddi-member-b form (contract §6); if members outnumber zones,
  # the index is appended to keep instance names unique.
  member_label = {
    for i in local.member_indexes :
    i => (
      var.member_count <= length(var.zones)
      ? local.member_letter[i]
      : format("%s-%d", local.member_letter[i], i)
    )
  }

  # --- Module-managed labels (contract §6) ------------------------------
  # GCP label values must be lowercase / limited charset; normalize the profile.
  managed_labels = {
    workload           = "infoblox-ddi"
    layer              = "connectivity-ddi"
    compliance_profile = lower(replace(var.compliance_profile, "/[^a-z0-9_-]/", "-"))
    deployment_model   = var.deployment_model
    managed_by         = "terraform"
    environment        = var.environment
  }
  labels = merge(var.labels, local.managed_labels)

  # --- Member internal IPs (populated by grid.tf OR universal_ddi.tf) ---
  # Exactly one of these collections is non-empty depending on deployment_model.
  member_dns_ips = local.is_grid ? (
    [for i in google_compute_instance.grid : i.network_interface[0].network_ip]
    ) : (
    [for i in google_compute_instance.niosx : i.network_interface[0].network_ip]
  )

  # Grid Master IP (grid only, contract §7). A supplied on-prem GM VIP is
  # authoritative; otherwise fall back to the first GCP member (lab/greenfield).
  grid_master_ip = local.is_grid ? try(
    coalesce(var.grid_master_vip, local.member_dns_ips[0]),
    null
  ) : null

  # --- DNS forwarding target (contract §7/§8) ---------------------------
  # Preferred spoke/forward-zone resolver address is the anycast VIP; fall back
  # to the members' individual internal IPs (dns_server_ips).
  effective_dns_target = var.ddi_anycast_vip != null ? [var.ddi_anycast_vip] : local.member_dns_ips
}

# ---------------------------------------------------------------------------
# BOUNDARY GUARD (contract §1) — HARD FAIL.
# deployment_model="universal_ddi" routes the control plane through the Infoblox
# Portal (SaaS), which sits OUTSIDE the ATO/GCC-Moderate boundary and needs
# outbound 443 to csp.infoblox.com. That path is only permitted with an explicit
# acknowledge_saas_boundary=true. A precondition here fails the PLAN (not just
# apply) with a message pointing to the authorization review.
# ---------------------------------------------------------------------------
resource "terraform_data" "boundary_guard" {
  input = var.deployment_model

  lifecycle {
    precondition {
      condition = !(var.deployment_model == "universal_ddi" && var.acknowledge_saas_boundary == false)
      error_message = join("\n", [
        "BOUNDARY VIOLATION: deployment_model = \"universal_ddi\" selects the Infoblox",
        "Portal (SaaS) control plane, which is OUTSIDE the ATO / GCC-Moderate boundary",
        "and requires OUTBOUND 443 to the Infoblox Portal (csp.infoblox.com) (contract §1).",
        "",
        "This path is disabled until it is explicitly authorized. To proceed you MUST:",
        "  1. Complete the FedRAMP/authorization review for the SaaS control-plane egress,",
        "     confirm the Portal SaaS offering's authorization status is acceptable for",
        "     this system's boundary (and that the Portal region suits any Assured",
        "     Workloads / data-residency requirement); then",
        "  2. Set  acknowledge_saas_boundary = true.",
        "",
        "For a boundary-clean deployment, use deployment_model = \"grid\" (the default),",
        "which keeps the vNIOS Grid control plane INSIDE the project/ATO boundary.",
      ])
    }
  }
}

# ---------------------------------------------------------------------------
# Dedicated DDI subnet, created by THIS module inside the Stage-1 Shared VPC.
# The host VPC network itself is NOT created here (it is Stage-1 / existing);
# the subnet is added into it. Naming: ddi-subnet (contract §6).
# ---------------------------------------------------------------------------
resource "google_compute_subnetwork" "ddi" {
  name          = local.subnet_name
  project       = var.host_project_id
  region        = var.region
  network       = local.network_self_link
  ip_cidr_range = var.ddi_subnet_cidr

  # Private Google Access lets the members reach googleapis.com without external
  # IPs (they resolve/forward google-service names — contract §8).
  private_ip_google_access = true

  # Flow logs feed audit/AU-* controls; keep on for the DDI data path.
  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

# ---------------------------------------------------------------------------
# Member runtime service account (attached to the vNIOS / NIOS-X instances).
# This is NOT the discovery SA (that is ddi-disco in discovery.tf). It carries
# only logging/monitoring write so appliance logs reach Cloud Logging (AU-*).
# Secrets are injected by Terraform via metadata, so this SA needs NO Secret
# Manager access.
# ---------------------------------------------------------------------------
resource "google_service_account" "member" {
  project      = var.host_project_id
  account_id   = "${var.name_prefix}-member"
  display_name = "Infoblox DDI member runtime SA (${var.environment})"
}

resource "google_project_iam_member" "member_logging" {
  project = var.host_project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.member.email}"
}

resource "google_project_iam_member" "member_monitoring" {
  project = var.host_project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.member.email}"
}

# ---------------------------------------------------------------------------
# Data sources for the module secrets in Secret Manager. Values are passed into
# the instance startup-script/metadata (grid.tf) and the Portal join
# (universal_ddi.tf). These read EXISTING secret VERSIONS — the module does not
# create the secrets. "latest" resolves the newest enabled version.
# ---------------------------------------------------------------------------
data "google_secret_manager_secret_version" "admin_password" {
  project = var.secret_project_id
  secret  = var.admin_password_secret_id
  version = "latest"
}

data "google_secret_manager_secret_version" "temp_license" {
  project = var.secret_project_id
  secret  = var.temp_license_secret_id
  version = "latest"
}

# Grid shared secret is only meaningful for the grid path.
data "google_secret_manager_secret_version" "grid_shared_secret" {
  count   = local.is_grid ? 1 : 0
  project = var.secret_project_id
  secret  = var.grid_shared_secret_id
  version = "latest"
}

# Portal join token is only meaningful for the universal_ddi path.
data "google_secret_manager_secret_version" "saas_join_token" {
  count   = local.is_uddi ? 1 : 0
  project = var.secret_project_id
  secret  = var.saas_join_token_secret_id
  version = "latest"
}
</content>
