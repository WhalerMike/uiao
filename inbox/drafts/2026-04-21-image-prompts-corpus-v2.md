# UIAO — Image Prompts Catalog

**Document ID:** UIAO_SPEC_IMAGE_PROMPTS_v2.0
**Supersedes:** IMAGE-PROMPTS.md v1.0 (Doc 01 only, 12 April 2026)
**Classification:** UIAO Canon — Public Release
**Boundary:** GCC-Moderate
**Date:** 21 April 2026
**Author:** Michael Stratton (owner) — expanded by Claude (Cowork)
**Paste targets:** Gemini, DALL·E 3, Midjourney, SeedDream, or any prompt-driven image generator.

---

## 0. How to use this file

1. Every image has a stable **ID** in the form `UIAO-<DOC>-NN`. That ID is the filename stem (`diagrams/UIAO-MPP-D001.png`) and the anchor the canon documents reference ("see Diagram UIAO-MPP-D001").
2. Do not regenerate a rendered image without bumping the **Rev** noted at the bottom of each prompt block — readers rely on stable IDs, not stable pixels.
3. All images obey the **global style contract** in §1 unless a prompt explicitly overrides it.
4. Baked-in text is prohibited. Captions, legends, and axis labels are added in the document, not in the image. This keeps images reusable across languages and accessibility profiles.
5. Prompts are written in prose so a non-technical generator produces something close on the first pass. If your generator expects parameters, the tail of every prompt lists them explicitly (aspect, palette, style).

---

## 1. Global style contract

Applies to every image unless the prompt says otherwise.

- **Audience:** a federal CIO reading a whitepaper. Think McKinsey, Deloitte, or a Government Accountability Office infographic. Not startup marketing.
- **Mood:** calm, trustworthy, deterministic. Never alarmist, never playful, never cute.
- **Aspect ratio:** 16:9 widescreen. Safe for both docx embedding and pptx slides.
- **Resolution target:** 1920×1080 minimum; 2560×1440 preferred; request the generator's highest available.
- **Palette (muted federal):**
  - Navy `#2E75B6` — primary structure, frames, headings, main lines.
  - Steel Gray `#5A5A5A` — secondary structure, neutral fills, legacy/on-prem elements.
  - Teal `#1A9E8F` — healthy, compliant, "flow is good" accents.
  - Amber `#D4A017` — warnings, drift, watchpoints. Never red unless the image is specifically about a failure/critical state.
  - White `#FFFFFF` — background.
- **Prohibited:** baked-in text (unless noted), people or silhouettes that read as a real individual, stock photography, clip art, vendor logos (including Microsoft/Azure/Entra marks), emoji, neon or saturated "tech startup" colors, 3D renders with glossy surfaces, isometric scenes with visible perspective distortion.
- **Preferred:** flat vector with subtle depth, clean isometrics, restrained shadow, legible at thumbnail size.
- **Composition:** strong focal point, generous white space, one visual idea per image.
- **Accessibility:** sufficient contrast (WCAG AA text-on-background equivalent); do not encode meaning in color alone — use shape or position as the primary carrier.

---

## 2. Index

| Doc code | Document                                             | Images |
|----------|------------------------------------------------------|--------|
| EXEC     | Doc 01 — Executive Brief                             | 8      |
| GAP      | UIAO vs. Microsoft Native Tools (Gap Analysis)       | 5      |
| MPP      | Master Project Plan                                  | 6      |
| ADR      | Git Infrastructure — ADR-001                         | 3      |
| PSB      | Platform Server Build Guide (Gitea + IIS)            | 4      |
| CLI      | CLI and Operations Guide                             | 3      |
| ADI      | AD Interaction Guide                                 | 4      |
| ROA      | Read-Only AD Assessment Guide                        | 3      |
| PSM      | PowerShell Module Reference                          | 3      |
| IDM      | Identity Modernization Guide                         | 6      |
| DNS      | DNS Modernization Guide                              | 5      |
| PKI      | PKI Modernization Guide                              | 5      |
| ACC      | AD Computer Object Conversion Guide                  | 4      |
| CA       | Conditional Access Policy Library                    | 4      |
| INT      | Intune Policy Templates                              | 4      |
| ARC      | Azure Arc Policy Library                             | 4      |
| COR      | Corpus-level (adapter doctrine, SCuBA parallel, etc.)| 6      |

Total: **77 images**. All are optional in the sense that documents remain readable without them; all are recommended for a Public Release posture.

---

## 3. EXEC — Doc 01, Executive Brief

*Preserved from the uploaded v1.0 file. IDs were added; prompt text is unchanged except for minor format alignment to this catalog.*

### UIAO-EXEC-01 — Cover / Hero
**Placement:** Page 1, below the title "UIAO" and above the tagline.
**Prompt:** A wide, clean, professional illustration representing continuous automated compliance monitoring for a federal government IT environment. A calm, abstract digital landscape where a central glowing blue shield or lens continuously scans a network of connected nodes representing cloud services (email, collaboration, identity, security). The nodes pulse with soft green light when healthy, amber when drifting. The visual feel is calm control — not alarm, not chaos. Flat vector with subtle depth, government whitepaper tone.

