---
id: ADR-030
title: "GCC Boundary Drift Class and Compensating Controls Architecture"
status: proposed
date: 2026-04-19
deciders:
  - governance-steward
  - security-steward
  - identity-engineer
supersedes: []
related_adrs:
  - ADR-028
  - ADR-029
canon_refs:
  - Appendix_U_Multi_Cloud_Boundary_Model
  - Appendix_M_Drift_Detection_Engine
  - Appendix_X_Governance_Telemetry_Model
uiao_doc_ref: UIAO_GCC_001
---

# ADR-030: GCC Boundary Drift Class and Compensating Controls Architecture

## Status

Proposed

## Context

### The Invisible Boundary Problem

Microsoft 365 GCC-Moderate is a tenancy designation on commercial
(.com) infrastructure with FedRAMP Moderate authorization. Unlike
GCC-High, there is no physically separate cloud. Intune for GCC-Moderate
is explicitly the commercial Intune service instance — same endpoints,
same infrastructure, same feature surface as any commercial customer.

However, a systematic class of failures occurs in GCC-Moderate
deployments that is not documented by Microsoft and is not visible
until features are activated and expected data never appears:

1. **Telemetry-dependent features fail silently.** FedRAMP Moderate
   compliance postures typically block or restrict Windows diagnostic
   telemetry endpoints (DiagTrack service, `*.events.data.microsoft.com`,
   `vortex.data.microsoft.com`). Intune features that depend on this
   pipeline — Endpoint Analytics, device performance reporting, anomaly
   detection, Windows quality update compliance — show as available in
   the portal but produce no data. No error is raised. Dashboards remain
   permanently empty.

2. **Location services are explicitly unavailable.** The Intune Locations
   feature (network fence / geofencing for compliance policies) is
   documented as unavailable for government customers. This eliminates
   a primary mechanism for scoping device compliance policies by
   organizational boundary.

3. **Diagnostic settings and Workbooks are unavailable.** Features
   expected for operational monitoring are silently absent.

4. **Windows Update management features are in planning phase.**
   Expedited updates, feature updates, Device Health Attestation, BIOS
   configuration policies, and DFCI are unavailable with no confirmed
   delivery dates for GCC-Moderate.

5. **ARC observability is degraded.** Azure Arc's monitoring plane
   (Azure Monitor extensions, VM Insights, Change Tracking) depends on
   telemetry flowing to Azure Commercial endpoints that FedRAMP-compliant
   network controls may restrict. Management plane functions but
   visibility plane is dark.

### Why This Is Not Documented by Microsoft

Microsoft's government service description document covers only
GCC-High and DoD. GCC-Moderate customers are directed to commercial
Intune documentation, which describes full feature availability. The
gap between what the documentation promises and what functions in a
correctly-hardened FedRAMP Moderate environment is discovered only
operationally — by administrators who activate features and observe
empty dashboards, then spend weeks diagnosing the silence.

This creates a systematic compliance risk: the SSP for a GCC-Moderate
deployment may claim inherited controls from Microsoft's M365 GCC-Moderate
FedRAMP package for features that are, in practice, non-functional. When
a 3PAO tests those controls, the evidence base is absent.

### Existing UIAO Drift Taxonomy Limitation

The existing five-class drift taxonomy (DRIFT-SCHEMA, DRIFT-SEMANTIC,
DRIFT-PROVENANCE, DRIFT-AUTHZ, DRIFT-IDENTITY) does not cover this
class of failure. The deviation is:
- Not a schema violation
- Not a semantic inconsistency in data
- Not a provenance gap
- Not an authorization problem
- Not an identity issue

It is a structural gap in the governance boundary itself — features
that are nominally within an authorized boundary but functionally
unavailable due to undocumented constraints imposed by the cloud
service provider. This requires a new drift class.

## Decision

### 1. Introduce DRIFT-BOUNDARY as a Sixth Drift Class

Add `DRIFT-BOUNDARY` to the canonical drift taxonomy alongside the
existing five classes. Definition:

> **DRIFT-BOUNDARY**: A feature, capability, or service that is
> nominally within the authorized system boundary and appears available
> in administrative interfaces, but is functionally unavailable or
> produces no data due to undocumented restrictions, telemetry
> dependencies that conflict with FedRAMP compliance controls, or
> cloud service provider limitations not reflected in official
> documentation. The drift exists within the CSP's infrastructure
> and is not correctable by tenant configuration.

Severity classification for DRIFT-BOUNDARY findings:

| Impact Category    | Severity | Example                              |
|--------------------|----------|--------------------------------------|
| Security control   | P1       | Device Health Attestation unavailable|
| Operational visibility | P2   | Endpoint Analytics empty             |
| Compliance documentation | P2 | SSP claims unsupported capability   |
| Feature capability | P3       | Location fence unavailable           |
| Analytics/reporting | P3      | Workbooks absent                    |

