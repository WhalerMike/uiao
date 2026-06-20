"""Tests for scripts/check_control_library.py — the control-library integrity
and schema-drift guard.
"""

from __future__ import annotations

import importlib.util
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check_control_library.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_control_library", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_library_is_internally_consistent():
    mod = _load()
    r = mod.scan()
    # index.yaml must match the files on disk
    assert r["mismatches"] == [], r["mismatches"]
    assert r["base"] + r["enhancements"] == r["total_files"]


def test_no_schema_drift():
    """Every control uses the canonical schema-A field set (no schema-B drift)."""
    mod = _load()
    r = mod.scan()
    assert r["schema_drift"] == [], "control(s) reintroduced legacy schema-B fields: " + "; ".join(r["schema_drift"])


def test_guard_field_set_nonempty():
    mod = _load()
    assert mod._LEGACY_FIELDS  # the guard must actually watch for something
