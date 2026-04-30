---
document_id: UIAO_009
title: "Microsoft Coverage And Gap Doctrine"
version: "1.0"
status: Draft
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-30"
updated_at: "2026-04-30"
boundary: GCC-Moderate
provenance:
  source: "ADR-049 §Decision 2 (allocation directive)"
  version: "1.0"
  derived_at: "2026-04-30"
  derived_by: "Doctrine extracted from ADR-049 §Why the gaps matter and the modernization-track inbox material analysis. Allocated and authored fresh — not derived from any external draft."
canonical_adrs:
  - ADR-035
  - ADR-038
  - ADR-040
  - ADR-049
canonical_docs:
  - UIAO_007
  - UIAO_135
  - UIAO_136
---

# UIAO_009 — Microsoft Coverage And Gap Doctrine

## Overview

UIAO's positioning is to **leverage Microsoft-native tooling** for the
identity / device / server / application planes, **provide the SSOT
governance shell** (canon, schemas, registries, drift detection), and
**fill the cross-plane gaps** Microsoft does not provide.

This document records the canonical statement of *what Microsoft does
provide that UIAO leverages* and *what Microsoft does not provide that
UIAO must fill*. Until this document was allocated, the latter
articulation lived only in inbox-scratch material and in the §Why the
gaps matter section of [ADR-049](adr/adr-049-microsoft-adapter-coverage-expansion.md);
ADR-049 §Decision 2 directed that it be promoted to canonical doctrine.
This document satisfies that directive.

The doctrine is canonical because every UIAO design decision —
adapter declaration, OrgPath ingestion contract, drift-engine
classification, downstream consumer modeling — depends on a stable
answer to "is this responsibility Microsoft's or UIAO's?"

## 1. The Two-Question Frame

UIAO design decisions reduce to two questions, asked in this order:

> **Q1.** Does Microsoft provide a usable surface for this concern?
>
> **Q2.** If yes, is the surface sufficient for UIAO governance, or
> does UIAO need to add structure on top?

Three outcomes follow:

| Q1 | Q2 | UIAO posture |
|---|---|---|
| **No** — Microsoft does not provide | n/a | **UIAO builds.** This is gap-fill territory. |
| **Yes** | **Sufficient** | **UIAO declares as adapter and consumes.** No additional structure required. The adapter registry is the declaration site. |
| **Yes** | **Insufficient** | **UIAO declares as adapter AND adds structure.** The structure is canonical (canon doc + ADR + drift class) and the Microsoft surface is the data plane. |

Most concrete UIAO components fit one of these three. The canonical
example of each:

- **Build** — OrgPath as a cross-plane dependency graph (no Microsoft
  surface). See §3.
- **Declare and consume** — Microsoft Entra Connect / Cloud Sync (HR
  → Entra sync; Microsoft-provided, sufficient). UIAO declares
  `entra-id` as an adapter and consumes its evidence.
- **Declare and structure** — Microsoft Intune (device configuration;
  Microsoft-provided but the OrgTree-policy-targeting binding adds
  structure UIAO requires). UIAO declares `entra-policy-targeting`
  (MOD_N) on top of Intune, and writes the binding to canon at
  [`canon/data/orgpath/policy-targets.yaml`](data/orgpath/policy-targets.yaml).

## 2. Microsoft Coverage UIAO Leverages

This section enumerates the Microsoft surfaces UIAO depends on and the
adapter (or adapters) that declares each.

### 2.1 Identity plane

