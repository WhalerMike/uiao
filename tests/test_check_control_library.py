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


def test_no_status_drift():
    """Every control's status is a valid OSCAL implementation-status token.

    Downstream matching is exact and case-sensitive (ssp.py passes the token
    straight into the OSCAL implementation-status prop), so a case variant such
    as "Implemented" matches neither the implemented nor the not-implemented
    bucket and is silently dropped.
    """
    mod = _load()
    r = mod.scan()
    assert r["status_drift"] == [], "control(s) carry an off-vocabulary status: " + "; ".join(r["status_drift"])


def test_status_vocabulary_is_lowercase():
    """The vocabulary itself must stay lower-case, or the guard cannot bite."""
    mod = _load()
    assert mod._VALID_STATUSES
    assert all(s == s.lower() for s in mod._VALID_STATUSES)


def test_status_guard_flags_case_variant(tmp_path, monkeypatch):
    """A capitalized status must be reported as drift and fail --strict."""
    mod = _load()
    fam_dir = tmp_path / "ca"
    fam_dir.mkdir()
    (fam_dir / "CA-1.yml").write_text("control_id: CA-1\nstatus: Implemented\n")
    (tmp_path / "index.yaml").write_text(
        "total_controls: 1\nbase_controls: 1\nenhancements: 0\nfamilies:\n  ca:\n    count: 1\n"
    )
    monkeypatch.setattr(mod, "LIB_DIR", tmp_path)
    monkeypatch.setattr(mod, "INDEX", tmp_path / "index.yaml")

    r = mod.scan()
    assert r["status_drift"] == ["ca/CA-1.yml: 'Implemented'"]
    assert any("status drift" in m for m in r["mismatches"])


def test_guard_field_set_nonempty():
    mod = _load()
    assert mod._LEGACY_FIELDS  # the guard must actually watch for something
