# variables.tf
# ---------------------------------------------------------------------------
# All canonical inputs from _module-contract.md §3 (mapped from the Azure
# package), followed by the SUPPORTING inputs the implementation needs
# (vCenter/NSX connection, DFW source CIDRs, member IP addressing, discovery
# scopes, secrets from Vault/CI). Contract variables are kept first and verbatim;
# supporting variables are grouped and labelled.
# ---------------------------------------------------------------------------

########################################################################
# §3 — Canonical contract variables
########################################################################

variable "name_prefix" {
  description = "Prefix for all resource names, e.g. 'ddi' -> ddi-vnios-h1, ddi-mgmt-group, ddi-disco-role (contract §6)."
  type        = string
  default     = "ddi"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,10}$", var.name_prefix))
    error_message = "name_prefix must be lowercase alphanumeric/hyphen, start with a letter, and be 2-11 chars."
  }
}

variable "vsphere_datacenter" {
  description = "vSphere datacenter name that contains the management/edge domain. Maps from the Azure 'location'. No default — must be supplied."
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
      * "grid"          — self-managed vNIOS Grid INSIDE the SDDC/ATO boundary
                          (default; boundary-clean and the natural fit — the Grid
                          Master usually already lives in the management domain).
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
  description = "Compliance posture driving tags + control mapping. Defaults to fedramp-moderate (self-contained VCF private cloud) per contract §1."
  type        = string
  default     = "fedramp-moderate"

  validation {
    condition     = length(trimspace(var.compliance_profile)) > 0
    error_message = "compliance_profile must be a non-empty string (default 'fedramp-moderate')."
  }
}

variable "compute_cluster" {
  description = "Target vSphere compute cluster in the management/edge domain where the vNIOS members run. Maps from the Azure hub_resource_group_name."
  type        = string
}

variable "resource_pool" {
  description = "Optional resource pool for the member VMs. If null, the cluster's root resource pool is used."
  type        = string
  default     = null
}

variable "datastore" {
  description = "Datastore for the member OS/DB disks. Size for the chosen appliance model (contract §9; see the vNIOS-for-VMware install guide)."
  type        = string
}

variable "management_portgroup" {
  description = "Management distributed port group (dvPortGroup) the member vNICs attach to. Maps from the Azure hub_vnet_id. Members use VMXNET3 on this port group."
  type        = string
}

variable "ddi_mgmt_network_cidr" {
  description = "CIDR of the management network the members sit on, e.g. '10.20.10.0/24'. Maps from the Azure ddi_subnet_address_prefix. Used for DFW scoping and static-IP sanity (member IPs must fall inside it)."
  type        = string

  validation {
    condition     = can(cidrhost(var.ddi_mgmt_network_cidr, 0))
    error_message = "ddi_mgmt_network_cidr must be a valid IPv4 CIDR (e.g. 10.20.10.0/24)."
  }
}

variable "member_count" {
  description = "Number of vNIOS members (grid) / NIOS-X hosts (universal_ddi). >=2 for HA. Spread across esxi_hosts with anti-affinity."
  type        = number
  default     = 2

  validation {
    condition     = var.member_count >= 1 && var.member_count <= 8
    error_message = "member_count must be between 1 and 8 (use >=2 for production HA)."
  }
}

variable "esxi_hosts" {
  description = "ESXi host names to spread members across (anti-affinity). Maps from the Azure availability_zones. Members are round-robined over this list; a DRS VM-VM anti-affinity rule keeps the HA pair on separate hosts (contract §9)."
  type        = list(string)
  default     = []
}

variable "vnios_appliance_model" {
  description = <<-EOT
    vNIOS appliance MODEL / OVF deployment option, e.g. CP-V805, TE-V825,
    TE-V1425. MODEL-DEPENDENT — NOT hard-coded. The model sets vCPU/RAM; confirm
    the current model list and figures against the Infoblox vNIOS-for-VMware
    installation guide for your NIOS release (see ../05-vmware.md §9). If your OVA
    exposes the model as an OVF deployment_option it is applied via vnios_ovf; you
    may also override vnios_num_cpus / vnios_memory_mb / vnios_disk_gb below.
  EOT
  type        = string
  # No default on purpose — you must choose per model/NIOS version.
}

