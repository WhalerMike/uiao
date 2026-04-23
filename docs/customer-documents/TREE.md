# Customer Document Tree — Authoritative Directory Map

> **Scope:** this file is the canonical, authoritative directory tree for
> the Customer Documents site under `/docs/customer-documents/` in the
> unified UIAO monorepo. It mirrors the published portal at
> <https://whalermike.github.io/uiao/customer-documents/>.
>
> **Status:** post‑consolidation, repo‑aligned. Any divergence between this
> tree and the on-disk layout is CI-blocking (`customer-docs-tree-check`).

## Tree

```
/docs/customer-documents/
├── index.qmd                            # Portal landing page (nav + exports)
├── TREE.md                              # This file — authoritative tree
│
├── executive-briefs/
│   ├── index.qmd
│   ├── governance-os-overview.qmd
│   ├── drift-engine-overview.qmd
│   ├── evidence-fabric-overview.qmd
│   ├── zero-trust-overview.qmd
│   └── modernization-overview.qmd
│
├── architecture-series/
│   ├── index.qmd
│   ├── six-plane-architecture.qmd
│   ├── three-layer-rule-model.qmd
│   ├── boundary-impact-model.qmd
│   ├── drift-engine.qmd
│   └── evidence-chain.qmd
│
├── modernization-specs/
│   ├── index.qmd
│   ├── identity.qmd
│   ├── cloud.qmd
│   ├── zero-trust.qmd
│   ├── sase.qmd
│   ├── sdwan.qmd
│   └── telemetry.qmd
│
├── adapter-specs/
│   ├── index.qmd
│   ├── cyberark.qmd
│   ├── entra-id.qmd
│   ├── infoblox.qmd
│   ├── intune.qmd
│   ├── m365.qmd
│   ├── mainframe.qmd
│   ├── palo-alto.qmd
│   ├── patch-state.qmd
│   ├── pki-ca.qmd
│   ├── scuba.qmd
│   ├── scubagear.qmd
│   ├── service-now.qmd
│   ├── siem.qmd
│   ├── stig-compliance.qmd
│   ├── terraform.qmd
│   └── vuln-scan.qmd
│
├── validation-suites/
│   ├── index.qmd
│   ├── adapters/
│   │   ├── cyberark.qmd
│   │   ├── entra-id.qmd
│   │   ├── infoblox.qmd
│   │   ├── intune.qmd
│   │   ├── m365.qmd
│   │   ├── mainframe.qmd
│   │   ├── palo-alto.qmd
│   │   ├── patch-state.qmd
│   │   ├── pki-ca.qmd
│   │   ├── scuba.qmd
│   │   ├── scubagear.qmd
│   │   ├── service-now.qmd
│   │   ├── siem.qmd
│   │   ├── stig-compliance.qmd
│   │   ├── terraform.qmd
│   │   └── vuln-scan.qmd
│   └── domains/
│       ├── identity.qmd
│       ├── cloud.qmd
│       ├── zero-trust.qmd
│       ├── sase.qmd
│       ├── sdwan.qmd
│       └── telemetry.qmd
│
├── case-studies/
│   ├── index.qmd
│   ├── identity-modernization-case-study.qmd
│   ├── cloud-boundary-case-study.qmd
│   └── federal-modernization-case-study.qmd
│
├── whitepapers/
│   ├── index.qmd
│   ├── uiao-governance-os-whitepaper.qmd
│   ├── zero-trust-governance-whitepaper.qmd
│   ├── modernization-governance-whitepaper.qmd
│   └── scubagear-integration-whitepaper.qmd
│
└── _exports/                            # Build-time only; not source-tracked
    ├── customer-documents.pdf
    ├── customer-documents.docx
    ├── customer-documents.epub
    ├── executive-briefs.{pdf,docx,epub}
    ├── architecture-series.{pdf,docx,epub}
    ├── modernization-specs.{pdf,docx,epub}
    ├── adapter-specs.{pdf,docx,epub}
    ├── validation-suites.{pdf,docx,epub}
    ├── case-studies.{pdf,docx,epub}
    └── whitepapers.{pdf,docx,epub}
```

## Section map

| Folder | Purpose | Canon source | Authoring posture |
|---|---|---|---|
| `executive-briefs/` | Single-page leadership summaries | `src/uiao/canon/` | Authored from canon |
| `architecture-series/` | Conceptual explainers, 2–4 pp each | `docs/docs/01_UnifiedArchitecture.qmd` | Authored under pseudonym |
| `modernization-specs/` | Cross-adapter specs by domain | `src/uiao/canon/modernization-registry.yaml` | Canon-derived frontmatter, authored body |
| `adapter-specs/` | Per-adapter operational design | `src/uiao/canon/adapter-registry.yaml` | Canon-derived (1:1 with registry) |
| `validation-suites/` | Tests, evidence, drift procedures | `src/uiao/canon/` | Canon-derived, paired 1:1 with specs |
| `case-studies/` | Real-world deployment narratives | Engagement material | Authored, review-gated |
| `whitepapers/` | Long-form external deep-dives | Multiple canon anchors | Authored, review-gated |

## Invariants

1. Every `.qmd` file under `/docs/customer-documents/` carries YAML
   frontmatter with `canon-source` and `derived-from` fields.
2. Every adapter entry in `adapter-specs/` has a matching entry in
   `validation-suites/adapters/` (and vice versa).
3. Every domain entry in `modernization-specs/` has a matching entry in
   `validation-suites/domains/` (and vice versa).
4. `_exports/` is not source-tracked; it is regenerated on every merge to
   `main` by the Quarto render pipeline.
5. No folder under `/docs/customer-documents/` may contain internal
   governance canon, substrate control surfaces, or authoring workflow
   material. Those live under `/src/uiao/canon/` and `/docs/modernization/`.

## Drift

Divergence between this tree and the on-disk layout is detected by
`src/uiao/tools/sync_canon.py` and surfaced as a `customer-docs-tree`-
labeled PR. The tree check is CI-blocking on `main`.

## Cross-references

- [Portal landing page](index.qmd)
- [`docs/_quarto.yml`](../_quarto.yml) — navbar and sidebar wiring
- [`AGENTS.md`](../../AGENTS.md) — module-level agent config
- [UIAO Canonical Document Specification v1.3](../../AGENTS.md) — source
  of truth for document families, frontmatter, and provenance rules.
