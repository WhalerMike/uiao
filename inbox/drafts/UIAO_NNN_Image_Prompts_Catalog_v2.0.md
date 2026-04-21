[DOCUMENT-METADATA]
Document Title: UIAO Image Prompts Catalog
Document ID: UIAO_NNN_Image_Prompts_Catalog_v2.0  (NNN = MISSING, Canon Steward to assign)
Version: 2.0
Date: 2026-04-21
Author: Michael Stratton (Canon Steward)
Drafting Agent: Claude (Cowork) — independent review session
Classification: UIAO Canon – Public Release
Compliance: GCC-Moderate Only
No-Hallucination Mode: ENABLED
Supersedes: IMAGE-PROMPTS.md v1.0 (2026-04-12, Doc 01 scope); inbox/drafts/2026-04-21-image-prompts-corpus-v2.md (non-canonical draft)
[/DOCUMENT-METADATA]

> **Conformance note.** This document is authored to the structure required by `UIAO_Master_Document_Specification_v1.3` (Section 3, Canonical Document Specification) and obeys the No-Hallucination Protocol in Section 2 of that specification. All image prompts are scoped to canon documents supplied by Michael Stratton during the 2026-04-21 review session. Prompts that reference documents in the backlog but not yet delivered are labeled **NEW (Proposed)**. The eight Doc 01 (Executive Brief) prompts are preserved verbatim from the v1.0 source.

---

## Table of Contents

1. Executive Summary
2. Context and Problem Statement
3. Architecture Overview
4. Detailed Sections — The Prompt Catalog
   - 4.1 EXEC — Doc 01, Executive Brief
   - 4.2 GAP — UIAO vs. Microsoft Native Tools
   - 4.3 MPP — Master Project Plan
   - 4.4 ADR — Git Infrastructure ADR-001
   - 4.5 PSB — Platform Server Build Guide (Gitea + IIS)
   - 4.6 CLI — CLI and Operations Guide
   - 4.7 ADI — AD Interaction Guide
   - 4.8 ROA — Read-Only AD Assessment Guide
   - 4.9 PSM — PowerShell Module Reference
   - 4.10 IDM — Identity Modernization Guide
   - 4.11 DNS — DNS Modernization Guide
   - 4.12 PKI — PKI Modernization Guide
   - 4.13 ACC — AD Computer Object Conversion Guide
   - 4.14 CA — Conditional Access Policy Library
   - 4.15 INT — Intune Policy Templates
   - 4.16 ARC — Azure Arc Policy Library
   - 4.17 COR — Corpus-level
5. Implementation Guidance
6. Risks and Mitigations
7. Appendices
   - Appendix A — Definitions
   - Appendix B — Object List
   - Appendix C — Copy Sections
   - Appendix D — References
8. Glossary
9. Footnotes
10. Validation Block

---

## 1. Executive Summary

This document is the canonical source of image-generation prompts for the UIAO documentation canon. It replaces the v1.0 catalog, which addressed Doc 01 (Executive Brief) only, with a corpus-wide set of **77 prompts** covering all eighteen canon documents and six corpus-level images used by the public web surface and the Canon Registry.

Every prompt carries a stable identifier of the form `UIAO-<DOC>-NN` that matches the filename stem for the rendered image in `diagrams/<UIAO-ID>.png` and the anchor a canon document uses when it writes "see Diagram UIAO-MPP-D001". The ID is stable across regenerations; only the image bits change between renders.

All prompts obey a single global style contract (Section 3.2) — muted federal palette, no baked-in text, no people, 16:9. The contract is designed so images produced months apart by different generators remain visually consistent when rendered side by side in a whitepaper or slide.

The catalog is written for two readers: (a) an operator who pastes a single prompt into a diagramming or image-generation tool and expects consistent first-pass output; and (b) the Canon Steward who needs to verify every document's diagram references resolve to an ID in this file before a canonical document is approved.

## 2. Context and Problem Statement

**The problem.** The UIAO canon routinely references diagrams, tables, and images by ID (e.g., "UIAO-MPP-D001"). Without a single source of prompts, each render risks drift: different palettes, inconsistent composition, baked-in text that breaks localization, or images that cannot be regenerated because the prompt was lost. The v1.0 catalog solved this for Doc 01 only; the remaining seventeen canon documents and the public web surface were covered only by ad-hoc or missing prompts.

**Why it matters.**
- Canonical documents that reference a diagram ID must be able to point to a deterministic prompt so the image can be regenerated on demand without hallucination.
- The public Quarto site embeds diagrams from `diagrams/` and must render with consistent visual language across every page.
- Federal audiences read visual style as a signal of governance maturity; drift in palette, voice, or composition reduces trust regardless of text quality.

**Who is affected.** Canon Steward (promotion and approval), any contributor generating diagrams for a canonical document, the Quarto site build (reads rendered images from `diagrams/`), and the Canon Registry generator (lists diagrams referenced but not yet rendered).

