# Federal Compliance & Automation Roadmap — DNS · EntraID · Azure

> Status: DRAFT for author review · Surface: `inbox/` (not canon)
> Scope parameter: **FedRAMP Moderate + Microsoft GCC Moderate** (per the series rule).
> Deferred: RedHat-on-AWS VMs (sequenced last, §6).

## 0. The organizing principle — compliance is the spine, not a phase

Every workstream below hangs off one anchor: **NIST SP 800-53 Rev 5 (Moderate baseline)
+ CISA SCuBA / BOD 25-01 + FedRAMP 20x KSIs**, tied together by the generated
**compliance spine** (`inbox/Application Aware Networking/aan-compliance-spine.yml`),
which maps every control → closing mechanism → book → evidence slot → KSI. Do not
build automation and *then* map it to controls; the spine already says which control
each mechanism closes, so each task is scoped by "which spine row does this satisfy."

Your three supported pillars map to the spine's planes:

| Pillar | Plane | Primary control families |
|---|---|---|
| **DNS / DDI** | Naming & addressing (truth) | SC-20, SC-20(1), SC-21, SC-22, CM-8 |
| **EntraID** | Identity (truth) | IA-2, IA-5, AC-2, AC-5/6, IA-3 |
| **Azure** | Policy enforcement + compute | CM-2/6, SI-2, RA-5, SC-7, AU-* |
| *(M365 SaaS)* | Policy + data | CM-6 (SCuBA), AC-4, SC-28, AU-10 |
| *(Teams/Telephony)* | Application/experience | SC-8, AU-*, SCuBA Teams baseline |

## 1. Asset map — what already exists (your "related tasks")

Most of your related work is **repo content**, not GitHub issues (only 4 issues are
open, and 3 are AI-identity governance — tangential; #832 is the SCuBA/NIST citation
sweep, which is compliance-relevant). Treat this table as the real backlog.

| Your ask | Existing artifacts (repo paths) | Status |
|---|---|---|
| **DDI / InfoBlox case** | `infoblox-ddi-book/` (9 chapters = Vol VIII), `Vol_I_Book_01_FedAAN_SSA_Landing_Zone_IPAM_FedRAMP.qmd`, spine rows SC-20/21/22 + CM-8 | Argument **done**; boss-facing proposal **gap** |
| **ServiceNow — compliance** | **Vol VII (Books 00–05)** — M365 & Azure control compliance, CMDB reconcile, attestation, scoped app | **Done** (deploy it) |
| **ServiceNow — DDI provisioning** | `infoblox-ddi-book/servicenow-app/` (Script Includes, Flows, ATF, update set), `07-servicenow-orchestration.md` | **Done** (exemplar) |
| **ServiceNow — helpdesk (Entra/M365/Azure)** | `docs/customer-documents/adapter-specs/service-now/service-now.qmd`, `uiao.adapters.servicenow`, ADR-003 inbound provisioning | **Gap** — no ITSM catalog (JML, password/MFA reset, group/license, unlock) |
| **ServiceNow — Landing Zone** | `Vol_VI_Book_01_FedAAN_Landing_Zone_Network_as_Code.qmd`, `infoblox-ddi-book/azure-alz-automation/`, CPG Terraform Connector | **Partial** — IaC done; catalog front-door gap |
| **ServiceNow — App Registrations** | `Vol_I_Book_03…Certificates_Tokens…`, `Vol_VI_Book_02…Identity_Access_as_Code`, Vol VII Book 02 (CA exceptions) | **Gap** — no request/govern/expire catalog |
| **EntraID compliance** | Vol I Books 03/04, Vol VI Book 02, Vol III Book 01 (PAM), Vol VII Book 02 | **Strong** |
| **Azure compliance** | Vol VI Book 01, Vol III Book 04 (Cloud-Native Posture), **Vol VII Book 03** | **Strong** |
| **Teams & Teams Telephony** | **`Vol_I_Book_06_FedAAN_Federal_Telecommunications_Modernization.qmd`** (Teams Phone, SBC, Direct Routing, Operator Connect, Calling Plans) | **Strong** — telephony covered; SCuBA-Teams drift automation gap |
| **SCuBA baselines** | `src/uiao/canon/UIAO_002_SCuBA_Technical_Specification_v1.0.md`, `UIAO_005…`, ADR-047 ConMon | **Done** (doctrine) |
| **RedHat on AWS (later)** | `Vol_III_Book_03…Patch_Systems_Management` (Satellite/Ansible/Insights, SSM), Vol VIII Book 02 (AWS DDI) | Coverage exists; **deferred** |

## 2. Task #1 — Convince the boss: DDI *must* be InfoBlox

The whole argument already exists as the series' **Closure Necessity doctrine (Theme A)** —
you just need it as a one-page brief. The core, boss-proof claim:

> **SC-20, SC-20(1), SC-21, SC-22 (authoritative + recursive DNSSEC name/address
> resolution) and CM-8 (authoritative component inventory keyed to addresses) have
> no alternate closure path.** A scanner *measures drift from* a source of truth; it
> cannot *author* one. You cannot attest authoritative name resolution without an
> authoritative resolver, and you cannot inventory what you cannot enumerate. Native
> per-cloud DNS (Azure DNS, Route 53) gives you N disconnected naming services, not
> one authoritative cross-cloud naming plane + IPAM SSOT.

The multiplier that makes this a leadership decision, not a networking one:

> **The CM-8 IPAM join key is the single identity that lets the ServiceNow CMDB,
> the multi-cloud patch queue, and the evidence fabric reconcile into *one*
> compliance picture.** DDI is upstream of the entire automation + ATO evidence
> chain — remove it and every downstream control loses its join key. DDI isn't a
> line item; it's the keystone the authorization package hangs on.

