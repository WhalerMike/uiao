# variables.tf
# ---------------------------------------------------------------------------
# All canonical inputs from _module-contract.md §3, followed by the SUPPORTING
# inputs the implementation needs (NSG/Security-List source CIDRs, resolver
# endpoint IPs, discovery scopes, Vault secret OCIDs, etc.). Contract variables
# are kept first; supporting variables are grouped and labelled.
# ---------------------------------------------------------------------------

########################################################################
# §3 — Canonical contract variables
########################################################################

variable "name_prefix" {
  description = "Prefix for all resource names, e.g. 'ddi' -> ddi-nsg, ddi-vnios-ad1-fd1, ddi-subnet, ddi-disco-dg (contract §6)."
  type        = string
  default     = "ddi"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,10}$", var.name_prefix))
    error_message = "name_prefix must be lowercase alphanumeric/hyphen, start with a letter, and be 2-11 chars."
  }
}

variable "region" {
  description = "OCI region identifier (COMMERCIAL OC1 realm), e.g. 'us-ashburn-1'. No default — must be supplied."
  type        = string
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
      * "grid"          — self-managed vNIOS Grid INSIDE the tenancy/ATO boundary
                          (default; boundary-clean for FedRAMP Moderate).
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
  description = "Compliance posture driving tags + control mapping. Defaults to fedramp-moderate (on commercial OCI OC1) per contract §1."
  type        = string
  default     = "fedramp-moderate"

  validation {
    condition     = length(trimspace(var.compliance_profile)) > 0
    error_message = "compliance_profile must be a non-empty string (default 'fedramp-moderate')."
  }
}

variable "network_compartment_ocid" {
  description = "OCID of the compartment holding the hub (connectivity) VCN. From Stage-1 (CIS Landing Zone) output. The DDI subnet, NSG/SL, instances, and DNS objects land here."
  type        = string

  validation {
    condition     = can(regex("^ocid1\\.compartment\\.", var.network_compartment_ocid))
    error_message = "network_compartment_ocid must be a compartment OCID (ocid1.compartment...)."
  }
}

variable "tenancy_ocid" {
  description = "Tenancy (root compartment) OCID. Required to create IAM dynamic groups, groups, and policies for the discovery identity (contract §5). These identity resources live in the tenancy/root, not the network compartment."
  type        = string

  validation {
    condition     = can(regex("^ocid1\\.tenancy\\.", var.tenancy_ocid))
    error_message = "tenancy_ocid must be a tenancy OCID (ocid1.tenancy...)."
  }
}

variable "hub_vcn_ocid" {
  description = "OCID of the hub (connectivity) VCN. From Stage-1 output. The DDI subnet is created inside this VCN."
  type        = string

  validation {
    condition     = can(regex("^ocid1\\.vcn\\.", var.hub_vcn_ocid))
    error_message = "hub_vcn_ocid must be a VCN OCID (ocid1.vcn...)."
  }
}

variable "drg_ocid" {
  description = "OCID of the hub-spoke Dynamic Routing Gateway (DRG v2) from Stage-1. Reachability reference for spoke VCNs and the on-prem Grid Master (FastConnect/IPSec). Optional; leave null if routing is managed entirely in Stage-1."
  type        = string
  default     = null
}

variable "ddi_subnet_cidr" {
  description = "CIDR for the dedicated DDI subnet this module creates in the hub VCN, e.g. '10.10.4.0/27'. Must fit inside the hub VCN address space and not overlap existing subnets."
  type        = string

  validation {
    condition     = can(cidrhost(var.ddi_subnet_cidr, 0))
    error_message = "ddi_subnet_cidr must be a valid IPv4 CIDR (e.g. 10.10.4.0/27)."
  }
}

variable "member_count" {
  description = "Number of vNIOS members (grid) / NIOS-X hosts (universal_ddi). >=2 for HA. Spread across availability_domains and fault_domains."
  type        = number
  default     = 2

  validation {
    condition     = var.member_count >= 1 && var.member_count <= 8
    error_message = "member_count must be between 1 and 8 (use >=2 for production HA)."
  }
}

variable "availability_domains" {
  description = <<-EOT
    Availability Domains to spread members across, e.g. ["Uocm:US-ASHBURN-AD-1",
    "Uocm:US-ASHBURN-AD-2"]. Members round-robin over this list. MANY OCI REGIONS
    ARE SINGLE-AD — there, supply one AD and rely on fault_domains for intra-region
    isolation, and add a second region for true DR (../04-oci.md §9).
  EOT
  type        = list(string)

  validation {
    condition     = length(var.availability_domains) >= 1
    error_message = "availability_domains must contain at least one AD name."
  }
}

