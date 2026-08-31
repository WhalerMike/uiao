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
import re
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
    # The live-validation tracks. Until these were wired up they rendered to no
    # .docx and appeared in no reading-order set, so a Word-only reader received
    # neither -- and START-HERE pointed at "the tracks below" that were not there.
    "CURRENT-STATE-PDI-VALIDATION": "OrgComp_Day2_Kit_Current_5_PDI_Validation",
    "CURRENT-STATE-AD-LAB-VALIDATION": "OrgComp_Day2_Kit_Current_6_AD_Lab_Validation",
    # The seam between the two tracks above: a PDI never picks the ECC row up,
    # the AD lab never writes one, so the transport itself was covered by
    # neither.
    "CURRENT-STATE-MID-BRIDGE": "OrgComp_Day2_Kit_Current_7_MID_Bridge",
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
    # Slot 8 was 8_Operator_Runbook.docx, dropped: no .md source in the kit, so
    # the doc-name map could only ever list 9 of 10; superseded by
    # 5_Operator_Usage (11 tasks vs 8); and it carried a team byline and a Draft
    # Proposal block in a de-branded kit. It still renders to the site from its
    # own .qmd -- this stops it being BUNDLED, not published.
    # Replaced by the shared Scripts Manifest, which 4_Implementation_Guide
    # references and this edition did not ship, so those references were
    # flattened to "(not in this bundle)".
    "OrgComp_Day2_Kit_2_Scripts_Manifest": "8_Scripts_Manifest.docx",
    "OrgComp_Day2_Kit_Current_4_Pilot_Rollout": "9_Pilot_Rollout.docx",
    # Appended rather than slotted before the pilot: renumbering 0..9 would
    # churn every existing filename for a reading-order nicety. Sequence is
    # carried where it binds to a decision instead -- CURRENT-STATE-PILOT-ROLLOUT
    # §0 now requires both tracks before the pilot may start.
    "OrgComp_Day2_Kit_Current_5_PDI_Validation": "10_PDI_Validation.docx",
    "OrgComp_Day2_Kit_Current_6_AD_Lab_Validation": "11_AD_Lab_Validation.docx",
    # Appended for the same reason as 10 and 11: renumbering to place it beside
    # them would churn every existing filename. Reading order is carried by
    # CURRENT-STATE-START-HERE §6, which sequences all three tracks.
    "OrgComp_Day2_Kit_Current_7_MID_Bridge": "12_MID_Bridge.docx",
}


# --- Bundle doc-name rewriting. ------------------------------------------------
# Both zips renumber every document (KIT-VARIABLES-REFERENCE -> 1_Variables_Reference)
# and drop the other edition's docs. The doc bodies cross-reference each other by
# their repo names, so without a rewrite every one of those references is dead in
# the shipped bundle -- and a reference to a doc this edition does not ship is dead
# in a second, worse way: it names a file that is simply not there.
#
# The map is COMPOSED from the two dicts above (repo stem -> docx stem -> numbered
# name) rather than hand-maintained, so it cannot drift from the reading order.

# Docs that exist in the repo and may be referenced by name, but are not part of
# either edition's numbered set (validation write-ups; the per-directory READMEs).
_EXTRA_DOC_STEMS = (
    "CURRENT-STATE-PDI-VALIDATION",
    "CURRENT-STATE-AD-LAB-VALIDATION",
)

# What to say when a referenced doc is not in this edition's bundle.
_ABSENT_NOTE = "not in this bundle"

# --- Figures. ------------------------------------------------------------------
# ADR-093: the committed figure source is SVG; the sibling PNG the docs reference
# is an untracked build artifact rasterized in CI. This script's --src-root is a
# fresh sparse checkout, so it sees the .svg and NOT the .png -- while every
# <img src> in the doc bodies names the .png. The rendered PNGs do exist in the
# Quarto output, so the deployable kit takes its figures from --site-root.
#
# The markdown-only zip carries no kit source tree at all (docs only, by design),
# so a relative figure path can never resolve there. Its <img> srcs are rewritten
# to the published site instead: the image loads for a human, and the
# data-fig-alt description -- which is what an AI reads -- is untouched.
QUARTO_CONFIG_REL = "docs/_quarto.yml"
# Used only when the config cannot be read (see read_site_base). Kept in sync by
# the test that asserts it matches docs/_quarto.yml.
SITE_BASE_FALLBACK = "https://whalermike.github.io/uiao/"
FIGS_REL = f"{SERIES}/servicenow-day2/figs"


