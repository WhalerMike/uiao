---
document_id: DM_002
title: "Active Directory Dependency Inventory — 11 Object Types"
version: "1.0"
status: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-19"
updated_at: "2026-04-19"
boundary: GCC-Moderate
---

# Active Directory Dependency Inventory

AD was not just an identity store. It was the implicit governance model for every
network service in the enterprise. This inventory defines all 11 object types that
AD was holding together — and that must be governed through migration.

| Object Type | Migration Risk |
|---|---|
| **Users / Identities** | Visible — but governance model (OU hierarchy) is lost |
| **Computers / Devices** | GPO to Intune mapping is non-deterministic without clean groups |
| **Service Accounts** | Kerberos-dependent, undocumented, break silently post-migration |
| **Security Groups** | Nested authorization logic; flattening loses inheritance model |
| **Group Policy Objects** | No 1:1 mapping to Intune configuration profiles |
| **DNS / DHCP** | AD-integrated; breaks silently when AD retires |
| **PKI / Certificates** | Most dangerous — invisible until certs expire post-migration |
| **RADIUS / NPS** | Breaks network access before users can authenticate |
| **LDAP Applications** | Largest hidden surface — every app doing LDAP bind breaks |
| **SPNs / Kerberos** | Maps to nothing in Entra ID without explicit reconstruction |
| **Trust Relationships** | Cross-domain/forest trusts encoding inter-org boundaries |

## Adapter Coverage

Each object type maps to one or more adapters in the directory-migration canon:

| Object Type | Primary Adapter | Secondary |
|---|---|---|
| Users / Identities | `orgtree/` (identity modernization) | `sync-engine/` |
| Computers / Devices | `device-management/` | `sync-engine/` |
| Service Accounts | `ldap-proxy/` | `sync-engine/` |
| Security Groups | `orgtree/` (dynamic groups) | — |
| Group Policy Objects | `device-management/` | — |
| DNS / DHCP | `ipam/` | — |
| PKI / Certificates | `pki/` | — |
| RADIUS / NPS | `radius/` | — |
| LDAP Applications | `ldap-proxy/` | — |
| SPNs / Kerberos | `ldap-proxy/` | — |
| Trust Relationships | (architectural — no single adapter) | — |
