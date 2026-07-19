#!/usr/bin/env python3
"""Build the OrgComp (Federal Organization Compliance) series download kit — at deploy time, never committed.

Mirrors build_scubadrift_download.py: the kit binary is assembled on site deploy
into ``_site/download/`` and is not a committed artifact (AGENTS.md: no committed
binaries; the stale committed OrgComp_Federal_Series_Complete_*.zip was removed with
this script for exactly that reason — it also predated the de-brand and carried
agency identity and the FOUO banner).

WHY IT READS THE BOOK .docx FROM ``_site`` AND NOTHING ELSE FROM THERE.
The books contain ``{{< meta agency.* >}}`` shortcodes and an edition-conditional
FOUO banner. ONLY Quarto resolves the federal metadata and drops the banner (the
banner is ``content-hidden unless-profile="ssa"``). The local kit script uses raw
Pandoc, which resolves neither — so re-rendering here would ship raw shortcodes and
the internal banner. The federal book .docx already sitting in ``_site`` after the
Quarto render is therefore the ONLY correct source for the book documents.

The ``.pptx`` decks and the deployable operator-kit directories are static source
(no shortcodes), read from ``--src-root``.

Produces, into ``--out`` (the deploy calls it with ``--out _site/download``):
  * ``aan-federal-series-latest.zip`` — per-volume folders of book .docx + .pptx,
    plus the operator kits, plus a README stating the edition and build date.

Federal edition ONLY. This script never reads inbox/aan-ssa-edition/; the .docx it
collects are the federal renders and the .pptx/kits carry no agency facts, so the
download cannot leak the agency edition.

Local preview:
    python scripts/build_orgcomp_download.py --site-root _site --src-root . --out /tmp/dl
CI (site deploy):
    python scripts/build_orgcomp_download.py --site-root _site --src-root _src --out _site/download
"""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from pathlib import Path

# The series sits at different relative paths in the two trees: docs/ is the
# Quarto project root, so _site strips it, but the source checkout keeps it. A
# single rel path silently found the book .docx (site side) while missing every
# .pptx and in-series kit (source side) — caught in a local test.
SERIES_SITE_REL = "customer-documents/orgcomp-series"
SERIES_SRC_REL = "docs/customer-documents/orgcomp-series"
ZIP_NAME = "aan-federal-series-latest.zip"

# Map a Vol_<V>_Book_* filename to its distribution folder. Mirrors the volume
# names build_distribution_kit.sh uses so the two kits are organised alike.
VOL_FOLDER = {
    "0": "Vol_0_Executive_Summary",
    "I": "Vol_I_Foundation_and_Transport",
    "II": "Vol_II_Data_Platform",
    "III": "Vol_III_Security_Operations",
    "IV": "Vol_IV_Governance_and_Assurance",
    "V": "Vol_V_Training_and_Certification",
    "VI": "Vol_VI_Implementation",
    "VII": "Vol_VII_ServiceNow_Automation",
    "VIII": "Vol_VIII_Multi_Cloud_DDI",
    "IX": "Vol_IX_Day2_Operations",
}
_VOL_RE = re.compile(r"^Vol_([0-9IVX]+)_Book_")

# Operator kit source directories, relative to --src-root. These are static
# deployable source (Terraform, ServiceNow Script Includes, detection rules,
# courseware) — no agency facts, no shortcodes.
KIT_DIRS = [
    f"{SERIES_SRC_REL}/servicenow-day2",
    f"{SERIES_SRC_REL}/x_fed_compliance",
    f"{SERIES_SRC_REL}/impl/detection-rules",
    f"{SERIES_SRC_REL}/OrgComp-Training-Program",
    "infoblox-ddi-book/servicenow-app",
    "infoblox-ddi-book/azure-alz-automation",
    "infoblox-ddi-book/aws-lz-automation",
    "infoblox-ddi-book/gcp-lz-automation",
    "infoblox-ddi-book/oci-lz-automation",
    "infoblox-ddi-book/vmware-lz-automation",
]


def _vol_folder(stem: str) -> str | None:
    m = _VOL_RE.match(stem)
    return VOL_FOLDER.get(m.group(1)) if m else None


