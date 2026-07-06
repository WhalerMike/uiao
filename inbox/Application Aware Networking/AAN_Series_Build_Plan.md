# AAN Series Build Plan — Necessity Doctrine, Series Expansion to 18, and Cross-Book Sharpening

> Status: DRAFT for author review · Surface: `inbox/` (not canon)
> Scope: `inbox/Application Aware Networking/` book series + `federal-aan-conmon-gap-roadmap.md`

## 1. Objective

Restructure and sharpen the Federal Application-Aware Networking series so that it
carries five doctrine themes consistently across every book, and expand the series
with two new early-position books (NAC; Certificates/Tokens), growing the series
from 17 documents (Books 00–16) to 19 documents (Books 00–18).

The unifying editorial thesis: **TIC 3.0, SD-WAN, and IPAM/DDI are not preferred
technologies — they are the only closure mechanisms for a specific, enumerable set
of NIST SP 800-53 Rev 5 controls and FedRAMP 20x KSIs.** Every book states this as
demonstration, not advocacy: control text + physics + protocol behavior, with a
"no alternate path" argument per control.

## 2. The Five Doctrine Themes

Each theme gets a named, reusable editorial device so it appears consistently
across books without repetition drift.

### Theme A — Closure Necessity ("Required, Not Preferred")

For every control/KSI a book claims to close, the book must show three columns:
*without* the technology, *with* it, and **why no alternate mechanism exists**
(control text, physics, or protocol behavior). The recurring device is a callout
block used in every book:

> **Closure Necessity — SC-8 on DIA circuits.** A DIA circuit carries traffic
> unencrypted at the network layer. Application-layer TLS provides no
> network-layer guarantee and no coverage for non-TLS flows. The only mechanism
> that encrypts *all* traffic on a DIA path regardless of application behavior is
> an IPsec overlay — i.e., SD-WAN. There is no configuration setting, scanner
> finding, or policy document that closes SC-8 on a bare pipe.

The three necessity anchors:

| Required technology | Controls with no alternate closure path | Why no alternative |
|---|---|---|
| **IPAM/DDI** (authoritative naming + addressing plane) | SC-20, SC-20(1), SC-21, SC-22 (DNS authority/resolution); CM-8 (authoritative component inventory keyed to addresses); IA-3 device-to-address binding | You cannot attest authoritative name resolution without an authoritative resolver, and you cannot inventory what you cannot enumerate. No scanner creates a source of truth; it can only measure drift from one. |
| **SD-WAN** (encrypted, application-aware overlay) | SC-8/SC-8(1) on DIA; SC-5 (traffic-class separation); SI-4 (application-layer telemetry on transport); CA-7 transport evidence | A pipe has no encryption, no path intelligence, no telemetry. Physics gives DIA lower latency; only the overlay gives it a control surface. |
| **TIC 3.0** (distributed policy enforcement for the pipes) | SC-7, SC-7(7) boundary protection on distributed egress; AC-4 information-flow enforcement outside the TIC access point | Under TIC 3.0, DIA is *permissible only when* the security-capabilities catalog is satisfied at the distributed PEP (SASE stack). An ungoverned DIA circuit is not a modernization — it is a compliance finding. |

### Theme B — "DIA Fixes Nothing" (Physics + Policy)

The boss-proof version of the argument, stated once in Book 00 and echoed where
DIA appears (Books 04, 05, 08, 13 in new numbering):

1. **What DIA solves:** exactly one thing — the geographic hairpin. G.114's 150ms
   one-way budget is a physics constraint; local breakout is the only fix.
2. **What DIA satisfies:** exactly zero NIST controls. DIA is a pipe. Every
   control claimed near it (SC-7, SC-8, AC-4, SI-4, CA-7) is satisfied by the
   SD-WAN/SASE/TIC 3.0 stack that governs the pipe — never by the pipe.
3. **What DIA breaks if deployed bare:** the TIC boundary (SC-7 regression vs.
   the MPLS/TIC 2.0 baseline it replaced). Bare DIA is *worse* than the hairpin
   it fixed, from the assessor's chair.

The speed-of-light propagation floor (Book 08, Network Physics) generalizes the
same argument: no procurement decision repeals physics; architecture is the act
of arranging around what physics permits.

### Theme C — The Load Balancer / Proxy Dissolution

Function-framed (no organizational owners — see Theme E). The classic ADC/proxy
tier does not migrate to any single successor; it **dissolves into three
functional planes**:

