"""Tests for scripts/generate_substrate_status_table.py.

Smoke tests that exercise the regenerator end-to-end against the live
canon. The script's value proposition is "every registered document
appears in the rendered status surface," so the tests assert that
property directly: load the registry, run the script, count rows.

Two failure-mode tests cover the pieces most likely to drift silently:
malformed frontmatter (non-mapping body) and missing artifacts (a
registered path that no longer exists).
"""

from __future__ import annotations

import importlib.util
import io
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "generate_substrate_status_table.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("gss_table", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gss_table"] = mod  # required for @dataclass to find the module
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def gss():
    return _load_module()


def test_collect_entries_covers_every_registered_document(gss):
    """Every UIAO_NNN entry in the registry produces a DocEntry in the
    output. Fails if the registry grows but the script silently drops
    rows."""
    entries = gss.collect_entries()
    registry_ids = {raw["id"] for raw in gss.load_registry()}
    emitted_ids = {e.uiao_id for e in entries}
    assert emitted_ids == registry_ids


def test_render_includes_every_uiao_id(gss):
    """The rendered Markdown contains a row for every registered ID."""
    entries = gss.collect_entries()
    rendered = gss.render(entries)
    for e in entries:
        assert e.uiao_id in rendered, f"missing row for {e.uiao_id}"


def test_render_groups_by_canonical_range(gss):
    """The rendered output uses the canonical range buckets per UIAO_001
    doctrine. Catches accidental loss of a bucket."""
    entries = gss.collect_entries()
    rendered = gss.render(entries)
    # We have at least one document in the SSOT, top-level, subsystem,
    # and operational ranges today; assert each section header appears.
    assert "UIAO_001 — SSOT" in rendered
    assert "UIAO_002–099 — Top-level canon" in rendered
    assert "UIAO_100–199 — Subsystem specs" in rendered
    assert "UIAO_200–299 — Operational/runtime" in rendered


def test_parse_frontmatter_handles_yaml_metadata_block(gss, tmp_path):
    """The UIAO_200/201/202 convention stores metadata under a
    top-level `metadata:` key in a YAML body, not as Markdown
    frontmatter. The parser must extract that block correctly."""
    sample = tmp_path / "sample.yaml"
    sample.write_text(
        "metadata:\n  title: Sample\n  status: Current\n  version: '1.0'\n",
        encoding="utf-8",
    )
    fm, err = gss.parse_frontmatter(sample)
    assert err is None
    assert fm == {"title": "Sample", "status": "Current", "version": "1.0"}


def test_parse_frontmatter_handles_markdown_block(gss, tmp_path):
    sample = tmp_path / "sample.md"
    sample.write_text(
        "---\ntitle: Sample\nstatus: Draft\n---\n\nbody\n",
        encoding="utf-8",
    )
    fm, err = gss.parse_frontmatter(sample)
    assert err is None
    assert fm == {"title": "Sample", "status": "Draft"}


def test_parse_frontmatter_reports_non_mapping_body(gss, tmp_path):
    """A frontmatter body that parses but isn't a mapping (e.g. a bare
    string) is a soft canon-authoring mistake we want to surface, not
    silently swallow."""
    sample = tmp_path / "sample.md"
    sample.write_text("---\njust a string\n---\nbody\n", encoding="utf-8")
    fm, err = gss.parse_frontmatter(sample)
    assert fm is None
    assert err is not None and "not a mapping" in err
