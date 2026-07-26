# Whitepaper Content Assessment — 2026-07-26

Full content-level review of all 17 papers under
`docs/customer-documents/whitepapers/` against the current canon
(engine 0.7.1, ADR-134 four-pillar family). Structural alignment
(index/sidebar/scanner) was fixed separately in PR #1366. Tier 1
mechanical corrections land in the same PR as this memo. This memo
records the **Tier 2 (editorial)** and **Tier 3 (canon-side)** items
that need author/owner judgment.

## Tier 2 — editorial rewrites (whitepaper content)

1. **`aodim-executive-whitepaper.qmd` teaches the retired Model B
   OrgPath.** Lines ~61–85 present the composite-slash
   `CORP/US/EAST/BALTIMORE/IT` single-attribute model. ADR-078 and
   UIAO_151 superseded this with the 15-facet Model C, and canonical
   `UIAO_006` v1.1 was reconciled 2026-06-03 specifically to remove this
   content. The paper needs the same reconciliation. Same defect in
   `docs/customer-documents/architecture-series/aodim-architecture.qmd`
   (~lines 69–135). Also: zero canon citations; docx-import escape
   artifacts (`\"` in dynamic-group rules); four recycled images from
   other papers with mismatched captions.

2. **`zero-trust-governance-whitepaper.qmd` enforcement language
   contradicts ADR-092.** Drift table rows say `DRIFT-IDENTITY` "denies
   access immediately" and `DRIFT-AUTHZ` "alerts and halts". ADR-092
   doctrine: UIAO is never the in-path enforcer; actuation is
   human-gated (L3 federal ceiling), providers enforce. Rows should be
   recast as detection/governance outcomes. §6 could also acknowledge
   the `state-local` (ADR-133) and `commercial-general` (ADR-129)
   boundaries beyond GCC-Moderate.

3. **`uiao-vs-native-tools.qmd`** —
   (a) §9 "Import Adapters (Future Development)" describes
   `UIAOImportAdapters.psm1` as conceptual with a live-API design; the
   module is implemented (`tools/powershell/UIAOImportAdapters/`,
   UIAO_182) with different function names and a file-based, no-live-API
   contract. Rewrite §9 to match UIAO_182.
   (b) Coverage-figure contradiction: 65% (exec summary), 40% (§4
   callout), 60% (§10.2) for the same quantity; none canon-anchored
   (UIAO_009 carries no percentages). Pick one and source it.
   (c) §9.2 mandates classification "Controlled" while
   `src/uiao/canon/data/program.yml` says Public (footer fixed in this
   PR; §9.2 prose left for author).
   (d) Point-in-time product claims (March/April 2026 previews) need a
   refresh or an as-of caveat.

4. **`federal-ssot-alignment.qmd` "six control planes" table is
   non-canonical.** §3.4 (and the mandate table + figure alt text) name
   Identity/Authorization/Compliance/Migration/Evidence/Operational;
   canon (ADR-030) defines Identity/Addressing/Overlay/Telemetry/
   Management/Governance. `16_DriftDetectionStandard.qmd` §7 cites this
   paper for the wrong set — circular. Decide: rename the paper's
   concept (it is arguably a different six-plane *federation* framing)
   or reconcile to ADR-030 vocabulary.

5. **`federal-hrit-productization.qmd` ↔ OrgLink reconciliation.** The
   USA Staffing / eOPF / EHRI / OPM-federation interconnections
   (Patterns B/C) are Link-object territory under UIAO_145 + ADR-134
   (counterparty class `federal-agency`, CA-3/CA-9/SA-9/AC-20). The
   paper predates the pillar; add Link-object framing or a pointer to
   the OrgLink narrative. Also: `provisioning-source: declared`
   invariant (~line 265) exists nowhere in canon — either register it
   or drop it; §5 cite of ADR-058 for "FedRAMP 20x continuous
   monitoring" appears to be a mis-citation (ADR-058 is Purview
   telemetry); paper is Active atop Draft Spec2-D6.1.

6. **`federal-ai-governance-submission-readiness.qmd` honesty ledger.**
   "Azure only today (no AWS/GCP IaC)" is false since ADR-117 landed
   `deploy/aws/` (CDK, ECS Fargate). AISystemRecord row understates
   state: UIAO_196 spec exists, L1 scanner implemented
   (`src/uiao/governance/ai_inventory/`). Refresh the ledger rows.

