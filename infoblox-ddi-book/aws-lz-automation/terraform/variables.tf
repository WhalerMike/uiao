# variables.tf
# ---------------------------------------------------------------------------
# All canonical inputs from _module-contract.md §3 (names mirror the Azure
# package where they map), followed by the SUPPORTING inputs the implementation
# needs (SG source CIDRs, Resolver inbound IP, discovery scopes, etc.). Contract
# variables are kept first; supporting variables are grouped and labelled.
# ---------------------------------------------------------------------------

########################################################################
# §3 — Canonical contract variables
########################################################################

variable "name_prefix" {
  description = "Prefix for all resource names, e.g. 'ddi' -> ddi-sg, ddi-vnios-use1a, ddi-subnet-use1a, ddi-disco-role (contract §6)."
  type        = string
  default     = "ddi"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,10}$", var.name_prefix))
    error_message = "name_prefix must be lowercase alphanumeric/hyphen, start with a letter, and be 2-11 chars."
  }
}

variable "region" {
  description = "AWS region (COMMERCIAL partition, .com endpoints), e.g. us-east-1. No default — must be supplied. Do NOT use a us-gov-* region (out of scope, contract §1)."
  type        = string

  validation {
    condition     = !can(regex("^us-gov-", var.region))
    error_message = "region must be a commercial-partition region; us-gov-* (AWS GovCloud) is out of scope for this deliverable (contract §1)."
  }
}

variable "environment" {
  description = "Deployment environment: dev | test | prod. Feeds tags and sizing decisions (contract §3)."
  type        = string
  default     = "prod"

  validation {
    condition     = contains(["dev", "test", "prod"], var.environment)
    error_message = "environment must be one of: dev, test, prod."
  }
}

variable "deployment_model" {
  description = <<-EOT
    Control-plane model (contract §1 boundary rule):
      * "grid"          — self-managed vNIOS Grid INSIDE the account/ATO boundary
                          (default; boundary-clean for GCC-Moderate).
      * "universal_ddi" — Infoblox Portal (SaaS) control plane OUTSIDE the boundary;
                          requires outbound 443 to the Portal AND
                          acknowledge_saas_boundary = true (hard-fails otherwise).
  EOT
  type        = string
  default     = "grid"

  validation {
    condition     = contains(["grid", "universal_ddi"], var.deployment_model)
    error_message = "deployment_model must be exactly one of: grid, universal_ddi."
  }
}

variable "acknowledge_saas_boundary" {
  description = <<-EOT
    Must be set to true to permit deployment_model = "universal_ddi". Leaving it
    false (the default) HARD-FAILS the plan when universal_ddi is selected, with a
    message pointing to the FedRAMP/authorization review. This gate exists because
    the Infoblox Portal (SaaS) control plane sits OUTSIDE the ATO boundary
    (contract §1). Has no effect for deployment_model = "grid".
  EOT
  type        = bool
  default     = false
}

variable "compliance_profile" {
  description = "Compliance posture driving tags + control mapping. Defaults to gcc-moderate (FedRAMP Moderate-equivalent on commercial AWS) per contract §1."
  type        = string
  default     = "gcc-moderate"

  validation {
    condition     = length(trimspace(var.compliance_profile)) > 0
    error_message = "compliance_profile must be a non-empty string (default 'gcc-moderate')."
  }
}

variable "network_account_id" {
  description = "AWS account ID of the Network/connectivity account owning the shared-services hub VPC. From Stage-1 (Control Tower / LZA) output. Used for tags/assertions; the provider must already target this account."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.network_account_id))
    error_message = "network_account_id must be a 12-digit AWS account ID."
  }
}

variable "hub_vpc_id" {
  description = "ID of the shared-services (hub) VPC in the Network account. From Stage-1 output. The DDI subnets are created inside this VPC."
  type        = string

  validation {
    condition     = can(regex("^vpc-[0-9a-f]+$", var.hub_vpc_id))
    error_message = "hub_vpc_id must be a VPC ID (vpc-xxxxxxxx)."
  }
}

