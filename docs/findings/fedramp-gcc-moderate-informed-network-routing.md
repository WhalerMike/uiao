---
title: "FedRAMP GCC-Moderate — Microsoft 365 Informed Network Routing unavailable"
finding_id: "FINDING-001"
status: Awaiting-External-Remediation
severity: P2
created_at: "2026-04-17"
updated_at: "2026-04-17"
owner: "Michael Stratton"
related_canon: ["UIAO_003", "UIAO_109", "UIAO_113", "UIAO_131"]
related_ksi: ["KSI-SC-07", "KSI-SI-04"]
supersedes: []
superseded_by: []
---

# FedRAMP GCC-Moderate — Microsoft 365 Informed Network Routing unavailable

## 1. Constraint

Microsoft 365 **Informed Network Routing** (INR) — the
bi-directional data-sharing channel between Microsoft and
customer SD-WAN solutions that enables Microsoft to share
quality feedback on Microsoft 365 application traffic so SD-WAN
can make path-selection decisions — is **not available** to
tenants in Microsoft 365 GCC Moderate, GCC High, DoD, Germany,
or China clouds. Availability is restricted to the WW
Commercial cloud.

This is a Microsoft-stated restriction documented in Microsoft
Learn and announced in the Microsoft Community Hub. The
mechanism of the restriction (whether imposed by FedRAMP
boundary definitions, by Microsoft engineering sequencing, or
by other constraints) is **not stated** in the public
documentation.

## 2. Evidence

### Primary source (Microsoft Learn)

