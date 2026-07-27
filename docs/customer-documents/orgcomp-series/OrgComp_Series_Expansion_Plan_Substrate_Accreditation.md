# OrgComp Series Expansion Plan — The Accreditation Substrate (Multi-CSP Patch/Management + Network Enforcement)

> Status: DRAFT for author review · Surface: `inbox/` (not canon)
> Scope: `docs/customer-documents/orgcomp-series/` book series
> Companion to: `OrgComp_Series_Build_Plan.md` (the 00–19 restructure this builds on)
> Constraint: **Book 11 (Vulnerability Management) is under active edit.** No
> phase in this plan renames or renumbers Book 11 until its in-flight edit
> lands (see Phase 3 gate).

## 1. Objective

Close two coverage gaps the series carries today, and grow the series to hold
them properly — adding books and reordering the existing sequence so the new
material sits domain-adjacent to what it depends on.

**Gap 1 — CSP-native patch & systems-management stacks.** Book 11 demonstrates
flaw remediation *only on the Microsoft/Azure estate* (Defender/MDVM, Arc,
Intune WUfB, Azure Update Manager, SQL CU). It even names a *"one mechanism,
several tools"* doctrine but never leaves Azure. AWS, Oracle (OCI), and VMware
each run their own patch/management stacks, each spanning Windows, Linux, and
SaaS with a different shared-responsibility line. The series does not cover
them.

**Gap 2 — Network Equipment Manufacturers.** Book 05 has a strong *Cisco
Catalyst SD-WAN + M365 INR* appendix — but it is Cisco-only and SD-WAN-only.
Palo Alto and Juniper appear nowhere of substance; Cisco's own NAC/firewall/
segmentation lines are absent. And the federal accreditation path for network
gear — **NIAP Common Criteria, DISA STIG, FIPS 140-3, DoDIN APL** — is never
systematized, so the series never explains *how gear closes NIST controls*
(which is a different gate from FedRAMP).

Both gaps are the same missing idea, which is why one theme and a small book
cluster cover both.

## 2. New Doctrine Theme F — The Accreditation Substrate

Add to the five themes in `OrgComp_Series_Build_Plan.md §2`.

> **Theme F — The Accreditation Substrate.** Every control the series closes is
> closed by a *mechanism*, and every mechanism ships inside a *product* that
> carries a *federal accreditation*. The gate differs by what the product is:
>
> - **CSP services → FedRAMP** (Moderate, per the series scope parameter).
> - **Network / endpoint gear → NIAP CC evaluation + DISA STIG-hardened
>   configuration + FIPS 140-3 validated module + DoDIN APL listing.**
>
> The **shared-responsibility line** decides who owns which mechanism: the CSP
> patches the platform below the line; the customer patches the OS and runs the
> edge gear above it. "Required, not preferred" (Theme A) names the mechanism;
> Theme F names the product that realizes it and the accreditation that lets a
> federal program buy it.

This preserves the series' *Mechanism, Not Product* rule: one mechanism,
realized by N products, each accredited by the same gate but differing by
**{CSP × OS × service-model}** (Gap 1) or **{vendor × appliance-class}**
(Gap 2). The book bodies stay function-first; the vendor matrix is the
*realization* layer, exactly as Book 05 already names Cisco and Book 01 names
InfoBlox.

## 3. New Books

### 3.1 Book — Patch & Systems Management: The SI-2 / CM Closure Plane (multi-CSP)

Splits the remediation half out of Vulnerability Management. Vuln Management
keeps the **assessment** half (RA-5, KEV cross-reference, MDVM — *what is
unpatched*); this book owns **remediation actuation and configuration state**
(SI-2, SI-2(2), CM-2/CM-6 baselines, CM-8 inventory binding — *close it, and
keep it closed*). Clean scan→remediate handoff, cross-referenced both ways.

Core artifact — the **{CSP × OS × service-model} → SI-2 mechanism** matrix:

