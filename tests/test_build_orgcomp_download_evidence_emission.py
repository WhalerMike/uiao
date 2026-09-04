"""Tests for the evidence-emission collector in scripts/build_orgcomp_download.py.

Scoped deliberately. That script had no test file; this one covers the section
it gained rather than retro-fitting coverage for the whole builder, and it
covers the two ways that collector can fail quietly:

* it sweeps a directory *outside* the series tree, so a rename there is not
  caught by anything the series collectors assert;
* it is one half of a split whose other half lives in
  build_org_family_download.py, which excludes the same directory from the
  OrgMod kit. The cross-script agreement itself is asserted in
  tests/test_build_org_family_download.py, beside the exclusion.
"""

import importlib.util
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "build_orgcomp_download",
    _REPO / "scripts" / "build_orgcomp_download.py",
)
bocd = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = bocd
_SPEC.loader.exec_module(bocd)


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"PK\x03\x04 fake docx")


def _site_with_emission(tmp_path: Path) -> Path:
    site = tmp_path / "_site"
    emission = site / bocd.EVIDENCE_EMISSION_SITE_REL
    for name in ("index", "01-entra-id", "02-azure-platform", "03-m365-unified-audit", "04-compliance-crosswalk"):
        _touch(emission / f"{name}.docx")
    # The section bundle the bundler writes beside the pages.
    _touch(emission / "siem-telemetry-emission-bundle.docx")
    return site


def test_the_declared_section_exists_in_the_repo_with_sources() -> None:
    # Closed-world against the real tree: the collector sweeps a path outside
    # the series, so a renamed section would empty the folder in the real
    # deploy while every fake-site test below still passed.
    src = _REPO / "docs" / bocd.EVIDENCE_EMISSION_SITE_REL
    assert src.is_dir(), f"no such section: {bocd.EVIDENCE_EMISSION_SITE_REL}"
    qmds = list(src.rglob("*.qmd"))
    assert len(qmds) >= bocd.EVIDENCE_EMISSION_MIN, (
        f"{bocd.EVIDENCE_EMISSION_SITE_REL} holds {len(qmds)} .qmd but the collector expects "
        f"at least {bocd.EVIDENCE_EMISSION_MIN}"
    )


def test_collect_takes_the_pages_and_not_the_section_bundle(tmp_path: Path) -> None:
    site = _site_with_emission(tmp_path)
    members, notes = bocd.collect(site, tmp_path / "src")

    emitted = {a for a in members if a.startswith(f"{bocd.EVIDENCE_EMISSION_FOLDER}/")}
    assert emitted == {
        f"{bocd.EVIDENCE_EMISSION_FOLDER}/index.docx",
        f"{bocd.EVIDENCE_EMISSION_FOLDER}/01-entra-id.docx",
        f"{bocd.EVIDENCE_EMISSION_FOLDER}/02-azure-platform.docx",
        f"{bocd.EVIDENCE_EMISSION_FOLDER}/03-m365-unified-audit.docx",
        f"{bocd.EVIDENCE_EMISSION_FOLDER}/04-compliance-crosswalk.docx",
    }
    # A page and a concatenation of that page must never both ship.
    assert not any(a.lower().endswith("-bundle.docx") for a in emitted)
    assert any("evidence-emission .docx" in n for n in notes)


def test_a_renamed_section_reports_a_gap_instead_of_shipping_quietly(tmp_path: Path) -> None:
    site = _site_with_emission(tmp_path)
    emission = site / bocd.EVIDENCE_EMISSION_SITE_REL
    emission.rename(emission.parent / "siem-telemetry-emission-renamed")

    members, notes = bocd.collect(site, tmp_path / "src")

    assert not any(a.startswith(f"{bocd.EVIDENCE_EMISSION_FOLDER}/") for a in members)
    assert any("MISSING" in n and bocd.EVIDENCE_EMISSION_SITE_REL in n for n in notes)


def test_a_short_section_warns(tmp_path: Path) -> None:
    site = tmp_path / "_site"
    _touch(site / bocd.EVIDENCE_EMISSION_SITE_REL / "index.docx")

    _, notes = bocd.collect(site, tmp_path / "src")

    assert any("WARNING" in n and "evidence-emission" in n for n in notes)