| Legacy function | Dissolves into | Functional plane | Series home |
|---|---|---|---|
| Forward proxy / VPN concentrator / SWG appliance | SASE/SSE (SWG, CASB, ZTNA) | Policy enforcement plane | Books 04–05 |
| Hardware ADC / reverse proxy / TLS offload | Cloud-native services (Front Door, App Gateway, ALB/NLB) provisioned in the landing zone | Application delivery plane (landing-zone function) | Book 01 |
| GSLB / global traffic steering | DNS-based traffic management (DTC, Traffic Manager, Route 53 policies) | **Naming & addressing plane — this is a DDI control-plane function** | Book 01 |

Key sentence for the series: *"SD-WAN does not replace the load balancer; it
retires the WAN edge. The load-balancer tier dissolves upward into cloud-native
delivery services and downward into the DNS control plane."* This is technically
precise and pre-empts the easy rebuttal.

### Theme D — Functional Planes, Not Divisions

Confirmed editorial rule (already true — audit found zero org names in the
series): the books describe **functions**, never owners. Book 00 gains an
explicit Functional Plane Model so any reader maps their own org chart onto it:

1. **Transport plane** — circuits, paths, overlay (MPLS → DIA + SD-WAN)
2. **Naming & addressing plane** — DNS, DHCP, IPAM, certificate issuance (DDI + PKI)
3. **Identity plane** — device identity (NAC), workload identity, tokens (OAuth/OIDC, CBA)
4. **Policy enforcement plane** — SASE, ZTNA, TIC 3.0 PEPs, conditional access
5. **Application/experience plane** — contact center, unified communications, business applications
6. **Evidence & telemetry plane** — SIEM/XDR, ConMon, KSI evidence pipeline

Hierarchy rule (already Principle-level in the four-principles figure): **truth
is separated from enforcement**. Planes 2, 3, and 6 are truth planes; planes 1,
4 are enforcement planes; plane 5 consumes both. Enforcement planes can be
re-platformed or absorbed; truth planes can only be depended on.

### Theme E — The Conformance-Tooling Coverage Gap

The series' answer to "SCuBA + Microsoft Zero Trust tooling will close the KSIs":
conformance tooling **measures drift from an intended state; it cannot author
one.** Made quantitative with the roadmap's own numbers:

- ScuBA-based rules: **KSI-001..010 — 10 of 29 active KSI rules.**
- The remaining **19 rules bind to evidence slots that exist only because the
  architecture in Parts 1–15 was built** (identity, network, telemetry,
  endpoint, security, continuity, training slots).

This lands as a coverage table in Book 00 and as the authoritative appendix in
Book 18 (Authorization Package / ConMon).

## 3. Series Restructure — Target Map (00–18)

New Book 02 (NAC) and Book 03 (Certificates & Tokens) insert after the landing
zone book; everything from old Book 02 onward shifts down two. Filenames renumber
to match (figure prefixes like `mf-fig`, `es-fig` are thematic, not numeric, so
figures do not rename).

| New # | Old # | Title | Edit level |
|---|---|---|---|
| 00 | 00 | Executive Summary | **Major** — foundation sections (§4.1) |
| 01 | 01 | Cloud Landing Zone, IPAM/DDI, FedRAMP | Moderate — IPAM necessity + DNS-steering/GSLB section |
| **02** | — | **NEW: Network Access Control — Device Identity at the Port** | New draft (§5.1) |
| **03** | — | **NEW: Certificates & Tokens — Cryptographic Identity** | New draft (§5.2) |
| 04 | 02 | From Mainframe to Application-Aware Modernization | **Major** — DIA physics, LB/proxy dissolution, TIC 3.0 PEP |
| 05 | 03 | Federal Telecommunications Modernization | **Major** — TIC 3.0 use cases; DIA-permissibility argument |
| 06 | 04 | SQL Server Authentication Modernization | Light — necessity callouts; link back to new Book 03 |
| 07 | 05 | SQL Server Implementation Guide | Light — renumber refs |
| 08 | 06 | Database Consolidation and Network Physics | Moderate — speed-of-light floor as general anti-"DIA fixes all" argument |
| 09 | 07 | Privileged Access Management | Light — necessity callouts; NAC cross-ref |
| 10 | 08 | Vulnerability Management | Light — CM-8/IPAM inventory necessity |
| 11 | 09 | Data Protection (Purview) | Light — renumber refs |
| 12 | 10 | SIEM / XDR Detection | Light — telemetry-plane framing |
| 13 | 11 | Business Continuity | Moderate — 11 DIA mentions to align with Theme B |
| 14 | 12 | Supply Chain Risk Management | Light — renumber refs |
| 15 | 13 | Program Management & Governance | Light — renumber refs |
| 16 | 14 | PII Processing & Transparency | Light — renumber refs |
| 17 | 15 | Cybersecurity Training & Awareness | Light — renumber refs; KSI-CED numbering check |
| 18 | 16 | Authorization Package & ConMon | **Major** — KSI Closure Necessity Matrix appendix; 10/29 coverage table; slot-binding updates |

