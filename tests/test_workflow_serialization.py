"""Tests for GitHub Actions workflow YAML serialization.

Validates that every workflow file in .github/workflows/ can be
round-tripped through PyYAML without data loss or parse errors.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


WORKFLOWS_DIR = Path(__file__).resolve().parent.parent / ".github" / "workflows"


def _workflow_files() -> list[Path]:
    """Return all YAML files in .github/workflows/."""
    return sorted(WORKFLOWS_DIR.glob("*.yml")) + sorted(WORKFLOWS_DIR.glob("*.yaml"))


@pytest.mark.parametrize("workflow_path", _workflow_files(), ids=lambda p: p.name)
def test_workflow_yaml_parses(workflow_path: Path) -> None:
    """Each workflow file must parse as valid YAML without errors."""
    text = workflow_path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    assert data is not None, f"{workflow_path.name} parsed to None (empty file?)"
    assert isinstance(data, dict), f"{workflow_path.name} top-level must be a mapping"


@pytest.mark.parametrize("workflow_path", _workflow_files(), ids=lambda p: p.name)
def test_workflow_yaml_round_trips(workflow_path: Path) -> None:
    """Each workflow file must survive a serialize → deserialize round-trip."""
    text = workflow_path.read_text(encoding="utf-8")
    original = yaml.safe_load(text)
    serialized = yaml.dump(original, default_flow_style=False, allow_unicode=True)
    restored = yaml.safe_load(serialized)
    assert original == restored, (
        f"{workflow_path.name}: round-trip produced different data\n"
        f"  original keys: {list(original.keys()) if isinstance(original, dict) else original}\n"
        f"  restored keys: {list(restored.keys()) if isinstance(restored, dict) else restored}"
    )


@pytest.mark.parametrize("workflow_path", _workflow_files(), ids=lambda p: p.name)
def test_workflow_has_required_keys(workflow_path: Path) -> None:
    """Each workflow must contain at least 'on' (trigger) and 'jobs' keys.

    Note: PyYAML parses the YAML bare word ``on`` as the Python boolean
    ``True``, so both ``True`` and the string ``'on'`` are checked.
    """
    text = workflow_path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    assert isinstance(data, dict), f"{workflow_path.name} must be a YAML mapping"

    # "on" is a YAML boolean (True) when parsed by PyYAML
    has_trigger = True in data or "on" in data
    assert has_trigger, f"{workflow_path.name} is missing required 'on' (trigger) key"
    assert "jobs" in data, f"{workflow_path.name} is missing required 'jobs' key"
