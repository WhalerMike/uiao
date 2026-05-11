# UIAO OrgPath Modernization — Narrative Overview (draft folder)

**Status:** DRAFT — awaiting Canon Steward review
**Origin:** `OneDrive\UAIO-NewDocs\UIAO Governance OS — The Complete Narrative\` (synced 2026-05-08)
**Proposed canon allocation:** `UIAO_010` (top-level architecture overview range; pending registry entry)

## What this folder is

A 15-document narrative-style overview of the OrgPath/OrgTree governance
substrate, originally authored as Word documents in OneDrive under the title
*UIAO Governance OS — The Complete Narrative*. The author submitted the set
on 2026-05-08 for assessment.

This folder contains the source `.docx` set, an errata-and-scope-fence
wrapper that retitles and corrects the main document, and the formal
assessment record produced during review. Nothing here is canon yet; the
canon path runs through PR review, factual correction, and Canon Steward
approval before any document moves to `src/uiao/canon/`.

## Why a retitle and scope-fence

The original main document presents itself as the *Complete Narrative* of
the UIAO Governance OS. On verification against canon, it is a strong and
internally coherent synthesis of one stream — the OrgPath/OrgTree
modernization track — but it does not cover the HRIT (`ADR-051`–`ADR-054`),
KYC customer-protocol (`ADR-055`–`ADR-056`, `UIAO_141`/`UIAO_142`),
SailPoint NERM (`ADR-059`), Microsoft Purview conformance (`ADR-058`),
adapter framework (`ADR-007`/`011`/`013`/…/`057`), evidence-determinism
(`ADR-006`/`009`/`016`/`020`/`026`), or FedRAMP CA-7 / RFC-0026
(`ADR-043`/`047`) tracks, all of which are operationally live in canon.

Calling a one-stream synthesis "complete" risks downstream readers
treating it as the program's charter. The retitle and the explicit
scope-fence (in `narrative-overview.md`) keep the narrative's value
intact while making its scope honest.

## Manifest

### Source `.docx` set (15 files in `source-docx/`)

Main document:

- `UIAO Governance OS — The Complete Narrative.docx` — 23-chapter synthesis,
  ~17 000 words, the primary artifact under review.

Supporting chapter documents (each elaborates a single Microsoft surface or
governance topic):

- `A Proposed Governance Substrate — Introducing OrgTree and OrgPath.docx`
- `The Microsoft Identity and Governance Stack — Native Capabilities and Inherited Limitations.docx`
- `What Must Exist — The Governance Substrate Requirements for Enterprise Identity Modernization.docx`
- `Implementing OrgTree and OrgPath — A Practical Guide to Building the Governance Substrate.docx`
- `OrgPath and Microsoft Intune — Structural Device Governance at Enterprise Scale.docx`
- `OrgPath and the Microsoft Defender Suite — Organizational Context in Security Operations.docx`
- `OrgPath and Microsoft Purview — Data Governance, DLP, Retention, and eDiscovery by Organizational Position.docx`
- `OrgPath and Application Identity — Governing Service Principals and App Registrations by Organizational Ownership.docx`
- `OrgPath and Azure Policy Guest Configuration — DSC-Based Machine State Enforcement Across Organizational Tiers.docx`
- `OrgPath and Cross-Tenant Collaboration — Governing B2B Guests Through the Organizational Structure.docx`
- `OrgPath in the Security Operations Layer — PIM, Lifecycle Automation, Sentinel Monitoring, and Azure RBAC.docx`
- `OrgPath in Infrastructure Services — DNS Governance, Cloud PKI, and the Complete Governance Model.docx`
- `OrgPath and Power BI Executive Reporting — Governance Posture Dashboards by Organizational Division.docx`
- `OrgPath with Third-Party DDI Platforms — Infoblox and BlueCat Integration Supplement.docx`

### Governance artifacts (in this folder)

- `README.md` — this file
- `narrative-overview.md` — the corrected wrapper: YAML frontmatter,
  retitled, scope-fence, inline errata against the main `.docx`, pointer to
  every supporting chapter
- `assessment-findings.md` — formal assessment record produced
  2026-05-08; lists factual errors, omissions, and the recommendation set

## Path to canon

1. Canon Steward review of `narrative-overview.md` and `assessment-findings.md`.
2. Author addresses errata in the source `.docx` (ADR-001 → ADR-041,
   `.qmd` count, "23-document corpus" framing). Re-export to `.docx` or
   convert to Markdown.
3. If accepted as a canon-grade document, allocate `UIAO_010` in
   `src/uiao/canon/document-registry.yaml`, add YAML frontmatter, and move
   to `src/uiao/canon/UIAO_010_OrgPath_Modernization_Narrative_Overview_v1.0.md`.
4. If retained as supplementary reading rather than canon, leave in
   `inbox/` and link from `UIAO_007` (OrgTree Modernization) as a
   narrative companion.

## Related canon

- `src/uiao/canon/UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md` —
  the canonical OrgTree/OrgPath specification this narrative paraphrases.
- `src/uiao/canon/adr/adr-035-orgpath-codebook-binding.md`
- `src/uiao/canon/adr/adr-036-dynamic-group-provisioning.md`
- `src/uiao/canon/adr/adr-037-admin-unit-provisioning.md`
- `src/uiao/canon/adr/adr-038-device-plane-orgpath.md`
- `src/uiao/canon/adr/adr-039-policy-targeting.md`
- `src/uiao/canon/adr/adr-040-drift-engine.md`
- `src/uiao/canon/adr/adr-041-uiao-git-infrastructure.md` — the actual
  Gitea-on-IIS infrastructure ADR (the source `.docx` cites it as ADR-001)
- `src/uiao/canon/adr/adr-048-orgpath-attribute-selection.md`
