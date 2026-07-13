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

Render the whole series in one pass (the renderable `Vol_*_Book_*.qmd` books —
~56 rendered book files; the compliance spine registers 66 deliverables total,
including the Volume VIII chapters that render from `infoblox-ddi-book/*.md` and
the non-prose kits):

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
previously-coded zip** (newest code wins — exactly one kept).

One script does the whole rebuild:

```bash
cd "inbox/Application Aware Networking"
./build_distribution_kit.sh   # renders all book .docx + the full Vol VIII
                              # chapter set, seeds decks from the prior kit,
                              # writes the new datecoded zip
```

`build_distribution_kit.sh` seeds staging from the prior kit (so every `.pptx`
deck and governance doc is preserved — only Vol VII/IX decks exist as loose
files), then overwrites each book's `.docx` with a fresh render and **adds the
full Volume VIII set**: the overview book, all per-cloud chapters
(`infoblox-ddi-book/01-azure.md … 05-vmware.md`), Cross-Platform Operations, the
two ServiceNow chapters (07 Orchestration, 08 ServiceNow-Led Implementation),
Appendix A, and the `servicenow-app` scoped-app kit as source. Earlier kits
represented Volume VIII by its overview book only; the Vol VIII chapters live at
repo-root `infoblox-ddi-book/` and are bound into the series via the compliance
spine (each with an explicit `source:` path).

## Why the split

`.pptx` decks are generated from tracked YAML by a pure-Python tool, so they build
anywhere (including CI) and are committed. `.docx` needs the Quarto+Pandoc
toolchain, which the web environment does not carry; committing a stale or
un-rendered docx would be worse than none, so the render is a local step and the
allowlist simply keeps a locally-produced docx from being silently dropped.

## Date-code convention (single source per book)

Each book's authoritative Date Code is its front-matter `date:`. Figure alt-text
that carries its own "Date Code" must match the book's front-matter date, not a
stale render timestamp — a figure Date Code that lags the book's `date:` is a
known drift smell a reviewer will notice. When a figure is regenerated, stamp it
with the current book date; when a book's content changes materially, refresh its
figures so their Date Codes do not fall behind. The series target is one date per
book, carried from the front matter into its figures.