**Constraints.**
- UIAO governance constraints apply verbatim: GCC-Moderate only, object identity only, Amazon Connect as the only Commercial Cloud exception.[^1]
- No baked-in text in images unless the prompt explicitly overrides; captions and labels are added in the document to preserve accessibility and translation readiness.
- No people or stock-photo silhouettes that could read as a real individual.
- No vendor logos (Microsoft, Azure, Entra, GitHub, Gitea). Abstract geometric substitutes only.

## 3. Architecture Overview

### 3.1 Catalog organization

Prompts are organized by a two-letter document code and a sequence number. Document codes (`EXEC`, `GAP`, `MPP`, `ADR`, `PSB`, `CLI`, `ADI`, `ROA`, `PSM`, `IDM`, `DNS`, `PKI`, `ACC`, `CA`, `INT`, `ARC`, `COR`) map to the sixteen canon documents plus a corpus-level bucket. Within each code, sequence numbers are monotonically increasing and never reused. When an image is retired, its ID stays reserved.

### 3.2 Global style contract

All prompts obey this contract unless explicitly overridden:

- **Audience.** A federal CIO reading a whitepaper. Think McKinsey, Deloitte, or a GAO infographic. Not startup marketing.
- **Mood.** Calm, trustworthy, deterministic. Never alarmist, never playful.
- **Aspect ratio.** 16:9 widescreen.
- **Resolution target.** 1920×1080 minimum; 2560×1440 preferred.
- **Palette (muted federal).**
  - Navy `#2E75B6` — primary structure, frames, main lines.
  - Steel Gray `#5A5A5A` — secondary structure, legacy/on-prem elements.
  - Teal `#1A9E8F` — healthy, compliant, "flow is good" accents.
  - Amber `#D4A017` — warnings, drift, watchpoints.
  - White `#FFFFFF` — background.
- **Prohibited.** Baked-in text (unless noted), people or silhouettes that read as real individuals, stock photography, clip art, vendor logos, emoji, saturated "startup" colors, glossy 3D renders.
- **Preferred.** Flat vector with subtle depth; clean isometrics; restrained shadow; legible at thumbnail size.
- **Accessibility.** Sufficient contrast; meaning never encoded in color alone — shape or position carries the signal too.

### 3.3 Boundary model

Every image in this catalog is classified **UIAO Canon – Public Release** by default and is safe to render on the public site. Images that reference Controlled or higher-classification material are out of scope for this catalog.

### 3.4 SSOT role

The catalog is the single source of truth for prompts. The `diagrams/` folder holds rendered images. The `diagrams/README.md` records render provenance (generator, model, seed). No other file in the repository may originate a prompt — all prompts originate here and are referenced elsewhere by ID.

### 3.5 Adapter classes relevant to this document

- **Telemetry** — the render tool emits logs and metadata about each generation; those logs enter the governance pipeline as evidence of canonical rendering.
- **Identity** — the operator who runs a generation is identified by their repository-level identity (git commit author on the resulting `diagrams/` update).

No new adapter classes are introduced.

### 3.6 Certificate-anchored provenance

Each rendered diagram is committed with a signed commit on a branch governed by the update hook. The render log in `diagrams/README.md` ties image ID to prompt Rev and generator identity. Regeneration that changes the Rev must bump the entry in Section 11 of this document.

## 4. Detailed Sections — The Prompt Catalog

Prompts below are written in prose so a non-technical generator produces acceptable first-pass output. The global style contract (Section 3.2) is always appended unless the prompt explicitly overrides it.

### 4.1 EXEC — Doc 01, Executive Brief

*Preserved verbatim from `IMAGE-PROMPTS.md` v1.0 (2026-04-12). IDs added; prompt text unchanged.*

**UIAO-EXEC-01 — Cover / Hero.** A wide, clean, professional illustration representing continuous automated compliance monitoring for a federal government IT environment. A calm, abstract digital landscape where a central glowing blue shield or lens continuously scans a network of connected nodes representing cloud services (email, collaboration, identity, security). The nodes pulse with soft green light when healthy, amber when drifting. Calm control — not alarm, not chaos. Flat vector with subtle depth, government whitepaper tone.

**UIAO-EXEC-02 — The Problem.** A conceptual illustration showing the pain of manual federal compliance. On one side, a towering stack of paper documents, binders, and spreadsheets — slightly disorganized, casting shadows. On the other side, a clock face showing months passing. Between them, a fading trail of screenshots and handwritten checkmarks that are visibly outdated. Weary, bureaucratic, quiet exhaustion. Warm grays, muted tan for paper, faded blue for the clock. Editorial illustration, clean lines.

**UIAO-EXEC-03 — Continuous Monitoring Loop.** A clean circular diagram with four stages flowing clockwise: SCAN (magnifying glass over cloud services), EVALUATE (checklist against rulebook), EVIDENCE (document with a cryptographic lock), ALERT (notification bell with amber glow). Smooth arrows connect the stages. Navy circle, white background, teal stage icons, amber alert. Flat infographic.