### UIAO-EXEC-02 — The Problem
**Placement:** After the first paragraph of "The Problem" section, or as a sidebar visual.
**Prompt:** A conceptual illustration showing the pain of manual federal compliance. On one side, a towering stack of paper documents, binders, and spreadsheets — slightly disorganized, casting shadows. On the other side, a clock face showing months passing. Between them, a fading trail of screenshots and handwritten checkmarks that are visibly outdated. Weary, bureaucratic, quiet exhaustion of paperwork that never ends. Warm grays, muted tan for paper, faded blue for the clock. Editorial illustration, clean lines, minimal detail.

### UIAO-EXEC-03 — Continuous Monitoring Loop
**Placement:** In the "What UIAO Does About It" section.
**Prompt:** A clean circular diagram showing a continuous monitoring loop. Four stages flow clockwise: SCAN (a magnifying glass over cloud services), EVALUATE (a checklist being compared against a rulebook), EVIDENCE (a document with a cryptographic lock/seal), ALERT (a notification bell with an amber glow). Arrows connect the stages smoothly. Navy circle, white background, teal stage icons, amber alert. Clean infographic, flat design with subtle shadows.

### UIAO-EXEC-04 — Before and After
**Placement:** In "The Effort, Time, and Money Conversation" section, near the comparison table.
**Prompt:** A split-screen illustration. LEFT "Before" (muted red/gray): compliance team buried in manual work — binders, calendar with 18 months circled, red-celled spreadsheets, abstract slumped silhouette. RIGHT "After" (clean blue/green): nearly empty desk, monitor with green dashboard, signed digital document with lock icon, calendar showing always current. Heavy vs. light, cluttered vs. clean, stressed vs. calm. Editorial comparison, minimalist.

### UIAO-EXEC-05 — Three Layers of Rules
**Placement:** In the "How It Works" section.
**Prompt:** A layered stack diagram showing three horizontal translucent layers like glass shelves. BOTTOM (widest, navy): FedRAMP Moderate Rev 5 — 247 Controls, as a grid of shield icons. MIDDLE (medium, teal): CISA SCuBA & BOD 25-01, as a governance seal. TOP (narrowest, steel gray): Your Agency Policies, as a small building or agency seal. A vertical arrow passes through all three. Clean layered diagram, white background.

### UIAO-EXEC-06 — Immutable Evidence Chain
**Placement:** In the "How It Works" section.
**Prompt:** A horizontal chain of linked evidence blocks — a simplified, elegant blockchain-style visualization. Each block contains a timestamp icon, a check-result icon, and a digital-signature (lock) icon. The blocks are connected by subtle chain links. The newest block glows softly; the chain extends into the distance. A magnifying glass hovers over one block. Navy blocks, white background, amber signature icons. Trust and permanence.

### UIAO-EXEC-07 — Three Differentiators
**Placement:** In the "What Makes This Different" section.
**Prompt:** Three distinct icons arranged horizontally with generous whitespace. LEFT: "Deterministic" — a binary ON/OFF switch, decisive. CENTER: "Produces Deliverables" — a finished document with an OSCAL-style official seal emerging from a conveyor. RIGHT: "Built for Federal M365" — an abstract M365-shape wrapped in a government shield. Each icon sits above a thin line for caption. Muted blue, teal, gray on white. Icon set, consistent weight.

### UIAO-EXEC-08 — The 90-Day Ask
**Placement:** In "What We Need From Leadership" section.
**Prompt:** A simple, confident 90-day timeline arc. DAY 1: a connection icon (UIAO linking to a GCC-Moderate tenant). DAY 45: a side-by-side comparison icon. DAY 90: a green checkmark or thumbs-up seal. Clean and optimistic, not a Gantt. Navy arc, white background, green final milestone.

---

## 4. GAP — UIAO vs. Microsoft Native Tools

### UIAO-GAP-01 — The Twelve Instruments
**Placement:** Opening of Section 2, Microsoft Native Tool Landscape.
**Prompt:** A wide flat-vector orchestra pit composition — twelve abstract musical instrument silhouettes arranged in a shallow semicircle, each a different shape (no real instrument is literal; think geometric interpretations), each rendered in muted navy and steel gray. No conductor, no people. Above the semicircle, a faint teal curved line arcs like a missing conductor's baton. Whitespace-heavy, editorial. Federal whitepaper tone. 16:9.

### UIAO-GAP-02 — The Orchestra — UIAO as Orchestrator
**Placement:** Section 6.1, Orchestration Layer Pattern.
**Prompt:** Same twelve instrument silhouettes as UIAO-GAP-01, now arranged below a central conducting node — a clean teal diamond with subtle radiating lines to each instrument. The lines are taut, purposeful, not beams of light. The diamond has no face, no hands, no implied person — it is pure geometry. Above the diamond, a thin navy bar labeled only by position suggests a governance layer. Palette: navy instruments, steel-gray shadows, teal diamond, white background.

### UIAO-GAP-03 — Coverage Matrix Visual
**Placement:** Section 3, Capability Matrix, as a section opener.
**Prompt:** A stylized capability matrix — ten rows by three columns, rendered as a soft-edged heatmap. Rows (unlabeled in the image) represent UIAO assessment domains; columns represent Microsoft coverage, third-party coverage, and UIAO coverage. Cells are shaded in a scale from steel-gray (no coverage) through muted amber (partial) to teal (full). The UIAO column is dominantly teal; the Microsoft column is a patchwork; the third-party column sits between. Flat, clean, whitespace generous. 16:9.

