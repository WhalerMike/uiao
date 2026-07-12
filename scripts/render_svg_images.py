#!/usr/bin/env python3
"""Rasterize committed SVG figure sources to PNG — UIAO image pipeline v2.

Source of truth is the ``<name>.svg`` file; the ``<name>.png`` beside it is a
build artifact. This REPLACES the Gemini "NanoBanana" generator (see ADR-093):
no AI runs at render time, so output is deterministic and text is always exactly
what the SVG says. SVGs are authored by Claude Code (or by hand) against the
house style in ``src/uiao/canon/svg-style/``.

For every ``<name>.svg`` under the scan roots this writes a sibling
``<name>.png`` plus a ``<name>.png.json`` sidecar using the SAME schema as
``generate_images.py`` (helpers are imported from it so the contract can't
drift), with ``generator = "claude-svg-v1"``.

Cache: a figure is skipped when its sidecar's ``prompt_sha256`` already matches
the current SVG's hash AND the PNG exists. ``--force`` re-renders everything.

Rasterizer: prefers ``cairosvg``; falls back to Playwright (Chromium), which is
already a declared ``[visuals]`` dependency and is required for any SVG that
uses ``<foreignObject>`` / web fonts.

Usage:
    python scripts/render_svg_images.py                 # render all changed SVGs
    python scripts/render_svg_images.py path/to/fig.svg # render specific files
    python scripts/render_svg_images.py docs/.../images  # render a directory
    python scripts/render_svg_images.py --force          # ignore cache
    python scripts/render_svg_images.py --dry-run        # report only, no API/render
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
from pathlib import Path

# Reuse the v1 provenance helpers so the sidecar/manifest contract stays in
# lockstep with generate_images.py. (generate_images imports the Gemini SDK
# lazily inside functions, so importing the module here pulls in NO google deps.)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_images import (  # noqa: E402
    REPO_ROOT,
    _now_iso_utc,
    embed_png_metadata,
    sha256_file,
    sha256_text,
    write_sidecar,
)

GENERATOR = "claude-svg-v1"
DEFAULT_SCALE = 3.0  # rasterize at 3x the SVG viewBox — enough pixels to stay
# crisp when a reader pinch-zooms an embedded PNG in a .docx on a phone (a raster
# has no detail beyond its own resolution; 3x ≈ 550 ppi at a 6.5in display).
MAX_WIDTH = 3600  # cap output width (px)
SCAN_ROOTS = [REPO_ROOT / "docs", REPO_ROOT / "src" / "uiao" / "canon"]
SKIP_PARTS = {"_site", "_freeze", ".quarto", "node_modules", ".git", ".venv"}


def find_svgs(roots: list[Path]) -> list[Path]:
    out: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*.svg"):
            if any(part in SKIP_PARTS for part in p.parts):
                continue
            out.append(p)
    return sorted(set(out))


def viewbox_dims(svg_text: str) -> tuple[float, float]:
    m = re.search(r'viewBox\s*=\s*["\']\s*[\d.]+\s+[\d.]+\s+([\d.]+)\s+([\d.]+)', svg_text)
    if m:
        return float(m.group(1)), float(m.group(2))
    w = re.search(r'\bwidth\s*=\s*["\']([\d.]+)', svg_text)
    h = re.search(r'\bheight\s*=\s*["\']([\d.]+)', svg_text)
    if w and h:
        return float(w.group(1)), float(h.group(1))
    return 1280.0, 720.0


def aspect_label(w: float, h: float) -> str:
    r = (w / h) if h else 1.0
    for aw, ah in [(16, 9), (4, 3), (1, 1), (3, 2), (21, 9)]:
        if abs(r - aw / ah) < 0.04:
            return f"{aw}:{ah}"
    return f"{int(round(w))}:{int(round(h))}"


def rasterize(svg_path: Path, png_path: Path, out_w: int, out_h: int) -> str:
    """Render SVG -> PNG. Prefer cairosvg; fall back to Playwright (Chromium)."""
    svg_bytes = svg_path.read_bytes()
    cairo_err = None
    try:
        import cairosvg  # type: ignore

        cairosvg.svg2png(
            bytestring=svg_bytes,
            write_to=str(png_path),
            output_width=out_w,
            output_height=out_h,
            background_color="white",
        )
        return "cairosvg"
    except Exception as e:  # noqa: BLE001
        cairo_err = e
    try:
        from playwright.sync_api import sync_playwright  # type: ignore

        data_uri = "data:image/svg+xml;base64," + base64.b64encode(svg_bytes).decode()
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(
                viewport={"width": out_w, "height": out_h},
                device_scale_factor=1,
            )
            page.goto(data_uri)
            page.screenshot(path=str(png_path), omit_background=False)
            browser.close()
        return "playwright"
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(
            f"No SVG rasterizer available. cairosvg error: {cairo_err}; "
            f"playwright error: {e}. Install one: `pip install cairosvg` "
            f"or `pip install playwright && playwright install chromium`."
        ) from e


def derive_ids(svg_path: Path) -> tuple[str, str]:
    """placeholder_id + slug from filename: <...>-(diagram|image|figure)-NN-<rest>."""
    m = re.search(r"-(?:diagram|image|figure)-(\d{1,3})-(.+)$", svg_path.stem, re.I)
    if m:
        return f"IMAGE-{int(m.group(1)):02d}", m.group(2)
    return "IMAGE-01", svg_path.stem


def main() -> int:
    ap = argparse.ArgumentParser(description="Rasterize committed SVG figures to PNG.")
    ap.add_argument("paths", nargs="*", help="Specific .svg files or dirs (default: scan all roots)")
    ap.add_argument("--force", action="store_true", help="Re-render even if the cache matches")
    ap.add_argument("--dry-run", action="store_true", help="Report only; no rendering")
    ap.add_argument("--scale", type=float, default=DEFAULT_SCALE, help="Rasterize at N x viewBox")
    args = ap.parse_args()

    if args.paths:
        svgs: list[Path] = []
        for raw in args.paths:
            p = Path(raw)
            if not p.is_absolute():
                p = (REPO_ROOT / p).resolve()
            if p.is_dir():
                svgs += find_svgs([p])
            elif p.suffix.lower() == ".svg":
                svgs.append(p)
        svgs = sorted(set(svgs))
    else:
        svgs = find_svgs(SCAN_ROOTS)

    print(f"SVG sources found: {len(svgs)}")
    rendered = skipped = failed = 0
    for svg in svgs:
        text = svg.read_text(encoding="utf-8")
        prompt_sha = sha256_text(text)
        png = svg.with_suffix(".png")
        sidecar = png.with_suffix(".png.json")

        if not args.force and png.exists() and sidecar.exists():
            try:
                meta = json.loads(sidecar.read_text(encoding="utf-8"))
                if meta.get("prompt_sha256") == prompt_sha and meta.get("generator") == GENERATOR:
                    skipped += 1
                    continue
            except Exception:  # noqa: BLE001
                pass

        vw, vh = viewbox_dims(text)
        out_w = int(min(vw * args.scale, MAX_WIDTH))
        out_h = int(round(out_w * (vh / vw)))
        pid, slug = derive_ids(svg)
        rel = svg.relative_to(REPO_ROOT)

        if args.dry_run:
            print(f"  [dry] {rel} -> {png.name} ({out_w}x{out_h})")
            rendered += 1
            continue

        try:
            engine = rasterize(svg, png, out_w, out_h)
            fsha = sha256_file(png)
            write_sidecar(
                png,
                document=None,
                placeholder_id=pid,
                canonical_id=None,
                slug=slug,
                prompt_sha256=prompt_sha,
                generator=GENERATOR,
                file_sha256=fsha,
                aspect=aspect_label(vw, vh),
            )
            embed_png_metadata(
                png,
                canonical_id=None,
                prompt_sha256=prompt_sha,
                generator=GENERATOR,
                generated_at=_now_iso_utc(),
            )
            # PNG bytes change after tEXt embed — re-hash so the sidecar matches disk.
            fsha2 = sha256_file(png)
            if fsha2 != fsha:
                meta = json.loads(sidecar.read_text(encoding="utf-8"))
                meta["sha256"] = fsha2
                sidecar.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(f"  rendered {png.relative_to(REPO_ROOT)} via {engine} ({out_w}x{out_h})")
            rendered += 1
        except Exception as e:  # noqa: BLE001
            print(f"  FAILED {rel}: {e}")
            failed += 1

    print(f"\nDone. rendered={rendered} skipped={skipped} failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
