# examples/hub-integration/main.tf
# ---------------------------------------------------------------------------
# Example: layer the Infoblox DDI module (Stage 2) onto a Google Cloud landing
# zone's Shared VPC host project (Stage 1), deployment_model = "grid".
#
# Stage-1 outputs (host_project_id, shared_vpc_network, region, and — if the
# foundation exposes them — the Cloud DNS inbound IP) flow in as this module's
# inputs. Here we read them from the landing-zone foundation's REMOTE STATE
# (Terraform Example Foundation / Fabric FAST publish outputs to a GCS backend);
# swap for plain variables / tfvars if you don't share state across stages.
#
# STARTER EXAMPLE — replace backend coordinates, the image/machine type, the
# secret project, and every CIDR with your real values. Do not deploy as-is.
# ---------------------------------------------------------------------------

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
  # Use your own GCS backend; shown for completeness.
  # backend "gcs" {
  #   bucket = "tf-state-example"
  #   prefix = "infoblox-ddi/stage2"
  # }
}

provider "google" {
  project = data.terraform_remote_state.lz.outputs.host_project_id
  region  = "us-central1"
}

# The module's dns.tf creates infoblox_zone_forward resources when
# cloud_dns_inbound_ip is set (as below), so the Infoblox (Grid) provider must be
# configured at the root. Credentials come from Secret Manager / CI secrets.
# provider "infoblox" {
#   server   = "192.168.100.10"        # Grid Master mgmt IP/FQDN
#   username = "admin"                 # from Secret Manager in CI
#   password = var.infoblox_password   # from Secret Manager in CI (do not commit)
# }

# --- Stage 1: read the landing-zone foundation outputs from remote state ---
# The foundation publishes the host project + Shared VPC outputs; adjust the
# backend block to point at wherever Stage 1 stored its state.
data "terraform_remote_state" "lz" {
  backend = "gcs"
  config = {
    bucket = "tf-state-example"
    prefix = "landing-zone/networking"
  }
}

# --- Stage 2: the Infoblox DDI module ---------------------------------
module "infoblox_ddi" {
  source = "../.."

  # Basics
  name_prefix = "ddi"
  region      = "us-central1"
  environment = "prod"

  # Boundary: grid keeps the control plane inside the ATO boundary (default).
  deployment_model = "grid"
  # acknowledge_saas_boundary intentionally left false — not needed for grid.
  compliance_profile = "gcc-moderate"

  # --- From Stage-1 (landing-zone foundation) outputs ---
  host_project_id    = data.terraform_remote_state.lz.outputs.host_project_id
  shared_vpc_network = data.terraform_remote_state.lz.outputs.shared_vpc_network # name or self-link

  # Dedicated DDI subnet carved from the VPC address plan (must not overlap).
  ddi_subnet_cidr = "10.10.4.0/27"

  # --- Members: 2 across zones a and b (HA) ---
  member_count = 2
  zones        = ["a", "b"] # -> us-central1-a, us-central1-b

  # Machine type + image are model/version dependent — discover, don't guess:
  #   gcloud compute images list --filter="family~infoblox OR name~vnios"
  machine_type = "n1-standard-4" # example only; confirm against NIOS model mapping
  vnios_image = {
    project = "<infoblox-image-project>" # Marketplace/custom image project
    family  = "<vnios-image-family>"     # or set name = "<pinned-image>"
  }

  # Project holding the Secret Manager secrets (admin pw, temp license, shared secret).
  secret_project_id = data.terraform_remote_state.lz.outputs.host_project_id

  # --- Firewall source scoping (never 0.0.0.0/0) ---
  mgmt_source_ranges = ["10.10.0.0/24"]                    # mgmt/bastion subnet
  dns_client_ranges  = ["10.20.0.0/16", "10.30.0.0/16"]    # service-project spokes
  grid_peer_ranges   = ["10.10.4.0/27", "192.168.100.0/24"] # DDI subnet + on-prem GM

  # --- Grid join (usual pattern: join GCP members to the on-prem GM) ---
  grid_name       = "CorpGrid"
  grid_master_vip = "192.168.100.10" # on-prem Grid Master VIP

  # --- DNS integration (§8) ---
  inbound_forwarding_enabled = true
  cloud_dns_inbound_ip       = "10.10.2.4"  # a Cloud DNS inbound forwarder IP (read after first apply)
  enterprise_forward_domains = ["corp.example.com.", "10.in-addr.arpa."]
  ddi_anycast_vip            = "10.10.4.10" # advertised from both members

  # --- Discovery SA + least-privilege IAM (§5) ---
  discovery_identity_type = "service_account"
  discovered_project_ids  = ["<host-project-id>", "<service-project-id>"]
  enable_record_write     = false # read-only discovery by default

  # --- Spoke DNS peering (opt-in) ---
  spoke_networks           = [] # e.g. [data.terraform_remote_state.lz.outputs.service_project_network]
  enable_spoke_dns_peering = false

  labels = {
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
