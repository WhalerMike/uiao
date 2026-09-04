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
  * ``orgcomp-federal-series-latest.zip`` — per-volume folders holding ONE Word
    file per volume (the ``Vol_<N>-<Theme>-Bundle.docx`` the bundler's volume
    pass concatenated from the volume's books) plus the per-book .pptx decks,
    plus the operator kits, plus a README stating the edition and build date.
    Individual per-book .docx are not shipped — the site offers those per page.

ONE SECTION COMES FROM OUTSIDE THE SERIES TREE.
``siem-telemetry-emission`` lives under ``customer-documents/operational-guides``
— OrgMod's operational home — but it is OrgComp's content: it is the *emission*
side of the evidence pipeline whose *consumption* side is Vol III Book 06, and
``operational-guides/index.qmd`` says so outright. It ships here in
``Evidence_Emission/``, and build_org_family_download.py excludes it from the
OrgMod kit's Guides sweep so it is not shipped twice.

Unlike the books it carries no ``{{< meta agency.* >}}`` shortcodes, so it is
not edition-sensitive and renders identically either way. It is still read from
``_site`` rather than re-rendered here, for the same reason everything else is:
the Quarto render is the only .docx source this script trusts.

Federal edition ONLY. This script never reads inbox/aan-ssa-edition/, and the .docx
it collects are the federal renders (Quarto resolved the agency metadata).

That is NOT sufficient on its own, and this script used to claim it was. KIT_DIRS
sweeps operator-kit directories with rglob("*"), which picks up whatever is on
disk — including committed .docx that never went through a Quarto render. Two of
them were the agency edition and shipped in every build until the leak gate below
was added. Nothing about the collection paths guarantees a de-branded kit; only
check_kit_agency_leak.scan_members, run over the ASSEMBLED member list before the
zip is written, does. Do not remove that call.

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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_kit_agency_leak import format_findings, scan_members  # noqa: E402

# The series sits at different relative paths in the two trees: docs/ is the
# Quarto project root, so _site strips it, but the source checkout keeps it. A
# single rel path silently found the book .docx (site side) while missing every
# .pptx and in-series kit (source side) — caught in a local test.
SERIES_SITE_REL = "customer-documents/orgcomp-series"
SERIES_SRC_REL = "docs/customer-documents/orgcomp-series"
ZIP_NAME = "orgcomp-federal-series-latest.zip"

# The one OrgComp section that lives outside the series tree — see the
# docstring. build_org_family_download.py names the same directory in
# ORGCOMP_EVIDENCE_EMISSION_DIR to keep it out of the OrgMod kit; a test
# asserts the two agree.
EVIDENCE_EMISSION_SITE_REL = "customer-documents/operational-guides/siem-telemetry-emission"
EVIDENCE_EMISSION_FOLDER = "Evidence_Emission"
EVIDENCE_EMISSION_MIN = 5

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
    "X": "Vol_X_Governance_Substrate_Integration",
}
_VOL_RE = re.compile(r"^Vol_([0-9IVX]+)_Book_")