Companion updates: `federal-aan-conmon-gap-roadmap.md` (slot bindings cite Part
numbers — all shift), Book 00 series-map tables, `AAN_Federal_Series_Complete.zip`
(rebuild last), series overview figure `es-fig-01` (four columns → revised track
layout per ADR-093 committed-SVG house style).

## 4. Existing-Document Edit Specs

### 4.1 Book 00 — Executive Summary (keystone edit)

New/expanded sections, in order:

1. **The Functional Plane Model** (new, after the series overview) — the
   six-plane taxonomy + truth-vs-enforcement hierarchy (Theme D). One new SVG
   figure (house style, ADR-093).
2. **The Closure Necessity Doctrine** (new) — the three-anchor table (Theme A)
   with the statement: *these are the only closure paths; the series
   demonstrates this control-by-control.*
3. **"DIA Is a Pipe" elevated to a named sidebar** (Theme B) — currently the
   argument exists at line ~267 but is buried in Part 2's section; promote to a
   first-class exec-summary claim with the three-step (solves / satisfies /
   breaks) structure.
4. **The Dissolution of the ADC Tier** (new, one page) — Theme C table.
5. **Conformance Tooling Coverage Gap** (new) — the 10-of-29 table (Theme E)
   with pointer to Book 18's authoritative matrix.
6. **Series map + sequencing roadmap updates** — 18-book layout; insert Parts
   2–3 (NAC, Cert/Token) into the implementation-sequencing table; refresh
   control-closure totals after new books' control claims are finalized.

### 4.2 Books 01, 04, 05, 08, 13 (moderate/major)

