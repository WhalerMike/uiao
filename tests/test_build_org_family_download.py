"""Unit tests for scripts/build_org_family_download.py.

Two halves, deliberately:

* Pure selection logic exercised end to end over a fake ``_site`` tree — no
  Quarto, no network — mirroring tests/test_build_orgcomp_markdown_download.py.
* A closed-world check that every ``site_rel`` in ``GROUPS`` names a real
  directory *in this repo* that actually holds ``.qmd`` sources. A fake-site
  test alone would happily pass while a renamed section silently emptied a
  group in the real deploy; the kit would then ship, look complete, and be
  short a whole folder. Only this second half catches that.
"""

import importlib.util
import re
import sys
import zipfile
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "build_org_family_download",
    _REPO / "scripts" / "build_org_family_download.py",
)
bofd = importlib.util.module_from_spec(_SPEC)
# Registered before exec: the module declares @dataclass, and dataclasses
# resolves a field's type through sys.modules[cls.__module__] — which is
# None, and raises, for a module loaded by spec but never registered.
sys.modules[_SPEC.name] = bofd
_SPEC.loader.exec_module(bofd)

_DOCS = _REPO / "docs" / bofd.DOCS_SITE_REL


# --------------------------------------------------------------------------
# The families as declared
# --------------------------------------------------------------------------


def test_both_families_are_declared_with_distinct_zip_names() -> None:
    assert set(bofd.FAMILIES) == {"orgpath", "orgmod"}
    names = [f.zip_name for f in bofd.FAMILIES.values()]
    assert len(set(names)) == len(names)
    for name in names:
        assert name.endswith("-latest.zip")


def test_every_group_declares_a_known_mode_and_a_blurb() -> None:
    for family in bofd.FAMILIES.values():
        assert family.groups, f"{family.key} declares no groups"
        for group in family.groups:
            assert group.mode in bofd.MODES, f"{family.key}/{group.folder}: bad mode {group.mode!r}"
            assert group.blurb, f"{family.key}/{group.folder}: no INDEX.md blurb"
            if group.mode == "files":
                assert group.only, f"{family.key}/{group.folder}: mode 'files' with no filenames"
            else:
                assert not group.only, f"{family.key}/{group.folder}: 'only' is meaningless in mode {group.mode!r}"


def test_group_folders_are_unique_within_a_family() -> None:
    for family in bofd.FAMILIES.values():
        folders = [g.folder for g in family.groups]
        assert len(set(folders)) == len(folders), f"{family.key}: duplicate archive folder"


# --------------------------------------------------------------------------
# Closed-world: the declared sections exist in the repo and carry sources
# --------------------------------------------------------------------------


def test_every_group_site_rel_exists_in_the_repo_with_qmd_sources() -> None:
    for family in bofd.FAMILIES.values():
        for group in family.groups:
            src = _DOCS / group.site_rel
            assert src.is_dir(), f"{family.key}/{group.folder}: no such section {group.site_rel}"
            qmds = list(src.rglob("*.qmd"))
            assert len(qmds) >= group.min_expected, (
                f"{family.key}/{group.folder}: {group.site_rel} holds {len(qmds)} .qmd "
                f"but the group expects at least {group.min_expected} documents"
            )


def test_files_mode_groups_name_real_pages() -> None:
    for family in bofd.FAMILIES.values():
        for group in family.groups:
            if group.mode != "files":
                continue
            for name in group.only:
                qmd = _DOCS / group.site_rel / Path(name).with_suffix(".qmd")
                assert qmd.is_file(), f"{family.key}/{group.folder}: no source page for {name}"


def test_excluded_subdirs_exist_so_the_exclusion_still_bites() -> None:
    # An exclusion that names a directory which no longer exists is a silent
    # no-op: the sub-section it was meant to keep out would start shipping in
    # both kits. Assert the directories are real.
    for family in bofd.FAMILIES.values():
        for group in family.groups:
            for name in group.exclude_dirs:
                assert (_DOCS / group.site_rel / name).is_dir(), (
                    f"{family.key}/{group.folder}: excluded dir {name} no longer exists"
                )


