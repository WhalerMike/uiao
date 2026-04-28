---
adr_id: adr-002
title: "Arc-Enabled Servers Require Non-Domain-Joined State"
status: ACCEPTED
decided: 2026-04-28
deciders: Michael Stratton
updated: 2026-04-28
next_review: 2026-11-01
review_trigger: Microsoft Ignite 2026; any Azure Arc or Windows Server identity announcement
impact: UIAO_IDT_002 Spec 1 (Computer Object Transformation — Servers)
supersedes: null
superseded_by: null
classification: Controlled
boundary: GCC-Moderate
---

# ADR-002: Arc-Enabled Servers Require Non-Domain-Joined State

## Status

**ACCEPTED** — April 28, 2026

## Context

The UIAO Computer Object Transformation spec must define how on-premises servers transition from AD domain-joined identities to cloud-managed identities. Azure Arc is the designated management plane for servers that remain on-premises (or in non-Azure hosting) while participating in Entra ID governance.

The AADLoginForWindows extension for Azure Arc enables Entra ID-based RDP authentication to Arc-enabled servers, replacing domain credential-based RDP. This capability is central to eliminating AD domain controller dependencies for server management.

However, a critical architectural constraint exists that shapes the entire server migration strategy.

## Decision

**Server migration from domain-joined to Arc-enabled with Entra ID authentication is a hard cutover, not a gradual hybrid transition. The AADLoginForWindows extension requires the server NOT be joined to any domain (AD or Entra Domain Services). This means servers must be unjoined from AD before Entra ID login can be enabled.**

## Rationale

1. **Microsoft documentation explicitly states the constraint.** From Microsoft Learn: *"After you enable this capability, your Arc-enabled machine will be Microsoft Entra joined. You can't join them to another domain, like on-premises Active Directory or Microsoft Entra Domain Services."* The server cannot simultaneously be domain-joined and Entra ID-joined.

2. **Windows Server 2025 or later is required.** The AADLoginForWindows extension requires Windows Server 2025 with Desktop Experience. Windows Server 2019 and 2022 can be Arc-enabled for management and telemetry but cannot use Entra ID authentication for RDP.

3. **No hybrid coexistence for server identity.** Unlike endpoints (which had HAADJ as a bridge), servers have no dual-identity state. A server is either domain-joined OR Entra ID-joined via Arc — never both simultaneously.

4. **Azure RBAC replaces local/domain group membership for server access.** Once Entra ID-joined via Arc, server RDP access is controlled through Azure roles: Virtual Machine Administrator Login and Virtual Machine User Login. Local Administrators group membership from AD no longer applies.

## Consequences

### Positive
- Clean break from AD dependency — no lingering dual-state confusion
- Server access governed by Azure RBAC + Conditional Access (once supported for Arc)
- Managed identities available for servers to authenticate to Azure resources
- Passwordless authentication supported for server RDP
- Centralized access revocation — disabling Entra ID account immediately blocks server access

### Negative
- **Hard cutover required** — server must be unjoined from AD, which disrupts all AD-dependent services running on that server
- **All Kerberos-dependent services must be migrated first** — any service on the server that authenticates users or other services via Kerberos will break at domain unjoin
- **Group Policy stops applying** — all GPO-based configuration must be replicated via Arc/Azure Policy/desired state configuration before unjoin
- **Windows Server 2019/2022 cannot use Entra ID login** — these servers can be Arc-managed but retain AD identity until OS upgrade to 2025
- **No Conditional Access for Arc servers yet** — as of April 2026, CA policies cannot target Arc-enabled server logins (this is a known gap)
- **LAPS integration not yet available for Arc Entra-joined servers** — local admin password management needs an alternative approach during transition

### Migration Sequencing Implications
1. **Inventory all services on the server** before domain unjoin (D1.7 in Spec 1)
2. **Migrate all Kerberos-dependent services** off the server or to modern auth first
3. **Replicate all GPO settings** to Azure Policy / Arc configuration before unjoin
4. **Upgrade OS to Windows Server 2025** if not already running
5. **Unjoin from domain** → Install Arc agent → Deploy AADLoginForWindows extension
6. **Assign Azure RBAC roles** for server administrators
7. **Validate access** via Entra ID RDP authentication
8. **Disable/delete AD computer object** after validation period

## Verification Sources

| Source | URL | Last Verified |
|---|---|---|
| Microsoft Learn — Sign in to Arc-enabled server using Entra ID | https://learn.microsoft.com/en-us/entra/identity/devices/howto-vm-sign-in-azure-ad-windows#azure-arc | 2026-04-28 |
| Blog: Join your Windows Server 2025 to Entra ID (Sinnathurai) | https://blog.sinnathurai.ch — detailed walkthrough with caveats | 2026-04-28 |
| Mindcore Techblog — Azure Arc RDP with Entra ID Authentication | https://techblog.dvbmedia.net — extension deployment and limitations | 2026-04-28 |

## Review Triggers

This ADR must be re-evaluated when any of the following occur:

- [ ] Microsoft announces support for simultaneous domain-join + Entra join for servers (hybrid server identity)
- [ ] AADLoginForWindows extension adds support for Windows Server 2019 or 2022
- [ ] Conditional Access adds support for Arc-enabled server login sessions
- [ ] LAPS integration becomes available for Arc Entra-joined servers
- [ ] Microsoft announces an in-place domain-unjoin + Entra-join migration tool for servers
- [ ] Microsoft Ignite 2026 (November) — scheduled review
- [ ] Microsoft Build 2027 (May) — scheduled review

## Related Documents

- UIAO_IDT_001 — Identity & Directory Transformation Inventory (Transformation #6: Azure Arc Telemetry Projection)
- UIAO_IDT_002 — Spec 1: Computer Object Transformation (D2.8: Server Management Transition Architecture)
- ADR-001 — HAADJ Deprecated — Entra ID Join as Sole Device Join Target