def read_site_base(src_root: Path) -> str:
    """The published site base, from ``site-url`` in docs/_quarto.yml.

    Deliberately a line scan, not a YAML parse: this script has no third-party
    imports and the CI step that runs it does not install pyyaml.

    A wrong base silently produces figure links that 404, so a config we cannot
    read is reported loudly -- but it falls back rather than raising, because
    the CI step is ``|| echo warning`` and an exception here would drop all four
    zips over a figure URL.
    """
    cfg = src_root / QUARTO_CONFIG_REL
    try:
        for line in cfg.read_text(encoding="utf8").splitlines():
            m = re.match(r"\s*site-url:\s*(\S+)\s*$", line)
            if m:
                return m.group(1).strip("\"'").rstrip("/") + "/"
        print(f"  WARNING: no 'site-url' in {cfg} — figure links fall back to {SITE_BASE_FALLBACK}")
    except OSError as e:
        print(f"  WARNING: cannot read {cfg} ({e}) — figure links fall back to {SITE_BASE_FALLBACK}")
    return SITE_BASE_FALLBACK


def rewrite_figure_srcs(text: str, site_base: str) -> tuple[str, int]:
    """Point relative figure srcs at the published site. Returns (text, n).

    Quarto's gfm output renders these as ``<img src=...>`` because the figures
    carry fig-alt and width attributes; the plain ``![alt](path)`` form is
    handled too, so a figure that loses its attributes does not silently start
    shipping a broken relative path again.
    """
    n_total = 0
    for pattern in (
        r'(<img\s+src=")(?:\./)?servicenow-day2/figs/',
        r"(!\[[^\]]*\]\()(?:\./)?servicenow-day2/figs/",
    ):
        text, n = re.subn(pattern, lambda m, b=site_base: f"{m.group(1)}{b}{FIGS_REL}/", text)
        n_total += n
    return text, n_total


def bundle_doc_names(edition: str) -> dict[str, str]:
    """{repo doc stem: numbered bundle stem} for this edition's doc set.

    e.g. current: ``KIT-VARIABLES-REFERENCE`` -> ``1_Variables_Reference``.
    Repo stems whose docx render is not in this edition's numbered set are
    absent from the result -- they do not ship in this bundle.
    """
    md_docx = {**SHARED_MD_DOCX, **(CURRENT_MD_DOCX if edition == "current" else TARGET_MD_DOCX)}
    docx_set = CURRENT_DOCX_SET if edition == "current" else TARGET_DOCX_SET
    return {
        repo_stem: Path(docx_set[docx_stem]).stem for repo_stem, docx_stem in md_docx.items() if docx_stem in docx_set
    }


def _known_doc_stems() -> list[str]:
    """Every repo doc stem a body might reference, longest first.

    Longest-first matters: ``CURRENT-STATE-START-HERE`` must win over
    ``START-HERE``. Path-like keys ("catalog/README") are excluded -- they name
    per-directory READMEs inside the kit source, not doc-set members.
    """
    stems = {
        *SHARED_MD_DOCX,
        *TARGET_MD_DOCX,
        *CURRENT_MD_DOCX,
        *_EXTRA_DOC_STEMS,
    }
    stems = {s for s in stems if "/" not in s}
    return sorted(stems, key=len, reverse=True)


