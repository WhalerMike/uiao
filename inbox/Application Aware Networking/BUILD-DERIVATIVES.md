# Building the AAN derivatives (.docx, .pptx, .zip)

> How the rendered/binary deliverables are produced. The `.qmd`/`.md` sources, the
> figures (`figs/*.svg` + `*.png`), the deck specs (`decks/*.yaml`), and the
> generated `.pptx` decks are tracked in git; the `.docx` renders and the
> distribution `.zip` are built **locally** (there is no cloud renderer in the
> Claude Code web environment, and the old `aan-docx-regen` CI job was removed).

## What is tracked in git today

| Artifact | Tracked? | How it's produced |
|---|---|---|
| Book sources `Vol_*_Book_*.qmd`, plans/`.md` | ✅ | authored |
| Figures `figs/*.svg` (SSOT) + `*.png` | ✅ | `scripts/render_svg_images.py` (SVG→PNG at 3×, ADR-093) |
| Deck specs `decks/Vol_*_Book_*.yaml` | ✅ | authored |
| Briefing decks `Vol_*_Book_*.pptx` | ✅ | `uiao generate aan-deck` (python-pptx) — buildable anywhere |
| Book renders `Vol_*_Book_*.docx` | ⚠️ allowlisted, **build locally** | `./render_all_docx.sh` — Pandoc + `aan-reference.docx` + `aan-callouts.lua` (AAN callout styling, no Quarto needed) |
| AAN reference doc `aan-reference.docx` | ✅ | `build_aan_reference.py` (adds callout/banner styles to `lz-reference.docx`) |
| Distribution kit `AAN_Federal_Series_Complete_<DATE>ET.zip` | ✅ (one, datecoded) | local rebuild (authoring-spec §1) |

## 1. Briefing decks (.pptx) — buildable in CI/cloud

```bash
uiao generate aan-deck \
  --spec "inbox/Application Aware Networking/decks/Vol_VII_Book_00.yaml" \
  --out  "inbox/Application Aware Networking/Vol_VII_Book_00_FedAAN_ServiceNow_Automation_Overview.pptx"
```

Repeat per `decks/*.yaml`. The `.pptx` are allowlisted (`Vol_*_Book_*.pptx`) so they
ride with their books in git.

## 2. Book renders (.docx)

> The book `.docx` are rendered with **Pandoc** (`pypandoc-binary`) using the AAN
> reference doc **`aan-reference.docx`** and the **`aan-callouts.lua`** filter, so
> text, tables, figures **and the callout/banner boxes** carry house style. The
> callouts (`.callout-important/note/tip/warning`, the `.fouo-banner`, and the
> `.exec-summary` block) render as shaded, bordered, palette-colored boxes rather
> than plain content. This is the **portable substitute for `quarto render`**:
> Quarto's own installer is a GitHub-release download that this environment's
> egress policy blocks, so the reference-doc + Lua-filter path reproduces the AAN
> callout styling without Quarto.

**How the callout styling works.** Pandoc's docx writer can only paint paragraph
shading/borders through *named* paragraph styles carried in the reference doc.
`build_aan_reference.py` extends `lz-reference.docx` with the `CalloutWarning`,
`CalloutImportant`, `CalloutNote`, `CalloutTip`, `CalloutCaution`, `ExecSummary`,
and `FouoBanner` styles (AAN palette shading + left accent border) → saves
`aan-reference.docx`. `aan-callouts.lua` then maps each callout/banner div class to
the matching style via the `custom-style` attribute the docx writer honors.

Render one book:

```bash
cd "inbox/Application Aware Networking"
PANDOC=/usr/local/lib/python3.11/dist-packages/pypandoc/files/pandoc
"$PANDOC" Vol_VII_Book_00_FedAAN_ServiceNow_Automation_Overview.qmd -f markdown \
  -o Vol_VII_Book_00_FedAAN_ServiceNow_Automation_Overview.docx \
  --reference-doc=aan-reference.docx --lua-filter=aan-callouts.lua --resource-path=.
```

Render the whole series (56 books) in one pass:

```bash
cd "inbox/Application Aware Networking"
python build_aan_reference.py   # (re)build aan-reference.docx if styles changed
./render_all_docx.sh            # renders every Vol_*_Book_*.docx in place
```

If **Quarto** ever becomes installable locally, `quarto render <book>.qmd --to docx`
is the native equivalent and supersedes the Pandoc render; the `docx:` format block
in each book still pins house style. The `Vol_*_Book_*.docx` outputs are allowlisted,
so a committed render rides with its source.

## 3. Distribution kit (.zip) — local rebuild (authoring-spec §1)

The datecoded kit bundles the rendered `.docx` + `.pptx` decks + the governance
`.docx`. Rebuild it **after** rendering the docx, carrying the Date Code in the
filename (`AAN_Federal_Series_Complete_YYYY-MM-DD_HHMMET.zip`), and **delete the
previously-coded zip** (newest code wins — exactly one kept). The current tracked
kit predates the Vol VII–IX work and should be rebuilt once the docx are rendered.

## Why the split

`.pptx` decks are generated from tracked YAML by a pure-Python tool, so they build
anywhere (including CI) and are committed. `.docx` needs the Quarto+Pandoc
toolchain, which the web environment does not carry; committing a stale or
un-rendered docx would be worse than none, so the render is a local step and the
allowlist simply keeps a locally-produced docx from being silently dropped.
