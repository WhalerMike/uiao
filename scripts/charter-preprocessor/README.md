# charter-preprocessor

Tools for converting OneDrive charter source files (V3 / V4 / V4U / UIAO-V1)
into ingestion-ready candidates for `src/uiao/canon/charter/`.

## Why this exists

The OneDrive foundational canon (`Application_Aware_Networking_White_Paper_by_Mike/`)
predates the UIAO substrate and was never ingested into the repo. Source
files carry pandoc-conversion artifacts (escape characters, code-fence
wrapping), structural corruption (verbatim-duplicate sections), and
non-ASCII typography (non-breaking hyphens) that need a preprocessing
pass before they can be canonized.

[Charter Restoration Plan PR-A1](https://github.com/WhalerMike/uiao/pull/522)
ingested CHARTER-001 (UIAO-V1 main spec) using a small one-off cleanup
script. PR-A2a uses `atobz_preprocess.py` to handle the larger
`AtoBZ_clean.md` master appendix file (~928KB, 35,669 lines, ~50%
verbatim duplication).

## Tools

### `atobz_preprocess.py` — AtoBZ master-appendix preprocessor

Splits `AtoBZ_clean.md` by `# Appendix X` H1 headings, dedups duplicate
appendix sections (keep first occurrence's content; drop subsequent),
reorders alphabetically, normalizes non-breaking hyphens, and flags
audit-named invented acronyms with `<!-- ARCHITECT-CONFIRM ... -->`
markers.

```bash
python scripts/charter-preprocessor/atobz_preprocess.py \
    inbox/_audit-input/AtoBZ-source.md \
    inbox/drafts/CHARTER-001-APPENDICES-cleaned.md \
    inbox/drafts/CHARTER-001-APPENDICES-preprocessing-report.json
```

Outputs:
- A cleaned markdown file (~50% smaller than source)
- A JSON report listing every dedup decision, similarity hash, and
  invented-acronym annotation

The preprocessing pass is **non-destructive** — content is kept,
duplicate copies are dropped, and every decision is recorded in the
JSON report for architect review. Companion human-readable report at
`inbox/drafts/CHARTER-001-APPENDICES-preprocessing-report.md`.

## Workflow

1. Copy the OneDrive source into `inbox/_audit-input/` (gitignored;
   ASCII path avoids shell-encoding issues with the OneDrive em-dashes
   and non-breaking hyphens):
   ```bash
   cp "$ONEDRIVE/UIAO-V1/AtoBZ_clean.md" inbox/_audit-input/AtoBZ-source.md
   ```
2. Run the preprocessor, writing draft + report to `inbox/drafts/`:
   ```bash
   python scripts/charter-preprocessor/atobz_preprocess.py \
       inbox/_audit-input/AtoBZ-source.md \
       inbox/drafts/CHARTER-001-APPENDICES-cleaned.md \
       inbox/drafts/CHARTER-001-APPENDICES-preprocessing-report.json
   ```
3. Review the human-readable report at
   `inbox/drafts/CHARTER-001-APPENDICES-preprocessing-report.md`.
4. After architect signoff, run the ingestion pass (PR-A2b — separate
   PR, separate tooling once authored):
   - Resolve every `<!-- ARCHITECT-CONFIRM ... -->` marker per architect
     decision (confirm canonical or replace).
   - Move the cleaned file to
     `src/uiao/canon/charter/CHARTER-001-APPENDICES.md`.
   - Add proper canon frontmatter (`document_id: CHARTER-001-APPENDICES`,
     `tier: foundational`, `supersedable: false`, `load_order: 0`,
     provenance block).
   - Update `charter-registry.yaml` (move from `pending_ingestion[]`
     into `charter_documents[]`).
   - Remove the draft and report from `inbox/drafts/`.

## Dependencies

Stdlib only. Tested on CPython 3.13+ and 3.14.

## Future tools (not yet built)

- `v4u_preprocess.py` for the V4U feeder docs (CHARTER-002..005,
  PR-A3..A4 scope).
- `v3_legacy_preprocess.py` for V3 long-form + TwoPager (CHARTER-V3-LEGACY,
  PR-A5 scope).
- A telemetry-PDF text-extractor for the Federal Cloud Telemetry Gap
  evidence file (CHARTER-EVIDENCE-TELEMETRY, PR-A6 scope).
