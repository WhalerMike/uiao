# Customer Documents Taxonomy — Working Doc

> **Status:** Working planning doc (not canon). Author: Canon Steward + Claude (Cowork).
> **Created:** 2026-04-23. **Scope:** Structure and migration plan for `docs/customer-documents/`.
> **Location:** `docs/planning/customer-documents-taxonomy.md` — edited in-repo, versioned through Git.

---

## 0. Purpose

Give UIAO a single two-pillar taxonomy — **Modernization** and **Compliance** —
plus a shared **Substrate** spine, so every document in the corpus has
exactly one canonical home and every reader enters the portal with an
unambiguous mental model.

This doc replaces ad-hoc categorisation (the current 8 families) with one
derived directly from what UIAO actually does: it **transforms** Microsoft
Client/Server estates into Hybrid-Cloud (Modernization) and it **governs**
that transformation against federal mandates (Compliance). Everything else
is substrate.

Iteration model: this is a `.md` in the repo. Edit, commit, PR. Once stable,
sections get promoted into actual Quarto landing pages under
`customer-documents/modernization/`, `customer-documents/compliance/`, and
`customer-documents/substrate/` (or kept as a steward-only planning artifact
depending on how §5 resolves).

---

## 1. Two pillars + shared substrate

```
customer-documents/
├── modernization/          ← what transforms, and the machinery that transforms it
│   ├── A platform-substrate/
│   ├── B transformation-engine/
│   ├── C identity-orgtree/
│   ├── D directory-migration/
│   ├── E target-surface/
│   ├── F access-plane/
│   ├── G network-transformation/
│   └── H program-management/
│
├── compliance/             ← how the transformation is governed and proved
│   ├── A federal-mandates/
│   ├── B boundary-authorization/
│   ├── C evidence-telemetry/
│   ├── D policy-libraries/
│   ├── E controls-testing/
│   ├── F incident-response/
│   └── G governance-canon/
│
└── substrate/              ← shared spine — serves both pillars
    ├── platform-tooling/
    ├── core-architecture/
    └── execution-patterns/
```

Two extra customer-facing surfaces live alongside these:

- `client-server-to-hybrid-cloud/` — the 11-chapter narrative series. Lives
  under `modernization/` as the flagship story.
- `executive-briefs/` — unchanged; one-page leadership summaries per topic.

---

## 2. Leaf-level component tree

Every leaf here is a potential customer-document. Empty leaves = authoring
backlog items.

### 2.1 Modernization

#### A. Platform Substrate
- A.1 Windows Server 2025 base configuration
- A.2 IIS reverse proxy
- A.3 Gitea canonical repo host
- A.4 Kerberos bridge (legacy auth → modern)
- A.5 Enterprise PKI / ADCS
- A.6 TLS certificate lifecycle
- A.7 Backup, replication, DR
- A.8 Security hardening (CIS, AppLocker, WDAC)

#### B. Transformation Engine
- B.1 PowerShell assessment modules (UIAOADAssessment, Read-Only AD)
- B.2 Python analysis scripts
- B.3 API integrator layer (Graph, ARM, Infoblox, vendor APIs)
- B.4 Plan generator (analysis → migration plan)
- B.5 Delivery pipeline (plan → target)
- B.6 Drift reconciliation loop
- B.7 CLI + module reference

#### C. Identity (OrgTree / MOD_*)
- C.1 OrgPath Codebook (MOD_A)
- C.2 Dynamic Group Library (MOD_B)
- C.3 Attribute Mapping Table (MOD_C)
- C.4 Delegation Matrix — AUs + Roles (MOD_D)
- C.5 Governance Workflow Catalog (MOD_E)
- C.6 Migration Runbook OU→Entra (MOD_F)
- C.7 JSON Schema (MOD_H)
- C.8 PowerShell Validation Module (MOD_I)
- C.9 Execution Substrate Integration (MOD_N)
- C.10 Identity Graph Normalization (MOD_Y)
- C.11 Identity Risk Scoring (MOD_T)

#### D. Directory Migration (DM_*)
- D.1 IPAM Adapter — DM_010 (Infoblox/BlueCat/generic)
- D.2 DNS Adapter — DM_015 ⚠ *gap — not in registry*
- D.3 DHCP Adapter — DM_016 ⚠ *gap — not in registry*
- D.4 PKI / ADCS Adapter — DM_020 (ADCS → Cloud PKI + Entra CBA)
- D.5 RADIUS / NPS Adapter — DM_030
- D.6 LDAP Proxy Adapter — DM_040
- D.7 Sync Engine Adapter — DM_050 (Entra Connect / Cloud Sync)
- D.8 Device Management Adapter — DM_060 (SCCM → Intune)
- D.9 NTP Adapter — DM_070
- D.10 DFS Adapter — DM_080
- D.11 SPN / App Registration Adapter — DM_085 ⚠ *gap*
- D.12 Trust Relationship Adapter — DM_090 ⚠ *gap*