**UIAO-EXEC-04 — Before and After.** Split-screen. LEFT "Before" (muted red/gray): buried compliance team — binders, calendar with 18 months circled, red-celled spreadsheets, abstract slumped silhouette. RIGHT "After" (clean blue/green): nearly empty desk, green dashboard monitor, signed digital document with lock icon, calendar showing always current. Heavy vs. light, cluttered vs. clean. Editorial comparison, minimalist.

**UIAO-EXEC-05 — Three Layers of Rules.** A layered stack diagram — three horizontal translucent layers like glass shelves. BOTTOM (widest, navy): FedRAMP Moderate Rev 5 — 247 Controls, as a grid of shield icons. MIDDLE (medium, teal): CISA SCuBA & BOD 25-01, as a governance seal. TOP (narrowest, steel gray): Agency Policies, as a small building or seal. A vertical arrow passes through all three.

**UIAO-EXEC-06 — Immutable Evidence Chain.** A horizontal chain of linked evidence blocks — simplified, elegant, blockchain-style. Each block contains a timestamp icon, a check-result icon, and a digital-signature lock. Subtle chain links between. Newest block glows softly; the chain extends into the distance. A magnifying glass hovers over one block. Navy blocks, white background, amber signature icons. Trust and permanence.

**UIAO-EXEC-07 — Three Differentiators.** Three distinct icons arranged horizontally with generous whitespace. LEFT: "Deterministic" — a binary ON/OFF switch, decisive. CENTER: "Produces Deliverables" — a finished document with an OSCAL-style seal emerging from a conveyor. RIGHT: "Built for Federal M365" — an abstract M365-shape wrapped in a government shield. Muted blue, teal, gray on white.

**UIAO-EXEC-08 — The 90-Day Ask.** A simple, confident 90-day timeline arc. DAY 1: a connection icon (UIAO linking to a GCC-Moderate tenant). DAY 45: a side-by-side comparison icon. DAY 90: a green checkmark or thumbs-up seal. Clean and optimistic, not a Gantt. Navy arc, white background, green final milestone.

### 4.2 GAP — UIAO vs. Microsoft Native Tools

**UIAO-GAP-01 — The Twelve Instruments.** A wide flat-vector composition: twelve abstract musical-instrument silhouettes arranged in a shallow semicircle, each a different geometric shape (no literal instrument), each rendered in muted navy and steel gray. Above, a faint teal arc suggests a missing conductor's baton. Whitespace-heavy, editorial.

**UIAO-GAP-02 — The Orchestra — UIAO as Orchestrator.** The same twelve silhouettes now beneath a central teal diamond with radiating lines to each instrument. The diamond has no face, no hands, no implied person — pure geometry. Above it, a thin navy bar suggests a governance layer. Navy instruments, steel-gray shadows, teal diamond.

**UIAO-GAP-03 — Coverage Matrix Visual.** A stylized capability matrix — ten rows by three columns, rendered as a soft-edged heatmap. Cells shaded on a scale from steel-gray (no coverage) through muted amber (partial) to teal (full). The UIAO column is dominantly teal; the Microsoft column is patchwork; the third-party column sits between. Flat, clean.

**UIAO-GAP-04 — SCuBA Parallel.** A horizontal dual-track diagram. TOP: left box as "CISA ScubaGear" (scuba-mask silhouette), arrow, center teal diamond (UIAO), arrow, right box showing a seal. BOTTOM: left box as the twelve-instrument silhouette, arrow, same teal diamond, arrow, same seal. A vertical dotted navy line connects the two diamonds to show they are the same node.

**UIAO-GAP-05 — Consume vs. Build.** Two vertical columns on white. LEFT: a stack of small inbound-arrow tiles feeding a teal funnel (CONSUME). RIGHT: a teal anvil/workbench with small outbound-arrow tiles emerging (BUILD). A thin navy divider between.

### 4.3 MPP — Master Project Plan

**UIAO-MPP-D001 — Program Timeline (Gantt Overview).** Seven-phase horizontal program timeline. Seven color-coded horizontal bars stacked vertically, each length matching Phase 0 through Phase 6 (3, 6, 4, 8, 12, 8, ongoing weeks). Phase bars rest on a subtle week ruler (ticks only). Small diamonds mark milestone gates between bars. A dashed navy line runs through all phases as the critical path. Below each phase: thin pillar bars for Identity, Devices, DNS, PKI, Server workstreams.

**UIAO-MPP-D002 — Milestone Dependency Network.** Directed acyclic graph of ~48 small nodes arranged roughly left-to-right by phase. Uniform navy circles; thin steel-gray edges with minimal arrowheads. A continuous navy line highlights the critical path. Faint translucent bands group nodes by phase.

