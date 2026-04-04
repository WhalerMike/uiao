"""Tests for uiao_core.models.canon module."""

from __future__ import annotations

import pytest

from uiao_core.models.canon import CanonEntry


class TestCanonEntry:
    """Tests for the CanonEntry Pydantic model."""

    def test_create_minimal_entry(self, sample_canon_entry: dict) -> None:
        """CanonEntry accepts a minimal dict with extra=allow."""
        entry = CanonEntry(**sample_canon_entry)
        assert entry.id == "test-entry-001"
        assert entry.name == "Test Canon Entry"

    def test_extra_fields_allowed(self) -> None:
        """CanonEntry allows extra fields (Week 1 permissive mode)."""
        entry = CanonEntry(
            id="extra-001",
            name="Extra Test",
            description="Has extra fields",
            category="testing",
            custom_field="custom_value",
        )
        assert entry.custom_field == "custom_value"

    def test_missing_required_field_raises(self) -> None:
        """CanonEntry requires id and name."""
        with pytest.raises(ValueError):
            CanonEntry(description="no id or name")


class TestDiagramDefinition:
    """Tests for the DiagramDefinition Pydantic model."""

    def test_create_minimal_diagram(self) -> None:
        """DiagramDefinition can be created with only content."""
        from uiao_core.models.canon import DiagramDefinition

        d = DiagramDefinition(content="flowchart TD\n    A --> B")
        assert d.content == "flowchart TD\n    A --> B"
        assert d.title == ""
        assert d.type == ""
        assert d.include_in == []

    def test_create_full_diagram(self) -> None:
        """DiagramDefinition accepts all documented fields."""
        from uiao_core.models.canon import DiagramDefinition

        d = DiagramDefinition(
            title="My Diagram",
            type="flowchart",
            description="A test diagram.",
            include_in=["doc1.md", "doc2.md"],
            content="flowchart TD\n    A --> B",
        )
        assert d.title == "My Diagram"
        assert d.type == "flowchart"
        assert d.include_in == ["doc1.md", "doc2.md"]

    def test_extra_fields_allowed(self) -> None:
        """DiagramDefinition allows extra fields (permissive mode)."""
        from uiao_core.models.canon import DiagramDefinition

        d = DiagramDefinition(content="flowchart TD\n    A --> B", author="alice")
        assert d.author == "alice"  # type: ignore[attr-defined]

    def test_empty_diagram_is_valid(self) -> None:
        """DiagramDefinition with no fields is valid (all default to empty)."""
        from uiao_core.models.canon import DiagramDefinition

        d = DiagramDefinition()
        assert d.content == ""
        assert d.title == ""


class TestCanonModelDiagrams:
    """Tests for the CanonModel.diagrams field."""

    def test_canon_model_has_diagrams_field(self) -> None:
        """CanonModel exposes a 'diagrams' dict field defaulting to empty."""
        from uiao_core.models.canon import CanonModel

        model = CanonModel()
        assert hasattr(model, "diagrams")
        assert model.diagrams == {}

    def test_canon_model_validates_diagrams(self) -> None:
        """CanonModel correctly validates a diagrams mapping."""
        from uiao_core.models.canon import CanonModel

        data = {
            "version": "1.0",
            "diagrams": {
                "my_diagram": {
                    "title": "Test",
                    "type": "flowchart",
                    "content": "flowchart TD\n    A --> B",
                }
            },
        }
        model = CanonModel.model_validate(data)
        assert "my_diagram" in model.diagrams
        assert model.diagrams["my_diagram"].title == "Test"
        assert "flowchart" in model.diagrams["my_diagram"].content

    def test_canon_model_backward_compatible_without_diagrams(self) -> None:
        """Existing canon YAML without 'diagrams' still validates."""
        from uiao_core.models.canon import CanonModel

        data = {"version": "1.0", "document": "Test Canon"}
        model = CanonModel.model_validate(data)
        assert model.diagrams == {}

    def test_leadership_briefing_canon_loads_with_diagrams(self, canon_dir) -> None:
        """generation-inputs/uiao_leadership_briefing_v1.0.yaml loads cleanly and has diagrams."""
        import yaml

        from uiao_core.models.canon import CanonModel

        canon_path = canon_dir / "uiao_leadership_briefing_v1.0.yaml"
        assert canon_path.exists(), f"Canon file not found: {canon_path}"
        data = yaml.safe_load(canon_path.read_text(encoding="utf-8"))
        model = CanonModel.model_validate(data)
        assert isinstance(model.diagrams, dict)
        assert len(model.diagrams) >= 1, "Expected at least one diagram in leadership briefing canon"
        for key, diagram in model.diagrams.items():
            assert diagram.content.strip(), f"Diagram '{key}' has empty content"


class TestCanonLoading:
    """Tests for loading canon YAML files from disk."""

    def test_canon_dir_exists(self, canon_dir) -> None:
        """The generation-inputs/ directory must exist in the project."""
        assert canon_dir.exists(), f"generation-inputs/ directory not found at {canon_dir}"

    def test_canon_has_yaml_files(self, canon_dir) -> None:
        """generation-inputs/ directory should contain at least one YAML file."""
        yamls = list(canon_dir.glob("*.yaml")) + list(canon_dir.glob("*.yml"))
        assert len(yamls) > 0, "No YAML files found in generation-inputs/"

    def test_data_dir_exists(self, data_dir) -> None:
        """The data/ directory must exist in the project."""
        assert data_dir.exists(), f"data/ directory not found at {data_dir}"

    def test_data_has_yaml_files(self, data_dir) -> None:
        """data/ directory should contain YAML files."""
        yamls = list(data_dir.glob("*.yml")) + list(data_dir.glob("*.yaml"))
        assert len(yamls) > 0, "No YAML files found in data/"
