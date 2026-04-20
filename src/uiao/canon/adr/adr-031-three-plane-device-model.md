---
id: ADR-031
title: "Three-Plane Device Model and OrgPath Plane-Aware Architecture"
status: proposed
date: 2026-04-20
deciders:
  - governance-steward
  - identity-engineer
  - security-steward
supersedes: []
related_adrs:
  - ADR-028
  - ADR-029
  - ADR-030
canon_refs:
  - Appendix_GAE
  - Appendix_GAD
  - Appendix_A_OrgPath_Codebook
  - Appendix_C_Attribute_Mapping_Table
  - Appendix_F_Migration_Runbook
---

# ADR-031: Three-Plane Device Model and OrgPath Plane-Aware Architecture

## Status

Proposed

## Context

The existing UIAO OrgPath model (Appendices A–F) was designed around
user objects. It assumes OrgPath is written to `extensionAttribute1`
and synced via Entra Connect — a model that works correctly for user
objects and Entra-joined client devices.

However, the architectural decomposition of the AD computer object
(Appendix GAE) reveals that devices do not map to a single construct.
They decompose across three planes:

- **Identity plane:** Entra Device object (clients only)
- **Management plane:** Intune (clients) or Azure Arc (servers as ARM resources)
- **Workload plane:** Service Principals / Managed Identities

Each plane has a different object type, different API surface, and
different OrgPath storage mechanism. A single OrgPath schema does
not fit all three.

Additionally, the existing Appendix F migration runbook describes
a single track for user objects. Computer objects require three
parallel migration tracks with independent gate criteria and different
technical paths.

## Decision

### 1. Formalize the Three-Plane Model as an Architectural Principle

Add to UIAO core principles (Section 3 of master document):

> **Principle 8: Plane Separation.**
> Identity, management, and workload functions are explicitly separated
> across distinct Microsoft service planes. No object crosses planes.
> OrgPath is the common organizational encoding across all planes,
> expressed in a plane-specific storage mechanism for each.

### 2. OrgPath Is Plane-Aware

The OrgPath value (`ORG-IT-SEC-SOC`) is universal. Its storage
mechanism is plane-specific:

| Plane | Object Type | OrgPath Storage | Targeting Mechanism |
|---|---|---|---|
| Identity (clients) | Entra Device | `extensionAttribute1` | Dynamic Entra group |
| Management (clients) | Intune enrollment | Inherited from Entra device | Intune scope tag |
| Management (servers) | Azure Arc machine | ARM resource tag `OrgPath` | Azure Policy assignment |
| Workload | Service Principal / MI | App tag or custom claim | App role / API permission |

Appendix C is extended with a Device Attribute Mapping section
covering all four plane-specific storage mechanisms.

### 3. Computer Disposition Map Is a Canonical Artifact

The output of the computer disposition classifier
(`disposition.py::classify_all_computers()`) is canonized as the
**Computer Disposition Map** — a formal UIAO artifact that:

- Declares the migration track for every AD computer object
- Identifies AD retirement blockers
- Provides the gate criteria for AD retirement readiness
- Is updated on each survey run and promoted via Appendix V workflow

### 4. Three Migration Tracks with Independent Gates

The Appendix F migration runbook is extended with three parallel tracks:

| Track | Scope | Target | Gate Criteria |
|---|---|---|---|
| Track 1 | Workstations / clients | Entra device + Intune | OrgPath coverage ≥ 99%, all GPO-to-profile mapping complete |
| Track 2 | Member servers | Azure Arc + OrgPath ARM tag | All eligible servers Arc-enrolled |
| Track 3 | Workload identity | SP + MI replacing SPNs/KCD | Zero unresolved SPNs on non-excluded objects |

Tracks 1 and 2 can proceed in parallel. Track 3 is a prerequisite
for AD retirement. Domain controllers (STAY-AD-DC) are retired last,
after all three tracks are complete for all other objects.

### 5. New Risk Factors in Appendix T

Eight computer-object-specific risk factors (RF-C01 through RF-C08)
are added to the identity risk scoring model (Appendix GAD.4).
Devices without OrgPath, servers with unresolved SPNs, and objects
with unconstrained Kerberos delegation receive elevated risk scores
that drive prioritized remediation.

### 6. New Canonical Appendices

| Appendix | Title | Category |
|---|---|---|
| GAD | Modernization Impact Model: Loss of Computer Objects | Model |
| GAE | Decomposition of the AD Computer Object | Model |
| GAF | Three-Track Computer Migration Runbook | Runbook |

GAF (three-track runbook) is the next canonical artifact to be authored,
following this ADR's approval.

## Consequences

### Positive

- OrgPath governance is now complete across all four planes — users,
  client devices, servers, and workload identities
- Computer Disposition Map provides the first machine-readable,
  canonical inventory of migration blockers
- Three-track structure prevents AD retirement being blocked by a
  single monolithic migration plan
- Risk factors RF-C01 through RF-C08 surface high-risk objects
  (unconstrained delegation, ADCS dependency) automatically in
  the identity risk score
- Track 1 and 2 can show early progress while Track 3 works through
  complex SPN mapping

### Negative

- ARM resource tagging for Arc machines requires Azure RBAC on the
  subscription — separate permission set from Graph API permissions
- Workload identity OrgPath (app tag / custom claim) is the least
  standardized plane and requires per-application implementation
- Three-track gate evaluation requires querying Entra, Arc, and
  Graph simultaneously — survey adapter must be extended

### Risks

- Track 3 (workload identity) has the highest variance in effort.
  A single legacy application with complex Kerberos delegation may
  block AD retirement for months. Early SPN cataloguing is critical.
- AD retirement readiness (`ad_retirement_ready` field in summary)
  will be false for most environments until Track 3 is substantially
  complete. This should be communicated to stakeholders early.

## Implementation Order

1. Merge ADR-031 (this document)
2. Canonize Appendix GAE and Appendix GAD
3. Deploy `disposition.py` as extension to active-directory adapter
4. Generate first Computer Disposition Map from survey output
5. Extend Appendix C with device attribute mapping section
6. Author Appendix GAF (three-track runbook) — next artifact
7. Wire RF-C01 through RF-C08 into Appendix T scoring
8. Update Appendix A to include ARM tag and app-tag OrgPath variants
