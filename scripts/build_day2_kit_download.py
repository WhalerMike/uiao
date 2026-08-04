#!/usr/bin/env python3
"""Build the standalone OrgComp Day-2 Automation Kit downloads — TWO edition zips.

The kit ships in two editions (same scripts, switched by x_fed_day2_ops.hybrid_mode):

  * ``orgcomp-day2-kit-active-directory-latest.zip`` — CURRENT STATE (run today): a
    hybrid, AD-mastered estate (Entra Connect syncs AD->Entra). Includes the AD
    write leg (AdHybridClient) and the CURRENT-STATE-* docs + current-state figures.
  * ``orgcomp-day2-kit-hrit-latest.zip`` — 2027 TARGET STATE: OPM-HRIT as SSOT,
    cloud-native provisioning into Entra. The base KIT-* docs + the overview and
    target-state per-task figures.

Each zip is a complete, deployable kit for its edition: the shared ServiceNow
source (Script Includes, scripted REST, control maps, ATF, catalog/flow/update-set
specs, gates) PLUS that edition's docs in BOTH forms (each *.md with its rendered
.docx sibling, and a numbered docx/ set in reading order). The other edition's
docs and figures are filtered out so neither zip mixes the two.

Reads the rendered .docx from ``_site`` (the only correct, house-styled source)
and the kit source from the repo. Federal edition only. Gap-reporting: if a
.docx render is missing it says so rather than shipping a source-only kit.

Usage (called from the Quarto assemble job, after the site renders):
    python scripts/build_day2_kit_download.py \
        --site-root _site --src-root . --out _site/download --date-code YYYY-MM-DD
"""

from __future__ import annotations

import argparse
import hashlib
import zipfile
from pathlib import Path

SERIES = "customer-documents/orgcomp-series"
KIT_SRC_REL = f"docs/{SERIES}/servicenow-day2"
SITE_SERIES_REL = f"{SERIES}"

# --- Rendered .docx (in _site) -> name to place BESIDE the matching .md. --------
# Shared docs describe the edition-neutral platform; both editions ship them.
SHARED_MD_DOCX = {
    "KIT-VARIABLES-REFERENCE": "OrgComp_Day2_Kit_1_Variables_Reference",
    "KIT-SCRIPTS": "OrgComp_Day2_Kit_2_Scripts_Manifest",
    "KIT-IMPLEMENTATION-GUIDE": "OrgComp_Day2_Kit_3_Implementation_Guide",
    "KIT-USAGE-SAM-INTEGRATION": "OrgComp_Day2_Kit_5_Usage_SAM_Integration",
    "KIT-BUILD-SPEC": "OrgComp_Day2_Kit_6_Build_Specification",
    "README": "OrgComp_Day2_Kit_Overview_README",
    "flow/flow-blueprint": "OrgComp_Day2_Kit_Flow_Blueprint",
    "catalog/README": "OrgComp_Day2_Kit_Catalog_README",
    "atf/README": "OrgComp_Day2_Kit_ATF_README",
    "update-set/README": "OrgComp_Day2_Kit_UpdateSet_README",
}
TARGET_MD_DOCX = {
    "START-HERE": "OrgComp_Day2_Kit_0_Start_Here",
    "KIT-USAGE-OPERATOR": "OrgComp_Day2_Kit_4_Usage_Operator",
}
CURRENT_MD_DOCX = {
    "CURRENT-STATE-START-HERE": "OrgComp_Day2_Kit_Current_0_Start_Here",
    "CURRENT-STATE-OPERATOR-USAGE": "OrgComp_Day2_Kit_Current_1_Operator_Usage",
    "CURRENT-STATE-SCRIPTS": "OrgComp_Day2_Kit_Current_2_Scripts",
    "CURRENT-STATE-BUILD-DELTA": "OrgComp_Day2_Kit_Current_3_Build_Delta",
    "CURRENT-STATE-PILOT-ROLLOUT": "OrgComp_Day2_Kit_Current_4_Pilot_Rollout",
}

