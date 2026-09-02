#!/usr/bin/env python3
"""Build the OrgComp (Federal Organization Compliance) series markdown-only
download kit — at deploy time, never committed.

The same book set as ``build_orgcomp_download.py``, packaged as plain
Markdown instead of Word/PowerPoint, for pasting into an AI tool or
uploading to an AI "project" — LLM context windows and AI knowledge uploads
take Markdown far more cleanly than .docx.

WHY IT READS THE .md FROM ``_site`` AND NOTHING ELSE.
The book ``.qmd`` source carries ``{{< meta agency.* >}}`` shortcodes and an
edition-conditional FOUO banner (``content-hidden unless-profile="ssa"``).
Only Quarto's own render resolves both — the ``render_md_orgcomp`` CI job
renders every ``customer-documents/orgcomp-series/*.qmd`` to GitHub-Flavored
Markdown (``--to gfm``) alongside the existing DOCX render, and the assemble
job merges that output into ``_site`` next to the ``.docx``. This script
reads THAT rendered markdown, never the raw .qmd, so the kit is
edition-correct exactly like the Word kit (see build_orgcomp_download.py).

Scope: readable book/doc content only — no .pptx, no operator-kit source
(Script Includes, Terraform, detection rules). Those stay Word/PowerPoint/
source-only; this kit is the text.

Federal edition ONLY — same posture as build_orgcomp_download.py. This
script never reads inbox/aan-ssa-edition/.

Produces, into ``--out`` (the deploy calls it with ``--out _site/download``):
  * ``orgcomp-federal-series-markdown-latest.zip`` — per-volume folders
    holding one ``.md`` per book plus a concatenated ``Vol_<N>-Bundle.md``,
    plus the runbook/kit-docs markdown, plus a README stating the edition
    and build date.

Local preview:
    python scripts/build_orgcomp_markdown_download.py --site-root _site --src-root . --out /tmp/dl
CI (site deploy):
    python scripts/build_orgcomp_markdown_download.py --site-root _site --src-root _src --out _site/download
"""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_kit_agency_leak import format_findings, scan_members  # noqa: E402

SERIES_SITE_REL = "customer-documents/orgcomp-series"
ZIP_NAME = "orgcomp-federal-series-markdown-latest.zip"

