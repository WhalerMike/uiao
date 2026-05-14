---
adr_id: adr-068
title: "Kerberos / NTLM Elimination — Cloud Kerberos Trust, Certificate-Based Auth, and the NTLM Deprecation Timeline"
status: ACCEPTED
decided: 2026-05-13
deciders: Michael Stratton
updated: 2026-05-13
next_review: 2026-11-01
review_trigger: Microsoft Ignite 2026; Windows Server 2025 GA NTLM-deprecation milestones; any Cloud Kerberos trust posture change
impact: UIAO_135 §3.2 (Partially Defined gap closure); broader-than-SQL-server auth modernization (Spec3-D1.8 already covers SQL Server path)
supersedes: null
superseded_by: null
classification: Controlled
boundary: GCC-Moderate
---

# ADR-068: Kerberos / NTLM Elimination — Cloud Kerberos Trust, Certificate-Based Auth, and the NTLM Deprecation Timeline

## Status

**ACCEPTED** — May 13, 2026

## Context

Spec3-D1.8 (`Get-SQLServerAuthAudit.ps1`) covers the SQL Server path from Windows Authentication (Kerberos/NTLM) to Entra ID auth for SQL 2022+. That covers one workload class. The broader auth modernization for the rest of the on-premises Windows estate remains without an explicit canonical pattern in canon as of UIAO_135 §3.2:

- **NTLM** is the legacy challenge-response protocol Microsoft has signalled for retirement, with Windows Server 2025 GA and Notice 0009 establishing concrete deprecation milestones. Without a canonical NTLM elimination timeline, agencies migrate ad-hoc, leaving long-lived NTLM dependencies in the estate that block zero-trust posture and produce monitoring noise.
- **Kerberos** is harder to retire because legitimate workloads still depend on it for delegated authentication patterns Entra ID does not yet fully replicate. The canonical question is **which Kerberos trust posture is the target** — full retirement, hybrid via Cloud Kerberos trust, or per-application carve-outs.
- **Certificate-based authentication (CBA)** is the canonical modern-auth replacement for password-based auth in Entra ID, but its rollout sequencing relative to NTLM disablement is not yet documented as canon.

UIAO_135 §3.2 explicitly flags this as a gap. Without canonical positions, every engagement re-litigates the same protocol-modernization tradeoffs, and the migration audit cannot certify that the post-migration estate satisfies the zero-trust posture mandated by PWS p. 112 and Solicitation 24322626R0007 Amd 4.

## Decision

**Three canonical positions, in operational sequence:**

### 1. NTLM is deprecated and elimination is mandatory by 2027-04-01 (Notice 0009 mandate)

- **Phase A (assess):** Tier-2 NTLM telemetry adapter (CCM-BIR ingestion + `Spec3-D1.x` NTLM-audit discovery) inventories every NTLM authentication event in the estate.
- **Phase B (block-where-safe):** NTLMv1 is disabled tenant-wide on schedule X (default: immediately on Phase A completion). NTLMv2 is restricted via Group Policy to documented exception groups only.
- **Phase C (eliminate):** All remaining NTLMv2 authentications are remediated to Kerberos or modern auth. Disablement at the LSA layer occurs on the Notice 0009 deadline.
- **Exception class:** A documented exception list of legacy applications that cannot be remediated by the deadline. Each exception requires a per-app ADR citing the inability-to-migrate reason and the compensating control.

### 2. Cloud Kerberos trust is the canonical hybrid Kerberos posture; standalone on-prem Kerberos is sunset

- **Cloud Kerberos trust** (Entra ID-issued Kerberos TGTs against a synthetic computer object in AD) is the canonical mechanism for Entra-joined or Entra-registered devices to acquire Kerberos tickets for legacy on-prem resources without retaining on-prem domain join. This pattern keeps Kerberos available for legacy file-share, print-queue, and database access **without** preserving the on-prem KDC trust as the authoritative authentication path.
- **Standalone on-prem Kerberos** (domain-joined endpoints authenticating to on-prem KDCs) is retained for the duration of the migration but is **not** the target end-state. Every domain-joined endpoint is on an explicit Entra-join migration path per ADR-001 (HAADJ deprecated) and ADR-002 (Arc + Entra join for servers).
- **Constrained delegation** (S4U2Proxy and friends) is permitted only for documented legacy applications; new integrations cannot rely on constrained delegation per ADR-004 (workload-identity-federation-default).

### 3. Certificate-based authentication (Entra CBA) is the canonical modern-auth replacement; rollout sequence is documented

