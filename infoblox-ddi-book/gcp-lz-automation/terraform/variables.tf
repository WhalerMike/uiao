# variables.tf
# ---------------------------------------------------------------------------
# All canonical inputs from _module-contract.md §3 (names mirror the Azure
# package), followed by the SUPPORTING inputs the implementation needs (firewall
# source ranges, Cloud DNS inbound IP, discovery scopes, secret ids, etc.).
# Contract variables are kept first and verbatim; supporting variables are
# grouped and labelled.
# ---------------------------------------------------------------------------

########################################################################
# §3 — Canonical contract variables
########################################################################

variable "name_prefix" {
  description = "Prefix for all resource names, e.g. 'ddi' -> ddi-subnet, ddi-member-a, ddi-disco (contract §6)."
  type        = string
  default     = "ddi"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,10}$", var.name_prefix))
    error_message = "name_prefix must be lowercase alphanumeric/hyphen, start with a letter, and be 2-11 chars (keeps generated GCP resource names within limits)."
  }
}

variable "region" {
  description = "GCP region (COMMERCIAL cloud). No default — must be supplied. Members are placed in zones of this region (see var.zones)."
  type        = string
}

variable "environment" {
  description = "Deployment environment: dev | test | prod. Feeds labels and sizing decisions (contract §3)."
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
      * "grid"          — self-managed vNIOS Grid INSIDE the project/ATO boundary
                          (default; boundary-clean for GCC-Moderate).
      * "universal_ddi" — Infoblox Portal (SaaS) control plane OUTSIDE the boundary;
                          requires outbound 443 to the Portal (csp.infoblox.com) AND
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
  description = "Compliance posture driving labels + control mapping. Defaults to gcc-moderate (FedRAMP Moderate-equivalent on commercial Google Cloud) per contract §1."
  type        = string
  default     = "gcc-moderate"

  validation {
    condition     = length(trimspace(var.compliance_profile)) > 0
    error_message = "compliance_profile must be a non-empty string (default 'gcc-moderate')."
  }
}

variable "host_project_id" {
  description = "Project ID of the Shared VPC HOST project. From Stage-1 (Google Cloud landing zone) output. The DDI subnet, firewall rules, members, and discovery SA land here (contract §2)."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.host_project_id))
    error_message = "host_project_id must be a valid GCP project ID (6-30 chars, lowercase letters/digits/hyphens)."
  }
}

variable "shared_vpc_network" {
  description = "Host VPC network name OR self-link (from Stage-1 output). The DDI subnet is created in this network. Accepts a bare name (resolved against host_project_id) or a full self-link."
  type        = string
}

variable "ddi_subnet_cidr" {
  description = "CIDR for the dedicated DDI subnet this module creates in the host VPC, e.g. '10.10.4.0/27'. Must fit inside the VPC's address plan and not overlap existing subnets."
  type        = string

  validation {
    condition     = can(cidrhost(var.ddi_subnet_cidr, 0))
    error_message = "ddi_subnet_cidr must be a valid IPv4 CIDR (e.g. 10.10.4.0/27)."
  }
}

variable "member_count" {
  description = "Number of vNIOS members (grid) / NIOS-X hosts (universal_ddi). >=2 for HA. Spread across zones."
  type        = number
  default     = 2

  validation {
    condition     = var.member_count >= 1 && var.member_count <= 8
    error_message = "member_count must be between 1 and 8 (use >=2 for production HA)."
  }
}

variable "zones" {
  description = "Zone LETTERS within var.region to spread members across (e.g. [\"a\",\"b\"] -> us-central1-a, us-central1-b). Members are round-robined over this list (contract §3, 03-gcp.md §9 cross-zone HA)."
  type        = list(string)
  default     = ["a", "b"]

  validation {
    condition     = length(var.zones) >= 1 && alltrue([for z in var.zones : can(regex("^[a-z]$", z))])
    error_message = "zones must be single lowercase zone letters (e.g. [\"a\",\"b\"]); use >=2 for cross-zone HA."
  }
}

variable "machine_type" {
  description = <<-EOT
    GCP machine type for vNIOS / NIOS-X. MODEL- AND NIOS-VERSION-DEPENDENT — NOT
    hard-coded. Guidance (03-gcp.md §4/§9): General purpose N1 series sized to the
    target vNIOS model. Confirm the model->machine-type->disk mapping and vCPU
    quota for your NIOS version in the current deployment guide.
  EOT
  type        = string
  # No default on purpose — you must choose per model/region/version.
}

