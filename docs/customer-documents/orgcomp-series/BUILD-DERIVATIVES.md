# Building the OrgComp derivatives (.docx, .pptx, .zip)

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
| Book renders `Vol_*_Book_*.docx` | ⚠️ allowlisted, **build locally** | `./render_all_docx.sh` — Pandoc + `orgcomp-reference.docx` + `orgcomp-callouts.lua` (fast batch path; `quarto render` produces the same docx — see §2) |
| AAN reference doc `orgcomp-reference.docx` | ✅ | `build_orgcomp_reference.py` (adds callout/banner styles to `lz-reference.docx`) |
| Distribution kit `OrgComp_Federal_Series_Complete_<DATE>ET.zip` | ✅ (one, datecoded) | local rebuild (authoring-spec §1) |

## 1. Briefing decks (.pptx) — buildable in CI/cloud

```bash
uiao generate aan-deck \
  --spec "docs/customer-documents/orgcomp-series/decks/Vol_VII_Book_00.yaml" \
  --out  "docs/customer-documents/orgcomp-series/Vol_VII_Book_00_OrgComp_ServiceNow_Automation_Overview.pptx"
```

Repeat per `decks/*.yaml`. The `.pptx` are allowlisted (`Vol_*_Book_*.pptx`) so they
ride with their books in git.

## 2. Book renders (.docx)

> The book `.docx` are rendered with **Pandoc** (`pypandoc-binary`) using the AAN
> reference doc **`orgcomp-reference.docx`** and the **`orgcomp-callouts.lua`** filter, so
> text, tables, figures **and the callout/banner boxes** carry house style. The
> callouts (`.aan-important/note/tip/warning/caution`, the `.fouo-banner`, and the
> `.exec-summary` block) render as shaded, bordered, palette-colored boxes rather
> than plain content.

**Both renderers work; both are kept on purpose.** Quarto **is** installed locally
(1.9.37 at the time of writing) and `quarto render <book>.qmd --to docx` succeeds.
Earlier revisions of this doc described the Pandoc path as a *forced workaround* —
"Quarto's installer is a GitHub-release download that egress policy blocks." That
justification is **obsolete**: it described the Claude Code web sandbox, not a
local checkout. The Pandoc path is kept because it is **faster**, not because
Quarto is unavailable.

| Renderer | Role | Measured (Book 00, 1,370 lines) |
|---|---|---|
| **Pandoc** (`render_all_docx.sh`) | Fast batch `.docx` for the kit rebuild — ~56 books per pass | **~1.6 s/book** |
| **Quarto** (`quarto render`) | Renders a book from **its own front matter** — the `format:` block (`html` + `docx`) and `filters:` are applied natively, with no CLI flags. The only path to the `html` format (`embed-resources` + `lz-style.css`); `render_all_docx.sh` emits docx only. | **~10.5 s/book** (~6× slower) |

Use Pandoc for the docx loop and the kit; reach for Quarto when you need the HTML
format, or to confirm a book renders correctly from the front matter alone.

**The two renderers agree.** Since **PR #1230** the AAN callout divs are `.aan-*`,
**not** Quarto's `.callout-*` — deliberately. Quarto *claims* `.callout-*` and
rewrites those divs inside its own pipeline **before any user filter runs**, so a
Quarto render of a `.callout-*` book silently dropped every house style and
substituted Quarto's own red-bordered widget; pointing the front matter at
`orgcomp-reference.docx` did not help, because the filter never saw a div Quarto had
already taken. Quarto has no opinion about `.aan-important`, so renaming the
classes takes them back: **one filter (`orgcomp-callouts.lua`) plus `lz-style.css` now
drives both renderers to identical output**, verified across 6 books
(`pandoc@HEAD == pandoc@renamed == quarto@renamed`, all six styles including
`ExecSummary`). `check_callout_classes.py` is the pre-commit gate that keeps it
true. Books are `.aan-*`-only; the `OrgComp-Training-Program/` pages still use native
`.callout-*` and are not part of the book render.