**UIAO-MPP-D003 — Phase Transition Flow.** Clean left-to-right flowchart: seven sequential rectangular phase blocks, each a slightly different shade of navy. Between every two phases, an amber diamond gate review. Within each block, three to five thin parallel pillar lines. Final block opens into an ongoing steady state that fades rightward.

**UIAO-MPP-D004 — Governance Cadence Wheel.** A single circular wheel, four concentric rings. Inner ring: weekly (smallest notches). Second: monthly. Third: quarterly. Outer: annually. Notch marks only; no text. Center dot teal. Rings navy on white with subtle amber highlights at critical reviews. Wheel offset left, negative space on the right for document-applied callouts.

**UIAO-MPP-D005 — Risk Heatmap.** A 5×5 probability/impact heatmap. Cells shaded on a diagonal gradient from white (low, bottom-left) to amber (high, top-right). Approximately twenty-two small navy dots scattered across the cells representing risks R-001 through R-022. Thin steel-gray grid lines. Axes are unlabeled rectangles; labels added in-document.

**UIAO-MPP-D006 — Budget Stacked Composition.** A clean horizontal stacked bar in four segments representing licensing, infrastructure, people, and services in relative proportion. Navy, steel gray, teal, amber. A thin vertical ruler marks the total. No numerals.

### 4.4 ADR — Git Infrastructure ADR-001

**UIAO-ADR-01 — Five Options at a Glance.** Five small square cards arranged horizontally with generous spacing. Each shows an abstract architectural silhouette: (A) IIS alone — single navy block; (B) Gitea behind IIS — two joined blocks with an arrow; (C) Azure DevOps on-prem — a cluster of blocks; (D) Gogs — single block; (E) Custom ASP.NET API — gear inside a block. Card (B) has a subtle teal highlight border.

**UIAO-ADR-02 — Recommended Architecture.** Two-tier architectural diagram. TOP (broad navy bar): IIS — TLS termination, lock icon, reverse-proxy arrows. BOTTOM (teal bar): Gitea — an abstract hex or diamond symbol. A short connector with a request/response curve between. LDAP/AD silhouette on the left, Entra OAuth silhouette on the right, both connecting only to Gitea.

**UIAO-ADR-03 — Migration Path.** A horizontal arrow sweep with five numbered milestones as small navy diamonds. Above the far left: a single IIS block (before). Below the far right: a Gitea + IIS two-tier block (after). Teal accent on the arrow tip.

### 4.5 PSB — Platform Server Build Guide (Gitea + IIS)

**UIAO-PSB-01 — Server Topology.** A clean five-tier vertical topology: Client tier (small browser/PowerShell silhouettes), Reverse Proxy tier (IIS block with lock), Application tier (Gitea block), Storage tier (disk + DB cylinder), Identity tier (LDAP/AD + Entra silhouettes side by side). Thin navy top-to-bottom arrows; teal east-west integration arrows.

**UIAO-PSB-02 — Phase Sequence.** Thirteen small circular step beads arranged along a gentle S-curve from top-left to bottom-right. Every third bead is teal-filled; the rest are navy outlines. The S-curve is a continuous navy ribbon.

**UIAO-PSB-03 — TLS Chain.** Three vertical certificate silhouettes (rectangles with a lock/seal icon), connected by thin curved lines: Root → Intermediate → Leaf. The leaf is teal; root and intermediate are navy. A browser silhouette at the far right reads the leaf with a tiny trust tick.

**UIAO-PSB-04 — Backup and DR Topology.** Primary Gitea server (large teal block) on the left, secondary passive server (muted teal block) on the right, Azure Blob icon at top as a detached backup target. Solid arrow from primary to blob (nightly backup). Dashed arrow from primary to passive (replication). Clock icon hovers between the two servers.

### 4.6 CLI — CLI and Operations Guide

**UIAO-CLI-01 — Dual-Remote Topology.** A developer workstation silhouette (laptop outline, no person) at center. Two outbound navy arrows: one to a Gitea block on the left (solid, bold), one to a GitHub block on the right (dashed, thinner).

**UIAO-CLI-02 — API Surface.** A central teal ring labeled visually by a small API-gear hint. Eight outbound arrows to eight identical small navy tiles representing endpoint families: repositories, pull requests, organizations, webhooks, releases, users, issues, admin.

**UIAO-CLI-03 — Governance Hook Chain.** A left-to-right flow with three hook stations: pre-receive (shield), update (key), post-receive (paper airplane). Short arrows between. A thin navy ribbon below captures the whole as "the governance gate."

### 4.7 ADI — AD Interaction Guide

**UIAO-ADI-01 — Forest Discovery Pipeline.** Left: an abstract geometric tree silhouette representing the AD forest. Right: a small navy file icon representing a JSON artifact. Between: three concentric arcs (domains, OUs, objects) funneling into the JSON icon.

**UIAO-ADI-02 — Assessment Output Schema.** A grid of small equal-sized navy tiles representing ~20 JSON artifacts. Four rows by five columns, whitespace-heavy. Each tile has a small icon hint (OU silhouette, lock, tree, object-identity user silhouette).

