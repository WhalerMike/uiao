# versions.tf
# ---------------------------------------------------------------------------
# Provider + Terraform version pinning for the Infoblox DDI Stage-2 module (AWS).
#
# STARTER SKELETON — verify the latest versions before you deploy. The
# constraints below were current when this skeleton was authored:
#   * hashicorp/aws         — 5.x series.
#   * infobloxopen/infoblox — 2.13.0 was latest (2026-04-02).
# Pin to a tested patch range in your own environment rather than trusting
# these defaults. Check:
#   https://registry.terraform.io/providers/hashicorp/aws/latest/docs
#   https://registry.terraform.io/providers/infobloxopen/infoblox/latest/docs
#
# Boundary note: this module targets the COMMERCIAL AWS partition (.com endpoints)
# for a GCC-Moderate operating posture. Do NOT point the provider at a
# us-gov-* region / the aws-us-gov partition here — AWS GovCloud is a different
# boundary and is explicitly out of scope for this deliverable (contract §1).
# ---------------------------------------------------------------------------

terraform {
  # Terraform 1.5+ is required for the `precondition` / `postcondition`
  # lifecycle checks and the `check {}` blocks used by this module.
  required_version = ">= 1.5.0, < 2.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0" # verify latest 5.x before deploy
    }

    # Infoblox NIOS/Grid provider. Used by dns.tf and discovery.tf to drive the
    # Grid control plane (conditional forwarders, vDiscovery jobs, IPAM). For
    # the universal_ddi (SaaS) path the Grid provider is NOT the control plane —
    # the Infoblox Portal (CSP) is — so those resources are handled via the
    # REST/API handoff in universal_ddi.tf instead.
    infoblox = {
      source  = "infobloxopen/infoblox"
      version = "~> 2.13" # verify latest before deploy
    }

    # Hosts the Portal-enrollment local-exec handoff in universal_ddi.tf and the
    # spoke DHCP-option-set / vDiscovery handoff sketches.
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}

# ---------------------------------------------------------------------------
# Provider blocks are intentionally MINIMAL here. In a real root module you
# would pass region + auth via environment/assume-role and a backend, and you
# would configure the Infoblox provider against your Grid Master or CSP.
#
# The aws provider defaults to the commercial (aws) partition, which is exactly
# the commercial/GCC-Moderate boundary this module targets.
# ---------------------------------------------------------------------------

provider "aws" {
  region = var.region
  # partition defaults to "aws" (commercial .com). Do NOT target us-gov-* /
  # the aws-us-gov partition — GovCloud is out of scope (contract §1).

  default_tags {
    tags = {
      workload = "infoblox-ddi"
    }
  }
}

# The Infoblox provider is configured by the ROOT module (credentials come from
# Secrets Manager / SSM / CI secrets, not committed here). Shown for reference:
#
# provider "infoblox" {
#   server   = var.infoblox_grid_master_host   # Grid Master mgmt IP/FQDN
#   username = var.infoblox_username           # sourced from Secrets Manager in CI
#   password = var.infoblox_password           # sourced from Secrets Manager in CI
#   # For Universal DDI (SaaS) this provider is not used for the control plane;
#   # the Portal (CSP) API is driven from universal_ddi.tf instead.
# }
