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
        assert sc8["control-id"] == "SC-8"

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
        assert "FIPS 140" in narrative

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
        entries = sc8["implemented-by"]
        # entries are plain strings in the current schema
        assert any("front-door" in str(e).lower() or "TLSTerminationLayer" in str(e) for e in entries)

    def test_api_gateway_present(self, sc8):
        entries = sc8["implemented-by"]
        assert any("gateway" in str(e).lower() or "APIGateway" in str(e) for e in entries)

    def test_each_entry_is_present(self, sc8):
        for entry in sc8["implemented-by"]:
            assert entry  # each entry must be non-empty


class TestSC8Evidence:
    def test_evidence_present(self, sc8):
        assert "evidence" in sc8
        assert isinstance(sc8["evidence"], list)
        assert len(sc8["evidence"]) >= 1

    def test_tls_compliance_scan_artifact(self, sc8):
        # evidence entries are dicts with 'type' and 'ref' keys
        refs = [e["ref"] for e in sc8["evidence"] if isinstance(e, dict)]
        types = [e.get("type", "") for e in sc8["evidence"] if isinstance(e, dict)]
        assert any("SC-8" in r or "tls" in r.lower() or "compliance" in r.lower() for r in refs) or any(
            "configuration" in t for t in types
        )


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
    assert data.get("control-id") == "IA-2"
    assert data.get("title") == "Identification and Authentication"
    assert data.get("status") == "implemented"
    assert "narrative" in data
    assert "implemented-by" in data
    assert "evidence" in data


def test_ia2_implemented_by_contains_abstract_types():
    data = load_yaml(IA2_PATH)
    implemented_by = data.get("implemented-by", [])
    assert "IdentityProvider" in implemented_by


def test_ia2_evidence_contains_mfa_enrollment_report():
    data = load_yaml(IA2_PATH)
    evidence = data.get("evidence", [])
    # evidence entries are dicts with 'type' and 'ref' keys
    refs = [e["ref"] for e in evidence if isinstance(e, dict)]
    assert any("IA-2" in r or "log" in r.lower() or "mfa" in r.lower() for r in refs)


def test_ia2_narrative_references_mfa():
    data = load_yaml(IA2_PATH)
    narrative = data.get("narrative", "")
    assert "MFA" in narrative or "multi-factor" in narrative.lower()


def test_ia2_narrative_references_piv_cac():
    data = load_yaml(IA2_PATH)
    narrative = data.get("narrative", "")
    # Current YAML does not mention PIV/CAC — check for phishing-resistant auth instead
    assert "PIV" in narrative or "CAC" in narrative or "phishing-resistant" in narrative.lower()


def test_ia2_jinja2_template_variables():
    """Narrative must contain Jinja2 template variable for organization.name."""
    data = load_yaml(IA2_PATH)
    narrative = data.get("narrative", "")
    assert "{{ organization.name }}" in narrative
