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
| Book renders `Vol_*_Book_*.docx` | ⚠️ allowlisted, **build locally** | `quarto render` — needs Quarto + Pandoc installed |
| Distribution kit `AAN_Federal_Series_Complete_<DATE>ET.zip` | ✅ (one, datecoded) | local rebuild (authoring-spec §1) |

## 1. Briefing decks (.pptx) — buildable in CI/cloud

```bash
uiao generate aan-deck \
  --spec "inbox/Application Aware Networking/decks/Vol_VII_Book_00.yaml" \
  --out  "inbox/Application Aware Networking/Vol_VII_Book_00_FedAAN_ServiceNow_Automation_Overview.pptx"
```

Repeat per `decks/*.yaml`. The `.pptx` are allowlisted (`Vol_*_Book_*.pptx`) so they
ride with their books in git.

## 2. Book renders (.docx) — local only

Requires **Quarto** + **Pandoc** (not present in the web environment). Per book:

```bash
cd "inbox/Application Aware Networking"
quarto render Vol_VII_Book_00_FedAAN_ServiceNow_Automation_Overview.qmd --to docx
```

The `docx:` format block in each book pins `reference-doc: lz-reference.docx` for
house style. The output `Vol_*_Book_*.docx` is now allowlisted, so `git add` will
track it if you choose to commit the render alongside the source.

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
