# outputs.tf
# ---------------------------------------------------------------------------
# Canonical outputs (contract §7) — mirror the Azure package:
#   ddi_anycast_vip, dns_server_ips (list), grid_master_ip (grid only),
#   discovery_identity_id, ddi_subnet_ids
# These are the Stage-2 -> Stage-3 (validation) hand-off values.
# ---------------------------------------------------------------------------

output "ddi_anycast_vip" {
  description = "Anycast/service VIP for DNS across the DDI members. Null if no anycast VIP was supplied (var.ddi_anycast_vip) — in that case use dns_server_ips. Advertising the anycast VIP from the members is an Infoblox-side config step (contract §8, ../02-aws.md §9)."
  value       = var.ddi_anycast_vip
}

output "dns_server_ips" {
  description = "List of the DDI members' LAN1 private DNS IPs (grid members or NIOS-X hosts, depending on deployment_model). Point spoke DHCP option sets / on-prem forwarders here if not using the anycast VIP."
  value       = local.member_dns_ips
}

output "grid_master_ip" {
  description = "Grid Master IP (deployment_model='grid' only; null otherwise). The supplied grid_master_vip if set (usual on-prem GM pattern), else the first AWS member's LAN1 private IP."
  value       = local.grid_master_ip
}

output "discovery_identity_id" {
  description = "Identity used for AWS->Infoblox discovery: the cross-account IAM role ARN (discovery_identity_type='iam_role'), or the supplied instance-profile role ARN ('instance_profile')."
  value       = local.disco_identity_id
}

output "ddi_subnet_ids" {
  description = "IDs of the dedicated DDI subnets created in the hub VPC (one per AZ)."
  value       = [for s in aws_subnet.ddi : s.id]
}
