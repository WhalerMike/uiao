# grid.tf
# ---------------------------------------------------------------------------
# vNIOS GRID path (deployment_model = "grid").
# Boundary-clean: the Grid control plane stays INSIDE the project/ATO boundary.
#
# Creates, gated on local.is_grid:
#   * google_compute_address    — one reserved internal IP per member
#   * google_compute_instance   — member_count members, spread across zones,
#                                  first-boot config via the startup-script
#                                  metadata (vNIOS user-data: temp_license +
#                                  default admin password + grid-join params from
#                                  Secret Manager)
#
# All resources here have count = 0 when deployment_model = "universal_ddi".
#
# ONE NIC PER VPC (03-gcp.md §2): a member serving a single Shared VPC uses one
# network interface. A member that must touch two VPCs uses two NICs on two VPCs
# — add a second `network_interface` block on the other network if you need that.
#
# DO NOT hard-code the image or machine type — both come from variables
# (vnios_image / machine_type). Discover the current image with:
#   gcloud compute images list --filter="family~infoblox OR name~vnios"
# ---------------------------------------------------------------------------

locals {
  grid_member_count = local.is_grid ? var.member_count : 0

  # Resolve the image self-link from either a family (latest) or a pinned name.
  vnios_image_ref = (
    try(var.vnios_image.name, null) != null
    ? "projects/${var.vnios_image.project}/global/images/${var.vnios_image.name}"
    : "projects/${var.vnios_image.project}/global/images/family/${var.vnios_image.family}"
  )

  # vNIOS first-boot user-data ("#infoblox-config" YAML), delivered via the
  # instance `metadata.startup-script` (also mirrored to user-data). Consumed by
  # the appliance on first boot to install the temp license, set the default
  # admin password, and (member) join the Grid to the Grid Master over 1194/udp
  # + 2114/tcp. Secrets come from Secret Manager (see main.tf data sources) and
  # are NEVER committed. The exact schema is NIOS-version dependent — verify
  # against the "vNIOS for Google Cloud" deployment guide for your build.
  grid_user_data = local.is_grid ? {
    for i in local.member_indexes : i => <<-EOT
      #infoblox-config

      temp_license: ${data.google_secret_manager_secret_version.temp_license.secret_data}
      default_admin_password: ${data.google_secret_manager_secret_version.admin_password.secret_data}
      remote_console_enabled: y

      # Grid-join parameters. For the usual GCP pattern the Grid Master lives
      # on-prem (grid_master_vip); the GCP members join as Grid members. If
      # grid_master_vip is null the first member is treated as the Grid Master
      # (lab/greenfield only).
      %{if var.grid_master_vip != null~}
      gridmaster:
        ip_addr: ${var.grid_master_vip}
        grid_name: ${var.grid_name}
        shared_secret: ${data.google_secret_manager_secret_version.grid_shared_secret[0].secret_data}
      %{else~}
      # This member (index ${i}) initializes the Grid as Grid Master:
      gridmaster:
        grid_name: ${var.grid_name}
        shared_secret: ${data.google_secret_manager_secret_version.grid_shared_secret[0].secret_data}
      %{endif~}
    EOT
  } : {}
}

# --- Reserved internal IPs on the DDI subnet --------------------------
resource "google_compute_address" "grid" {
  count        = local.grid_member_count
  name         = "${local.member_base}-${local.member_label[count.index]}-ip"
  project      = var.host_project_id
  region       = var.region
  subnetwork   = google_compute_subnetwork.ddi.id
  address_type = "INTERNAL"
}

# --- vNIOS member instances -------------------------------------------
# Spread across zones via local.member_zone. Persistent balanced/SSD boot disk
# sized to the model (03-gcp.md §4). Single NIC on the Shared VPC by default.
resource "google_compute_instance" "grid" {
  count        = local.grid_member_count
  name         = "${local.member_base}-${local.member_label[count.index]}"
  project      = var.host_project_id
  zone         = local.member_zone[count.index]
  machine_type = var.machine_type
  labels       = local.labels
  tags         = [local.member_tag]

  boot_disk {
    initialize_params {
      image = local.vnios_image_ref
      # Size/type are model dependent; confirm the model->disk mapping. Balanced
      # PD shown; use SSD PD for higher-throughput members.
      type = "pd-balanced"
      # size = 250   # set per model (03-gcp.md §4) — left to the image default here
    }
  }

  # ONE NIC PER VPC. Single interface on the Shared VPC host network's DDI
  # subnet, with the reserved internal IP. No external IP (private members).
  network_interface {
    subnetwork = google_compute_subnetwork.ddi.id
    network_ip = google_compute_address.grid[count.index].address
    # Deliberately no access_config {} — members have no public IP.
  }

  # First-boot vNIOS configuration (temp_license + admin pw + grid join). vNIOS
  # consumes it from the startup-script metadata; also mirrored as user-data.
  metadata = {
    startup-script = local.grid_user_data[count.index]
    user-data      = local.grid_user_data[count.index]
  }

  service_account {
    email  = google_service_account.member.email
    scopes = ["https://www.googleapis.com/auth/logging.write", "https://www.googleapis.com/auth/monitoring.write"]
  }

  lifecycle {
    # metadata changes would re-bootstrap; ignore post-first-boot so a secret
    # rotation in Secret Manager doesn't disturb running members. Remove if you
    # WANT re-bootstrap on user-data change.
    ignore_changes = [metadata["startup-script"], metadata["user-data"]]
  }

  depends_on = [terraform_data.boundary_guard]
}
</content>
