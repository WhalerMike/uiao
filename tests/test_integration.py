"""Integration tests for Week 4 migrations.

Verifies that shared utils and migrated generators can be imported
and that their public APIs have the expected signatures.
"""

import inspect
from pathlib import Path

# ---------------------------------------------------------------------------
# Utils integration
# ---------------------------------------------------------------------------


def test_utils_context_imports():
    """Shared utils module exposes expected symbols."""
    from uiao_core.utils.context import get_settings, load_canon, load_context

    assert callable(get_settings)
    assert callable(load_context)
    assert callable(load_canon)


def test_utils_package_reexports():
    """uiao_core.utils re-exports context helpers."""
    from uiao_core.utils import get_settings

    assert callable(get_settings)


def test_get_settings_returns_settings():
    """get_settings returns a Settings instance without .env."""
    from uiao_core.utils.context import get_settings

    s = get_settings()
    assert hasattr(s, "canon_dir")
    assert hasattr(s, "data_dir")
    assert hasattr(s, "exports_dir")
    assert isinstance(s.canon_dir, Path)


def test_load_context_empty_dir(tmp_path):
    """load_context returns empty dict when data dir has no yml files."""
    from uiao_core.utils.context import load_context

    canon = tmp_path / "canon.yaml"
    canon.write_text("key: value\n")
    ctx = load_context(canon_path=canon, data_dir=tmp_path / "empty")
    assert isinstance(ctx, dict)
    assert ctx.get("key") == "value"


def test_load_context_merges_data(tmp_path):
    """load_context merges data YAML files into context."""
    from uiao_core.utils.context import load_context

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "alpha.yml").write_text("foo: bar\n")
    canon = tmp_path / "canon.yaml"
    canon.write_text("version: '1.0'\n")
    ctx = load_context(canon_path=canon, data_dir=data_dir)
    # load_context stores each data file under its stem key (nested)
    assert ctx["alpha"]["foo"] == "bar"
    assert ctx.get("version") == "1.0"


# ---------------------------------------------------------------------------
# Generator imports
# ---------------------------------------------------------------------------


def test_docs_generator_import():
    """docs.py exposes build_docs."""
    from uiao_core.generators.docs import build_docs

    assert callable(build_docs)


def test_oscal_generator_import():
    """oscal.py exposes build_oscal."""
    from uiao_core.generators.oscal import build_oscal

    assert callable(build_oscal)


def test_poam_generator_import():
    """poam.py exposes build_poam."""
    from uiao_core.generators.poam import build_poam

    assert callable(build_poam)


def test_charts_generator_import():
    """charts.py exposes build_charts."""
    from uiao_core.generators.charts import build_charts

    assert callable(build_charts)


def test_ssp_generator_import():
    """ssp.py exposes build_ssp."""
    from uiao_core.generators.ssp import build_ssp

    assert callable(build_ssp)


def test_rich_docx_generator_import():
    """rich_docx.py exposes build_rich_docx."""
    from uiao_core.generators.rich_docx import build_rich_docx

    assert callable(build_rich_docx)
    sig = inspect.signature(build_rich_docx)
    assert "canon_path" in sig.parameters
    assert "exports_dir" in sig.parameters


def test_trestle_generator_import():
    """trestle.py exposes assemble_ssp."""
    from uiao_core.generators.trestle import assemble_ssp

    assert callable(assemble_ssp)
    sig = inspect.signature(assemble_ssp)
    assert "ssp_skeleton" in sig.parameters
    assert "output_path" in sig.parameters
