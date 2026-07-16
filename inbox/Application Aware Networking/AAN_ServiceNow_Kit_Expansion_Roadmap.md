# AAN ServiceNow Kit Expansion Roadmap

> Status: DRAFT for author review · Surface: `inbox/` (not canon)
> Scope parameter: **FedRAMP Moderate + Microsoft GCC Moderate** (per the series rule).
> Companion to: `inbox/Federal_Compliance_Automation_Roadmap.md` (lanes A–F, phases 0–5),
> `AAN_Vol_VII_ServiceNow_Automation_Plan.md`, `AAN-Training-Program/AAN_Identity_Access_Governance_Kit_Requirements.docx`,
> `AAN_Series_Requirements.md`
> Date Code: 2026-07-15 22:19 ET

## 1. Purpose

Name the **AAN ServiceNow kit portfolio** — the scoped applications that operate the
AAN architecture — and sequence its expansion beyond what the series already carries.
The `AAN_Identity_Access_Governance_Kit_Requirements.docx` cites this roadmap as the
document that proposes that kit "as a Phase 2 deliverable"; this file is that roadmap,
reconciled against the lanes and phases the repo already tracks in
`Federal_Compliance_Automation_Roadmap.md` so there is one sequencing story, not two.

**Numbering reconciliation (read this first).** The compliance-automation roadmap's
phases 0–5 sequence *all* federal compliance work (DDI decision, Vol VII deployment,
day-2 build, Teams, RedHat-on-AWS). The **kit phases** below sequence only the
ServiceNow kit portfolio, and are numbered independently:

| Kit phase | Contents | Maps onto compliance-roadmap phase |
|---|---|---|
| **Kit Phase 1 — Foundation kits** (exist) | Compliance Kit (Vol VII), DDI Kit (Vol VIII exemplar), Day-2 Kit (Vol IX) | Phases 2–4 |
| **Kit Phase 2 — Identity & Access Governance Kit** (proposed) | JML automation, access certification, IAM KSI evidence | After phase 3 (extends the Day-2 Kit's JML lane) |
| **Kit Phase 3+ — Candidate kits** (future) | PAM/JIT, Device Compliance (Intune), AWS/RedHat queue extension, analytics | Phase 5 and beyond |

## 2. Doctrine guardrails (inherited, non-negotiable)

Every kit in the portfolio — existing and proposed — carries the Vol VII discipline:

1. **Coordination, not actuation.** The kit routes drift/requests to an owner, gates
   change (CM-3), and rolls posture up to ConMon (CA-7); actuation stays
   platform-native (Microsoft Graph, Azure Policy, Update Manager).
2. **CMDB reconciles to the naming plane.** IPAM/DDI (CM-8 join key) and HRIT are the
   truth planes; a CMDB that drifts from them is a reconciliation defect, never a
   second source of truth.
3. **FedRAMP Moderate + GCC Moderate only.** ServiceNow Government Cloud referred to
   as *FedRAMP-authorized*; never cite High.
4. **In-boundary by construction.** MID Server inside the ATO boundary;
   least-privilege connector identities — read plus scoped/logged/approved write,
   never standing tenant admin (AC-6).
5. **Everything as code, checked against the SSOT.** Each kit's control map is
   machine-readable data projected from `aan-compliance-spine.yml`, CI-checked with
   the regen-and-diff discipline (`validate_day2_control_maps.py` pattern); ATF
   coverage and update-set packaging are release requirements.
6. **Requirements before build.** Each new kit enters the portfolio through a
   detailed requirements document in the format of
   `AAN_Identity_Access_Governance_Kit_Requirements.docx` / `AAN_Series_Requirements.md`
   (overview, scope, FR tables with Req IDs, integration matrix, NFRs, personas,
   KPIs, dependencies), reviewed by CSI, OIS, and ServiceNow stakeholders.

## 3. Kit Phase 1 — Foundation kits (exist today)

| Kit | Series home | Lanes | What it operates | Status |
|---|---|---|---|---|
| **Compliance Kit** (`x_ssa_fed_compliance`) | Vol VII Books 00–05 | A | M365 + Azure control drift → tracked work, CMDB reconciliation (CM-8), attestation/evidence/KSI (CA-2/5/7) | Authored; deploy to sub-prod, wire MID + Graph/ARM connectors, run ATF |
| **DDI Kit** | Vol VIII / `infoblox-ddi-book/servicenow-app/` | B | Catalog → approval/SoD (CM-5) → Terraform → validation gate → CMDB for DDI change | Complete importable exemplar; point at the DDI backend once the InfoBlox decision (compliance-roadmap Task #1) lands |
| **Day-2 Kit** | Vol IX Books 00–05 / `servicenow-day2/` | C, D, E, §4, F | Helpdesk/ITSM catalog (JML, credential, access), landing-zone front door, app-registration governance, Teams telephony, SaaS integration governance (SA-9 gate) | Books + control maps + flows + ATF spec authored (issues #1139–#1141); remaining: export `sys_atf_test` XML and the assembled update set from a sub-prod build, per-item catalog variable sets |

These three kits close the coordination layer for the estate's *routine* state:
compliance drift, DDI change, and day-2 requests. What they deliberately do **not**
carry is identity *governance* — certification campaigns, least-privilege evidence,
and the IAM KSI feed — which is the Phase 2 kit's job.

## 4. Kit Phase 2 — Identity & Access Governance Kit (proposed)

Detailed requirements: `AAN-Training-Program/AAN_Identity_Access_Governance_Kit_Requirements.docx`
(Draft v0.9). Tracking issue: **#1221** (same pattern as #1139–#1141).
Summary of what it adds and where it sits:

- **Extends, not duplicates, the Day-2 Kit.** Vol IX Book 01 already governs JML
  *requests*; this kit automates the full lifecycle from **HRIT Org SSOT events**
  (joiner/mover/leaver with approval gates, FR-JML-001..005) and layers **access
  certification campaigns** (user, manager, application-owner, privileged;
  FR-CERT-001..006) on top.
- **Feeds the Compliance Kit's evidence loop.** Campaign completion, MFA/conditional
  access coverage, SSOT-vs-Entra least-privilege comparison, and JML audit trails
  become IAM KSI evidence (FR-EVD-001..006), exported OSCAL-compatibly via the
  `uiao oscal bundle` path into Vol VII Book 04 attestation.
- **Dependencies:** Vol I Book 04 (HRIT Identity & Org SSOT) implemented and reliable;
  Vol I Book 05 (Entra ID modernization) on at least a parallel path; foundation kits
  deployed (the requirements doc assumes the Day-2 and DDI kits are live).
- **Series home (proposal):** a new Vol IX book (Vol IX Book 06 — Identity & Access
  Governance) or, if certification-campaign scope grows, its own volume; decide at
  requirements sign-off. Spine registration, control map, ATF, and update set follow
  the guardrails in §2 either way.
- **Out of the kit's scope, deferred to Phase 3+:** full PAM/JIT provisioning, device
  compliance / Intune integration, non-Entra identity sources, AI-driven access
  recommendations, automated remediation beyond evidence + alerting.

## 5. Kit Phase 3+ — Candidate kits (future, unsequenced)

Candidates named by the Phase 2 requirements document and the series' explicit
follow-ups; each requires its own requirements document (§2 guardrail 6) before any
build:

| Candidate kit | Seed doctrine in the series | Would close / operate |
|---|---|---|
| **PAM / JIT Access Kit** | Vol III Book 01 (Privileged Access Management) | Just-in-time elevation, standing-privilege burndown (AC-6), privileged-session evidence |
| **Device Compliance Kit (Intune)** | ZTNA-related work in Vol I Book 05; Intune-first drafts in `inbox/drafts/` | Device-compliance gates in conditional access, endpoint evidence slots |
| **AWS / RedHat Queue Extension** | Vol III Book 03 (Patch & Systems Management), Vol VIII Book 02 (AWS DDI) | SI-2/CM-6/RA-5 queues for the AWS RedHat estate reconciling into the same ServiceNow queues (compliance-roadmap phase 5) |
| **Identity Analytics Kit** | Phase 2 kit's evidence store | AI-assisted access recommendations, anomaly detection, risk scoring — evidence-consuming, never auto-remediating without human-in-the-loop |

## 6. Sequencing & gates

```
Kit Phase 1 (deploy)          Kit Phase 2 (build)                Kit Phase 3+ (propose)
Compliance Kit ──┐
DDI Kit ─────────┼─ sub-prod, ATF, update sets
Day-2 Kit ───────┘        │
                          ▼
              Identity & Access Governance Kit
              (gate: HRIT SSOT live, Entra modernization
               underway, requirements v1.0 signed off)
                          │
                          ▼
              PAM/JIT · Device Compliance · AWS/RedHat · Analytics
              (gate: per-kit requirements doc + OIS review)
```

Gates, concretely:

1. **Phase 1 → 2:** foundation kits running in sub-prod with green ATF; HRIT Org SSOT
   (Vol I Book 04) providing reliable data; Identity & Access Governance Kit
   requirements advanced from Draft v0.9 to a signed-off v1.0 through the CSI/OIS
   workshops the document itself calls for.
2. **Phase 2 → 3+:** IAM KSI evidence flowing into Vol VII Book 04; per-candidate
   requirements documents authored and reviewed; sequencing decided against the
   compliance-roadmap phase 5 (RedHat-on-AWS) timing.

## 7. Immediate next actions

1. Decide the Phase 2 kit's series home (Vol IX Book 06 vs. new volume) and register
   it in `aan-compliance-spine.yml`.
2. Advance the Identity & Access Governance Kit requirements doc to v1.0 (CSI/OIS
   workshop pass; align with the CR26 Indicator Mapping effort).
3. Finish the Day-2 Kit's remaining steps (issue #1139: ATF XML export, update-set
   assembly, catalog variable sets) so the Phase 1 → 2 gate is testable.
4. ~~File a tracking issue for the Phase 2 kit (same pattern as #1139–#1141) so the
   portfolio backlog lives in GitHub, not only in documents.~~ **Done — #1221.**

## 8. Cross-references

- `inbox/Federal_Compliance_Automation_Roadmap.md` — lanes A–F, compliance phases 0–5.
- `inbox/Application Aware Networking/AAN-Training-Program/AAN_Identity_Access_Governance_Kit_Requirements.docx` — Phase 2 kit detailed requirements (Draft v0.9).
- `inbox/Application Aware Networking/AAN_Series_Requirements.md` — series-level requirements document.
- `inbox/Application Aware Networking/AAN_Vol_VII_ServiceNow_Automation_Plan.md` — Vol VII volume plan and doctrine guardrails.
- `inbox/Application Aware Networking/servicenow-day2/README.md` — Day-2 Kit data layer and remaining steps.
- `infoblox-ddi-book/servicenow-app/` — DDI Kit scoped-app exemplar.
- `inbox/Application Aware Networking/aan-compliance-spine.yml` — the machine-readable SSOT every kit's control map projects from.
