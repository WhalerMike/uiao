# versions.tf
# ---------------------------------------------------------------------------
# Provider + Terraform version pinning for the Infoblox DDI Stage-2 module on
# VMware (VCF / vSphere / NSX-T).
#
# STARTER SKELETON — verify the latest versions before you deploy. The
# constraints below were current when this skeleton was authored:
#   * hashicorp/vsphere      — 2.x series (OVF deploy, DRS anti-affinity).
#   * vmware/nsxt            — 3.x series (policy DFW, DNS forwarder, DHCP relay).
#   * infobloxopen/infoblox  — 2.13.0 was latest (2026-04-02).
# Pin to a tested patch range in your own environment rather than trusting
# these defaults. Check:
#   https://registry.terraform.io/providers/hashicorp/vsphere/latest/docs
#   https://registry.terraform.io/providers/vmware/nsxt/latest/docs
#   https://registry.terraform.io/providers/infobloxopen/infoblox/latest/docs
#
# Boundary note: this module targets a SELF-CONTAINED VCF private cloud for a
# FedRAMP-Moderate operating posture. The Grid control plane stays INSIDE the
# SDDC unless deployment_model="universal_ddi" is explicitly acknowledged
# (see _module-contract.md §1 and main.tf boundary_guard).
# ---------------------------------------------------------------------------

terraform {
  # Terraform 1.5+ is required for the `precondition` / `postcondition`
  # lifecycle checks and the `check {}` blocks used by this module.
  required_version = ">= 1.5.0, < 2.0.0"

  required_providers {
    # vSphere: deploys the vNIOS OVA/OVF (content library or local .ova) as
    # vsphere_virtual_machine, places members on ESXi hosts with anti-affinity,
    # and (optionally) manages the read-only discovery role/permission.
    vsphere = {
      source  = "hashicorp/vsphere"
      version = "~> 2.6" # verify latest 2.x before deploy
    }

    # NSX-T: distributed firewall (DFW) micro-segmentation for the DDI members,
    # plus the DNS forwarder zone and DHCP relay that point tenant traffic at
    # the vNIOS members.
    nsxt = {
      source  = "vmware/nsxt"
      version = "~> 3.7" # verify latest 3.x before deploy
    }

    # Infoblox NIOS/Grid provider. Used by dns.tf to drive the Grid control
    # plane (conditional forwarders to on-prem AD DNS, IPAM). For the
    # universal_ddi (SaaS) path the Grid provider is NOT the control plane —
    # the Infoblox Portal (CSP) is — so those steps are an API handoff
    # (universal_ddi.tf).
    infoblox = {
      source  = "infobloxopen/infoblox"
      version = "~> 2.13" # verify latest before deploy
    }

    # Hosts the Portal-enrollment local-exec handoff in universal_ddi.tf.
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}

# ---------------------------------------------------------------------------
# Provider blocks are intentionally MINIMAL here. Credentials come from
# HashiCorp Vault / CI secrets (NOT a cloud KMS — there is none on-prem) and
# are passed as sensitive variables; nothing is committed.
#
# NOTE: allow_unverified_ssl is exposed as a variable and defaults to FALSE.
# Do NOT disable TLS verification in production — supply a trusted CA instead.
# ---------------------------------------------------------------------------

provider "vsphere" {
  vsphere_server       = var.vsphere_server
  user                 = var.vsphere_user
  password             = var.vsphere_password        # sensitive; from Vault/CI
  allow_unverified_ssl = var.allow_unverified_ssl    # default false
}

provider "nsxt" {
  host                 = var.nsx_manager
  username             = var.nsx_user
  password             = var.nsx_password             # sensitive; from Vault/CI
  allow_unverified_ssl = var.allow_unverified_ssl     # default false
}

# The Infoblox provider is configured by the ROOT module (credentials from
# Vault / CI secrets, not committed here). Shown for reference only:
#
# provider "infoblox" {
#   server   = var.infoblox_grid_master_host   # Grid Master mgmt IP/FQDN
#   username = var.infoblox_username           # sourced from Vault/CI
#   password = var.infoblox_password           # sourced from Vault/CI
#   # For Universal DDI (SaaS) this provider is not used for the control plane;
#   # the Portal (CSP) API is driven from universal_ddi.tf instead.
# }
