"""Tests for data/control-library/ YAML files."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

CONTROL_LIBRARY_DIR = Path(__file__).resolve().parent.parent / "data" / "control-library"

IA2_PATH = CONTROL_LIBRARY_DIR / "IA-2.yml"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# IA-2.yml existence and structure
# ---------------------------------------------------------------------------

def test_ia2_file_exists():
    assert IA2_PATH.exists(), f"Expected {IA2_PATH} to exist"


def test_ia2_yaml_is_valid():
    data = load_yaml(IA2_PATH)
    assert isinstance(data, dict)


def test_ia2_required_fields():
    data = load_yaml(IA2_PATH)
    assert data.get("control_id") == "IA-2"
    assert data.get("title") == "Identification and Authentication (Organizational Users)"
    assert data.get("status") == "implemented"
    assert "narrative" in data
    assert "implemented_by" in data
    assert "evidence" in data


def test_ia2_implemented_by_contains_abstract_types():
    data = load_yaml(IA2_PATH)
    implemented_by = data.get("implemented_by", [])
    assert "IdentityProvider" in implemented_by
    assert "PIVAuthenticationService" in implemented_by


def test_ia2_evidence_contains_mfa_enrollment_report():
    data = load_yaml(IA2_PATH)
    evidence = data.get("evidence", [])
    assert "mfa-enrollment-report" in evidence


def test_ia2_narrative_references_mfa():
    data = load_yaml(IA2_PATH)
    narrative = data.get("narrative", "")
    assert "MFA" in narrative or "multi-factor" in narrative.lower()


def test_ia2_narrative_references_piv_cac():
    data = load_yaml(IA2_PATH)
    narrative = data.get("narrative", "")
    assert "PIV" in narrative
    assert "CAC" in narrative


def test_ia2_jinja2_template_variables():
    """Narrative must contain Jinja2 template variables for organization.name
    and parameters.mfa-requirement."""
    data = load_yaml(IA2_PATH)
    narrative = data.get("narrative", "")
    assert "{{ organization.name }}" in narrative
    assert "{{ parameters.mfa-requirement }}" in narrative
