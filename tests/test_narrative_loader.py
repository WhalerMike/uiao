"""Unit tests for src/uiao_core/generators/narrative_loader.py."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_yaml(path: Path, data: dict) -> None:
    """Write *data* as YAML to *path*, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.dump(data, fh, allow_unicode=True)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_load_empty_dir(tmp_path: Path) -> None:
    """Returns an empty dict when the control-library directory has no YAMLs."""
    from uiao_core.generators.narrative_loader import load_control_library

    control_lib = tmp_path / "control-library"
    control_lib.mkdir()

    result = load_control_library(data_dir=tmp_path, context={})
    assert result == {}


def test_load_renders_jinja2(tmp_path: Path) -> None:
    """{{ organization.name }} and {{ parameters['x'] }} are rendered correctly."""
    from uiao_core.generators.narrative_loader import load_control_library

    control_lib = tmp_path / "control-library"
    _write_yaml(
        control_lib / "XX-1.yml",
        {
            "control_id": "XX-1",
            "title": "Test Control",
            "status": "implemented",
            "implemented_by": ["ServiceA"],
            "evidence": ["artifact-a"],
            "parameters": [],
            "narrative": (
                "{{ organization.name }} enforces XX-1. "
                "Timeout is {{ parameters['session-timeout'] }}."
            ),
        },
    )

    # Provide a minimal context that supplies the values the template needs.
    context = {
        "leadership_briefing": {"organization": "Acme Corp"},
        "parameters": {
            "identity": [
                {"id": "session-timeout", "value": "30 minutes"},
            ],
        },
    }

    result = load_control_library(data_dir=tmp_path, context=context)

    assert "XX-1" in result
    narrative = result["XX-1"]["narrative"]
    assert "Acme Corp" in narrative
    assert "30 minutes" in narrative
    assert "{{" not in narrative


def test_load_handles_missing_vars(tmp_path: Path) -> None:
    """Missing Jinja2 variables render as [TBD], not a crash."""
    from uiao_core.generators.narrative_loader import load_control_library

    control_lib = tmp_path / "control-library"
    _write_yaml(
        control_lib / "XX-2.yml",
        {
            "control_id": "XX-2",
            "title": "Missing Vars Control",
            "status": "implemented",
            "implemented_by": ["ServiceB"],
            "evidence": [],
            "parameters": [],
            "narrative": (
                "Org: {{ organization.name }}, "
                "Param: {{ parameters['nonexistent-param'] }}, "
                "Unknown: {{ totally_unknown_var }}"
            ),
        },
    )

    # Empty context — no organization name, no parameters.
    result = load_control_library(data_dir=tmp_path, context={})

    assert "XX-2" in result
    narrative = result["XX-2"]["narrative"]
    # The rendered output must not contain raw Jinja2 delimiters.
    assert "{{" not in narrative
    # Missing variables must resolve to [TBD].
    assert "[TBD]" in narrative


def test_both_implemented_by_schemas(tmp_path: Path) -> None:
    """Both simple-string and typed-object implemented_by schemas are handled."""
    from uiao_core.generators.narrative_loader import (
        load_control_library,
        _normalise_implemented_by,
    )

    # Variant A: simple string list.
    string_list = ["IdentityProvider", "HRSystem"]
    normalised_a = _normalise_implemented_by(string_list)
    assert len(normalised_a) == 2
    assert normalised_a[0] == {"type": "IdentityProvider", "description": ""}
    assert normalised_a[1] == {"type": "HRSystem", "description": ""}

    # Variant B: typed-object list.
    object_list = [
        {"type": "NetworkOverlay", "description": "SD-WAN VRF segmentation"},
        {"type": "FirewallCluster", "description": "Stateful ingress/egress"},
    ]
    normalised_b = _normalise_implemented_by(object_list)
    assert len(normalised_b) == 2
    assert normalised_b[0]["type"] == "NetworkOverlay"
    assert normalised_b[0]["description"] == "SD-WAN VRF segmentation"
    assert normalised_b[1]["type"] == "FirewallCluster"

    # Verify load_control_library handles both schemas end-to-end.
    control_lib = tmp_path / "control-library"
    _write_yaml(
        control_lib / "STRING-1.yml",
        {
            "control_id": "STRING-1",
            "title": "String Schema",
            "status": "implemented",
            "implemented_by": string_list,
            "evidence": [],
            "parameters": [],
            "narrative": "Narrative for STRING-1.",
        },
    )
    _write_yaml(
        control_lib / "TYPED-1.yml",
        {
            "control_id": "TYPED-1",
            "title": "Typed Schema",
            "status": "implemented",
            "implemented_by": object_list,
            "evidence": [],
            "parameters": [],
            "narrative": "Narrative for TYPED-1.",
        },
    )

    result = load_control_library(data_dir=tmp_path, context={})

    assert "STRING-1" in result
    assert result["STRING-1"]["implemented_by"][0]["type"] == "IdentityProvider"

    assert "TYPED-1" in result
    assert result["TYPED-1"]["implemented_by"][1]["type"] == "FirewallCluster"