### UIAO-GAP-04 — SCuBA Parallel
**Placement:** Section 6.3, The SCuBA Parallel.
**Prompt:** A horizontal dual-track diagram. TOP TRACK: left box labeled visually as "CISA ScubaGear" (pure silhouette — a scuba mask shape), a small arrow, a center teal diamond (UIAO), a small arrow, right box showing a seal. BOTTOM TRACK: left box showing the twelve-instrument silhouette from UIAO-GAP-01, a small arrow, the same teal diamond, a small arrow, the same seal on the right. A single vertical dotted navy line connects the two teal diamonds, showing they are the same node. Clean, symmetric, no text. 16:9.

### UIAO-GAP-05 — Consume vs. Build
**Placement:** Section 7, What UIAO Should Consume vs. Build.
**Prompt:** Two vertical columns on a white canvas. LEFT column: a stack of small inbound-arrow tiles labeled only by color (various muted tones) feeding into a teal funnel — this represents CONSUME. RIGHT column: a teal anvil/workbench with small outbound-arrow tiles emerging — this represents BUILD. Between them, a thin navy divider. No text. The composition reads immediately as "inputs on the left, outputs on the right." 16:9.

---

## 5. MPP — Master Project Plan

### UIAO-MPP-D001 — Program Timeline (Gantt Overview)
**Placement:** Section 1 Executive Summary, after the Program Timeline Summary table.
**Prompt:** A seven-phase horizontal program timeline in flat vector. Seven color-coded horizontal bars stacked vertically, each of a different length corresponding to Phase 0 through Phase 6 (3, 6, 4, 8, 12, 8, ongoing weeks). Phase bars rest on a subtle week-number ruler at the bottom (ticks only, no numerals baked in). Between bars, small diamond shapes mark milestone gates. One horizontal dashed navy line runs through all phases, representing the critical path. Parallel thin bars below each phase bar indicate the five pillar workstreams (Identity, Devices, DNS, PKI, Server). Palette: navy primary bars, teal pillar bars, amber critical-path dashes, white background. Editorial Gantt style, no grid lines. 16:9.

### UIAO-MPP-D002 — Milestone Dependency Network
**Placement:** Section 11 Dependency Map.
**Prompt:** A directed acyclic graph of approximately forty-eight small nodes arranged roughly left to right by phase. Nodes are small navy circles of uniform size. Edges are thin steel-gray lines with minimal arrowheads. A continuous navy line highlights one specific path through the graph — the critical path — without labels. Clusters of nodes visually group by phase with thin translucent bands in the background. No node labels, no text. 16:9.

### UIAO-MPP-D003 — Phase Transition Flow
**Placement:** Section 11.2, after Critical Path statement.
**Prompt:** A clean left-to-right flowchart with seven sequential rectangular phase blocks, each in a slightly different shade of navy. Between every two phases, a diamond-shaped gate review node in amber. Within each phase block, three to five thin parallel pillar lines suggest parallel workstreams. At the end, a final block opens into an ongoing "steady state" that fades rightward. No text. 16:9.

### UIAO-MPP-D004 — Governance Cadence Wheel
**Placement:** Section 2.3 Communication Cadence.
**Prompt:** A single circular wheel divided into four concentric rings. Innermost ring: weekly (smallest notches). Second ring: monthly. Third ring: quarterly. Outermost ring: annually. Notch marks for cadence events only; no words, no days. Center dot is teal. Rings are navy outlines on a white background, with very subtle amber highlights where critical reviews fall. Minimal, clockwork-like. 16:9 with the wheel offset left, white negative space on the right for callout labels applied in the document.

### UIAO-MPP-D005 — Risk Heatmap
**Placement:** Section 10 Risk Register.
**Prompt:** A five-by-five probability/impact heatmap. Cells shaded on a diagonal gradient from white (low probability, low impact, bottom-left) to amber (high, high, top-right). Approximately twenty-two small navy dots scattered across the cells representing risks R-001 through R-022 (no IDs shown in-image). Grid lines are thin, steel-gray. Axes are unlabeled rectangles — labels applied in-document. 16:9.

### UIAO-MPP-D006 — Budget Stacked Composition
**Placement:** Section 12 Budget and Resource Estimate.
**Prompt:** A clean horizontal stacked bar rendered in four segments representing licensing, infrastructure, people, and services in relative proportion. Each segment a distinct palette color: navy, steel gray, teal, and amber. A thin vertical ruler marks the total. Generous whitespace above and below. No numerals. 16:9.

---

## 6. ADR — Git Infrastructure — ADR-001

### UIAO-ADR-01 — Five Options at a Glance
**Placement:** Section 3 Architecture Options Evaluated, section opener.
**Prompt:** Five small square cards arranged horizontally with generous spacing. Each card shows an abstract architectural silhouette: (A) IIS alone — a single navy block; (B) Gitea behind IIS — two joined blocks with an arrow; (C) Azure DevOps on-prem — a cluster of blocks; (D) Gogs — single block; (E) Custom ASP.NET API — gear inside a block. One card (B) has a subtle teal highlight border; the others are plain navy. No text. 16:9.

