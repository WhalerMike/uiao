# versions.tf
# ---------------------------------------------------------------------------
# Provider + Terraform version pinning for the Infoblox DDI Stage-2 module.
#
# STARTER SKELETON — verify the latest versions before you deploy. The
# constraints below were current when this skeleton was authored:
#   * hashicorp/google      — 6.x series (verify latest before deploy).
#   * infobloxopen/infoblox — 2.13.0 was latest (2026-04-02).
# Pin to a tested patch range in your own environment rather than trusting
# these defaults. Check:
#   https://registry.terraform.io/providers/hashicorp/google/latest/docs
#   https://registry.terraform.io/providers/infobloxopen/infoblox/latest/docs
#
# Boundary note: this module targets COMMERCIAL Google Cloud for a GCC-Moderate
# operating posture. Data-residency / personnel controls on GCP are delivered via
# Assured Workloads folders (Stage-1 concern) — this module does not switch
# endpoints or provision Assured Workloads (see _module-contract.md §1).
# ---------------------------------------------------------------------------

terraform {
  # Terraform 1.5+ is required for the `precondition` / `postcondition`
  # lifecycle checks and `terraform_data` used by this module's boundary guard.
  required_version = ">= 1.5.0, < 2.0.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0" # verify latest before deploy
    }

    # Infoblox NIOS/Grid provider. Used by dns.tf (and the discovery seam) to
    # drive the Grid control plane (conditional forwarders, IPAM). For the
    # universal_ddi (SaaS) path the Grid provider is NOT the control plane — the
    # Infoblox Portal (CSP) is — so those resources are handled via the REST/API
    # handoff in universal_ddi.tf instead.
    infoblox = {
      source  = "infobloxopen/infoblox"
      version = "~> 2.13" # verify latest before deploy
    }

    # Hosts the vDiscovery / Portal-enrollment local-exec handoffs.
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}

# ---------------------------------------------------------------------------
# Provider blocks are intentionally MINIMAL here. In a real root module you
# would pass project/region + auth via environment (Application Default
# Credentials, a workload-identity federation credential in CI, or a service
# account), and you would configure the Infoblox provider against your Grid
# Master or CSP.
# ---------------------------------------------------------------------------

provider "google" {
  project = var.host_project_id
  region  = var.region
  # Credentials come from ADC / a workload-identity-federation token in CI —
  # never a committed key file. See pipelines/ for the OIDC wiring.
}

# The Infoblox provider is configured by the ROOT module (credentials come from
# Secret Manager / CI secrets, not committed here). Shown for reference only:
#
# provider "infoblox" {
#   server   = var.infoblox_grid_master_host   # Grid Master mgmt IP/FQDN
#   username = var.infoblox_username           # sourced from Secret Manager in CI
#   password = var.infoblox_password           # sourced from Secret Manager in CI
#   # For Universal DDI (SaaS) this provider is not used for the control plane;
#   # the Portal (CSP) API is driven from universal_ddi.tf instead.
# }
</content>