### 2. Introduce the GCC Boundary Probe Adapter

A new modernization adapter (`gcc-boundary-probe-v1`) performs
automated functional testing of Microsoft service features within
the tenant. It distinguishes:

- `FUNCTIONAL`: Feature operates as documented
- `SILENTLY_BLOCKED`: Feature appears available but produces no data
- `EXPLICITLY_UNAVAILABLE`: Feature is documented as unavailable
- `PLANNING_PHASE`: Feature is on Microsoft's government roadmap
- `COMPENSATED`: Gap exists but a UIAO compensating control provides
  equivalent governance capability

The probe runs as part of `uiao substrate walk` and emits
`DriftFinding` objects with `drift_class: DRIFT-BOUNDARY`.

### 3. Introduce the Compensating Controls Registry

A machine-generated, canonized YAML document
(`src/uiao/canon/gcc-boundary-gap-registry.yaml`) serves as:

- A living inventory of boundary gaps and their status
- A compensating controls map (gap → UIAO control → NIST control)
- An ATO artifact for the SSP inherited controls section
- Input to the continuous monitoring KSI signal set

The registry is updated automatically on each probe run and
promoted to canonical status through the Appendix V contributor
workflow.

### 4. Introduce In-Boundary Telemetry Aggregation

A UIAO telemetry aggregation service replaces blocked Microsoft
telemetry pipelines with in-boundary alternatives:

- Device health via WMI/CIM local queries (no telemetry endpoint)
- Intune management state via Graph API (management plane, not
  telemetry plane — available in GCC-Moderate)
- Update compliance via Windows Update for Business Graph reports
- Configuration drift via Intune compliance policy results via Graph
- AD/device correlation from the existing AD survey adapter

This satisfies NIST 800-137 continuous monitoring requirements
without dependency on Microsoft's commercial telemetry pipeline.

### 5. Extend Appendix U

The current Appendix U boundary model has two categories:
in-scope and excluded. Add a third:

> **Nominally In-Scope, Functionally Restricted**: Services that are
> within the FedRAMP-authorized boundary contractually but produce
> no operational value in a correctly-hardened FedRAMP Moderate
> deployment. Governed by DRIFT-BOUNDARY detection and the
> compensating controls registry.

### 6. OrgPath as Location Service Replacement

The blocked Locations feature (network fence) is architecturally
replaced by OrgPath-scoped device groups. Device objects enrolled
in Intune and/or ARC carry OrgPath in extensionAttribute1, enabling
dynamic group membership that scopes compliance policies by
organizational unit — which is more accurate than physical location
for centralized-datacenter environments.

## Consequences

### Positive

- The invisible boundary becomes a visible, governed, auditable
  registry — a first-class canonical artifact
- The SSP can accurately represent capability gaps and compensating
  controls instead of claiming functionality that doesn't exist
- Continuous monitoring obligation (NIST 800-137) is satisfied
  through the in-boundary telemetry alternative
- 3PAO audit evidence exists for every documented gap
- OrgPath-scoped device policy targeting is architecturally superior
  to geography-based targeting for centralized environments
- DRIFT-BOUNDARY findings automatically feed the KSI signal set
  (Appendix T risk scoring)

### Negative

- Adds implementation complexity: probe adapter, telemetry
  aggregation service, registry generation pipeline
- Microsoft roadmap gaps (Device Health Attestation, Feature Updates)
  remain uncompensated until Microsoft delivers government support
- DRIFT-BOUNDARY class cannot be auto-remediated — gaps in Microsoft
  infrastructure require Microsoft resolution or permanent compensating
  control designation
- Requires ADR-031 to formally extend Appendix U with the third
  boundary category before any probe output is canonical

### Risks

- Probe accuracy depends on telemetry endpoint accessibility at
  probe run time — probe results may vary based on network policy
  at the collection point
- Microsoft may change feature availability without notice — probe
  must run on a scheduled basis (recommended: weekly) not just at
  initial deployment
- Compensating controls must be re-validated at each annual ATO
  renewal cycle

## Implementation Path

1. Merge ADR-030 (this document) — governance gate
2. Add DRIFT-BOUNDARY to drift taxonomy in
   `docs/docs/16_DriftDetectionStandard.qmd`
3. Deploy `gcc-boundary-probe-v1` adapter to
   `impl/src/uiao/impl/adapters/modernization/gcc-boundary-probe/`
4. Generate initial `gcc-boundary-gap-registry.yaml` from first probe run
5. Submit registry as canonical artifact via Appendix V workflow
6. Update Appendix U with third boundary category (ADR-031)
7. Deploy in-boundary telemetry aggregation service
8. Wire probe output to KSI signal set (Appendix T)