def rewrite_doc_references(text: str, edition: str) -> tuple[str, int, dict[str, int]]:
    """Rewrite by-name cross-references in a doc body to bundle-relative names.

    Returns ``(text, n_rewritten, {absent_stem: count})``. A reference to a doc
    this edition does not ship is annotated rather than silently left dangling,
    and reported to the caller so the build can say so out loud.
    """
    names = bundle_doc_names(edition)
    rewritten = 0
    absent: dict[str, int] = {}

    for stem in _known_doc_stems():
        target = names.get(stem)
        # ``[text](./STEM.md)`` -- a real link. Retarget it, or flatten it to
        # plain text when the target does not ship in this edition.
        link = re.compile(r"\[([^\]]+)\]\((?:\./)?" + re.escape(stem) + r"\.md(#[^)]*)?\)")
        if target:
            text, n = link.subn(lambda m, t=target: f"[{m.group(1)}](./{t}.md{m.group(2) or ''})", text)
        else:
            text, n = link.subn(lambda m: f"{m.group(1)} ({_ABSENT_NOTE})", text)
            if n:
                absent[stem] = absent.get(stem, 0) + n
        rewritten += n

        # Bare or backticked name, with or without the .md suffix. "README" is
        # too common a word to match bare -- require its extension.
        suffix = r"(\.md)" if stem == "README" else r"(\.md)?"
        bare = re.compile(r"(?<![A-Za-z0-9/_-])" + re.escape(stem) + suffix + r"(?![A-Za-z0-9_-])")
        if target:
            text, n = bare.subn(lambda m, t=target: t + (m.group(1) or ""), text)
        else:
            text, n = bare.subn(lambda m, st=stem: f"{st}{m.group(1) or ''} ({_ABSENT_NOTE})", text)
            if n:
                absent[stem] = absent.get(stem, 0) + n
        rewritten += n

        # Backticked bare `README` -- unambiguous enough to annotate, unlike a
        # prose mention of "the README".
        if stem == "README":
            tick = re.compile(r"`README`")
            if target:
                text, n = tick.subn(f"`{target}`", text)
            else:
                text, n = tick.subn(f"`README` ({_ABSENT_NOTE})", text)
                if n:
                    absent[stem] = absent.get(stem, 0) + n
            rewritten += n

    return text, rewritten, absent


def doc_map_lines(edition: str) -> str:
    """The repo-name -> bundle-name table, for the zip READMEs.

    The Word bundle ships pre-rendered .docx whose bodies cannot be rewritten
    here, so its by-name references stay in repo form; this table is how a
    reader resolves them.
    """
    names = bundle_doc_names(edition)
    width = max(len(k) for k in names)
    return "\n".join(f"  {k.ljust(width)}  ->  {v}" for k, v in sorted(names.items(), key=lambda kv: kv[1]))


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
        "\n"
        "DOC NAMES. These docs are numbered for reading order; in the repo and in\n"
        "the deployable kit they carry their own names. Cross-references inside\n"
        "the bodies have been rewritten to the numbered names, so they resolve\n"
        "within this bundle. The mapping, if you need it:\n"
        "\n"
        "{doc_map}\n"
        "\n"
        "FIGURES. This bundle is Markdown only, so the diagrams are not files in\n"
        "here -- each <img> points at the published copy on the docs site. Every\n"
        "figure also carries a data-fig-alt description of what it shows, which is\n"
        "what an AI tool reads; no diagram content is lost if the images do not\n"
        "load.\n"
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
        "\n"
        "DOC NAMES. These docs are numbered for reading order; in the repo and in\n"
        "the deployable kit they carry their own names. Cross-references inside\n"
        "the bodies have been rewritten to the numbered names, so they resolve\n"
        "within this bundle. The mapping, if you need it:\n"
        "\n"
        "{doc_map}\n"
        "\n"
        "FIGURES. This bundle is Markdown only, so the diagrams are not files in\n"
        "here -- each <img> points at the published copy on the docs site. Every\n"
        "figure also carries a data-fig-alt description of what it shows, which is\n"
        "what an AI tool reads; no diagram content is lost if the images do not\n"
        "load.\n"
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
                     gates, plus RunBook/, lab/ and examples/ described below). The
                     CURRENT-STATE-*.md docs cover the hybrid delta; shared KIT-*
                     docs (variables, implementation, scripts, build spec, SAM) apply
                     to both editions. Every doc in the docx/ set below ships here as
                     its *.md source WITH a rendered .docx sibling. The three
                     directories below are the exception and carry Markdown and
                     scripts, with one .docx of their own noted where it exists.
    RunBook/         the live-validation RunBook (all three tracks), its cover
                     sheet, and a README index. The RunBook itself also ships as
                     Day2Kit-Live-Validation-RunBook.docx; the cover and README
                     are Markdown only.
    lab/             New-Day2AdLab.ps1 — stands up a throwaway Hyper-V AD lab for
                     the AD leg validation track. The single canonical copy.
    examples/        sample SAM push payloads (and a README) for exercising the
                     inbound endpoint. Markdown and JSON only.
  docx/              the Current State doc set as Word, in reading order (0..11),
                     including a diagram for every catalog task's current-state
                     write path (Operator Usage) and both live-validation tracks.

