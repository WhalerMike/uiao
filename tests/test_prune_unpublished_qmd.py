"""Unit tests for scripts/prune_unpublished_qmd.py (issue #639 render prune)."""

import importlib.util
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "prune_unpublished_qmd",
    _REPO_ROOT / "scripts" / "prune_unpublished_qmd.py",
)
prune = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = prune
_SPEC.loader.exec_module(prune)


def _qmd(root: Path, name: str, frontmatter: str) -> Path:
    p = root / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"---\n{frontmatter}\n---\n\nbody\n", encoding="utf-8")
    return p


def test_is_unpublished_variants() -> None:
    assert prune.is_unpublished("---\npublish_to_site: false\n---\n") is True
    assert prune.is_unpublished('---\npublish_to_site: "no"\n---\n') is True
    assert prune.is_unpublished("---\npublish_to_site: true\n---\n") is False
    assert prune.is_unpublished("---\nstatus: reserved\n---\n") is False
    assert prune.is_unpublished("no frontmatter here") is False


def test_find_only_returns_unpublished(tmp_path: Path) -> None:
    _qmd(tmp_path, "keep/a.qmd", "status: active")
    _qmd(tmp_path, "keep/b.qmd", "status: reserved\npublish_to_site: true")
    drop = _qmd(tmp_path, "drop/c.qmd", "status: reserved\npublish_to_site: false")

    assert prune.find_unpublished(tmp_path) == [drop]


def test_main_deletes_unpublished_and_keeps_rest(tmp_path: Path) -> None:
    keep = _qmd(tmp_path, "keep/a.qmd", "status: active")
    drop = _qmd(tmp_path, "drop/c.qmd", "publish_to_site: false")

    rc = prune.main(["--root", str(tmp_path)])

    assert rc == 0
    assert keep.exists()
    assert not drop.exists()


def test_dry_run_deletes_nothing(tmp_path: Path) -> None:
    drop = _qmd(tmp_path, "drop/c.qmd", "publish_to_site: false")

    rc = prune.main(["--root", str(tmp_path), "--dry-run"])

    assert rc == 0
    assert drop.exists()