### UIAO-ADR-02 — Recommended Architecture
**Placement:** Section 4 Recommended Architecture — Gitea + IIS Hybrid.
**Prompt:** A two-tier architectural diagram. TOP tier (broad navy bar): "IIS" — handling TLS termination, depicted as a lock icon and reverse-proxy arrows. BOTTOM tier (teal bar): "Gitea" — depicted as a single Go-style gopher-free geometric symbol (use an abstract hex or diamond). Between them, a short vertical connector with a subtle request/response curve. Around the outside: LDAP/AD silhouette on the left, Entra OAuth silhouette on the right, both connecting only to the Gitea tier. Minimal, schematic. 16:9.

### UIAO-ADR-03 — Migration Path
**Placement:** Section 6 Migration Path from IIS-Only to Gitea+IIS.
**Prompt:** A horizontal arrow sweep with five numbered milestones along its length — small navy diamonds at each milestone. Above the arrow: a "before" silhouette on the far left (single IIS block). Below the arrow: an "after" silhouette on the far right (Gitea + IIS two-tier block). No numerals. Teal accent on the arrow tip. 16:9.

---

## 7. PSB — Platform Server Build Guide (Gitea + IIS)

### UIAO-PSB-01 — Server Topology
**Placement:** Section 2.6 Architecture Diagram.
**Prompt:** A clean five-tier vertical topology: Client tier (top, small browser/PowerShell silhouettes), Reverse Proxy tier (IIS block with lock icon), Application tier (Gitea block), Storage tier (disk + DB cylinder icons), Identity tier (LDAP/AD silhouette + Entra silhouette side by side). Thin navy arrows connect tiers top-to-bottom; thin teal arrows show east-west integrations. White background, subtle grid. 16:9.

### UIAO-PSB-02 — Phase Sequence
**Placement:** Section opener before Phase 1.
**Prompt:** Thirteen small circular step beads arranged along a gentle S-curve from top-left to bottom-right. Every third bead is filled teal; the rest are navy outlines. The S-curve is a continuous navy ribbon. No numerals, no text. 16:9.

### UIAO-PSB-03 — TLS Chain
**Placement:** Section 6 TLS Certificate Configuration.
**Prompt:** Three vertical certificate silhouettes (a small rectangle with a lock/seal icon at its top), connected by thin curved lines: Root → Intermediate → Leaf. The leaf is highlighted teal; the root and intermediate are navy. A browser silhouette at the far right reads the leaf with a tiny "trust" tick. No text. 16:9.

### UIAO-PSB-04 — Backup and DR Topology
**Placement:** Section 12 Backup, Replication, and Disaster Recovery.
**Prompt:** Primary Gitea server (large teal block) on the left, secondary passive server (muted teal block) on the right, Azure Blob icon at top as a detached backup target (small cloud silhouette). Solid arrow from primary to blob (nightly backup). Dashed arrow from primary to passive (replication). Small clock icon hovers between the two servers. No numerals. 16:9.

---

## 8. CLI — CLI and Operations Guide

### UIAO-CLI-01 — Dual-Remote Topology
**Placement:** Part I, Section 1.4 Configure Dual Remotes.
**Prompt:** A developer workstation silhouette (small laptop outline, no person) in the center. Two outbound navy arrows: one to a Gitea block on the left labeled visually by a small hex icon (Gitea), one to a GitHub block on the right with a small octocat-free geometric mark. The Gitea arrow is solid and bold; the GitHub arrow is dashed and thinner. No text. 16:9.

### UIAO-CLI-02 — API Surface
**Placement:** Part II, Gitea REST API Reference opener.
**Prompt:** A central teal ring labeled visually by a small API gear icon. Eight outbound arrows to eight small navy tiles representing endpoint families: repositories, pull requests, organizations, webhooks, releases, users, issues, admin. Tiles are identical in size and weight. White background, clean infographic. 16:9.

### UIAO-CLI-03 — Governance Hook Chain
**Placement:** Part VII, before Appendix. Hook execution sequence.
**Prompt:** A left-to-right horizontal flow showing three hook stations: pre-receive (shield icon), update (key icon), post-receive (paper-airplane icon). Between each station, a short arrow. A thin navy ribbon below captures the whole as "the governance gate." No text. 16:9.

---

## 9. ADI — AD Interaction Guide

### UIAO-ADI-01 — Forest Discovery Pipeline
**Placement:** Section 3 opener.
**Prompt:** Left: an abstract tree silhouette (geometric, not botanical) representing the AD forest. Right: a small navy file icon representing a JSON artifact. Between them: three concentric arcs labeled visually only by shape — domains, OUs, objects — each funneling into the JSON icon. Clean flow, no text. 16:9.

### UIAO-ADI-02 — Assessment Output Schema
**Placement:** Appendix B Assessment Output Schema Reference.
**Prompt:** A grid of small equal-sized navy tiles, each representing a JSON artifact — approximately twenty tiles. Arranged four rows by five columns, whitespace-heavy. Each tile has a small icon hint (OU silhouette, lock, tree, person-less user silhouette) but no text. Clean, orderly, canonical. 16:9.

