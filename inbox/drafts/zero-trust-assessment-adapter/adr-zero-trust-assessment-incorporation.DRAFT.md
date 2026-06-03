---
adr_id: adr-NNN  # PLACEHOLDER — assign at promotion. ADR-090 is highest merged;
                 # ADR-092 (Active Governance) is in flight (PR #755). Do NOT
                 # hard-code 091/092 — pick the next free number against main.
title: "Zero Trust Assessment Incorporation — Microsoft ZeroTrustAssessment Output as Governed Evidence"
status: DRAFT
decided: null
deciders: Michael Stratton
updated: 2026-06-03
next_review: null
review_trigger: Microsoft ships SecOps/AI-pillar checks; ZeroTrustAssessment JSON schema changes (TestId, TestStatus, or TestMinimumLicense semantics); GCC/GCC-High endpoint support is added to the module; ADR-092 (Active Governance) provider-incorporation contract is revised.
impact: Establishes that UIAO incorporates the output of Microsoft's open-source ZeroTrustAssessment tool as governed evidence via an import adapter — UIAO does not re-implement the checks and does not auto-remediate. Defines the JSON->canonical-evidence normalization, the dual TestId namespace handling, and a boundary-applicability tag derived from existing fields. Sibling to UIAO_005/UIAO_002 (ScubaGear). Subordinate to ADR-092 (Active Governance) provider-incorporation contract and its federal L3 actuation ceiling.
supersedes: null
superseded_by: null
classification: Controlled
boundary: GCC-Moderate
publish_to_site: false   # raw findings are Controlled; only the de-identified crosswalk/doctrine publishes
publication_style: include
---

# ADR-NNN (DRAFT): Zero Trust Assessment Incorporation

## Status

**DRAFT** — 2026-06-03. Staged in `inbox/drafts/zero-trust-assessment-adapter/`.
Promote by assigning the next free ADR number against `main` and moving to
`src/uiao/canon/adr/`. This ADR is **subordinate to ADR-092 (Active Governance)**
— it is one worked instance of that ADR's provider-incorporation contract.

## Context

Microsoft ships the **Zero Trust Assessment** — an open-source PowerShell module
(`Install-Module ZeroTrustAssessment`; `github.com/microsoft/zerotrustassessment`)
that runs hundreds of **read-only** checks against an Entra / Intune / Azure /
Exchange / SharePoint / Purview tenant, aligned to NIST / CISA / CIS plus
Microsoft's Secure Future Initiative (SFI) and the Zero Trust pillars. It emits
`ZeroTrustAssessmentReport.html` (presentation) and a parallel structured
`…Report.json` (data). It does not remediate.

This is structurally the **ScubaGear relationship UIAO already adopted** in
[UIAO_005](../../../docs/canon/UIAO_005_SCuBA_Value_Proposition_v1.0.qmd) /
[UIAO_002](../../../src/uiao/canon/UIAO_002_SCuBA_Technical_Specification_v1.0.md):
an external Microsoft/CISA assessment **producer** whose output UIAO **consumes,
normalizes, versions, and drift-detects** — *a complementary orchestration layer,
not a competitive replacement*. Per ADR-092, UIAO is the active reconciliation
control plane that **governs + incorporates** provider data planes; the Zero
Trust Assessment is exactly such a provider.

The decision is grounded in the **actual v2.1.8 JSON schema** (verified against
the shipped `SampleReport.json`, Contoso demo, 295 tests — see
`SampleReport.json` and `triage_zt_report.py` in this folder), not on the
rendered HTML or documentation prose.

## Decision

1. **Incorporate, don't re-implement.** UIAO ingests the ZeroTrustAssessment
   `…Report.json` as evidence. UIAO does not duplicate the checks in its native
   `UIAO*Assessment` modules; this is an **import adapter** on the planned
   `UIAOImportAdapters` surface.
2. **Ground truth is `Tests[]`, not `TestResultSummary`.** In the shipped demo
   the summary block does not reconcile with the per-test statuses (it reports
   Identity 85/100 passed; the per-test counts are 41 Passed / 52 Failed / 35
   Planned). The adapter **recomputes every roll-up from `Tests[]`** and treats
   `TestResultSummary` as a non-authoritative dashboard hint.
3. **Six statuses, not pass/fail.** `TestStatus ∈ {Passed, Failed, Skipped,
   Planned, Investigate, Error}`. Only `Failed` and `Investigate` are findings.
   `Skipped` (not applicable / unlicensed / service disconnected), `Planned`
   (a check Microsoft has not yet implemented — 37 in the demo, 35 of them
   Identity), and `Error` are **coverage/applicability signals, never gaps.**
4. **Derive the boundary-applicability tag from existing fields.** No
   hand-authored applicability map. The tri-state is computed:
   - `not-available-in-boundary` — `TestStatus == Skipped` with a `SkippedReason`
     of *"not applicable to the current environment"* / *"requires … license"* /
     *"requires connection to the service(s) … currently disconnected"*, **or**
     `TestMinimumLicense` names a SKU not present/authorized in the GCC-Moderate
     boundary;
   - `above-baseline` — passes/fails but the underlying control exceeds the
     FedRAMP Moderate 800-53 baseline (ZT defense-in-depth);
   - `required` — maps to an in-scope FedRAMP Moderate / SCuBA control.
5. **No auto-remediation.** Remediation text the tool emits is surfaced as a
   **proposed** change routed through governance/change-control (CM-3), never
   applied. This honors ADR-092's federal **L3 actuation ceiling** and the fact
   that the agency tenant cannot be live-actuated from UIAO.
