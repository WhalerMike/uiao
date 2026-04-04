"""Shared pytest fixtures for uiao-core tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def canon_dir(project_root: Path) -> Path:
    """Return the generation-inputs/ directory path."""
    return project_root / "generation-inputs"


@pytest.fixture
def data_dir(project_root: Path) -> Path:
    """Return the data/ directory path."""
    return project_root / "data"


@pytest.fixture
def exports_dir(project_root: Path, tmp_path: Path) -> Path:
    """Return a temporary exports directory for test output."""
    out = tmp_path / "exports" / "oscal"
    out.mkdir(parents=True)
    return out


@pytest.fixture
def sample_canon_entry() -> dict:
    """Return a minimal canon-like dict for unit tests."""
    return {
        "id": "test-entry-001",
        "name": "Test Canon Entry",
        "description": "A test entry for unit testing.",
        "category": "testing",
    }