# --- Numbered docx/ reading-order sets, per edition. ----------------------------
TARGET_DOCX_SET = {
    "OrgComp_Day2_Kit_0_Start_Here": "0_START_HERE.docx",
    "OrgComp_Operator_Runbook_Day2_Compliant": "1_Operator_Runbook.docx",
    "OrgComp_Day2_Kit_1_Variables_Reference": "2_Variables_Reference.docx",
    "OrgComp_Day2_Kit_2_Scripts_Manifest": "3_Scripts_Manifest.docx",
    "OrgComp_Day2_Kit_3_Implementation_Guide": "4_Implementation_Guide.docx",
    "OrgComp_Day2_Kit_4_Usage_Operator": "5_Usage_Operator.docx",
    "OrgComp_Day2_Kit_5_Usage_SAM_Integration": "6_Usage_SAM_Integration.docx",
    "OrgComp_Day2_Kit_6_Build_Specification": "7_Build_Specification.docx",
    "OrgComp_ServiceNow_Kit_Expansion_Roadmap_page": "8_Kit_Expansion_Roadmap.docx",
}
CURRENT_DOCX_SET = {
    "OrgComp_Day2_Kit_Current_0_Start_Here": "0_START_HERE.docx",
    "OrgComp_Day2_Kit_1_Variables_Reference": "1_Variables_Reference.docx",
    "OrgComp_Day2_Kit_Current_3_Build_Delta": "2_Build_Delta.docx",
    "OrgComp_Day2_Kit_Current_2_Scripts": "3_Scripts.docx",
    "OrgComp_Day2_Kit_3_Implementation_Guide": "4_Implementation_Guide.docx",
    "OrgComp_Day2_Kit_Current_1_Operator_Usage": "5_Operator_Usage.docx",
    "OrgComp_Day2_Kit_5_Usage_SAM_Integration": "6_Usage_SAM_Integration.docx",
    "OrgComp_Day2_Kit_6_Build_Specification": "7_Build_Specification.docx",
    "OrgComp_Operator_Runbook_Day2_Compliant": "8_Operator_Runbook.docx",
    "OrgComp_Day2_Kit_Current_4_Pilot_Rollout": "9_Pilot_Rollout.docx",
}


def _is_current_only(rel: str) -> bool:
    """A source file (path relative to servicenow-day2/) belonging only to the
    Current State edition."""
    return (
        rel == "script-includes/AdHybridClient.js"
        or rel.startswith("CURRENT-STATE-")
        or rel.startswith("figs/day2kit-current-fig-")
        or rel.startswith("figs/day2kit-task-")
        # Hybrid ATF suites exercise AdHybridClient (the AD leg) — meaningless in
        # the HRIT edition, which has no AD leg. They ship with Current State only.
        or rel.startswith("atf/atf-hybrid-")
        or rel == "atf/atf-negative-route-unclassified.xml"
    )


def _is_target_only(rel: str) -> bool:
    """A source file belonging only to the 2027 Target State edition."""
    return (
        rel == "START-HERE.md"
        or rel.startswith("KIT-USAGE-OPERATOR")
        or rel.startswith("figs/day2kit-fig-")
        or rel.startswith("figs/day2kit-target-task-")
    )


ROOTS = {
    "current": "OrgComp-Day2-Kit-Active-Directory",
    "target": "OrgComp-Day2-Kit-HRIT",
}
ZIP_NAMES = {
    "current": "orgcomp-day2-kit-active-directory-latest.zip",
    "target": "orgcomp-day2-kit-hrit-latest.zip",
}