| | Windows | Linux | macOS / mobile | Appliance / firmware | SaaS layer |
|---|---|---|---|---|---|
| **Microsoft** | WUfB / Autopatch; MECM/WSUS (legacy) | Azure Update Manager (+ Arc for hybrid) | Intune | — | CSP-managed (M365) |
| **AWS** | SSM Patch Manager | SSM Patch Manager (AL2/RHEL/Ubuntu/SUSE) | — | EC2 Image Builder (golden AMI) | CSP-managed (RDS / Lambda) |
| **Oracle (OCI)** | OS Management Hub | OS Management Hub; **Ksplice** (zero-downtime kernel) | — | — | Autonomous DB self-patching |
| **VMware (Broadcom)** | Workspace ONE (UEM) | Workspace ONE | Workspace ONE | vSphere Lifecycle Manager (ESXi + firmware) | — |
| **Cross-CSP overlay** | Tanium / BigFix / Ivanti / Red Hat Satellite / SUSE Manager — OS-agnostic, runs on any of the above | | | | |

Working outline:

1. The shared-responsibility line as the SI-2 scoping rule — who patches what,
   per IaaS / PaaS / SaaS, per CSP. The line moves; the control does not.
2. Scanner ≠ remediation (Theme E applied): assessment tools *measure* the gap,
   the patch stack *closes* it. Hand-off contract to Book (Vuln Management).
3. Per-CSP native stack, worked: Microsoft (reference implementation, imported
   from current Book 11 depth), AWS Systems Manager, OCI OS Management Hub +
   Ksplice, VMware vLCM + Workspace ONE.
4. The OS dimension: Windows vs. Linux vs. macOS vs. appliance firmware — the
   mechanism is constant, the delivery tool and cadence are not.
5. Configuration state, not just patch level — CM-2/CM-6 baselines, drift
   detection, State Manager / Automanage / Aria as the CM control surface.
6. The cross-CSP overlay decision — when a single third-party plane (Tanium/
   BigFix/Ivanti) is the right answer vs. native per-cloud stacks.
7. Accreditation substrate (Theme F): each stack's FedRAMP status and the
   authorization-boundary implication of a hybrid Arc/SSM agent reaching in.
8. Control closure: SI-2, SI-2(2), SI-2(3), CM-2, CM-6, CM-8, RA-5 hand-off;
   KSI bindings (KSI-CM, KSI-MLA, KSI-SVC).

### 3.2 Book — Network Enforcement Substrate: Cisco, Palo Alto, Juniper and the NIAP/STIG/FIPS Path

The customer-edge enforcement layer CSP-native controls do not reach. Function
→ vendor realization → accreditation gate.

| Function / control | Cisco | Palo Alto | Juniper |
|---|---|---|---|
| Boundary protection (SC-7, AC-4) | Secure Firewall / Firepower | NGFW / PAN-OS + Panorama | SRX / Junos + Security Director |
| Encrypted overlay (SC-8, SC-8(1)) | Catalyst SD-WAN (Viptela) | Prisma SD-WAN | Session Smart Router (128T) |
| Distributed PEP / TIC 3.0 (SC-7, SC-7(8), AC-4) | Umbrella / Secure Access | Prisma Access (SASE) | — |
| Device identity / NAC (IA-3, AC-19, CM-8) | ISE, TrustSec | — | Mist Access Assurance |
| Config-as-truth (CM-2, CM-6) | — | — | Apstra (intent-based DC) |
| Telemetry / detection (SI-4, AU-6) | Secure Network Analytics, XDR | Cortex XDR / XSIAM | — |
| Remote access (AC-17) | AnyConnect / Secure Client | GlobalProtect | — |

Working outline:

1. Why the enforcement substrate is customer-owned — SC-7/SC-8 at the DIA edge
   and branch CPE is above the CSP's shared-responsibility line. FedRAMP
   inheritance stops at the cloud boundary; the gear on-prem is yours to accredit.
2. The accreditation gate for gear (Theme F, formalized): NIAP CC evaluation
   (Protection Profiles for Network Devices / Firewalls), DISA STIG-hardened
   config, FIPS 140-3 validated crypto module, DoDIN APL listing — what each
   gate certifies and where they compose.
3. Per-vendor realization, function by function (the matrix above, worked with
   the NIST control each row closes and the STIG that hardens it).