def collect(site_root: Path, src_root: Path) -> tuple[dict[str, Path], list[str]]:
    """Return {archive_path: source_file} and a list of notes about what was found.

    Deterministic and gap-reporting: if a class of input is missing, it says so
    rather than shipping a silently incomplete kit that looks complete.
    """
    members: dict[str, Path] = {}
    notes: list[str] = []
    series_site = site_root / SERIES_SITE_REL
    series_src = src_root / SERIES_SRC_REL

    # 1. Federal book .docx from _site (the only correct edition source).
    n_docx = 0
    for docx in sorted(series_site.rglob("Vol_*_Book_*.docx")):
        if docx.name.endswith("-bundle.docx"):
            continue
        folder = _vol_folder(docx.stem)
        if folder:
            members[f"{folder}/{docx.name}"] = docx
            n_docx += 1
    notes.append(f"book .docx (federal, from _site): {n_docx}")
    if n_docx == 0:
        notes.append("  WARNING: no book .docx in _site — did the Quarto render run first?")

    # 2. Committed .pptx decks from source.
    n_pptx = 0
    for pptx in sorted(series_src.glob("Vol_*_Book_*.pptx")):
        folder = _vol_folder(pptx.stem)
        if folder:
            members[f"{folder}/{pptx.name}"] = pptx
            n_pptx += 1
    notes.append(f".pptx decks (from source): {n_pptx}")

    # 3. Operator kit directories from source.
    n_kits = 0
    for rel in KIT_DIRS:
        d = src_root / rel
        if not d.is_dir():
            notes.append(f"  kit dir missing (skipped): {rel}")
            continue
        n_kits += 1
        for f in sorted(d.rglob("*")):
            if f.is_file():
                members[f"kits/{Path(rel).name}/{f.relative_to(d).as_posix()}"] = f
    notes.append(f"operator kit dirs: {n_kits}/{len(KIT_DIRS)}")

    return members, notes


def _index_md(members: dict[str, Path], date_code: str) -> str:
    """Render the kit's master index — the zip-root INDEX.md.

    Groups the archive members by volume folder (each book listed once per
    stem, with the formats present) and by operator kit (file counts), so a
    reader can navigate the kit from the root instead of spelunking folders.
    """
    vols: dict[str, dict[str, set[str]]] = {}
    kits: dict[str, int] = {}
    for arc in members:
        top, _, rest = arc.partition("/")
        if top == "kits":
            kits[rest.partition("/")[0]] = kits.get(rest.partition("/")[0], 0) + 1
        elif _VOL_RE.match(Path(rest).stem):
            vols.setdefault(top, {}).setdefault(Path(rest).stem, set()).add(Path(rest).suffix)
    lines = [
        "# Federal Organization Compliance (OrgComp) Series — kit index",
        "",
        f"Build date: {date_code}. Edition and scope notes: README.txt.",
        "",
        "## Volumes",
        "",
    ]
    for folder in VOL_FOLDER.values():
        books = vols.get(folder)
        if not books:
            continue
        lines += [f"### {folder.replace('_', ' ')}", ""]
        for stem in sorted(books):
            fmts = " + ".join(sorted(s.lstrip(".") for s in books[stem]))
            lines.append(f"- `{folder}/{stem}` ({fmts})")
        lines.append("")
    lines += ["## Operator kits (`kits/`)", ""]
    for kit in sorted(kits):
        lines.append(f"- `kits/{kit}/` — {kits[kit]} file(s)")
    lines.append("")
    return "\n".join(lines)


def build(site_root: Path, src_root: Path, out_dir: Path, date_code: str) -> int:
    members, notes = collect(site_root, src_root)
    print("Federal Organization Compliance (OrgComp) Series kit — build inputs")
    print("=" * 60)
    for n in notes:
        print(" ", n)

    if not any(k.endswith(".docx") for k in members):
        print("\nFATAL: no book documents collected — refusing to ship an empty kit.")
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / ZIP_NAME
    readme = (
        "Federal Organization Compliance (OrgComp) Series — complete kit\n"
        f"Build date: {date_code}\n\n"
        "FEDERAL EDITION. Written for any federal agency; no agency is named. The\n"
        "agency-specific edition is not distributed here.\n\n"
        "Contents: every book as Word (.docx, per-volume folders) and PowerPoint\n"
        "(.pptx), plus the deployable operator kits (ServiceNow day-2 catalog, the\n"
        "compliance scoped app, detection rules, the multi-cloud DDI landing-zone\n"
        "automation, and the training academy).\n\n"
        "A master index of every volume, book, and kit is in INDEX.md.\n\n"
        "Rebuilt from source on every site deploy — no fixed SHA-256 is published.\n"
    )
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("README.txt", readme)
        z.writestr("INDEX.md", _index_md(members, date_code))
        for arc, src in sorted(members.items()):
            z.write(src, arc)

    size_mb = zip_path.stat().st_size / 1_048_576
    print(f"\nWrote {zip_path}  ({len(members)} files, {size_mb:.1f} MB)")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--site-root", type=Path, required=True, help="rendered _site root")
    ap.add_argument("--src-root", type=Path, required=True, help="repo source root")
    ap.add_argument("--out", type=Path, required=True, help="output dir for the zip")
    # Date passed in (never derived here): the caller stamps a deterministic value.
    ap.add_argument("--date-code", default="unknown", help="build date label for the README")
    args = ap.parse_args(argv)
    return build(args.site_root, args.src_root, args.out, args.date_code)


if __name__ == "__main__":
    sys.exit(main())
