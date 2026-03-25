"""Tests for data/control-library/ YAML files."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

CONTROL_LIBRARY_DIR = Path(__file__).resolve().parent.parent / "data" / "control-library"
SC8_PATH = CONTROL_LIBRARY_DIR / "SC-8.yml"
IA2_PATH = CONTROL_LIBRARY_DIR / "IA-2.yml"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# SC-8.yml tests
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def sc8() -> dict:
    return yaml.safe_load(SC8_PATH.read_text())


class TestSC8FileExists:
    def test_file_exists(self):
        assert SC8_PATH.exists(), "data/control-library/SC-8.yml must exist"

    def test_is_valid_yaml(self, sc8):
        assert isinstance(sc8, dict)


class TestSC8RequiredFields:
    def test_control_id(self, sc8):
        assert sc8["control_id"] == "SC-8"

    def test_title(self, sc8):
        assert sc8["title"] == "Transmission Confidentiality and Integrity"

    def test_status_implemented(self, sc8):
        assert sc8["status"] == "implemented"

    def test_narrative_present(self, sc8):
        assert "narrative" in sc8
        assert len(sc8["narrative"]) > 0


class TestSC8Narrative:
    def test_narrative_references_tls(self, sc8):
        narrative = sc8["narrative"].lower()
        assert "tls" in narrative

    def test_narrative_references_fips_140_2(self, sc8):
        narrative = sc8["narrative"]
        assert "FIPS 140-2" in narrative

    def test_narrative_references_tls_12(self, sc8):
        narrative = sc8["narrative"]
        assert "TLS 1.2" in narrative

    def test_narrative_has_jinja2_org_name(self, sc8):
        narrative = sc8["narrative"]
        assert "{{ organization.name }}" in narrative


class TestSC8ImplementedBy:
    def test_implemented_by_present(self, sc8):
        assert "implemented-by" in sc8
        assert isinstance(sc8["implemented-by"], list)
        assert len(sc8["implemented-by"]) >= 2

    def test_tls_termination_layer_present(self, sc8):
        types = [entry["type"] for entry in sc8["implemented-by"]]
        assert "TLSTerminationLayer" in types

    def test_api_gateway_present(self, sc8):
        types = [entry["type"] for entry in sc8["implemented-by"]]
        assert "APIGateway" in types

    def test_each_entry_has_description(self, sc8):
        for entry in sc8["implemented-by"]:
            assert "description" in entry
            assert len(entry["description"]) > 0


class TestSC8Evidence:
    def test_evidence_present(self, sc8):
        assert "evidence" in sc8
        assert isinstance(sc8["evidence"], list)
        assert len(sc8["evidence"]) >= 1

    def test_tls_compliance_scan_artifact(self, sc8):
        artifacts = [e["artifact"] for e in sc8["evidence"]]
        assert "tls-compliance-scan" in artifacts


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