variable "vnios_image" {
  description = <<-EOT
    Compute image reference for vNIOS / NIOS-X. DO NOT hard-code an image name —
    discover the current image with:
      gcloud compute images list --filter="family~infoblox OR name~vnios" --show-deprecated
    Supply the publishing PROJECT and EITHER a `family` (tracks latest) or a
    pinned `name`. Marketplace images publish into an Infoblox-owned image project;
    a custom image lives in your own project.
  EOT
  type = object({
    project = string
    family  = optional(string) # tracks latest in the family; mutually use with name
    name    = optional(string) # a pinned image name (preferred for prod)
  })

  validation {
    condition     = (try(var.vnios_image.family, null) != null) != (try(var.vnios_image.name, null) != null)
    error_message = "vnios_image must set exactly one of family (latest) or name (pinned)."
  }
}

variable "secret_project_id" {
  description = "Project ID holding the Secret Manager secrets (admin password, temp license, grid shared secret, join token). Secret ids are set via *_secret_id variables below. Often equals host_project_id."
  type        = string
}

variable "discovery_identity_type" {
  description = "Identity used for GCP->Infoblox discovery/IPAM sync: 'service_account' (module creates ddi-disco) or 'existing_service_account' (bind roles to a pre-created SA via existing_service_account_email). Contract §5."
  type        = string
  default     = "service_account"

  validation {
    condition     = contains(["service_account", "existing_service_account"], var.discovery_identity_type)
    error_message = "discovery_identity_type must be 'service_account' or 'existing_service_account'."
  }
}

variable "spoke_networks" {
  description = "Optional list of service-project VPC self-links that should resolve via the DDI members (Cloud DNS peering zone to the hub, or an outbound server policy). The module wires these only when non-empty AND enable_spoke_dns_peering=true (contract §8)."
  type        = list(string)
  default     = []
}

variable "labels" {
  description = "Extra labels merged with the module-managed labels (contract §6). Module-managed keys win on conflict. GCP label values are lowercase."
  type        = map(string)
  default     = {}
}

########################################################################
# Supporting variables (NOT in §3, required by the implementation).
# Grouped and commented; keep names stable across TF and the pipelines.
########################################################################

# --- Firewall source scoping (contract §4: never 0.0.0.0/0) ----------

variable "mgmt_source_ranges" {
  description = "CIDR(s) allowed to reach management ports (443/tcp, and 22/tcp if enabled). Scope tightly to jump host/bastion/mgmt subnets. MUST NOT be 0.0.0.0/0."
  type        = list(string)

  validation {
    condition     = length(var.mgmt_source_ranges) > 0 && !contains(var.mgmt_source_ranges, "0.0.0.0/0")
    error_message = "mgmt_source_ranges must be non-empty and must not contain 0.0.0.0/0 (contract §4 forbids open management)."
  }
}

variable "monitoring_source_ranges" {
  description = "CIDR(s) allowed to reach SNMP (161/udp) when enable_snmp=true. MUST NOT be 0.0.0.0/0."
  type        = list(string)
  default     = []

  validation {
    condition     = !contains(var.monitoring_source_ranges, "0.0.0.0/0")
    error_message = "monitoring_source_ranges must not contain 0.0.0.0/0."
  }
}

variable "dns_client_ranges" {
  description = "CIDR(s) permitted to query DNS (53 tcp+udp) ingress — spoke/service-project and on-prem ranges. Prefer explicit ranges over broad ones. Also used for DHCP ingress when enable_dhcp=true."
  type        = list(string)

  validation {
    condition     = length(var.dns_client_ranges) > 0 && !contains(var.dns_client_ranges, "0.0.0.0/0")
    error_message = "dns_client_ranges must list at least one client CIDR and must not contain 0.0.0.0/0."
  }
}

variable "grid_peer_ranges" {
  description = "CIDR(s) of Grid members / Grid Master (e.g. on-prem GM subnet + the DDI subnet) for Grid VPN 1194/udp + Grid comms 2114/tcp. Used only when deployment_model='grid'."
  type        = list(string)
  default     = []
}

variable "enable_ssh" {
  description = "Open 22/tcp ingress from mgmt_source_ranges for SSH admin. Off by default; prefer IAP TCP forwarding / serial console."
  type        = bool
  default     = false
}

# --- Optional services -----------------------------------------------

variable "enable_dhcp" {
  description = "Serve DHCP (67-68/udp) from vNIOS. OFF by default — GCP subnet DHCP is platform-managed via the metadata server 169.254.169.254 (contract §4)."
  type        = bool
  default     = false
}

variable "enable_snmp" {
  description = "Open 161/udp ingress from monitoring_source_ranges for SNMP. Optional (contract §4)."
  type        = bool
  default     = false
}

# --- Networking / DNS integration (contract §8) ----------------------

variable "inbound_forwarding_enabled" {
  description = "Create an INBOUND Cloud DNS server policy (google_dns_policy, enable_inbound_forwarding) on the host VPC so Cloud DNS allocates inbound forwarder IPs that Infoblox/on-prem can target (contract §8)."
  type        = bool
  default     = true
}

