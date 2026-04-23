"""Tests for the OPA version pre-flight in normalize_scuba.

Covers enhancement E3.3 of the RFC-0026 roadmap
(docs/docs/uiao-rfc-0026-roadmap.md): the DRIFT-PROVENANCE classifier that
verifies ScubaGear runs used an OPA binary at or above the pin declared in
scuba.yaml.

Until cisagov/ScubaGear#2075 (Qwilfish, 2026-06-30) lands, the OpaVersion
field is expected to be absent in real ScubaGear output; the pre-flight
must tolerate absence with a warning rather than a hard failure.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest

from uiao.adapters.scuba.ir import normalize_scuba as ns_mod
from uiao.adapters.scuba.ir.normalize_scuba import (
    _parse_version,
    _preflight_opa_provenance,
    normalize_scuba,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_overlay_cache():
    """Ensure each test sees a fresh overlay load — no cross-test leakage."""
    ns_mod._SCUBA_OVERLAY_CACHE = None
    yield
    ns_mod._SCUBA_OVERLAY_CACHE = None


def _overlay(opa_pin: str | None) -> Dict[str, Any]:
    """Build a minimal scuba.yaml-shaped dict with or without a pin."""
    uiao_ext: Dict[str, Any] = {}
    if opa_pin is not None:
        uiao_ext["opa_version_minimum"] = opa_pin
    return {"uiao_extensions": uiao_ext}


def _scuba_json(
    *,
    tool_version: str | None = "1.5.0",
    opa_version: str | None = None,
    extra_envelope: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Build a ScubaGear-shaped JSON with TestResults + optional envelope fields."""
    doc: Dict[str, Any] = {
        "TestResults": [
            {"PolicyId": "MS.AAD.2.1v1", "RequirementMet": True, "ActualValue": {"mfa_enabled": True}},
        ],
    }
    if tool_version is not None:
        doc["ToolVersion"] = tool_version
    if opa_version is not None:
        doc["OpaVersion"] = opa_version
    if extra_envelope:
        doc.update(extra_envelope)
    return doc


# ---------------------------------------------------------------------------
# Unit tests — _parse_version
# ---------------------------------------------------------------------------


class TestParseVersion:
    @pytest.mark.parametrize(
        "s,expected",
        [
            # Trailing 0 is the release marker; -1 marks a pre-release suffix
            ("0.59.0", (0, 59, 0, 0)),
            ("1.2.3", (1, 2, 3, 0)),
            ("v1.0.0", (1, 0, 0, 0)),
            ("V0.60", (0, 60, 0)),
            ("0.59.0-rc1", (0, 59, 0, -1)),
        ],
    )
    def test_parses_valid(self, s: str, expected: tuple) -> None:
        assert _parse_version(s) == expected

    @pytest.mark.parametrize("s", [None, "", "nonsense", "..."])
    def test_returns_none_for_invalid(self, s: Any) -> None:
        assert _parse_version(s) is None

    def test_rc_sorts_below_release(self) -> None:
        assert _parse_version("0.59.0-rc1") < _parse_version("0.59.0")  # type: ignore[operator]


# ---------------------------------------------------------------------------
# Unit tests — _preflight_opa_provenance (covers all five status paths)
# ---------------------------------------------------------------------------


