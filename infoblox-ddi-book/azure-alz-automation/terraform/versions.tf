# versions.tf
# ---------------------------------------------------------------------------
# Provider + Terraform version pinning for the Infoblox DDI Stage-2 module.
#
# STARTER SKELETON — verify the latest versions before you deploy. The
# constraints below were current when this skeleton was authored:
#   * hashicorp/azurerm     — 4.80.0 was latest (2026-07-02); 4.x series.
#   * infobloxopen/infoblox — 2.13.0 was latest (2026-04-02).
# Pin to a tested patch range in your own environment rather than trusting
# these defaults. Check:
#   https://registry.terraform.io/providers/hashicorp/azurerm/latest
#   https://registry.terraform.io/providers/infobloxopen/infoblox/latest
#
# Boundary note: this module targets COMMERCIAL Azure (.com endpoints) for a
# GCC-Moderate operating posture. Do NOT set the azurerm provider `environment`
# to "usgovernment" here — that is the Azure Government (.us) boundary and is
# explicitly out of scope for this deliverable (see _module-contract.md §1).
# ---------------------------------------------------------------------------

terraform {
  # Terraform 1.5+ is required for the `precondition` / `postcondition`
  # lifecycle checks and the `check {}` blocks used by this module.
  required_version = ">= 1.5.0, < 2.0.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0" # verify latest 4.x before deploy
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

    # Generates the ephemeral SSH key attached to the VM object so Azure's
    # Linux VM contract is satisfied while password auth stays disabled (vNIOS
    # uses its own admin account from Key Vault). See grid.tf / universal_ddi.tf.
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
    # Hosts the Portal-enrollment local-exec handoff in universal_ddi.tf.
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}

# ---------------------------------------------------------------------------
# Provider blocks are intentionally MINIMAL here. In a real root module you
# would pass subscription/tenant + auth via environment or a backend, and you
# would configure the Infoblox provider against your Grid Master or CSP.
#
# The azurerm provider defaults to the AzurePublicCloud (.com) environment,
# which is exactly the commercial/GCC-Moderate boundary this module targets.
# ---------------------------------------------------------------------------

provider "azurerm" {
  features {}
  # environment = "public"   # DEFAULT. Commercial .com. Do not switch to
  #                          # "usgovernment" — Gov (.us) is out of scope.
}

# The Infoblox provider is configured by the ROOT module (credentials come from
# Key Vault / CI secrets, not committed here). Shown for reference only:
#
# provider "infoblox" {
#   server   = var.infoblox_grid_master_host   # Grid Master mgmt IP/FQDN
#   username = var.infoblox_username           # sourced from Key Vault in CI
#   password = var.infoblox_password           # sourced from Key Vault in CI
#   # For Universal DDI (SaaS) this provider is not used for the control plane;
#   # the Portal (CSP) API is driven from universal_ddi.tf instead.
# }
