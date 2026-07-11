# outputs.tf
# ---------------------------------------------------------------------------
# Canonical outputs (contract §7):
#   ddi_anycast_vip, dns_server_ips (list), grid_master_ip (grid only),
#   discovery_service_account_email, ddi_subnet_id
# These are the Stage-2 -> Stage-3 (validation) hand-off values. (The Azure
# package's discovery_identity_id maps to discovery_service_account_email here.)
# ---------------------------------------------------------------------------

output "ddi_anycast_vip" {
  description = "Anycast/service VIP for DNS across the DDI members. Null if no anycast VIP was supplied (var.ddi_anycast_vip) — in that case use dns_server_ips. Advertising the anycast VIP from the members is an Infoblox-side config step (contract §8, 03-gcp.md §9)."
  value       = var.ddi_anycast_vip
}

output "dns_server_ips" {
  description = "List of the DDI members' internal DNS IPs (grid members or NIOS-X hosts, depending on deployment_model). Use these as Cloud DNS forwarding-zone targets / spoke resolvers if not using the anycast VIP."
  value       = local.member_dns_ips
}

output "grid_master_ip" {
  description = "Grid Master IP (deployment_model='grid' only; null otherwise). The supplied grid_master_vip if set (usual on-prem GM pattern), else the first GCP member's internal IP."
  value       = local.grid_master_ip
}

output "discovery_service_account_email" {
  description = "Email of the service account used for GCP->Infoblox discovery: the module-created ddi-disco SA, or existing_service_account_email when discovery_identity_type='existing_service_account'. (Canonical output; Azure analog: discovery_identity_id.)"
  value       = local.disco_sa_email
}

output "ddi_subnet_id" {
  description = "Self-link/id of the dedicated DDI subnet created in the Shared VPC host project."
  value       = google_compute_subnetwork.ddi.id
}
</content>