class TestPreflightOpaProvenance:
    def test_ok_when_observed_at_pin(self) -> None:
        result = _preflight_opa_provenance(
            source_metadata={"OpaVersion": "0.59.0"},
            scuba_overlay=_overlay("0.59.0"),
        )
        assert result["status"] == "ok"
        assert result["observed"] == "0.59.0"
        assert result["minimum"] == "0.59.0"
        assert result["drift_class"] is None
        assert result["classification"] is None

    def test_ok_when_observed_above_pin(self) -> None:
        result = _preflight_opa_provenance(
            source_metadata={"OpaVersion": "0.62.1"},
            scuba_overlay=_overlay("0.59.0"),
        )
        assert result["status"] == "ok"
        assert result["drift_class"] is None

    def test_missing_emits_drift_provenance_risky(self) -> None:
        # The Qwilfish-blocking scenario — ScubaGear output doesn't expose OpaVersion
        result = _preflight_opa_provenance(
            source_metadata={"ToolVersion": "1.5.0"},  # no OpaVersion
            scuba_overlay=_overlay("0.59.0"),
        )
        assert result["status"] == "missing"
        assert result["drift_class"] == "DRIFT-PROVENANCE"
        assert result["classification"] == "risky"
        assert "2075" in result["reason"]  # reason cites the upstream issue

    def test_below_pin_emits_drift_provenance_unauthorized(self) -> None:
        result = _preflight_opa_provenance(
            source_metadata={"OpaVersion": "0.55.0"},
            scuba_overlay=_overlay("0.59.0"),
        )
        assert result["status"] == "below_pin"
        assert result["drift_class"] == "DRIFT-PROVENANCE"
        assert result["classification"] == "unauthorized"
        assert "0.55.0" in result["reason"]
        assert "0.59.0" in result["reason"]

    def test_unparseable_observed_emits_drift_provenance(self) -> None:
        result = _preflight_opa_provenance(
            source_metadata={"OpaVersion": "totally not a version"},
            scuba_overlay=_overlay("0.59.0"),
        )
        assert result["status"] == "unparseable"
        assert result["drift_class"] == "DRIFT-PROVENANCE"

    def test_skipped_when_no_pin_configured(self) -> None:
        result = _preflight_opa_provenance(
            source_metadata={"OpaVersion": "0.59.0"},
            scuba_overlay=_overlay(None),
        )
        assert result["status"] == "skipped"
        assert result["drift_class"] is None

    def test_recognizes_case_variant_field_names(self) -> None:
        # Envelope might land with OPAVersion or opa_version depending on source
        for field in ("OpaVersion", "OPAVersion", "OpaBinaryVersion", "opa_version"):
            result = _preflight_opa_provenance(
                source_metadata={field: "0.60.0"},
                scuba_overlay=_overlay("0.59.0"),
            )
            assert result["status"] == "ok", f"Field {field!r} should be recognized"


# ---------------------------------------------------------------------------
# Integration test — full normalize_scuba attaches pre-flight to envelope
# ---------------------------------------------------------------------------


class TestNormalizeScubaAttachesPreflight:
    def test_envelope_carries_preflight_when_opa_present(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # Force overlay to a known pin, isolated from the real scuba.yaml
        monkeypatch.setattr(ns_mod, "_load_scuba_overlay", lambda repo_root=None: _overlay("0.59.0"))

        report = tmp_path / "ScubaResults.json"
        report.write_text(json.dumps(_scuba_json(opa_version="0.60.0")))

        out = normalize_scuba(report)
        preflight = out["assessment_metadata"]["provenance_preflight"]
        assert preflight["status"] == "ok"
        assert preflight["observed"] == "0.60.0"
        assert preflight["minimum"] == "0.59.0"

    def test_envelope_carries_missing_preflight_when_opa_absent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Realistic post-merge, pre-Qwilfish state: ScubaGear JSON has no OpaVersion
        monkeypatch.setattr(ns_mod, "_load_scuba_overlay", lambda repo_root=None: _overlay("0.59.0"))

        report = tmp_path / "ScubaResults.json"
        report.write_text(json.dumps(_scuba_json(opa_version=None)))

        out = normalize_scuba(report)
        preflight = out["assessment_metadata"]["provenance_preflight"]
        assert preflight["status"] == "missing"
        assert preflight["drift_class"] == "DRIFT-PROVENANCE"
        assert preflight["classification"] == "risky"

    def test_envelope_carries_below_pin_when_opa_stale(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        monkeypatch.setattr(ns_mod, "_load_scuba_overlay", lambda repo_root=None: _overlay("0.59.0"))

        report = tmp_path / "ScubaResults.json"
        report.write_text(json.dumps(_scuba_json(opa_version="0.55.0")))

        import logging

        with caplog.at_level(logging.WARNING, logger=ns_mod.logger.name):
            out = normalize_scuba(report)

        preflight = out["assessment_metadata"]["provenance_preflight"]
        assert preflight["status"] == "below_pin"
        assert preflight["classification"] == "unauthorized"
        # Confirm the DRIFT-PROVENANCE warning was actually emitted
        assert any("DRIFT-PROVENANCE" in rec.getMessage() for rec in caplog.records), (
            f"Expected DRIFT-PROVENANCE warning in log, got: {[r.getMessage() for r in caplog.records]}"
        )

    def test_real_overlay_pin_is_discoverable(self) -> None:
        """The real canon scuba.yaml should carry an opa_version_minimum.

        This guards against silently losing the pin during future overlay
        edits — without the pin, every real-world run degrades to status=skipped.
        """
        overlay = ns_mod._load_scuba_overlay()
        pin = (overlay.get("uiao_extensions") or {}).get("opa_version_minimum")
        assert pin, "scuba.yaml must declare uiao_extensions.opa_version_minimum"
        # Confirm it's a parseable version
        assert _parse_version(pin) is not None, f"Pin {pin!r} must be a parseable semver"
