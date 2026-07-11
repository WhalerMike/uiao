# outputs.tf
# ---------------------------------------------------------------------------
# Canonical outputs (contract §7) — names kept identical to the Azure package for
# cross-cloud parity:
#   ddi_anycast_vip, dns_server_ips (list), grid_master_ip (grid only),
#   discovery_identity_id, ddi_subnet_id
# These are the Stage-2 -> Stage-3 (validation) hand-off values.
# ---------------------------------------------------------------------------

output "ddi_anycast_vip" {
  description = "Anycast/service VIP for DNS across the DDI members. Null if none supplied (var.ddi_anycast_vip) — then use dns_server_ips. On OCI the VIP is advertised via BGP over the DRG or fronted by an OCI Load Balancer (contract §8, ../04-oci.md §9)."
  value       = var.ddi_anycast_vip
}

output "dns_server_ips" {
  description = "List of the DDI members' private DNS IPs (grid members or NIOS-X hosts, per deployment_model). Point spoke/hub resolver forwarding rules here if not using the anycast VIP."
  value       = local.member_dns_ips
}

output "grid_master_ip" {
  description = "Grid Master IP (deployment_model='grid' only; null otherwise). The supplied grid_master_vip if set (usual on-prem GM over the DRG), else the first OCI member's private IP."
  value       = local.grid_master_ip
}

output "discovery_identity_id" {
  description = "Identity used for OCI->Infoblox discovery: the dynamic group OCID (instance_principal) or the IAM group OCID (api_key_user)."
  value = (
    local.use_instance_principal
    ? try(oci_identity_dynamic_group.disco[0].id, null)
    : try(oci_identity_group.disco[0].id, null)
  )
}

output "ddi_subnet_id" {
  description = "OCID of the dedicated DDI subnet created in the hub VCN."
  value       = oci_core_subnet.ddi.id
}