variable "transit_gateway_id" {
  description = "Transit Gateway ID that spokes attach to (Stage-1 owned). The DDI subnets route spoke/on-prem CIDRs to it; the hub VPC's TGW attachment itself is Stage-1's, not created here."
  type        = string

  validation {
    condition     = can(regex("^tgw-[0-9a-f]+$", var.transit_gateway_id))
    error_message = "transit_gateway_id must be a Transit Gateway ID (tgw-xxxxxxxx)."
  }
}

variable "ddi_subnet_cidrs" {
  description = "One dedicated DDI subnet CIDR PER availability zone, e.g. ['10.10.4.0/27','10.10.4.32/27']. Length must equal availability_zones. Must fit inside the hub VPC CIDR and not overlap existing subnets."
  type        = list(string)

  validation {
    condition     = length(var.ddi_subnet_cidrs) >= 1 && alltrue([for c in var.ddi_subnet_cidrs : can(cidrhost(c, 0))])
    error_message = "ddi_subnet_cidrs must be a non-empty list of valid IPv4 CIDRs."
  }
}

variable "member_count" {
  description = "Number of vNIOS members (grid) / NIOS-X hosts (universal_ddi). >=2 for HA. Spread across availability_zones."
  type        = number
  default     = 2

  validation {
    condition     = var.member_count >= 1 && var.member_count <= 8
    error_message = "member_count must be between 1 and 8 (use >=2 for production HA)."
  }
}

variable "availability_zones" {
  description = "Availability Zones to spread members across, e.g. ['us-east-1a','us-east-1b']. Members are round-robined over this list (contract §3, ch.9 cross-AZ guidance)."
  type        = list(string)

  validation {
    condition     = length(var.availability_zones) >= 1
    error_message = "availability_zones must contain at least one zone; use >=2 for cross-AZ HA."
  }
}

variable "vnios_instance_type" {
  description = <<-EOT
    EC2 instance type for vNIOS / NIOS-X. REGION- AND NIOS-VERSION-DEPENDENT —
    NOT hard-coded. Guidance (see ../02-aws.md §4/§9): M7i / R7i shapes for
    NIOS 9.0.5+; size per member role. Confirm vCPU quota and the supported-shape
    list for your NIOS version and region.
  EOT
  type        = string
  # No default on purpose — you must choose per model/region/version.
}

variable "vnios_ami_id" {
  description = <<-EOT
    AMI ID of the vNIOS / NIOS-X Marketplace image in THIS region. DO NOT invent
    an AMI ID — subscribe to "Infoblox NIOS for AWS" (BYOL or PayGo) in AWS
    Marketplace, then discover the AMI:
      aws ec2 describe-images --owners aws-marketplace \
        --filters 'Name=name,Values=*Infoblox*NIOS*' --query 'Images[].ImageId'
    AMIs are region-specific; supply the one for var.region.
  EOT
  type        = string

  validation {
    condition     = can(regex("^ami-[0-9a-f]+$", var.vnios_ami_id))
    error_message = "vnios_ami_id must be an AMI ID (ami-xxxxxxxx). Discover it with `aws ec2 describe-images`; do not invent one."
  }
}

variable "secrets_store_type" {
  description = "Where module secrets live: 'secrets_manager' (AWS Secrets Manager, default) or 'ssm_parameter_store' (SSM SecureString parameters). The *_secret_name variables are the secret names / parameter paths accordingly."
  type        = string
  default     = "secrets_manager"

  validation {
    condition     = contains(["secrets_manager", "ssm_parameter_store"], var.secrets_store_type)
    error_message = "secrets_store_type must be 'secrets_manager' or 'ssm_parameter_store'."
  }
}

variable "discovery_identity_type" {
  description = "Identity used for AWS->Infoblox discovery/IPAM sync: 'iam_role' (cross-account role assumed by the Infoblox integration account with an ExternalId, preferred) or 'instance_profile' (attach a role to the vNIOS instance, single-account). Contract §5."
  type        = string
  default     = "iam_role"

  validation {
    condition     = contains(["iam_role", "instance_profile"], var.discovery_identity_type)
    error_message = "discovery_identity_type must be 'iam_role' or 'instance_profile'."
  }
}

