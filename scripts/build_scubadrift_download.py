#!/usr/bin/env python3
"""Build the ScubaDrift standalone download set (ADR: no committed binaries).

Produces, into ``--out``:

* ``scubadrift-<version>.zip`` — the ScubaDrift standalone set: the runnable
  package (source, tests, examples, figure SVG/PNG) plus the rendered
  ``ScubaDrift-Documentation.docx``. The Markdown doc source is a build input,
  not shipped in the zip.
* ``ScubaDrift-Documentation.docx`` — the same document, offered standalone.

The ScubaGear-facing binaries are generated here at build time (on site deploy),
never committed to the source tree — see AGENTS.md. Run locally with any
``--out`` to preview; the Quarto deploy calls it with ``--out _site/download``.

Requires ``cairosvg`` + ``python-docx`` (already installed by the site
``assemble`` job). If they are missing the docx step is skipped with a warning
and the source-only zip is still produced.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PKG = REPO / "tools" / "scubadrift"
BUILD = PKG / "docbuild"
DOCX = PKG / "ScubaDrift-Documentation.docx"

# Paths (relative to PKG) excluded from the distributed zip. ``docbuild`` is the
# doc-authoring tooling (figure + docx build) — build input, not part of the
# runnable download set.
EXCLUDE_DIRS = {"__pycache__", ".pytest_cache", ".ruff_cache", "build", "docbuild", ".venv"}
EXCLUDE_SUFFIXES = {".pyc"}


def _version() -> str:
    text = (PKG / "src" / "scubadrift" / "__init__.py").read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*"([^"]+)"', text)
    return m.group(1) if m else "0.0.0"


def build_docx() -> bool:
    """Render ScubaDrift-Documentation.docx via the figure + assembly scripts."""
    try:
        import cairosvg  # noqa: F401
        import docx  # noqa: F401
    except ModuleNotFoundError as exc:
        print(f"::warning::skipping docx build — {exc.name} not installed", file=sys.stderr)
        return False
    subprocess.run([sys.executable, "build.py"], cwd=str(BUILD), check=True)
    if not DOCX.exists():
        print("::warning::docx build reported success but produced no file", file=sys.stderr)
        return False
    return True


def _zip_member(rel: Path) -> bool:
    parts = set(rel.parts)
    if parts & EXCLUDE_DIRS:
        return False
    if rel.suffix in EXCLUDE_SUFFIXES:
        return False
    # The Markdown doc source is a build input, not shipped in the zip.
    if rel.parts[:1] == ("docs",) and rel.suffix == ".md":
        return False
    return True


def build_zip(out_dir: Path, have_docx: bool) -> Path:
    version = _version()
    zip_path = out_dir / f"scubadrift-{version}.zip"
    with tempfile.TemporaryDirectory() as td:
        stage = Path(td) / "scubadrift"
        # copy the package, filtering excluded dirs/files
        for src in sorted(PKG.rglob("*")):
            rel = src.relative_to(PKG)
            if not _zip_member(rel):
                continue
            dst = stage / rel
            if src.is_dir():
                dst.mkdir(parents=True, exist_ok=True)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        if have_docx:
            shutil.copy2(DOCX, stage / DOCX.name)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(stage.rglob("*")):
                if f.is_file():
                    zf.write(f, f.relative_to(stage.parent))
    return zip_path


def main() -> int:
    ap = argparse.ArgumentParser(description="Build the ScubaDrift standalone download set.")
    ap.add_argument("--out", required=True, help="output directory (e.g. _site/download)")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    have_docx = build_docx()
    if have_docx:
        shutil.copy2(DOCX, out_dir / DOCX.name)

    zip_path = build_zip(out_dir, have_docx)
    # Stable alias so the Downloads landing links survive a version bump.
    latest = out_dir / "scubadrift-latest.zip"
    shutil.copy2(zip_path, latest)
    size_kb = zip_path.stat().st_size // 1024
    docx_note = "with docx" if have_docx else "source-only (no docx)"
    print(f"Built {zip_path.name} (+ {latest.name}) ({size_kb} KB, {docx_note}) in {out_dir}")
    if have_docx:
        print(f"Built {DOCX.name} in {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