4. The interoperability seams — 802.1X supplicant/authenticator across vendors;
   MACsec (SC-8) hop-by-hop; RADIUS/TACACS+ to the identity plane (Book 02/03).
5. Vendor-neutral vs. vendor-locked decisions — where intent-based config
   (Apstra) or SASE (Prisma) changes the boundary picture.
6. Control closure: SC-7, SC-7(8), SC-8, SC-8(1), AC-4, IA-3, AC-19, SI-4,
   AC-17; KSI bindings (slot-03 network, slot-05 endpoint, slot-04 telemetry).

### 3.3 Optional third book — Multi-Cloud Platform Realization (flag, do not draft yet)

If Gap 1's per-CSP work reveals that patch/management is only one of several
places the series' Azure-centricity leaves AWS/OCI/VMware readers stranded
(landing-zone, IAM, logging planes realized per-cloud), a dedicated
platform-realization book may be warranted. **Recommendation: defer** — draft
the two books above first; decide on this one from what they surface. Named
here only so the series map has a reserved intent.

## 4. Target Reorder Map

New books sit domain-adjacent: the network-enforcement book joins the network
cluster (after Telecom); the patch book joins the security-operations cluster
(right after Vulnerability Management). Result: **22 documents, 00–21.**

| New # | Old # | Title | Change |
|---|---|---|---|
| 00 | 00 | Executive Summary | edit: add Theme F + management plane |
| 01 | 01 | Cloud Landing Zone, IPAM/DDI, FedRAMP | — |
| 02 | 02 | Network Access Control (802.1X) | cross-ref new 07 |
| 03 | 03 | Certificates & Tokens (Cryptographic Identity) | — |
| 04 | 04 | HRIT Identity Org SSOT | — |
| 05 | 05 | Network Modernization | edit: point Cisco appendix at new 07 |
| 06 | 06 | Federal Telecommunications Modernization | — |
| **07** | — | **NEW: Network Enforcement Substrate (Cisco/PA/Juniper)** | new draft |
| 08 | 07 | SQL Server Authentication Modernization | renumber |
| 09 | 08 | SQL Server Implementation Guide | renumber |
| 10 | 09 | Database Consolidation & Network Physics | renumber |
| 11 | 10 | Privileged Access Management | renumber |
| 12 | 11 | **Vulnerability Management** (assessment half) | renumber **only after active edit lands** |
| **13** | — | **NEW: Patch & Systems Management (SI-2/CM, multi-CSP)** | new draft |
| 14 | 12 | Data Protection (Purview) | renumber |
| 15 | 13 | SIEM / XDR Detection | renumber |
| 16 | 14 | Business Continuity | renumber |
| 17 | 15 | Supply Chain Risk Management | edit: NEM supply chain (§889/TAA/HW RoT) |
| 18 | 16 | Program Management & Governance | renumber |
| 19 | 17 | PII Processing & Transparency | renumber |
| 20 | 18 | Cybersecurity Training & Awareness | renumber |
| 21 | 19 | Authorization Package & ConMon | edit: NIAP/STIG evidence slots |

## 5. Targeted Edits to Existing Books

- **Book 00** — add the *Compute & Systems-Management plane* to the Functional
  Plane Model (Theme D gains a plane) and introduce Theme F with the two-gate
  (FedRAMP vs. NIAP/STIG/FIPS/APL) table.
- **Book 11 → 12 (Vuln Management)** — once its active edit lands, carve the
  scan-vs-remediate boundary explicitly and hand SI-2 actuation to new Book 13;
  its Microsoft depth stays as the reference implementation, cited from 13.
- **Books 05 / 06** — keep the Cisco INR appendix; replace its "Cisco-only"
  framing with a pointer into new Book 07 and add Palo Alto / Juniper
  equivalents as cross-refs (do not turn the function-framed body into a
  vendor bake-off).
- **Book 15 → 17 (SCRM)** — add the NEM supply-chain gate currently missing:
  NDAA §889 (covered-equipment exclusions), TAA, hardware root-of-trust /
  secure boot as SR-family closure for gear.
- **Book 19 → 21 (Authorization / ConMon)** — add NIAP-CC / DISA-STIG evidence
  slots distinct from FedRAMP inheritance; a control closed by on-prem gear is
  attested differently than one inherited from a CSP.