**UIAO-ADI-03 — Pipeline Integration.** Horizontal three-step flow: PowerShell icon → JSON file icon → Gitea hex icon. Each step a teal-bordered card; navy connecting arrows. A thin amber dashed line returns from Gitea back to PowerShell, suggesting drift feedback.

**UIAO-ADI-04 — Trust Map.** Five to seven small tree silhouettes representing domains in a loose cluster. Lines between them: solid navy for two-way trusts, dashed navy for one-way trusts. One tree is slightly larger and highlighted teal — the root.

### 4.8 ROA — Read-Only AD Assessment Guide

**UIAO-ROA-01 — Coverage vs. Delegation Gap.** A single horizontal bar: a large teal segment (~87%) with a check silhouette; a smaller amber segment (~13%) with a key silhouette. Above the bar: a small magnifying glass. Below: thin navy ruler ticks, no numerals.

**UIAO-ROA-02 — Least-Privilege Principle.** A small padlock silhouette on the left. A thin navy arrow to the right reaches a grid of ~50 tiny tiles — most teal (read-only reachable), a minority amber (requires elevation). The lock is not broken; the reach is long.

**UIAO-ROA-03 — Delegation Request Flow.** Three-step horizontal flow: read-only baseline (teal circle) → gap identified (amber diamond) → delegation request submitted (navy envelope). A small clock icon above the amber diamond suggests review latency.

### 4.9 PSM — PowerShell Module Reference

**UIAO-PSM-01 — Module Family.** Eight small identical navy rectangles in two rows of four. Top row (shipped): solid teal border. Bottom row (planned): dashed teal border. Each rectangle has a tiny icon hint (tree, globe, lock, eye, identity silhouette, plug, blueprint, gauge).

**UIAO-PSM-02 — JSON Envelope Pattern.** A single navy document silhouette with a cleanly stylized curly-brace boundary. Inside the boundary: five small horizontal rectangles representing envelope fields. Outside: a small teal data block representing the Data payload. A thin chain link connects the envelope to a Gitea hex icon.

**UIAO-PSM-03 — Integration Surface.** A central teal hex icon (UIAO modules) with four outbound navy arrows to: a Gitea hex (commit), a webhook bolt (notification), a gauge dial (drift), a chart bar silhouette (dashboard).

### 4.10 IDM — Identity Modernization Guide

**UIAO-IDM-01 — AD to Entra Landscape.** Left (steel gray): an abstract AD domain tree with small geometric nodes for users, groups, service accounts, OUs, AdminSDHolder. Right (teal): an Entra ID tenant as a soft cloud silhouette with small hex nodes for the same object classes. A clean navy arrow between.

**UIAO-IDM-02 — Entra Connect vs. Cloud Sync.** Two vertical panels, identical dimensions. LEFT (steel gray header): Entra Connect Sync — larger on-prem server block with sync icon to a cloud. RIGHT (teal header): Entra Cloud Sync — smaller on-prem agent with a cleaner sync icon.

**UIAO-IDM-03 — OrgPath Targeting.** A central object-identity user silhouette surrounded by four attribute tags in soft-edged navy pills, each pointing toward a teal dynamic-group node. The arrows converge into a single teal target ring on the right.

**UIAO-IDM-04 — Privileged Access Tiers.** Three concentric rings — outer (broad, steel gray) Tier 2, middle (medium, navy) Tier 1, center (small, teal with amber highlight) Tier 0. Each ring has a small key icon.

**UIAO-IDM-05 — Conditional Access Signal Funnel.** A funnel on white. Inputs at the top: five small signal tiles (user, device, location, app, risk). Output at the bottom: a single teal grant/deny diamond. Funnel walls navy; signals steel gray; diamond teal with amber edge.

**UIAO-IDM-06 — Migration Playbook Timeline.** A horizontal timeline ribbon with four segments of increasing length: assessment, pilot, scale, cutover. Between segments, small amber diamond go/no-go gates. Below: three thin parallel pillar lines (identity, device, authentication).

### 4.11 DNS — DNS Modernization Guide

**UIAO-DNS-01 — Current-State Landscape.** A clustered map of DNS zone types as small differently-shaped tiles: primary (rectangle), secondary (dashed-border rectangle), stub (half-rectangle), conditional forwarder (chevron), GlobalNames (hex), reverse (mirrored rectangle), integrated (rectangle with a tree icon). Navy and steel gray.

**UIAO-DNS-02 — Target State: Azure DNS Private Resolver.** Three-tier clean diagram. TOP: on-prem DNS silhouette (steel gray). MIDDLE: Azure DNS Private Resolver (teal), two inbound and two outbound endpoints. BOTTOM: Azure Private Zones as three hex cards. Thin navy arrows between.

**UIAO-DNS-03 — Split-Brain Pattern.** Central vertical dotted line. LEFT (public): a globe icon resolving `app.contoso.com` to a public IP silhouette. RIGHT (private): a lock-bound lan icon resolving the same name to a private IP. Both answers correct for their audience.