# Same volume/theme mapping as build_orgcomp_download.py and
# bundle_section_docx.py's VOLUME_THEMES — kept local (small, stable table)
# rather than importing across scripts that are each invoked standalone from
# a sparse checkout in CI.
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
    "X": "Vol_X_Governance_Substrate_Integration",
}
VOLUME_THEMES = {
    "0": "Executive Summary, Questionnaire & Control Crosswalk",
    "I": "Foundation & Transport",
    "II": "Data Platform",
    "III": "Security Operations",
    "IV": "Governance & Assurance",
    "V": "Training & Certification",
    "VI": "Implementation",
    "VII": "ServiceNow Automation",
    "VIII": "Multi-Cloud DDI",
    "IX": "Day-2 Operations",
    "X": "Governance-Substrate Integration",
}
_ROMAN_RANK = {"0": 0, "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10}
_VOL_RE = re.compile(r"^Vol_([0-9IVX]+)_Book_")

# Non-book series markdown (runbook + kit reference/usage docs) — same stem
# list as build_orgcomp_download.py's Runbooks_and_Kit_Docs group. These are
# wrapper .qmd (``{{< include servicenow-day2/... >}}``) rendered to .md by
# render_md_orgcomp, so they land in _site under these same stems.
EXTRA_STEMS = (
    "OrgComp_Day2_Kit_0_Start_Here",
    "OrgComp_Operator_Runbook_Day2_Compliant",
    "OrgComp_Day2_Kit_1_Variables_Reference",
    "OrgComp_Day2_Kit_2_Scripts_Manifest",
    "OrgComp_Day2_Kit_3_Implementation_Guide",
    "OrgComp_Day2_Kit_4_Usage_Operator",
    "OrgComp_Day2_Kit_5_Usage_SAM_Integration",
    "OrgComp_Day2_Kit_6_Build_Specification",
    "OrgComp_Day2_Kit_Current_0_Start_Here",
    "OrgComp_Day2_Kit_Current_1_Operator_Usage",
    "OrgComp_Day2_Kit_Current_2_Scripts",
    "OrgComp_Day2_Kit_Current_3_Build_Delta",
    "OrgComp_Day2_Kit_Overview_README",
    "OrgComp_Day2_Kit_Flow_Blueprint",
    "OrgComp_Day2_Kit_Catalog_README",
    "OrgComp_Day2_Kit_ATF_README",
    "OrgComp_Day2_Kit_UpdateSet_README",
    "OrgComp_ServiceNow_Kit_Expansion_Roadmap_page",
)


def _volume_bundle_filename(vol_id: str) -> str:
    theme = VOLUME_THEMES.get(vol_id)
    if theme is None:
        return f"Vol_{vol_id}-Bundle.md"
    return f"Vol_{vol_id}-{theme}-Bundle.md"


def collect_books(series_site: Path) -> dict[str, list[Path]]:
    """Group top-level ``Vol_<N>_Book_*.md`` pages by volume id, filename-sorted.

    Filenames are zero-padded (``Book_00a``, ``Book_01``, ...) so a plain
    lexicographic sort already yields reading order within a volume.
    """
    volumes: dict[str, list[Path]] = {}
    for md in sorted(series_site.glob("Vol_*.md")):
        m = _VOL_RE.match(md.stem)
        if not m or m.group(1) not in VOL_FOLDER:
            continue
        volumes.setdefault(m.group(1), []).append(md)
    return volumes


def _volume_bundle_text(vol_id: str, books: list[Path]) -> str:
    vol_label = "Volume 0" if vol_id == "0" else f"Volume {vol_id}"
    theme = VOLUME_THEMES.get(vol_id)
    title = f"# Federal Organization Compliance — {vol_label}"
    if theme:
        title += f" — {theme}"
    parts = [title, ""]
    for book in books:
        parts.append(book.read_text(encoding="utf-8").rstrip())
        parts.append("\n---\n")
    return "\n".join(parts).rstrip() + "\n"


def collect(site_root: Path) -> tuple[dict[str, Path], dict[str, str], list[str]]:
    """Return (file members, generated members, notes).

    ``file members`` map an archive path to a source .md file to copy in
    verbatim (per-book pages, runbook/kit docs). ``generated members`` map
    an archive path to in-memory text (the per-volume concatenated bundles).
    """
    files: dict[str, Path] = {}
    generated: dict[str, str] = {}
    notes: list[str] = []
    series_site = site_root / SERIES_SITE_REL

    volumes = collect_books(series_site)
    n_books = 0
    for vol_id, books in volumes.items():
        folder = VOL_FOLDER[vol_id]
        for book in books:
            files[f"{folder}/{book.name}"] = book
            n_books += 1
        generated[f"{folder}/{_volume_bundle_filename(vol_id)}"] = _volume_bundle_text(vol_id, books)
    notes.append(f"book .md pages (federal, from _site): {n_books} across {len(volumes)} volume(s)")
    if len(volumes) != len(VOL_FOLDER):
        notes.append(
            f"  WARNING: expected {len(VOL_FOLDER)} volumes, found {len(volumes)} — "
            "did render_md_orgcomp run before this build?"
        )

    n_extra = 0
    for stem in EXTRA_STEMS:
        md = series_site / f"{stem}.md"
        if md.is_file():
            files[f"Runbooks_and_Kit_Docs/{md.name}"] = md
            n_extra += 1
    notes.append(f"runbook + kit .md (from _site): {n_extra}/{len(EXTRA_STEMS)}")

    return files, generated, notes


def _index_md(files: dict[str, Path], generated: dict[str, str], date_code: str) -> str:
    vols: dict[str, set[str]] = {}
    for arc in list(files) + list(generated):
        top, _, rest = arc.partition("/")
        if top in VOL_FOLDER.values():
            vols.setdefault(top, set()).add(rest)
    lines = [
        "# Federal Organization Compliance (OrgComp) Series — markdown kit index",
        "",
        f"Build date: {date_code}. Plain Markdown, for AI import — see README.txt.",
        "",
        "## Volumes",
        "",
    ]
    for folder in VOL_FOLDER.values():
        names = vols.get(folder)
        if not names:
            continue
        lines += [f"### {folder.replace('_', ' ')}", ""]
        for name in sorted(names):
            lines.append(f"- `{folder}/{name}`")
        lines.append("")
    lines += ["## Runbook & kit docs (`Runbooks_and_Kit_Docs/`)", ""]
    for arc in sorted(files):
        if arc.startswith("Runbooks_and_Kit_Docs/"):
            lines.append(f"- `{arc}`")
    lines.append("")
    return "\n".join(lines)


def build(site_root: Path, out_dir: Path, date_code: str) -> int:
    files, generated, notes = collect(site_root)
    print("Federal Organization Compliance (OrgComp) Series markdown kit — build inputs")
    print("=" * 60)
    for n in notes:
        print(" ", n)

    if not files and not generated:
        print("\nFATAL: no Markdown collected — refusing to ship an empty kit.")
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / ZIP_NAME
    readme = (
        "Federal Organization Compliance (OrgComp) Series — markdown kit\n"
        f"Build date: {date_code}\n\n"
        "FEDERAL EDITION. Written for any federal agency; no agency is named. The\n"
        "agency-specific edition is not distributed here.\n\n"
        "Plain Markdown (.md) — no Word, no PowerPoint, no operator-kit source. Meant\n"
        "for pasting into an AI tool or uploading to an AI 'project': one .md per book,\n"
        "plus a concatenated Vol_<N>-Bundle.md per volume, plus the runbook and kit\n"
        "reference/usage docs.\n\n"
        "For the Word/PowerPoint kit (with the deployable operator kits), see\n"
        "orgcomp-federal-series-latest.zip.\n\n"
        "A master index of every volume and doc is in INDEX.md.\n\n"
        "Rebuilt from source on every site deploy — no fixed SHA-256 is published.\n"
    )
    index_md = _index_md(files, generated, date_code)

    # Same gate as build_orgcomp_download.py — see check_kit_agency_leak. The
    # concatenated volume bundles live in ``generated`` and never touch disk,
    # so they go through ``extra`` or they would ship unscanned.
    findings = scan_members(files, extra={**generated, "README.txt": readme, "INDEX.md": index_md})
    if findings:
        print(format_findings(findings))
        return 1

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("README.txt", readme)
        z.writestr("INDEX.md", index_md)
        for arc, src in sorted(files.items()):
            z.write(src, arc)
        for arc, text in sorted(generated.items()):
            z.writestr(arc, text)

    size_mb = zip_path.stat().st_size / 1_048_576
    print(f"\nWrote {zip_path}  ({len(files) + len(generated)} files, {size_mb:.1f} MB)")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--site-root", type=Path, required=True, help="rendered _site root")
    ap.add_argument(
        "--src-root",
        type=Path,
        required=False,
        help="repo source root (unused — kept for CLI symmetry with build_orgcomp_download.py)",
    )
    ap.add_argument("--out", type=Path, required=True, help="output dir for the zip")
    ap.add_argument("--date-code", default="unknown", help="build date label for the README")
    args = ap.parse_args(argv)
    return build(args.site_root, args.out, args.date_code)


if __name__ == "__main__":
    sys.exit(main())
