# examples/hub-integration/main.tf
# ---------------------------------------------------------------------------
# Example: layer the Infoblox DDI module (Stage 2) onto the AWS Control Tower /
# Landing Zone Accelerator Network-account hub VPC (Stage 1), deployment_model="grid".
#
# Stage-1 outputs (network_account_id, hub_vpc_id, transit_gateway_id,
# r53_resolver_inbound_ip, dns_query_log_group_arn) flow in as this module's inputs.
# Here we read them from the LZA/Control Tower REMOTE STATE; swap for SSM parameters
# or plain variables / tfvars if you don't share state across stages.
#
# STARTER EXAMPLE — replace backend coordinates, the Marketplace AMI/instance type,
# the ExternalId, and every CIDR with your real values. Do not deploy as-is.
# ---------------------------------------------------------------------------

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  # Use your own backend; shown for completeness.
  # backend "s3" {
  #   bucket         = "my-tfstate-bucket"
  #   key            = "infoblox-ddi/stage2.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "tf-lock"     # state locking
  #   encrypt        = true
  # }
}

provider "aws" {
  region = "us-east-1"
  # The provider must target the Network/connectivity account (assume a role into
  # it if you run the pipeline from a tooling account).
  # assume_role { role_arn = "arn:aws:iam::<network-account>:role/DeployRole" }
}

# The module's dns.tf creates infoblox_zone_forward resources when
# r53_resolver_inbound_ip is set (as below), so the Infoblox (Grid) provider must
# be configured at the root. Credentials come from Secrets Manager / CI secrets.
# provider "infoblox" {
#   server   = "192.168.100.10"        # Grid Master mgmt IP/FQDN
#   username = "admin"                 # from Secrets Manager in CI
#   password = var.infoblox_password   # from Secrets Manager in CI (do not commit)
# }

# --- Stage 1: read Control Tower / LZA hub outputs from remote state ---
data "terraform_remote_state" "lza" {
  backend = "s3"
  config = {
    bucket = "my-tfstate-bucket"
    key    = "lza/network.tfstate"
    region = "us-east-1"
  }
}

# --- Stage 2: the Infoblox DDI module ---------------------------------
module "infoblox_ddi" {
  source = "../.."

  # Basics
  name_prefix = "ddi"
  region      = "us-east-1"
  environment = "prod"

  # Boundary: grid keeps the control plane inside the ATO boundary (default).
  deployment_model = "grid"
  # acknowledge_saas_boundary intentionally left false — not needed for grid.
  compliance_profile = "gcc-moderate"

  # --- From Stage-1 (Control Tower / LZA) outputs ---
  network_account_id = data.terraform_remote_state.lza.outputs.network_account_id
  hub_vpc_id         = data.terraform_remote_state.lza.outputs.hub_vpc_id
  transit_gateway_id = data.terraform_remote_state.lza.outputs.transit_gateway_id

  # Dedicated DDI subnets carved from the hub VPC CIDR (one per AZ, must not overlap).
  ddi_subnet_cidrs   = ["10.10.4.0/27", "10.10.4.32/27"]
  availability_zones = ["us-east-1a", "us-east-1b"]

  # --- Members: 2 across two AZs (HA) ---
  member_count = 2

  # Instance type + Marketplace AMI are REGION/VERSION dependent — discover, don't guess:
  #   aws ec2 describe-images --owners aws-marketplace \
  #     --filters 'Name=name,Values=*Infoblox*NIOS*' --query 'Images[].ImageId'
  vnios_instance_type = "m7i.xlarge"            # example only; confirm NIOS supported shape list
  vnios_ami_id        = "ami-0123456789abcdef0" # example only; discover per region

  # Secrets in AWS Secrets Manager (admin pw, temp license, grid shared secret).
  secrets_store_type = "secrets_manager"

  # --- SG source scoping (never 0.0.0.0/0) ---
  mgmt_source_cidrs = ["10.10.0.0/24"]                    # mgmt/bastion subnet
  dns_client_cidrs  = ["10.20.0.0/16", "10.30.0.0/16"]    # spokes (via TGW)
  grid_peer_cidrs   = ["10.10.4.0/26", "192.168.100.0/24"] # DDI subnets + on-prem GM

  # --- Grid join (usual pattern: join AWS members to the on-prem GM) ---
  grid_name       = "CorpGrid"
  grid_master_vip = "192.168.100.10" # on-prem Grid Master VIP

  # --- DNS integration (§8) ---
  r53_resolver_inbound_ip = "10.10.2.4"  # Route 53 Resolver inbound endpoint
  ddi_anycast_vip         = "10.10.4.10" # advertised from both members

  # --- Cross-account discovery role (§5) ---
  discovery_identity_type          = "iam_role"
  discovery_integration_account_id = "111122223333" # Infoblox integration account
  discovery_external_id            = "REPLACE-with-a-strong-external-id"
  discovered_account_ids           = ["444455556666"]
  enable_record_read               = false # EC2/IPAM discovery only by default

  # --- Spoke DHCP-option-set write-through (opt-in) ---
  spoke_vpc_ids          = [] # e.g. [data.terraform_remote_state.lza.outputs.spoke_vpc_id]
  enable_spoke_dns_write = false

  tags = {
    owner      = "network-platform"
    costcenter = "cc-1234"
  }
}

output "ddi_dns_server_ips" {
  value = module.infoblox_ddi.dns_server_ips
}

output "ddi_subnet_ids" {
  value = module.infoblox_ddi.ddi_subnet_ids
}

output "ddi_grid_master_ip" {
  value = module.infoblox_ddi.grid_master_ip
}
