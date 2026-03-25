"""Tests for data/control-library/SC-8.yml."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

CONTROL_LIBRARY_DIR = Path(__file__).parent.parent / "data" / "control-library"
SC8_PATH = CONTROL_LIBRARY_DIR / "SC-8.yml"


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
