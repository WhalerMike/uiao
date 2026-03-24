"""End-to-end tests for migrated generators (ADR-0003).

Verifies that all generator modules can be imported and that their
core builder functions work with minimal/empty context data.
"""

import json
from pathlib import Path

# Locate the repo root relative to this test file so paths are portable
_REPO_ROOT = Path(__file__).parent.parent
_TEMPLATE_PATH = _REPO_ROOT / "data" / "fedramp_ssp_template_structure.yaml"


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
            build_docs,
            build_oscal,
            build_poam_export,
            build_ssp,
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
        _result = build_ssp(
            canon_path=tmp_path / "nonexistent.yaml",
            data_dir=tmp_path,
            output=output,
        )
        assert output.exists()
        with open(output) as f:
            data = json.load(f)
        assert "system-security-plan" in data

    def test_build_ssp_output_path_alias(self, tmp_path):
        """Verify that the deprecated output_path kwarg still works."""
        from uiao_core.generators.ssp import build_ssp

        output = tmp_path / "ssp_alias.json"
        build_ssp(
            canon_path=tmp_path / "nonexistent.yaml",
            data_dir=tmp_path,
            output_path=output,
        )
        assert output.exists()

    def test_build_ssp_skeleton_required_top_level_keys(self, tmp_path):
        """SSP skeleton must contain all OSCAL top-level keys."""
        from uiao_core.generators.ssp import build_ssp_skeleton

        ssp = build_ssp_skeleton({}, data_dir=tmp_path)
        for key in (
            "uuid",
            "metadata",
            "import-profile",
            "system-characteristics",
            "system-implementation",
            "control-implementation",
        ):
            assert key in ssp, f"Missing required OSCAL key: {key}"

    def test_build_ssp_fedramp_rev5_metadata_props(self, tmp_path):
        """Metadata must carry fedramp-version=rev5 and impact-level=moderate when template is present."""
        import shutil

        from uiao_core.generators.ssp import build_ssp_skeleton

        # Copy real template into tmp_path so the generator can load it
        src = _TEMPLATE_PATH
        shutil.copy(src, tmp_path / "fedramp_ssp_template_structure.yaml")

        ssp = build_ssp_skeleton({}, data_dir=tmp_path)
        prop_names = {p["name"]: p["value"] for p in ssp["metadata"].get("props", [])}
        assert prop_names.get("fedramp-version") == "rev5"
        assert prop_names.get("impact-level") == "moderate"
        assert prop_names.get("authorization-type") == "fedramp-agency"

    def test_build_ssp_all_required_roles(self, tmp_path):
        """SSP metadata must include all FedRAMP Rev 5 required roles."""
        import shutil

        from uiao_core.generators.ssp import build_ssp_skeleton

        src = _TEMPLATE_PATH
        shutil.copy(src, tmp_path / "fedramp_ssp_template_structure.yaml")

        ssp = build_ssp_skeleton({}, data_dir=tmp_path)
        role_ids = {r["id"] for r in ssp["metadata"].get("roles", [])}
        required = {
            "system-owner",
            "authorizing-official",
            "information-system-security-officer",
            "system-poc-technical",
            "system-poc-management",
            "prepared-by",
        }
        assert required.issubset(role_ids), f"Missing roles: {required - role_ids}"

    def test_build_ssp_responsible_parties(self, tmp_path):
        """SSP metadata must include responsible-parties for key FedRAMP roles."""
        import shutil

        from uiao_core.generators.ssp import build_ssp_skeleton

        src = _TEMPLATE_PATH
        shutil.copy(src, tmp_path / "fedramp_ssp_template_structure.yaml")

        ssp = build_ssp_skeleton({}, data_dir=tmp_path)
        rp_role_ids = {rp["role-id"] for rp in ssp["metadata"].get("responsible-parties", [])}
        assert "system-owner" in rp_role_ids
        assert "authorizing-official" in rp_role_ids

    def test_build_ssp_system_characteristics_sections(self, tmp_path):
        """Section 7-10: system-characteristics must include status, props, network-architecture, data-flow."""
        import shutil

        from uiao_core.generators.ssp import build_ssp_skeleton

        src = _TEMPLATE_PATH
        shutil.copy(src, tmp_path / "fedramp_ssp_template_structure.yaml")

        ssp = build_ssp_skeleton({}, data_dir=tmp_path)
        sc = ssp["system-characteristics"]
        assert "status" in sc  # Section 7
        assert "props" in sc  # Section 8 (cloud model)
        assert "authorization-boundary" in sc  # Section 9
        assert "network-architecture" in sc  # Section 10
        assert "data-flow" in sc  # Section 10
        assert "system-information" in sc  # Section 2
        assert "security-impact-level" in sc  # Section 2

    def test_build_ssp_system_characteristics_cloud_props(self, tmp_path):
        """Section 8: system-characteristics props must include cloud-service-model and cloud-deployment-model."""
        import shutil

        from uiao_core.generators.ssp import build_ssp_skeleton

        src = _TEMPLATE_PATH
        shutil.copy(src, tmp_path / "fedramp_ssp_template_structure.yaml")

        ssp = build_ssp_skeleton({}, data_dir=tmp_path)
        prop_names = {p["name"] for p in ssp["system-characteristics"].get("props", [])}
        assert "cloud-service-model" in prop_names
        assert "cloud-deployment-model" in prop_names

    def test_build_ssp_back_matter_section12(self, tmp_path):
        """Section 12: SSP must contain back-matter with laws/regulations resources."""
        import shutil

        from uiao_core.generators.ssp import build_ssp_skeleton

        src = _TEMPLATE_PATH
        shutil.copy(src, tmp_path / "fedramp_ssp_template_structure.yaml")

        ssp = build_ssp_skeleton({}, data_dir=tmp_path)
        assert "back-matter" in ssp
        resources = ssp["back-matter"].get("resources", [])
        assert len(resources) >= 5, "Section 12 must reference at least 5 laws/regulations"
        titles = [r.get("title", "") for r in resources]
        assert any("FISMA" in t or "Federal Information Security" in t for t in titles)
        assert any("NIST" in t for t in titles)

    def test_build_ssp_information_type_has_uuid(self, tmp_path):
        """Section 2: information-types must include a uuid (OSCAL 1.0.4 requirement)."""
        from uiao_core.generators.ssp import build_ssp_skeleton

        ssp = build_ssp_skeleton({}, data_dir=tmp_path)
        info_types = ssp["system-characteristics"]["system-information"]["information-types"]
        assert len(info_types) >= 1
        assert "uuid" in info_types[0]

    def test_build_ssp_all_matrix_controls_included(self, tmp_path):
        """Appendix A: all unique NIST controls from compliance matrix must appear in implemented-requirements."""
        from uiao_core.generators.ssp import build_ssp_skeleton

        context = {
            "unified_compliance_matrix": [
                {"pillar": "Identity", "nist_controls": ["IA-2", "IA-5"]},
                {"pillar": "Network", "nist_controls": ["SC-7", "AC-4"]},
                {"pillar": "Monitoring", "nist_controls": ["CA-7", "SI-4"]},
            ]
        }
        ssp = build_ssp_skeleton(context, data_dir=tmp_path)
        implemented_ids = {r["control-id"] for r in ssp["control-implementation"]["implemented-requirements"]}
        assert implemented_ids == {"IA-2", "IA-5", "SC-7", "AC-4", "CA-7", "SI-4"}

    def test_build_ssp_no_duplicate_control_ids(self, tmp_path):
        """Appendix A: implemented-requirements must not contain duplicate control-ids."""
        from uiao_core.generators.ssp import build_ssp_skeleton

        context = {
            "unified_compliance_matrix": [
                {"pillar": "A", "nist_controls": ["AC-1"]},
                {"pillar": "B", "nist_controls": ["AC-1", "SC-7"]},
            ]
        }
        ssp = build_ssp_skeleton(context, data_dir=tmp_path)
        ctrl_ids = [r["control-id"] for r in ssp["control-implementation"]["implemented-requirements"]]
        assert len(ctrl_ids) == len(set(ctrl_ids)), "Duplicate control-ids found"

    def test_build_ssp_users_include_all_roles(self, tmp_path):
        """Section 11: system-implementation users must include all standard user types."""
        from uiao_core.generators.ssp import build_ssp_skeleton

        ssp = build_ssp_skeleton({}, data_dir=tmp_path)
        user_role_ids = {r for u in ssp["system-implementation"]["users"] for r in u.get("role-ids", [])}
        assert "admin" in user_role_ids
        assert "agency-admin" in user_role_ids

    def test_load_ssp_template_structure(self):
        """data/fedramp_ssp_template_structure.yaml must be loadable with all required keys."""
        import yaml

        template_path = _TEMPLATE_PATH
        assert template_path.exists(), "Template structure file not found"
        with open(template_path) as f:
            template = yaml.safe_load(f)
        assert template.get("version") == "rev5"
        assert template.get("impact_level") == "moderate"
        assert len(template.get("sections", [])) == 12, "Template must define exactly 12 sections"
        assert "appendix_a" in template
        assert "laws_and_regulations" in template
        assert len(template["laws_and_regulations"]) >= 5
        # Verify section numbers 1-12
        section_numbers = {s["number"] for s in template["sections"]}
        assert section_numbers == {str(i) for i in range(1, 13)}
