# IPAM Adapter Interface
**Version:** 0.1-draft | **Aligned with:** UIAO Core Concepts #1 (SSOT) and #4 (Deterministic Addressing)

## Purpose
Defines the canonical contract any IPAM/DNS/DHCP system must satisfy to function
as the authoritative Addressing adapter in a uiao-gos governed migration.
Exactly one IPAM adapter may be authoritative per deployment. Split-brain DNS is drift.

## Registered Implementations
| Adapter | Path | Use Case |
|---|---|---|
| InfoBlox NIOS | adapters/ipam/infoblox/ | Federal — FedRAMP authorized, CDM-integrated |
| BlueCat | adapters/ipam/bluecat/ | Enterprise alternative |
| Generic | adapters/ipam/generic/ | Any RFC-compliant IPAM with REST API |

## Required Capabilities
### DNS Record Governance
- Read all forward and reverse lookup zones
- CRUD for A, AAAA, PTR, CNAME, SRV, MX records
- SRV records critical: _kerberos, _ldap, _gc must be migrated explicitly
- Full zone export as canonical snapshot for drift detection baseline
- Detect unauthorized record changes (drift detection hook)

### DHCP Governance
- Inventory all DHCP scopes
- Map scopes to OrgPath where applicable
- Detect rogue DHCP servers — critical migration safety check
- Reservation-to-identity binding — SSOT for hostname-to-identity

### IP Address Management
- Full IP space inventory including unmanaged/shadow assignments
- Identity-to-IP binding (Core Concept #3 — identity as root namespace)
- Deterministic IP assignment from identity attributes (Core Concept #4)
- Subnet-to-OrgPath mapping

### Migration-Specific Requirements
- Side-by-side operation with AD-integrated DNS during hybrid window
- Zone delegation from AD DNS to standalone
- Conditional forwarder management
- AD replication zone export before any changes

## Adapter Registration Schema
```json
{
  "adapter_id": "<vendor>-<product>-<version>",
  "adapter_type": "ipam",
  "vendor": "",
  "fedramp_authorized": true|false,
  "capabilities": {
    "dns_governance": true,
    "dhcp_governance": true,
    "ip_management": true,
    "side_by_side_ad": true,
    "event_stream": true
  }
}
```
