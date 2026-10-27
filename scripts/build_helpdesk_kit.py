#!/usr/bin/env python3
"""Build the Help Desk / Cloud Services Entra ID Operations Kit zip.

The kit's sources all live in the repo (ADR-105 D1):

  docs/customer-documents/operational-guides/helpdesk-entra-operations/
    *.qmd            -> documents/*.docx  (rendered by Quarto, then AutoFit-patched)
    kit/*.md         -> README.md, implementation-path.md, CHANGELOG.md
    scripts/*.ps1    -> scripts/*.ps1 (+ .txt copy)
    scripts/*.psm1   -> lib/*.psm1    (+ .txt copy)
    scripts/tests/   -> tests/

The ``.txt`` copies exist because many mail systems strip ``.ps1`` attachments.

AutoFit patch: pandoc writes data tables with ``<w:tblLayout w:type="fixed"/>``
and equal column widths, so Word shows long first columns cramped next to
near-empty ones. The patch switches every table to autofit at 100% page width so
Word sizes columns to their content.

Usage:
    python scripts/build_helpdesk_kit.py --out build/helpdesk-entra-kit          # render + zip
    python scripts/build_helpdesk_kit.py --out build/helpdesk-entra-kit --no-render  # reuse _site docx
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
KIT_DIR = REPO / "docs/customer-documents/operational-guides/helpdesk-entra-operations"
SITE_DIR = REPO / "docs/_site/customer-documents/operational-guides/helpdesk-entra-operations"
ZIP_NAME = "helpdesk-entra-operations-kit.zip"

# qmd stem -> published .docx name (names kept from v1.5 so links stay stable)
DOCUMENTS = {
    "helpdesk-flow": "Helpdesk-Flow.docx",
    "help-desk-administrative-responsibilities": "Help-Desk-Administrative-Responsibilities-Guide.docx",
    "enterprise-application-access-governance": "Enterprise-Application-Access-Governance-and-Approval-Model.docx",
    "orgpath-identity-governance-structure": "Governance-Structure-Brief.docx",
}


def render_docx(stem: str) -> Path:
    qmd = KIT_DIR / f"{stem}.qmd"
    rel = qmd.relative_to(REPO / "docs").as_posix()
    print(f"render {rel} -> docx", flush=True)
    subprocess.run(["quarto", "render", rel, "--to", "docx"], cwd=REPO / "docs", check=True)
    out = SITE_DIR / f"{stem}.docx"
    if not out.exists():
        raise SystemExit(f"quarto did not produce {out}")
    return out


def autofit_patch(docx: Path) -> int:
    """Rewrite word/document.xml in place; return the number of tables touched."""
    with zipfile.ZipFile(docx) as zin:
        items = [(i, zin.read(i.filename)) for i in zin.infolist()]
    touched = 0
    out_items = []
    for info, data in items:
        if info.filename == "word/document.xml":
            xml = data.decode("utf-8")
            touched = len(re.findall(r'<w:tblLayout w:type="fixed"\s*/>', xml))
            xml = re.sub(r'<w:tblLayout w:type="fixed"\s*/>', '<w:tblLayout w:type="autofit" />', xml)
            xml = re.sub(r'<w:tblW w:type="auto" w:w="0"\s*/>', '<w:tblW w:type="pct" w:w="5000" />', xml)
            data = xml.encode("utf-8")
        out_items.append((info, data))
    tmp = docx.with_suffix(".tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for info, data in out_items:
            zout.writestr(info, data)
    tmp.replace(docx)
    return touched


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True, help="output directory (staging + zip)")
    ap.add_argument("--no-render", action="store_true", help="reuse .docx already in docs/_site")
    args = ap.parse_args()

    out = args.out.resolve()
    stage = out / "helpdesk-entra-operations-kit"
    if stage.exists():
        shutil.rmtree(stage)
    (stage / "documents").mkdir(parents=True)
    (stage / "scripts").mkdir()
    (stage / "lib").mkdir()
    (stage / "tests").mkdir()

    if not args.no_render:
        subprocess.run(
            [sys.executable, str(REPO / "scripts/render_svg_images.py"), str(KIT_DIR / "images")], check=True
        )

    for stem, name in DOCUMENTS.items():
        src = SITE_DIR / f"{stem}.docx" if args.no_render else render_docx(stem)
        if not src.exists():
            raise SystemExit(f"missing render: {src} (run without --no-render)")
        dst = stage / "documents" / name
        shutil.copy2(src, dst)
        print(f"  {name}: AutoFit patched {autofit_patch(dst)} table(s)")

    for md in ("README.md", "implementation-path.md", "CHANGELOG.md"):
        shutil.copy2(KIT_DIR / "kit" / md, stage / md)

    for src in sorted((KIT_DIR / "scripts").iterdir()):
        if src.suffix == ".ps1":
            dest_dir = stage / "scripts"
        elif src.suffix == ".psm1":
            dest_dir = stage / "lib"
        else:
            continue
        shutil.copy2(src, dest_dir / src.name)
        shutil.copy2(src, dest_dir / f"{src.name}.txt")
    for src in sorted((KIT_DIR / "scripts/tests").glob("*.ps1")):
        shutil.copy2(src, stage / "tests" / src.name)

    zpath = out / ZIP_NAME
    if zpath.exists():
        zpath.unlink()
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(stage.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(stage).as_posix())

    print(f"\n{zpath}")
    for f in [zpath, *sorted((stage / "documents").glob("*.docx"))]:
        print(f"  sha256 {hashlib.sha256(f.read_bytes()).hexdigest()}  {f.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