def test_orgpath_implementation_belongs_to_orgpath_only() -> None:
    # The one sub-section of OrgMod's operational home that is OrgPath's
    # (operational-guides/index.qmd states this outright). It must ship in the
    # OrgPath kit and be excluded from the OrgMod guides sweep.
    orgpath_sections = {g.site_rel for g in bofd.FAMILIES["orgpath"].groups}
    assert "operational-guides/orgpath-implementation" in orgpath_sections

    guides = next(g for g in bofd.FAMILIES["orgmod"].groups if g.site_rel == "operational-guides")
    assert "orgpath-implementation" in guides.exclude_dirs


def _orgmod_guides() -> object:
    return next(
        g for g in bofd.FAMILIES["orgmod"].groups if g.site_rel == "operational-guides" and g.folder == "Guides"
    )


def test_the_governance_subsections_moved_to_orgpath_and_left_orgmod() -> None:
    # The triage that split steady-state governance out of the modernization
    # kit. Both halves must read the same constant: an exclusion that drifts
    # from the inclusion ships a page twice, or drops it from both kits.
    gov = next(g for g in bofd.FAMILIES["orgpath"].groups if g.folder == "Governance_Operations")
    assert gov.include_dirs == bofd.ORGPATH_GOVERNANCE_OPS
    assert set(bofd.ORGPATH_GOVERNANCE_OPS) <= set(_orgmod_guides().exclude_dirs)

    for name in bofd.ORGPATH_GOVERNANCE_OPS:
        assert (_DOCS / "operational-guides" / name).is_dir(), f"{name} no longer exists — the split is a no-op"


def test_the_shared_operational_guides_tree_is_partitioned_not_sampled() -> None:
    # Closed world in both directions over the tree the two families share:
    # every page reaches exactly one kit. A one-way "nothing new leaked in"
    # check would pass while a whole sub-section silently stopped shipping.
    og = _DOCS / "operational-guides"
    on_disk = {q.relative_to(og).with_suffix("").as_posix() for q in og.rglob("*.qmd")}

    claimed: dict[str, list[str]] = {}
    for key, folder, prefix in (
        ("orgmod", "Guides", ""),
        ("orgmod", "Transformation_Narrative", bofd.ORGMOD_PROMOTED_DIR + "/"),
        ("orgpath", "Implementation", bofd.ORGPATH_IMPLEMENTATION_DIR + "/"),
        ("orgpath", "Governance_Operations", ""),
    ):
        group = next(g for g in bofd.FAMILIES[key].groups if g.folder == folder)
        src = _DOCS / group.site_rel
        for q in src.rglob("*.qmd"):
            rel = q.relative_to(src)
            if group.include_dirs and rel.parts[0] not in group.include_dirs:
                continue
            if rel.parts[0] in group.exclude_dirs:
                continue
            claimed.setdefault(prefix + rel.with_suffix("").as_posix(), []).append(f"{key}/{folder}")

    assert not sorted(on_disk - set(claimed)), "pages that reach neither kit"
    assert not sorted(set(claimed) - on_disk), "pages claimed by a kit that are not on disk"
    assert not sorted(k for k, v in claimed.items() if len(v) > 1), "pages shipped by both kits"