Procurement facts to verify at buy time: **InfoBlox BloxOne DDI Federal is
FedRAMP-authorized (Moderate)** — confirm on the FedRAMP Marketplace; state the CSO's
actual level, never "High" (series scope rule).

**Deliverable (gap):** a 2-page executive brief `SSA_IPAM_Proposal_InfoBlox.docx`
(already allowlisted in `inbox/.gitignore`, not yet authored). I can generate it from
Vol I Book 01 + the spine rows + Vol VIII — say the word.

## 3. Task #2 — ServiceNow automation, in five lanes

Sequence lanes by dependency: A and B exist; C/D/E are the build.

- **Lane A — Compliance automation → *deploy Vol VII.*** The scoped app
  `x_ssa_fed_compliance` (Vol VII Book 05) coordinates M365 + Azure control drift.
  Action: stand it up in sub-prod, wire the in-boundary MID + least-privilege Graph/ARM
  connectors, load the control map, run the ATF suites.
- **Lane B — DDI provisioning → *reuse the exemplar.*** `infoblox-ddi-book/servicenow-app/`
  is a complete, importable pattern (catalog → approval/SoD → Terraform → validation
  gate → CMDB). Action: point it at the chosen DDI backend once Task #1 lands.
- **Lane C — Helpdesk / ITSM catalog (GAP).** The most-requested day-2 automation, none
  of it built yet. Catalog items, each mapped to a control:
  - Joiner/Mover/Leaver (AC-2) · password + MFA reset / account unlock (IA-5) ·
    group & license assignment (AC-2/AC-6) · Conditional-Access exception
    (AC-3 — already modeled in Vol VII Book 02) · guest/B2B invite (AC-2).
  - Same discipline as Vol VII: **actuate via Graph through the in-boundary MID; never
    standing tenant admin; every action a change/approval record (CM-3/AU-2).**
- **Lane D — Landing Zone front door.** IaC exists (Vol VI Book 01 + azure-alz); the gap
  is the *catalog request* → CPG Terraform Connector → subscription/vNet/subnet
  provisioning (reconciled to IPAM/DDI, CM-8).
- **Lane E — App Registration governance (GAP).** Request → approve → scoped consent →
  secret/cert issuance with expiry → automated rotation & attestation. Closes IA-5(2),
  SC-17, AC-6; feeds Vol VII Book 04 attestation.

## 4. Teams & Teams Telephony

Telephony architecture is **already covered** in `Vol_I_Book_06` (Teams Phone, SBC,
Direct Routing, Operator Connect, Calling Plans). Two additions to make it compliance-
and automation-complete:

1. **Teams SCuBA drift → ServiceNow** (extend the Vol VII Book 02 M365 loop with the
   Teams SCuBA baseline; CM-6).
2. **Telephony ServiceNow catalog (GAP):** phone-number assignment, calling-policy
   assignment, emergency-address (E911) validation — as governed catalog items.

## 5. Compliance crosswalk (the anchor for every workstream)

| Workstream | Controls closed | SCuBA / KSI |
|---|---|---|
| DDI (InfoBlox) | SC-20/20(1)/21/22, CM-8 | KSI-CNA, KSI-PIY |
| Entra identity + helpdesk | IA-2, IA-5, AC-2/5/6, IA-3 | KSI-IAM |
| Azure posture + patch | CM-2/6, SI-2, RA-5, SC-7 | KSI-CMT, KSI-SVC, KSI-MLA |
| M365 (SCuBA) + Teams | CM-6, AC-4, SC-28, AU-10 | KSI-CMT (SCuBA baselines) |
| ServiceNow coordination | CM-3, CM-5, CA-2/5/7, AU-2 | KSI-MLA |

## 6. Sequenced phases (the roadmap)

| Phase | Work | Depends on | Compliance payoff |
|---|---|---|---|
| **0 — Baseline** (mostly exists) | Confirm the spine, SCuBA baselines, KSI mapping cover DNS/Entra/Azure/M365/Teams | — | The control map every phase reports against |
| **1 — DDI decision** | Author the InfoBlox exec brief (§2); get the DDI-must-be-InfoBlox sign-off | Spine, Vol I B01, Vol VIII | SC-20/21/22 + CM-8 closure path locked |
| **2 — ServiceNow compliance** | Deploy Vol VII (Lane A); reuse DDI app (Lane B) | Phase 1 (CM-8 join key) | CM-6/SI-2/RA-5/CA-7 *operated*, not just deployed |
| **3 — ServiceNow day-2** | Build helpdesk (C), landing-zone front door (D), app-reg governance (E) | Phase 2 patterns | IA-5, AC-2/5/6, CM-3, IA-5(2)/SC-17 |
| **4 — Teams/Telephony** | Teams SCuBA drift automation + telephony catalog | Phase 2 (M365 loop) | CM-6 (Teams baseline), SC-8, AU-* |
| **5 — RedHat on AWS** | Extend patch/posture + DDI to AWS RedHat (Vol III B03, Vol VIII B02) | Phases 2–3 queues | SI-2/CM-6/RA-5 on the AWS estate |

## 7. Immediate next actions I can take

1. **Generate the InfoBlox executive brief** (Task #1 deliverable) from existing canon.
2. **File GitHub issues** for the three real gaps (helpdesk catalog, app-reg governance,
   Teams telephony catalog) so you have a tracked backlog.
3. **Scaffold the Lane C helpdesk catalog** as a Vol VII-style scoped-app spec + control map.
4. **Draft a Volume IX outline** — "ServiceNow Day-2 Operations (Helpdesk, Landing Zone,
   App Registrations, Telephony)" — the natural home for Lanes C/D/E + §4.

Tell me which to start and I'll build it.