variable "spoke_vpc_ids" {
  description = "Optional list of spoke VPC IDs whose DHCP option set (domain-name-servers) should point at the DDI anycast VIP. The module only writes them when this is non-empty AND enable_spoke_dns_write=true (contract §8)."
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Extra tags merged with the module-managed tags (contract §6). Module-managed keys win on conflict."
  type        = map(string)
  default     = {}
}

########################################################################
# Supporting variables (NOT in §3, required by the implementation).
# Grouped and commented; keep names stable across artifacts.
########################################################################

# --- SG source scoping (contract §4: never 0.0.0.0/0) ----------------
#
# SER-3 remediation: an exact-string "!contains(list, \"0.0.0.0/0\")" test is
# defeated by splitting the address space into two halves that together cover
# all of IPv4 -- e.g. ["0.0.0.0/1","128.0.0.0/1"], or four /2 blocks -- since
# none of those literal strings equal "0.0.0.0/0". Every source-CIDR variable
# below now floors the accepted prefix length instead of string-matching one
# forbidden literal, which catches the exact case AND the split-halves
# evasion. min_cidr_prefix documents the floor; it cannot be referenced
# inside a `validation` block (Terraform forbids cross-variable references
# there), so the floor is also written as the literal 8 in each condition —
# keep the two in sync if you raise the floor.

variable "min_cidr_prefix" {
  description = <<-EOT
    Shortest IPv4 prefix length accepted in any source-CIDR list. /8 permits a
    large private range while rejecting the split-halves evasion of an exact
    "0.0.0.0/0" test. Raise it (e.g. 16) where the estate allows. Not directly
    referenceable inside a variable's own `validation` block (Terraform
    restriction) -- the CIDR variables below hard-code the same floor (8);
    keep them in sync if this changes.
  EOT
  type        = number
  default     = 8

  validation {
    condition     = var.min_cidr_prefix >= 1 && var.min_cidr_prefix <= 32
    error_message = "min_cidr_prefix must be between 1 and 32."
  }
}

variable "mgmt_source_cidrs" {
  description = "CIDR(s) allowed to reach management ports (443/tcp, and 22/tcp if enabled). Scope tightly to jumpboxes/bastion/mgmt subnets. MUST NOT be 0.0.0.0/0."
  type        = list(string)

  validation {
    condition     = length(var.mgmt_source_cidrs) > 0
    error_message = "mgmt_source_cidrs must be non-empty (contract §4 forbids open management)."
  }

  validation {
    condition = alltrue([
      for c in var.mgmt_source_cidrs :
      can(cidrhost(c, 0)) && tonumber(split("/", c)[1]) >= 8
    ])
    error_message = "Every mgmt_source_cidrs entry must be a valid CIDR with a prefix of /8 or longer. A prefix shorter than /8 (including 0.0.0.0/0 and split-halves pairs like 0.0.0.0/1 + 128.0.0.0/1) is effectively the whole internet."
  }

  validation {
    condition = !alltrue([
      contains(var.mgmt_source_cidrs, "0.0.0.0/1"),
      contains(var.mgmt_source_cidrs, "128.0.0.0/1")
    ])
    error_message = "0.0.0.0/1 together with 128.0.0.0/1 covers the entire IPv4 space."
  }
}

variable "monitoring_source_cidrs" {
  description = "CIDR(s) allowed to reach SNMP (161/udp) when enable_snmp=true. MUST NOT be 0.0.0.0/0."
  type        = list(string)
  default     = []

  validation {
    condition = alltrue([
      for c in var.monitoring_source_cidrs :
      can(cidrhost(c, 0)) && tonumber(split("/", c)[1]) >= 8
    ])
    error_message = "Every monitoring_source_cidrs entry must be a valid CIDR with a prefix of /8 or longer (0.0.0.0/0 and split-halves evasions are rejected)."
  }

  validation {
    condition = !alltrue([
      contains(var.monitoring_source_cidrs, "0.0.0.0/1"),
      contains(var.monitoring_source_cidrs, "128.0.0.0/1")
    ])
    error_message = "0.0.0.0/1 together with 128.0.0.0/1 covers the entire IPv4 space."
  }
}