# --- Markdown-only doc kits (docs only, no source, no Word) — for AI import. ----
# Reuses the same numbered reading-order dicts as the Word docx/ set above, but
# resolves each stem's ``.md`` sibling in _site (rendered by render_md_orgcomp)
# instead of its ``.docx``. No servicenow-day2/ kit source, no MANIFEST — just
# the doc set, meant to be pasted into an AI tool or uploaded to an AI project.
ZIP_NAMES_MD = {
    "current": "orgcomp-day2-kit-active-directory-docs-markdown-latest.zip",
    "target": "orgcomp-day2-kit-hrit-docs-markdown-latest.zip",
}
README_MD = {
    "current": (
        "OrgComp Day-2 Automation Kit — CURRENT STATE edition — Markdown docs\n"
        "=====================================================================\n"
        "FedRAMP Moderate / GCC Moderate. De-branded (no agency names).\n"
        "Build date: {date}\n\n"
        "Plain Markdown, docs only — no ServiceNow kit source, no Word. For pasting\n"
        "into an AI tool or uploading to an AI 'project'. For the deployable kit\n"
        "(Script Includes, ATF, catalog/flow/update-set, plus these docs as Word), see\n"
        "orgcomp-day2-kit-active-directory-latest.zip.\n\n"
        "START HERE: 0_START_HERE.md, then 2_Build_Delta.md, then 5_Operator_Usage.md.\n"
    ),
    "target": (
        "OrgComp Day-2 Automation Kit — 2027 TARGET STATE edition — Markdown docs\n"
        "==========================================================================\n"
        "FedRAMP Moderate / GCC Moderate. De-branded (no agency names).\n"
        "Build date: {date}\n\n"
        "Plain Markdown, docs only — no ServiceNow kit source, no Word. For pasting\n"
        "into an AI tool or uploading to an AI 'project'. For the deployable kit\n"
        "(Script Includes, ATF, catalog/flow/update-set, plus these docs as Word), see\n"
        "orgcomp-day2-kit-hrit-latest.zip.\n\n"
        "START HERE: 0_START_HERE.md, then 7_Build_Specification.md, then\n"
        "2_Variables_Reference.md.\n"
    ),
}

README_CURRENT = """OrgComp Day-2 Automation Kit — CURRENT STATE edition
====================================================
FedRAMP Moderate / GCC Moderate. De-branded (no agency names).
Build date: {date}

RUN THIS EDITION TODAY. Your Entra ID users are synced from Active Directory
(Entra Connect): AD is the identity master, Entra is its projection. So for a
synced object, lifecycle / attribute / password / AD-group writes land in AD (the
added AD leg, AdHybridClient) and flow to Entra; cloud-native objects (MFA, Azure
RBAC, license, guest, app consent) stay on Graph/ARM. Property hybrid_mode = true.

UPGRADE PATH. When identity mastering moves to the OPM-HRIT SSOT (the Federal
HR 2.0 Core HCM platform — Oracle Fusion Cloud HCM; Wave 2 agency transitions
complete in FY 2027) and provisioning goes cloud-native into Entra, upgrade to
the HRIT edition
(orgcomp-day2-kit-hrit-latest.zip): the same scripts with hybrid_mode = false, so
the AD leg retires. It is a configuration change, not a rebuild.

CONTENTS
  servicenow-day2/   the deployable kit source (Script Includes incl. AdHybridClient,
                     scripted-rest, control maps, atf/, catalog/, flow/, update-set/,
                     gates), with each *.md AND its rendered .docx sibling. The
                     CURRENT-STATE-*.md docs cover the hybrid delta; shared KIT-*
                     docs (variables, implementation, scripts, build spec, SAM) apply
                     to both editions.
  docx/              the Current State doc set as Word, in reading order (0..8),
                     including a diagram for every catalog task's current-state
                     write path (Operator Usage).

START HERE
  1. docx/0_START_HERE       — what changes and the sandbox rule
  2. docx/2_Build_Delta      — the AD MID, AdHybridClient, the router, the properties
  3. docx/5_Operator_Usage   — each task's current-state write path
  Build the base platform first: docx/7_Build_Specification, then the delta.

Rebuilt from source on every site deploy — no fixed SHA-256 is published for the
kit as a whole (it changes on every rebuild), but MANIFEST-SHA256.txt inside this
archive gives you a per-file SHA-256, generated at this exact build, so you can
verify nothing was altered in transit or storage after download.
"""