6. **Raw findings are Controlled; only the crosswalk publishes.** Ingested
   findings are tenant-specific vulnerability data (the tool's own docs warn as
   much). They live in the in-boundary substrate (Gitea/Postgres) classified
   `Controlled`; `publish_to_site: false`. Only the **de-identified pillar →
   800-53 / SCuBA crosswalk and doctrine** render to the public site (consistent
   with ADR-072 publication policy and ADR-079 Tier-4 boundary enforcement).

## Source artifact — verified schema (v2.1.8)

Top level: `ExecutedAt, TenantId, TenantName, Domain, Account, CurrentVersion,
LatestVersion, TestResultSummary, Tests[], TenantInfo, EndOfJson, IsDemo`.

Each `Tests[]` entry (16 fields):

| Field | Role in UIAO |
|---|---|
| `TestId` | **Stable crosswalk key.** Dual namespace: 276 short-numeric (Graph checks) + 19 GUID (Azure-resource checks) in the demo. Key must accept both. |
| `TestStatus` | Outcome (6-valued, see Decision §3). |
| `TestResult` | Human-readable evidence sentence (contains ✅/❌ — UTF-8). |
| `TestPillar` | ZT pillar: Identity / Devices / Network / Data / Infrastructure (SecOps, AI defined but empty in v2.1.8). |
| `TestSfiPillar` | Parallel SFI taxonomy — second crosswalk axis. |
| `TestRisk` | High / Medium / Low — prioritization. |
| `TestImpact`, `TestImplementationCost` | User-impact and effort — remediation triage. |
| `TestMinimumLicense` | SKU list **or** string. Drives the applicability tag. ~108/295 cite a premium/P2-class SKU. |
| `TestSkipped`, `SkippedReason` | Skip flag + reason text — drives the applicability tag. |
| `TestAppliesTo` | Scoping list (non-null on 85). |
| `TestCategory`, `TestDescription`, `TestTitle`, `TestTags` | Descriptive. |

## Normalization mapping (ZT JSON → UIAO evidence record)

Proposed canonical evidence record (one per `Tests[]` entry):

```yaml
evidence_id: ztassess:<TestId>          # namespace-prefixed; stable across runs
source:
  tool: microsoft/zerotrustassessment
  version: <CurrentVersion>             # e.g. 2.1.8 — pin + record
  executed_at: <ExecutedAt>
  tenant: <TenantId>                    # Controlled
check:
  id: <TestId>
  id_namespace: numeric | guid          # see dual-namespace note
  title: <TestTitle>
  pillar_zt: <TestPillar>
  pillar_sfi: <TestSfiPillar>
  category: <TestCategory>
outcome:
  status: <TestStatus>                  # verbatim 6-valued
  is_finding: <status in {Failed, Investigate}>
  risk: <TestRisk>
  result_text: <TestResult>
applicability:                          # DERIVED, not from the tool
  tag: required | above-baseline | not-available-in-boundary
  rationale: <SkippedReason | license-derivation | crosswalk-note>
  minimum_license: <normalized TestMinimumLicense>
crosswalk:                              # authored/maintained in UIAO canon
  nist_800_53_moderate: [<control ids>]
  scuba: [<baseline ids>]               # reuse UIAO_002/005 mapping plane
  orgpath_posture: <ref | null>
provenance:
  ingested_at: <stamp>
  classification: Controlled
  boundary: GCC-Moderate
```

Mapping rules:
- **Key on `evidence_id = ztassess:<TestId>`** so re-runs reconcile and feed the
  existing drift taxonomy (a status flip Passed→Failed is a drift event).
- **Recompute roll-ups** from `is_finding`; ignore `TestResultSummary`.
- **`crosswalk.*` is the UIAO value-add** — Microsoft maps to NIST/CISA/CIS
  generically; UIAO maps each `TestId` to the FedRAMP Moderate 800-53 control set
  and to the SCuBA plane already modeled in UIAO_002/005. Maintain as a canon
  table keyed by `TestId` (handles both namespaces).
- **Pin tool version + module hash** in `source` (CM-7 / SA supply-chain).

## FedRAMP Moderate boundary impacts (summary; see prior analysis)

- **Feature applicability** is the dominant distortion — recompute, and trust the
  derived applicability tag over the raw pass-rate.
- **Endpoint support**: the module documents only commercial endpoints. True
  **GCC-Moderate runs on commercial endpoints** (likely fine); **GCC-High/DoD**
  is unverified/unsupported — confirm tenant cloud before relying on it.
- **Controlled data**: findings do not publish; substrate must be in-boundary.
- **Privileged, change-managed execution**: GA consent on first run; broad read
  roles thereafter — an auditable event, not ad hoc.
- **Actuation ceiling**: propose, never apply (L3).
- **Baseline distinction**: separate FedRAMP-Moderate-required from
  ZT-above-baseline so optional hardening is not mislabeled as a compliance gap.

## Consequences

**Positive.** Reuses the proven ScubaGear incorporation pattern; binds to
structured JSON (not brittle HTML scraping); applicability tag is derived, not
maintained by hand; `TestId` gives a stable drift + crosswalk anchor; testable
end-to-end against `SampleReport.json` with zero tenant access.

**Negative / watch.** ZT JSON schema is young (v2.x) and may churn — the version
pin and `review_trigger` exist for this. `TestResultSummary` unreliability must
be guarded in code. SecOps/AI pillars are empty today; the crosswalk table needs
ongoing curation as Microsoft adds checks.

## Open questions

1. Does the at-work `\zt-export\` folder emit the same JSON schema as
   `SampleReport.json`? (Confirm with one real export before locking the parser.)
2. Where does the crosswalk table live — a new `UIAO_NNN` canon doc (sibling to
   UIAO_005) or an annex to UIAO_002?
3. Is the customer-facing surface a new Book chapter or the ADR-092 Platform page?
