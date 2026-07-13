# variables.tf
# ---------------------------------------------------------------------------
# All canonical inputs from _module-contract.md §3 (identical names in TF and
# Bicep), followed by the SUPPORTING inputs the implementation needs (NSG source
# CIDRs, Private Resolver IP, discovery scopes, etc.). Contract variables are
# kept first and verbatim; supporting variables are grouped and labelled.
# ---------------------------------------------------------------------------

########################################################################
# §3 — Canonical contract variables
########################################################################

variable "name_prefix" {
  description = "Prefix for all resource names, e.g. 'ddi' -> ddi-nsg, ddi-vnios-z1, ddi-subnet, ddi-disco-mi (contract §6)."
  type        = string
  default     = "ddi"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,10}$", var.name_prefix))
    error_message = "name_prefix must be lowercase alphanumeric/hyphen, start with a letter, and be 2-11 chars (keeps generated resource names within Azure limits)."
  }
}

variable "location" {
  description = "Azure region (COMMERCIAL cloud, .com endpoints). No default — must be supplied."
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
      * "grid"          — self-managed vNIOS Grid INSIDE the tenant/ATO boundary
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
  description = "Compliance posture driving tags + control mapping. Defaults to gcc-moderate (FedRAMP Moderate-equivalent on commercial Azure) per contract §1."
  type        = string
  default     = "gcc-moderate"

  validation {
    # Kept permissive but non-empty; gcc-moderate is the contract default. Add
    # your own enum here if you standardise on a fixed profile set.
    condition     = length(trimspace(var.compliance_profile)) > 0
    error_message = "compliance_profile must be a non-empty string (default 'gcc-moderate')."
  }
}

variable "hub_resource_group_name" {
  description = "Resource group of the Connectivity hub VNet. From Stage-1 (ALZ Accelerator) output hub_resource_group_name."
  type        = string
}

variable "hub_vnet_id" {
  description = "Full resource ID of the Connectivity hub VNet. From Stage-1 output hub_vnet_id. The DDI subnet is created inside this VNet."
  type        = string

  validation {
    condition     = can(regex("/subscriptions/.+/resourceGroups/.+/providers/Microsoft.Network/virtualNetworks/.+", var.hub_vnet_id))
    error_message = "hub_vnet_id must be a full Azure VNet resource ID (/subscriptions/.../virtualNetworks/<name>)."
  }
}

