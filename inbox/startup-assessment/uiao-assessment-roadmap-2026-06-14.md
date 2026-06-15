# UIAO — Assessment & Roadmap, Tree-Verified (2026-06-14)

> **Not canon.** This is an `inbox/` working document — a project assessment and
> roadmap, not governance authority. It traces no provenance to
> `src/uiao/canon/` and is not scanned by the substrate walker. It captures a
> grounded, codebase-anchored read on UIAO's current state and near-term work.
>
> **Verification markers.** Where a claim is checked against this repository it
> is marked **[repo-verified]**; where it depends on facts outside the working
> tree (commit totals on a *shallow* clone, GitHub traction, signing, market
> facts) it is marked **[unverified]** and treated as an input, not a finding.
> This document supersedes the inline numbers in the original 2026-06-14
> assessment where they conflict; corrections are called out explicitly.
>
> **Verification basis:** HEAD at PR #917 (`adr-104-e911-compliance-layer`),
> working tree clean, plus GitHub repo/release API. The local clone is
> **shallow (50 commits, no tags)** — any commit-count or tag claim cannot be
> settled here.

---

## 1. What UIAO is

UIAO (Unified Identity-Addressing-Overlay) is a solo-developed **Governance OS**
for identity-first, canon-anchored, drift-detected modernization of identity,
telemetry, policy, and enforcement. The core engine is vertical-agnostic; the
federal vertical (FedRAMP Moderate Rev 5 + OSCAL + KSI + SCuBA, deployed against
a GCC-Moderate boundary) is the most mature adapter pack on top of it.
**[repo-verified]** via `AGENTS.md` (ADR-085 universal-enterprise positioning)
and the canon topology.

Anchors that hold up against the tree **[repo-verified]**:

- Protected **canon** under `src/uiao/canon/` as SSOT; schema-first governance
  (five JSON Schemas validate registries/manifests/frontmatter in CI).
- **5-class drift taxonomy** — `DRIFT-SCHEMA / SEMANTIC / PROVENANCE / AUTHZ /
  IDENTITY` — present across the governance engine, adapters, and canon.
- **105 ADR files**, highest **ADR-104** (E911/LocPath). ADRs are append-only
  with supersession markers.
- Single installable `uiao` package after the ADR-032 consolidation.
- Identity-transformation roadmap **UIAO_135/136** with a **107-deliverable**
  total (24+ weeks), Phase 1 ~62% landed, Phases 2–5 awaiting drafts.

## 2. Corrected current-state numbers

The original assessment is directionally accurate; these specific figures are
corrected against the tree.

| Claim (original) | Corrected finding | Source |
|---|---|---|
| "Core has reached v0.7.0" | **Package `__version__` is still `0.6.1`.** CHANGELOG has a `[0.7.0] — 2026-06-07` section and GitHub has a `v0.7.0` release (published **2026-05-26**), but the in-tree package version bump lags. **[repo-verified]** | `src/uiao/__version__.py`, `CHANGELOG.md`, GH releases |
| (n/a) | **Anomalous `v1.6.0` GitHub release** with no publish date and no CHANGELOG entry — does not reconcile with a 0.x core; likely a stray/draft. Recommend cleanup. **[repo-verified via GH]** | GH releases API |
| "163 signed KSIs" | **~165** `ksi-*.yaml` rule files (192 unique KSI IDs counting cross-references). Cryptographic signing asserted in canon, **[unverified]** here. | `src/uiao/rules/**/ksi-*.yaml` |
| "13 adapters" | **Understated.** `modernization-registry.yaml` ≈ 20 entries; plus conformance `adapter-registry.yaml`; `src/uiao/adapters/` holds ~40 modules (entra, intune, cyberark, servicenow, paloalto, infoblox, bluecat, mssql, siem, vulnscan, terraform, …). **[repo-verified]** | registries + `adapters/` |
| "ADR-078 OrgPath/AD-to-Entra Model C phases" | **Mischaracterized.** ADR-078 is `orgpath-attribute-schema-15-facet` (the 15-facet OrgPath attribute schema). Model-C / AD-to-Entra work lives in UIAO_007, ADR-038, etc. **[repo-verified]** | `adr/adr-078-*.md` |
| "~999 commits" | **Unverifiable here** — shallow clone (50 commits, no tags). Plausible given repo age (created 2026-04-16) and PR #917 in ~2 months. **[unverified]** | shallow clone |
| "2 stars, 0 forks/watchers" | **2 stars, 0 forks** confirmed; **1 open issue** exists. API `watchers_count` aliases stars (=2); true subscriber count not exposed. **[repo-verified via GH]** | GH repo API |

