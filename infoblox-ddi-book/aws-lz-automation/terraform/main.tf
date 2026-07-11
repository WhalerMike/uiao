# main.tf
# ---------------------------------------------------------------------------
# Locals, module-managed tags (contract §6), the dedicated DDI subnets in the
# hub VPC, their route table (spoke/on-prem CIDRs -> Transit Gateway), the
# HARD-FAIL boundary guard for the universal_ddi (SaaS) path, and the reads of
# module secrets from Secrets Manager / SSM Parameter Store.
#
# Resource layout across files:
#   main.tf           — locals, tags, subnets, route table, boundary guard, secrets
#   securitygroups.tf — Security Group + rules (contract §4), default-deny in AND out
#   grid.tf           — vNIOS Grid members         (deployment_model="grid")
#   universal_ddi.tf  — NIOS-X hosts + Portal join  (deployment_model="universal_ddi")
#   discovery.tf      — cross-account IAM discovery role + least-priv policy (contract §5)
#   dns.tf            — conditional forwarders + spoke DHCP option set (contract §8)
#   outputs.tf        — canonical outputs (contract §7)
# ---------------------------------------------------------------------------

locals {
  # --- Naming convention (contract §6): ${name_prefix}-<role>-<zone/index> ---
  sg_name          = "${var.name_prefix}-sg"
  disco_role_name  = "${var.name_prefix}-disco-role"
  member_base_name = "${var.name_prefix}-vnios" # grid members: ddi-vnios-use1a...
  niosx_base_name  = "${var.name_prefix}-niosx" # uddi hosts:   ddi-niosx-1...

  # --- Model flags ------------------------------------------------------
  is_grid = var.deployment_model == "grid"
  is_uddi = var.deployment_model == "universal_ddi"
  use_sm  = var.secrets_store_type == "secrets_manager"

  # --- Subnet planning: one DDI subnet per AZ ---------------------------
  # zip availability_zones with ddi_subnet_cidrs by index (lengths must match;
  # enforced by the check block below). Keyed by AZ for stable addressing.
  subnet_by_az = {
    for idx, az in var.availability_zones : az => var.ddi_subnet_cidrs[idx]
    if idx < length(var.ddi_subnet_cidrs)
  }
  az_label = { for az in var.availability_zones : az => replace(az, "-", "") } # us-east-1a -> useast1a

  # --- Member -> zone/subnet round-robin --------------------------------
  member_indexes  = range(var.member_count)
  member_zone_for = { for i in local.member_indexes : i => var.availability_zones[i % length(var.availability_zones)] }
  # Per-member name label: clean ddi-vnios-<azcode> when one member per zone,
  # else append the index to keep names unique (contract §6).
  member_label = {
    for i in local.member_indexes :
    i => (
      var.member_count <= length(var.availability_zones)
      ? local.az_label[local.member_zone_for[i]]
      : format("%s-%d", local.az_label[local.member_zone_for[i]], i)
    )
  }

  # --- Module-managed tags (contract §6) --------------------------------
  # These keys are authoritative; caller tags are merged UNDER them.
  managed_tags = {
    workload           = "infoblox-ddi"
    layer              = "connectivity-ddi"
    compliance_profile = var.compliance_profile
    deployment_model   = var.deployment_model
    managed_by         = "terraform"
    environment        = var.environment
  }
  tags = merge(var.tags, local.managed_tags)

  # --- Member DNS (LAN1) IPs (populated by grid.tf OR universal_ddi.tf) --
  # Exactly one of these collections is non-empty depending on deployment_model.
  member_dns_ips = local.is_grid ? (
    aws_network_interface.grid_lan1[*].private_ip
    ) : (
    aws_network_interface.niosx_lan1[*].private_ip
  )

  # Grid Master IP (grid only, contract §7). Supplied on-prem VIP is authoritative;
  # else fall back to the first AWS member (lab/greenfield where it is the GM).
  grid_master_ip = local.is_grid ? try(
    coalesce(var.grid_master_vip, aws_network_interface.grid_lan1[0].private_ip),
    null
  ) : null

  # Preferred spoke resolver: anycast VIP; fall back to member LAN1 IPs.
  effective_dns_target = var.ddi_anycast_vip != null ? [var.ddi_anycast_vip] : local.member_dns_ips

  # Secrets resolved from the chosen store (see data sources at the bottom).
  admin_password    = local.use_sm ? data.aws_secretsmanager_secret_version.admin[0].secret_string : data.aws_ssm_parameter.admin[0].value
  temp_license      = local.use_sm ? data.aws_secretsmanager_secret_version.temp_license[0].secret_string : data.aws_ssm_parameter.temp_license[0].value
  grid_shared_secret = local.is_grid ? (local.use_sm ? data.aws_secretsmanager_secret_version.grid_shared[0].secret_string : data.aws_ssm_parameter.grid_shared[0].value) : null
  saas_join_token    = local.is_uddi ? (local.use_sm ? data.aws_secretsmanager_secret_version.saas_join[0].secret_string : data.aws_ssm_parameter.saas_join[0].value) : null
}

# Hard-fail (at plan) if the subnet/AZ lists don't line up 1:1. A precondition on
# a terraform_data resource fails the PLAN (a `check` block would only warn).
resource "terraform_data" "input_guard" {
  input = length(var.ddi_subnet_cidrs)

  lifecycle {
    precondition {
      condition     = length(var.ddi_subnet_cidrs) == length(var.availability_zones)
      error_message = "ddi_subnet_cidrs must have exactly one CIDR per availability_zone (got ${length(var.ddi_subnet_cidrs)} CIDRs vs ${length(var.availability_zones)} AZs)."
    }
  }
}