| Microsoft surface | UIAO adapter declaration | Notes |
|---|---|---|
| Microsoft Entra ID (user / group / SP / Conditional Access) | [`entra-id`](modernization-registry.yaml) (active) | The base identity adapter. |
| Microsoft Entra Connect / Cloud Sync | n/a — sufficient as configured; no UIAO adapter required | Microsoft-managed bridge. |
| Microsoft Entra ID Governance (Access Reviews, Entitlement Mgmt, Lifecycle Workflows, PIM, SoD) | [`entra-id-governance`](modernization-registry.yaml) (reserved per ADR-049) | Sibling of `entra-id`, declared separately because the governance surface has its own configuration model and lifecycle. |
| Microsoft Entra Workload Identity | [`entra-workload-identity`](modernization-registry.yaml) (reserved per ADR-049) | Anchored in [ADR-004](adr/adr-003-api-driven-inbound-provisioning.md) workload-identity-federation-default. |
| Microsoft Defender for Cloud Apps (read-only discovery) | [`defender-for-cloud-apps`](adapter-registry.yaml) (reserved per ADR-049) | OAuth inventory, Shadow IT discovery, app risk scoring, session analytics. |
| Microsoft Defender for Cloud Apps (change-making actions) | [`defender-for-cloud-apps-actions`](modernization-registry.yaml) (reserved per ADR-049) | OAuth governance writes, session-control policy, Conditional Access App Control. |

### 2.2 Device plane

| Microsoft surface | UIAO adapter declaration | Notes |
|---|---|---|
| Microsoft Intune (configuration profiles, compliance policies, baselines, Autopilot, app deployment) | [`intune`](modernization-registry.yaml) (modernization side, reserved per ADR-049) + [`intune`](adapter-registry.yaml) (conformance side, reserved) | Two-axis declaration per ADR-049 §Decision 1. |
| Intune policy targeting by OrgTree | [`entra-policy-targeting`](modernization-registry.yaml) (active, MOD_N / [ADR-039](adr/adr-039-policy-targeting.md)) | UIAO structure on top of Microsoft Intune assignments. |
| Microsoft Defender for Endpoint | [`defender-for-endpoint`](adapter-registry.yaml) (reserved per ADR-049) | Device exposure score, software/vulnerability inventory, attack-path analysis. |
| Windows Autopilot | n/a — consumed via `intune` adapter scope | Not a separate declaration. |

### 2.3 Server plane

| Microsoft surface | UIAO adapter declaration | Notes |
|---|---|---|
| Azure Arc (server onboarding, managed identity attachment) | [`active-directory`](modernization-registry.yaml) (Phase F) + [`entra-device-orgpath`](modernization-registry.yaml) (MOD_C / [ADR-038](adr/adr-038-device-plane-orgpath.md)) | OrgPath propagation to Arc machines is structured by UIAO. |
| Azure Policy for Arc (compliance + remediation) | [`azure-policy-arc`](modernization-registry.yaml) (reserved per ADR-049) | Body authoring + remediation; complements MOD_N targeting. |
| Microsoft Defender for Servers | [`defender-for-servers`](adapter-registry.yaml) (reserved per ADR-049) | EDR, posture, vulnerability, baseline state for hybrid servers. |
| Azure Migrate (dependency discovery) | [`azure-migrate`](adapter-registry.yaml) (reserved per ADR-049) | Primary native input for OrgPath server-plane edges. |
| Arc Guest Configuration / Azure Monitor Agent / Update Management | n/a — consumed via `azure-policy-arc` adapter scope | Not separate declarations. |

### 2.4 Application plane

| Microsoft surface | UIAO adapter declaration | Notes |
|---|---|---|
| Microsoft 365 tenant (Exchange, SharePoint, Teams, Purview, Defender for O365) | [`m365`](modernization-registry.yaml) (active) | Base M365 tenant adapter. |
| CISA SCuBA M365 Secure Baseline (apply) | [`scuba`](modernization-registry.yaml) (active) | Modernization side. |
| CISA SCuBA M365 Secure Baseline (assess) | [`scubagear`](adapter-registry.yaml) (active) | Conformance side. |
| Entra Enterprise Apps / App Proxy (SSO) | n/a — consumed via `entra-id` adapter scope | Not a separate declaration; SSO migration is a MOD-level transformation, not an adapter. |