- **Book 01:** Necessity callouts on SC-20/21/22 + CM-8 ("no scanner creates a
  source of truth"); new section *DNS-Based Traffic Steering as a DDI Function*
  (Theme C landing point — GSLB is DNS).
- **Book 04 (old 02):** Extend the existing "load balancers became inline
  proxies" history (line ~89) forward to the dissolution (Theme C); sharpen the
  SD-WAN sections with necessity callouts; add TIC 3.0 as the policy frame that
  makes the SASE PEP mandatory, not optional.
- **Book 05 (old 03):** The TIC 3.0 book. New section mapping TIC 3.0 use cases
  (Branch Office, Remote User) to the security-capabilities catalog, closing the
  loop: *DIA is only lawful under TIC 3.0 with the distributed PEP in place* —
  the formal version of Theme B's policy half. G.114 physics stays as the
  operational driver.
- **Book 08 (old 06):** Generalize the speed-of-light floor into the series'
  physics doctrine: latency budgets are non-negotiable inputs; DIA/local
  breakout is the only latency fix, and it is *only* a latency fix.
- **Book 13 (old 11):** Reconcile 11 DIA mentions with Theme B language; BC/DR
  path diversity claims should cite SD-WAN multipath, not bare circuits.

### 4.3 All remaining books (light)

- Renumber: title block, cross-references, "Part N" mentions, inter-book links.
- Add one **Closure Necessity** callout per book at its primary control-closure
  table, citing whichever of the three anchors (IPAM / SD-WAN / TIC 3.0) its
  controls depend on — or explicitly none, where honest (e.g., Book 15 PM
  governance closes via artifacts, not network technology; saying so preserves
  credibility of the necessity claims elsewhere).

### 4.4 Book 18 (old 16) + gap roadmap

- **KSI Closure Necessity Matrix** (authoritative appendix): every active KSI
  rule → closing technology → conformance-tool-attestable? (Y/N) → evidence slot
  → series Part. The 10/29 split becomes a first-class, citable table.
- Update all slot bindings and Part references for the renumbering.
- Roadmap: add a "coverage gap" preamble making Theme E explicit; re-point slot
  bindings (slot-01 identity gains new Book 03; slot-03 network gains new Book 02).

## 5. New Documents

### 5.1 Book 02 — Network Access Control: Device Identity at the Port

Working outline:

1. The unmanaged-device problem — you cannot Zero-Trust what you cannot identify
2. The Voice VLAN precedent — DHCP option-based device steering as proto-NAC
   (the earliest production case of the naming/addressing plane asserting device
   identity; function-framed, no org history)
3. 802.1X, MAB, and device certificates — port-level authentication
4. DHCP fingerprinting and IPAM as the device source of truth (CM-8 necessity —
   Theme A anchor 1)
5. NAC → ZTNA continuum — posture at the port evolves into posture in the token
6. Control closure: IA-3 (device identification & authentication), AC-19,
   CM-8, SC-7 segmentation prerequisites
7. Closure Necessity callouts + KSI bindings (slot-03 network, slot-05 endpoint)

### 5.2 Book 03 — Certificates & Tokens: Cryptographic Identity

Working outline:

1. Why session-based, location-bound auth died — Kerberos on multipath (imports
   the mf-fig-10 argument as its foundation; deep-links Book 04)
2. PKI as a naming-plane function — issuance, CRL/OCSP, and DNS (CAA, ACME
   DNS-01) are the same substrate
3. Certificate lifecycle automation — ACME, short-lived certs, the death of the
   spreadsheet CA
4. Token-based identity — OAuth 2.0/OIDC, certificate-based authentication,
   phishing-resistant MFA (BOD 25-01 alignment)
5. Machine and workload identity — service principals, managed identities,
   SPIFFE-shaped future
6. Control closure: IA-5(2), SC-12, SC-17, IA-2(1)/(2), plus the enabling role
   for Books 06–07 (SQL auth modernization becomes an *application* of this book)
7. Closure Necessity callouts + KSI bindings (slot-01 identity)

### 5.3 KSI Closure Necessity Matrix

Single citable artifact (lives as Book 18 appendix; optionally also extracted as
a standalone one-pager for circulation). Columns: KSI rule · rule family · closing
technology · attestable by conformance tooling alone (Y/N) · evidence slot ·
series Part. Bottom line pre-computed: 10 Y / 19 N.

## 6. Execution Phases

| Phase | Work | Output | Gate |
|---|---|---|---|
| **0** | This plan reviewed; slotting of new Books 02/03 confirmed; edit levels agreed | Approved plan | Author sign-off |
| **1** | Mechanical renumber: rename 15 files (old 02–16 → 04–18), update every cross-reference, title block, and "Part N" mention; update roadmap slot bindings | Renumbered series, zero content change | Link-check clean; grep audit for stale "Book/Part" numbers |
| **2** | Book 00 keystone edit (§4.1) — establishes the named devices and vocabulary every other edit reuses | Book 00 v2 | Author review of doctrine language |
| **3** | New Book 02 (NAC) and Book 03 (Cert/Token) full drafts (§5.1–5.2) | Two new books + control-closure tables | Author review; control claims verified against Rev 5 text |
| **4** | Moderate/major edits: Books 01, 04, 05, 08, 13 (§4.2) | Sharpened transport/physics/TIC spine | Necessity callouts consistent with Book 00 vocabulary |
| **5** | Light passes: Books 06–07, 09–12, 14–17 (§4.3); Book 18 + roadmap + Necessity Matrix (§4.4) | Full-series consistency; authoritative matrix | KSI counts reconcile: Book 00 = Book 18 = roadmap |
| **6** | Derived artifacts: regenerate .docx/.html from .qmd; redraw es-fig-01 series figure (committed SVG per ADR-093); rebuild `AAN_Federal_Series_Complete.zip`; note training-program modules (`docs/publications/aan-training-program/`) as downstream regeneration | Publishable series v2 | Render clean; fig-alt text updated |

Phases 2–5 are content; each lands as its own commit (or commit series) on this
branch so review is per-phase, not one monolith.

## 7. Consistency Rules (apply to every edit)

1. **No organizational names.** Functions and planes only (Theme D). The audit
   baseline is zero org references; keep it zero.
2. **Every necessity claim is falsifiable.** "Required" always pairs with the
   mechanism that makes alternatives impossible (control text, physics, or
   protocol behavior) — never with adjectives.
3. **Technology leads; conclusions follow.** No book tells the reader who should
   run anything. The chips fall where the control-closure tables put them.
4. **Numbers reconcile.** Control-closure totals and KSI counts must match
   across Book 00, Book 18, and the roadmap in every commit that touches them.
5. **Diagrams per ADR-093.** New figures are committed house-style SVG; PNG is a
   build artifact; no new Mermaid blocks.

## 8. Open Items for Author Decision

1. Confirm insertion points: NAC as Book 02 and Cert/Token as Book 03 (this plan
   assumes both; "maybe" was attached to Cert/Token — if deferred, NAC-only
   yields an 17-book series ending at Book 17 and the renumber map shifts by one).
2. Necessity Matrix: Book 18 appendix only, or also a standalone circulation
   one-pager?
3. Confirm the .docx/.html regeneration path (quarto render profile vs. existing
   pipeline) before Phase 6.
