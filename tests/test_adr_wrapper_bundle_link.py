"""Tests for the ADR index's bundle link and wrapper freshness (issues #1429/#1430).

PR #1421 moved section .docx bundles to GitHub Releases by hand-editing the
generated pages but not the generator, so re-running the generator reverted it.
These tests pin both halves: the generator emits the Release URL, and it derives
the tag from the workflow that publishes it rather than keeping a second copy.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"

_SPEC = importlib.util.spec_from_file_location(
    "generate_adr_qmd_wrappers", SCRIPTS_DIR / "generate_adr_qmd_wrappers.py"
)
gen = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(gen)

ADR_INDEX = REPO_ROOT / "docs" / "adr" / "adr-index.qmd"


def test_release_tag_is_read_from_the_deploy_workflow() -> None:
    """Not a second hardcoded copy — that divergence is what caused #1429."""
    workflow = (REPO_ROOT / ".github" / "workflows" / "quarto.yml").read_text(encoding="utf-8")
    assert f'DOWNLOADS_RELEASE_TAG: "{gen.downloads_release_tag()}"' in workflow


def test_bundle_url_is_absolute_and_points_at_releases() -> None:
    url = gen.bundle_url("adr-bundle.docx")
    assert url.startswith("https://github.com/WhalerMike/uiao/releases/download/")
    assert url.endswith("/adr-bundle.docx")


def test_committed_index_uses_the_release_url_not_a_local_path() -> None:
    """The exact regression: a relative bundle link means #1421 was reverted."""
    text = ADR_INDEX.read_text(encoding="utf-8")
    assert "](adr-bundle.docx)" not in text, "adr-index.qmd reverted to the local bundle path"
    assert gen.bundle_url("adr-bundle.docx") in text


def test_every_published_adr_has_a_committed_wrapper() -> None:
    """#1430: an ACCEPTED ADR with publish_to_site: true but no wrapper page."""
    adr_dir = REPO_ROOT / "src" / "uiao" / "canon" / "adr"
    missing = []
    for source in sorted(adr_dir.glob("adr-[0-9][0-9][0-9]-*.md")):
        text = source.read_text(encoding="utf-8", errors="replace")
        head = text.split("---", 2)[1] if text.startswith("---") else ""
        if "publish_to_site: true" not in head:
            continue
        if not (REPO_ROOT / "docs" / "adr" / f"{source.stem}.qmd").exists():
            missing.append(source.name)
    assert missing == [], f"published ADRs with no wrapper page: {missing}"


def test_regenerating_is_a_no_op() -> None:
    """For a generated artifact, regenerating on a clean tree must change nothing."""
    subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "generate_adr_qmd_wrappers.py")],
        cwd=REPO_ROOT,
        capture_output=True,
        timeout=300,
        check=True,
    )
    diff = subprocess.run(
        ["git", "diff", "--exit-code", "--", "docs/adr", "tools/publication-gaps/adr-sidebar-snippet.yaml"],
        cwd=REPO_ROOT,
        capture_output=True,
        timeout=120,
    )
    assert diff.returncode == 0, (
        "regenerating changed committed files — generator and output disagree:\n"
        + diff.stdout.decode("utf-8", "replace")[:2000]
    )