**Every book declares its reference doc.** Since **PR #1229** all 58 book `.qmd`
carry `reference-doc: orgcomp-reference.docx` in front matter. They previously said
`lz-reference.docx` while `render_all_docx.sh` passed `--reference-doc=orgcomp-reference.docx`
— Pandoc ignores the *nested* `format: docx:` key, so the CLI silently won and the
front matter was inert. The bug was invisible under Pandoc and would only have
surfaced under Quarto, which *does* honor that key. Front matter and CLI now agree.

**How the callout styling works.** Pandoc's docx writer can only paint paragraph
shading/borders through *named* paragraph styles carried in the reference doc.
`build_orgcomp_reference.py` extends `lz-reference.docx` with the `CalloutWarning`,
`CalloutImportant`, `CalloutNote`, `CalloutTip`, `CalloutCaution`, `ExecSummary`,
and `FouoBanner` styles (AAN palette shading + left accent border) → saves
`orgcomp-reference.docx`. `orgcomp-callouts.lua` then maps each callout/banner div class to
the matching style via the `custom-style` attribute the docx writer honors.

Render one book:

```bash
cd "docs/customer-documents/orgcomp-series"
PANDOC=/usr/local/lib/python3.11/dist-packages/pypandoc/files/pandoc
"$PANDOC" Vol_VII_Book_00_OrgComp_ServiceNow_Automation_Overview.qmd -f markdown \
  -o Vol_VII_Book_00_OrgComp_ServiceNow_Automation_Overview.docx \
  --reference-doc=orgcomp-reference.docx --lua-filter=orgcomp-callouts.lua --resource-path=.
```

Render the whole series in one pass (the renderable `Vol_*_Book_*.qmd` books —
~56 rendered book files; the compliance spine registers 66 deliverables total,
including the Volume VIII chapters that render from `infoblox-ddi-book/*.md` and
the non-prose kits):

```bash
cd "docs/customer-documents/orgcomp-series"
python build_orgcomp_reference.py   # (re)build orgcomp-reference.docx if styles changed
./render_all_docx.sh            # renders every Vol_*_Book_*.docx in place
```

Or render one book with **Quarto**, which reads the `format:`/`filters:` blocks
straight from the book's front matter (no flags needed):

```bash
cd "docs/customer-documents/orgcomp-series"
quarto render Vol_0_Book_00_OrgComp_Executive_Summary.qmd --to docx
```

Quarto does **not** supersede the Pandoc pass — since PR #1229/#1230 the two agree,
and Pandoc is ~6× faster across a ~56-book batch. Note that `quarto render` will
not write outside the project directory, so use its default output location rather
than an absolute `-o` path. The `Vol_*_Book_*.docx` outputs are allowlisted, so a
committed render rides with its source.

## 3. Distribution kit (.zip) — local rebuild (authoring-spec §1)

The datecoded kit bundles the rendered `.docx` + `.pptx` decks + the governance
`.docx`. Rebuild it **after** rendering the docx, carrying the Date Code in the
filename (`OrgComp_Federal_Series_Complete_YYYY-MM-DD_HHMMET.zip`), and **delete the
previously-coded zip** (newest code wins — exactly one kept).

One script does the whole rebuild:

```bash
cd "docs/customer-documents/orgcomp-series"
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
anywhere (including CI) and are committed. `.docx` needs a Pandoc-or-Quarto
toolchain that the Claude Code web environment does not carry, and the
`aan-docx-regen` CI job was removed — so no cloud renderer produces them. This is
an **environment** split, not a tool limitation: a local checkout has both
renderers. Committing a stale or un-rendered docx would be worse than none, so the
render is a local step and the allowlist simply keeps a locally-produced docx from
being silently dropped.

## Date-code convention (single source per book)

Each book's authoritative Date Code is its front-matter `date:`. Figure alt-text
that carries its own "Date Code" must match the book's front-matter date, not a
stale render timestamp — a figure Date Code that lags the book's `date:` is a
known drift smell a reviewer will notice. When a figure is regenerated, stamp it
with the current book date; when a book's content changes materially, refresh its
figures so their Date Codes do not fall behind. The series target is one date per
book, carried from the front matter into its figures.