### 2.5 Discovery / extraction

The PowerShell-based discovery scripts under
[`tools/discovery/`](../../../tools/discovery/) (Spec1-D1.x, Spec2-D1.x,
Spec3-D1.x) are not adapters but *deliverables of UIAO_136*. They
extract data Microsoft does not expose in adapter-friendly form
(LDAP bind events, GPO inventories, AD service account audits). Their
output feeds the OrgPath ETL contract documented in UIAO_007 §Discovery
Feeders (forthcoming sibling section to this doctrine).

## 3. The Four Gaps Microsoft Does Not Provide

This is the load-bearing section of UIAO_009. UIAO exists because
Microsoft tooling, even when fully leveraged, does not deliver these
four capabilities. Each gap is a UIAO build responsibility and a
canonical UIAO surface.

### 3.1 Gap #1 — Cross-plane dependency graph (Identity → Device → Server → App → Data)

**Microsoft does not provide:** a single graph that unifies identity,
device, server, application, and data dependencies into a queryable
model.

Microsoft surfaces *do* provide per-plane data:

- Entra sign-in logs (identity → app)
- Intune device inventory (identity → device)
- Defender attack paths (within device plane)
- Azure Migrate dependency mapping (server → server)
- M365 audit logs (within app plane)

What Microsoft does *not* provide is the cross-plane join. Identifying
the blast radius of decommissioning a domain controller requires
correlating evidence from at least four of the surfaces above. No
Microsoft product does that natively.

**UIAO fills with:** OrgPath as a canonical cross-plane dependency
graph.

- **Anchor canon:** [ADR-035 — OrgPath Codebook Binding](adr/adr-035-orgpath-codebook-binding.md), [ADR-038 — Device-plane OrgPath](adr/adr-038-device-plane-orgpath.md), [ADR-048 — OrgPath Attribute Selection](adr/adr-048-orgpath-attribute-selection.md).
- **Executable canon:** [`canon/data/orgpath/codebook.yaml`](data/orgpath/codebook.yaml), [`canon/data/orgpath/dynamic-groups.yaml`](data/orgpath/dynamic-groups.yaml), [`canon/data/orgpath/admin-units.yaml`](data/orgpath/admin-units.yaml), [`canon/data/orgpath/device-planes.yaml`](data/orgpath/device-planes.yaml), [`canon/data/orgpath/policy-targets.yaml`](data/orgpath/policy-targets.yaml).
- **Implementation:** [`src/uiao/adapters/entra_device_orgpath.py`](../adapters/entra_device_orgpath.py), [`src/uiao/adapters/entra_policy_targeting.py`](../adapters/entra_policy_targeting.py), and the four MOD adapters (B/C/D/N).
- **Ingestion:** UIAO_007 §Discovery Feeders (forthcoming) names the canonical adapter id for each OrgPath input stream.

### 3.2 Gap #2 — Multi-plane drift engine

**Microsoft does not provide:** a drift detector that observes drift
*across* the identity / device / server / app planes simultaneously
and classifies findings into a unified taxonomy.

Microsoft surfaces *do* provide per-plane drift detection:

- Entra ID Conditional Access policy audit (identity)
- Intune compliance non-compliance reports (device)
- Azure Policy compliance state (server)
- Defender for Cloud Apps anomaly detection (app)

What Microsoft does *not* provide is the cross-plane reconciliation
or the canonical taxonomy. A drift in OrgPath that propagates through
dynamic-group → admin-unit → policy assignment cannot be observed as a
single causal chain by any Microsoft tool.

**UIAO fills with:** the OrgTree drift engine and the five-class
canonical drift taxonomy.

- **Anchor canon:** [ADR-040 — OrgTree Drift Detection Engine — Six-Phase Orchestrator](adr/adr-040-drift-engine.md).
- **Taxonomy:** DRIFT-SCHEMA, DRIFT-SEMANTIC, DRIFT-PROVENANCE,
  DRIFT-AUTHZ, DRIFT-IDENTITY (per ADR-040 §Decision and ADR-012).
