# examples/hub-integration/main.tf
# ---------------------------------------------------------------------------
# Example: layer the Infoblox DDI module (Stage 2) onto the Microsoft ALZ
# Accelerator's Connectivity hub (Stage 1), deployment_model = "grid".
#
# Stage-1 outputs (hub_vnet_id, hub_resource_group_name, connectivity_subscription_id,
# log_analytics_workspace_id, firewall_private_ip) flow in as this module's inputs.
# Here we read them from the ALZ Accelerator's REMOTE STATE; swap for plain
# variables / tfvars if you don't share state across stages.
#
# STARTER EXAMPLE — replace backend coordinates, the Marketplace image/SKU, the
# Key Vault id, and every CIDR with your real values. Do not deploy as-is.
# ---------------------------------------------------------------------------

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
  # Use your own backend; shown for completeness.
  # backend "azurerm" {
  #   resource_group_name  = "rg-tfstate"
  #   storage_account_name = "sttfstateexample"
  #   container_name       = "tfstate"
  #   key                  = "infoblox-ddi/stage2.tfstate"
  # }
}

provider "azurerm" {
  features {}
  # subscription_id = data.terraform_remote_state.alz.outputs.connectivity_subscription_id
}

# The module's dns.tf creates infoblox_zone_forward resources when
# private_resolver_inbound_ip is set (as below), so the Infoblox (Grid) provider
# must be configured at the root. Credentials come from Key Vault / CI secrets.
# provider "infoblox" {
#   server   = "192.168.100.10"        # Grid Master mgmt IP/FQDN
#   username = "admin"                 # from Key Vault in CI
#   password = var.infoblox_password   # from Key Vault in CI (do not commit)
# }

# --- Stage 1: read the ALZ Accelerator hub outputs from remote state ---
# The Accelerator publishes the connectivity/hub outputs; adjust the backend
# block to point at wherever Stage 1 stored its state.
data "terraform_remote_state" "alz" {
  backend = "azurerm"
  config = {
    resource_group_name  = "rg-tfstate"
    storage_account_name = "sttfstateexample"
    container_name       = "tfstate"
    key                  = "alz-accelerator/connectivity.tfstate"
  }
}

# --- Stage 2: the Infoblox DDI module ---------------------------------
module "infoblox_ddi" {
  source = "../.."

  # Basics
  name_prefix = "ddi"
  location    = "eastus"
  environment = "prod"

  # Boundary: grid keeps the control plane inside the ATO boundary (default).
  deployment_model = "grid"
  # acknowledge_saas_boundary intentionally left false — not needed for grid.
  compliance_profile = "gcc-moderate"

  # --- From Stage-1 (ALZ Accelerator) outputs ---
  hub_resource_group_name = data.terraform_remote_state.alz.outputs.hub_resource_group_name
  hub_vnet_id             = data.terraform_remote_state.alz.outputs.hub_vnet_id

  # Dedicated DDI subnet carved from the hub VNet address space (must not overlap).
  ddi_subnet_address_prefix = "10.10.4.0/27"

  # --- Members: 2 across zones 1 and 2 (HA) ---
  member_count       = 2
  availability_zones = ["1", "2"]

  # VM SKU + Marketplace image are REGION/VERSION dependent — discover, don't guess:
  #   az vm image list --publisher infoblox --all -o table
  vnios_vm_sku = "Standard_E4s_v5" # example only; confirm against NIOS supported list
  vnios_image = {
    publisher = "infoblox"
    offer     = "infoblox_nios_on_azure"
    sku       = "nios-byol" # example; verify with `az vm image list`
    version   = "latest"     # pin to a build in production
  }

  # Existing Key Vault holding admin pw, temp license, grid shared secret.
  key_vault_id = data.terraform_remote_state.alz.outputs.connectivity_key_vault_id

  # --- NSG source scoping (never 0.0.0.0/0) ---
  mgmt_source_cidrs = ["10.10.0.0/24"]      # mgmt/bastion subnet
  dns_client_cidrs  = ["10.20.0.0/16", "10.30.0.0/16"] # spokes
  grid_peer_cidrs   = ["10.10.4.0/27", "192.168.100.0/24"] # DDI subnet + on-prem GM

  # --- Grid join (usual pattern: join Azure members to the on-prem GM) ---
  grid_name       = "CorpGrid"
  grid_master_vip = "192.168.100.10" # on-prem Grid Master VIP

  # --- DNS integration (§8) ---
  private_resolver_inbound_ip = "10.10.2.4" # Private Resolver inbound endpoint
  ddi_anycast_vip             = "10.10.4.10" # advertised from both members

  # --- Discovery identity + least-privilege RBAC (§5) ---
  discovery_identity_type     = "user_assigned_mi"
  discovered_subscription_ids = ["00000000-0000-0000-0000-000000000001"]
  enable_record_write         = false # read-only discovery by default

  # --- Spoke dns_servers write-through (opt-in; needs Network Contributor) ---
  spoke_vnet_ids         = [] # e.g. [data.terraform_remote_state.alz.outputs.spoke_vnet_id]
  enable_spoke_dns_write = false

  tags = {
    owner      = "network-platform"
    costcenter = "cc-1234"
  }
}

output "ddi_dns_server_ips" {
  value = module.infoblox_ddi.dns_server_ips
}

output "ddi_subnet_id" {
  value = module.infoblox_ddi.ddi_subnet_id
}

output "ddi_grid_master_ip" {
  value = module.infoblox_ddi.grid_master_ip
}