#### E. Target Surface (Hybrid Cloud)
- E.1 Entra ID tenant
- E.2 Administrative Units
- E.3 Intune (MDM, Autopilot, compliance)
- E.4 Azure Arc (hybrid server + cluster management)
- E.5 Microsoft 365 SaaS
- E.6 Conditional Access targeting
- E.7 PIM + Access Reviews + Entitlement Management

#### F. Access Plane
- F.1 MFA (methods, phishing resistance)
- F.2 Zero Trust model
- F.3 SASE
- F.4 Certificate-Based Authentication (Entra CBA)
- F.5 Privileged Access Management (CyberArk)
- F.6 Break-glass accounts

#### G. Network Transformation
- G.1 SD-WAN
- G.2 IPAM (hybrid address governance)
- G.3 DNS (hybrid resolution)
- G.4 DHCP (scoped, governed)
- G.5 Palo Alto (firewall / edge)
- G.6 RADIUS/802.1X modernization

#### H. Program Management
- H.1 Master Project Plan (capstone)
- H.2 Migration Roadmap
- H.3 Architecture Decision Records (ADRs)
- H.4 ServiceNow change / incident integration
- H.5 SAM (software asset management)
- H.6 End-user training

### 2.2 Compliance

#### A. Federal Mandates
- A.1 FedRAMP Moderate
- A.2 FedRAMP High
- A.3 CISA SCuBA / BOD 25-01
- A.4 Executive Orders (14028, 14110, 13800, and successors)
- A.5 FISMA
- A.6 NIST 800-53 Rev 5
- A.7 NIST 800-171 (CUI)
- A.8 DoD IL4 / IL5 (future-state)

#### B. Boundary + Authorization
- B.1 GCC-Moderate boundary model (MOD_U)
- B.2 Commercial-Cloud exception (Amazon Connect)
- B.3 Data classification (Controlled, CUI)
- B.4 ATO package / OSCAL authoring
- B.5 3PAO engagement flow
- B.6 Package handoff / continuous authorization

#### C. Evidence + Telemetry
- C.1 Governance Telemetry Model (MOD_X)
- C.2 KSI (Key Security Indicators)
- C.3 ScubaGear evidence pipeline
- C.4 Drift Detection Engine (MOD_M — *primary home is here*)
- C.5 Governance OS State Machine (MOD_S)
- C.6 Provenance chain / signed commits
- C.7 SIEM forwarding

#### D. Policy Libraries
- D.1 Conditional Access Policy Library
- D.2 Intune Policy Templates
- D.3 Azure Arc / Guest Configuration
- D.4 STIG compliance
- D.5 SCuBA baseline policies
- D.6 Defender for Servers policies

#### E. Controls + Testing
- E.1 Validation Suites (adapter + domain)
- E.2 Governance Enforcement Test Suite (MOD_J)
- E.3 Enforcement Decision Trees (MOD_K)
- E.4 Mock Tenant Test Harness (MOD_O)
- E.5 Pester test framework
- E.6 Continuous monitoring
- E.7 DR testing

#### F. Incident + Response
- F.1 Disaster Recovery Playbook (IR-8)
- F.2 SLA Escalation Playbooks (MOD_Q)
- F.3 Incident runbooks
- F.4 Break-glass procedures
- F.5 Active-passive Git replication

#### G. Governance Canon
- G.1 Master Document Specification v1.3
- G.2 [DOCUMENT-METADATA] + [VALIDATION] block templates
- G.3 Classification labels (Controlled, CUI, UNCLASSIFIED reconciliation)
- G.4 Canon Change Protocol
- G.5 ADR-001 Git Infrastructure
- G.6 ADR-002 Two-Brain Execution (to author)
- G.7 Canonical Contributor Workflow (MOD_V)
- G.8 Canonical Error Taxonomy (MOD_W)
- G.9 Glossary (MOD_Z)
- G.10 Document Lifecycle Management

### 2.3 Substrate (shared spine)