## 6. Execution Phases — sequenced around the active Book 11 edit

| Phase | Work | Gate |
|---|---|---|
| **0** | This plan reviewed; new-book slotting + reorder map confirmed | Author sign-off |
| **1** | Draft both new books at **temporary append slots 20/21** — zero renumber, zero collision with the live Book 11 edit. Content is the value; get it written and reviewed. Cross-references use **titles/filename stems, not numbers**, so they survive the later renumber. | Author review; control claims verified vs. Rev 5 text; matrices sourced per authoring-spec §3 vendor rule |
| **2** | Theme F + Book 00 keystone edit (management plane + two-gate table). | Doctrine language consistent with existing themes |
| **3** | **After Book 11's active edit lands:** execute the mechanical renumber/reorder to §4's target map in one commit — rename files, fix every cross-reference and "Book N" mention, roadmap slot bindings, Book 00 series-map tables. This is where temp slots 20/21 move to 07 and 13. | Book 11 stable; link-check clean; grep audit for stale numbers |
| **4** | Targeted edits: Books 05/06 (cross-ref 07), 17 SCRM (§889/TAA), 21 ConMon (NIAP/STIG slots). | Necessity + Theme F callouts consistent |
| **5** | Derived artifacts: re-render .docx/.html from .qmd; redraw `es-fig-01` series figure (committed SVG per ADR-093); rebuild the datecoded kit `OrgComp_Federal_Series_Complete_<DATE>ET.zip` locally (docx + .pptx decks + governance docx). | Render clean; fig-alt updated; date codes bumped |

Rationale for the temp-slot detour in Phase 1: renumbering *now* would rename
the actively-edited Book 11 mid-flight and guarantee a merge collision. Drafting
at 20/21 lets the new content proceed in parallel; the single renumber in
Phase 3 happens once, after the live edit is done.

## 7. Consistency Rules (carried from the build plan)

1. **Mechanism, not product.** The book body states the mechanism; the vendor
   matrix is the realization layer. No book tells the reader which vendor to buy.
2. **Every necessity claim is falsifiable** — control text, physics, or protocol
   behavior, never adjectives.
3. **Vendor claims are sourced** (authoring-spec §3): every FedRAMP / NIAP /
   STIG / FIPS / APL assertion carries a link to the vendor doc, the FedRAMP
   Marketplace, the NIAP Product Compliant List, or the DoDIN APL.
4. **FedRAMP Moderate only** (authoring-spec §2) — never cite High; gear claims
   state the actual NIAP PP / FIPS level / APL status verified at procurement.
5. **Diagrams per ADR-093** — committed white-background house-style SVG; no new
   Mermaid; PNG is a build artifact.
6. **Cross-refs by title until Phase 3** — no hard "Book NN" numbers in the new
   drafts until the renumber lands.

## 8. Open Items for Author Decision

1. **VMware scope** — full inclusion in the patch matrix, or note-and-defer
   given Broadcom licensing turmoil and its uncertain federal uptake? (Plan
   currently includes it fully.)
2. **Third book (§3.3)** — reserve the slot, or drop the idea? (Plan defers.)
3. **Oracle depth** — OCI OS Management Hub + Ksplice as a full worked section,
   or a shorter treatment than AWS/Microsoft given smaller federal footprint?
4. **Network book vendor set** — Cisco/PA/Juniper as specified; add Fortinet or
   Arista, or hold to the three you named?

---

# Part II — Series-Wide Compliance Rebuild (added after Book 11 landed)

This part scales the plan from "two new books + edits" to a **comprehensive,
series-wide compliance update** (Book 00 → as many as necessary), so the series
reads as a complete compliance reference to NIST, FedRAMP 20x, CISA, EO, and
OMB direction — authored agnostic-first so an SSA-specific and a
Federal-agnostic edition render from one source.

## 9. The Management-Plane Coordination Doctrine

The series' governing answer to *"will everything be Microsoft (Intune / Azure
Arc), or native Cloud / RedHat / VMware systems coordinated — and how?"*

**Split the management plane in two.**