# Per-volume Word bundle produced by bundle_section_docx.py's volume pass —
# themed form "Vol_I-Foundation & Transport-Bundle.docx", themeless fallback
# "Vol_<N>-bundle.docx". Both live at the series root in _site.
_VOL_BUNDLE_RE = re.compile(r"^Vol_([0-9IVX]+)-.*[Bb]undle\.docx$")

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

    # 1. Per-volume Word bundles from _site (the only correct edition source).
    # One Word file per volume — bundle_section_docx.py's volume pass already
    # concatenated the volume's books, so the kit ships eleven volume files
    # instead of ~90 per-book .docx. The site still offers per-book downloads
    # on each page.
    n_docx = 0
    for docx in sorted(series_site.glob("Vol_*.docx")):
        m = _VOL_BUNDLE_RE.match(docx.name)
        if not m:
            continue
        folder = VOL_FOLDER.get(m.group(1))
        if folder:
            members[f"{folder}/{docx.name}"] = docx
            n_docx += 1
    notes.append(f"per-volume bundle .docx (federal, from _site): {n_docx}")
    if n_docx != len(VOL_FOLDER):
        notes.append(
            f"  WARNING: expected {len(VOL_FOLDER)} volume bundles, found {n_docx} — "
            "did the bundler's volume pass run before this build?"
        )

    # 1b. Non-book series .docx from _site — the operator runbook and the day-2
    # kit reference/usage docs. These are registered .qmd that render to .docx
    # but are not Vol_*_Book_* files, so the book collector above skips them.
    # They ship in a "Runbooks_and_Kit_Docs" folder alongside the volumes.
    n_extra = 0
    for stem in (
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
    ):
        docx = series_site / f"{stem}.docx"
        if docx.is_file():
            members[f"Runbooks_and_Kit_Docs/{docx.name}"] = docx
            n_extra += 1
    notes.append(f"runbook + kit .docx (from _site): {n_extra}")

    # 1c. The evidence-emission section from _site. It sits under
    # operational-guides rather than the series tree, so neither collector
    # above reaches it; see the docstring for why it is OrgComp's.
    emission_site = site_root / EVIDENCE_EMISSION_SITE_REL
    n_emit = 0
    if emission_site.is_dir():
        for docx in sorted(emission_site.rglob("*.docx")):
            if docx.name.lower().endswith("-bundle.docx"):
                continue  # never ship a page and a concatenation of it
            members[f"{EVIDENCE_EMISSION_FOLDER}/{docx.name}"] = docx
            n_emit += 1
    else:
        notes.append(f"  MISSING: {EVIDENCE_EMISSION_SITE_REL} not found — Evidence_Emission is empty")
    notes.append(f"evidence-emission .docx (from _site): {n_emit}")
    if n_emit < EVIDENCE_EMISSION_MIN:
        notes.append(
            f"  WARNING: expected at least {EVIDENCE_EMISSION_MIN} evidence-emission pages, "
            f"found {n_emit} — did the DOCX render sweep that section?"
        )

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
        elif top in VOL_FOLDER.values():
            # Volume folders hold the volume's Word bundle plus the per-book
            # .pptx decks; group by stem so each lists once with its formats.
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
        print("\nFATAL: no Word documents collected — refusing to ship an empty kit.")
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / ZIP_NAME
    readme = (
        "Federal Organization Compliance (OrgComp) Series — complete kit\n"
        f"Build date: {date_code}\n\n"
        "FEDERAL EDITION. Written for any federal agency; no agency is named. The\n"
        "agency-specific edition is not distributed here.\n\n"
        "Contents: one Word file per volume (.docx volume bundles, per-volume\n"
        "folders) and the per-book PowerPoint (.pptx) briefings that exist so\n"
        "far — Volumes VII and IX; the other volumes have no decks yet — plus\n"
        "the deployable\n"
        "operator kits (ServiceNow day-2 catalog, the compliance scoped app,\n"
        "detection rules, the multi-cloud DDI landing-zone automation, and the\n"
        "training academy).\n\n"
        "A master index of every volume, book, and kit is in INDEX.md.\n\n"
        "Rebuilt from source on every site deploy — no fixed SHA-256 is published.\n"
    )
    index_md = _index_md(members, date_code)

    # The README above promises "no agency is named". Prove it before writing,
    # over the assembled member list — the .docx from _site, the .pptx, and
    # everything KIT_DIRS swept — plus the two members generated in memory.
    # INDEX.md matters here specifically because it reproduces every archive
    # path, which is how a leaking FILENAME reaches a reader.
    findings = scan_members(members, extra={"README.txt": readme, "INDEX.md": index_md})
    if findings:
        print(format_findings(findings))
        return 1

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("README.txt", readme)
        z.writestr("INDEX.md", index_md)
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