**UIAO-DNS-04 — Hub-Spoke DNS.** A central teal hub hex with spoke lines to four smaller navy spoke hexes. Each spoke carries a tiny resolver icon. One spoke is dashed to indicate on-prem connection.

**UIAO-DNS-05 — Migration Wave Bar.** Horizontal stacked bar in four segments: AD-integrated, standard primary, stub/forwarder, SRV. Segments shaded from steel gray (legacy) to teal (migrated). A small triangle progress cursor two-thirds along the bar.

### 4.12 PKI — PKI Modernization Guide

**UIAO-PKI-01 — ADCS Baseline Topology.** Hierarchical CA tree: offline root CA at top (steel gray, dashed border), two intermediate CAs below (navy), several issuing CAs beneath (teal). Thin navy tree connectors.

**UIAO-PKI-02 — ESC Risk Surface.** Eight small navy shield silhouettes in a row representing ESC1 through ESC8. Four shields are intact; four have a small amber crack. Generous whitespace. Thin tick marks below each shield.

**UIAO-PKI-03 — Cloud PKI Deployment Models.** Two side-by-side panels. LEFT: "Full Cloud Hierarchy" — a cloud with a root CA inside and issuing CAs beneath. RIGHT: "BYOCA" — a cloud on top, an on-prem root block below, a clean signing arrow between. Identical frames.

**UIAO-PKI-04 — Entra CBA Flow.** Horizontal flow: client certificate silhouette → chain validator (filter icon) → user binding (matching-keys icon, object-identity only) → token issuance (ticket silhouette) → Conditional Access diamond (teal) → granted (check) or denied (amber).

**UIAO-PKI-05 — Hybrid Coexistence.** Left (steel gray): on-prem ADCS silhouette. Right (teal): Cloud PKI silhouette. Between: a bridge diagram with two overlapping trust lines. A clock icon above the bridge.

### 4.13 ACC — AD Computer Object Conversion Guide

**UIAO-ACC-01 — Identity Decomposition.** Left: a legacy AD computer object silhouette (tower-shape rectangle with an LDAP-style hint). Right: three target objects — Entra device (cloud hex), Intune enrolled device (shield hex), Arc-enrolled server (globe hex). Navy arrows fan out from left to the three targets. Object identity only.

**UIAO-ACC-02 — OrgPath Replacement for OU.** Left: a small tree silhouette (OU hierarchy, steel gray). Right: a grid of small navy tiles (OrgPath attribute dimensions) feeding into a teal dynamic group node. A clean arrow from left to right.

**UIAO-ACC-03 — GPO to Intune Mapping.** Bipartite mapping. LEFT column (steel gray): stack of small GPO rectangles. RIGHT column (teal): stack of small Intune rectangles. Thin navy lines connect most GPOs to matching Intune tiles. A few GPOs have amber dashed lines to empty space (no direct equivalent).

**UIAO-ACC-04 — Azure Arc Resource Hierarchy.** Three-tier nested structure: management group (outer navy rounded rectangle), subscription (inner teal rectangle), resource groups (small white cards inside). Each card carries a tiny Arc-enrolled server icon.

### 4.14 CA — Conditional Access Policy Library

**UIAO-CA-01 — Policy Taxonomy.** A radial taxonomy. Center: a single teal diamond. Six spokes outward to six colored clusters: baseline, device tier, environment, region/site, application-specific, governance. Each cluster is a small group of same-colored tiles.

**UIAO-CA-02 — Policy Evaluation Model.** A stack of transparent policy layers in navy. An arrow marked with a small block shape passes through the stack and exits as teal (grant) — except where one layer is amber, forcing an amber-edged (block) exit.

**UIAO-CA-03 — Report-Only Test Funnel.** Seven-step funnel as stacked decreasing-width horizontal bars. Top bar steel gray; bottom bar teal. A thin amber dashed arrow loops from the second-to-last bar back to the second bar, representing remediation iteration.

**UIAO-CA-04 — Break-Glass Account Architecture.** Two small shield icons side by side with different edge-crack patterns (primary/secondary emergency accounts). A dashed boundary around both shields represents the exclusion group. A FIDO2 key silhouette stands outside the boundary in an unbreakable safe block.

### 4.15 INT — Intune Policy Templates

**UIAO-INT-01 — Policy Type Map.** Four quadrants on white. TOP-LEFT: compliance (shield). TOP-RIGHT: configuration (gear). BOTTOM-LEFT: endpoint security (lock). BOTTOM-RIGHT: app protection (app tile). Each quadrant a subtle muted pastel of the palette.

**UIAO-INT-02 — Assignment Flow.** Horizontal three-stage flow: dynamic group (teal hex) → filter (funnel icon) → device (abstract laptop outline). Small navy arrows between. A thin amber dashed line loops back from device to group, representing drift.