variable "dns_client_cidrs" {
  description = "CIDR(s) permitted to query DNS (53 tcp+udp) inbound — spokes (reachable via TGW) and on-prem ranges. Prefer explicit spoke/on-prem CIDRs over broad ranges. MUST NOT be 0.0.0.0/0."
  type        = list(string)

  validation {
    condition     = length(var.dns_client_cidrs) > 0
    error_message = "dns_client_cidrs must list at least one spoke/on-prem CIDR."
  }

  validation {
    condition = alltrue([
      for c in var.dns_client_cidrs :
      can(cidrhost(c, 0)) && tonumber(split("/", c)[1]) >= 8
    ])
    error_message = "Every dns_client_cidrs entry must be a valid CIDR with a prefix of /8 or longer (0.0.0.0/0 and split-halves evasions are rejected)."
  }

  validation {
    condition = !alltrue([
      contains(var.dns_client_cidrs, "0.0.0.0/1"),
      contains(var.dns_client_cidrs, "128.0.0.0/1")
    ])
    error_message = "0.0.0.0/1 together with 128.0.0.0/1 covers the entire IPv4 space."
  }
}

variable "grid_peer_cidrs" {
  description = "CIDR(s) of Grid members / Grid Master (e.g. on-prem GM subnet + the DDI subnets) for Grid VPN 1194/udp + Grid comms 2114/tcp. Required when deployment_model='grid'. MUST NOT be 0.0.0.0/0."
  type        = list(string)
  default     = []

  validation {
    condition = alltrue([
      for c in var.grid_peer_cidrs :
      can(cidrhost(c, 0)) && tonumber(split("/", c)[1]) >= 8
    ])
    error_message = "Every grid_peer_cidrs entry must be a valid CIDR with a prefix of /8 or longer (0.0.0.0/0 and split-halves evasions are rejected)."
  }

  validation {
    condition = !alltrue([
      contains(var.grid_peer_cidrs, "0.0.0.0/1"),
      contains(var.grid_peer_cidrs, "128.0.0.0/1")
    ])
    error_message = "0.0.0.0/1 together with 128.0.0.0/1 covers the entire IPv4 space."
  }
}

variable "enable_ssh" {
  description = "Open 22/tcp inbound from mgmt_source_cidrs for SSH admin. Off by default; prefer SSM Session Manager / a bastion."
  type        = bool
  default     = false
}

# --- Optional services -----------------------------------------------

variable "enable_dhcp" {
  description = "Serve DHCP (67-68/udp) from vNIOS. OFF by default — AWS VPC DHCP is option-set based and vNIOS DHCP is uncommon in AWS (contract §4)."
  type        = bool
  default     = false
}

variable "enable_snmp" {
  description = "Open 161/udp inbound from monitoring_source_cidrs for SNMP. Optional (contract §4)."
  type        = bool
  default     = false
}

variable "enable_source_dest_check" {
  description = "EC2 source/dest check on member ENIs. Set false when advertising an anycast/HA service IP that isn't the ENI's own primary IP (contract §9 / ch.9). Default false (anycast-friendly)."
  type        = bool
  default     = false
}

# --- Networking / DNS integration ------------------------------------

variable "r53_resolver_inbound_ip" {
  description = "IP of the Route 53 Resolver INBOUND endpoint (Stage-1/existing). Infoblox members conditionally forward AWS-service names here (contract §8). Leave null to skip conditional-forwarder creation."
  type        = string
  default     = null
}

variable "aws_service_forward_domains" {
  description = "AWS-owned/service domains conditionally forwarded to the Route 53 Resolver inbound endpoint (contract §8). Add your Route 53 private-hosted-zone domains here. Note '<region>.compute.internal' is region-specific."
  type        = list(string)
  default = [
    "amazonaws.com",
    "compute.internal",
  ]
}

variable "ddi_anycast_vip" {
  description = "Anycast/service VIP advertised by the DDI members and written to spoke DHCP option sets. If null, outputs fall back to the members' LAN1 ENI IPs (dns_server_ips)."
  type        = string
  default     = null
}