variable "cloud_dns_inbound_ip" {
  description = "A Cloud DNS INBOUND forwarder IP (allocated from the VPC subnet ranges once the inbound server policy exists) that the Infoblox members conditionally forward googleapis/private-zone names to (contract §8). Leave null to skip creating infoblox_zone_forward objects."
  type        = string
  default     = null
}

variable "infoblox_forward_domains" {
  description = "Domains the INFOBLOX members conditionally forward to the Cloud DNS inbound forwarder IP (contract §8) — Google-service and Cloud DNS private names that must resolve natively."
  type        = list(string)
  default = [
    "googleapis.com",
    "run.app",
  ]
}

variable "enterprise_forward_domains" {
  description = "Domains for which the module creates Cloud DNS FORWARDING ZONES targeting the Infoblox member IPs (so GCP VMs resolve corp/on-prem names via Infoblox), e.g. ['corp.example.com.','10.in-addr.arpa.']. Trailing dot required. Empty = create none."
  type        = list(string)
  default     = []

  validation {
    condition     = alltrue([for d in var.enterprise_forward_domains : endswith(d, ".")])
    error_message = "each enterprise_forward_domains entry must be a fully-qualified DNS name ending in a dot (e.g. corp.example.com.)."
  }
}

variable "ddi_anycast_vip" {
  description = "Anycast/service VIP advertised by the DDI members and used as the Cloud DNS forwarding target / spoke resolver. If null, outputs fall back to the members' individual internal IPs (dns_server_ips)."
  type        = string
  default     = null
}

variable "enable_spoke_dns_peering" {
  description = "Create Cloud DNS PEERING zones so spoke_networks resolve enterprise domains via the host VPC's forwarding config (contract §8). Only takes effect when spoke_networks is non-empty."
  type        = bool
  default     = false
}

# --- Discovery identity scoping (contract §5) ------------------------

variable "discovered_project_ids" {
  description = "Project IDs the discovery SA gets roles/compute.networkViewer + roles/dns.reader on, to enumerate VPCs/subnets/instances/addresses and Cloud DNS (contract §5). Include the host project and each service project to discover."
  type        = list(string)
  default     = []
}

variable "dns_admin_project_ids" {
  description = "Project IDs holding Cloud DNS zones. Discovery SA gets roles/dns.admin here ONLY when enable_record_write=true (record-write is opt-in, contract §5)."
  type        = list(string)
  default     = []
}

variable "enable_record_write" {
  description = "Opt in to Infoblox writing records into Cloud DNS: grants roles/dns.admin on dns_admin_project_ids. Off by default = read-only discovery (contract §5)."
  type        = bool
  default     = false
}

variable "existing_service_account_email" {
  description = "When discovery_identity_type='existing_service_account', the email of the pre-created discovery SA to bind roles to. This module does not create the SA in that mode."
  type        = string
  default     = null
}

# --- Secret Manager secret ids ---------------------------------------

variable "admin_password_secret_id" {
  description = "Secret Manager secret id (short name) holding the vNIOS default admin password (bootstrapped via startup-script/metadata)."
  type        = string
  default     = "ddi-vnios-admin-password"
}

variable "temp_license_secret_id" {
  description = "Secret Manager secret id holding the vNIOS temp license string(s) for first boot (e.g. 'vnios dns dhcp grid enterprise')."
  type        = string
  default     = "ddi-vnios-temp-license"
}

variable "grid_shared_secret_id" {
  description = "Secret Manager secret id holding the Grid shared secret used to join members to the Grid (deployment_model='grid')."
  type        = string
  default     = "ddi-grid-shared-secret"
}

variable "saas_join_token_secret_id" {
  description = "Secret Manager secret id holding the Infoblox Portal (CSP) join token used to enroll NIOS-X hosts (deployment_model='universal_ddi')."
  type        = string
  default     = "ddi-uddi-join-token"
}

# --- Grid join parameters (deployment_model='grid') ------------------

variable "grid_name" {
  description = "Infoblox Grid name the GCP members join (deployment_model='grid'). Typically your existing on-prem Grid name."
  type        = string
  default     = "Infoblox"
}

variable "grid_master_vip" {
  description = "VIP/IP of the Grid Master the GCP members join over 1194/udp + 2114/tcp (deployment_model='grid'). Usually the on-prem GM. Leave null if the first GCP member IS the Grid Master (lab only)."
  type        = string
  default     = null
}

# --- Universal DDI (SaaS) portal parameters --------------------------

variable "infoblox_portal_url" {
  description = "Infoblox Portal (CSP) base URL for NIOS-X enrollment (deployment_model='universal_ddi'). Commercial: https://csp.infoblox.com. Outbound 443 required (contract §1/§4)."
  type        = string
  default     = "https://csp.infoblox.com"
}
</content>
