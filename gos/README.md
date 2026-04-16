# uiao-gos — Governance OS for Enterprise Directory Migration

**Universal governance platform for AD to Entra ID and M365 migration.**
Not government-specific. Identity-first. No rip-and-replace.

## The Problem
Active Directory was not just an identity store. It was the implicit governance
model for every network service in your enterprise: DNS, DHCP, PKI, RADIUS,
LDAP authentication, GPO device policy, file services, and trust relationships.

Entra ID flattened the identity hierarchy but left all of that infrastructure
without a governance model. Microsoft gave you the tools. Nobody gave you
the framework for what decisions to make with those tools.

gos is that framework.

## What gos Governs
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
1. Discover  — complete governance inventory of what AD actually encodes
2. Normalize — rationalize decades of organic growth into a clean authority model
3. Map       — translate X.500/LDAP governance into Entra ID equivalents
4. Migrate   — execute with continuous validation
5. Validate  — prove governance continuity with evidence

## Built On
UIAO's Eight Core Concepts — proven in federal civilian compliance under
FedRAMP Moderate, Zero Trust mandates, and TIC 3.0.
For the enterprise, it's easier.

## Related Repositories
- uiao-core: Federal reference architecture and compliance canon
- uiao-docs: Architectural narrative and strategic documentation

## License
Apache 2.0 — see LICENSE
