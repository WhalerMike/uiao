#!/usr/bin/env python3
"""Build the standalone OrgComp Day-2 Automation Kit download zip.

The day-2 kit ships inside the full federal-series bundle under
kits/servicenow-day2/, but an implementation team wants it on its own. This
emits ``orgcomp-day2-kit-latest.zip`` — the deployable ServiceNow kit source
(Script Includes, the scripted REST resource, control maps, ATF, catalog,
update-set + flow specs) PLUS the reference/usage/build docs in BOTH forms:
each KIT-*.md with its rendered .docx sibling, and a numbered docx/ set in
reading order.

Reads the rendered .docx from ``_site`` (the only correct, house-styled source)
and the kit source from the repo. Federal edition only. Deterministic and
gap-reporting: if the .docx renders are missing it says so rather than shipping
a source-only kit that looks complete.

Usage (called from the Quarto assemble job, after the site renders):
    python scripts/build_day2_kit_download.py \
        --site-root _site --src-root . --out _site/download --date-code YYYY-MM-DD
"""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

ZIP_NAME = "orgcomp-day2-kit-latest.zip"
SERIES = "customer-documents/orgcomp-series"
KIT_SRC_REL = f"docs/{SERIES}/servicenow-day2"
SITE_SERIES_REL = f"{SERIES}"

# Rendered .docx (in _site) → name to place BESIDE the matching .md in the kit.
MD_DOCX = {
    "START-HERE": "OrgComp_Day2_Kit_0_Start_Here",
    "KIT-VARIABLES-REFERENCE": "OrgComp_Day2_Kit_1_Variables_Reference",
    "KIT-SCRIPTS": "OrgComp_Day2_Kit_2_Scripts_Manifest",
    "KIT-IMPLEMENTATION-GUIDE": "OrgComp_Day2_Kit_3_Implementation_Guide",
    "KIT-USAGE-OPERATOR": "OrgComp_Day2_Kit_4_Usage_Operator",
    "KIT-USAGE-SAM-INTEGRATION": "OrgComp_Day2_Kit_5_Usage_SAM_Integration",
    "KIT-BUILD-SPEC": "OrgComp_Day2_Kit_6_Build_Specification",
    # Current State edition (hybrid, AD-mastered — Entra Connect syncs AD->Entra).
    # The base KIT-* docs above describe the 2027 Target State; these describe the
    # estate as it is today and add the AD write leg. Same scripts, hybrid_mode switch.
    "CURRENT-STATE-START-HERE": "OrgComp_Day2_Kit_Current_0_Start_Here",
    "CURRENT-STATE-OPERATOR-USAGE": "OrgComp_Day2_Kit_Current_1_Operator_Usage",
    "CURRENT-STATE-SCRIPTS": "OrgComp_Day2_Kit_Current_2_Scripts",
    "CURRENT-STATE-BUILD-DELTA": "OrgComp_Day2_Kit_Current_3_Build_Delta",
    # Remaining .md — a .docx sibling for every document in the kit. Keys are
    # paths relative to servicenow-day2/, so subfolder READMEs land in place.
    "README": "OrgComp_Day2_Kit_Overview_README",
    "flow/flow-blueprint": "OrgComp_Day2_Kit_Flow_Blueprint",
    "catalog/README": "OrgComp_Day2_Kit_Catalog_README",
    "atf/README": "OrgComp_Day2_Kit_ATF_README",
    "update-set/README": "OrgComp_Day2_Kit_UpdateSet_README",
}

