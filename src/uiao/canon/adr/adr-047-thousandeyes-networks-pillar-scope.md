---
id: ADR-047
title: "ThousandEyes — Networks-Pillar Conditional Adoption Under GCC-Moderate"
status: PROPOSED
date: 2026-04-27
deciders:
  - governance-steward
  - networks-steward
  - procurement-steward
  - Michael Stratton
extends:
  - ADR-033
supersedes: []
tags:
  - fedramp
  - gcc-moderate
  - thousandeyes
  - networks-pillar
  - ztmm
  - sc-7
  - boundary
  - procurement
  - compensating-control
canon_refs:
  - UIAO_003
  - UIAO_109
related_findings:
  - FINDING-001
  - FINDING-002
related_discussions: []
---

# ADR-047: ThousandEyes — Networks-Pillar Conditional Adoption Under GCC-Moderate

## Status

**PROPOSED — 2026-04-27.** Captures UIAO's position on Cisco ThousandEyes
adoption under FedRAMP Moderate / GCC-Moderate. Promotion to ACCEPTED is
gated on (a) verified FedRAMP Marketplace authorization of the specific
SKU at the Moderate baseline and (b) procurement-side ratification of the
Networks-only framing.

## Context

The GCC-Moderate Boundary & ThousandEyes Assessment
(`inbox/New_FedRAMP_Boundary/GCC-Moderate_Boundary_and_ThousandEyes_Assessment_External_with_images.docx`)
addresses three procurement questions: live-assessment feasibility,
ThousandEyes suitability as a workaround, and total cost. The relevant
output for this ADR is the second: ThousandEyes covers approximately one
of the seven CISA ZTMM v2.0 pillars (Networks) plus the BGP / DNS / MITM
detection chain, and contributes nothing to the Identity, Devices, Data,
Applications & Workloads, Visibility & Analytics (cross-cutting), or
Automation & Orchestration (cross-cutting) pillars.

This is consequential because the same procurement conversations that
raise ThousandEyes routinely frame it as a *general* telemetry workaround
for the GCC-Moderate gap matrix. It is not. The headline gaps in that
matrix — Adoption Score behavioral baselines, Endpoint Analytics Advanced,
Entra Identity Protection ML, CAE real-time revocation, DLP behavioral
analytics, audit-retention cliffs — are not network problems and have no
ThousandEyes substitute.

The risk this ADR exists to manage is **opportunity cost**: a budget cycle
spent deploying ThousandEyes as a general workaround can create the
appearance of closing the gap while the Identity / Devices / Data pillars
— where the most consequential compound-attack risks live (see MITRE
Chains A and B in the canon spec) — go unaddressed.

## Decision

UIAO endorses ThousandEyes adoption under GCC-Moderate **only as a
Networks-pillar component of a broader compensating-architecture stack**,
subject to the preconditions in §3 below. UIAO does **not** endorse
ThousandEyes as a general workaround for the GCC-Moderate telemetry gap
matrix.

### 1. Endorsed scope

ThousandEyes is endorsed to address:

- **INR substitute** — synthetic latency / jitter / packet-loss to
  Microsoft front doors (per-ISP and per-peering path performance).
- **BGP / DNS / MITM detection chain** — BGP route monitoring, DNS
  tests, certificate-validation tests.
- **M365 service availability** — endpoint and HTTP server tests.

These map to the gap-matrix rows tagged `network_path_substitute`:

```
inr-realtime-path-metrics
network-connectivity-scores-per-location
```

(The Teams CQD EUII row, `cqd-euii-long-term`, is **not** in this set —
ThousandEyes' Microsoft Teams test type does not recover the per-call
EUII that drives the 28-day forensic cliff. Long-term CQD export remains
the answer for that row.)

### 2. Non-endorsed scope

ThousandEyes is explicitly **not** endorsed as a substitute for any of:

- Identity-pillar gaps (Entra Identity Protection ML, CAE real-time,
  cross-tenant access telemetry).
- Devices-pillar gaps (Endpoint Analytics Advanced, Intune behavioral
  analytics, EPM elevation, WUfB trend telemetry).