7. **`git-server-interfaces-whitepaper.qmd`** — anchored to
   `platform-server-build.qmd` v1.3; the build doc is v1.5. "PostgreSQL,
   not SQLite" (§7.2) contradicts ADR-041 v1.3's sanctioned single-host
   SQLite profile; DR posture (RPO 24h/RTO 4h) predates ADR-090
   hot-standby. `status: Active` over a DRAFT/aspirational runbook
   (Phase 14 presented as operating). Needs a v1.5 reconciliation pass
   and probably a status demotion to Draft.

8. **`ad-to-entraid-migration-problem.qmd`** — invokes "Eight Core
   Concepts" but lists seven (missing certificate-anchored overlay per
   `docs/governance/VISION.qmd`); second-person advisory tone ("Your
   agency…") unedited from the docx import for an Active
   customer-facing doc; hero images recycled from other papers with
   mismatched captions; pillar framing ends where the four-pillar canon
   now begins.

9. **`infoblox-hybrid-dns-unified-ddi.qmd`** — no cross-linkage in
   either direction with the Vol VIII DDI book
   (`orgcomp-series/Vol_VIII_*` / `infoblox-ddi-book/`); uses
   "BloxOne DDI" naming where the newer book says "Universal DDI
   (formerly BloxOne DDI)".

10. **`snowflake-keypair-vs-uiao-orgpath.qmd`** — boundary framing
    predates ADR-129/ADR-133 (a non-federal engagement no longer needs
    a new `gcc-boundary` enum value); OrgPath described as
    Entra-slot-materialized, predating ADR-098 vendor-neutral binding
    profiles.

11. **Cross-cutting** — none of the 17 papers mentions OrgLink or the
    four-pillar family; the flagship governance-OS paper predates
    ADR-092 Active Governance (no reconciliation/actuation framing);
    Active/Draft statuses invert actual canon-anchoring quality
    (the Draft papers are the best-anchored). Consider a section-wide
    pillar-vocabulary pass and a status re-baseline against the index's
    own Active definition.

## Tier 3 — canon-side staleness (canon-change protocol applies)

1. **`src/uiao/canon/substrate-manifest.yaml`** (~line 61) still says
   "Five-class taxonomy"; ADR-074 added the sixth class
   (`DRIFT-SSOT-CONTENTION`). `16_DriftDetectionStandard.qmd` prose
   (~line 33) says "five classes" above its own six-row table.
2. **`src/uiao/canon/UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md`**
   (~lines 72–155) still carries Model B `CORP/US/EAST` examples despite
   `status: Current` — same reconciliation UIAO_006 already received.
3. **ScubaGear pin chain lag**: `adapter-registry.yaml#scubagear`
   `runtime-version: "1.5.1"` and
   `adapter-specs/scubagear/scubagear.qmd` ("Pinned to v1.5.1") vs
   `.github/scubagear-upstream-pin.yaml` `scubagear_version: "1.8.0"`
   (validated 2026-05-12).
4. **`document-registry.yaml`** has no row for UIAO_196
   (`Spec4-AI-D1.1-AISystemIdentityRecord.md` self-declares the ID).

## Fixed in this PR (Tier 1 record)

Site banner v0.6.1 → v0.7.1; five → six drift classes in prose
(governance-os, zero-trust table row added, federal-ssot, federal-hrit);
"five JSON schemas" → forty; modernization registry "10 entries" → 28;
"eight adapter interfaces" → nine (+ SQL Server); HRIT "nine systems" →
eleven; "TARGET / DESIGN-ONLY" runtime-drift claims → "partially
implemented" (governance-os ×2, modernization-governance ×2); license
MIT → Apache-2.0 and footer Controlled → Public (vs-native); scubagear
companion-spec link (`index.qmd` → `scubagear.qmd`) and orgpath-narrative
frontmatter path (`07a-…` → `Book_07a.qmd`, also in federal-ssot);
git-server foundation link path fixed ×2; hybrid-join "forthcoming"
companion references now link the published modernization-journey paper;
stale "not yet promoted or published" provenance notes updated in
hybrid-join and modernization-journey; Infoblox closing-note part
numbers (3 → 4, Parts 1–8 → 1–9).