#### Platform & tooling
- S.P.1 GitHub / Gitea monorepo
- S.P.2 Quarto render pipeline
- S.P.3 Canon sync (sync_canon.py)
- S.P.4 CI/CD (GitHub Actions)
- S.P.5 Customer Documents portal
- S.P.6 UIAO-Core CLI
- S.P.7 PowerShell Module Reference
- S.P.8 UIAO Academy (training platform)

#### Core architecture
- S.A.1 Six-Plane Architecture
- S.A.2 Three-Layer Rule Model
- S.A.3 Drift Engine (feeds both pillars)
- S.A.4 Evidence Chain
- S.A.5 Boundary Impact Model
- S.A.6 Two-Way Governance (SCuBA assesses · ScubaConnect automates · UIAO governs)

#### Execution patterns
- S.E.1 Two-Brain Execution (Copilot + Execution Substrate)
- S.E.2 AODIM — Attribute-Oriented Directory & Identity Model
- S.E.3 "Instruments vs. Orchestra" positioning narrative

---

## 3. Posted/ → target mapping

Every file currently in `inbox/Posted/` mapped to its target pillar and
sub-category. `Target location` is the proposed Quarto path once the
2-pillar restructure ships.

| # | Posted file (short) | Pillar | Sub-cat | Target location | Status |
|---|---|---|---|---|---|
| 1 | Master Project Plan | Modernization | H.1 | `modernization/program-management/master-project-plan.qmd` | **PARTIAL** — capstone, not yet hosted |
| 2 | Governance OS A-Z Canonical Suite | Substrate | S.A / S.E | `substrate/core-architecture/a-z-canonical-suite.qmd` | **PARTIAL** — 26 appendices map to MOD_* + substrate |
| 3 | Gap Analysis (vs MS Native Tools) | Substrate | S.E.3 | `substrate/execution-patterns/instruments-vs-orchestra.qmd` | **MISSING** |
| 4 | Identity Modernization Guide | Modernization | C | (superseded by MOD_001..Z) | **SUPERSEDED** |
| 5 | PKI Modernization Guide | Modernization | D.4 | `modernization/directory-migration/pki/` (companion to DM_020) | **PARTIAL** |
| 6 | DNS Modernization Guide | Modernization | D.2 / G.3 | `modernization/directory-migration/dns/` (seeds DM_015) | **MISSING target** |
| 7 | AD Computer Object Conversion Guide | Modernization | D.8 / E.3 | `modernization/directory-migration/device-management/` (companion to DM_060) | **PARTIAL** |
| 8 | AD Interaction Guide | Modernization | B.1 | `modernization/transformation-engine/ad-interaction-guide.qmd` | **PARTIAL** |
| 9 | Read-Only AD Assessment Guide | Modernization | B.1 | `modernization/transformation-engine/ad-assessment-read-only.qmd` | **PARTIAL** |
| 10 | PowerShell Module Reference | Modernization | B.7 | `modernization/transformation-engine/powershell-reference.qmd` | **MISSING** |
| 11 | Conditional Access Policy Library | Compliance | D.1 | `compliance/policy-libraries/conditional-access.qmd` | **PARTIAL** — currently in adapter-specs/entra-id |
| 12 | Intune Policy Templates | Compliance | D.2 | `compliance/policy-libraries/intune-templates.qmd` | **PARTIAL** — currently in adapter-specs/intune |
| 13 | Azure Arc Policy Library | Compliance | D.3 | `compliance/policy-libraries/azure-arc.qmd` | **PARTIAL** |
| 14 | Platform Server Build Guide | Modernization | A (1–8) | `modernization/platform-substrate/platform-server-build.qmd` | **COVERED** — authored 2026-04-23 |
| 15 | Git Server WS2025 (Option A) | Modernization | A.2 | `modernization/platform-substrate/` *(archive w/ SUPERSEDED-BY)* | **SUPERSEDED** — by ADR-001 |
| 16 | Git on WS2025 (generic) | Modernization | A.2 | *(archive w/ SUPERSEDED-BY)* | **SUPERSEDED** |
| 17 | CLI & Operations Guide | Substrate | S.P.6 | `substrate/platform-tooling/cli-operations.qmd` | **PARTIAL** |
| 18 | UIAO-Core CLI Reference | Substrate | S.P.6 | `substrate/platform-tooling/uiao-core-cli.qmd` | **PARTIAL** |
| 19 | SCuBA Value Proposition | Compliance | A.3 | `compliance/federal-mandates/scuba-value-proposition.qmd` | **PARTIAL** — authorship issue (Doroszewski) |
| 20 | SCuBA Technical Specification | Compliance | A.3 | `compliance/federal-mandates/scuba-technical-spec.qmd` | **PARTIAL** |
| 21 | SCuBA Pipeline Deliverables | Compliance | C.3 | `compliance/evidence-telemetry/scuba-pipeline.qmd` | **PARTIAL** |
| 22 | FedRAMP-CISA Update | Compliance | A.1/A.3 | `compliance/federal-mandates/fedramp-cisa-update.qmd` | **MISSING** |
| 23 | Disaster Recovery Playbook | Compliance | F.1 | `compliance/incident-response/disaster-recovery.qmd` | **MISSING** — Posted v1.0 ready to port |
| 24 | Operations Runbook | Modernization | A.7 / H | `modernization/platform-substrate/operations-runbook.qmd` | **MISSING** — Posted v1.0 ready to port |
| 25 | End User Training Guide | Modernization | H.6 | `modernization/program-management/end-user-training.qmd` | **MISSING** |
| 26 | Quarto Pipeline Integration Guide | Substrate | S.P.2 | `substrate/platform-tooling/quarto-pipeline.qmd` | **MISSING** |
| 27 | Document Lifecycle Management | Compliance | G.10 | `compliance/governance-canon/document-lifecycle.qmd` | **MISSING** |
| 28 | Documentation Pipeline Setup | Substrate | S.P.2 | `substrate/platform-tooling/doc-pipeline-setup.qmd` | **MISSING** — also "UNCLASSIFIED" banner fix |
| 29 | Compliance Mapping & Gap Analysis | Compliance | B.4 / A | `compliance/boundary-authorization/compliance-crosswalk.qmd` | **MISSING** |
| 30 | UIAO-Executive-Brief (+ SOURCE + with-images) | — | — | `executive-briefs/uiao-overview.qmd` | **COVERED** — consolidate 3 files |
| 31 | AODIM Architecture + Whitepaper | Substrate | S.E.2 | `substrate/execution-patterns/aodim.qmd` | **MISSING** — 300-word stubs, expand or absorb |
| 32 | AD to EntraID Tree (transcript) | — | — | `inbox/transcripts/` *(not canon)* | **TRANSCRIPT** |
| 33 | AD to EntraID - Structural Migration Problem | Modernization | C | (absorb into Client-Server-to-Hybrid-Cloud ch. 00) | **PARTIAL** |
| 34 | Entra ID Org Hierarchy Guide | Modernization | C.4 | (merge into MOD_D customer-docs page) | **COVERED** |
| 35 | Master Document Specification v1.3 | Compliance | G.1 | `compliance/governance-canon/master-document-spec.qmd` | **MISSING** |
| 36 | UIAO-Document-Report Ch 4-9 | Substrate | S.P.8 | `substrate/platform-tooling/document-report.qmd` | **MISSING** — Ch 1-3 absent; canon status undecided |
| 37 | Claude Integration Plan | Substrate | S.E.1 | `substrate/execution-patterns/claude-integration.qmd` | **MISSING** |
| 38 | UIAO Git Infrastructure ADR (ADR-001) | Compliance | G.5 | `compliance/governance-canon/adr/adr-001-git-infrastructure.qmd` | **PARTIAL** |
| 39 | UIAO platform and modernization guides | — | — | *(archive — unedited AI transcript)* | **TRANSCRIPT** |
| 40 | claude-session AD Group/OU mapping | — | — | `inbox/transcripts/` | **TRANSCRIPT** |
| 41 | Error-Github-deploy-docs | — | — | `inbox/scaffolding/` | **SCAFFOLDING** |
| 42 | NanoBanana Batch 1 | — | — | `inbox/scaffolding/` | **SCAFFOLDING** |
| 43 | Test-site research | — | — | `inbox/scaffolding/` | **SCAFFOLDING** |
| 44 | AI IMPORT PROMPT | — | — | `inbox/scaffolding/` | **SCAFFOLDING** |
| 45 | Executive brief grok | — | — | `inbox/scaffolding/` | **SCAFFOLDING** |
| 46 | uiao-gos-implementation-instructions | Substrate | S.E.1 | `substrate/execution-patterns/gos-implementation.qmd` | **MISSING** |
| 47 | fedramp_git_decision_matrix.pdf | Compliance | G.5 | (appendix to ADR-001) | **MISSING HOME** |
| 48 | 2026-04-21-corpus-assessment (+ supplement) | — | — | `docs/planning/` | working assessment |