### UIAO-ADI-03 — Pipeline Integration
**Placement:** Section 11 UIAO Assessment Pipeline Integration.
**Prompt:** Horizontal three-step flow: PowerShell icon → JSON file icon → Gitea hex icon. Each step a small teal-bordered card; arrows between are clean navy. Below the flow: a thin amber dashed line returning from Gitea back to PowerShell labeled only by a small arrow curve, suggesting drift feedback. 16:9.

### UIAO-ADI-04 — Trust Map
**Placement:** Section 10 Trust Relationship Mapping.
**Prompt:** Five to seven small tree silhouettes representing domains, arranged in a loose cluster. Lines between them: solid navy for two-way trusts, dashed navy for one-way trusts. One tree is slightly larger and highlighted teal — the root. No text. 16:9.

---

## 10. ROA — Read-Only AD Assessment Guide

### UIAO-ROA-01 — Coverage vs. Delegation Gap
**Placement:** Section 4 Read-Only Assessment Coverage Score.
**Prompt:** A single horizontal bar divided left-to-right: a large teal segment (~87% of the bar) labeled visually by a check-silhouette; a smaller amber segment (~13%) labeled visually by a key silhouette (delegation required). Above the bar: a small magnifying glass. Below the bar: a thin navy ruler tick marks without numerals. 16:9.

### UIAO-ROA-02 — Least-Privilege Principle
**Placement:** Section opener.
**Prompt:** A small padlock silhouette on the left. A thin navy arrow going right toward a grid of tiny tiles (approximately fifty) — most of the tiles are teal (reachable by read-only), a minority are amber (require elevated access). The lock is not broken; the reach is long. White background, clean. 16:9.

### UIAO-ROA-03 — Delegation Request Flow
**Placement:** Section 8 Delegation Request Template.
**Prompt:** Three-step horizontal flow: read-only baseline (teal circle) → gap identified (amber diamond) → delegation request submitted (navy envelope). Each step connected by a short arrow. A small clock icon above the amber diamond suggests review latency. No text. 16:9.

---

## 11. PSM — PowerShell Module Reference

### UIAO-PSM-01 — Module Family
**Placement:** Section 1.2 Modules Covered.
**Prompt:** Eight small identical navy rectangles arranged in two rows of four. The top row (shipped) has a solid teal border. The bottom row (planned) has a dashed teal border. Each rectangle has a tiny icon hint: tree, globe, lock, eye, person-less identity silhouette, plug, blueprint, gauge. No text. Whitespace-heavy. 16:9.

### UIAO-PSM-02 — JSON Envelope Pattern
**Placement:** Section 1.4 JSON Output Envelope.
**Prompt:** A single navy document silhouette with a cleanly stylized curly-brace boundary. Inside the boundary: five small horizontal rectangles of varying lengths representing the standard envelope fields. Outside the boundary: a small teal data block labeled visually by a grid hint representing the Data payload. A thin chain link connects the envelope to a Gitea hex icon on the right. No text. 16:9.

### UIAO-PSM-03 — Integration Surface
**Placement:** Section 10 Integration Guide opener.
**Prompt:** A central teal hex icon (UIAO modules) with four outbound navy arrows to: a Gitea hex (commit), a webhook bolt (notification), a governance gauge dial (drift), and a chart bar silhouette (dashboard). Clean, radial, whitespace-heavy. 16:9.

---

## 12. IDM — Identity Modernization Guide

### UIAO-IDM-01 — AD to Entra Landscape
**Placement:** Section 2 opener.
**Prompt:** Left side (steel gray, muted): an abstract AD domain tree with small nodes for users, groups, service accounts, OUs, and AdminSDHolder (all as geometric silhouettes, no people). Right side (teal): an Entra ID tenant depicted as a soft cloud silhouette with small hex nodes for the same object classes. A clean navy horizontal arrow in the middle with the word-free suggestion of migration. No labels. 16:9.

### UIAO-IDM-02 — Entra Connect vs. Cloud Sync
**Placement:** Section 4.1 Decision Matrix.
**Prompt:** Two vertical panels, side by side, identical dimensions. LEFT (steel gray header): Entra Connect Sync — depicted as a larger on-prem server block with a sync icon pointing up to a cloud silhouette. RIGHT (teal header): Entra Cloud Sync — depicted as a smaller on-prem agent with a cleaner, more direct sync icon. Minimal, side-by-side comparison, no text. 16:9.

### UIAO-IDM-03 — OrgPath Targeting
**Placement:** Section 3.4 OrgPath Pattern — Extension Attribute Mapping.
**Prompt:** A central user silhouette (abstract, object-identity only) surrounded by four attribute tags in soft-edged navy pills, each pointing toward a teal dynamic-group node. The arrows converge into a single teal target ring on the right. White background, whitespace-heavy. No text. 16:9.

### UIAO-IDM-04 — Privileged Access Tiers
**Placement:** Section 7 Privileged Access Management.
**Prompt:** Three concentric rings — outer (broad, steel gray) Tier 2, middle (medium, navy) Tier 1, center (small, teal with amber highlight) Tier 0. Each ring has a small key icon. No people, no text. 16:9.

