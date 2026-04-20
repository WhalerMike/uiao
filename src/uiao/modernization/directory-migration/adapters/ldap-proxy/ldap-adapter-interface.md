---
document_id: DM_040
title: "LDAP Proxy / Application Authentication Adapter Interface"
version: "0.1-draft"
status: DRAFT
owner: "Michael Stratton"
created_at: "2026-04-19"
updated_at: "2026-04-19"
boundary: GCC-Moderate
core_concepts: ["#3 Identity as root namespace"]
priority: CRITICAL
risk: "Silent application auth failure — largest hidden surface"
---

# LDAP Proxy / Application Authentication Adapter Interface

**Priority:** CRITICAL | **Risk:** Silent application auth failure — largest hidden surface

## Registered Implementations

| Adapter | Use Case |
|---|---|
| entra-domain-services/ | Microsoft LDAP compatibility layer in Entra |
| generic-ldap-proxy/ | Standalone LDAP proxy forwarding to Entra ID |

## Discovery Phase Requirements (Phase 1 — before any migration)

- Network traffic analysis: identify all hosts making LDAP bind requests to DCs
- Service account inventory: which service accounts are used for LDAP binds
- Application inventory: map every LDAP-dependent application
- Query analysis: what attributes are being read (dn, sAMAccountName, memberOf, etc.)
- Bind type inventory: simple bind vs. SASL vs. certificate-based

## Transition Requirements

- LDAP proxy capable of forwarding queries to Entra ID / Entra Domain Services
- Attribute mapping: AD attribute names to Entra ID equivalents
- Service account migration to Entra service principals
- Application-by-application validation before DC decommission

## Migration Sequence

1. Deploy passive LDAP traffic monitor on DC network segment
2. Run 30-day discovery window — capture all LDAP bind sources
3. Build application-to-LDAP-dependency map
4. Deploy LDAP proxy pointed at Entra Domain Services
5. Validate each application against proxy before cutover
6. Cut over applications in waves — never all at once