variable "ddi_subnet_address_prefix" {
  description = "CIDR for the dedicated DDI subnet this module creates in the hub VNet, e.g. '10.10.4.0/27'. Must fit inside the hub VNet address space and not overlap existing subnets."
  type        = string

  validation {
    condition     = can(cidrhost(var.ddi_subnet_address_prefix, 0))
    error_message = "ddi_subnet_address_prefix must be a valid IPv4 CIDR (e.g. 10.10.4.0/27)."
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
  description = "Availability Zones to spread members across. Members are round-robined over this list (contract §3, ch.9 cross-AZ guidance)."
  type        = list(string)
  default     = ["1", "2"]

  validation {
    condition     = length(var.availability_zones) >= 1
    error_message = "availability_zones must contain at least one zone; use >=2 for cross-AZ HA."
  }
}

variable "vnios_vm_sku" {
  description = <<-EOT
    Azure VM size for vNIOS / NIOS-X. REGION- AND NIOS-VERSION-DEPENDENT — NOT
    hard-coded. Guidance (see ../01-azure.md §4/§9): Esv3-series (NIOS < 9.0.6),
    Esv5-series (NIOS 9.0.5+), DS-series for reporting members. Confirm vCPU
    quota and the supported-appliance list for your NIOS version and region.
  EOT
  type        = string
  # No default on purpose — you must choose per model/region/version.
}

variable "vnios_image" {
  description = <<-EOT
    Azure Marketplace image reference for vNIOS / NIOS-X. DO NOT hard-code a
    version — discover the current plan with:
      az vm image list --publisher infoblox --all -o table
    Typical offer is the 'infoblox_nios_on_azure' listing (BYOL or PAYG). The
    `plan_*` fields must match the Marketplace plan for the agreement + VM plan
    block; often they equal publisher/offer/sku but verify per listing.
  EOT
  type = object({
    publisher = string
    offer     = string
    sku       = string
    version   = string           # e.g. "latest" or a pinned build; verify.
    plan_name = optional(string) # defaults to sku if unset
  })
}

variable "key_vault_id" {
  description = "Resource ID of an EXISTING Key Vault holding module secrets (admin password, grid shared secret, join token, discovery creds). Secret names are set via *_secret_name variables below."
  type        = string

  validation {
    condition     = can(regex("/subscriptions/.+/resourceGroups/.+/providers/Microsoft.KeyVault/vaults/.+", var.key_vault_id))
    error_message = "key_vault_id must be a full Key Vault resource ID."
  }
}

variable "discovery_identity_type" {
  description = "Identity used for Azure->Infoblox discovery/IPAM sync: 'user_assigned_mi' (preferred) or 'service_principal' (Entra app registration). Contract §5."
  type        = string
  default     = "user_assigned_mi"

  validation {
    condition     = contains(["user_assigned_mi", "service_principal"], var.discovery_identity_type)
    error_message = "discovery_identity_type must be 'user_assigned_mi' or 'service_principal'."
  }
}

variable "spoke_vnet_ids" {
  description = "Optional list of spoke VNet resource IDs whose dns_servers should point at the DDI anycast VIP. The module only writes dns_servers when this is non-empty AND enable_spoke_dns_write=true (which requires Network Contributor, contract §5/§8)."
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
# Grouped and commented; keep names stable across TF and Bicep.
########################################################################

# --- NSG source scoping (contract §4: never 0.0.0.0/0) ---------------

variable "mgmt_source_cidrs" {
  description = "CIDR(s) allowed to reach management ports (443/tcp, and 22/tcp if enabled). Scope tightly to jumpboxes/bastion/mgmt subnets. MUST NOT be 0.0.0.0/0."
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
  description = "CIDR(s) permitted to query DNS (53 tcp+udp) inbound — spokes and on-prem ranges. Prefer explicit spoke/on-prem CIDRs over broad ranges."
  type        = list(string)

  validation {
    condition     = length(var.dns_client_cidrs) > 0
    error_message = "dns_client_cidrs must list at least one spoke/on-prem CIDR permitted to query DNS."
  }
}

variable "grid_peer_cidrs" {
  description = "CIDR(s) of Grid members / Grid Master (e.g. on-prem GM subnet + the DDI subnet) for Grid VPN 1194/udp + Grid comms 2114/tcp. Used only when deployment_model='grid'."
  type        = list(string)
  default     = []
}

variable "enable_ssh" {
  description = "Open 22/tcp inbound from mgmt_source_cidrs for SSH admin. Off by default; prefer Bastion/serial console."
  type        = bool
  default     = false
}

# --- Optional services -----------------------------------------------

variable "enable_dhcp" {
  description = "Serve DHCP (67-68/udp) from vNIOS. OFF by default — Azure VNet DHCP is platform-managed and vNIOS DHCP is uncommon in Azure (contract §4)."
  type        = bool
  default     = false
}

variable "enable_snmp" {
  description = "Open 161/udp inbound from monitoring_source_cidrs for SNMP. Optional (contract §4)."
  type        = bool
  default     = false
}

variable "enable_accelerated_networking" {
  description = "Enable Accelerated Networking on member NICs for line-rate DNS. Region/VM-SKU dependent — verify support for your vnios_vm_sku (../01-azure.md §4)."
  type        = bool
  default     = true
}

# --- Networking / DNS integration ------------------------------------

variable "private_resolver_inbound_ip" {
  description = "IP of the Azure DNS Private Resolver INBOUND endpoint (Stage-1/existing). Infoblox members conditionally forward Azure-service names here (contract §8). Leave null to skip conditional-forwarder creation."
  type        = string
  default     = null
}

variable "azure_service_forward_domains" {
  description = "Azure private/privatelink domains conditionally forwarded to the Private Resolver inbound endpoint (contract §8)."
  type        = list(string)
  default = [
    "privatelink.blob.core.windows.net",
    "privatelink.database.windows.net",
    "privatelink.vaultcore.azure.net",
    "azure.com",
  ]
}

variable "ddi_anycast_vip" {
  description = "Anycast/service VIP advertised by the DDI members and written to spoke dns_servers. If null, outputs fall back to the members' individual NIC IPs (dns_server_ips)."
  type        = string
  default     = null
}

variable "enable_spoke_dns_write" {
  description = "Write dns_servers on spoke VNets (requires Network Contributor on those spokes, contract §5/§8). Only takes effect when spoke_vnet_ids is non-empty."
  type        = bool
  default     = false
}

# --- Discovery identity scoping (contract §5) ------------------------

variable "discovered_subscription_ids" {
  description = "Subscription IDs (bare GUIDs) the discovery identity gets READER on, to enumerate VNets/subnets/NICs/tags (contract §5)."
  type        = list(string)
  default     = []
}

variable "private_dns_zone_rg_ids" {
  description = "Resource-group IDs holding Azure Private DNS zones. Discovery identity gets 'Private DNS Zone Contributor' here ONLY when enable_record_write=true (record-write is opt-in, contract §5)."
  type        = list(string)
  default     = []
}

variable "enable_record_write" {
  description = "Opt in to Infoblox writing records into Azure Private DNS: grants 'Private DNS Zone Contributor' on private_dns_zone_rg_ids. Off by default = read-only discovery (contract §5)."
  type        = bool
  default     = false
}

variable "existing_service_principal_object_id" {
  description = "When discovery_identity_type='service_principal', the objectId (principalId) of the pre-created Entra app registration's service principal to assign roles to. This module does not create Entra app registrations."
  type        = string
  default     = null
}

# --- Key Vault secret names ------------------------------------------

variable "admin_password_secret_name" {
  description = "Key Vault secret name holding the vNIOS default admin password (bootstrapped via cloud-init/user-data)."
  type        = string
  default     = "ddi-vnios-admin-password"
}

variable "temp_license_secret_name" {
  description = "Key Vault secret name holding the vNIOS temp license string(s) for first boot (e.g. 'vnios dns dhcp grid enterprise')."
  type        = string
  default     = "ddi-vnios-temp-license"
}

variable "grid_shared_secret_name" {
  description = "Key Vault secret name holding the Grid shared secret used to join members to the Grid (deployment_model='grid')."
  type        = string
  default     = "ddi-grid-shared-secret"
}

variable "saas_join_token_secret_name" {
  description = "Key Vault secret name holding the Infoblox Portal (CSP) join token used to enroll NIOS-X hosts (deployment_model='universal_ddi')."
  type        = string
  default     = "ddi-uddi-join-token"
}

# --- Grid join parameters (deployment_model='grid') ------------------

variable "grid_name" {
  description = "Infoblox Grid name the Azure members join (deployment_model='grid'). Typically your existing on-prem Grid name."
  type        = string
  default     = "Infoblox"
}

variable "grid_master_vip" {
  description = "VIP/IP of the Grid Master the Azure members join over 1194/udp + 2114/tcp (deployment_model='grid'). Usually the on-prem GM. Leave null if the first Azure member IS the Grid Master (lab only)."
  type        = string
  default     = null
}

# --- Universal DDI (SaaS) portal parameters --------------------------

variable "infoblox_portal_url" {
  description = "Infoblox Portal (CSP) base URL for NIOS-X enrollment (deployment_model='universal_ddi'). Commercial: https://csp.infoblox.com. Outbound 443 required (contract §1/§4)."
  type        = string
  default     = "https://csp.infoblox.com"
}

# --- Marketplace ------------------------------------------------------

variable "accept_marketplace_agreement" {
  description = "Have Terraform accept the Azure Marketplace agreement for the vNIOS/NIOS-X image plan. Set false if the agreement is already accepted in the subscription (re-accepting an accepted plan is a no-op but the resource is easier to omit)."
  type        = bool
  default     = true
}

variable "admin_username" {
  description = "Local admin username set on the VM os_profile. vNIOS is administered via its own 'admin' account/user-data; this satisfies the Azure VM contract."
  type        = string
  default     = "azinfoblox"
}

# --- Scoped egress (SC-7) --------------------------------------------
variable "infoblox_portal_cidrs" {
  description = "Destination CIDRs for the Infoblox Universal DDI SaaS portal 443/tcp egress (universal_ddi only). SCOPE to the published Infoblox Portal (csp.infoblox.com) ranges for production; the open default ['0.0.0.0/0'] is lab-only. Replaces the 'Internet' service tag so egress is an explicit, documented CIDR set."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}