Confirmed as stated **[repo-verified]**: ADR-032 / 083 (docs reorg) / 085 / 097
(`sql-server-saas-placement`, currently in `[Unreleased]`); operational kits
`helpdesk-entra-kit-v1.5` (2026-06-09) and `intune-arc-kit-v1.0` (2026-06-08);
ServiceNow (0.6.1) and CyberArk (0.6.3) release lineage.

## 3. Already done — drop from the roadmap

- **Rendered Quarto site is already hosted.** `has_pages: true`, homepage
  **https://whalermike.github.io/uiao/**. The original roadmap's Phase 1 item
  "consider hosting rendered Quarto site (GitHub Pages…)" is **shipped** — move
  it to *done* and re-scope toward link-audit / Draft-status cleanup instead.
  **[repo-verified via GH]**

## 4. Maturity verdict (unchanged, now substantiated)

Advanced, production-oriented prototype / early operational Governance OS:
versioned, CI-gated, artifact-emitting, with real federal value in
Entra/Intune/OrgPath/ConMon/drift. Pilot-ready for agency identity modernization
or helpdesk/cloud-ops teams. Risks center on **scope management, external
validation, and sustained solo execution** — not fundamental technical
shortcomings. The tree supports this verdict.

## 5. Roadmap (re-prioritized from the corrections above)

### Phase 1 — Stabilization & hygiene (1–4 weeks)
- **Reconcile versioning:** bump `src/uiao/__version__.py` to match the released
  line, and resolve/retire the stray **`v1.6.0`** GitHub release so the Releases
  page tells one story.
- **Merge `[Unreleased]`:** ADR-097 SQL Server placement; GCC-Moderate Phase
  1.4/4/5 cherry-picks (KQL, `sentinel_probe.py`, FINDING-002..009).
- **Docs finalization (re-scoped):** the site is live — focus on post-reorg
  link audit, resolving remaining Draft statuses, and 100% publication-pipeline
  CI coverage. Improve the quickstart + adapter-authoring tutorial.
- **Refresh public counts** (KSI ~165, adapters ~20+) wherever the docs quote
  stale figures (e.g., the "13 adapters" line).
- **Queued items:** ServiceNow real-tenant validation plan, Palo Alto NGFW
  adapter completion, CyberArk PAM enhancements.

### Phase 2 — Core completion & expansion (1–3 months)
- **Identity Transformation (UIAO_135/136):** land prioritized phases (Computer
  Object Transformation, Service-Account → Workload Identity, HR-agnostic
  provisioning) with canon updates, adapters, and drift coverage. Sequence
  ruthlessly against the 107-deliverable total.
- **Drift/KSI/ConMon maturation:** complete orchestrator/FastAPI elements;
  expand configuration-latitude detection + SLA enforcement; tag the ~165 KSIs
  for FedRAMP 20x/MAS alignment.
- **SaaS hardening:** test/document the multi-tenant Azure Container Apps model
  (ADR-096); add Bicep/Terraform templates, monitoring, cost controls; keep the
  Windows/IIS path fully supported.

### Phase 3 — Usability, adoption & ecosystem (3–6+ months)
- ATO/reciprocity package (tailored SSP excerpts, POA&M, ConMon evidence
  bundles); agency integration playbooks; synthetic/anonymized case studies.
- Non-federal adapter packs (HIPAA, SOC 2, StateRAMP, ISO 27001/NIST CSF) to
  prove vertical-agnostic value.
- Evaluate PyPI publish; lightweight onboarding paths; pilot-agency validation
  feeding findings back into canon.
- Advance provisional patent work on the governance substrate / drift taxonomy /
  canon-anchored SSOT / OrgPath orchestration. **[unverified — off-repo]**

### Cross-cutting / ongoing
- Preserve invariants: all canon changes via ADR + document-registry allocation;
  keep drift detection in CI gates.
- Scope & sustainability: triage relentlessly (107+ identity deliverables is
  ambitious for solo + AI-assisted execution).
- Success metrics: agency traction, completed high-impact adapters/kits, clean
  live docs site, visible coverage/quality signals, identity-phase progress.

---

*Authored 2026-06-14 as an `inbox/` working document. Not canon; not provenance-*
*anchored. Supersedes the inline figures of the same-day assessment where they*
*conflict.*
