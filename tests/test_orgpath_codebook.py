"""Tests for the OrgPath codebook loader (ADR-035, MOD_A)."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from uiao.governance.drift import DRIFT_IDENTITY, classify_identity_drift
from uiao.ir.models.core import ProvenanceRecord
from uiao.modernization.orgtree import (
    Codebook,
    CodebookValidationError,
    load_codebook,
)


PROV = ProvenanceRecord(source="test", timestamp="2026-04-20T00:00:00Z", version="0.1.0")


def test_default_codebook_loads_and_validates() -> None:
    codebook = load_codebook()
    assert isinstance(codebook, Codebook)
    assert codebook.document_id == "MOD_A"
    assert codebook.regex == "^ORG(-[A-Z0-9]{2,6}){0,8}$"
    assert codebook.is_active("ORG-IT-SEC-SOC-T1")
    assert codebook.parent_of("ORG-IT-SEC-SOC-T1") == "ORG-IT-SEC-SOC"
    # Root has no parent
    assert codebook.parent_of("ORG") is None


def test_codes_set_is_populated_and_regex_matches_every_entry() -> None:
    codebook = load_codebook()
    assert "ORG" in codebook.codes
    for code in codebook.codes:
        assert codebook.has_format(code), f"{code} fails regex"


def test_rejects_missing_parent(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        textwrap.dedent("""\
        schema_version: "1.0.0"
        document_id: MOD_A
        parent_canon: UIAO_007
        format:
          regex: "^ORG(-[A-Z0-9]{2,6}){0,8}$"
          max_depth: 8
          segment_pattern: "^[A-Z0-9]{2,6}$"
          root: ORG
          separator: "-"
        codes:
          - { code: ORG,       level: 0, description: Root,    parent: null }
          - { code: ORG-GHOST, level: 1, description: Orphan,  parent: ORG-NOPE }
    """)
    )
    with pytest.raises(CodebookValidationError, match="unknown parent"):
        load_codebook(bad)


def test_rejects_non_root_null_parent(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        textwrap.dedent("""\
        schema_version: "1.0.0"
        document_id: MOD_A
        parent_canon: UIAO_007
        format:
          regex: "^ORG(-[A-Z0-9]{2,6}){0,8}$"
          max_depth: 8
          segment_pattern: "^[A-Z0-9]{2,6}$"
          root: ORG
          separator: "-"
        codes:
          - { code: ORG,     level: 0, description: Root,   parent: null }
          - { code: ORG-IT,  level: 1, description: "IT",   parent: null }
    """)
    )
    with pytest.raises(CodebookValidationError, match="null parent"):
        load_codebook(bad)


def test_rejects_deprecated_pointing_to_unknown(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        textwrap.dedent("""\
        schema_version: "1.0.0"
        document_id: MOD_A
        parent_canon: UIAO_007
        format:
          regex: "^ORG(-[A-Z0-9]{2,6}){0,8}$"
          max_depth: 8
          segment_pattern: "^[A-Z0-9]{2,6}$"
          root: ORG
          separator: "-"
        codes:
          - { code: ORG,    level: 0, description: Root,   parent: null }
          - { code: ORG-IT, level: 1, description: "IT",   parent: ORG }
        deprecated:
          - { code: ORG-MKT, replaced_by: ORG-NOPE }
    """)
    )
    with pytest.raises(CodebookValidationError, match="replaced_by"):
        load_codebook(bad)


def test_phantom_drift_fires_on_deprecated_code(tmp_path: Path) -> None:
    good = tmp_path / "good.yaml"
    good.write_text(
        textwrap.dedent("""\
        schema_version: "1.0.0"
        document_id: MOD_A
        parent_canon: UIAO_007
        format:
          regex: "^ORG(-[A-Z0-9]{2,6}){0,8}$"
          max_depth: 8
          segment_pattern: "^[A-Z0-9]{2,6}$"
          root: ORG
          separator: "-"
        codes:
          - { code: ORG,       level: 0, description: Root,  parent: null }
          - { code: ORG-SALES, level: 1, description: Sales, parent: ORG }
        deprecated:
          - { code: ORG-MKT, replaced_by: ORG-SALES, reason: "Rename" }
    """)
    )
    codebook = load_codebook(good)
    assert codebook.is_deprecated("ORG-MKT")
    assert codebook.replacement_for("ORG-MKT") == "ORG-SALES"

    drift = classify_identity_drift(
        resource_id="user:1",
        policy_ref="orgpath-codebook",
        expected_state={"orgpath": "ORG-SALES"},
        actual_state={"orgpath": "ORG-MKT"},
        provenance=PROV,
        orgpath_codebook=codebook,
    )
    assert drift is not None
    assert drift.drift_class == DRIFT_IDENTITY
    assert any("Phantom Drift" in r for r in drift.delta["identity_reasons"])


def test_legacy_set_argument_still_accepted() -> None:
    drift = classify_identity_drift(
        resource_id="user:1",
        policy_ref="orgpath-codebook",
        expected_state={"orgpath": "ORG-IT"},
        actual_state={"orgpath": "ORG-GHOST"},
        provenance=PROV,
        orgpath_codebook={"ORG", "ORG-IT"},
    )
    assert drift is not None
    assert drift.drift_class == DRIFT_IDENTITY
    assert any("not in canonical codebook" in r for r in drift.delta["identity_reasons"])