### UIAO-IDM-05 — Conditional Access Signal Funnel
**Placement:** Section 8 Conditional Access Policy Framework.
**Prompt:** A funnel shape on a white canvas. Inputs to the top of the funnel: five small labeled-by-icon-only signal tiles (user, device, location, app, risk). Output at the bottom: a single teal grant/deny diamond. The funnel walls are navy; signals are steel gray; the diamond is teal with an amber edge. 16:9.

### UIAO-IDM-06 — Migration Playbook Timeline
**Placement:** Section 13 Migration Execution Playbook.
**Prompt:** A horizontal timeline ribbon with four segments of increasing length: assessment, pilot, scale, cutover. Each segment a different muted palette color. Between segments, small amber diamonds mark go/no-go gates. Below the ribbon: three thin parallel pillar lines suggesting identity, device, and authentication workstreams. No text. 16:9.

---

## 13. DNS — DNS Modernization Guide

### UIAO-DNS-01 — Current-State Landscape
**Placement:** Section 2 opener.
**Prompt:** A clustered map of DNS zone types arranged as small differently-shaped tiles: primary (rectangle), secondary (rectangle with dashed border), stub (half-rectangle), conditional forwarder (chevron), GlobalNames zone (small hex), reverse zone (mirrored rectangle), integrated zone (rectangle with small tree icon inside). Arranged in a loose galaxy, whitespace-heavy. Navy and steel gray palette. No text. 16:9.

### UIAO-DNS-02 — Target State: Azure DNS Private Resolver
**Placement:** Section 3.3 Azure DNS Private Resolver.
**Prompt:** A clean three-tier diagram. TOP: on-prem DNS silhouette (steel gray). MIDDLE: Azure DNS Private Resolver (teal), shown as two inbound endpoints and two outbound endpoints as small paired icons. BOTTOM: Azure Private Zones, depicted as three small hex cards. Thin navy arrows between tiers. White background. No text. 16:9.

### UIAO-DNS-03 — Split-Brain Pattern
**Placement:** Section 9.1 Pattern 1: Same Namespace, Different Answers.
**Prompt:** Two sides of a central vertical dotted line. LEFT (public): a small globe icon resolving `app.contoso.com` to a public IP silhouette. RIGHT (private): a small lock-bound lan icon resolving the same name to a private IP silhouette. Both answers are correct for their audience. Neutral, explanatory, no alarm. 16:9.

### UIAO-DNS-04 — Hub-Spoke DNS
**Placement:** Section 3.7 Hub-Spoke DNS Topology.
**Prompt:** A central hub hex (teal) with spoke lines to four smaller spoke hexes (navy). Each spoke carries a tiny DNS resolver icon. One spoke is dashed to indicate on-prem connection. White background, clean radial. 16:9.

### UIAO-DNS-05 — Migration Wave Bar
**Placement:** Section 13 Migration Execution Playbook.
**Prompt:** Horizontal stacked bar divided into four zone-family segments: AD-integrated, standard primary, stub/forwarder, SRV. Segments shaded from steel gray (legacy) to teal (migrated). A progress cursor (small triangle) sits two-thirds along the bar. No numerals. 16:9.

---

## 14. PKI — PKI Modernization Guide

### UIAO-PKI-01 — ADCS Baseline Topology
**Placement:** Section 2.1 Typical ADCS Topology.
**Prompt:** A hierarchical CA tree: offline root CA at the top (steel gray rectangle, dashed border), two intermediate CAs below (navy rectangles), several issuing CAs beneath (teal rectangles). Tree connectors are thin navy lines. No text. 16:9.

### UIAO-PKI-02 — ESC Risk Surface
**Placement:** Section 3 ADCS Security Assessment (ESC Vulnerabilities).
**Prompt:** Eight small navy shield silhouettes arranged in a row representing ESC1 through ESC8. Four shields are intact; four have a small amber crack. The shields are evenly spaced with generous whitespace. Below each shield, a thin tick mark. No text. 16:9.

### UIAO-PKI-03 — Cloud PKI Deployment Models
**Placement:** Section 5 Target Architecture.
**Prompt:** Two side-by-side panels. LEFT: "Full Cloud Hierarchy" — a cloud silhouette with a root CA inside, issuing CAs beneath. RIGHT: "BYOCA" — a cloud silhouette on top, an on-prem root block below, a clean signing arrow between. Both panels in identical frames. No text. 16:9.

### UIAO-PKI-04 — Entra CBA Flow
**Placement:** Section 7.1 Authentication Flow.
**Prompt:** A horizontal flow: client certificate silhouette → chain validator (a small filter icon) → user binding (a matching-keys icon, object-identity only) → token issuance (a small ticket silhouette) → Conditional Access diamond (teal) → granted (check) or denied (amber). Each step a small clean tile connected by thin navy arrows. 16:9.

### UIAO-PKI-05 — Hybrid Coexistence
**Placement:** Section 8 Hybrid Coexistence Architecture.
**Prompt:** Left (steel gray): on-prem ADCS silhouette. Right (teal): Cloud PKI silhouette. Between: a bridge diagram with two overlapping trust lines — client certificates flow through both paths during coexistence. A clock icon above the bridge suggests migration window. 16:9.

---

## 15. ACC — AD Computer Object Conversion Guide

