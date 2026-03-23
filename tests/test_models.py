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
        with pytest.raises(Exception):
            CanonEntry(description="no id or name")


class TestCanonLoading:
    """Tests for loading canon YAML files from disk."""

    def test_canon_dir_exists(self, canon_dir) -> None:
        """The canon/ directory must exist in the project."""
        assert canon_dir.exists(), f"canon/ directory not found at {canon_dir}"

    def test_canon_has_yaml_files(self, canon_dir) -> None:
        """canon/ directory should contain at least one YAML file."""
        yamls = list(canon_dir.glob("*.yaml")) + list(canon_dir.glob("*.yml"))
        assert len(yamls) > 0, "No YAML files found in canon/"

    def test_data_dir_exists(self, data_dir) -> None:
        """The data/ directory must exist in the project."""
        assert data_dir.exists(), f"data/ directory not found at {data_dir}"

    def test_data_has_yaml_files(self, data_dir) -> None:
        """data/ directory should contain YAML files."""
        yamls = list(data_dir.glob("*.yml")) + list(data_dir.glob("*.yaml"))
        assert len(yamls) > 0, "No YAML files found in data/"