- Data-pillar gaps (DLP behavioral richness, sensitivity-label analytics,
  Office Optional diagnostic).
- Applications & Workloads gaps (Copilot / AI telemetry, app-protection
  policy violation analytics).
- Visibility & Analytics retention gaps (CQD EUII 28-day, Audit Standard
  180-day, M365 Usage Analytics 12+ month historical pivots).

A procurement package that lists ThousandEyes against any row outside
the endorsed scope above must be returned for rework.

### 3. Preconditions for adoption

Before ingest is permitted, all four must hold:

| # | Precondition | Owner |
|---|---|---|
| 1 | FedRAMP Marketplace authorization verified at the Moderate baseline for the **specific SKU** being purchased. | Procurement-steward |
| 2 | Cloud Agent egress documented as cross-boundary in the SSP (synthetic-probe metadata = source IPs, paths, timing — treated as egress for assessment purposes, not as a free signal). | 3PAO |
| 3 | Procurement framing names ThousandEyes as Networks-only and links to FINDING-002 and the gap matrix. | Procurement-steward |
| 4 | Compensating-architecture stack for Identity / Devices / Data pillars is on the same roadmap (not deferred behind this purchase). | Governance-steward |

If any precondition is not met, this ADR's endorsement does **not**
attach.

### 4. Alternatives considered

| Alternative | Why rejected |
|---|---|
| Adopt ThousandEyes as a general telemetry workaround. | Mis-spends against the actual risk surface. The Identity / Devices / Data pillars drive the headline findings and ThousandEyes covers none of them. |
| Decline ThousandEyes entirely; rely on agency SD-WAN / SASE for all Networks-pillar telemetry. | Some agencies do not have an SD-WAN / SASE deployment that produces equivalent BGP / DNS / MITM signal quality. ThousandEyes is a defensible Networks-pillar component when this is the case. |
| Defer the decision until MAS 2026 boundary refinement. | The Networks-pillar gap is real today. MAS 2026 may eventually descope INR-class telemetry from the boundary, but the agency still needs synthetic path measurement in the interim. |

## Consequences

### Positive

- Procurement conversations have a canonical reference for what
  ThousandEyes does and does not cover.
- Networks-pillar work proceeds without blocking on the broader
  compensating-architecture build.
- The gap matrix retains its integrity as the single source of truth for
  Identity / Devices / Data / cross-cutting gaps; ThousandEyes does not
  get smeared across rows it cannot address.

### Negative

- Agencies that interpreted ThousandEyes as a general workaround will
  need to re-scope their Identity / Devices / Data investments, which
  may require additional budget cycles.
- Precondition #1 (FedRAMP Marketplace SKU verification) introduces a
  procurement-side dependency that is not always trivial to satisfy.

### Neutral

- The compensating-architecture stack defined in the canon spec
  (`gcc-moderate-boundary-assessment/methodology.md`) is independent of
  this ADR and proceeds on its own schedule.

## Compliance and audit

- **NIST 800-53**: SC-7 (Boundary Protection — Cloud Agent egress
  documentation). SI-4 (Information System Monitoring — Sentinel
  ingestion of ThousandEyes data).
- **CISA ZTMM v2.0**: Networks pillar (Initial → Advanced when paired
  with the broader stack).
- **OMB M-22-09**: Networks pillar continuous-monitoring intent partially
  addressed.
- **FedRAMP Marketplace**: precondition #1 above is the audit anchor.

## Related

- **FINDING-001** — INR unavailable in GCC-Moderate.
- **FINDING-002** — ThousandEyes coverage scope (this ADR's
  decision-record companion).
- **ADR-033** — GCC Boundary Drift Class (this ADR extends).
- **Canon spec**:
  `src/uiao/canon/compliance/reference/gcc-moderate-boundary-assessment/`
- **Gap matrix**: `src/uiao/canon/data/gcc-moderate-telemetry-gaps.yaml`
- **Source memo**:
  `inbox/New_FedRAMP_Boundary/GCC-Moderate_Boundary_and_ThousandEyes_Assessment_External_with_images.docx`
