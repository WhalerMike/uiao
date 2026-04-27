---
title: "FedRAMP GCC-Moderate — ThousandEyes covers one of seven ZTMM pillars, not the gap"
finding_id: "FINDING-002"
status: Open-Procurement-Guidance
severity: P3
created_at: "2026-04-27"
updated_at: "2026-04-27"
owner: "Michael Stratton"
related_canon: ["UIAO_003", "UIAO_109", "UIAO_113", "UIAO_131"]
related_findings: ["FINDING-001"]
related_adrs: ["ADR-047"]
supersedes: []
superseded_by: []
---

# FedRAMP GCC-Moderate — ThousandEyes covers one of seven ZTMM pillars, not the gap

## 1. Constraint

Cisco **ThousandEyes** is being raised in agency procurement
conversations as a workaround for the GCC-Moderate telemetry gaps
documented in FINDING-001 and the broader gap matrix
(`src/uiao/canon/data/gcc-moderate-telemetry-gaps.yaml`). This finding
records the position that ThousandEyes is **a legitimate but narrow
answer** — it materially closes the **Networks pillar** of the CISA Zero
Trust Maturity Model and the BGP / DNS / MITM detection chain, and it
addresses **none of the Identity, Devices, Data, Applications & Workloads,
or audit-retention pillars** that drive the assessment's headline
findings.

Characterizing ThousandEyes as a general workaround for the missing
telemetry overstates its coverage by roughly an order of magnitude — it
closes approximately one of the seven ZTMM pillars.

## 2. Evidence

### Source memo

