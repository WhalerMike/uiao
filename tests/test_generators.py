"""End-to-end tests for migrated generators (ADR-0003).

Verifies that all generator modules can be imported and that their
core builder functions work with minimal/empty context data.
"""
import json
import pytest
from pathlib import Path


class TestGeneratorImports:
    """Verify all generator modules import cleanly."""

    def test_import_ssp(self):
        from uiao_core.generators import ssp
        assert hasattr(ssp, "build_ssp")
        assert hasattr(ssp, "load_context")
        assert hasattr(ssp, "build_set_parameters")

    def test_import_oscal(self):
        from uiao_core.generators import oscal
        assert hasattr(oscal, "build_oscal")
        assert hasattr(oscal, "build_component_definition")
        assert hasattr(oscal, "load_context")

    def test_import_poam(self):
        from uiao_core.generators import poam
        assert hasattr(poam, "build_poam_export")
        assert hasattr(poam, "build_poam")
        assert hasattr(poam, "detect_gaps")

    def test_import_docs(self):
        from uiao_core.generators import docs
        assert hasattr(docs, "build_docs")
        assert hasattr(docs, "load_canon")
        assert hasattr(docs, "load_data_files")

    def test_import_package_init(self):
        from uiao_core.generators import (
            build_ssp,
            build_oscal,
            build_poam_export,
            build_docs,
        )
        assert callable(build_ssp)
        assert callable(build_oscal)
        assert callable(build_poam_export)
        assert callable(build_docs)


class TestOSCALBuilder:
    """Test OSCAL component-definition builder with empty context."""

    def test_build_component_definition_empty(self):
        from uiao_core.generators.oscal import build_component_definition
        cd = build_component_definition({})
        assert "uuid" in cd
        assert "metadata" in cd
        assert "components" in cd
        assert isinstance(cd["components"], list)

    def test_build_component_definition_with_planes(self):
        from uiao_core.generators.oscal import build_component_definition
        context = {
            "control_planes": [
                {"id": "identity", "name": "Identity Plane", "description": "Test"},
            ],
            "unified_compliance_matrix": [],
        }
        cd = build_component_definition(context)
        assert len(cd["components"]) == 1
        assert cd["components"][0]["title"] == "Identity Plane"


class TestPOAMBuilder:
    """Test POA&M gap detection and builder."""

    def test_detect_gaps_empty(self):
        from uiao_core.generators.poam import detect_gaps
        gaps = detect_gaps({})
        assert isinstance(gaps, list)
        assert len(gaps) == 0

    def test_detect_gaps_low_maturity(self):
        from uiao_core.generators.poam import detect_gaps
        context = {
            "unified_compliance_matrix": [
                {"category": "Access Control", "cisa_maturity": "Initial", "nist_controls": ["AC-1"]},
            ],
        }
        gaps = detect_gaps(context)
        assert len(gaps) >= 1
        assert "Low maturity" in gaps[0]["title"]

    def test_build_poam_empty(self):
        from uiao_core.generators.poam import build_poam
        poam = build_poam({})
        assert "uuid" in poam
        assert "metadata" in poam
        assert "poam-items" in poam


class TestSSPBuilder:
    """Test SSP builder with empty context."""

    def test_build_ssp_empty_context(self, tmp_path):
        from uiao_core.generators.ssp import build_ssp
        output = tmp_path / "ssp.json"
        result = build_ssp(
            canon_path=tmp_path / "nonexistent.yaml",
            data_dir=tmp_path,
            output=output,
        )
        assert output.exists()
        with open(output) as f:
            data = json.load(f)
        assert "system-security-plan" in data
