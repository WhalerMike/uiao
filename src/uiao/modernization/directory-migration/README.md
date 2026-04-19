---
document_id: DM_000
title: "Directory Migration — Microsoft AD to Entra ID Governance Bridge"
version: "1.0"
status: CANONICAL
owner: "Michael Stratton"
author: "Michal Doroszewski"
created_at: "2026-04-19"
updated_at: "2026-04-19"
boundary: GCC-Moderate
provenance:
  source_file: "uiao-gos-implementation-instructions.docx"
  extracted_by: "Copilot Tasks"
  extraction_date: "2026-04-19"
  original_repo: "WhalerMike/uiao-gos (archived — dissolved into monorepo via ADR-028)"
---

# Directory Migration — Microsoft AD to Entra ID Governance Bridge

**Universal governance platform for AD to Entra ID and M365 migration.**
Not government-specific. Identity-first. No rip-and-replace.

## Canon Rule

> uiao-gos is a universal enterprise product. It is NOT government-specific.
> Federal compliance (FedRAMP, OSCAL, KSI) is one vertical adapter on top of
> the universal core. Never frame the core engine as federal-only.

## The Problem

Active Directory was not just an identity store. It was the implicit governance
model for every network service in the enterprise: DNS, DHCP, PKI, RADIUS,
LDAP authentication, GPO device policy, file services, and trust relationships.

Entra ID flattened the identity hierarchy but left all of that infrastructure
without a governance model. Microsoft gave you the tools. Nobody gave you
the framework for what decisions to make with those tools.

This directory-migration canon is that framework.

## What This Canon Governs

Not just users. Every object AD was holding together:

- Users, computers, service accounts
- Security groups and GPOs
- DNS, DHCP, and IPAM (InfoBlox / BlueCat)
- PKI / Certificate Services
- RADIUS / 802.1X / VPN authentication
- LDAP-dependent applications
- Kerberos SPNs and application registrations
- Cross-domain and cross-forest trust relationships

## The Five Phases

1. **Discover** — complete governance inventory of what AD actually encodes
2. **Normalize** — rationalize decades of organic growth into a clean authority model
3. **Map** — translate X.500/LDAP governance into Entra ID equivalents
4. **Migrate** — execute with continuous validation
5. **Validate** — prove governance continuity with evidence

## Built On

UIAO's Eight Core Concepts — proven in federal civilian compliance under
FedRAMP Moderate, Zero Trust mandates, and TIC 3.0.

For the enterprise, it's easier.

## Structure

```
directory-migration/
├── README.md                              ← This file
├── eight-core-concepts.md                 ← The 8 universal architectural concepts
├── ad-dependency-inventory.md             ← 11 AD object types and migration risks
├── migration-adapter-registry.yaml        ← Adapter registry (separate from compliance adapters)
├── validation-checklist.md                ← Post-implementation validation
└── adapters/
    ├── ipam/
    │   ├── ipam-adapter-interface.md
    │   ├── infoblox/adapter-manifest.json
    │   └── bluecat/adapter-manifest.json
    ├── pki/pki-adapter-interface.md
    ├── radius/radius-adapter-interface.md
    ├── ldap-proxy/ldap-adapter-interface.md
    ├── sync-engine/sync-adapter-interface.md
    ├── device-management/device-adapter-interface.md
    ├── ntp/ntp-adapter-interface.md
    └── dfs/dfs-adapter-interface.md
```

## Related

- `src/uiao/modernization/orgtree/` — Identity modernization (OrgPath, dynamic groups, AUs, HR lifecycle)
- `src/uiao/canon/` — Core UIAO platform specifications (UIAO_001–202)
- Original source: `WhalerMike/uiao-gos` (archived via ADR-028, April 2026)