def test_orgmod_whitepapers_are_the_reading_guides_modernization_tracks() -> None:
    # The whitepaper section serves all four pillars, so the OrgMod selection
    # is editorial unless it tracks something published. It tracks
    # reading-guide.qmd: every paper named here must still be linked from that
    # guide, so a renamed or retired paper fails here rather than vanishing
    # from the kit at deploy time.
    guide = (_DOCS / "whitepapers" / "reading-guide.qmd").read_text(encoding="utf-8")
    for name in bofd.ORGMOD_WHITEPAPERS:
        slug = Path(name).stem
        assert f"({slug}.qmd)" in guide, f"{slug} is in the OrgMod kit but no longer in the reading guide"

    # Papers whose tracks are explicitly not OrgMod's must stay out.
    for slug in ("orgpath-composability-matrix", "uiao-governance-os-whitepaper", "scubagear-integration-whitepaper"):
        assert f"{slug}.docx" not in bofd.ORGMOD_WHITEPAPERS, f"{slug} is not a modernization-track paper"

    wp = next(g for g in bofd.FAMILIES["orgmod"].groups if g.folder == "Whitepapers")
    assert len(set(wp.only)) == len(wp.only), "duplicate paper in the OrgMod whitepaper selection"


# --------------------------------------------------------------------------
# Selection over a fake _site
# --------------------------------------------------------------------------


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"PK\x03\x04 fake docx")


def _fake_site(tmp_path: Path) -> Path:
    site = tmp_path / "_site"
    docs = site / bofd.DOCS_SITE_REL

    # orgpath-narrative: chapters, per-book bundles, and the section bundle.
    narrative = docs / "orgpath-narrative"
    _touch(narrative / "Book_01.docx")
    _touch(narrative / "Book_01_CPT_01.docx")
    _touch(narrative / "Book_01-bundle.docx")
    _touch(narrative / "Book_02-bundle.docx")
    _touch(narrative / "orgpath-narrative-bundle.docx")

    # reference-architecture: flat pages plus its section bundle.
    ref = docs / "reference-architecture"
    _touch(ref / "orgtree.docx")
    _touch(ref / "locpath.docx")
    _touch(ref / "directory-migration.docx")
    _touch(ref / "adapters.docx")
    _touch(ref / "reference-architecture-bundle.docx")

    # operational-guides: the OrgMod home, with the two promoted/excluded subdirs.
    og = docs / "operational-guides"
    _touch(og / "pki-modernization.docx")
    _touch(og / "target-surface" / "intune-policy-templates.docx")
    _touch(og / "target-surface" / "target-surface-bundle.docx")
    _touch(og / "orgpath-implementation" / "01-prerequisites.docx")
    _touch(og / "client-server-to-hybrid-cloud" / "01-ad-governance-surface.docx")
    # The three governance sub-sections that are OrgPath's, not OrgMod's.
    _touch(og / "active-governance-directory" / "index.docx")
    _touch(og / "ai-identity-governance" / "governed-path.docx")
    _touch(og / "helpdesk-entra-operations" / "helpdesk-flow.docx")

    # whitepapers: a flat section the OrgMod kit takes named papers out of.
    wp = docs / "whitepapers"
    _touch(wp / bofd.ORGMOD_WHITEPAPERS[0])
    _touch(wp / "orgpath-composability-matrix.docx")

    _touch(docs / "orgpath-multicloud" / "01-the-substrate.docx")
    _touch(docs / "modernization-specs" / "identity" / "spec.docx")
    _touch(docs / "sql-server-narrative" / "Book_01-bundle.docx")
    _touch(docs / "sql-server-implementation" / "Book_01.docx")
    return site


def test_orgpath_collect_takes_book_bundles_and_pages_not_section_bundles(tmp_path: Path) -> None:
    members, _ = bofd.collect(_fake_site(tmp_path), bofd.FAMILIES["orgpath"])

    assert set(members) == {
        "Narrative/Book_01-bundle.docx",
        "Narrative/Book_02-bundle.docx",
        "Reference_Architecture/orgtree.docx",
        "Reference_Architecture/locpath.docx",
        "Reference_Architecture/directory-migration.docx",
        "Reference_Architecture/adapters.docx",
        "Implementation/01-prerequisites.docx",
        "Multi_Cloud/01-the-substrate.docx",
        "Governance_Operations/active-governance-directory/index.docx",
        "Governance_Operations/ai-identity-governance/governed-path.docx",
        "Governance_Operations/helpdesk-entra-operations/helpdesk-flow.docx",
    }
    # include_dirs takes only what it names: the rest of the shared
    # operational-guides tree must not leak into the OrgPath kit.
    assert not any(arc.startswith("Governance_Operations/pki-modernization") for arc in members)
    assert not any("target-surface" in arc for arc in members)


