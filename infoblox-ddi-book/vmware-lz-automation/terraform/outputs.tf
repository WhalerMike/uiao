# outputs.tf
# ---------------------------------------------------------------------------
# Canonical outputs (contract §7), mapped from the Azure package:
#   ddi_anycast_vip, dns_server_ips (list), grid_master_ip (grid only),
#   discovery_identity_id, ddi_member_vm_ids (maps from Azure ddi_subnet_id)
# These are the Stage-2 -> Stage-3 (validation) hand-off values.
# ---------------------------------------------------------------------------

output "ddi_anycast_vip" {
  description = "Anycast/VRRP service VIP for DNS across the DDI members. Null if none was supplied (var.ddi_anycast_vip) — in that case use dns_server_ips. Advertising the VIP from the HA pair is an Infoblox-side config step (contract §8, ../05-vmware.md §9)."
  value       = var.ddi_anycast_vip
}

output "dns_server_ips" {
  description = "List of the DDI members' management IPs (grid members or NIOS-X hosts, per deployment_model). Point the NSX DNS forwarder / DHCP relay here if not using the anycast VIP."
  value       = local.member_dns_ips
}

output "grid_master_ip" {
  description = "Grid Master IP (deployment_model='grid' only; null otherwise). The supplied grid_master_vip if set (usual existing-GM pattern), else the first member's IP."
  value       = local.grid_master_ip
}

output "discovery_identity_id" {
  description = "The least-privilege discovery credential reference: the managed vSphere read-only role id when manage_discovery_role=true, else the configured discovery_vcenter_user (documented for the CNA handoff)."
  value = (
    var.manage_discovery_role
    ? try(vsphere_role.discovery_readonly[0].id, null)
    : var.discovery_vcenter_user
  )
}

output "ddi_member_vm_ids" {
  description = "Managed-object IDs of the deployed member VMs (grid members or NIOS-X hosts). Maps from the Azure ddi_subnet_id — the Stage-2 objects handed to Stage-3 validation."
  value = local.is_grid ? vsphere_virtual_machine.grid[*].id : vsphere_virtual_machine.niosx[*].id
}