variable "fault_domains" {
  description = "Fault Domains to spread members across within an AD (always spread across FDs so a rack failure never takes both members). Contract §3, ../04-oci.md §9."
  type        = list(string)
  default     = ["FAULT-DOMAIN-1", "FAULT-DOMAIN-2"]
}

variable "vnios_shape" {
  description = <<-EOT
    OCI FLEXIBLE shape for vNIOS / NIOS-X, e.g. "VM.Standard.E4.Flex" or
    "VM.Standard3.Flex". MODEL- AND REGION-DEPENDENT — NOT hard-coded. Match the
    OCPU/memory (vnios_ocpus / vnios_memory_gbs) to the target vNIOS model spec
    (CP-2205 / TE-V). Validate against the vNIOS-for-OCI spec table for your build.
  EOT
  type        = string
  # No default on purpose — you must choose per model/region.
}

variable "vnios_ocpus" {
  description = "OCPUs assigned to the flexible shape, matched to the vNIOS model's minimum. Verify against the vNIOS-for-OCI spec table."
  type        = number
  default     = 4
}

variable "vnios_memory_gbs" {
  description = "Memory (GB) assigned to the flexible shape, matched to the vNIOS model's minimum."
  type        = number
  default     = 32
}

variable "vnios_image_ocid" {
  description = <<-EOT
    OCID of the vNIOS / NIOS-X CUSTOM IMAGE. OCI has NO Marketplace vNIOS listing:
    obtain the image from Infoblox Support, upload the qcow2/VMDK to an Object
    Storage bucket, and `oci compute image import` it (launch mode Paravirtualized)
    — that produces this OCID. DO NOT invent it; supply your own. Optionally set
    import_image=true to have this module drive the import (see grid.tf).
  EOT
  type        = string
  default     = null
}

variable "vault_ocid" {
  description = "OCID of an EXISTING OCI Vault holding module secrets (admin password, temp license, grid shared secret, join token, discovery key). Individual secrets are referenced by their *_secret_ocid variables below."
  type        = string

  validation {
    condition     = can(regex("^ocid1\\.vault\\.", var.vault_ocid))
    error_message = "vault_ocid must be a Vault OCID (ocid1.vault...)."
  }
}

variable "discovery_identity_type" {
  description = "Identity used for OCI->Infoblox discovery/IPAM sync: 'instance_principal' (preferred; dynamic group) or 'api_key_user' (IAM user + API signing key). Contract §5."
  type        = string
  default     = "instance_principal"

  validation {
    condition     = contains(["instance_principal", "api_key_user"], var.discovery_identity_type)
    error_message = "discovery_identity_type must be 'instance_principal' or 'api_key_user'."
  }
}

variable "spoke_vcn_ocids" {
  description = "Optional list of spoke VCN OCIDs whose resolver forwarding should point at the DDI anycast VIP. The module only writes forwarding rules when this is non-empty AND enable_spoke_dns_write=true (contract §5/§8)."
  type        = list(string)
  default     = []
}

variable "freeform_tags" {
  description = "Extra OCI freeform tags merged with the module-managed tags (contract §6). Module-managed keys win on conflict."
  type        = map(string)
  default     = {}
}

variable "defined_tags" {
  description = "Optional OCI defined tags, keyed 'namespace.key' = 'value'. Applied to taggable resources alongside freeform tags."
  type        = map(string)
  default     = {}
}

########################################################################
# Supporting variables (NOT in §3, required by the implementation).
########################################################################

# --- Security enforcement model + source scoping (contract §4) --------

variable "security_model" {
  description = "How the port rules are enforced: 'nsg' (oci_core_network_security_group, per-VNIC, preferred) or 'security_list' (oci_core_security_list, subnet-wide). Both implement the identical §4 port table."
  type        = string
  default     = "nsg"

  validation {
    condition     = contains(["nsg", "security_list"], var.security_model)
    error_message = "security_model must be 'nsg' or 'security_list'."
  }
}

variable "mgmt_source_cidrs" {
  description = "CIDR(s) allowed to reach management ports (443/tcp, and 22/tcp if enabled). Scope tightly to bastion/mgmt subnets. MUST NOT be 0.0.0.0/0."
  type        = list(string)

  validation {
    condition     = length(var.mgmt_source_cidrs) > 0 && !contains(var.mgmt_source_cidrs, "0.0.0.0/0")
    error_message = "mgmt_source_cidrs must be non-empty and must not contain 0.0.0.0/0 (contract §4 forbids open management)."
  }
}

