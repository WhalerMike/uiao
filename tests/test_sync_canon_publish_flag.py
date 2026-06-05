"""Unit tests for sync_canon.py publish_to_site emission (issue #639).

A reserved/stub adapter scaffold must carry `publish_to_site: false` so it stays
off the customer surface; authored or active pages must not get the key.
"""

import importlib.util
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "sync_canon",
    _REPO_ROOT / "scripts" / "tools" / "sync_canon.py",
)
sc = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = sc
_SPEC.loader.exec_module(sc)


def _adapter(status: str) -> dict:
    return {
        "name": "Example Adapter",
        "id": "example",
        "class": "conformance",
        "mission-class": "telemetry",
        "status": status,
        "phase": "phase-planning",
        "gcc-boundary": "gcc-moderate",
        "_source_registry": "canon/adapter-registry.yaml",
    }


def test_body_is_stub_detects_scaffold_markers() -> None:
    assert sc.body_is_stub("## Scaffold — awaiting authored content") is True
    assert sc.body_is_stub("_TODO — Author an overview._") is True
    assert sc.body_is_stub("Fully authored, real content here.") is False


def test_scaffold_unpublished_tracks_prepublish_status() -> None:
    assert sc._scaffold_unpublished(_adapter("reserved")) is True
    assert sc._scaffold_unpublished(_adapter("draft")) is True
    assert sc._scaffold_unpublished(_adapter("active")) is False


def test_render_frontmatter_emits_publish_flag_when_unpublished() -> None:
    fm = sc.render_frontmatter(_adapter("reserved"), "avs", "Adapter Validation Suite", unpublished=True)
    assert "publish_to_site: false" in fm
    assert "aspirational: true" in fm


def test_render_frontmatter_omits_publish_flag_by_default() -> None:
    fm = sc.render_frontmatter(_adapter("active"), "ats", "Adapter Technical Specification")
    assert "publish_to_site" not in fm


def test_apply_publish_flag_preserves_other_keys() -> None:
    doc = "---\nstatus: reserved\nlifecycle: adopted\ntiers_adopted: [1]\n---\n\nbody stays\n"
    out = sc.apply_publish_flag(doc, unpublished=True)
    # Adds exactly one line, leaves every other line byte-for-byte intact.
    assert out == doc.replace("---\n\nbody", "publish_to_site: false\n---\n\nbody")
    assert "lifecycle: adopted" in out
    assert "tiers_adopted: [1]" in out


def test_apply_publish_flag_is_idempotent_and_removable() -> None:
    doc = "---\nstatus: reserved\npublish_to_site: false\n---\n\nbody\n"
    # Re-applying does not duplicate the line.
    assert sc.apply_publish_flag(doc, unpublished=True).count("publish_to_site") == 1
    # Removing strips it back out.
    assert "publish_to_site" not in sc.apply_publish_flag(doc, unpublished=False)