# ---------------------------------------------------------------------------
# BOUNDARY GUARD (contract §1) — HARD FAIL.
# deployment_model="universal_ddi" routes the control plane through the Infoblox
# Portal (SaaS), which sits OUTSIDE the ATO boundary and needs outbound 443.
# That path is only permitted with an explicit acknowledge_saas_boundary=true.
# A precondition here fails the PLAN (not just apply).
# ---------------------------------------------------------------------------
resource "terraform_data" "boundary_guard" {
  input = var.deployment_model

  lifecycle {
    precondition {
      condition = !(var.deployment_model == "universal_ddi" && var.acknowledge_saas_boundary == false)
      error_message = join("\n", [
        "BOUNDARY VIOLATION: deployment_model = \"universal_ddi\" selects the Infoblox",
        "Portal (SaaS) control plane, which is OUTSIDE the ATO / GCC-Moderate boundary",
        "and requires OUTBOUND 443 to the Infoblox Portal (contract §1).",
        "",
        "This path is disabled until it is explicitly authorized. To proceed you MUST:",
        "  1. Complete the FedRAMP/authorization review for the SaaS control-plane egress,",
        "     and confirm the Portal SaaS offering's authorization status is acceptable",
        "     for this system's boundary; then",
        "  2. Set  acknowledge_saas_boundary = true.",
        "",
        "For a boundary-clean deployment, use deployment_model = \"grid\" (the default),",
        "which keeps the vNIOS Grid control plane INSIDE the account/ATO boundary.",
      ])
    }
  }
}

# ---------------------------------------------------------------------------
# Dedicated DDI subnets, one per AZ, created by THIS module inside the Stage-1
# hub VPC. The hub VPC and the Route 53 Resolver endpoint subnets are NOT
# created here (Stage-1 / existing). Naming: ddi-subnet-<azcode> (contract §6).
# ---------------------------------------------------------------------------
resource "aws_subnet" "ddi" {
  for_each          = local.subnet_by_az
  vpc_id            = var.hub_vpc_id
  availability_zone = each.key
  cidr_block        = each.value

  tags = merge(local.tags, { Name = "${var.name_prefix}-subnet-${local.az_label[each.key]}" })
}

# ---------------------------------------------------------------------------
# Route table for the DDI subnets: the VPC-local route is implicit; add routes
# for spoke + on-prem CIDRs toward the Transit Gateway so members are reachable
# from the spokes and can reach on-prem Grid peers. The hub VPC's TGW ATTACHMENT
# is Stage-1 owned; we only add routes on OUR subnets' route table.
# ---------------------------------------------------------------------------
resource "aws_route_table" "ddi" {
  vpc_id = var.hub_vpc_id
  tags   = merge(local.tags, { Name = "${var.name_prefix}-rt" })
}

resource "aws_route_table_association" "ddi" {
  for_each       = aws_subnet.ddi
  subnet_id      = each.value.id
  route_table_id = aws_route_table.ddi.id
}

# Spoke/on-prem CIDRs -> TGW. De-duplicated union of DNS clients + Grid peers.
resource "aws_route" "to_tgw" {
  for_each               = toset(distinct(concat(var.dns_client_cidrs, var.grid_peer_cidrs)))
  route_table_id         = aws_route_table.ddi.id
  destination_cidr_block = each.value
  transit_gateway_id     = var.transit_gateway_id
}

# ---------------------------------------------------------------------------
# Module secrets, read from the chosen store (Secrets Manager OR SSM Parameter
# Store). These read EXISTING secrets — the module does not create them. Values
# feed user-data (grid.tf / universal_ddi.tf). Never emitted as plaintext output.
# ---------------------------------------------------------------------------

# ---- Secrets Manager variant ----
data "aws_secretsmanager_secret_version" "admin" {
  count     = local.use_sm ? 1 : 0
  secret_id = var.admin_password_secret_name
}
data "aws_secretsmanager_secret_version" "temp_license" {
  count     = local.use_sm ? 1 : 0
  secret_id = var.temp_license_secret_name
}
data "aws_secretsmanager_secret_version" "grid_shared" {
  count     = local.use_sm && local.is_grid ? 1 : 0
  secret_id = var.grid_shared_secret_name
}
data "aws_secretsmanager_secret_version" "saas_join" {
  count     = local.use_sm && local.is_uddi ? 1 : 0
  secret_id = var.saas_join_token_secret_name
}

# ---- SSM Parameter Store variant (SecureString) ----
data "aws_ssm_parameter" "admin" {
  count           = local.use_sm ? 0 : 1
  name            = var.admin_password_secret_name
  with_decryption = true
}
data "aws_ssm_parameter" "temp_license" {
  count           = local.use_sm ? 0 : 1
  name            = var.temp_license_secret_name
  with_decryption = true
}
data "aws_ssm_parameter" "grid_shared" {
  count           = !local.use_sm && local.is_grid ? 1 : 0
  name            = var.grid_shared_secret_name
  with_decryption = true
}
data "aws_ssm_parameter" "saas_join" {
  count           = !local.use_sm && local.is_uddi ? 1 : 0
  name            = var.saas_join_token_secret_name
  with_decryption = true
}
