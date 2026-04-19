---
document_id: DM_030
title: "RADIUS / Network Policy Server Adapter Interface"
version: "0.1-draft"
status: DRAFT
owner: "Michael Stratton"
created_at: "2026-04-19"
updated_at: "2026-04-19"
boundary: GCC-Moderate
core_concepts: ["#3 Identity as root namespace", "#5 Certificate-anchored overlay"]
priority: CRITICAL
risk: "Network access failure pre-migration completion"
---

# RADIUS / Network Policy Server Adapter Interface

**Priority:** CRITICAL | **Risk:** Network access failure pre-migration completion

## Registered Implementations

| Adapter | Use Case |
|---|---|
| nps/ | Windows NPS migration source |
| cisco-ise/ | Enterprise RADIUS replacement |
| aruba-clearpass/ | Enterprise RADIUS replacement |
| entra-radius/ | Entra ID RADIUS proxy (cloud-native) |

## Required Capabilities

- Inventory all NPS policies (Connection Request, Network, Health)
- Map NPS policies to AD group dependencies
- Identify all RADIUS clients (access points, VPN concentrators, switches)
- 802.1X certificate profile inventory
- EAP method inventory (PEAP, EAP-TLS, EAP-TTLS)
- Policy translation from AD group membership to Entra ID dynamic groups
- Side-by-side operation during transition window
- Validation: confirm RADIUS auth succeeds against new backend before cutover

## Migration Sequence

1. Inventory all RADIUS clients and NPS policies
2. Map all NPS AD group dependencies to Entra ID equivalents
3. Deploy replacement RADIUS (Cisco ISE / ClearPass / Entra proxy)
4. Validate in parallel before cutover
5. Cut over RADIUS clients to new server
6. Decommission NPS only after 30-day validation window
