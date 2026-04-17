# `scripts/` — developer-run tooling

Thin helper scripts that developers and reviewers run on-demand. None
of these are CI-invoked (CI uses the workflows under
`.github/workflows/` directly); this directory is for **human-run**
supplements.

## Inventory

### `bootstrap.sh`

One-shot first-time setup for a fresh checkout: pip-install the
Python impl in dev mode, install pre-commit hooks, run the substrate
walker to confirm the workspace is intact.

```bash
make bootstrap
# or directly:
./scripts/bootstrap.sh
```

### `validate_schemas.py`

Validates every registry and manifest YAML against its pinned JSON
Schema. Mirrors what the `schema-validation.yml` workflow runs in
CI, so a local pass guarantees a CI pass.

```bash
make schemas
# or directly:
python3 scripts/validate_schemas.py
```

### `check-links.ps1`

PowerShell script that crawls the **rendered** UIAO Modernization
Atlas site at `https://whalermike.github.io/uiao/docs/` and
HEAD/GET-checks every link it finds. Reports non-200 status codes.

**Complements the lychee workflow** in
`.github/workflows/link-check.yml`:

| Tool | What it scans | When it runs |
|---|---|---|
| `lychee` (CI) | source Markdown / Quarto Markdown link patterns | every PR |
| `check-links.ps1` | rendered HTML link graph on the live site (after Quarto `.qmd → .html` rewrite, after Pages URL-mangling) | on-demand, human-run |

Different jobs; both are needed. lychee catches broken links before
they ship; this script catches whatever lychee can't see until the
site renders (Quarto-rewritten paths, Pages-specific URL shape).

**Requires:** PowerShell 7+ (`pwsh`), available on Windows, macOS,
and Linux.

```bash
make check-links
# override URL or depth:
make check-links URL=https://whalermike.github.io/uiao/programs/ DEPTH=3
# or directly:
pwsh scripts/check-links.ps1
pwsh scripts/check-links.ps1 -StartUrl https://whalermike.github.io/uiao/ -MaxDepth 3
```

Exit code is `0` on all-200, `1` when any non-200 is found.

**Recommended cadence:** run before shipping a PR that changes
internal link structure (adds sidebar entries, introduces new
cross-document references, renames canon docs).

## Adding a new script here

- Write it so a human running it once knows what it did and what to
  do next — print useful progress, exit 0/non-0 meaningfully.
- Add a Makefile target so it's discoverable via `make help`.
- Add a row to the inventory above.
- If it should block CI, wire it into `.github/workflows/` instead —
  `scripts/` is explicitly the human-run layer.