1. **Actuation is platform-native and non-negotiable.** Each platform patches
   and configures with the stack its own support model requires:

   | Platform | Guest OS actuation | Platform / appliance actuation |
   |---|---|---|
   | Microsoft | Intune (WUfB/Autopatch), Azure Update Manager (+Arc for hybrid) | — (SaaS CSP-managed) |
   | AWS | SSM Patch Manager / State Manager | EC2 Image Builder (golden AMI); RDS CSP-managed |
   | Oracle (OCI) | OS Management Hub; **Ksplice** (zero-downtime kernel) | Autonomous DB self-patching |
   | VMware | Workspace ONE (endpoints) | **vSphere Lifecycle Manager** (ESXi + firmware) |
   | Red Hat | Satellite (content/patch), Ansible Automation Platform (actuation), Insights (advisories/drift) | — |

   **No overlay repeals a vendor's support boundary.** Azure Arc governs the
   *guest OS* across clouds and on-prem — it does not patch ESXi, firmware, or a
   managed DB service. A Microsoft-monoculture claim fails at the first
   hypervisor or appliance. Arc is *one* actuation-and-visibility tool inside
   the plane, not the plane.

2. **Governance and evidence are unified — coordination lives here, as a
   contract, not a tool.** Every native stack must emit the same
   machine-readable compliance record — patch state, baseline conformance,
   last-scan, SLA class — into one evidence lake (Sentinel / Log Analytics) and
   up into **CISA CDM** and the FedRAMP 20x KSI evidence pipeline. Any stack
   that satisfies the contract is admissible; the series mandates the *contract*,
   never a single vendor.

**The join key is authoritative asset identity (the naming plane).** You cannot
correlate AWS + Azure + VMware + Red Hat inventory into one compliance picture
unless every asset carries one authoritative name/address (IPAM/DDI, CM-8). So
multi-stack coordination is a **Closure Necessity (Theme A) argument for the
naming plane**, and it is federally mandated by **CISA BOD 23-01** (enterprise
asset visibility + vulnerability enumeration across exactly this heterogeneity).

Doctrine mapping (Theme D): **actuation = enforcement plane** (per-vendor,
re-platformable); **evidence/governance = truth plane** (must be unified).
Book 11 is the reference implementation of the evidence contract; new Book 13
(Patch & Systems Management) generalizes it and defines the contract itself.

## 10. The Compliance Spine — complete authority coverage

The series carries **one generated compliance spine**, not 22 hand-authored
crosswalks. A single data artifact (`orgcomp-compliance-spine.yml`) with rows:

> **authority · requirement id · requirement text · closing mechanism · series
> book · evidence slot · FedRAMP 20x KSI · attestable-by-tooling (Y/N)**

renders the per-book control-closure tables and Book 21's authoritative matrix,
and is drift-gated (a book table that diverges from the spine fails CI — same
pattern as the status/index/sitemap generators).

Authority set the spine must cover completely:

| Family | Instruments |
|---|---|
| **NIST** | SP 800-53 Rev 5 (+800-53B Moderate baseline), 800-207 (Zero Trust), 800-137 (ISCM), 800-37 (RMF), CSF 2.0, 800-171/172 (CUI), 800-63 (digital identity), 800-218 (SSDF), 800-122 (PII) |
| **FedRAMP 20x** | KSIs (the assertion/attestation layer over the NIST closure) |
| **CISA** | BOD 22-01 (KEV), **BOD 23-01 (asset visibility & vuln enumeration)**, BOD 18-01, ZTMM v2, SCuBA, TIC 3.0, CDM |
| **EO / OMB** | EO 14028 → M-22-09 (Federal ZT Strategy), M-21-31 (event logging), M-22-18 / M-23-16 + SSDF attestation (software supply chain), OMB A-130, M-24-04 (FY24 FISMA) |
| **Statute** | FISMA; Privacy Act (PII book) |

Every book gains a short **"Authorities Closed Here"** header table generated
from the spine, and Book 00 carries the master crosswalk + a completeness
assertion (every authority row maps to at least one book + evidence slot).

## 11. SSA-Specific vs Federal-Agnostic — SSA-first, split later