variable "vnios_ovf" {
  description = <<-EOT
    Source for the vNIOS OVA/OVF. DO NOT invent a build — download the .ova for
    your NIOS release from the Infoblox support/download portal. Provide EITHER a
    vSphere content-library item OR a local OVF/OVA path (exactly one):
      * content_library + content_library_item  — preferred, repeatable.
      * local_ovf_path                           — a .ova/.ovf on the runner.
    deployment_option maps to the OVA's model/size choice when the OVA exposes one.
  EOT
  type = object({
    content_library      = optional(string) # content library name
    content_library_item = optional(string) # item (template) name within it
    local_ovf_path       = optional(string) # OR a local .ova/.ovf path
    deployment_option    = optional(string) # OVA deployment option / model id, if any
  })

  validation {
    condition = (
      (try(var.vnios_ovf.content_library, null) != null && try(var.vnios_ovf.content_library_item, null) != null)
      || try(var.vnios_ovf.local_ovf_path, null) != null
    )
    error_message = "vnios_ovf must set BOTH content_library and content_library_item, OR local_ovf_path."
  }
}

variable "discovery_identity_type" {
  description = "Discovery credential model for vCenter/NSX -> Infoblox IPAM sync. Only 'vcenter_service_account' is supported on VMware (a least-privilege read-only vCenter SA + NSX API user). Contract §5."
  type        = string
  default     = "vcenter_service_account"

  validation {
    condition     = contains(["vcenter_service_account"], var.discovery_identity_type)
    error_message = "discovery_identity_type must be 'vcenter_service_account' on VMware."
  }
}

variable "workload_tier1_ids" {
  description = "Optional list of NSX-T Tier-1 gateway paths whose DNS forwarder should point at the DDI anycast VIP. Maps from the Azure spoke_vnet_ids. The module wires the DNS forwarder zone only when this is non-empty AND enable_nsx_dns_forwarder=true (contract §8)."
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Extra key/value pairs applied as vSphere tags on the member VMs, merged with the module-managed tags (contract §6). Module-managed keys win on conflict."
  type        = map(string)
  default     = {}
}

########################################################################
# Supporting variables (NOT in §3, required by the implementation).
# Grouped and commented; keep names stable across TF and the pipeline.
########################################################################

# --- vCenter / NSX connection (secrets from Vault/CI) -----------------

variable "vsphere_server" {
  description = "vCenter Server hostname/FQDN for the vsphere provider."
  type        = string
}

variable "vsphere_user" {
  description = "vCenter user for the vsphere provider (deploy scope). NOT the read-only discovery SA (that is separate, §5)."
  type        = string
}

variable "vsphere_password" {
  description = "vCenter password. SENSITIVE — inject from HashiCorp Vault or the CI secret store; never commit."
  type        = string
  sensitive   = true
}

variable "nsx_manager" {
  description = "NSX-T Manager hostname/FQDN for the nsxt provider."
  type        = string
}

variable "nsx_user" {
  description = "NSX-T user for the nsxt provider (creates DFW rules, DNS forwarder zone, DHCP relay)."
  type        = string
}

variable "nsx_password" {
  description = "NSX-T password. SENSITIVE — inject from Vault/CI; never commit."
  type        = string
  sensitive   = true
}

variable "allow_unverified_ssl" {
  description = "Skip TLS verification for vCenter/NSX. DEFAULT FALSE. Do NOT enable in production — supply a trusted CA instead."
  type        = bool
  default     = false
}

# --- DFW source scoping (contract §4: never 0.0.0.0/0) ---------------

variable "mgmt_source_cidrs" {
  description = "CIDR(s) allowed to reach management/WAPI (443/tcp, and 22/tcp if enabled) — admins, the Aria plug-in, CNA discovery. Scope tightly. MUST NOT be 0.0.0.0/0."
  type        = list(string)

  validation {
    condition     = length(var.mgmt_source_cidrs) > 0 && !contains(var.mgmt_source_cidrs, "0.0.0.0/0")
    error_message = "mgmt_source_cidrs must be non-empty and must not contain 0.0.0.0/0 (contract §4 forbids open management)."
  }
}