Total substantive (non-transcript / non-scaffold) Posted docs: **~38**.
Of those: **COVERED** 2 · **PARTIAL** 17 · **SUPERSEDED** 3 · **MISSING** 16.

## 4. Current customer-documents/ → target mapping

Existing Quarto pages to be re-homed during the restructure.

| Current path | Target pillar | Target sub-cat |
|---|---|---|
| `executive-briefs/` | *(unchanged)* | *(unchanged)* |
| `architecture-series/boundary-impact-model.md` | Substrate | S.A.5 |
| `architecture-series/drift-engine.md` | Substrate | S.A.3 |
| `architecture-series/evidence-chain.md` | Substrate | S.A.4 |
| `architecture-series/six-plane-architecture.md` | Substrate | S.A.1 |
| `architecture-series/three-layer-rule-model.md` | Substrate | S.A.2 |
| `modernization-specs/identity/` | Modernization | C |
| `modernization-specs/cloud/` | Modernization | E |
| `modernization-specs/sase/` | Modernization | F.3 |
| `modernization-specs/sdwan/` | Modernization | G.1 |
| `modernization-specs/telemetry/` | Compliance | C |
| `modernization-specs/zero-trust/` | Modernization | F.2 |
| `adapter-specs/cyberark/` | Modernization | F.5 |
| `adapter-specs/entra-id/` | Modernization | E.1 |
| `adapter-specs/infoblox/` | Modernization | D.1 |
| `adapter-specs/intune/` | Modernization | E.3 |
| `adapter-specs/m365/` | Modernization | E.5 |
| `adapter-specs/mainframe/` | Modernization | (H — legacy bridge) |
| `adapter-specs/palo-alto/` | Modernization | G.5 |
| `adapter-specs/patch-state/` | Compliance | E.6 |
| `adapter-specs/pki-ca/` | Modernization | D.4 |
| `adapter-specs/scuba/` | Compliance | A.3 |
| `adapter-specs/scubagear/` | Compliance | C.3 |
| `adapter-specs/service-now/` | Modernization | H.4 |
| `adapter-specs/siem/` | Compliance | C.7 |
| `adapter-specs/stig-compliance/` | Compliance | D.4 |
| `adapter-specs/terraform/` | Substrate | S.P.1 |
| `adapter-specs/vuln-scan/` | Compliance | E.6 |
| `validation-suites/adapters/*` | Compliance | E.1 |
| `validation-suites/domains/*` | Compliance | E.1 |
| `case-studies/` | *(no re-home — cross-pillar narratives)* | — |
| `executive-governance-series/` | Substrate | S.A (narrative wrap) |
| `whitepapers/` | *(no re-home — cross-pillar long-form)* | — |
| `platform/platform-server-build.qmd` *(new)* | Modernization | A |