- **Executable canon:** [`canon/data/orgpath/drift-engine-config.yaml`](data/orgpath/drift-engine-config.yaml).
- **Implementation:** [`src/uiao/governance/drift_engine.py`](../governance/drift_engine.py).
- **Adapter declaration:** [`orgtree-drift-engine`](modernization-registry.yaml) (active).
- **Halt-on-critical posture:** any P1 finding during Classify halts
  the remediation pass entirely; governance-review ops never
  auto-dispatch.

### 3.3 Gap #3 — GPO → Intune mapping with operational sequencing

**Microsoft does not provide:** a deterministic, sequenced migration
plan from on-prem Group Policy to Intune configuration profiles. The
Microsoft Group Policy Analytics tool maps individual GPOs to Intune
settings but does not produce a phased rollout sequence with
dependency awareness.

Microsoft surfaces *do* provide:

- Group Policy Analytics (per-setting mapping)
- Intune profile templates
- Compliance policy templates

What Microsoft does *not* provide is the *order* in which to migrate
GPOs given a population of devices with overlapping memberships and
inherited settings.

**UIAO fills with:** the Spec 1 Phase 2 transformation specifications
and the OrgTree-based device cohort sequencing.

- **Anchor canon:** [UIAO_007 — OrgTree Modernization (AD → Entra)](UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md), [UIAO_136 §SPEC 1](UIAO_136_priority1-transformation-project-plans.md).
- **Discovery:** Spec1-D1.x discovery scripts under
  [`tools/discovery/`](../../../tools/discovery/).
- **Sequencing model:** OrgTree dynamic groups (MOD_B / [ADR-036](adr/adr-036-dynamic-group-provisioning.md)) define device cohorts; policy targeting (MOD_N) binds Intune profiles to those cohorts.
- **Open work:** Spec 1 Phase 2 deliverables (D2.x) are not yet
  authored; this is a known UIAO surface to expand.

### 3.4 Gap #4 — Deterministic domain-retirement sequencing

