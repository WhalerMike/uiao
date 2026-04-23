# Customer Document Tree — Authoritative Directory Map

> **Scope:** this file is the canonical, authoritative directory tree for
> the Customer Documents site under `/docs/customer-documents/` in the
> unified UIAO monorepo. It mirrors the published portal at
> <https://whalermike.github.io/uiao/customer-documents/>.
>
> **Status:** post‑migration, repo‑aligned. Any divergence between this
> tree and the on-disk layout is CI-blocking (`customer-docs-tree-check`).

## Tree

```
/docs/customer-documents/
├── index.qmd                                   # Portal landing page
├── ROADMAP.qmd                                 # Authoring backlog
├── TREE.md                                     # This file — authoritative tree
│
├── executive-briefs/
│   ├── index.qmd
│   ├── drift-engine-overview.md
│   ├── evidence-fabric-overview.md
│   ├── governance-os-overview.md
│   ├── modernization-overview.md
│   └── zero-trust-overview.md
│
├── architecture-series/
│   ├── index.qmd
│   ├── boundary-impact-model.md
│   ├── drift-engine.md
│   ├── evidence-chain.md
│   ├── six-plane-architecture.md
│   └── three-layer-rule-model.md
│
├── modernization-specs/
│   ├── index.qmd
│   ├── _template/
│   │   └── generic-template.md
│   ├── cloud/cloud.md
│   ├── identity/identity.md
│   ├── sase/sase.md
│   ├── sdwan/sdwan.md
│   ├── telemetry/telemetry.md
│   └── zero-trust/zero-trust.md
│
├── adapter-specs/                              # 1:1 with adapter-registry.yaml
│   ├── index.qmd
│   ├── cyberark/
│   │   ├── cyberark.qmd
│   │   ├── IMAGE-PROMPTS.md
│   │   └── images/
│   ├── entra-id/                (same triad: <slug>.qmd + IMAGE-PROMPTS.md + images/)
│   ├── infoblox/
│   ├── intune/
│   ├── m365/
│   ├── mainframe/
│   ├── palo-alto/
│   ├── patch-state/
│   ├── pki-ca/
│   ├── scuba/
│   ├── scubagear/
│   ├── service-now/
│   ├── siem/
│   ├── stig-compliance/
│   ├── terraform/
│   └── vuln-scan/
│
├── validation-suites/
│   ├── index.qmd
│   ├── adapters/                               # 1:1 with adapter-specs/
│   │   ├── bluecat-address-manager/            # in-flight, not yet paired with spec
│   │   ├── cyberark/cyberark.qmd
│   │   ├── entra-id/
│   │   ├── infoblox/
│   │   ├── intune/
│   │   ├── m365/
│   │   ├── mainframe/
│   │   ├── palo-alto/
│   │   ├── patch-state/
│   │   ├── pki-ca/
│   │   ├── scuba/
│   │   ├── scubagear/
│   │   ├── service-now/
│   │   ├── siem/
│   │   ├── stig-compliance/
│   │   ├── terraform/
│   │   └── vuln-scan/
│   └── domains/                                # 1:1 with modernization-specs/
│       ├── _template/generic-template.md
│       ├── cloud/cloud.md
│       ├── identity/identity.md
│       ├── sase/sase.md
│       ├── sdwan/sdwan.md
│       ├── telemetry/telemetry.md
│       └── zero-trust/zero-trust.md
│
├── case-studies/
│   ├── index.qmd
│   ├── cloud-boundary-case-study.md
│   ├── federal-modernization-case-study.md
│   └── identity-modernization-case-study.md
│
├── whitepapers/
│   ├── index.qmd
│   ├── modernization-governance-whitepaper.md
│   ├── scubagear-integration-whitepaper.md
│   ├── uiao-governance-os-whitepaper.md
│   └── zero-trust-governance-whitepaper.md
│
└── executive-governance-series/
    ├── index.qmd
    ├── 00-introduction/index.md
    ├── 01-modernization-arc/index.md
    ├── 02-governance-os-overview/index.md
    ├── 03-boundary-impact-model/index.md
    ├── 04-evidence-chain/index.md
    ├── 05-governance-through-specification-and-validation/index.md
    ├── 06-program-model/index.md
    ├── 07-leadership-alignment/index.md
    └── 08-executive-summary/index.md
```

## Section map

| Folder | Purpose | Canon source | Authoring posture |
|---|---|---|---|
| `executive-briefs/` | Single-page leadership summaries | `src/uiao/canon/` | Authored from canon |
| `architecture-series/` | Conceptual explainers, 2–4 pp each | `docs/docs/01_UnifiedArchitecture.qmd` | Authored under pseudonym |
| `modernization-specs/` | Cross-adapter specs by domain | `src/uiao/canon/modernization-registry.yaml` | Canon-derived frontmatter, authored body |
| `adapter-specs/` | Per-adapter operational design | `src/uiao/canon/adapter-registry.yaml` | Canon-derived (1:1 with registry) |
| `validation-suites/adapters/` | Per-adapter validation | `src/uiao/canon/adapter-registry.yaml` | Canon-derived (1:1 with adapter-specs) |
| `validation-suites/domains/` | Per-domain validation | `src/uiao/canon/modernization-registry.yaml` | Canon-derived (1:1 with modernization-specs) |
| `case-studies/` | Real-world deployment narratives | Engagement material | Authored, review-gated |
| `whitepapers/` | Long-form external deep-dives | Multiple canon anchors | Authored, review-gated |
| `executive-governance-series/` | 9-chapter governance narrative | Multiple canon anchors | Authored, chapter-by-chapter |

## Per-adapter leaf layout

Every `adapter-specs/<adapter-id>/` and
`validation-suites/adapters/<adapter-id>/` folder carries the triad:

```
<adapter-id>/
├── <adapter-id>.qmd       # content with frontmatter, canon-derived
├── IMAGE-PROMPTS.md       # per-document image prompts (schema §7.2)
└── images/
    └── .gitkeep           # (and generated image artifacts; LFS-tracked)
```

## Invariants

1. Every `.qmd` / `.md` file under `/docs/customer-documents/` carries YAML
   frontmatter with `canon-source` and `derived-from` fields.
2. Every entry in `adapter-specs/<adapter-id>/` **should** have a matching
   entry in `validation-suites/adapters/<adapter-id>/` (and vice versa).
   In-flight adapters may temporarily appear on only one side with an
   `aspirational: true` flag.
3. Every entry in `modernization-specs/<domain>/` **must** have a matching
   entry in `validation-suites/domains/<domain>/` (and vice versa).
4. No folder under `/docs/customer-documents/` may contain internal
   governance canon, substrate control surfaces, or authoring workflow
   material. Those live under `/src/uiao/canon/` and `/docs/modernization/`.
5. Per-adapter filenames drop the legacy `ats-` / `avs-` prefixes — the
   folder name carries adapter identity.

## Drift

Divergence between this tree and the on-disk layout is detected by
`scripts/tools/sync_canon.py` and surfaced as a `canon-sync`-labeled PR.
The tree check is CI-blocking on `main`.

## Cross-references

- [Portal landing page](index.qmd)
- [Authoring roadmap](ROADMAP.qmd)
- [`docs/_quarto.yml`](../_quarto.yml) — navbar and sidebar wiring
- [`scripts/tools/sync_canon.py`](../../scripts/tools/sync_canon.py) — the
  canonical drift detector / scaffolder
- [`docs/governance/ARCHITECTURE.md`](../governance/ARCHITECTURE.md) §5 —
  architectural context for the customer documentation tree