### UIAO-ACC-01 — Identity Decomposition
**Placement:** Section 1 opener.
**Prompt:** Left: a legacy AD computer object silhouette (small tower-shaped rectangle with an LDAP-style hint). Right: three target objects — Entra device (cloud hex), Intune enrolled device (shield hex), Arc-enrolled server (globe hex). Thin navy arrows fan out from the left to the three targets. No people, object identity only. 16:9.

### UIAO-ACC-02 — OrgPath Replacement for OU
**Placement:** Section 2 OrgPath for Devices.
**Prompt:** Left: a small tree silhouette (OU hierarchy, steel gray). Right: a grid of small navy tiles (OrgPath attribute dimensions) feeding into a teal dynamic group node. A clean arrow from left to right suggests the shift from hierarchy to attribute targeting. No text. 16:9.

### UIAO-ACC-03 — GPO to Intune Mapping
**Placement:** Section 4 GPO-to-Intune Policy Mapping.
**Prompt:** A bipartite mapping diagram. LEFT column (steel gray): stack of small GPO rectangles. RIGHT column (teal): stack of small Intune rectangles. Thin navy lines connect most GPOs to a matching Intune tile. A few GPO tiles have amber dashed lines to an empty space (no direct equivalent). No text. 16:9.

### UIAO-ACC-04 — Azure Arc Resource Hierarchy
**Placement:** Section 5.2 Resource Hierarchy Design.
**Prompt:** A three-tier nested structure: management group (outer navy rounded rectangle), subscription (inner teal rectangle), resource groups (small white cards inside). Each card has a tiny Arc-enrolled server icon hint. Clean, nested, no text. 16:9.

---

## 16. CA — Conditional Access Policy Library

### UIAO-CA-01 — Policy Taxonomy
**Placement:** Section 1 Executive Summary.
**Prompt:** A radial taxonomy. Center: a single teal diamond. Six spokes outward to six colored clusters: baseline, device tier, environment, region/site, application-specific, governance. Each cluster is a small group of tiles of the same color. Clean, whitespace-heavy. No text. 16:9.

### UIAO-CA-02 — Policy Evaluation Model
**Placement:** Section 2.1 Policy Evaluation Order and Conflict Resolution.
**Prompt:** A stack of several transparent policy layers in navy. An arrow marked with a small block shape passes through the stack and exits as teal (grant) — except where one layer is amber, which forces the exit to amber-edged (block). Wordless, cause-and-effect. 16:9.

### UIAO-CA-03 — Report-Only Test Funnel
**Placement:** Section 2.5 Report-Only Mode Testing Methodology.
**Prompt:** A seven-step funnel rendered as a set of decreasing-width horizontal bars stacked top-to-bottom (widest at top). The top bar is steel gray; the bottom bar is teal. Thin amber dashed arrow loops back from the second-to-last bar to the second bar, representing the iteration required if remediation is needed. No text. 16:9.

### UIAO-CA-04 — Break-Glass Account Architecture
**Placement:** Section 11 Break-Glass Account Procedures.
**Prompt:** Two small shield icons side by side labeled visually only by different cracks (primary/secondary emergency accounts — different edge patterns). Around both shields: a dashed boundary representing the exclusion group. A small FIDO2 key silhouette stands outside the boundary in an unbreakable safe block. No people, no text. 16:9.

---

## 17. INT — Intune Policy Templates

### UIAO-INT-01 — Policy Type Map
**Placement:** Section 2.1 Intune Policy Types.
**Prompt:** Four quadrants on a white canvas. TOP-LEFT: compliance (shield silhouette). TOP-RIGHT: configuration (gear silhouette). BOTTOM-LEFT: endpoint security (lock silhouette). BOTTOM-RIGHT: app protection (app tile silhouette). Each quadrant a subtle muted pastel of the palette. No text. 16:9.

### UIAO-INT-02 — Assignment Flow
**Placement:** Section 2.2 Policy Assignment Strategy.
**Prompt:** A horizontal three-stage flow: dynamic group (teal hex) → filter (funnel icon) → device (abstract laptop outline, no person). Between each stage, a small navy arrow. A thin amber dashed line loops back from device to group, representing drift. 16:9.

### UIAO-INT-03 — Compliance State Ladder
**Placement:** Section 10 Monitoring and Drift Detection.
**Prompt:** A vertical ladder of five rungs labeled only by color: green teal (compliant), muted amber (in grace period), amber (non-compliant), steel gray (unassigned), navy (not evaluated). A few small device silhouettes hang off different rungs at different heights. No text. 16:9.

### UIAO-INT-04 — Co-Management Pivot
**Placement:** Section 2.5 Co-Management Considerations.
**Prompt:** A horizontal slider labeled by two side panels. LEFT (steel gray): SCCM authoritative — a small control knob on that side. RIGHT (teal): Intune authoritative — the knob slides there. Seven workload-family cards sit above the slider, each colored according to which side currently owns it. No text. 16:9.

---

## 18. ARC — Azure Arc Policy Library

### UIAO-ARC-01 — Arc-Enrolled Server
**Placement:** Section 2.2 Arc-Enabled Servers in UIAO.
**Prompt:** A single on-prem server silhouette (no person) with a small cloud tether cable extending up to an Azure resource block. The cable is teal, thin, confident. Around the server: three small policy/tag badges. White background, whitespace-heavy. 16:9.