- **Target state:** Every privileged account authenticates via Entra CBA against the Federal Common Policy CA G2 chain (or agency-equivalent FPKI sub-CA). Non-privileged user authentication uses passwordless flows (FIDO2, Windows Hello for Business, or CBA) with passwords as fallback only during migration.
- **Rollout sequence:** (a) Privileged accounts first — every PIM-eligible role assignment requires CBA before activation; (b) Service accounts second — workload identity federation per ADR-004 supersedes password-based service-account auth; (c) Non-privileged users last — phased by OrgPath segment with explicit pilot → ring → broad deployment cadence.
- **Companion ADR:** ADR-051 (SAML federation trust anchor) defines the federation-layer trust anchor. ADR-068 covers the authentication-layer migration that sits beneath it.

## Rationale

1. **NTLM has no zero-trust story.** Every NTLM event is opaque to telemetry, lacks meaningful auditability beyond the originating account name, and grants no device-trust context. PWS p. 112 zero-trust posture cannot be satisfied while NTLM is in-band; the only question is timeline.

2. **Cloud Kerberos trust preserves the legitimate Kerberos use cases without retaining the legacy KDC dependency.** The bulk of legitimate Kerberos use is "user on Entra-managed device needs an SMB share on a legacy file server" — Cloud Kerberos trust covers that flow without preserving on-prem domain join.

3. **CBA is mandated for federal-personnel access already.** Solicitation 24322626R0007 Amd 4 Clause 1752.224-70(b) and PWS p. 112 establish PIV/CAC (which IS Entra CBA against the Federal Common Policy CA chain) as the federal-personnel authentication standard. This ADR aligns the substrate's authentication modernization with the federal-personnel mandate.

4. **Sequencing matters.** Disabling NTLM before CBA is rolled out leaves the estate without an authentication path for the migrated workloads. The canonical sequence — assess → block-where-safe → CBA rollout → eliminate — produces a workable migration without breaking workloads, but only if the order is preserved.

5. **Exception class prevents the spec from being aspirational.** A small number of legacy applications cannot be migrated by 2027-04-01 (mainframe-bound terminal emulators, vendor appliances with hard-coded NTLM, etc.). A documented exception class with per-app ADRs makes the deprecation real for everything else while honestly accepting the residual long-tail.

## Implementation Plan

| Phase | Deliverable | Owner | Notice 0009 alignment |
|---|---|---|---|
| **A** | `Spec3-D1.x` NTLM-audit discovery script | Identity team | Pre-2027-04-01 |
| **A** | CCM-BIR adapter ingestion of NTLM telemetry | Telemetry team | Pre-2027-04-01 |
| **B** | NTLMv1 disablement Group Policy + tenant-wide audit | Identity team | 2026-Q3 |
| **B** | Cloud Kerberos trust enabled tenant-wide | Identity team | 2026-Q4 |
| **C** | Entra CBA rollout — privileged accounts | Identity team | 2026-Q4 → 2027-Q1 |
| **C** | Entra CBA rollout — service accounts (WIF per ADR-004) | Identity team | 2027-Q1 |
| **C** | Entra CBA rollout — non-privileged users by OrgPath | Identity team | 2027-Q1 → 2027-Q2 |
| **C** | NTLMv2 disablement at LSA layer | Identity team | **2027-04-01 (mandatory)** |
| **C** | Exception-class ADRs filed per residual legacy app | App owners | Continuous |

## Consequences

**Positive:**
- Concrete, sequenced timeline aligns substrate authentication modernization with Notice 0009 mandatory adoption date.
- Cloud Kerberos trust preserves legitimate Kerberos use cases without retaining the on-prem KDC trust as the authoritative path.
- CBA rollout sequence is deterministic; agencies execute the same pattern regardless of which RIT they're on.
- Exception-class ADRs surface residual long-tail dependencies as named known-unknowns rather than silent failures.

**Negative:**
- Cloud Kerberos trust requires Windows Server 2019+ domain functional level on the remaining on-prem AD; older infrastructure must be upgraded first.
- CBA rollout for non-privileged users at scale requires per-user smartcard issuance or alternative-credential provisioning that some agencies have not yet operationalized.
- The exception-class ADR process can become a backdoor for "we'll get to it later" if not actively reviewed.

**Operationally accepted:** the post-migration audit must enumerate every NTLM event observed against the documented exception list, and every CBA rollout phase must produce a sign-off ADR before the next phase proceeds.

## References

- ADR-001 — HAADJ deprecated; Entra Join only for clients
- ADR-002 — Arc + Entra Join (no domain join) for servers
- ADR-004 — Workload identity federation as default for external integrations
- ADR-051 — SAML federation trust anchor
- UIAO_135 §3.2 — Partially Defined transformation gaps
- Spec3-D1.8 — `Get-SQLServerAuthAudit.ps1` (SQL Server path covered separately)
- Notice 0009 — https://www.fedramp.gov/20x/notice-0009/
- Microsoft Learn: "NTLM deprecation"
- Microsoft Learn: "Cloud Kerberos trust deployment"