> **Author decision (locked):** SSA-first now; extract a Federal-agnostic
> edition in a later pass. The Quarto-profile / variable-layer machinery below
> is **deferred** — do not build it in Phase B. Author SSA-specific content
> directly. **Ease the later split** by not embedding SSA facts mid-sentence
> where a section boundary or a callout would isolate them just as well; no hard
> parameterization required yet.

Deferred design (for the later agnostic-extraction pass):
Author **agnostic body + SSA as a parameter layer**:

- **Agnostic** (constant): control-closure logic, the coordination doctrine,
  necessity arguments, the substrate/accreditation matrices, mechanism physics.
- **SSA-specific** (isolated into `_variables-ssa.yml` + includes): GCC Moderate
  boundary, DIA circuits, named CSOs (e.g., InfoBlox BloxOne), CIO/OIS-office
  references, org-boundary specifics.

Render both editions from one source via Quarto **profiles**
(`--profile ssa` / `--profile federal`). Retrofitting separability after a
22-book rewrite is expensive; doing it *during* the rewrite is nearly free.
Consistency rule: no SSA-specific fact appears in agnostic body text — it lives
only behind a variable or an `{{< include >}}`.

## 12. Series-Wide Execution (supersedes §6 for the comprehensive pass)

Dependency order — Book 00 defines vocabulary every other book inherits, so it
and the spine come first; propagation follows.

| Phase | Work | Gate |
|---|---|---|
| **A** | Lock the three doctrines: coordination model (§9), spine architecture (§10), separability (§11). | Author decisions (see §13) |
| **B** | Build `orgcomp-compliance-spine.yml` + the generator + drift gate; stand up the SSA/agnostic variable layer + Quarto profiles. | Spine renders; both profiles build clean |
| **C** | **Book 00 keystone rewrite** — coordination doctrine, Theme F, full authority set, master crosswalk + completeness assertion, management plane added to the plane model, separability note. | Author review of doctrine language |
| **D** | New Books 07 (Network Enforcement) + 13 (Patch & Systems Mgmt) drafted at temp slots 20/21 (per §6 Phase 1 — no renumber while Book 11 settles). | Control claims verified; matrices sourced |
| **E** | Reframe/expand **Book 11** (Vuln Mgmt) to the assessment half + evidence-contract emitter; align to the coordination doctrine. | Scan/remediate boundary clean vs Book 13 |
| **F** | Propagate the compliance spine + coordination callouts to **every remaining book** — one book per unit of work; each regenerates its "Authorities Closed Here" table from the spine. *(Candidate for a parallel multi-agent pass — one agent per book — if the author opts in.)* | Spine drift-gate green across all books; KSI counts reconcile Book 00 = Book 21 = roadmap |
| **G** | Renumber/reorder to §4 target map (after Book 11 stable); regenerate derived artifacts; rebuild datecoded kit; render both editions. | Link-check clean; both profiles render; date codes bumped |

## 13. Decisions — LOCKED (author sign-off, this session)

1. **Coordination model** — ✅ **Coordinated-native + unified evidence contract**
   (§9). Actuation platform-native; governance/evidence unified via the
   IPAM-keyed evidence contract → Sentinel + CDM + KSI. Arc is one tool, not the
   plane.
2. **Compliance spine** — ✅ **Generated data artifact + drift gate** (§10).
   `orgcomp-compliance-spine.yml` renders every book's tables; CI fails on drift.
3. **Separability** — ✅ **SSA-first now, split later** (§11). No profile
   machinery in Phase B; author SSA-specific directly; keep facts isolable.
4. **Propagation (Phase F)** — ✅ **Sequential, author-in-the-loop** — one book
   per unit of work; author reviews each. No parallel workflow.

Phase B is therefore trimmed: build the spine + generator + drift gate; **skip**
the Quarto profile/variable layer. Phase C (Book 00 keystone) proceeds next.

## 14. Post-Extension Scope Audit — Newly Exposed Gaps (2026-07-08)

A grep-based completeness scan after adding multi-CSP + NEM coverage found the
series still Microsoft-monoculture exactly where the coordination doctrine says
it cannot be. Grounded findings:

