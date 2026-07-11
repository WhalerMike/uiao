# discovery.tf
# ---------------------------------------------------------------------------
# Least-privilege discovery identity for AWS -> Infoblox IPAM sync (contract §5).
#
# Preferred: a CROSS-ACCOUNT IAM ROLE (discovery_identity_type="iam_role")
# assumed by the Infoblox INTEGRATION account, with an ExternalId condition
# (confused-deputy protection). Least-priv custom policy — NOT the broad
# AWS-managed *ReadOnlyAccess policies. ZERO data-plane access.
#
# Fallback: an INSTANCE PROFILE (discovery_identity_type="instance_profile")
# attached to the vNIOS instances for single-account discovery; the module wraps
# an EXISTING role ARN you supply (it does not create the role in that mode).
#
# NOTE (multi-account): the cross-account role is created HERE, in the account
# this module runs in. To discover OTHER accounts, replicate this role (same
# trust + ExternalId + policy) into each of them via CloudFormation StackSets or
# a per-account apply. var.discovered_account_ids records the intended scope.
# ---------------------------------------------------------------------------

locals {
  make_role    = var.discovery_identity_type == "iam_role"
  make_profile = var.discovery_identity_type == "instance_profile"

  # Instance-profile name attached to member instances (grid.tf/universal_ddi.tf).
  # Null in cross-account role mode (no profile on the appliances then).
  member_instance_profile_name = local.make_profile ? aws_iam_instance_profile.disco[0].name : null

  # Canonical identity id emitted as output discovery_identity_id (§7): the role
  # ARN (iam_role) or the supplied instance-profile role ARN.
  disco_identity_id = local.make_role ? try(aws_iam_role.disco[0].arn, null) : var.existing_instance_profile_role_arn

  # Least-privilege read actions (contract §5). Route 53 read is opt-in.
  disco_ec2_actions = [
    "ec2:DescribeVpcs",
    "ec2:DescribeSubnets",
    "ec2:DescribeInstances",
    "ec2:DescribeNetworkInterfaces",
    "ec2:DescribeAvailabilityZones",
    "ec2:DescribeRegions",
    "ec2:DescribeTags",
  ]
  disco_route53_actions = [
    "route53:ListHostedZones",
    "route53:ListResourceRecordSets",
    "route53:GetHostedZone",
  ]
}

# Hard-fail (at plan) if the selected discovery mode is missing its required inputs.
# Preconditions on a terraform_data resource fail the PLAN (a `check` would warn).
resource "terraform_data" "discovery_guard" {
  input = var.discovery_identity_type

  lifecycle {
    precondition {
      condition = !local.make_role || (
        var.discovery_integration_account_id != null && var.discovery_external_id != null
      )
      error_message = "discovery_identity_type='iam_role' requires discovery_integration_account_id and discovery_external_id (ExternalId) — contract §5."
    }
    precondition {
      condition     = !local.make_profile || var.existing_instance_profile_role_arn != null
      error_message = "discovery_identity_type='instance_profile' requires existing_instance_profile_role_arn (this module does not create the role in that mode)."
    }
  }
}

# =====================================================================
# Cross-account discovery role (discovery_identity_type = "iam_role")
# =====================================================================
resource "aws_iam_role" "disco" {
  count = local.make_role ? 1 : 0
  name  = local.disco_role_name
  tags  = local.tags

  # Trust: only the Infoblox integration account may assume this role, and ONLY
  # when it presents the agreed ExternalId. This is the confused-deputy guard.
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { AWS = "arn:aws:iam::${var.discovery_integration_account_id}:root" }
      Action    = "sts:AssumeRole"
      Condition = { StringEquals = { "sts:ExternalId" = var.discovery_external_id } }
    }]
  })
}

resource "aws_iam_policy" "disco" {
  count       = local.make_role ? 1 : 0
  name        = "${local.disco_role_name}-policy"
  description = "Infoblox vDiscovery least-privilege read (ec2:Describe*, tags, optional route53 read). No data-plane access (contract §5)."
  tags        = local.tags

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      [{
        Sid      = "Ec2ReadForDiscovery"
        Effect   = "Allow"
        Action   = local.disco_ec2_actions
        Resource = "*" # ec2:Describe* does not support resource-level scoping
      }],
      var.enable_record_read ? [{
        Sid      = "Route53ReadForZoneSync"
        Effect   = "Allow"
        Action   = local.disco_route53_actions
        Resource = "*"
      }] : [],
    )
  })
}

resource "aws_iam_role_policy_attachment" "disco" {
  count      = local.make_role ? 1 : 0
  role       = aws_iam_role.disco[0].name
  policy_arn = aws_iam_policy.disco[0].arn
}

# =====================================================================
# Instance-profile mode (single-account discovery)
# =====================================================================
# Wrap an EXISTING role (existing_instance_profile_role_arn) in an instance
# profile attached to the vNIOS members. The role's policy should carry the same
# least-priv read actions above.
resource "aws_iam_instance_profile" "disco" {
  count = local.make_profile ? 1 : 0
  name  = "${local.disco_role_name}-profile"
  role  = reverse(split("/", var.existing_instance_profile_role_arn))[0] # role NAME from ARN
  tags  = local.tags
}

# =====================================================================
# INFOBLOX vDISCOVERY — CONFIG PLACEHOLDER
# =====================================================================
# The IAM above grants the credential; the Infoblox SIDE of discovery is
# configured on the control plane, not in AWS. There is no first-class
# "infoblox_vdiscovery_job" resource in the infobloxopen/infoblox provider today,
# so this is an explicit API/UI handoff:
#
#   * vNIOS Grid  -> Cloud Network Automation "vDiscovery job" pointed at each
#                    account/region, authenticating by ASSUMING the cross-account
#                    role above (role ARN + ExternalId). A single job can span
#                    multiple accounts of an AWS Organization (NIOS 9.0.4+).
#                    Configured via WAPI (POST /wapi/vX/vdiscoverytask) or the UI.
#   * Universal   -> Portal "Universal Cloud" AWS source using the same role +
#                    ExternalId; configured through the CSP API/UI.
#
# Sketch of the WAPI handoff (uncomment + wire real values / a restapi provider):
#
# resource "null_resource" "vdiscovery_job" {
#   triggers = { accounts = join(",", var.discovered_account_ids) }
#   provisioner "local-exec" {
#     command = "curl -sS -u \"$IB_USER:$IB_PASS\" -X POST \\
#       $GRID_MASTER/wapi/v2.12/vdiscoverytask \\
#       -d 'name=aws-disco&member=infoblox.localdomain&credential_type=AWS&role_arn=${local.disco_identity_id}'"
#   }
# }