### UIAO-ARC-02 — Tagging and OrgPath Integration
**Placement:** Section 4 Tagging and OrgPath Policies.
**Prompt:** A horizontal flow showing how OrgPath attributes on AD computer objects become Arc tags on Azure resources. LEFT: AD computer silhouette with three attribute pills. MIDDLE: Entra sync silhouette. RIGHT: Arc resource card with the same three tags now on it. Clean, symmetric, no text. 16:9.

### UIAO-ARC-03 — Policy Initiative Composition
**Placement:** Section 10 Policy Initiative (Policy Set) Definitions.
**Prompt:** A bundle of seven small policy-document tiles arranged in a fan, with a single ribbon wrapping them. The ribbon is teal; the tiles are navy. Above the bundle: a stamp silhouette indicating "initiative." No text. 16:9.

### UIAO-ARC-04 — Guest Configuration Loop
**Placement:** Section 16 Appendix C Guest Configuration Package Development.
**Prompt:** A circular six-stage loop: author → compile → package → test → publish → assign. Each stage a small icon (pencil, gear, box, microscope, upload arrow, target). Central hub is a teal circle. Whitespace-heavy. 16:9.

---

## 19. COR — Corpus-level

These are images that belong to the overall canon or the website, not a single document.

### UIAO-COR-01 — Canon Topology
**Placement:** Landing page hero / canon index.
**Prompt:** A clean network graph of approximately eighteen small nodes representing the canon documents. Three nodes are slightly larger (capstone, gap analysis, master spec). Edges are thin steel gray. Five cluster bands in the background tint groups (capstone, strategic, platform, assessment, modernization, policy libraries) in very faint color washes. No text. 16:9.

### UIAO-COR-02 — Adapter Doctrine (SSOT + Identity + Security)
**Placement:** Landing page or Adapter Doctrine section.
**Prompt:** A clean triptych. LEFT panel: SSOT — a single teal obelisk with a faint reflection underneath (one source, one truth). MIDDLE panel: Identity — a certificate silhouette with a chain link (object identity only, no person). RIGHT panel: Security — a shield with a subtle perimeter line. Above all three: a thin navy band tying them together. No text. 16:9.

### UIAO-COR-03 — Governance Pipeline
**Placement:** Landing page "How it works."
**Prompt:** A horizontal pipeline of six stages rendered as connected rectangular segments: assess → validate → commit → review → deploy → monitor. Each stage a different palette tone fading from navy to teal. Above the pipeline: a small Gitea hex sits centered, with a thin dashed line to every stage suggesting Gitea as the backbone. No text. 16:9.

### UIAO-COR-04 — Boundary Map
**Placement:** Landing page "Scope."
**Prompt:** A nested set of three labeled-by-color-only ring bands. Innermost teal: GCC-Moderate (in scope). Middle steel gray: GCC-High / DoD IL (out of scope, noted). Outermost amber: Commercial Cloud (only Amazon Connect and Azure Arc exceptions, visible as two small tiles inside the outer ring). White background. No text. 16:9.

### UIAO-COR-05 — Drift and Evidence Example
**Placement:** Landing page "Evidence & provenance."
**Prompt:** A four-panel comic-strip-free sequence arranged horizontally. Panel 1: a config tile with a small amber glow (drift detected). Panel 2: a Gitea commit dot (drift logged). Panel 3: an issue-tracker card being filed. Panel 4: a clean green check with a signed seal (remediation closed). Each panel is minimalist, symbol-only. No text. 16:9.

### UIAO-COR-06 — Consume vs. Build Bookshelf
**Placement:** Governance page or README hero for contributors.
**Prompt:** A flat bookshelf in navy with nine identical book spines. Five spines on the left in muted steel gray (CONSUME — external tool outputs). Four spines on the right in teal (BUILD — UIAO native). Each spine has a small icon hint at the top. No text on the spines. White background. 16:9.

---

## 20. Rendering workflow

For any image generator:

1. Copy the **Prompt** text block verbatim.
2. Append the global style contract from §1 if the generator did not absorb it from context.
3. Request the highest available resolution; downscale locally if needed.
4. Save to `diagrams/<UIAO-ID>.png` in the repo. If the generator produces multiple candidates, retain the approved one as `.png` and the rejects as `.draft.png` under a gitignored path.
5. Record the source (generator, model/version, seed if available) in `diagrams/README.md` next to the ID. This is the provenance the UIAO governance posture requires.

A minimal PowerShell helper (`tools/image_render.ps1`) is recommended that accepts an image ID and writes the associated prompt to STDOUT, so an operator can `. tools/image_render.ps1 UIAO-MPP-D001 | pbcopy` and paste into a generator.

---

## 21. Revision log

| Rev  | Date       | Change                                                                 |
|------|------------|------------------------------------------------------------------------|
| v1.0 | 2026-04-12 | Doc 01 Executive Brief — 8 images. (Original upload, preserved in §3.) |
| v2.0 | 2026-04-21 | Expanded to 77 images across full canon + corpus level.                |

---

*This file is a UIAO Canon artifact. Every image added must carry a unique ID, must obey §1, and must be recorded in the revision log.*