# Rendered .docx (in _site) → reading-order name in the top-level docx/ folder.
DOCX_SET = {
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

# Current State edition, as its own reading-order set under docx/Current_State/.
# This is the edition to run TODAY (hybrid, AD-mastered); the numbered set above
# is the 2027 Target State.
DOCX_SET_CURRENT = {
    "OrgComp_Day2_Kit_Current_0_Start_Here": "Current_State/0_START_HERE.docx",
    "OrgComp_Day2_Kit_Current_1_Operator_Usage": "Current_State/1_Operator_Usage.docx",
    "OrgComp_Day2_Kit_Current_2_Scripts": "Current_State/2_Scripts.docx",
    "OrgComp_Day2_Kit_Current_3_Build_Delta": "Current_State/3_Build_Delta.docx",
}

README = """OrgComp Day-2 Automation Kit
============================
FedRAMP Moderate / GCC Moderate. De-branded (no agency names).
Build date: {date}

ServiceNow day-2 operations integrated with Entra/Azure (Graph + ARM via the
in-boundary MID) and SailPoint SAM (IdentityIQ push primary; ISC secondary).
Every task travels the MACD-R lifecycle: SSOT-originated -> authoritatively
authorized -> least-privilege / JIT PIM -> provenance-closed -> evidence emitted.

TWO EDITIONS (same scripts, switched by x_fed_day2_ops.hybrid_mode)
  CURRENT STATE (run this today) — a hybrid, AD-mastered estate: Active Directory
    is the identity master and Entra Connect syncs AD->Entra. Synced-object
    lifecycle / attribute / password / AD-group writes land in AD (the added AD
    leg) and flow to Entra; cloud-native objects (MFA, Azure RBAC, license, guest,
    app consent) stay on Graph/ARM. hybrid_mode = true.
  2027 TARGET STATE (the base kit) — OPM-HRIT as SSOT, provisioning cloud-native
    straight into Entra. hybrid_mode = false. Keep it as the goal.

CONTENTS
  servicenow-day2/   the deployable kit source (Script Includes incl. the current-
                     state AdHybridClient, scripted-rest, control maps, atf/,
                     catalog/, flow/, update-set/, gates), with each *.md AND its
                     rendered .docx sibling. The CURRENT-STATE-*.md docs cover the
                     hybrid delta; the KIT-*.md docs describe the 2027 target.
  docx/              the 2027 Target doc set as Word, in reading order (1..8).
  docx/Current_State/  the Current State doc set as Word (0..3), incl. a diagram
                     for every catalog task showing its current-state write path.

START HERE
  If your Entra users are synced from Active Directory today (most likely):
    1. docx/Current_State/0_START_HERE   — what changes and the sandbox rule
    2. docx/Current_State/3_Build_Delta  — the AD MID, AdHybridClient, the router
    3. docx/Current_State/1_Operator_Usage — each task's current-state write path
    Build the base platform first: docx/7_Build_Specification, then the delta.

Rebuilt from source on every site deploy — no fixed SHA-256 is published.
"""


def collect(site_root: Path, src_root: Path) -> tuple[dict[str, Path], list[str]]:
    members: dict[str, Path] = {}
    notes: list[str] = []
    kit_src = src_root / KIT_SRC_REL
    site_series = site_root / SITE_SERIES_REL

    # 1. Kit source — every file under servicenow-day2/.
    n_src = 0
    if kit_src.is_dir():
        for f in sorted(kit_src.rglob("*")):
            if f.is_file():
                members[f"servicenow-day2/{f.relative_to(kit_src).as_posix()}"] = f
                n_src += 1
    notes.append(f"kit source files: {n_src}")

    # 2. Rendered .docx beside their .md in servicenow-day2/.
    n_beside = 0
    for md, stem in MD_DOCX.items():
        docx = site_series / f"{stem}.docx"
        if docx.is_file():
            members[f"servicenow-day2/{md}.docx"] = docx
            n_beside += 1
    notes.append(f"KIT .docx beside .md: {n_beside}/{len(MD_DOCX)}")

    # 3. Reading-order docx/ set (2027 Target State) + the Current State set.
    n_set = 0
    for stem, name in {**DOCX_SET, **DOCX_SET_CURRENT}.items():
        docx = site_series / f"{stem}.docx"
        if docx.is_file():
            members[f"docx/{name}"] = docx
            n_set += 1
    total_set = len(DOCX_SET) + len(DOCX_SET_CURRENT)
    notes.append(f"docx/ set: {n_set}/{total_set} (incl. {len(DOCX_SET_CURRENT)} Current State)")

    return members, notes


def build(site_root: Path, src_root: Path, out_dir: Path, date_code: str) -> int:
    members, notes = collect(site_root, src_root)
    print("OrgComp Day-2 Automation Kit — build inputs")
    print("=" * 48)
    for n in notes:
        print(" ", n)

    if not any(k.startswith("servicenow-day2/") for k in members):
        print("\nFATAL: no kit source collected — refusing to ship an empty kit.")
        return 1
    if not any(k.endswith(".docx") for k in members):
        print("\nWARNING: no .docx renders found in _site — shipping source only (did the Quarto render run first?).")

    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / ZIP_NAME
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("OrgComp-Day2-Kit/README.txt", README.format(date=date_code))
        for arc, src in sorted(members.items()):
            z.write(src, f"OrgComp-Day2-Kit/{arc}")

    size_kb = zip_path.stat().st_size / 1024
    print(f"\nWrote {zip_path}  ({len(members) + 1} files, {size_kb:.1f} KB)")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--site-root", type=Path, required=True, help="rendered _site root")
    ap.add_argument("--src-root", type=Path, required=True, help="repo source root")
    ap.add_argument("--out", type=Path, required=True, help="output dir for the zip")
    ap.add_argument("--date-code", default="unknown", help="build date label for the README")
    args = ap.parse_args(argv)
    return build(args.site_root, args.src_root, args.out, args.date_code)


if __name__ == "__main__":
    raise SystemExit(main())