`inbox/New_FedRAMP_Boundary/GCC-Moderate_Boundary_and_ThousandEyes_Assessment_External_with_images.docx`,
Section 2 ("Does ThousandEyes provide a real way around the missing
telemetry?") and Figure 2 ("ThousandEyes pillar coverage").

### Coverage matrix

| Telemetry gap area | ThousandEyes substitutes? |
|---|---|
| INR real-time path metrics (latency / jitter / packet loss to M365 front doors) | **Yes** — closest thing to a real substitute. Synthetic, not per-user-session, but genuine network measurement from Cloud + Enterprise + Endpoint Agents. |
| MITM / BGP hijack / DNS manipulation | **Yes** — strong fit. BGP route monitoring, DNS tests, and certificate-validation tests are flagship ThousandEyes use cases. |
| Teams CQD network-quality dimension | **Partial.** Microsoft Teams test type gives synthetic call-quality baselines. Does not recover the EUII (BSSID, public IP, subnet) that makes up the forensic-attribution gap. |
| M365 service availability / performance | **Yes.** Endpoint and HTTP server tests cover this well. |
| Adoption Score (communication, collaboration, mobility patterns) | **No.** User-behavior signals; not a network problem. |
| Endpoint Analytics Advanced (boot time, app crashes, AppCrashCount, AvgProcessorUsage, performance outliers) | **No.** The Endpoint Agent collects local network telemetry, not Windows kernel or performance counters. |
| Entra Identity Protection ML signals (impossible travel, atypical IP, leaked credentials) | **No.** Identity-data problem. |
| Continuous Access Evaluation sub-second revocation | **No.** Token-state problem. |
| Intune EPM, app-protection, Windows Update for Business trend telemetry | **No.** Endpoint policy and state events. |
| DLP behavioral / sensitivity-label / Copilot telemetry | **No.** Content and policy-event problem. |
| MailItemsAccessed, SearchQueryInitiated, unified audit gaps | **No.** SaaS audit events. |

## 3. Capability gap

### What ThousandEyes meaningfully addresses

1. **Networks pillar** — synthetic latency / jitter / packet-loss to
   Microsoft front doors; per-ISP and per-peering path performance.
2. **BGP / DNS / MITM detection chain** — BGP route monitoring, DNS
   tests, certificate-validation tests.
3. **M365 service availability** — endpoint and HTTP server tests.

### What ThousandEyes does **not** address

- Identity (no replacement for Entra Identity Protection ML; no CAE
  substitute).
- Devices (no Endpoint Analytics Advanced equivalent; no Intune
  behavioral analytics).
- Data (no DLP behavioral context; no sensitivity-label analytics).
- Applications & Workloads (no Office Optional diagnostic; no Copilot /
  AI telemetry).
- Visibility & Analytics (cross-cutting; ThousandEyes contributes only
  the Networks slice).
- Automation & Orchestration (no policy-event signal source).

## 4. Two integrity caveats before any procurement conversation

### 4.1 FedRAMP authorization of the specific SKU

ThousandEyes' FedRAMP authorization status **must be verified on the
FedRAMP Marketplace at the Moderate baseline for the specific SKU being
purchased**. If the SKU is not Moderate-authorized, ingesting its data
into the agency's boundary creates an SC-7 and supply-chain inheritance
question that defeats the purpose. This finding does not cite a current
Marketplace status; doing so without verification would be unsound.

### 4.2 Cloud Agent egress treatment

Cloud Agent measurements traverse the public Internet from non-agency
endpoints. Synthetic-probe metadata (source IPs, paths, timing) should be
treated as **cross-boundary egress for assessment purposes**, not as a
free signal.

## 5. Cost dimensions (descending by practical impact)

| Dimension | Estimate / note |
|---|---|
| Opportunity cost (highest) | Spending the next budget cycle deploying ThousandEyes can create the appearance of closing the telemetry gap while the Identity, Devices, and Data pillars — where the most consequential compound-attack risks actually live — go unaddressed. |
| ATO scope and authorization | 3–6 months of governance work (SSP insertion, boundary-diagram updates, 3PAO impact analysis) before ingest can begin. |
| Licensing | Quote-based; no public list price. Cloud Agents, Enterprise Agents (per agent or appliance), Endpoint Agents (per seat), BGP Monitors. Treat as a meaningful annual line item, not a rounding error. Require a fresh GSA / SEWP quote. |
| Deployment and integration | 4–8 weeks of engineering for a multi-site agency (Enterprise Agent per site, Endpoint Agent push via Intune, OpenTelemetry / API into Sentinel). |
| SOC operating load | 0.25–0.5 FTE on an ongoing basis to triage, baseline, and suppress synthetic-monitoring alert volume. |

## 6. Proposed disposition

### Recommended

Adopt ThousandEyes only as **a Networks-pillar component of a broader
compensating-architecture stack** (per the source memo §13.2), with the
following preconditions:

1. **FedRAMP Marketplace verification** of the specific SKU at the
   Moderate baseline before ingest is permitted.
2. **Cloud Agent egress** treated as cross-boundary in the SSP,
   not as a free signal.
3. **Procurement framing** explicitly names ThousandEyes as Networks-only
   and links to the gap matrix so reviewers see what it does and does not
   cover.

### Not recommended

Adoption as a "general telemetry workaround" in lieu of the agency-side
analytics build (Sentinel, custom risk models, local long-term retention
of CQD exports, OS-level logs supplementing Intune). That mis-spends
against the actual risk surface and leaves the Identity / Devices / Data
gaps fully open.

See **ADR-047** for the canonical proposal.

## 7. Related

- **FINDING-001** — INR unavailable in GCC-Moderate (the specific
  Networks-pillar gap that ThousandEyes can substitute for).
- **ADR-047** — ThousandEyes Networks-pillar conditional adoption (the
  decision-record realization of this finding's recommendation).
- **Canon spec**:
  `src/uiao/canon/compliance/reference/gcc-moderate-boundary-assessment/`
- **Gap matrix**: `src/uiao/canon/data/gcc-moderate-telemetry-gaps.yaml`
  (rows that ThousandEyes addresses are tagged in the
  `network_path_substitute` set in ADR-047).

## Status tracking

| Date | Status | Note |
|---|---|---|
| 2026-04-27 | Open-Procurement-Guidance | Initial landing |

This table is append-only.
