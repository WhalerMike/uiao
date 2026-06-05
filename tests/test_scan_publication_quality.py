"""Unit tests for scripts/scan_publication_quality.py.

Covers the publish_to_site suppression path added for issue #639: a page
declared `publish_to_site: false` is off the published surface and must clear
both gates, while a still-published reserved+stub page must still be flagged.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "scan_publication_quality",
    _REPO_ROOT / "scripts" / "scan_publication_quality.py",
)
spq = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = spq
_SPEC.loader.exec_module(spq)


@pytest.fixture(autouse=True)
def _root_at_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """evaluate() reports paths relative to REPO_ROOT; point it at the fixture
    tree so tmp_path .qmd files resolve."""
    monkeypatch.setattr(spq, "REPO_ROOT", tmp_path)


_STUB_BODY = "\n# Title\n\n## Scaffold — awaiting authored content\n\n_TODO — Author an overview of the adapter._\n"


def _write(tmp_path: Path, frontmatter: str, body: str = _STUB_BODY) -> Path:
    p = tmp_path / "doc.qmd"
    p.write_text(f"---\n{frontmatter}\n---\n{body}", encoding="utf-8")
    return p


def test_reserved_stub_without_flag_is_a_defect(tmp_path: Path) -> None:
    """The baseline Gate A case: reserved + stub body, still published."""
    p = _write(tmp_path, "status: reserved")
    finding = spq.evaluate(p)
    assert finding.gate_a_stub is True
    assert finding.is_defect is True


def test_publish_to_site_false_clears_the_finding(tmp_path: Path) -> None:
    """publish_to_site: false suppresses an otherwise-flagged reserved stub."""
    p = _write(tmp_path, "status: reserved\npublish_to_site: false")
    finding = spq.evaluate(p)
    assert finding.gate_a_stub is False
    assert finding.is_defect is False


def test_publish_to_site_string_false_clears_the_finding(tmp_path: Path) -> None:
    """A quoted/string false value is also honoured."""
    p = _write(tmp_path, 'status: reserved\npublish_to_site: "false"')
    assert spq.evaluate(p).is_defect is False


def test_publish_to_site_true_does_not_suppress(tmp_path: Path) -> None:
    """An explicit true must NOT hide a real defect."""
    p = _write(tmp_path, "status: reserved\npublish_to_site: true")
    assert spq.evaluate(p).is_defect is True


def test_unpublished_also_clears_gate_b(tmp_path: Path) -> None:
    """Drafting prose on an off-surface page is out of scope too."""
    body = "\n# Title\n\nLet me reflect it back to you.\n"
    p = _write(tmp_path, "status: active\npublish_to_site: false", body=body)
    finding = spq.evaluate(p)
    assert finding.gate_b_drafting is False
    assert finding.is_defect is False


def test_is_unpublished_helper() -> None:
    assert spq._is_unpublished({"publish_to_site": False}) is True
    assert spq._is_unpublished({"publish_to_site": "off"}) is True
    assert spq._is_unpublished({"publish_to_site": True}) is False
    assert spq._is_unpublished({}) is False