README_TARGET = """OrgComp Day-2 Automation Kit — 2027 TARGET STATE edition
========================================================
FedRAMP Moderate / GCC Moderate. De-branded (no agency names).
Build date: {date}

THE 2027 GOAL. Identities originate cloud-native from the OPM-HRIT SSOT — the
Federal HR 2.0 Core HCM platform (Oracle Fusion Cloud HCM, awarded June 2026;
OMB/OPM memo of December 10, 2025) — and are actuated directly in Entra Graph /
Azure ARM, no on-prem AD write leg. Property hybrid_mode = false.

CONTENTS
  servicenow-day2/   the deployable kit source (Script Includes, scripted-rest,
                     control maps, atf/, catalog/, flow/, update-set/, gates), with
                     each *.md AND its rendered .docx sibling.
  docx/              the Target doc set as Word, in reading order (0..8), including
                     a cloud-native write-path diagram for every catalog task
                     (Usage Operator).

START HERE
  1. docx/0_START_HERE          — ordered steps, disclaimers, debug, sandbox-first
  2. docx/7_Build_Specification — tables, ACLs, roles, the 50-item catalog, export
  3. docx/2_Variables_Reference — fill in your environment's values

Rebuilt from source on every site deploy — no fixed SHA-256 is published for the
kit as a whole (it changes on every rebuild), but MANIFEST-SHA256.txt inside this
archive gives you a per-file SHA-256, generated at this exact build, so you can
verify nothing was altered in transit or storage after download.
"""

READMES = {"current": README_CURRENT, "target": README_TARGET}