---

## 5. Boundary cases (steward decisions needed)

Components that legitimately straddle the pillars. Each needs a primary
home assigned; the other pillar(s) cross-reference.

| Component | Candidate primary | Candidate secondary | Recommendation |
|---|---|---|---|
| Drift Detection Engine (MOD_M) | Compliance C.4 | Modernization (feeds SSOT) | **Primary: Compliance C.4**. Cross-ref in Mod D + Mod C. Rationale: drift is an evidentiary concept before it is a modernization concept. |
| Governance Telemetry Model (MOD_X) | Compliance C.1 | Mod B (consumed by engine) | **Primary: Compliance C.1**. Cross-ref in Mod B. |
| Governance OS State Machine (MOD_S) | Substrate S.A | Compliance C.5 | **Primary: Substrate S.A**. State machine is architecture; compliance consumes it. |
| SLA Escalation Playbooks (MOD_Q) | Compliance F.2 | Mod H | **Primary: Compliance F.2**. |
| A-Z Canonical Document Suite | Substrate S.A/S.E | *capstone candidate* | **Primary: Substrate** as canonical architecture reference. Capstone-vs-MPP decision still pending. |
| Multi-Cloud Boundary Model (MOD_U) | Compliance B.1 | Mod E | **Primary: Compliance B.1**. |
| Two-Brain Execution (ADR-002) | Substrate S.E.1 | Compliance G.6 | **Primary: Substrate S.E.1** (execution pattern); ADR lives in Compliance G.6. Two artifacts. |
| AODIM | Substrate S.E.2 | Mod C | **Primary: Substrate S.E.2** (conceptual model); if expanded, MOD_C consumes. |
| Platform Server Build | Mod A | Compliance (runs compliance tooling) | **Primary: Mod A**. |
| UIAO-Document-Report | Substrate S.P.8 | — | **Primary: Substrate**. Canon status undecided (keep or drop). |
| CyberArk (PAM) | Mod F.5 | Compliance D | **Primary: Mod F.5**. |
| STIG Compliance adapter | Compliance D.4 | Mod E | **Primary: Compliance D.4**. |
| ServiceNow | Mod H.4 | Compliance F.3 (incident routing) | **Primary: Mod H.4**. |