def test_orgmod_collect_excludes_orgpath_implementation_and_the_promoted_narrative(tmp_path: Path) -> None:
    members, _ = bofd.collect(_fake_site(tmp_path), bofd.FAMILIES["orgmod"])

    assert set(members) == {
        "Transformation_Narrative/01-ad-governance-surface.docx",
        "Guides/pki-modernization.docx",
        "Guides/target-surface/intune-policy-templates.docx",
        "Modernization_Specs/identity/spec.docx",
        "Directory_Migration_Bridge/directory-migration.docx",
        "Directory_Migration_Bridge/adapters.docx",
        f"Whitepapers/{bofd.ORGMOD_WHITEPAPERS[0]}",
        "SQL_Server_Transformation/Narrative/Book_01-bundle.docx",
        "SQL_Server_Transformation/Implementation/Book_01.docx",
    }
    # The OrgPath sub-section and the promoted narrative appear exactly once,
    # in their own homes — never swept a second time by the Guides group.
    assert not any(arc.startswith("Guides/orgpath-implementation/") for arc in members)
    assert not any(arc.startswith("Guides/client-server-to-hybrid-cloud/") for arc in members)
    # ...and the three governance sub-sections left the OrgMod kit entirely.
    for name in bofd.ORGPATH_GOVERNANCE_OPS:
        assert not any(arc.startswith(f"Guides/{name}/") for arc in members)
    # The whitepapers group is a named selection, never the whole section.
    assert "Whitepapers/orgpath-composability-matrix.docx" not in members


def test_collect_reports_a_gap_instead_of_shipping_quietly(tmp_path: Path) -> None:
    site = _fake_site(tmp_path)
    # Rename the multi-cloud section: the group must go empty AND say so.
    (site / bofd.DOCS_SITE_REL / "orgpath-multicloud").rename(site / bofd.DOCS_SITE_REL / "orgpath-multicloud-renamed")

    members, notes = bofd.collect(site, bofd.FAMILIES["orgpath"])

    assert not any(arc.startswith("Multi_Cloud/") for arc in members)
    assert any("MISSING" in n and "orgpath-multicloud" in n for n in notes)


def test_short_group_warns(tmp_path: Path) -> None:
    _, notes = bofd.collect(_fake_site(tmp_path), bofd.FAMILIES["orgpath"])
    # The fake site has 2 book bundles against a floor of 20.
    assert any("WARNING" in n for n in notes)


# --------------------------------------------------------------------------
# End-to-end build
# --------------------------------------------------------------------------


def test_build_writes_both_zips_with_readme_and_index(tmp_path: Path) -> None:
    site = _fake_site(tmp_path)
    out = tmp_path / "out"

    assert bofd.build(site, out, list(bofd.FAMILIES), "2026-09-02") == 0

    for family in bofd.FAMILIES.values():
        zip_path = out / family.zip_name
        assert zip_path.is_file()
        with zipfile.ZipFile(zip_path) as z:
            names = set(z.namelist())
            assert "README.txt" in names
            assert "INDEX.md" in names
            readme = z.read("README.txt").decode()
            index = z.read("INDEX.md").decode()
        assert "2026-09-02" in readme
        assert family.title in index
        # Every shipped file is listed in the index — a folder that reaches the
        # zip but not the index is a folder readers never find.
        for arc in names - {"README.txt", "INDEX.md"}:
            assert f"`{arc}`" in index


