# examples/hub-integration/main.tf
# ---------------------------------------------------------------------------
# Example: layer the Infoblox DDI module (Stage 2) onto the OCI CIS Landing Zone
# (Stage 1) hub VCN, deployment_model = "grid".
#
# Stage-1 outputs (hub_vcn_ocid, network_compartment_ocid, drg_ocid, vault_ocid,
# hub resolver/subnet OCIDs) flow in as this module's inputs. Here we read them
# from the CIS Landing Zone's REMOTE STATE; swap for plain variables / tfvars if
# you don't share state across stages (or use OCI Resource Manager stack outputs).
#
# STARTER EXAMPLE — replace backend coordinates, the imported image OCID, the
# Vault secret OCIDs, ADs, and every CIDR with your real values. Do not deploy as-is.
# ---------------------------------------------------------------------------

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "~> 6.0"
    }
  }
  # Use your own backend; shown for completeness. OCI Object Storage (S3-compat)
  # is a common Terraform backend, or use OCI Resource Manager's managed state.
  # backend "s3" {
  #   bucket                      = "tfstate"
  #   key                         = "infoblox-ddi/stage2.tfstate"
  #   region                      = "us-ashburn-1"
  #   endpoints                   = { s3 = "https://<namespace>.compat.objectstorage.us-ashburn-1.oraclecloud.com" }
  #   skip_region_validation      = true
  #   skip_credentials_validation = true
  #   skip_requesting_account_id  = true
  # }
}

provider "oci" {
  region = "us-ashburn-1"
  # Auth via API-key config, instance/resource principal, or Resource Manager.
}

# The module's dns.tf creates infoblox_zone_forward resources when
# oci_listening_endpoint_ip is set, so the Infoblox (Grid) provider must be
# configured at the root. Credentials come from OCI Vault / CI secrets.
# provider "infoblox" {
#   server   = "192.168.100.10"        # Grid Master mgmt IP/FQDN
#   username = "admin"                 # from OCI Vault in CI
#   password = var.infoblox_password   # from OCI Vault in CI (do not commit)
# }

# --- Stage 1: read the CIS Landing Zone hub outputs from remote state ---
data "terraform_remote_state" "lz" {
  backend = "s3"
  config = {
    bucket                      = "tfstate"
    key                         = "cis-landing-zone/network.tfstate"
    region                      = "us-ashburn-1"
    endpoints                   = { s3 = "https://<namespace>.compat.objectstorage.us-ashburn-1.oraclecloud.com" }
    skip_region_validation      = true
    skip_credentials_validation = true
    skip_requesting_account_id  = true
  }
}

variable "tenancy_ocid" {
  type = string
}

# --- Stage 2: the Infoblox DDI module ---------------------------------
module "infoblox_ddi" {
  source = "../.."

  # Basics
  name_prefix = "ddi"
  region      = "us-ashburn-1"
  environment = "prod"

  # Boundary: grid keeps the control plane inside the tenancy/ATO boundary (default).
  deployment_model = "grid"
  # acknowledge_saas_boundary intentionally left false — not needed for grid.
  compliance_profile = "fedramp-moderate"

  # --- From Stage-1 (CIS Landing Zone) outputs ---
  tenancy_ocid             = var.tenancy_ocid
  network_compartment_ocid = data.terraform_remote_state.lz.outputs.network_compartment_ocid
  hub_vcn_ocid             = data.terraform_remote_state.lz.outputs.hub_vcn_ocid
  drg_ocid                 = data.terraform_remote_state.lz.outputs.drg_ocid
  vault_ocid               = data.terraform_remote_state.lz.outputs.vault_ocid

  # Dedicated DDI subnet carved from the hub VCN address space (must not overlap).
  ddi_subnet_cidr = "10.10.4.0/27"

  # --- Members: 2 across ADs 1 and 2, FDs 1 and 2 (HA) ---
  member_count         = 2
  availability_domains = ["Uocm:US-ASHBURN-AD-1", "Uocm:US-ASHBURN-AD-2"]
  fault_domains        = ["FAULT-DOMAIN-1", "FAULT-DOMAIN-2"]

  # Shape + imported CUSTOM IMAGE are model/region dependent — supply your own.
  #   oci compute image import from-object -c <compartment> --namespace <ns> \
  #     --bucket-name <bucket> --name vnios-<ver>.qcow2 \
  #     --source-image-type QCOW2 --launch-mode PARAVIRTUALIZED
  vnios_shape      = "VM.Standard.E4.Flex" # example; confirm against NIOS spec
  vnios_ocpus      = 4
  vnios_memory_gbs = 32
  vnios_image_ocid = "ocid1.image.oc1..aaaaEXAMPLEimportedcustomimage"

  # --- OCI Vault secret OCIDs (pre-created) ---
  admin_password_secret_ocid = "ocid1.vaultsecret.oc1..aaaaEXAMPLEadminpw"
  temp_license_secret_ocid   = "ocid1.vaultsecret.oc1..aaaaEXAMPLElicense"
  grid_shared_secret_ocid    = "ocid1.vaultsecret.oc1..aaaaEXAMPLEgridsecret"

  # --- Security-list/NSG source scoping (never 0.0.0.0/0) ---
  security_model    = "nsg"
  mgmt_source_cidrs = ["10.10.0.0/24"]                      # mgmt/bastion subnet
  dns_client_cidrs  = ["10.20.0.0/16", "10.30.0.0/16"]     # spokes over the DRG
  grid_peer_cidrs   = ["10.10.4.0/27", "192.168.100.0/24"] # DDI subnet + on-prem GM

  # --- Grid join (usual pattern: join OCI members to the on-prem GM over the DRG) ---
  grid_name       = "CorpGrid"
  grid_master_vip = "192.168.100.10" # on-prem Grid Master VIP

  # --- DNS integration (§8) ---
  manage_resolver_endpoints     = true
  hub_resolver_ocid             = data.terraform_remote_state.lz.outputs.hub_resolver_ocid
  resolver_endpoint_subnet_ocid = "ocid1.subnet.oc1..aaaaEXAMPLEresolversubnet" # dedicated resolver subnet
  oci_listening_endpoint_ip     = "10.10.4.20"   # OCI resolver LISTENING endpoint IP
  ddi_anycast_vip               = "10.10.4.10"   # advertised from both members

  # --- Discovery identity + least-privilege IAM (§5) ---
  discovery_identity_type      = "instance_principal"
  discovered_compartment_ocids = ["ocid1.compartment.oc1..aaaaEXAMPLEspokenet"]
  enable_record_write          = false # read-only discovery by default

  # --- Spoke resolver write-through (opt-in) ---
  spoke_vcn_ocids        = [] # e.g. [data.terraform_remote_state.lz.outputs.spoke_vcn_ocid]
  enable_spoke_dns_write = false

  freeform_tags = {
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
