# UIAO Lifecycle Banner Extension

Quarto shortcode that renders a per-page lifecycle banner from frontmatter
per [ADR-082](../../adr/adr-082-status-label-lifecycle-policy.qmd) — replaces
hand-authored callout blocks with a rule-driven banner read from the
`lifecycle:` family of frontmatter fields.

## Usage

Add to any `.qmd` page that has `lifecycle:` frontmatter:

```markdown
{{< lifecycle-banner >}}
```

The banner renders automatically based on the frontmatter `lifecycle:`
value (`aspirational` / `adopted` / `superseded` / `deprecated`). Pages
without `lifecycle:` produce no output, so it's safe to add the
shortcode unconditionally — backfill (ADR-082 Phases 4-5) populates
the frontmatter incrementally.

## Behavior matrix

| Frontmatter | Banner |
|---|---|
| `lifecycle: aspirational` | Yellow `callout-warning` — "Aspirational — canonically declared, not yet fully adopted" |
| `lifecycle: adopted` + `tiers_adopted: [1, 3]` | Green `callout-note` — "Adopted at Tier 1 (Passive Observation), Tier 3 (Active Substrate)" |
| `lifecycle: superseded` + `superseded_by: path/to/successor.qmd` | Red `callout-important` — "Superseded. See: [path]" |
| `lifecycle: deprecated` + `deprecated_replacement: ...` (optional) | Yellow `callout-warning` — "Deprecated. See: [path]" or "No replacement was declared." |
| No `lifecycle:` field | No banner (empty output) |
| Unknown `lifecycle:` value | Red `callout-important` — flags the typo; scanner will also fail strict mode |

## Tier names (per ADR-076)

The banner expands tier numbers to their canonical names:

- Tier 1 — Passive Observation
- Tier 2 — Transformative Authoring
- Tier 3 — Active Substrate
- Tier 4 — Active Services
- Tier 5 — Embedded Libraries

If a `tiers_adopted` value is outside `[1, 5]`, the banner emits "Tier N"
without a name and `scripts/scan_lifecycle_consistency.py` flags it as an
error.

## Sibling tooling

- [`scripts/scan_lifecycle_consistency.py`](../../../scripts/scan_lifecycle_consistency.py)
  — validates the same frontmatter fields the banner reads. Run with
  `--strict` to fail builds on inconsistency.
- [`src/uiao/schemas/metadata-schema.json`](../../../src/uiao/schemas/metadata-schema.json)
  — schema declaration for the lifecycle fields.
- [ADR-082](../../adr/adr-082-status-label-lifecycle-policy.qmd) —
  the doctrine establishing the lifecycle model.

## Extension layout

```
docs/_extensions/uiao-lifecycle/
├── _extension.yml          # Quarto extension manifest
├── lifecycle-banner.lua    # The shortcode implementation
└── README.md               # This file
```

No additional dependencies; Quarto's built-in Lua filter runtime executes
the shortcode at render time.