variable "enable_spoke_dns_write" {
  description = "Write the DDI resolver into spoke VPC DHCP option sets (contract §8). Only takes effect when spoke_vpc_ids is non-empty. Requires the running identity to have ec2:CreateDhcpOptions / ec2:AssociateDhcpOptions on those VPCs."
  type        = bool
  default     = false
}

# --- Discovery identity scoping (contract §5) ------------------------

variable "discovered_account_ids" {
  description = "AWS account IDs to be discovered. The cross-account discovery role is created HERE; replicate it (StackSets / per-account apply) into each of these accounts with the same trust + ExternalId (contract §5). Used for tags/documentation of intended scope."
  type        = list(string)
  default     = []
}

variable "discovery_integration_account_id" {
  description = "AWS account ID of the Infoblox integration account that is trusted to sts:AssumeRole the discovery role. Required when discovery_identity_type='iam_role'."
  type        = string
  default     = null

  validation {
    condition     = var.discovery_integration_account_id == null || can(regex("^[0-9]{12}$", var.discovery_integration_account_id))
    error_message = "discovery_integration_account_id must be a 12-digit AWS account ID."
  }
}

variable "discovery_external_id" {
  description = "ExternalId string required on the discovery role's sts:AssumeRole trust (confused-deputy protection, contract §5). Required when discovery_identity_type='iam_role'. Treat as a shared secret; store it with Infoblox's discovery config."
  type        = string
  default     = null
  sensitive   = true
}

variable "enable_record_read" {
  description = "Grant the discovery role Route 53 READ actions (ListHostedZones/ListResourceRecordSets/GetHostedZone) so Infoblox can sync Route 53 zones (contract §5). Off by default = EC2/IPAM discovery only."
  type        = bool
  default     = false
}

variable "existing_instance_profile_role_arn" {
  description = "When discovery_identity_type='instance_profile', the ARN of an existing role to attach to the vNIOS instances (single-account discovery). This module does not create the instance profile in that mode."
  type        = string
  default     = null
}

# --- Secret names (Secrets Manager name or SSM parameter path) -------

variable "admin_password_secret_name" {
  description = "Secrets Manager secret name / SSM parameter path holding the vNIOS default admin password (bootstrapped via user-data)."
  type        = string
  default     = "ddi/vnios-admin-password"
}

variable "temp_license_secret_name" {
  description = "Secret/parameter holding the vNIOS temp license string(s) for first boot (e.g. 'vnios dns dhcp grid enterprise')."
  type        = string
  default     = "ddi/vnios-temp-license"
}

variable "grid_shared_secret_name" {
  description = "Secret/parameter holding the Grid shared secret used to join members to the Grid (deployment_model='grid')."
  type        = string
  default     = "ddi/grid-shared-secret"
}

variable "saas_join_token_secret_name" {
  description = "Secret/parameter holding the Infoblox Portal (CSP) join token used to enroll NIOS-X hosts (deployment_model='universal_ddi')."
  type        = string
  default     = "ddi/uddi-join-token"
}

# --- Grid join parameters (deployment_model='grid') ------------------

variable "grid_name" {
  description = "Infoblox Grid name the AWS members join (deployment_model='grid'). Typically your existing on-prem Grid name."
  type        = string
  default     = "Infoblox"
}

variable "grid_master_vip" {
  description = "VIP/IP of the Grid Master the AWS members join over 1194/udp + 2114/tcp (deployment_model='grid'). Usually the on-prem GM. Leave null if the first AWS member IS the Grid Master (lab only)."
  type        = string
  default     = null
}

# --- Universal DDI (SaaS) portal parameters --------------------------

variable "infoblox_portal_url" {
  description = "Infoblox Portal (CSP) base URL for NIOS-X enrollment (deployment_model='universal_ddi'). Commercial: https://csp.infoblox.com. Outbound 443 required (contract §1/§4)."
  type        = string
  default     = "https://csp.infoblox.com"
}

# --- EC2 access ------------------------------------------------------

variable "ssh_key_name" {
  description = "Optional EC2 key pair name attached to member instances. vNIOS is administered via its own admin account/user-data; a key pair only matters if enable_ssh=true. Null = no key pair."
  type        = string
  default     = null
}
