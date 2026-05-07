"""Shared fixtures for ``tests/integration/``.

Deliberately small. Per-tier conftests (``tier1/conftest.py``) carry the
tier-specific behavior; this file only holds helpers that are useful in
both tier-1 and any future tier-3 reference-deployment harness.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def record_response(tmp_path: Path):
    """Opt-in recorder for promoting tier-1 captures to tier-2 fixtures.

    Activated only when ``UIAO_TIER1_RECORD=1`` is set in the environment.
    Writes one JSON file per call to ``tmp_path / 'tier1-record' / <name>.json``.
    The caller is responsible for sanitization before promoting any captured
    file to ``tests/fixtures/contract/<adapter>/`` per the contract README.
    """
    enabled = os.environ.get("UIAO_TIER1_RECORD") == "1"
    out_dir = tmp_path / "tier1-record"
    if enabled:
        out_dir.mkdir(parents=True, exist_ok=True)

    def _record(name: str, payload: Any) -> Path | None:
        if not enabled:
            return None
        target = out_dir / f"{name}.json"
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        return target

    return _record
