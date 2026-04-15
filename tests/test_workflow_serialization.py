"""Workflow serialization tests.

The ``Validate Workflow Serialization`` workflow runs this file on every
PR that touches ``.github/workflows/**``. The goal is a fast syntactic
gate: every workflow YAML must parse cleanly, define at minimum a ``name``
and a ``jobs:`` block, and declare at least one trigger in ``on:``.

Implementation is intentionally minimal — GitHub's action parser is the
canonical schema authority; this test only catches the class of mistakes
that silently break a workflow without surfacing until the next
``workflow_run`` event.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"


def _workflow_files() -> list[Path]:
    if not WORKFLOWS_DIR.is_dir():
        return []
    return sorted(
        p for p in WORKFLOWS_DIR.iterdir()
        if p.is_file() and p.suffix in (".yml", ".yaml")
    )


@pytest.mark.parametrize("workflow_path", _workflow_files(), ids=lambda p: p.name)
def test_workflow_parses(workflow_path: Path) -> None:
    """Every workflow YAML file must parse without error."""
    text = workflow_path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    assert data is not None, f"{workflow_path.name}: YAML parsed to None"
    assert isinstance(data, dict), f"{workflow_path.name}: top level is not a mapping"


@pytest.mark.parametrize("workflow_path", _workflow_files(), ids=lambda p: p.name)
def test_workflow_has_required_keys(workflow_path: Path) -> None:
    """Every workflow must declare name, on, and jobs.

    PyYAML parses the bareword ``on`` as boolean ``True`` unless quoted, so
    accept either key form to stay compatible with hand-written workflows.
    """
    data = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    assert "name" in data, f"{workflow_path.name}: missing top-level 'name'"
    assert "jobs" in data and isinstance(data["jobs"], dict) and data["jobs"], (
        f"{workflow_path.name}: missing or empty 'jobs' block"
    )
    assert "on" in data or True in data, (
        f"{workflow_path.name}: missing 'on' trigger block"
    )


def test_workflows_directory_not_empty() -> None:
    """Sanity check: we expect at least one workflow to exist."""
    files = _workflow_files()
    assert files, f"no workflow files found under {WORKFLOWS_DIR}"
