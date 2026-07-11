# examples/hub-integration/main.tf
# ---------------------------------------------------------------------------
# Example: layer the Infoblox DDI module (Stage 2) onto an existing VMware Cloud
# Foundation management/edge domain (Stage 1), deployment_model = "grid".
#
# Stage-1 facts (datacenter, cluster, datastore, management dvPortGroup, ESXi
# hosts, Tier-1 gateway paths) flow in as this module's inputs. Here they are
# plain values wired to a realistic vSphere/NSX inventory; swap for your own
# datasource/remote-state lookups as your platform team publishes them.
#
# STARTER EXAMPLE — replace the vCenter/NSX coordinates, the OVA/model, the CIDRs,
# and inject every secret via TF_VAR_* from Vault/CI. Do not deploy as-is.
# ---------------------------------------------------------------------------

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    vsphere  = { source = "hashicorp/vsphere", version = "~> 2.6" }
    nsxt     = { source = "vmware/nsxt", version = "~> 3.7" }
    infoblox = { source = "infobloxopen/infoblox", version = "~> 2.13" }
  }
  # Use your own backend (a shared remote state); shown for completeness.
  # backend "s3" { ... }   # or "http", "consul", etc. — no Azure/cloud KMS on-prem
}

# --- Connection + secrets: from Vault/CI via TF_VAR_* (never committed) -------
# vsphere_password, nsx_password, admin_password, grid_shared_secret are declared
# in the module's variables.tf as sensitive; provide them through:
#   export TF_VAR_vsphere_password="$(vault kv get -field=pw secret/vsphere)"
#   export TF_VAR_nsx_password="$(vault kv get -field=pw secret/nsx)"
#   export TF_VAR_admin_password="$(vault kv get -field=pw secret/vnios-admin)"
#   export TF_VAR_grid_shared_secret="$(vault kv get -field=secret secret/grid)"

# --- Stage 2: the Infoblox DDI module ---------------------------------
module "infoblox_ddi" {
  source = "../.."

  # Basics
  name_prefix = "ddi"
  environment = "prod"

  # Boundary: grid keeps the control plane inside the SDDC (default, natural fit).
  deployment_model = "grid"
  # acknowledge_saas_boundary intentionally left false — not needed for grid.
  compliance_profile = "fedramp-moderate"

  # --- Stage-1 SDDC inventory (the management/edge domain) ---
  vsphere_datacenter    = "DC1"
  compute_cluster       = "MgmtCluster"
  resource_pool         = "MgmtCluster/Resources/infoblox"
  datastore             = "DS-SSD-01"
  management_portgroup  = "MGMT-dvPG"
  ddi_mgmt_network_cidr = "10.20.10.0/24"

  # --- Members: 2 across two ESXi hosts (HA, anti-affinity) ---
  member_count = 2
  esxi_hosts   = ["esxi-01.corp.example", "esxi-02.corp.example"]

  # Static management addressing (from the IPAM plan).
  member_ip_addresses = ["10.20.10.11", "10.20.10.12"]
  member_netmask      = "255.255.255.0"
  member_gateway      = "10.20.10.1"
  ddi_anycast_vip     = "10.20.10.10" # VRRP VIP advertised by the HA pair

  # vNIOS OVA + model are RELEASE/MODEL dependent — download + supply, don't guess:
  vnios_appliance_model = "TE-V1425" # example only; confirm the model list
  vnios_ovf = {
    content_library      = "infoblox"
    content_library_item = "nios-9.0.x" # your uploaded OVA item
    # or: local_ovf_path = "/opt/ova/nios.ova"
  }
  disk_thin_provisioned = false # thick eager-zeroed for DNS/DHCP DB performance

  # --- DFW source scoping (never 0.0.0.0/0) ---
  mgmt_source_cidrs = ["10.20.0.0/24"]       # admin/bastion + Aria + CNA
  dns_client_cidrs  = ["10.30.0.0/16"]       # tenant segments / NSX forwarder
  dhcp_relay_cidrs  = ["10.30.0.0/16"]       # NSX DHCP relay sources (DHCP is ON)
  grid_peer_cidrs   = ["10.20.10.0/24", "192.168.100.0/24"] # mgmt net + on-prem GM

  # --- Grid join (usual pattern: join to an existing GM) ---
  grid_name       = "CorpGrid"
  grid_master_vip = "192.168.100.10" # existing Grid Master VIP

  # --- DNS integration (§8) ---
  ad_dns_servers           = ["192.168.100.5", "192.168.100.6"] # on-prem AD DNS
  ad_forward_domains       = ["corp.example"]
  enable_nsx_dns_forwarder = true
  workload_tier1_ids       = ["/infra/tier-1s/t1-workload-a"] # Tier-1 DNS forwarder target

  # --- Discovery (least-privilege read-only) ---
  discovery_identity_type = "vcenter_service_account"
  discovery_vcenter_user  = "svc-infoblox-disco@vsphere.local"
  discovery_nsx_user      = "svc-infoblox-nsx"
  manage_discovery_role   = true

  # --- Connection (passwords via TF_VAR_* from Vault/CI) ---
  vsphere_server = "vcenter.corp.example"
  vsphere_user   = "svc-tf@vsphere.local"
  nsx_manager    = "nsx.corp.example"
  nsx_user       = "svc-tf-nsx"

  # temp_license default is fine; admin_password / grid_shared_secret from Vault/CI.

  tags = {
    owner      = "network-platform"
    costcenter = "cc-1234"
  }
}

output "ddi_dns_server_ips" {
  value = module.infoblox_ddi.dns_server_ips
}

output "ddi_member_vm_ids" {
  value = module.infoblox_ddi.ddi_member_vm_ids
}

output "ddi_grid_master_ip" {
  value = module.infoblox_ddi.grid_master_ip
}