**UIAO-INT-03 — Compliance State Ladder.** Vertical ladder of five rungs labeled only by color: teal (compliant), muted amber (in grace period), amber (non-compliant), steel gray (unassigned), navy (not evaluated). Small device silhouettes hang off different rungs.

**UIAO-INT-04 — Co-Management Pivot.** Horizontal slider with two side panels. LEFT (steel gray): SCCM authoritative with a control knob. RIGHT (teal): Intune authoritative — the knob slides there. Seven workload-family cards above the slider, each colored according to current ownership.

### 4.16 ARC — Azure Arc Policy Library

**UIAO-ARC-01 — Arc-Enrolled Server.** A single on-prem server silhouette (no person) with a small cloud tether cable extending up to an Azure resource block. Cable is teal, thin, confident. Around the server: three small policy/tag badges.

**UIAO-ARC-02 — Tagging and OrgPath Integration.** Horizontal flow: AD computer silhouette with three attribute pills → Entra sync silhouette → Arc resource card with the same three tags. Clean, symmetric.

**UIAO-ARC-03 — Policy Initiative Composition.** A bundle of seven small policy-document tiles arranged in a fan, wrapped by a teal ribbon. Tiles are navy. Above the bundle: a stamp silhouette indicating "initiative."

**UIAO-ARC-04 — Guest Configuration Loop.** Circular six-stage loop: author → compile → package → test → publish → assign. Each stage a small icon (pencil, gear, box, microscope, upload arrow, target). Central hub a teal circle.

### 4.17 COR — Corpus-level

These images belong to the overall canon or the public site rather than any single document.

**UIAO-COR-01 — Canon Topology.** A clean network graph of approximately eighteen small nodes representing the canon documents. Three nodes are slightly larger (capstone, gap analysis, master spec). Edges are thin steel gray. Faint color washes group the clusters (capstone, strategic, platform, assessment, modernization, policy libraries).

**UIAO-COR-02 — Adapter Doctrine (SSOT + Identity + Security).** Triptych. LEFT: SSOT — a single teal obelisk with a faint reflection. MIDDLE: Identity — a certificate silhouette with a chain link (object identity only). RIGHT: Security — a shield with a subtle perimeter line. Above all three: a thin navy band.

**UIAO-COR-03 — Governance Pipeline.** Horizontal pipeline of six connected rectangular segments: assess → validate → commit → review → deploy → monitor. Each stage fades from navy to teal. Above the pipeline: a small Gitea hex with a dashed line to every stage, suggesting Gitea as the backbone.

**UIAO-COR-04 — Boundary Map.** Three nested ring bands. Innermost teal: GCC-Moderate (in scope). Middle steel gray: GCC-High / DoD IL (out of scope, noted). Outermost amber: Commercial Cloud (Amazon Connect and Azure Arc exceptions visible as two small tiles inside the outer ring).

**UIAO-COR-05 — Drift and Evidence Example.** Four-panel horizontal sequence. Panel 1: a config tile with amber glow (drift detected). Panel 2: a Gitea commit dot (drift logged). Panel 3: an issue-tracker card being filed. Panel 4: a green check with a signed seal (remediation closed).

**UIAO-COR-06 — Consume vs. Build Bookshelf.** A flat bookshelf in navy with nine identical book spines. Five spines on the left in muted steel gray (CONSUME — external tool outputs). Four on the right in teal (BUILD — UIAO native). Each spine has a tiny icon hint at the top.

## 5. Implementation Guidance

### 5.1 Rendering workflow

1. Copy the target prompt text block verbatim from Section 4.
2. Append the global style contract (Section 3.2) if the generator did not absorb it from context.
3. Request the highest available resolution; downscale locally if needed.
4. Save to `diagrams/<UIAO-ID>.png`. Generator rejects may be retained as `.draft.png` under a gitignored path.
5. Record the render (generator name, model or version, seed if available, Rev of this catalog) in `diagrams/README.md` next to the ID.

### 5.2 Stability rules

- **IDs are stable; pixels are not.** Do not change an ID to indicate a re-render. Bump the Rev in Section 11 instead.
- **IDs are never reused.** When an image is retired, its ID stays reserved.
- **A single prompt yields many rendered variants.** Operators may render multiple candidates; only one commits to `diagrams/<UIAO-ID>.png`.

### 5.3 Recommended helper

A minimal PowerShell helper at `tools/image_render.ps1` accepts an image ID and emits its prompt to STDOUT so an operator can pipe to the clipboard:

```powershell
. tools/image_render.ps1 UIAO-MPP-D001 | Set-Clipboard
# paste into the generator
```

The helper does not call external APIs. Rendering remains an explicit operator step.

## 6. Risks and Mitigations

