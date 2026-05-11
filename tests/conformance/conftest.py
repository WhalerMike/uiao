"""Shared fixtures for the HRIT conformance test pack (WS-B4).

All fixtures point at the WS-A8 reference fixture:
    examples/hrit/opm-treas-irs/

The entire module is skipped if any required fixture file is absent.

References
----------
- inbox/v0.6.0-hrit-productization/03-batch-plan.md §WS-B4
- examples/hrit/opm-treas-irs/ — WS-A8 reference fixture
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_FIXTURE_ROOT = Path(__file__).parent.parent.parent / "examples" / "hrit" / "opm-treas-irs"

_REQUIRED_FILES = [
    _FIXTURE_ROOT / "controlling-ato.json",
    _FIXTURE_ROOT / "ssp-latitude-table.yaml",
    _FIXTURE_ROOT / "tenant-treas-config.yaml",
    _FIXTURE_ROOT / "tenant-irs-config.yaml",
]

# ---------------------------------------------------------------------------
# Module-level skip if any fixture file is absent
# ---------------------------------------------------------------------------

_MISSING = [str(p) for p in _REQUIRED_FILES if not p.exists()]
if _MISSING:
    pytest.skip(
        f"WS-A8 fixture files not found — skipping conformance module: {_MISSING}",
        allow_module_level=True,
    )


# ---------------------------------------------------------------------------
# YAML helper
# ---------------------------------------------------------------------------


def _load_yaml(path: Path) -> Any:
    """Load a YAML file, skipping the test if PyYAML is unavailable."""
    try:
        import yaml  # type: ignore[import-untyped]  # noqa: PLC0415
    except ImportError:
        pytest.skip("PyYAML not installed — cannot load YAML fixture files")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def hrit_fixture_root() -> Path:
    """Path to examples/hrit/opm-treas-irs/."""
    return _FIXTURE_ROOT


@pytest.fixture(scope="session")
def controlling_ato_data() -> dict[str, Any]:
    """Parsed controlling-ato.json from the reference fixture."""
    raw = (_FIXTURE_ROOT / "controlling-ato.json").read_text(encoding="utf-8")
    return json.loads(raw)  # type: ignore[no-any-return]


@pytest.fixture(scope="session")
def ssp_latitude_table() -> Any:
    """Parsed ssp-latitude-table.yaml from the reference fixture."""
    return _load_yaml(_FIXTURE_ROOT / "ssp-latitude-table.yaml")


@pytest.fixture(scope="session")
def treas_tenant_config() -> Any:
    """Parsed tenant-treas-config.yaml from the reference fixture."""
    return _load_yaml(_FIXTURE_ROOT / "tenant-treas-config.yaml")


@pytest.fixture(scope="session")
def irs_tenant_config() -> Any:
    """Parsed tenant-irs-config.yaml from the reference fixture."""
    return _load_yaml(_FIXTURE_ROOT / "tenant-irs-config.yaml")


@pytest.fixture(scope="session")
def hmac_signing_key() -> bytes:
    """Deterministic test HMAC key — MUST NOT be used in production."""
    return b"test-conformance-key-do-not-use-in-prod"
