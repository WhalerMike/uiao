"""Shared pytest fixtures for uiao tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from canon_paths import CANON_ROOT, DATA_DIR, GENERATION_INPUTS_DIR


@pytest.fixture
def project_root() -> Path:
    """Return the uiao project root directory."""
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def canon_root() -> Path:
    """Return the resolved canon root (uiao checkout)."""
    return CANON_ROOT


@pytest.fixture
def canon_dir() -> Path:
    """Return the generation-inputs/ directory from canon."""
    return GENERATION_INPUTS_DIR


@pytest.fixture
def data_dir() -> Path:
    """Return the data/ directory from canon."""
    return DATA_DIR


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


# ---------------------------------------------------------------------------
# Auto-skip canon-dependent modules when generation-inputs/ is not available.
# Canon lives in uiao; generation-inputs/ was not migrated in the split
# (tracked in issue #2). These modules re-activate automatically once canon
# is restored in uiao.
# ---------------------------------------------------------------------------
from canon_paths import GENERATION_INPUTS_DIR as _GEN_INPUTS_DIR

_CANON_DEPENDENT_MODULES = {
    "test_diagrams",
    "test_mover_logic",
    "test_generators",
    "test_models",
    "test_overlay_loader",
    "test_ssp_inject",
    # Note: test_scuba_transformer_determinism was previously listed here
    # but it uses tests/fixtures/scuba_normalized_sample.json, not
    # generation-inputs/. Removed so the 16 SCuBA transformer tests
    # actually run.
}


def pytest_collection_modifyitems(config, items):
    """Skip tests depending on canon files not yet migrated to uiao."""
    if _GEN_INPUTS_DIR.exists():
        return
    skip_marker = pytest.mark.skip(
        reason="canon generation-inputs/ not migrated to uiao yet (issue #2)"
    )
    for item in items:
        module_name = item.module.__name__.rsplit(".", 1)[-1]
        if module_name in _CANON_DEPENDENT_MODULES:
            item.add_marker(skip_marker)