variable "monitoring_source_cidrs" {
  description = "CIDR(s) allowed to reach SNMP (161/udp) when enable_snmp=true. MUST NOT be 0.0.0.0/0."
  type        = list(string)
  default     = []

  validation {
    condition     = !contains(var.monitoring_source_cidrs, "0.0.0.0/0")
    error_message = "monitoring_source_cidrs must not contain 0.0.0.0/0."
  }
}

variable "dns_client_cidrs" {
  description = "CIDR(s) permitted to query DNS (53 tcp+udp) ingress — spokes and on-prem ranges reached over the DRG. Prefer explicit spoke/on-prem CIDRs over broad ranges. MUST NOT be 0.0.0.0/0."
  type        = list(string)

  validation {
    condition     = length(var.dns_client_cidrs) > 0 && !contains(var.dns_client_cidrs, "0.0.0.0/0")
    error_message = "dns_client_cidrs must list at least one spoke/on-prem CIDR and must not contain 0.0.0.0/0."
  }
}

variable "grid_peer_cidrs" {
  description = "CIDR(s) of Grid members / Grid Master (e.g. on-prem GM subnet + the DDI subnet) for Grid VPN 1194/udp + Grid comms 2114/tcp. Required when deployment_model='grid'."
  type        = list(string)
  default     = []

  validation {
    condition     = !contains(var.grid_peer_cidrs, "0.0.0.0/0")
    error_message = "grid_peer_cidrs must not contain 0.0.0.0/0."
  }
}

variable "enable_ssh" {
  description = "Open 22/tcp ingress from mgmt_source_cidrs for SSH admin. Off by default; prefer OCI Bastion / serial console."
  type        = bool
  default     = false
}

# --- Optional services -----------------------------------------------

variable "enable_dhcp" {
  description = "Serve DHCP (67-68/udp) from vNIOS for on-prem/extranet relay clients. OFF by default — OCI VCN DHCP is platform-managed (contract §4)."
  type        = bool
  default     = false
}

variable "enable_snmp" {
  description = "Open 161/udp ingress from monitoring_source_cidrs for SNMP. Optional (contract §4)."
  type        = bool
  default     = false
}

# --- Networking / DNS integration ------------------------------------

variable "manage_resolver_endpoints" {
  description = "Have this module create the hub VCN resolver's LISTENING + FORWARDING endpoints and forwarding rules (contract §8). Set false if Stage-1 or the platform team owns the resolver and you only reference its endpoint IPs."
  type        = bool
  default     = true
}

variable "hub_resolver_ocid" {
  description = "OCID of the hub VCN's OCI DNS resolver (each VCN has one). Needed to attach LISTENING/FORWARDING endpoints and rules. If null the module looks it up from the hub VCN (see dns.tf)."
  type        = string
  default     = null
}

variable "resolver_endpoint_subnet_ocid" {
  description = "Subnet OCID in which the OCI resolver LISTENING (1 IP) and FORWARDING (2 IPs) endpoints are placed. Often the DDI subnet or a dedicated resolver subnet. Required when manage_resolver_endpoints=true."
  type        = string
  default     = null
}

variable "oci_listening_endpoint_ip" {
  description = "IP of the OCI resolver LISTENING endpoint (Stage-1/existing OR created here). Infoblox members conditionally forward OCI-owned names (*.oraclevcn.com, private zones) to this IP (contract §8). Leave null to skip conditional-forwarder creation."
  type        = string
  default     = null
}

variable "oci_forward_domains" {
  description = "OCI-owned domains conditionally forwarded from Infoblox to the OCI resolver LISTENING endpoint (contract §8)."
  type        = list(string)
  default = [
    "oraclevcn.com",
  ]
}

variable "enterprise_forward_domains" {
  description = "Enterprise domains (and reverse zones) the OCI resolver FORWARDS to the Infoblox members. A catch-all ('.') may be added on the OCI side for full split-horizon (contract §8)."
  type        = list(string)
  default     = ["corp.example"]
}

variable "ddi_anycast_vip" {
  description = "Anycast/service VIP advertised by the DDI members (via BGP over the DRG) or an OCI Load Balancer VIP, used as the DNS service address. If null, outputs fall back to the members' individual VNIC IPs (dns_server_ips)."
  type        = string
  default     = null
}