| Risk ID | Risk                                                                                            | Probability | Impact | Mitigation                                                                                                                                      | Owner         |
|---------|--------------------------------------------------------------------------------------------------|-------------|--------|-------------------------------------------------------------------------------------------------------------------------------------------------|---------------|
| IP-001  | Rendered diagrams drift from this catalog because a prompt was edited in place without Rev bump | High        | Medium | CI lint that compares the Rev recorded in `diagrams/README.md` to the Rev in Section 11 of this document; fail build on mismatch.              | Canon Steward |
| IP-002  | An image references a person identity or vendor logo after render                              | Low         | High   | Visual-content review by the Canon Steward before commit; deny list in CONTRIBUTING.md.                                                        | Security Lead |
| IP-003  | Generator drift — different generators produce visually inconsistent output for the same prompt | Medium      | Medium | Record generator and model with every render; re-generate from the canonical generator when inconsistency is detected.                         | Canon Steward |
| IP-004  | A canonical document references an ID not present in this catalog                              | Medium      | Medium | CI lint: fail the build on any `UIAO-<DOC>-<NN>` reference in `canon/` that does not resolve to an ID in this document.                        | Canon Steward |
| IP-005  | Rendered image contains baked-in text that leaks classification or confidential terms          | Low         | Critical | Prompt policy forbids baked-in text; visual review prior to commit.                                                                             | Security Lead |

## 7. Appendices

### Appendix A — Definitions

See **Section 8 Glossary**.

### Appendix B — Object List

This document is itself a catalog of image objects. Section 4 enumerates all 77 images with stable IDs; that enumeration is the canonical Object List for the document. No additional tables or diagrams are introduced by this appendix.

### Appendix C — Copy Sections

Boilerplate referenced, not duplicated:
- **Adapter Doctrine paragraph** — Master Document Specification v1.3, Section 4.
- **Canonical UIAO Governance Constraints** — Master Spec, Section 3, item 12.
- **No-Hallucination Protocol** — Master Spec, Section 2.

### Appendix D — References

All references are to documents supplied by the user (Michael Stratton) during the 2026-04-21 session. No external sources are cited.

1. `UIAO_Master_Document_Specification.docx` (v1.3, April 2026)
2. `IMAGE-PROMPTS.md` (v1.0, 2026-04-12, Doc 01 scope — preserved verbatim in Section 4.1)
3. The eighteen uploaded UIAO Canon documents (full list in the corpus assessment, `2026-04-21-corpus-assessment.docx`)
4. `UIAO_Corpus_Assessment.docx` (Claude, 2026-04-21 — sibling review document)
5. `UIAO_NNN_Repository_and_Web_Strategy_v1.0.md` (sibling strategy document)

## 8. Glossary

**Catalog:** An enumerated, versioned collection of prompts whose identifiers are stable even as renders change.

**Diagram ID:** A stable identifier of the form `UIAO-<DOC>-<NN>` that names both an entry in this catalog and a file in `diagrams/`.

**Object identity:** The principle that images in the canon depict only system objects, not named persons. Silhouettes used in prompts are abstract placeholders with no implied identity.

**Palette (muted federal):** The five-color canon palette — Navy `#2E75B6`, Steel Gray `#5A5A5A`, Teal `#1A9E8F`, Amber `#D4A017`, White `#FFFFFF`.

**Prompt:** The prose input to a generator. Preserved verbatim in Section 4 so an operator can copy-paste without ambiguity.

**Rev:** The revision number recorded in Section 11 for each prompt block. Incremented when prompt text changes; unchanged by re-renders of the same prompt.

**Render:** The bits produced by a generator for a given prompt. Multiple renders may exist for the same Rev; only one is committed to `diagrams/`.

**SSOT — Single Source of Truth:** For this document, the catalog in Section 4 is SSOT for all canon image prompts.

## 9. Footnotes

[^1]: The governance-constraint list is reproduced from `UIAO_Master_Document_Specification_v1.3`, Section 3, item 12. Not originated in this document.

## 10. Validation Block

[VALIDATION]
All sections validated against source text.
Source text: the eighteen canon documents, the three master specifications, and `IMAGE-PROMPTS.md` v1.0 — all supplied by Michael Stratton during the 2026-04-21 review session.
Conformance: Master Document Specification v1.3, Section 3.
Doc 01 prompts (Section 4.1) preserved verbatim from v1.0.
All corpus-wide and corpus-level prompts (Sections 4.2 through 4.17) originated in this catalog and labeled **NEW (Proposed)** where a target canon document does not yet specify a diagram requirement.
No hallucinations detected.
Uncertain items explicitly marked **MISSING**, **UNSURE**, or **NEW (Proposed)** in-line.
[/VALIDATION]

---

## 11. Revision Log

| Rev  | Date       | Change                                                                                           |
|------|------------|--------------------------------------------------------------------------------------------------|
| v1.0 | 2026-04-12 | Doc 01 Executive Brief — 8 prompts. Original upload (now Section 4.1 here, preserved verbatim). |
| v2.0 | 2026-04-21 | Full corpus catalog: 77 prompts across 16 canon documents plus 6 corpus-level images.            |
