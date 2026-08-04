"""Unit tests for scripts/build_orgcomp_markdown_download.py.

Covers the pure grouping/naming logic and an end-to-end build over a fake
``_site`` tree — no Quarto/network dependency, mirroring the style of
tests/test_bundle_section_docx.py.
"""

import importlib.util
import zipfile
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "build_orgcomp_markdown_download",
    Path(__file__).resolve().parents[1] / "scripts" / "build_orgcomp_markdown_download.py",
)
bomd = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(bomd)


def test_volume_bundle_filename_carries_theme() -> None:
    assert bomd._volume_bundle_filename("I") == "Vol_I-Foundation & Transport-Bundle.md"
    assert bomd._volume_bundle_filename("IX") == "Vol_IX-Day-2 Operations-Bundle.md"


def test_volume_bundle_filename_falls_back_without_theme() -> None:
    assert bomd._volume_bundle_filename("XI") == "Vol_XI-Bundle.md"


def test_every_ranked_volume_has_a_folder_and_theme() -> None:
    for vol_id in bomd._ROMAN_RANK:
        assert vol_id in bomd.VOL_FOLDER
        assert vol_id in bomd.VOLUME_THEMES


def test_collect_books_groups_by_volume_and_sorts(tmp_path: Path) -> None:
    series = tmp_path / "customer-documents" / "orgcomp-series"
    series.mkdir(parents=True)
    (series / "Vol_I_Book_02_Second.md").write_text("# Second\n")
    (series / "Vol_I_Book_00a_First.md").write_text("# First\n")
    (series / "Vol_IX_Book_01_Other.md").write_text("# Other\n")
    # Not a volume book page — must be ignored by the grouping regex.
    (series / "OrgComp_Day2_Kit_0_Start_Here.md").write_text("# Start Here\n")

    volumes = bomd.collect_books(series)

    assert set(volumes) == {"I", "IX"}
    assert [p.name for p in volumes["I"]] == ["Vol_I_Book_00a_First.md", "Vol_I_Book_02_Second.md"]


def test_build_produces_zip_with_book_pages_bundle_and_extras(tmp_path: Path) -> None:
    site_root = tmp_path / "_site"
    series = site_root / bomd.SERIES_SITE_REL
    series.mkdir(parents=True)
    (series / "Vol_0_Book_00a_Brief.md").write_text("# Brief\n\ncontent\n")
    (series / "OrgComp_Day2_Kit_0_Start_Here.md").write_text("# Start Here\n")

    out_dir = tmp_path / "out"
    rc = bomd.build(site_root, out_dir, "2026-08-04")
    assert rc == 0

    zip_path = out_dir / bomd.ZIP_NAME
    assert zip_path.is_file()
    with zipfile.ZipFile(zip_path) as z:
        names = set(z.namelist())
        assert "README.txt" in names
        assert "INDEX.md" in names
        assert "Vol_0_Executive_Summary/Vol_0_Book_00a_Brief.md" in names
        bundle_name = f"Vol_0_Executive_Summary/{bomd._volume_bundle_filename('0')}"
        assert bundle_name in names
        assert "content" in z.read(bundle_name).decode()
        assert "Runbooks_and_Kit_Docs/OrgComp_Day2_Kit_0_Start_Here.md" in names


def test_build_refuses_empty_kit(tmp_path: Path) -> None:
    site_root = tmp_path / "_site"
    (site_root / bomd.SERIES_SITE_REL).mkdir(parents=True)
    rc = bomd.build(site_root, tmp_path / "out", "2026-08-04")
    assert rc == 1