variable "enable_spoke_dns_write" {
  description = "Write spoke->hub resolver forwarding rules so spokes resolve enterprise names via Infoblox (contract §5/§8). Only takes effect when spoke_vcn_ocids is non-empty."
  type        = bool
  default     = false
}

# --- Discovery identity scoping (contract §5) ------------------------

variable "discovered_compartment_ocids" {
  description = "Compartment OCIDs the discovery identity gets read policies on, to enumerate VCNs/subnets/VNICs/DNS (contract §5). Defaults to [network_compartment_ocid] if empty."
  type        = list(string)
  default     = []
}

variable "enable_record_write" {
  description = "Opt in to Infoblox writing records into OCI DNS: grants 'manage dns-*' on the discovered compartments. Off by default = read-only discovery (contract §5)."
  type        = bool
  default     = false
}

variable "discovery_user_ocid" {
  description = "When discovery_identity_type='api_key_user', the OCID of the pre-created IAM user to add to the discovery group. This module does not create the user's console credentials; supply an existing user."
  type        = string
  default     = null
}

variable "discovery_dynamic_group_matching_rule" {
  description = "Matching rule for the instance-principal dynamic group (discovery_identity_type='instance_principal'), e.g. \"instance.compartment.id = '<network-compartment-ocid>'\" or a tag-based rule. Defaults to matching instances in network_compartment_ocid."
  type        = string
  default     = null
}

# --- OCI Vault secret OCIDs ------------------------------------------

variable "admin_password_secret_ocid" {
  description = "OCID of the OCI Vault secret holding the vNIOS default admin password (bootstrapped via cloud-init/user_data)."
  type        = string
}

variable "temp_license_secret_ocid" {
  description = "OCID of the OCI Vault secret holding the vNIOS temp license string(s) for first boot (e.g. 'vnios dns dhcp grid enterprise')."
  type        = string
}

variable "grid_shared_secret_ocid" {
  description = "OCID of the OCI Vault secret holding the Grid shared secret used to join members to the Grid (deployment_model='grid'). Unused for universal_ddi."
  type        = string
  default     = null
}

variable "saas_join_token_secret_ocid" {
  description = "OCID of the OCI Vault secret holding the Infoblox Portal (CSP) join token used to enroll NIOS-X hosts (deployment_model='universal_ddi'). Unused for grid."
  type        = string
  default     = null
}

# --- Grid join parameters (deployment_model='grid') ------------------

variable "grid_name" {
  description = "Infoblox Grid name the OCI members join (deployment_model='grid'). Typically your existing on-prem Grid name."
  type        = string
  default     = "Infoblox"
}

variable "grid_master_vip" {
  description = "VIP/IP of the Grid Master the OCI members join over 1194/udp + 2114/tcp (deployment_model='grid'). Usually the on-prem GM reached over FastConnect/IPSec via the DRG. Leave null if the first OCI member IS the Grid Master (lab only)."
  type        = string
  default     = null
}

# --- Universal DDI (SaaS) portal parameters --------------------------

variable "infoblox_portal_url" {
  description = "Infoblox Portal (CSP) host for NIOS-X enrollment (deployment_model='universal_ddi'). Commercial: csp.infoblox.com (scheme added at runtime). Outbound 443 required (contract §1/§4)."
  type        = string
  default     = "csp.infoblox.com"
}

# --- Image import (optional) -----------------------------------------

variable "import_image" {
  description = "Have this module drive the vNIOS custom-image import from Object Storage (creates an oci_core_image, see grid.tf). If false (default) you supply a pre-imported vnios_image_ocid."
  type        = bool
  default     = false
}

variable "image_source_uri" {
  description = "Object Storage URI of the uploaded vNIOS qcow2/VMDK, used only when import_image=true. Form: n/<namespace>/b/<bucket>/o/<object> or a pre-authenticated request URI. Supply your own."
  type        = string
  default     = null
}

# --- Instance admin ---------------------------------------------------

variable "admin_username" {
  description = "Metadata SSH username set on the instance. vNIOS is administered via its own 'admin' account/user_data; this satisfies the OCI instance metadata contract."
  type        = string
  default     = "opc"
}

variable "data_volume_size_gbs" {
  description = "Size (GB) of the optional vNIOS data block volume attached per member (NIOS DB / reporting disk). 0 (default) skips the block volume; set to the model's published disk requirement in production."
  type        = number
  default     = 0
}
