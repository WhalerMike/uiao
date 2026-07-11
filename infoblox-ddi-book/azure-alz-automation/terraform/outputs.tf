# outputs.tf
# ---------------------------------------------------------------------------
# Canonical outputs (contract §7) — identical names in TF and Bicep:
#   ddi_anycast_vip, dns_server_ips (list), grid_master_ip (grid only),
#   discovery_identity_id, ddi_subnet_id
# These are the Stage-2 -> Stage-3 (validation) hand-off values.
# ---------------------------------------------------------------------------

output "ddi_anycast_vip" {
  description = "Anycast/service VIP for DNS across the DDI members. Null if no anycast VIP was supplied (var.ddi_anycast_vip) — in that case use dns_server_ips. Advertising the anycast VIP from the members is an Infoblox-side config step (contract §8, ../01-azure.md §9)."
  value       = var.ddi_anycast_vip
}

output "dns_server_ips" {
  description = "List of the DDI members' private DNS IPs (grid members or NIOS-X hosts, depending on deployment_model). Point spoke/hub dns_servers here if not using the anycast VIP."
  value       = local.member_dns_ips
}

output "grid_master_ip" {
  description = "Grid Master IP (deployment_model='grid' only; null otherwise). The supplied grid_master_vip if set (usual on-prem GM pattern), else the first Azure member's private IP."
  value       = local.grid_master_ip
}

output "discovery_identity_id" {
  description = "Identity used for Azure->Infoblox discovery: the user-assigned managed identity resource id, or the service principal object id when discovery_identity_type='service_principal'."
  value       = local.disco_identity_id
}

output "ddi_subnet_id" {
  description = "Resource id of the dedicated DDI subnet created in the hub VNet."
  value       = azurerm_subnet.ddi.id
}