- **[Microsoft 365 informed network routing — Microsoft Learn](https://learn.microsoft.com/en-us/microsoft-365/enterprise/office-365-network-mac-perf-cpe?view=o365-worldwide)**
  Accessed 2026-04-17. Direct quote:
  > "Microsoft 365 informed network routing supports tenants in
  > WW Commercial cloud but not the GCC Moderate, GCC High, DoD,
  > Germany, or China clouds."

### Supporting sources

- **[Announcing general availability of Microsoft 365 informed network routing — Microsoft Community Hub](https://techcommunity.microsoft.com/discussions/deploymentnetworking/announcing-general-availability-of-microsoft-365-informed-network-routing/3021309)**
  GA announcement describing INR's bi-directional data-sharing model
  for SD-WAN path optimization.
- **[Announcing Microsoft 365 informed network routing preview — Microsoft Community Hub](https://techcommunity.microsoft.com/discussions/deploymentnetworking/announcing-microsoft-365-informed-network-routing-preview/2041972)**
  Original preview announcement, context on the feature's
  operational model.
- **[Microsoft Teams call flows — Microsoft Learn](https://learn.microsoft.com/en-us/microsoftteams/microsoft-teams-online-call-flows)**
  Background on media-path behavior in GCC tenants where INR is not
  present.

### Terminology note

The pre-UIAO narrative (in particular the *FedRAMP Boundaries*
book, Article 01 §2) referred to this feature as **"Intelligent
Network Routing."** Microsoft's actual product name is **"Informed
Network Routing"** (same INR acronym, different adjective). This
finding uses the Microsoft term throughout for citation alignment.

## 3. Capability gap

### What UIAO cannot do because of this constraint

1. **Consume Microsoft-sourced M365 path-quality telemetry** in a
   GCC-Moderate agency deployment. The INR feedback channel does
   not exist for those tenants, so UIAO adapters that would
   forward M365 path quality to the drift engine
   ([UIAO_110](https://github.com/WhalerMike/uiao/blob/main/src/uiao/canon/specs/drift.md))
   have no upstream input.

2. **Feed Microsoft-authenticated M365 traffic signals into the
   evidence graph**
   ([UIAO_113](https://github.com/WhalerMike/uiao/blob/main/src/uiao/canon/specs/graph-schema.md))
   as first-class evidence objects sourced from INR. The signals
   are absent at the tenant boundary.

3. **Produce commercial-parity drift findings** for M365 path
   degradation. Commercial tenants with INR get a quality feedback
   stream; GCC-Moderate tenants do not. UIAO's drift detector
   cannot emit a DRIFT-SEMANTIC finding on M365 path quality
   because the semantic signal isn't available.

### What this does NOT affect

- UIAO's adapter registry and test framework ([UIAO_131
  §3.1](https://github.com/WhalerMike/uiao/blob/main/src/uiao/canon/specs/adapter-test-strategy.md))
  — tier-1 live commercial-tenant tests can still be run against
  the M365 Developer Program (WW Commercial), which has INR
  available. Tier-2 contract fixtures can record INR's
  unavailability in GCC-Moderate as a fixture and verify the
  adapter handles it gracefully.
- Non-M365 telemetry — other adapter mission-classes (identity,
  policy, enforcement) are unaffected by this specific constraint.
- OSCAL evidence generation — SSP / SAR / POA&M assembly is
  independent of INR.

## 4. Proposed remedy

Split between internal (inside UIAO's scope) and external
(requires Microsoft or FedRAMP action).

### Internal remedy (already in scope)

1. **Tier-2 fixture encoding the INR unavailability** under
   `tests/fixtures/contract/m365/` that records the feature
   as `unavailable` for GCC-Moderate deployments and asserts the
   M365 adapter does not attempt to call INR endpoints when
   configured for a GCC-Moderate tenant. This follows [UIAO_131
   §7](https://github.com/WhalerMike/uiao/blob/main/src/uiao/canon/specs/adapter-test-strategy.md)
   (relationship to the FedRAMP-INR finding).
2. **Equivalent-capability adapter** in UIAO's telemetry control
   plane: an agency-side path-quality collector that pulls signals
   from the SD-WAN device (rather than Microsoft) and feeds them
   into the evidence graph. This gives GCC-Moderate agencies a
   UIAO-native substitute while INR remains unavailable. Scope for
   a future adapter; not yet in the registry.
3. **Documentation** on the Substrate Status page naming this
   capability gap explicitly so agency operators understand that
   M365 path-quality drift detection in their deployment sources
   from agency SD-WAN telemetry, not from Microsoft's INR feed.

### External remedy (outside UIAO's scope)

1. **Microsoft** deploys INR to GCC-Moderate with any telemetry
   envelope acceptable under the Moderate boundary. Requires
   Microsoft engineering investment + FedRAMP authorization
   adjustment if applicable.
2. **FedRAMP** authorization package for GCC-Moderate permits the
   specific telemetry signals INR requires, with documented PIAs
   for any PII/location data that flows through the feedback
   channel.

The external remedy is not a prerequisite for UIAO to deliver
value; the internal remedy (option 2 above) is the canonical
substrate response and proceeds independently.

## 5. Ownership trail

- **2026-04-17** — Constraint identified during review of pre-UIAO
  narrative content (Application-Aware Networking book, Article 01
  §2). The narrative framed the constraint as *"FedRAMP Moderate
  boundaries prohibited cloud service providers from bringing the
  same telemetry pipelines … into GCC-Moderate that already
  existed in the Commercial cloud."*
- **2026-04-17** — Independent verification via Microsoft Learn
  (cited in §2). Confirmed the unavailability fact; **did not
  confirm** the narrative's claim about the *cause*. Microsoft's
  public docs state unavailability without naming FedRAMP as the
  mechanism. This finding reflects the corrected framing.
- **Prior to substrate formalization** — The constraint was
  escalated internally. Division Director and Branch Chief
  responded *"not our responsibility"*; the agency's current CIO
  has stated the operating principle: **"Everyone owns all
  problems they identify."** That principle is the substrate-level
  ownership basis for documenting this finding here rather than
  withdrawing it.
- **2026-04-17** — Finding lands under `docs/findings/` with
  status **Awaiting-External-Remediation**. Michael Stratton
  owns the finding. Internal remedies §4 are in scope for UIAO
  and proceed on the substrate roadmap; external remedies stay
  tracked here until Microsoft or FedRAMP action closes them.

## 6. Related

- [ADR-030 §5.2](https://github.com/WhalerMike/uiao/blob/main/src/uiao/canon/adr/adr-030-pre-uiao-terminology-reconciliation.md)
  — established the governance-findings artifact class that this
  document instantiates.
- [UIAO_131 §7](https://github.com/WhalerMike/uiao/blob/main/src/uiao/canon/specs/adapter-test-strategy.md)
  — Adapter Test Strategy explicitly anticipates this finding as
  a tier-2 fixture class for M365 adapter tests.
- [Application-Aware Networking book](../series/application-aware-networking-book/index.qmd)
  — particularly Article 01 (The Blindfold Problem) and Article 06
  (The Telemetry Problem) — narrative-layer treatment of the
  GCC-Moderate telemetry gap, now corrected to cite Microsoft's
  "Informed" product name.

## Status tracking

| Date | Status | Note |
|---|---|---|
| 2026-04-17 | Awaiting-External-Remediation | Initial landing |

This table is append-only. Closure of the finding (Resolved or
Withdrawn) moves the status and adds a row; the prior rows
remain for audit.