---

## 6. Migration path

Sequence for moving from current 8-family layout to 2-pillar + substrate.
Non-destructive — every move is an add + redirect, not a delete.

### Phase 1 — Structure (1 week)
1. Create directory stubs: `customer-documents/modernization/`,
   `customer-documents/compliance/`, `customer-documents/substrate/`.
2. Author index.qmd landings for each of the three pillars.
3. Author sub-category landings (A..H for Mod, A..G for Comp, 3 for Sub).
4. Update `_quarto.yml` sidebar to add the new pillars **alongside** the
   existing 8 families (keep both visible during migration).
5. Land `docs/planning/customer-documents-taxonomy.md` (this file).

### Phase 2 — Client-Server-to-Hybrid-Cloud series (2–3 weeks)
Author the 11-chapter flagship story under
`customer-documents/modernization/client-server-to-hybrid-cloud/`.

### Phase 3 — Existing pages re-homed (1 week)
Move existing pages per §4 mapping table. Use Quarto redirects
(`redirect-from:` frontmatter) on the old paths so external links don't break.

### Phase 4 — Posted/ absorption (3–4 weeks)
Promote the 17 PARTIAL and 16 MISSING Posted docs per §3 mapping. Order:
- Executive Briefs (15 pages, 1-day each).
- Architecture / Whitepapers (priority: Gap Analysis, AODIM, FedRAMP-CISA).
- Operations + DR Playbooks (Posted v1.0 → Quarto).
- Policy Libraries (CA, Intune, Arc).
- References (PowerShell Module Reference, CLI Reference).
- Training + Compliance + Validation.

### Phase 5 — 8-family layout retired (1 week)
Once all pages re-homed and redirects in place, remove the old 8-family
sidebar entries. Existing adapter-specs paths stay as redirects forever.

### Phase 6 — DM authoring (3–4 weeks)
Close the DM_* gaps: DM_015 DNS, DM_016 DHCP, DM_085 SPN, DM_090 Trust.
These are blocking the Mod D sub-category completeness.

Total estimate: **10–13 weeks** end-to-end. Most of it is authoring; the
structural work is the first week.

---

## 7. Open decisions

These are either blocking authoring or governance-level choices only the
Canon Steward can make.

1. **Approve 2-pillar + substrate split** (this doc). Y/N.
2. **Folder naming** — `modernization/` + `compliance/` + `substrate/`, or
   alternative names (e.g. `modernize/` + `govern/` + `spine/`).
3. **Capstone** — Master Project Plan, A-Z Suite, or dual. Unchanged from
   earlier assessment.
4. **Boundary model reconciliation** — Master Spec v1.3 vs. A-Z Suite +
   Core CLI Reference. Unchanged from earlier assessment.
5. **SCuBA Value Prop authorship** — Doroszewski attribution.
6. **AODIM fate** — expand (to MOD_AA/AB) / absorb (into MOD_C + Substrate
   S.E.2) / retire.
7. **UIAO-Document-Report canon status** — keep (author Ch 1-3) or drop.
8. **DM registry expansion** — author DM_015/016/085/090 to hit the "15
   files" claim, or reduce the claim to 8.
9. **ADR-002 Two-Brain Execution** — author now or defer.

---

## 8. Next steps (deferred — Canon Steward selects)

- [ ] Approve taxonomy (§1–2) and mapping (§3–4).
- [ ] Decide boundary cases (§5).
- [ ] Pick opening authoring slice (likely: Phase 1 + Phase 2 Chapter 00).
- [ ] Resolve open decisions (§7) that block that slice.

---

## Appendix — Authorship note

This working doc is maintained by Claude (Cowork) under the Canon
Steward's direction. It is **not canon**; it is a planning surface. When
sections stabilise, they graduate into actual Quarto landing pages or
canonical appendices. Deletions are tracked by Git; edits are merged via
PR. No Copilot Tasks credits are spent at any point in this flow —
authoring happens in markdown, rendering happens via Quarto, and the
`.docx` artifacts fall out of the pipeline deterministically.