def collect(site_root: Path, src_root: Path, edition: str) -> tuple[dict[str, Path], list[str]]:
    members: dict[str, Path] = {}
    notes: list[str] = []
    kit_src = src_root / KIT_SRC_REL
    site_series = site_root / SITE_SERIES_REL
    exclude = _is_target_only if edition == "current" else _is_current_only

    # 1. Kit source — every file under servicenow-day2/ minus the other edition's.
    n_src = 0
    if kit_src.is_dir():
        for f in sorted(kit_src.rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(kit_src).as_posix()
            if exclude(rel):
                continue
            members[f"servicenow-day2/{rel}"] = f
            n_src += 1
    notes.append(f"kit source files: {n_src}")

    # 2. Rendered .docx beside their .md (shared + this edition's).
    md_map = {**SHARED_MD_DOCX, **(CURRENT_MD_DOCX if edition == "current" else TARGET_MD_DOCX)}
    n_beside = 0
    for md, stem in md_map.items():
        docx = site_series / f"{stem}.docx"
        if docx.is_file():
            members[f"servicenow-day2/{md}.docx"] = docx
            n_beside += 1
    notes.append(f"KIT .docx beside .md: {n_beside}/{len(md_map)}")

    # 3. Reading-order docx/ set for this edition.
    docx_set = CURRENT_DOCX_SET if edition == "current" else TARGET_DOCX_SET
    n_set = 0
    for stem, name in docx_set.items():
        docx = site_series / f"{stem}.docx"
        if docx.is_file():
            members[f"docx/{name}"] = docx
            n_set += 1
    notes.append(f"docx/ set: {n_set}/{len(docx_set)}")

    return members, notes


def collect_markdown(site_root: Path, edition: str) -> tuple[dict[str, Path], list[str]]:
    """Return {archive_name: source .md file} for this edition's numbered doc set.

    Same reading-order dicts as the Word docx/ set (``TARGET_DOCX_SET`` /
    ``CURRENT_DOCX_SET``), resolved to the ``.md`` sibling rendered by
    render_md_orgcomp instead of the ``.docx``.
    """
    members: dict[str, Path] = {}
    notes: list[str] = []
    site_series = site_root / SITE_SERIES_REL
    docx_set = CURRENT_DOCX_SET if edition == "current" else TARGET_DOCX_SET

    n_set = 0
    for stem, docx_name in docx_set.items():
        md = site_series / f"{stem}.md"
        if md.is_file():
            members[Path(docx_name).with_suffix(".md").name] = md
            n_set += 1
    notes.append(f"markdown doc set: {n_set}/{len(docx_set)}")

    return members, notes


def build_markdown_one(site_root: Path, out_dir: Path, date_code: str, edition: str) -> int:
    members, notes = collect_markdown(site_root, edition)
    label = "Current State" if edition == "current" else "2027 Target State"
    print(f"OrgComp Day-2 Automation Kit — {label} edition — Markdown docs")
    print("=" * 52)
    for n in notes:
        print(" ", n)

    if not members:
        print(f"\nWARNING: no markdown docs found in _site for {label} — skipping markdown zip.")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    root = ROOTS[edition]
    zip_path = out_dir / ZIP_NAMES_MD[edition]
    readme = README_MD[edition].format(date=date_code)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{root}/README.txt", readme)
        for arc, src in sorted(members.items()):
            z.write(src, f"{root}/{arc}")

    size_kb = zip_path.stat().st_size / 1024
    print(f"Wrote {zip_path}  ({len(members) + 1} files, {size_kb:.1f} KB)\n")
    return 0


def build_one(site_root: Path, src_root: Path, out_dir: Path, date_code: str, edition: str) -> int:
    members, notes = collect(site_root, src_root, edition)
    label = "Current State" if edition == "current" else "2027 Target State"
    print(f"OrgComp Day-2 Automation Kit — {label} edition")
    print("=" * 52)
    for n in notes:
        print(" ", n)

    if not any(k.startswith("servicenow-day2/") for k in members):
        print(f"\nFATAL: no kit source collected for {label} — refusing to ship an empty kit.")
        return 1
    if not any(k.endswith(".docx") for k in members):
        print(
            f"\nWARNING: no .docx renders found in _site for {label} — shipping source only "
            "(did the Quarto render run first?)."
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    root = ROOTS[edition]
    zip_path = out_dir / ZIP_NAMES[edition]
    readme_bytes = READMES[edition].format(date=date_code).encode("utf-8")
    hashes: list[tuple[str, str]] = [(f"{root}/README.txt", hashlib.sha256(readme_bytes).hexdigest())]
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{root}/README.txt", readme_bytes)
        for arc, src in sorted(members.items()):
            arcname = f"{root}/{arc}"
            z.write(src, arcname)
            hashes.append((arcname, hashlib.sha256(src.read_bytes()).hexdigest()))
        # Per-file integrity check for this exact build — the kit as a whole has
        # no fixed hash (it's rebuilt on every deploy), but a recipient can verify
        # no individual file was altered after this build produced it.
        manifest_lines = [f"{h}  {arc}" for arc, h in sorted(hashes)]
        manifest = (
            f"SHA-256 manifest — OrgComp Day-2 Automation Kit — {label} edition\n"
            f"Build date: {date_code}\n"
            f"Generated at build time by scripts/build_day2_kit_download.py — verify with\n"
            f"'sha256sum -c' (strip the archive-relative prefix first) or equivalent.\n\n"
            + "\n".join(manifest_lines)
            + "\n"
        )
        z.writestr(f"{root}/MANIFEST-SHA256.txt", manifest)

    size_kb = zip_path.stat().st_size / 1024
    print(f"Wrote {zip_path}  ({len(members) + 2} files, {size_kb:.1f} KB)\n")
    return 0


def build(site_root: Path, src_root: Path, out_dir: Path, date_code: str) -> int:
    rc = 0
    for edition in ("current", "target"):
        rc |= build_one(site_root, src_root, out_dir, date_code, edition)
        # Markdown-only doc zips are additive and never fatal to the main
        # kit build — a missing markdown render (e.g. render_md_orgcomp
        # skipped) just means no markdown zip this deploy.
        rc |= build_markdown_one(site_root, out_dir, date_code, edition)
    return rc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--site-root", type=Path, required=True, help="rendered _site root")
    ap.add_argument("--src-root", type=Path, required=True, help="repo source root")
    ap.add_argument("--out", type=Path, required=True, help="output dir for the zips")
    ap.add_argument("--date-code", default="unknown", help="build date label for the READMEs")
    args = ap.parse_args(argv)
    return build(args.site_root, args.src_root, args.out, args.date_code)


if __name__ == "__main__":
    raise SystemExit(main())