def test_build_refuses_an_empty_kit(tmp_path: Path) -> None:
    empty = tmp_path / "_site"
    (empty / bofd.DOCS_SITE_REL).mkdir(parents=True)

    assert bofd.build(empty, tmp_path / "out", ["orgpath"], "2026-09-02") == 1
    assert not (tmp_path / "out").exists()


def test_main_accepts_a_single_family(tmp_path: Path) -> None:
    site = _fake_site(tmp_path)
    out = tmp_path / "out"

    rc = bofd.main(
        [
            "--family",
            "orgmod",
            "--site-root",
            str(site),
            "--out",
            str(out),
            "--date-code",
            "2026-09-02",
        ]
    )

    assert rc == 0
    assert (out / bofd.FAMILIES["orgmod"].zip_name).is_file()
    assert not (out / bofd.FAMILIES["orgpath"].zip_name).exists()


# --------------------------------------------------------------------------
# Deploy wiring: the kits reach the Downloads page and the release
# --------------------------------------------------------------------------


def test_the_quarto_deploy_builds_both_kits_before_it_strips_the_bundles() -> None:
    # Ordering is the whole risk here. The builder reads per-book
    # Book_NN-bundle.docx written by "Build per-section .docx bundles" and is
    # read by "Publish download kits ..."; "Remove published download kits and
    # .docx bundles from the Pages artifact" deletes those bundles from _site.
    # Land the build step outside that window and the Narrative folders come
    # back empty in the real deploy while every unit test above still passes.
    workflow = (_REPO / ".github" / "workflows" / "quarto.yml").read_text(encoding="utf-8")
    steps = [
        "Build per-section .docx bundles",
        "Build OrgPath and OrgMod series download kits",
        "Publish download kits to GitHub Releases",
        "Remove published download kits and .docx bundles from the Pages artifact",
    ]
    positions = []
    for name in steps:
        needle = f"- name: {name}"
        assert needle in workflow, f"step missing from quarto.yml: {name}"
        positions.append(workflow.index(needle))
    assert positions == sorted(positions), "the kit build step is out of order in quarto.yml"

    # The workflow's path filter and the assemble job's sparse checkout must
    # both name the script: an unlisted path is simply not on disk there.
    assert "- 'scripts/build_org_family_download.py'" in workflow
    assert "            scripts/build_org_family_download.py" in workflow


def test_the_downloads_page_links_both_kits_by_their_real_asset_names() -> None:
    page = (_REPO / "docs" / "download" / "index.qmd").read_text(encoding="utf-8")
    for family in bofd.FAMILIES.values():
        assert f"https://github.com/WhalerMike/uiao/releases/download/downloads-latest/{family.zip_name}" in page, (
            f"{family.key}: the Downloads page does not link {family.zip_name}"
        )


def test_both_kit_links_are_checked_not_suppressed() -> None:
    # Inverted from the bootstrap guard this replaces. Both kits were linked
    # before they existed -- the release assets only appear on the first deploy
    # after the PR merges -- so .lycheeignore briefly carried a two-line, one-
    # file-per-line suppression to cover that window. The deploy on d7150c256
    # published both (2026-09-02, 37.1 MB / 116 MB), the links resolve, and the
    # suppression is gone.
    #
    # What stays is the assertion that it does not come back. The NOTE beside
    # those entries in .lycheeignore records why: a suppression there was added
    # for a real reason, silently outlived it, and went on to mask 11 genuinely
    # broken release links -- because GitHub rewrites spaces, commas and
    # ampersands in asset names, so a link can rot while the file exists. A kit
    # link that stops being checked is exactly how that repeats.
    base = "https://github.com/WhalerMike/uiao/releases/download/downloads-latest/"
    patterns = [
        re.compile(line.strip())
        for line in (_REPO / ".lycheeignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]

    for family in bofd.FAMILIES.values():
        url = base + family.zip_name
        masking = [p.pattern for p in patterns if p.search(url)]
        assert not masking, (
            f"{family.zip_name} is published and must stay link-checked, but .lycheeignore suppresses it via {masking}"
        )
