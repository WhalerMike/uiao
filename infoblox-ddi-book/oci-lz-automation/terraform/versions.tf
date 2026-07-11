# versions.tf
# ---------------------------------------------------------------------------
# Provider + Terraform version pinning for the Infoblox DDI Stage-2 module (OCI).
#
# STARTER SKELETON — verify the latest versions before you deploy. The
# constraints below were current when this skeleton was authored:
#   * oracle/oci            — 6.x series was current.
#   * infobloxopen/infoblox — 2.13.0 was latest.
# Pin to a tested patch range in your own environment rather than trusting
# these defaults. Check the provider-docs roots:
#   https://registry.terraform.io/providers/oracle/oci/latest/docs
#   https://registry.terraform.io/providers/infobloxopen/infoblox/latest/docs
#
# Boundary note: this module targets COMMERCIAL OCI (the OC1 realm,
# *.oraclecloud.com) for a FedRAMP Moderate-equivalent operating posture. Do NOT
# point the oci provider at a Government (OC2/OC3) or National-Security realm
# here — those are separate boundaries and out of scope for this deliverable
# (see _module-contract.md §1).
# ---------------------------------------------------------------------------

terraform {
  # Terraform 1.5+ is required for the `precondition` / `postcondition`
  # lifecycle checks used by this module (boundary guard, security-model guards).
  required_version = ">= 1.5.0, < 2.0.0"

  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "~> 6.0" # verify latest before deploy
    }

    # Infoblox NIOS/Grid provider. Used by dns.tf and discovery.tf to drive the
    # Grid control plane (conditional forwarders, IPAM). For the universal_ddi
    # (SaaS) path the Grid provider is NOT the control plane — the Infoblox
    # Portal (CSP) is — so those objects are handled via the REST/API handoff in
    # universal_ddi.tf instead.
    infoblox = {
      source  = "infobloxopen/infoblox"
      version = "~> 2.13" # verify latest before deploy
    }

    # Generates the ephemeral SSH key attached to the instance so OCI's metadata
    # contract is satisfied while the vNIOS admin account comes from OCI Vault.
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
    # Hosts the API/SDK-driven discovery + Portal-enrollment local-exec handoffs.
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}

# ---------------------------------------------------------------------------
# Provider blocks are intentionally MINIMAL here. In a real root module you
# would pass tenancy/user/fingerprint/private_key + region via a config file,
# environment, or (in OCI Resource Manager) the stack's built-in credentials,
# and you would configure the Infoblox provider against your Grid Master.
# ---------------------------------------------------------------------------

provider "oci" {
  region = var.region
  # Auth is supplied out-of-band:
  #   * OCI Resource Manager stacks inject credentials automatically.
  #   * CI runners use an API-key config or instance/resource principals.
  # Do NOT commit tenancy_ocid / user_ocid / private_key here.
}

# The Infoblox provider is configured by the ROOT module (credentials come from
# OCI Vault / CI secrets, not committed here). Shown for reference only:
#
# provider "infoblox" {
#   server   = var.infoblox_grid_master_host   # Grid Master mgmt IP/FQDN
#   username = var.infoblox_username           # sourced from OCI Vault in CI
#   password = var.infoblox_password           # sourced from OCI Vault in CI
#   # For Universal DDI (SaaS) this provider is not used for the control plane;
#   # the Portal (CSP) API is driven from universal_ddi.tf instead.
# }
