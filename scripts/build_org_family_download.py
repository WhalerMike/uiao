#!/usr/bin/env python3
"""Build the OrgPath and OrgMod download kits — at deploy time, never committed.

The Org-family siblings of ``build_orgcomp_download.py``. OrgComp already had a
one-click "the whole series as a kit" download; OrgPath (governance) and OrgMod
(modernization) did not, even though both are published corpora of the same
size. This produces one zip per family, assembled on site deploy into
``_site/download/`` and never committed (AGENTS.md: no committed binaries).

WHERE THE CONTENT COMES FROM — ``_site``, AND ONLY ``_site``.
Every page in these families renders to ``.docx`` in the ``render_docx`` matrix
(it sweeps the whole ``customer-documents`` tree), and ``bundle_section_docx.py``
runs earlier in the same ``assemble`` job to emit the per-book
``Book_NN-bundle.docx`` files. So the rendered site already holds exactly the
Word documents these kits ship, and this script only has to select and group
them. Unlike the OrgComp kit there is no ``--src-root`` content: neither family
has committed ``.pptx`` decks or deployable operator-kit directories, and
neither carries the ``{{< meta agency.* >}}`` shortcodes that make the OrgComp
kit edition-sensitive (verified: every ``meta agency.`` reference in
``docs/customer-documents/`` is inside ``orgcomp-series/``). ``--src-root`` is
accepted and ignored, for CLI symmetry with the OrgComp builders.

WHY THE NARRATIVE SHIPS AS PER-BOOK BUNDLES AND EVERYTHING ELSE AS PAGES.
``orgpath-narrative`` is 314 chaptered pages across 32 books; shipping every
chapter would make the kit unusable, so it ships the ``Book_NN-bundle.docx``
per-book concatenations — the same call the OrgComp kit makes when it ships one
Word file per volume instead of ~90 per-book files. The other groups are 1–60
pages each, small enough that per-page files are the more useful unit, and they
keep their on-site directory layout inside the archive.

WHAT BELONGS TO WHICH FAMILY.
Not a guess: the two hub pages are the authority, and ``GROUPS`` below mirrors
them. ``docs/orgpath/index.qmd`` names the narrative, the reference
architecture, the OrgPath implementation guides, and the multi-cloud series.
``docs/orgmod/index.qmd`` names the modernization guides, the modernization
specs, the AD infrastructure bridge, and the SQL Server transformation as its
worked consumer — and ``operational-guides/index.qmd`` states outright that
that section is "the operational home of OrgMod", with the OrgPath
implementation guides as the one sub-section that belongs to the sibling.

THE TEST APPLIED TO THE SHARED ``operational-guides`` TREE.
"Operational home of OrgMod" is a statement about where the directory lives,
not a claim on every sub-section inside it. The dividing question is whether a
page's deliverable exists because an estate is *moving* (OrgMod) or because an
estate is *governed in steady state* (OrgPath). A modernization runbook that
happens to bind OrgPath — ``intune-arc-modernization/governed-path`` is the
clearest case — is still OrgMod: the deliverable is the move, and the
governance is how the move is bound. Three sub-sections fail that test in the
other direction and are listed in ``ORGPATH_GOVERNANCE_OPS``:

* ``active-governance-directory`` — stands up the in-path LDAP projection *of
  the OrgPath governance substrate* (ADR-092). Nothing in it migrates anything.
* ``ai-identity-governance`` — its own index says it applies "OrgPath identity
  governance" to the M-25-21 AI inventory. It governs a class of identities; no
  legacy estate is being retired.
* ``helpdesk-entra-operations`` — the steady-state authority model (SAM governs,
  ServiceNow routes) for an estate that is *already* hybrid, and one of its five
  pages is titled "OrgPath Identity Governance Structure" outright.

That constant is the single source for the split: the OrgPath kit uses it as
``include_dirs`` and the OrgMod ``Guides`` sweep folds it into ``exclude_dirs``,
so the two sides cannot drift apart into a page that ships twice or not at all.

HOW THE WHITEPAPER CORPUS IS SPLIT BETWEEN THE TWO KITS.
The whitepaper corpus is one flat section serving all four Org-family pillars,
so it cannot be swept wholesale into any one kit. ``reading-guide.qmd`` already
partitions it — six tracks, "grouped by the question they answer" — and the two
selections below follow that published grouping rather than an editorial call,
which keeps them auditable and gives a renamed paper somewhere to fail loudly:

* ``ORGMOD_WHITEPAPERS`` — Track 2 (Identity & Directory Modernization) and
  Track 4 (Network & Infrastructure Modernization), plus the one Track 1 paper
  that guide itself calls "the bridge into Track 2".
* ``ORGPATH_WHITEPAPERS`` — the rest of Track 1 (Governance Foundations) and
  Track 6 (Positioning, Comparison & Vendor Reads).

Two papers are cross-listed in the guide across a Track 2/4 and a Track 1/6
row. Each is single-homed here, in its primary track's kit:
``modernization-governance-whitepaper`` and ``uiao-vs-native-tools`` both ship
in the OrgMod kit only. A test asserts the two selections stay disjoint.

Tracks 3 (Zero Trust Assessment & Compliance Closure) and 5 (Federal
Program-Specific Alignment) reach neither kit, and neither do the two papers
the guide files outside the six tracks (``federal-compliance-for-moderate-
agencies`` and ``event-logging-fedramp-boundary-limitations``). All of those
are compliance material — OrgComp's, and OrgComp builds its kit elsewhere. The
whitepapers section publishes its own complete zip regardless.

Local preview (needs a rendered _site):
    python scripts/build_org_family_download.py --family all --site-root _site --out /tmp/dl
CI (site deploy):
    python scripts/build_org_family_download.py --family all --site-root _site \
        --src-root _repo --out _site/download --date-code "$(date -u +%F)"
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

# Everything both families publish lives under this subtree of the rendered site.
DOCS_SITE_REL = "customer-documents"

# Selection modes for a group (see Group.mode):
#   pages        — every page .docx under the directory, recursively, keeping
#                  the on-site relative layout. Section/book bundles are
#                  excluded so a group never ships both a page and a
#                  concatenation of it.
#   book-bundles — only the per-book ``Book_NN-bundle.docx`` concatenations
#                  bundle_section_docx.py wrote beside the book landing pages.
#   files        — an explicit list of filenames, for a group that is a few
#                  named pages out of a larger section rather than the section.
MODES = ("pages", "book-bundles", "files")

# The sub-sections of ``operational-guides`` that are OrgPath's, not OrgMod's —
# see "THE TEST APPLIED TO THE SHARED operational-guides TREE" above. Declared
# once and consumed from both sides of the split.
ORGPATH_GOVERNANCE_OPS = (
    "active-governance-directory",
    "ai-identity-governance",
    "helpdesk-entra-operations",
)

# The OrgPath sub-section of the same tree, which has always shipped in the
# OrgPath kit's Implementation folder instead.
ORGPATH_IMPLEMENTATION_DIR = "orgpath-implementation"

# Promoted out of the Guides sweep into its own top-level archive folder rather
# than reassigned — it is OrgMod's, just not filed under Guides.
ORGMOD_PROMOTED_DIR = "client-server-to-hybrid-cloud"

# Track 2 + Track 4 of docs/customer-documents/whitepapers/reading-guide.qmd,
# plus the Track 1 paper that guide names as "the bridge into Track 2". Order
# is reading order within each track, not alphabetical.
ORGMOD_WHITEPAPERS = (
    # Track 1 — the bridge into the modernization arc.
    "modernization-governance-whitepaper.docx",
    # Track 2 — Identity & Directory Modernization: the AD to Entra ID arc.
    "ad-to-entraid-migration-problem.docx",
    "session-vs-telemetry-identity.docx",
    "aodim-executive-whitepaper.docx",
    "modernization-journey.docx",
    "hybrid-join-without-governance.docx",
    "federal-ssot-alignment.docx",
    "uiao-vs-native-tools.docx",
    # Track 4 — Network & Infrastructure Modernization.
    "federal-application-aware-networking-architecture.docx",
    "tic3-sdwan-vs-dia.docx",
    "infoblox-hybrid-dns-unified-ddi.docx",
    "infoblox-dns-reference.docx",
    "field-office-wan-transformation-dp-consolidation.docx",
    "git-server-interfaces-whitepaper.docx",
)

# Track 1 + Track 6 of the same reading guide, less the two papers cross-listed
# into ORGMOD_WHITEPAPERS above. Order is reading order within each track.
ORGPATH_WHITEPAPERS = (
    # Track 1 — Governance Foundations: what UIAO is.
    "uiao-governance-os-whitepaper.docx",
    "zero-trust-governance-whitepaper.docx",
    "zero-trust-governance-principles.docx",
    "zero-trust-whole-agency-unification.docx",
    # Track 6 — Positioning, Comparison & Vendor Reads.
    "orgpath-composability-matrix.docx",
    "snowflake-keypair-vs-uiao-orgpath.docx",
)


@dataclass(frozen=True)
class Group:
    """One archive folder, and the rendered-site directory that fills it."""

    folder: str
    site_rel: str
    mode: str
    #: mode "files" — filenames (relative to site_rel) to take, in order.
    only: tuple[str, ...] = ()
    #: mode "pages" — immediate sub-directory names to skip entirely.
    exclude_dirs: tuple[str, ...] = ()
    #: mode "pages" — if set, take *only* these immediate sub-directories.
    #: The inverse of exclude_dirs, for a group that is a few named
    #: sub-sections carved out of a larger shared tree.
    include_dirs: tuple[str, ...] = ()
    #: Loud-gap floor. A group that collects fewer files than this reports a
    #: WARNING in the build log rather than silently shrinking the kit — the
    #: failure mode where a renamed section quietly drops out of the download.
    min_expected: int = 1
    #: One line for the kit's INDEX.md, saying what the folder holds.
    blurb: str = ""


@dataclass(frozen=True)
class Family:
    key: str
    title: str
    zip_name: str
    tagline: str
    groups: tuple[Group, ...] = field(default_factory=tuple)


FAMILIES: dict[str, Family] = {
    "orgpath": Family(
        key="orgpath",
        title="OrgPath — Governance",
        zip_name="orgpath-governance-series-latest.zip",
        tagline=(
            "The governance expression of the UIAO substrate: canon as the source of\n"
            "truth, addressing as the governed namespace. OrgTree, OrgPath, and LocPath\n"
            "give every identity, device, and policy a governed address."
        ),
        groups=(
            Group(
                folder="Narrative",
                site_rel="orgpath-narrative",
                mode="book-bundles",
                min_expected=20,
                blurb="The OrgPath reading sequence — one Word file per book (chapters concatenated).",
            ),
            Group(
                folder="Reference_Architecture",
                site_rel="reference-architecture",
                mode="pages",
                min_expected=10,
                blurb="OrgTree, LocPath, the codebook, drift, delegation, dynamic groups, portability.",
            ),
            Group(
                folder="Implementation",
                site_rel="operational-guides/orgpath-implementation",
                mode="pages",
                min_expected=5,
                blurb="The seven-step OrgPath rollout onto Intune and Azure Arc, prerequisites through operate.",
            ),
            Group(
                folder="Multi_Cloud",
                site_rel="orgpath-multicloud",
                mode="pages",
                min_expected=5,
                blurb="OrgPath beyond Microsoft — binding profiles, the other identity planes, VMware, zero trust.",
            ),
            Group(
                folder="Governance_Operations",
                site_rel="operational-guides",
                mode="pages",
                # The three sub-sections of OrgMod's operational home that are
                # steady-state governance rather than migration — see
                # ORGPATH_GOVERNANCE_OPS. They shipped in the OrgMod kit until
                # this triage; the OrgMod Guides sweep now excludes them from
                # the same constant.
                include_dirs=ORGPATH_GOVERNANCE_OPS,
                min_expected=8,
                blurb=(
                    "Steady-state governance operations — the Active Governance Directory LDAP "
                    "projection, federal AI identity governance, and the Help Desk / Cloud Services "
                    "authority model for an already-hybrid estate."
                ),
            ),
            Group(
                folder="Whitepapers",
                site_rel="whitepapers",
                mode="files",
                # Not the whole section: see ORGPATH_WHITEPAPERS. The
                # modernization tracks of the same guide ship in the OrgMod kit.
                only=ORGPATH_WHITEPAPERS,
                min_expected=6,
                blurb=(
                    "The governance papers — governance foundations (Track 1) and positioning and "
                    "vendor reads (Track 6) from the whitepaper reading guide. The modernization "
                    "tracks ship in the OrgMod kit; the compliance tracks in neither."
                ),
            ),
        ),
    ),
    "orgmod": Family(
        key="orgmod",
        title="OrgMod — Modernization",
        zip_name="orgmod-modernization-series-latest.zip",
        tagline=(
            "The modernization expression of the UIAO substrate: moving a legacy estate\n"
            "forward without rip-and-replace, governed by the same spine. Active\n"
            "Directory to Entra ID is the leading worked path, not the only one."
        ),
        groups=(
            Group(
                folder="Transformation_Narrative",
                site_rel="operational-guides/client-server-to-hybrid-cloud",
                mode="pages",
                min_expected=8,
                blurb="Microsoft Client-Server to Hybrid-Cloud — the chapter narrative of the full arc.",
            ),
            Group(
                folder="Guides",
                site_rel="operational-guides",
                mode="pages",
                # orgpath-implementation and the three ORGPATH_GOVERNANCE_OPS
                # sub-sections belong to OrgPath and ship in that kit instead;
                # client-server-to-hybrid-cloud is promoted to its own
                # top-level folder above rather than duplicated here.
                exclude_dirs=(ORGPATH_IMPLEMENTATION_DIR, ORGMOD_PROMOTED_DIR, *ORGPATH_GOVERNANCE_OPS),
                # 44 pages after the governance sub-sections left; the floor
                # stays well under that so a real gap is still loud.
                min_expected=25,
                blurb=(
                    "The modernization guide shelf — platform substrate, transformation engine, "
                    "identity/OrgTree, directory migration, target surface, access plane, network "
                    "transformation, program management."
                ),
            ),
            Group(
                folder="Modernization_Specs",
                site_rel="modernization-specs",
                mode="pages",
                min_expected=5,
                blurb="Cross-adapter specs — cloud, identity, SASE, SD-WAN, telemetry, zero trust.",
            ),
            Group(
                folder="Directory_Migration_Bridge",
                site_rel="reference-architecture",
                mode="files",
                # The two reference-architecture pages the OrgMod hub names as
                # its entry point. The rest of that section is addressing-plane
                # canon and ships in the OrgPath kit.
                only=("directory-migration.docx", "adapters.docx"),
                min_expected=2,
                blurb="The AD infrastructure bridge — what replaces AD's implicit roles, and the adapter interfaces.",
            ),
            Group(
                folder="Whitepapers",
                site_rel="whitepapers",
                mode="files",
                # Not the whole section: the whitepaper corpus serves all four
                # pillars. These are the Track 2 + Track 4 papers of
                # whitepapers/reading-guide.qmd plus its named Track 1 bridge —
                # see ORGMOD_WHITEPAPERS.
                only=ORGMOD_WHITEPAPERS,
                min_expected=14,
                blurb=(
                    "The modernization papers — the AD to Entra ID arc (Track 2) and network and "
                    "infrastructure modernization (Track 4) from the whitepaper reading guide. The "
                    "rest of that section is OrgPath, compliance, and positioning material."
                ),
            ),
            Group(
                folder="SQL_Server_Transformation/Narrative",
                site_rel="sql-server-narrative",
                mode="book-bundles",
                min_expected=5,
                blurb="The worked consumer — a twenty-year SQL estate off Windows Authentication, one file per book.",
            ),
            Group(
                folder="SQL_Server_Transformation/Implementation",
                site_rel="sql-server-implementation",
                mode="pages",
                min_expected=5,
                blurb="The executable companion to the SQL Server narrative.",
            ),
        ),
    ),
}


def _is_bundle(name: str) -> bool:
    """True for a section/book/volume bundle filename.

    Case-insensitive because the OrgComp per-volume pass writes
    ``-Bundle.docx`` with a capital B while every other pass writes
    ``-bundle.docx`` — the same case-insensitive test bundle_section_docx.py
    uses when it excludes prior bundles from a re-run.
    """
    return name.lower().endswith("-bundle.docx")


def _collect_group(docs_site: Path, group: Group) -> tuple[dict[str, Path], list[str]]:
    """Return {archive_path: source_file} for one group, plus its build notes."""
    members: dict[str, Path] = {}
    notes: list[str] = []
    src = docs_site / group.site_rel

    if not src.is_dir():
        notes.append(f"  MISSING: {group.site_rel} not found under {docs_site} — group '{group.folder}' is empty")
        return members, notes

    if group.mode == "files":
        for name in group.only:
            f = src / name
            if f.is_file():
                members[f"{group.folder}/{name}"] = f
            else:
                notes.append(f"  missing page (skipped): {group.site_rel}/{name}")
    elif group.mode == "book-bundles":
        for f in sorted(src.rglob("Book_*-bundle.docx")):
            members[f"{group.folder}/{f.name}"] = f
    elif group.mode == "pages":
        excluded = set(group.exclude_dirs)
        included = set(group.include_dirs)
        for f in sorted(src.rglob("*.docx")):
            rel = f.relative_to(src)
            if included and rel.parts[0] not in included:
                continue
            if rel.parts[0] in excluded:
                continue
            if _is_bundle(f.name):
                continue
            members[f"{group.folder}/{rel.as_posix()}"] = f
    else:  # pragma: no cover — guarded by the MODES assertion in main()
        raise ValueError(f"unknown group mode: {group.mode!r}")

    notes.append(f"{group.folder}: {len(members)} file(s) from {group.site_rel} ({group.mode})")
    if len(members) < group.min_expected:
        notes.append(
            f"  WARNING: expected at least {group.min_expected}, found {len(members)} — "
            "did the DOCX render (and, for book bundles, bundle_section_docx.py) run first?"
        )
    return members, notes


def collect(site_root: Path, family: Family) -> tuple[dict[str, Path], list[str]]:
    """Return {archive_path: source_file} and gap-reporting build notes.

    Deterministic and loud about gaps: a group that comes back short says so in
    the log rather than shipping a silently thinner kit that looks complete.
    """
    docs_site = site_root / DOCS_SITE_REL
    members: dict[str, Path] = {}
    notes: list[str] = []
    for group in family.groups:
        got, group_notes = _collect_group(docs_site, group)
        members.update(got)
        notes.extend(group_notes)
    notes.append(f"total: {len(members)} file(s) across {len(family.groups)} group(s)")
    return members, notes


def _readme(family: Family, date_code: str, n_files: int) -> str:
    return (
        f"{family.title} — complete series kit\n"
        f"Build date: {date_code}\n\n"
        f"{family.tagline}\n\n"
        f"{n_files} Microsoft Word documents, grouped into folders that mirror the\n"
        "published site. A master index of every folder and file is in INDEX.md.\n\n"
        "Every page is also browsable on the site with its own Word download button;\n"
        "this kit is the whole family in one file.\n\n"
        "Rebuilt from source on every site deploy — no fixed SHA-256 is published.\n"
    )


def _index_md(family: Family, members: dict[str, Path], date_code: str) -> str:
    """Render the kit's master index — the zip-root INDEX.md.

    Groups the archive members under their folder heading so a reader can
    navigate the kit from the root instead of spelunking directories.
    """
    lines = [
        f"# {family.title} — kit index",
        "",
        f"Build date: {date_code}. Scope notes: README.txt.",
        "",
    ]
    for group in family.groups:
        prefix = f"{group.folder}/"
        entries = sorted(arc for arc in members if arc.startswith(prefix))
        if not entries:
            continue
        lines += [f"## {group.folder.replace('/', ' / ').replace('_', ' ')}", ""]
        if group.blurb:
            lines += [group.blurb, ""]
        lines += [f"- `{arc}`" for arc in entries]
        lines.append("")
    return "\n".join(lines)


def build_one(site_root: Path, out_dir: Path, family: Family, date_code: str) -> int:
    members, notes = collect(site_root, family)
    print(f"{family.title} kit — build inputs")
    print("=" * 60)
    for n in notes:
        print(" ", n)

    if not members:
        print(f"\nFATAL: no Word documents collected for {family.key} — refusing to ship an empty kit.")
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / family.zip_name
    readme = _readme(family, date_code, len(members))
    index_md = _index_md(family, members, date_code)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("README.txt", readme)
        z.writestr("INDEX.md", index_md)
        for arc, src in sorted(members.items()):
            z.write(src, arc)

    size_mb = zip_path.stat().st_size / 1_048_576
    print(f"\nWrote {zip_path}  ({len(members)} files, {size_mb:.1f} MB)")
    return 0


def build(site_root: Path, out_dir: Path, keys: list[str], date_code: str) -> int:
    rc = 0
    for i, key in enumerate(keys):
        if i:
            print()
        rc |= build_one(site_root, out_dir, FAMILIES[key], date_code)
    return rc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--family",
        default="all",
        choices=[*FAMILIES, "all"],
        help="which family kit to build (default: all)",
    )
    ap.add_argument("--site-root", type=Path, required=True, help="rendered _site root")
    ap.add_argument(
        "--src-root",
        type=Path,
        required=False,
        help="repo source root (unused — kept for CLI symmetry with build_orgcomp_download.py)",
    )
    ap.add_argument("--out", type=Path, required=True, help="output dir for the zip(s)")
    # Date passed in (never derived here): the caller stamps a deterministic value.
    ap.add_argument("--date-code", default="unknown", help="build date label for the README")
    args = ap.parse_args(argv)

    keys = list(FAMILIES) if args.family == "all" else [args.family]
    return build(args.site_root, args.out, keys, args.date_code)


if __name__ == "__main__":
    sys.exit(main())
