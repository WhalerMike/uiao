# Canon-spec figures — derived raster copies

The PNGs in this directory are **derived raster copies** used so that the
canon source specs (`../UIAO_002_*.md`, `../UIAO_003_*.md`) render their
figures correctly when browsed on GitHub and pass the `lychee` local-image
link check (which resolves `![](images/<name>.png)` relative to the `.md`).

**Source of truth lives elsewhere.** The authored SVG sources and the
CI-rasterized PNGs are under
[`docs/canon/images/`](../../../../docs/canon/images/) — that tree is inside
the Quarto project root (`docs/`), so the published site renders the same
figures and the image-gen CI (ADR-093, `scripts/render_svg_images.py`)
rasterizes the committed `*.svg` there.

Why the duplication: a single `images/<name>.png` literal in a canon `.md`
must resolve from two different base directories — `src/uiao/canon/` (GitHub
blob view + lychee) and `docs/canon/` (the `{{< include >}}` wrapper at render
time, which Quarto resolves relative to the wrapper, not the included file).
There is no single on-disk path that satisfies both, so the PNG is mirrored
here.

**To update a figure:** edit the SVG under `docs/canon/images/`, re-render
(`python scripts/render_svg_images.py docs/canon/images`), then copy the
updated `*.png` + `*.png.json` back into this directory.