| Gap | Evidence | Disposition (LOCKED) |
|---|---|---|
| Multi-cloud telemetry ingestion — SIEM book is Sentinel/Defender-only; no AWS Security Hub/GuardDuty, OCI Cloud Guard, or NEM log ingestion into the evidence lake + CDM | Book 13: 124 MS hits, ~0 multi-CSP | **NEW BOOK — Multi-Cloud Evidence Fabric** (`book-evidence-fabric`, Vol III) |
| Cloud-native posture + containers (CSPM/CNAPP, K8s) absent series-wide | 10 CSPM hits total; container/K8s all incidental | **NEW BOOK — Cloud-Native Security Posture & Containers** (`book-cloudnative-posture`, Vol III) |
| Multi-cloud data protection & key mgmt — Purview + Azure Key Vault only | Book 12: 39 key-vault hits, all MS | **Section in Book 12** (AWS KMS, OCI Vault, cross-cloud CMK/HYOK) |
| Multi-cloud privileged access — Entra PIM/PAW only | Book 10: 70 MS, ~0 multi-CSP | **Section in Book 10** (SailPoint ISC, CyberArk, AWS IAM Identity Center, OCI IAM) |
| Multi-cloud BC/DR — Azure Site Recovery only | Book 14: 9 MS, 1 multi-CSP | **Section in Book 14** (AWS Backup, OCI DR) |

Landing zone (Book 01, 106 multi-CSP hits) and telecom (Book 06) are already
multi-cloud — no action. Series grows by **2 books** (now 24 registered) plus 3
multi-CSP sections.

## 15. Series Structure — One Program, Named Volumes (LOCKED)

The series is ONE program with ONE compliance spine (SSOT), presented as named
**volumes**, each independently distributable — "joined, but different series."
Continuous cross-references and the spine stay unified; volume-local numbering
removes the awkward flat-numbering section boundaries.

- **Book 00 (Executive Summary) sits ABOVE the volumes** as the program
  keystone covering all of them (`keystone: book-00` in the spine; not a member
  of any volume).
- **Vol I — Foundation & Transport** — Landing Zone, NAC, Certs/Tokens, HRIT,
  Network Modernization, Telecom, **Network Enforcement Substrate**.
- **Vol II — Data Platform** — SQL auth, SQL implementation, DB/physics.
- **Vol III — Security Operations** — PAM, Vulnerability Mgmt, **Patch & Systems
  Mgmt**, **Cloud-Native Posture**, Data Protection, SIEM/XDR, **Evidence
  Fabric**.
- **Vol IV — Governance & Assurance** — BC, SCRM, Program Mgmt, PII, Training,
  Authorization/ConMon.

The spine's `volumes:` block (book-id order = authoritative reorder sequence)
makes continuous-vs-volume-local numbering a rendering switch, not a rewrite.
Per-book `target_slot` is now indicative only.

## 16. Multi-Surface Coordinators — FedRAMP-Authorized (verified 2026-07-08)

No single product spans CSP + NEM + OS. Coordination is layered by plane; the two
strongest hubs are already owned by the agency. Verify each on the FedRAMP
Marketplace at procurement.

| Plane | Product | FedRAMP | Surfaces | Series home |
|---|---|---|---|---|
| Workflow / CMDB / evidence | **ServiceNow Gov Cloud** *(owned)* | **High** (DoD IL-4) | CSP + NEM + OS | Evidence Fabric book (coordination home) |
| Identity governance | **SailPoint Identity Security Cloud** *(owned)* | **Moderate** (AWS GovCloud) | CSP + SaaS + OS + NEM admin | PAM section; identity books |
| Cross-OS endpoint | **Tanium TC-USG** | **Moderate** (Class C) | OS + Intune connector | Patch & Systems Mgmt overlay |
| Multi-cloud posture | **Wiz for Gov**; **Prisma Cloud** | **High** / **High** | AWS/Azure/GCP/OCI/vSphere/K8s | Cloud-Native Posture book |
| Telemetry → CDM | Sentinel; Splunk Cloud / Google SecOps (verify) | Moderate/High | CSP + NEM + OS logs | Evidence Fabric book |