variable "dns_client_cidrs" {
  description = "CIDR(s) permitted to query DNS (53 tcp+udp) inbound — tenant segments and the NSX DNS forwarder ranges. Prefer explicit segment CIDRs over broad ranges."
  type        = list(string)

  validation {
    condition     = length(var.dns_client_cidrs) > 0 && !contains(var.dns_client_cidrs, "0.0.0.0/0")
    error_message = "dns_client_cidrs must list at least one segment/forwarder CIDR and must not contain 0.0.0.0/0."
  }
}

variable "dhcp_relay_cidrs" {
  description = "CIDR(s) of the NSX DHCP relay source(s) permitted to reach DHCP (67-68/udp). Used only when enable_dhcp=true (ON by default on VMware). MUST NOT be 0.0.0.0/0."
  type        = list(string)
  default     = []

  validation {
    condition     = !contains(var.dhcp_relay_cidrs, "0.0.0.0/0")
    error_message = "dhcp_relay_cidrs must not contain 0.0.0.0/0."
  }
}

variable "grid_peer_cidrs" {
  description = "CIDR(s) of Grid members / Grid Master (e.g. the mgmt network + an existing on-prem GM subnet) for Grid VPN 1194/udp + Grid comms 2114/tcp. Required when deployment_model='grid'."
  type        = list(string)
  default     = []
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

variable "enable_ssh" {
  description = "Open 22/tcp inbound from mgmt_source_cidrs for SSH admin. Off by default; prefer the VM console / remote console."
  type        = bool
  default     = false
}

# --- Optional / toggled services -------------------------------------

variable "enable_dhcp" {
  description = "Serve DHCP (67-68/udp) from vNIOS via NSX DHCP relay. ON BY DEFAULT on VMware — here DHCP is genuinely Infoblox's job (contract §4/§8), unlike the hyperscalers."
  type        = bool
  default     = true
}

variable "enable_snmp" {
  description = "Open 161/udp inbound from monitoring_source_cidrs for SNMP. Optional (contract §4)."
  type        = bool
  default     = false
}

variable "enable_nsx_dns_forwarder" {
  description = "Manage the NSX-T DNS forwarder zone pointing tenant resolution at the DDI VIP (contract §8). Only takes effect when workload_tier1_ids is non-empty."
  type        = bool
  default     = false
}

variable "manage_discovery_role" {
  description = "Optionally create the read-only vSphere role + permission for the discovery service account (convenience helper, contract §5). Off by default — the vCenter SA itself is an SSO/AD task, and the CNA vDiscovery job is an API/UI handoff."
  type        = bool
  default     = false
}

# --- Member VM sizing overrides (model-dependent) --------------------

variable "vnios_num_cpus" {
  description = "vCPU override for the member VMs. Leave null to use the OVA/model default. Model-dependent — see ../05-vmware.md §9 (do not invent)."
  type        = number
  default     = null
}

variable "vnios_memory_mb" {
  description = "Memory (MB) override for the member VMs. Leave null to use the OVA/model default. Model-dependent (do not invent)."
  type        = number
  default     = null
}

variable "vnios_disk_gb" {
  description = "OS/DB disk size (GB) override. Leave null to use the OVA default. Resizable to ~2.5 TB for reporting/large DBs (../05-vmware.md §9)."
  type        = number
  default     = null
}

variable "disk_thin_provisioned" {
  description = "Thin-provision the member disk. DEFAULT FALSE (thick eager-zeroed is recommended for DNS/DHCP DB write performance; thin is acceptable for lab) — ../05-vmware.md §5."
  type        = bool
  default     = false
}

# --- Member IP addressing (static; carried in OVF vApp properties) ----

variable "member_ip_addresses" {
  description = "Static management IPs for the members (one per member_count), inside ddi_mgmt_network_cidr. Set via OVF vApp properties at first boot. These become the dns_server_ips output."
  type        = list(string)
  default     = []
}

variable "member_netmask" {
  description = "Netmask for the member management IPs, e.g. '255.255.255.0'."
  type        = string
  default     = null
}

variable "member_gateway" {
  description = "Default gateway for the member management network."
  type        = string
  default     = null
}

variable "ddi_anycast_vip" {
  description = "Anycast/VRRP service VIP advertised by the DDI members for DNS (and the DHCP/forwarder target). If null, outputs fall back to member_ip_addresses (dns_server_ips)."
  type        = string
  default     = null
}

# --- DNS integration (contract §8) -----------------------------------

variable "ad_dns_servers" {
  description = "On-prem AD DNS server IP(s) that the Grid conditionally forwards AD zones to (contract §8). Leave empty to skip conditional-forwarder creation."
  type        = list(string)
  default     = []
}

variable "ad_forward_domains" {
  description = "AD-integrated domains conditionally forwarded to ad_dns_servers (e.g. corp.example + reverse zones). Contract §8 — the mirror of the Azure forward-to-resolver path."
  type        = list(string)
  default     = ["corp.example"]
}

# --- Discovery credential documentation (contract §5) ----------------
# The vCenter SA + NSX API user are least-privilege READ-ONLY. Their creation
# is an SSO/AD task; the module can OPTIONALLY manage the vSphere role (see
# manage_discovery_role). These variables carry the identities for the (optional)
# permission grant and for the discovery-config handoff documented in discovery.tf.

variable "discovery_vcenter_user" {
  description = "vCenter SSO principal (user@domain or group) for the least-privilege READ-ONLY discovery service account (contract §5). Used to grant the vSphere permission when manage_discovery_role=true."
  type        = string
  default     = null
}

variable "discovery_nsx_user" {
  description = "NSX-T API user for read-only segment/gateway discovery (contract §5). Documented for the CNA discovery handoff; no NSX role resource is created here."
  type        = string
  default     = null
}

# --- Grid join parameters (deployment_model='grid') ------------------

variable "grid_name" {
  description = "Infoblox Grid name the members join (deployment_model='grid'). Typically your existing on-prem Grid name."
  type        = string
  default     = "Infoblox"
}

variable "grid_master_vip" {
  description = "VIP/IP of the Grid Master the members join over 1194/udp + 2114/tcp (deployment_model='grid'). Usually an existing on-prem or in-domain GM. Leave null if the first member IS the Grid Master (lab only)."
  type        = string
  default     = null
}

# --- Universal DDI (SaaS) portal parameters --------------------------

variable "infoblox_portal_url" {
  description = "Infoblox Portal (CSP) base URL for NIOS-X enrollment (deployment_model='universal_ddi'). Outbound 443 required (contract §1/§4)."
  type        = string
  default     = "csp.infoblox.com"
}

# --- Secrets from Vault / CI (SENSITIVE; never a cloud KMS) -----------
# On VMware there is no Key Vault. These VALUES are injected at apply time from
# HashiCorp Vault or the CI secret store and carried into the OVF vApp
# properties / Portal enrollment. They are never emitted as outputs.

variable "admin_password" {
  description = "vNIOS default admin password set at first boot (OVF vApp property). SENSITIVE — from Vault/CI."
  type        = string
  sensitive   = true
}

variable "temp_license" {
  description = "vNIOS temporary license string for first boot, e.g. 'nios dns dhcp grid cloud'. SENSITIVE-ish — from Vault/CI."
  type        = string
  default     = "nios dns dhcp grid cloud"
}

variable "grid_shared_secret" {
  description = "Grid shared secret used to join members to the Grid (deployment_model='grid'). SENSITIVE — from Vault/CI. Required for the grid path."
  type        = string
  sensitive   = true
  default     = null
}

variable "saas_join_token" {
  description = "Infoblox Portal (CSP) join token used to enroll NIOS-X hosts (deployment_model='universal_ddi'). SENSITIVE — from Vault/CI. Required for the universal_ddi path."
  type        = string
  sensitive   = true
  default     = null
}
