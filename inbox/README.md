# inbox/

Local processing scratch area. Drop raw inputs here — Word docs,
PDFs, spreadsheets, exports, screenshots — for extraction,
transformation, and eventual landing into their canonical home.

## Contract

1. **Not canon.** Nothing in this directory is authoritative. The
   substrate manifest (UIAO_200) does not list `inbox/` as a
   module. The substrate walker does not scan it.
2. **Not tracked by default.** The `.gitignore` in this directory
   excludes common binary formats (`*.docx`, `*.doc`, `*.pdf`,
   `*.xlsx`, `*.pptx`, `*.zip`) so raw inputs stay local and
   don't bloat history. This `README.md` is the only file here
   that is always tracked.
3. **Transient.** Once content is extracted into `core/`,
   `docs/`, or `impl/` with proper provenance, the raw input can
   be deleted from the inbox. Keep a record of what was
   processed in the target artifact's `provenance` block, not
   here.
4. **No canonical references into `inbox/`.** Nothing under
   `core/`, `docs/`, or `impl/` may link to a file inside this
   directory. If processing output needs to cite its source,
   the source must first land in an appropriate canonical
   location.

## Workflow

1. Drop the raw file into `inbox/`.
2. Extract content via the appropriate tool (Python, Quarto,
   pandoc, manual review).
3. Place the extracted content in its canonical home:
   - Canonical governance text → `src/uiao/canon/` (new UIAO_NNN
     entry in the document registry).
   - Derived narrative / explainer → `docs/narrative/` or
     `docs/docs/` (provenance block required).
   - Code or tooling → `impl/`.
4. Add a provenance block on the new artifact referencing the
   original source by filename and date (the file itself does
   not need to be kept).
5. Optionally remove the raw file from `inbox/` once
   extraction is verified.

### Pandoc bridge (`make inbox-convert`)

For `.docx` inputs, use the repo-provided pandoc bridge instead of
converting ad-hoc:

```bash
make inbox-status    # list docx files without an up-to-date .md sibling
make inbox-convert   # regenerate stale .md siblings via pandoc
```

The target runs `pandoc --from=docx --to=gfm --wrap=none
--markdown-headings=atx` against every `inbox/**/*.docx` and writes a
sibling `.md` only when the `.docx` is newer (idempotent). Extracted
media land under `inbox/.media/`. The `.md` siblings **are** tracked
(allowlisted in `.gitignore`) so they ship with the PR that promotes
the content to canon; the `.docx` sources stay local unless explicitly
opted-in via the `.gitignore` allowlist block.

Prerequisite: `pandoc >= 2.19`
(`winget install pandoc` / `brew install pandoc` / `apt install pandoc`).

## What this directory is *not*

- Not a publishing location. Nothing here is rendered by Quarto.
- Not a staging area for pull requests. Open a PR against the
  canonical destination, not against `inbox/`.
- Not a substitute for `core/`. If you find yourself writing
  canonical content here, move it to `src/uiao/canon/` with a proper
  document ID before the PR lands.

## CI behavior

- `metadata-validator.yml` scans `src/uiao/canon/` only — does not
  inspect `inbox/`.
- `schema-validation.yml` validates registries — does not
  inspect `inbox/`.
- `substrate-drift.yml` walks the substrate manifest — `inbox/`
  is intentionally not a declared module.
- `quarto.yml` renders `docs/` — does not render `inbox/`.
- `link-check.yml` does scan this `README.md`; keep its links
  internal and valid.
