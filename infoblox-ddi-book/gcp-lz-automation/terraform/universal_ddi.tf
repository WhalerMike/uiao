# universal_ddi.tf
# ---------------------------------------------------------------------------
# UNIVERSAL DDI (SaaS) path (deployment_model = "universal_ddi").
#
# BOUNDARY WARNING: this path enrolls lightweight NIOS-X hosts into the Infoblox
# Portal (CSP), whose control plane is SaaS and sits OUTSIDE the ATO/GCC-Moderate
# boundary. It requires OUTBOUND 443 to the Portal (firewall.tf out_portal_sync)
# and is HARD-GATED behind acknowledge_saas_boundary=true (main.tf boundary_guard).
# Do not enable without completing the authorization review (contract §1).
#
# Creates, gated on local.is_uddi:
#   * google_compute_address       — one reserved internal IP per NIOS-X host
#   * google_compute_instance      — member_count NIOS-X hosts, across zones
#   * null_resource (local-exec)   — PORTAL ENROLLMENT HANDOFF placeholder:
#                                     confirms each host enrolled to the Portal.
#                                     This is the API seam — swap for the real
#                                     CSP REST call / provider.
#
# All resources here have count = 0 when deployment_model = "grid".
# ---------------------------------------------------------------------------

locals {
  uddi_member_count = local.is_uddi ? var.member_count : 0

  # NIOS-X first-boot user-data. The join token (from Secret Manager) enrolls the
  # host into the Portal over outbound 443. Exact schema is release-dependent —
  # verify against the current NIOS-X / Infoblox Cloud Services docs.
  uddi_user_data = local.is_uddi ? <<-EOT
    #infoblox-config

    default_admin_password: ${data.google_secret_manager_secret_version.admin_password.secret_data}
    remote_console_enabled: y

    # Portal (CSP) enrollment. The host phones home to infoblox_portal_url over
    # 443 and registers using the join token.
    join_token: ${data.google_secret_manager_secret_version.saas_join_token[0].secret_data}
    csp_url: ${var.infoblox_portal_url}
  EOT
  : null
}

# --- Reserved internal IPs on the DDI subnet --------------------------
resource "google_compute_address" "niosx" {
  count        = local.uddi_member_count
  name         = "${local.niosx_base}-${count.index + 1}-ip"
  project      = var.host_project_id
  region       = var.region
  subnetwork   = google_compute_subnetwork.ddi.id
  address_type = "INTERNAL"
}

# --- NIOS-X host instances --------------------------------------------
resource "google_compute_instance" "niosx" {
  count        = local.uddi_member_count
  name         = "${local.niosx_base}-${count.index + 1}"
  project      = var.host_project_id
  zone         = local.member_zone[count.index]
  machine_type = var.machine_type
  labels       = local.labels
  tags         = [local.member_tag]

  boot_disk {
    initialize_params {
      image = local.vnios_image_ref
      type  = "pd-balanced"
    }
  }

  # ONE NIC PER VPC — single interface on the Shared VPC, no external IP.
  network_interface {
    subnetwork = google_compute_subnetwork.ddi.id
    network_ip = google_compute_address.niosx[count.index].address
  }

  metadata = {
    startup-script = local.uddi_user_data
    user-data      = local.uddi_user_data
  }

  service_account {
    email  = google_service_account.member.email
    scopes = ["https://www.googleapis.com/auth/logging.write", "https://www.googleapis.com/auth/monitoring.write"]
  }

  lifecycle {
    ignore_changes = [metadata["startup-script"], metadata["user-data"]]
  }

  depends_on = [terraform_data.boundary_guard]
}

# =====================================================================
# PORTAL ENROLLMENT — API HANDOFF PLACEHOLDER
# =====================================================================
# There is no Terraform-native "join NIOS-X to the Portal" resource; in most
# deployments the host self-enrolls from the startup-script above, and any
# Portal-side configuration (DNS/DHCP service assignment, host groups) is done
# through the Infoblox Portal (CSP) REST API or the Infoblox CSP Terraform
# provider.
#
# This null_resource is the explicit SEAM for that handoff. Replace the local-
# exec sketch with a real CSP API call (curl/gcloud/SDK) or a provider resource.
# It is triggered per host and re-runs if the host id changes.
resource "null_resource" "portal_enroll" {
  count = local.uddi_member_count

  triggers = {
    host_id    = google_compute_instance.niosx[count.index].id
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
      JOIN_TOKEN = data.google_secret_manager_secret_version.saas_join_token[0].secret_data
      HOST_NAME  = google_compute_instance.niosx[count.index].name
    }
    command = <<-EOC
      echo "[PLACEHOLDER] Would confirm Portal enrollment of $HOST_NAME at $CSP_URL"
      echo "[PLACEHOLDER] Replace with a real CSP REST call, e.g.:"
      echo "  curl -sS -H 'Authorization: Token '\"$JOIN_TOKEN\" \\"
      echo "       $CSP_URL/api/infra/v1/hosts?_filter=display_name=='$HOST_NAME'"
      # Real handoff options:
      #   * Infoblox CSP/Universal DDI Terraform provider resources, or
      #   * gcloud / curl against csp.infoblox.com, or
      #   * an Ansible play invoked here.
    EOC
  }

  depends_on = [terraform_data.boundary_guard]
}
</content>