START HERE
  1. docx/0_START_HERE       — what changes and the sandbox rule
  2. docx/2_Build_Delta      — the AD MID, AdHybridClient, the router, the properties
  3. docx/5_Operator_Usage   — each task's current-state write path
  Build the base platform first: docx/7_Build_Specification, then the delta.
  Before the pilot: docx/10_PDI_Validation and docx/11_AD_Lab_Validation —
  docx/9_Pilot_Rollout §0 requires both (the AD lab track may be waived by the
  ISSO, with the waiver recorded).

DOC NAMES. Documents cross-reference each other by their repo names (the names
they carry under servicenow-day2/). The docx/ reading-order set renumbers them.
The mapping:

{doc_map}

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

DOC NAMES. Documents cross-reference each other by their repo names (the names
they carry under servicenow-day2/). The docx/ reading-order set renumbers them.
The mapping:

{doc_map}

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

    # 3. Rendered figure PNGs (ADR-093 rasterizes them in CI; --src-root only
    #    has the .svg sources, and every <img src> in the docs names the .png).
    n_png = 0
    site_figs = site_root / FIGS_REL
    if site_figs.is_dir():
        for png in sorted(site_figs.glob("*.png")):
            rel = f"figs/{png.name}"
            if exclude(rel):
                continue
            members[f"servicenow-day2/{rel}"] = png
            n_png += 1
    n_svg = sum(1 for k in members if k.startswith("servicenow-day2/figs/") and k.endswith(".svg"))
    notes.append(f"figure PNGs from _site: {n_png} (SVG sources from repo: {n_svg})")
    if n_svg and not n_png:
        notes.append(
            "  WARNING: shipping figure SVGs with no rendered PNG -- every <img> in "
            "the docs names a .png and will be broken. Did the rasterize step run?"
        )

    # 4. Reading-order docx/ set for this edition.
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


def build_markdown_one(site_root: Path, out_dir: Path, date_code: str, edition: str, src_root: Path) -> int:
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
    readme = README_MD[edition].format(date=date_code, doc_map=doc_map_lines(edition))

    # Every doc is renumbered on the way in, so rewrite the by-name
    # cross-references in each body to match -- otherwise they all point at
    # repo filenames that do not exist in this bundle.
    site_base = read_site_base(src_root)
    n_refs = 0
    n_figs = 0
    absent_total: dict[str, int] = {}
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{root}/README.txt", readme)
        for arc, src in sorted(members.items()):
            body, n, absent = rewrite_doc_references(src.read_text(encoding="utf8"), edition)
            n_refs += n
            for stem, count in absent.items():
                absent_total[stem] = absent_total.get(stem, 0) + count
            body, n_fig = rewrite_figure_srcs(body, site_base)
            n_figs += n_fig
            z.writestr(f"{root}/{arc}", body)

    print(f"  cross-references rewritten: {n_refs}")
    print(f"  figure srcs pointed at {site_base}: {n_figs}")
    if absent_total:
        detail = ", ".join(f"{k} x{v}" for k, v in sorted(absent_total.items()))
        print(f"  referenced but not in this edition (annotated '{_ABSENT_NOTE}'): {detail}")

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
    readme_bytes = READMES[edition].format(date=date_code, doc_map=doc_map_lines(edition)).encode("utf-8")
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
        rc |= build_markdown_one(site_root, out_dir, date_code, edition, src_root)
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