**Microsoft does not provide:** a deterministic plan for retiring on-
prem AD domain dependencies. Microsoft guidance ("Retiring AD with
Entra ID + Azure Arc") is structural — it names the steps —
but is explicit that "not all journeys are the same" and stops short
of a deterministic sequence.

Microsoft surfaces *do* provide:

- Per-server Arc onboarding flow (server-by-server)
- Group Policy Analytics (per-policy migration aid)
- Workload identity federation (per-service-account migration)
- Entra app provisioning (per-app SSO migration)

What Microsoft does *not* provide is the *cross-server* sequence:
which servers must be modernized first because they hold dependencies
that block others, and which domain dependencies can be retired safely
because nothing else needs them.

**UIAO fills with:** the OrgPath dependency graph (§3.1) operationalized
through the Spec 2 / Spec 3 transformation plans.

- **Anchor canon:** UIAO_007 §domain-retirement guidance (forthcoming
  sibling section to the §Discovery Feeders contract); UIAO_136 §SPEC
  3 (Service Account → Workload Identity Mapping); ADR-049
  §Decision 2 reference for `azure-migrate` (the cross-server
  dependency feeder).
- **Mechanism:** OrgPath edges from Azure Migrate + AD discovery
  scripts produce a directed dependency graph; topological sort
  yields the retirement sequence; per-wave validation gates ensure
  no in-use dependency is decommissioned.
- **Open work:** the topological-sort + validation-gate logic is not
  yet implemented; the dependency-graph data is present, the
  sequencing engine is not.

## 4. What This Doctrine Implies

### 4.1 For new adapter proposals

Any proposed new UIAO adapter MUST satisfy at least one of:

1. Declares a Microsoft surface UIAO depends on but does not yet
   declare (the §2 coverage map).
2. Implements one of the four §3 gaps (UIAO build).
3. Provides cross-plane structure on top of Microsoft surfaces (the
   "Declare and structure" outcome from §1).

If a proposed adapter doesn't satisfy any of these, the proposal is
out of scope for UIAO and should be evaluated against UIAO_002 (SCuBA
Technical Specification) or treated as a downstream agency-specific
extension.

### 4.2 For drift-engine classification

Findings the OrgTree drift engine produces MUST be classifiable into
one of the five drift classes (per ADR-040 / ADR-012). If a finding
doesn't fit any class, the discrepancy is between this doctrine and
the drift taxonomy — file an ADR; don't add a sixth class without
governance review.

### 4.3 For canon expansion decisions

When a canon expansion proposal arrives, the first question is "which
of §1's three outcomes does this fit?" Answers shape the structure of
the resulting canon:

- **Build** → new ADR + new canon doc + new schema if applicable.
- **Declare and consume** → new entry in `adapter-registry.yaml` or
  `modernization-registry.yaml`; no other canon required.
- **Declare and structure** → new entry in a registry **plus** a MOD
  spec **plus** an executable canon (YAML) under
  [`canon/data/`](data/) **plus** a JSON Schema under
  [`schemas/`](../schemas/).

The dual-axis taxonomy from UIAO_003 §4.2–§4.7 sits orthogonally across
these outcomes — it classifies the adapter, while §1 classifies the
build-vs-buy posture.

### 4.4 For external integration claims

UIAO documentation and customer-facing material that claim "Microsoft
provides X" or "UIAO provides Y" SHALL ground those claims in §2 or
§3 of this doctrine. Disagreement with the doctrine is resolved by
ADR; not by ad-hoc revision of the claim text.

## 5. Open Items

The following are known doctrine gaps that this v1.0 does not yet
close. Each is a candidate for a v1.1 expansion or a sibling canon doc.

| # | Topic | Why deferred |
|---|---|---|
| 1 | The relationship between this doctrine and UIAO_002 (SCuBA Technical Specification) | UIAO_002 covers the M365 SCuBA conformance plane; UIAO_009 covers the broader Microsoft stack. Need a §6 in this doc explaining the boundary. |
| 2 | Network-plane gaps (Palo Alto / Infoblox / BlueCat — currently declared but not gap-classified per §3) | The four §3 gaps are all cross-plane joins between MS surfaces. Network-plane gaps may need a fifth category. |
| 3 | The non-Microsoft baseline (where AWS, GCP, on-prem fit relative to this doctrine) | UIAO is GCC-Moderate / M365-aligned per ADR-028; multi-cloud doctrine is out of scope until that boundary is revisited. |
| 4 | Sequencing of the four gaps for a new agency engagement | Doctrine does not prescribe order; a sibling implementation guide could. |

## 6. Cross-References

- Rationale source: [ADR-049](adr/adr-049-microsoft-adapter-coverage-expansion.md) §Decision 2.
- Adjacent canon: [UIAO-SSOT.md](UIAO-SSOT.md) (overall doctrinal frame), [UIAO_003](UIAO_003_Adapter_Segmentation_Overview_v1.0.md) (dual-axis adapter taxonomy), [UIAO_007](UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md) (the OrgPath transformation guide), [UIAO_135](UIAO_135_identity-directory-transformation-inventory.md) (transformation coverage assessment), [UIAO_136](UIAO_136_priority1-transformation-project-plans.md) (priority-1 transformation project plans).
- Drift engine: [ADR-040](adr/adr-040-drift-engine.md), [`canon/data/orgpath/drift-engine-config.yaml`](data/orgpath/drift-engine-config.yaml).
- Adapter registries: [`canon/adapter-registry.yaml`](adapter-registry.yaml) (conformance), [`canon/modernization-registry.yaml`](modernization-registry.yaml) (modernization).