**Doctrine guardrail:** ServiceNow CMDB **reconciles to** the authoritative
IPAM/DDI asset identity (CM-8 join key) — it does not replace it; SailPoint
governs access **on top of** the HRIT identity SSOT. Coordinators are
enforcement/workflow planes; DDI and HRIT remain truth planes. ServiceNow at
FedRAMP High comfortably covers the series' Moderate boundary (refer to it as
"FedRAMP-authorized" per the scope rule; do not cite High in body text).

Sources: SailPoint ISC FedRAMP Moderate (fedramp.gov/marketplace FR2001938710A);
ServiceNow Gov Cloud FedRAMP High; Tanium TC-USG FedRAMP Moderate
(FR2110342613); Wiz for Gov FedRAMP High; Palo Alto Prisma Cloud FedRAMP High.

## 17. Product Inventory Questionnaire (companion instrument)

`OrgComp_Product_Inventory_Questionnaire.qmd` — a discovery instrument that maps an
agency's **already-deployed** tools onto the OrgComp planes/books, so the plan can
be tailored to what exists rather than executed blind. Structure: scope rule
(§2, SSA = exclusively FedRAMP **Class C / Moderate**, with a flag convention
for High-only / gear / unauthorized), a **pre-filled Known-SSA block** (§3,
removed for the agnostic edition — SSA-first per §11), the plane/volume-
organized discovery tables (§4), and a flags/gaps rollup (§5).

FedRAMP status of named/owned tools **verified 2026-07-08**: SailPoint ISC =
Moderate ✅; ServiceNow Gov = High ⚠️ (covers Moderate; CMDB must reconcile to
IPAM/DDI); Splunk Cloud = Moderate ✅ (+High); **Riverbed** = Aternity/NPM+ High-
only ⚠️ + SteelHead on-prem gear (NIAP path) ⚠️; **Confluence** = Moderate ✅
only via Atlassian Government Cloud (commercial = unauthorized) ⚠️; InfoBlox =
Moderate ✅. New FedRAMP nomenclature (May 4 2026): "FedRAMP Certified", Class
C = Moderate, Class D = High. The agnostic edition strips §3 and relaxes §2 to
"state boundary level, require products at or above it."

## 18. Product-Selection & Diagram Principles (agency guidance, 2026-07-08)

### 18.1 Microsoft-suite preference — earned, not automatic

The agency holds a large Microsoft enterprise agreement, so a Microsoft product
is the **default candidate** for any coordination or control role **when it
genuinely coordinates the multi-vendor surface (CSP + NEM + OS) at FedRAMP
Moderate.** Preference is *earned by demonstrated cross-vendor coordination, not
granted by ownership*:

- **Qualifies:** **Sentinel** (ingests AWS/OCI/NEM telemetry) → default Evidence
  Fabric SIEM, Splunk the Moderate alternative. **Defender for Cloud** (multi-
  cloud CNAPP across AWS/GCP/OCI, GCC Moderate) → default Moderate CNAPP for the
  Cloud-Native Posture book (Prisma Cloud / Wiz are both High). **Azure Arc**
  (cross-cloud guest-OS) → valid but **bounded** — governs guest OS only, never
  ESXi/firmware (coordination doctrine).
- **Does not auto-qualify:** where a Microsoft product coordinates only Microsoft
  surfaces or cannot reach the surface, the best cross-vendor coordinator at
  Moderate wins (Tanium cross-OS actuation; ServiceNow workflow/CMDB hub,
  reconciled to IPAM/DDI).

Refines "Mechanism, Not Product": **ownership sets the default; cross-vendor
coordination capability sets the decision.**

### 18.2 Diagram detail differs by format (docx vs pptx)

Under the standing docx+pptx build rule: the **.docx carries the more detailed
diagram** — the committed SVG SSOT (ADR-093), richer and standalone, readable
without a presenter. The **.pptx carries the simpler build-sequence visual**
(progressive reveal, one idea per step). PPTX→DOCX figure write-back applies
where the slide visual suffices; **complex concepts get a docx-specific detailed
diagram, not just the slide export.** SVG remains the SSOT; both formats derive
from it, at different levels of detail.
