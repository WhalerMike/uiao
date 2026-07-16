# ADR-111 Rule Set → CR26 Moderate Indicator Reconciliation

> **Generated file — do not hand-edit.** Produced by `render_cr26_reconciliation.py`. Regenerate when the internal rules or the CR26 catalog snapshot change.

> **Provenance.** Internal rule set: the 29 `src/uiao/ksi/rules/KSI-0NN.yaml` files (the series' "ADR-111 rule set"). CR26 catalog: the authoritative FedRAMP CR26 OSCAL catalog committed in-repo at `src/uiao/canon/compliance/reference/fedramp-cr26/snapshot/c31eb04c082d6d578a26a00de9a482707ab7a00c/catalog/json/FedRAMP_CR26_catalog.json`. Each rule's declared `Mappings.CR26` indicator ID is matched against the catalog's leaf indicators — no IDs are invented.

## Headline delta

- **CR26 Moderate indicators in the in-repo catalog snapshot:** **46** across 10 themes (the finalized published catalog may count 56–63 depending on statement-level vs indicator-level counting; this snapshot enumerates indicator-level IDs).
- **Internal ADR-111 rules:** **29**.
- **Indicators explicitly mapped 1:1 to an internal rule (satisfied at indicator-ID level):** **19 of 46**.
- **Indicators not yet bound to an internal rule ID (not-yet-mapped):** **27 of 46** — four of these themes are *partially* addressed by the 10 CISA ScuBA baseline rules (KSI-001..010), which attest M365 baseline state but declare no CR26 indicator ID.

So "29/29 satisfied" is a statement about the **internal rule set**, not the CR26 Moderate catalog: at the CR26 indicator level, coverage is **19/46 explicitly mapped**, with 27 indicators still to be bound (mostly the IAM/CNA/SVC/MLA themes the ScuBA rules touch without an indicator-ID binding). The POA&M is therefore expected to be non-empty once these are assessed against the finalized CR26 list.

## Per-theme reconciliation

| Theme | CR26 indicator | Internal rule | Status |
|---|---|---|---|
| KSI-IAM (Identity and Access Management) | KSI-IAM-AAM — Automating Account Management | — (ScuBA rules KSI-001..010 attest this theme) | 🟡 Partial — ScuBA baseline, no indicator-ID binding |
| KSI-IAM (Identity and Access Management) | KSI-IAM-APM — Adopting Passwordless Methods | — (ScuBA rules KSI-001..010 attest this theme) | 🟡 Partial — ScuBA baseline, no indicator-ID binding |
| KSI-IAM (Identity and Access Management) | KSI-IAM-ELP — Ensuring Least Privilege | — (ScuBA rules KSI-001..010 attest this theme) | 🟡 Partial — ScuBA baseline, no indicator-ID binding |
| KSI-IAM (Identity and Access Management) | KSI-IAM-JIT — Authorizing Just-in-Time | — (ScuBA rules KSI-001..010 attest this theme) | 🟡 Partial — ScuBA baseline, no indicator-ID binding |
| KSI-IAM (Identity and Access Management) | KSI-IAM-SNU — Securing Non-User Authentication | — (ScuBA rules KSI-001..010 attest this theme) | 🟡 Partial — ScuBA baseline, no indicator-ID binding |
| KSI-IAM (Identity and Access Management) | KSI-IAM-SUS — Responding to Suspicious Activity | — (ScuBA rules KSI-001..010 attest this theme) | 🟡 Partial — ScuBA baseline, no indicator-ID binding |
| KSI-CNA (Cloud Native Architecture) | KSI-CNA-DFP — Defining Functionality and Privileges | — (ScuBA rules KSI-001..010 attest this theme) | 🟡 Partial — ScuBA baseline, no indicator-ID binding |
| KSI-CNA (Cloud Native Architecture) | KSI-CNA-EIS — Enforcing Intended State | — (ScuBA rules KSI-001..010 attest this theme) | 🟡 Partial — ScuBA baseline, no indicator-ID binding |
| KSI-CNA (Cloud Native Architecture) | KSI-CNA-IBP — Implementing Best Practices | — (ScuBA rules KSI-001..010 attest this theme) | 🟡 Partial — ScuBA baseline, no indicator-ID binding |
| KSI-CNA (Cloud Native Architecture) | KSI-CNA-MAT — Minimizing Attack Surface | — (ScuBA rules KSI-001..010 attest this theme) | 🟡 Partial — ScuBA baseline, no indicator-ID binding |
| KSI-CNA (Cloud Native Architecture) | KSI-CNA-OFA — Optimizing for Availability | — (ScuBA rules KSI-001..010 attest this theme) | 🟡 Partial — ScuBA baseline, no indicator-ID binding |
| KSI-CNA (Cloud Native Architecture) | KSI-CNA-RNT — Restricting Network Traffic | — (ScuBA rules KSI-001..010 attest this theme) | 🟡 Partial — ScuBA baseline, no indicator-ID binding |
| KSI-CNA (Cloud Native Architecture) | KSI-CNA-RVP — Reviewing Protections | — (ScuBA rules KSI-001..010 attest this theme) | 🟡 Partial — ScuBA baseline, no indicator-ID binding |
| KSI-CNA (Cloud Native Architecture) | KSI-CNA-ULN — Using Logical Networking | — (ScuBA rules KSI-001..010 attest this theme) | 🟡 Partial — ScuBA baseline, no indicator-ID binding |
| KSI-SVC (Service Configuration) | KSI-SVC-ACM — Automating Configuration Management | — (ScuBA rules KSI-001..010 attest this theme) | 🟡 Partial — ScuBA baseline, no indicator-ID binding |
| KSI-SVC (Service Configuration) | KSI-SVC-ASM — Automating Secret Management | — (ScuBA rules KSI-001..010 attest this theme) | 🟡 Partial — ScuBA baseline, no indicator-ID binding |
| KSI-SVC (Service Configuration) | KSI-SVC-EIS — Evaluating and Improving Security | — (ScuBA rules KSI-001..010 attest this theme) | 🟡 Partial — ScuBA baseline, no indicator-ID binding |
| KSI-SVC (Service Configuration) | KSI-SVC-PRR — Preventing Residual Risk | — (ScuBA rules KSI-001..010 attest this theme) | 🟡 Partial — ScuBA baseline, no indicator-ID binding |
| KSI-SVC (Service Configuration) | KSI-SVC-RUD — Removing Unwanted Data | — (ScuBA rules KSI-001..010 attest this theme) | 🟡 Partial — ScuBA baseline, no indicator-ID binding |
| KSI-SVC (Service Configuration) | KSI-SVC-SNT — Securing Network Traffic | — (ScuBA rules KSI-001..010 attest this theme) | 🟡 Partial — ScuBA baseline, no indicator-ID binding |
| KSI-SVC (Service Configuration) | KSI-SVC-VCM — Validating Communications | — (ScuBA rules KSI-001..010 attest this theme) | 🟡 Partial — ScuBA baseline, no indicator-ID binding |
| KSI-SVC (Service Configuration) | KSI-SVC-VRI — Validating Resource Integrity | — (ScuBA rules KSI-001..010 attest this theme) | 🟡 Partial — ScuBA baseline, no indicator-ID binding |
| KSI-MLA (Monitoring, Logging, and Auditing) | KSI-MLA-ALA — Authorizing Log Access | — (ScuBA rules KSI-001..010 attest this theme) | 🟡 Partial — ScuBA baseline, no indicator-ID binding |
| KSI-MLA (Monitoring, Logging, and Auditing) | KSI-MLA-EVC — Evaluating Configurations | — (ScuBA rules KSI-001..010 attest this theme) | 🟡 Partial — ScuBA baseline, no indicator-ID binding |
| KSI-MLA (Monitoring, Logging, and Auditing) | KSI-MLA-LET — Logging Event Types | — (ScuBA rules KSI-001..010 attest this theme) | 🟡 Partial — ScuBA baseline, no indicator-ID binding |
| KSI-MLA (Monitoring, Logging, and Auditing) | KSI-MLA-OSM — Operating SIEM Capability | — (ScuBA rules KSI-001..010 attest this theme) | 🟡 Partial — ScuBA baseline, no indicator-ID binding |
| KSI-MLA (Monitoring, Logging, and Auditing) | KSI-MLA-RVL — Reviewing Logs | — (ScuBA rules KSI-001..010 attest this theme) | 🟡 Partial — ScuBA baseline, no indicator-ID binding |
| KSI-CMT (Change Management) | KSI-CMT-LMC — Logging Changes | KSI-011 — Change Logging and Monitoring | ✅ Mapped |
| KSI-CMT (Change Management) | KSI-CMT-RMV — Redeploying vs Modifying | KSI-012 — Immutable Redeployment over Direct Modification | ✅ Mapped |
| KSI-CMT (Change Management) | KSI-CMT-RVP — Reviewing Change Procedures | KSI-013 — Change-Procedure Effectiveness Review | ✅ Mapped |
| KSI-CMT (Change Management) | KSI-CMT-VTD — Validating Throughout Deployment | KSI-014 — Automated Validation Throughout Deployment | ✅ Mapped |
| KSI-PIY (Policy and Inventory) | KSI-PIY-GIV — Generating Inventories | KSI-017 — Endpoint Inventory Visibility | ✅ Mapped |
| KSI-PIY (Policy and Inventory) | KSI-PIY-RES — Reviewing Executive Support | KSI-018 — Endpoint Entity State Resolution | ✅ Mapped |
| KSI-PIY (Policy and Inventory) | KSI-PIY-RIS — Reviewing Investments in Security | KSI-019 — Endpoint Inventory State Recording | ✅ Mapped |
| KSI-PIY (Policy and Inventory) | KSI-PIY-RSD — Reviewing Security in the SDLC | KSI-020 — SDLC Security Review | ✅ Mapped |
| KSI-PIY (Policy and Inventory) | KSI-PIY-RVD — Reviewing Vulnerability Disclosures | KSI-021 — Privileged Access via Defined Paths | ✅ Mapped |
| KSI-SCR (Supply Chain Risk) | KSI-SCR-MIT — Mitigating Supply Chain Risk | KSI-015 — Supply Chain Risk Mitigation | ✅ Mapped |
| KSI-SCR (Supply Chain Risk) | KSI-SCR-MON — Monitoring Supply Chain Risk | KSI-016 — Supply Chain Monitoring | ✅ Mapped |
| KSI-CED (Cybersecurity Education) | KSI-CED-RAT — Reviewing All Training | KSI-022 — Cybersecurity Training Effectiveness Review | ✅ Mapped |
| KSI-INR (Incident Response) | KSI-INR-AAR — Generating After Action Reports | KSI-023 — Incident After Action Report Generation | ✅ Mapped |
| KSI-INR (Incident Response) | KSI-INR-RIR — Reviewing Incident Response Procedures | KSI-024 — Incident Response Procedure Effectiveness Review | ✅ Mapped |
| KSI-INR (Incident Response) | KSI-INR-RPI — Reviewing Past Incidents | KSI-025 — Past Incident Pattern Review | ✅ Mapped |
| KSI-RPL (Recovery Planning) | KSI-RPL-ABO — Aligning Backups with Objectives | KSI-026 — Backup Alignment with Recovery Objectives | ✅ Mapped |
| KSI-RPL (Recovery Planning) | KSI-RPL-ARP — Aligning Recovery Plan | KSI-027 — Recovery Plan Alignment with Objectives | ✅ Mapped |
| KSI-RPL (Recovery Planning) | KSI-RPL-RRO — Reviewing Recovery Objectives | KSI-028 — Recovery Objective Review | ✅ Mapped |
| KSI-RPL (Recovery Planning) | KSI-RPL-TRC — Testing Recovery Capabilities | KSI-029 — Recovery Capability Testing | ✅ Mapped |

## Theme summary

| Theme | Indicators | Mapped 1:1 | Coverage |
|---|---|---|---|
| KSI-IAM — Identity and Access Management | 6 | 0 | partial (ScuBA baseline) |
| KSI-CNA — Cloud Native Architecture | 8 | 0 | partial (ScuBA baseline) |
| KSI-SVC — Service Configuration | 8 | 0 | partial (ScuBA baseline) |
| KSI-MLA — Monitoring, Logging, and Auditing | 5 | 0 | partial (ScuBA baseline) |
| KSI-CMT — Change Management | 4 | 4 | fully mapped |
| KSI-PIY — Policy and Inventory | 5 | 5 | fully mapped |
| KSI-SCR — Supply Chain Risk | 2 | 2 | fully mapped |
| KSI-CED — Cybersecurity Education | 1 | 1 | fully mapped |
| KSI-INR — Incident Response | 3 | 3 | fully mapped |
| KSI-RPL — Recovery Planning | 4 | 4 | fully mapped |
| **Total** | **46** | **19** | **19/46 explicitly mapped** |

## Remediation plan for the not-yet-mapped indicators

The **27 not-yet-mapped indicators** fall entirely in the 4 themes below, each attested today at the CISA ScuBA baseline level (rules KSI-001..010) but not yet bound to a CR26 indicator ID. The external dependency has **cleared** — the finalized CR26 Moderate list was published **June 25, 2026** — so this is actionable now, not blocked. Owner is stated by role (no individual named here); the authorization timeline dates are from the ConMon Gap Roadmap.

| Theme | Unmapped indicators | Disposition | Owner (role) | Target |
|---|---|---|---|---|
| KSI-IAM — Identity and Access Management | 6 | Bind each indicator to a rule, **or** record an explicit ScuBA-baseline attestation decision | AAN compliance authoring lead (OIS ConMon lead accountable) | Before independent SCA; no later than the Class B+C window (Aug 31, 2026) |
| KSI-CNA — Cloud Native Architecture | 8 | Bind each indicator to a rule, **or** record an explicit ScuBA-baseline attestation decision | AAN compliance authoring lead (OIS ConMon lead accountable) | Before independent SCA; no later than the Class B+C window (Aug 31, 2026) |
| KSI-SVC — Service Configuration | 8 | Bind each indicator to a rule, **or** record an explicit ScuBA-baseline attestation decision | AAN compliance authoring lead (OIS ConMon lead accountable) | Before independent SCA; no later than the Class B+C window (Aug 31, 2026) |
| KSI-MLA — Monitoring, Logging, and Auditing | 5 | Bind each indicator to a rule, **or** record an explicit ScuBA-baseline attestation decision | AAN compliance authoring lead (OIS ConMon lead accountable) | Before independent SCA; no later than the Class B+C window (Aug 31, 2026) |
| **Total** | **27** | — | — | — |

Until these are dispositioned, the POA&M is expected to be non-empty: each unmapped indicator is a candidate POA&M item pending the binding decision and the independent SCA verdict.
