"""Tests for UIAO_110 DRIFT-AUTHZ ConsentEnvelopeValidator (§0.4).

Closes the registry-level half of DRIFT-AUTHZ: when an adapter
accesses object types outside its declared canon ``scope:``, or when
an active adapter has no scope declaration at all, the validator
emits a DRIFT-AUTHZ DriftState. The state-diff half lives in
``tests/test_drift_classifiers.py`` and remains unchanged.

The substrate walker is wired to flag missing/empty ``scope:``
declarations so registry-hygiene drift is caught at PR time.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from uiao.governance.consent_envelope import (
    ConsentEnvelopeValidator,
    load_adapter_envelopes,
    observed_scope_for_run,
)
from uiao.ir.models.core import ProvenanceRecord


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def provenance() -> ProvenanceRecord:
    return ProvenanceRecord(
        source="test",
        timestamp="2026-04-24T13:00:00+00:00",
        version="1.0",
        content_hash="probe",
        actor="test",
    )


def _write_registry(path: Path, adapters: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"adapters": adapters}), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# load_adapter_envelopes
# ---------------------------------------------------------------------------


class TestLoadAdapterEnvelopes:
    def test_missing_files_return_empty(self, tmp_path):
        envs = load_adapter_envelopes([tmp_path / "nope.yaml"])
        assert envs == {}

    def test_single_registry_load(self, tmp_path):
        path = _write_registry(
            tmp_path / "reg.yaml",
            [
                {"id": "entra-id", "scope": ["user-objects", "group-objects"]},
                {"id": "scubagear", "scope": []},
            ],
        )
        envs = load_adapter_envelopes([path])
        assert envs["entra-id"] == {"user-objects", "group-objects"}
        assert envs["scubagear"] == set()

    def test_later_registry_overrides_earlier(self, tmp_path):
        early = _write_registry(
            tmp_path / "a.yaml",
            [{"id": "entra-id", "scope": ["user-objects"]}],
        )
        late = _write_registry(
            tmp_path / "b.yaml",
            [{"id": "entra-id", "scope": ["user-objects", "group-objects"]}],
        )
        envs = load_adapter_envelopes([early, late])
        assert envs["entra-id"] == {"user-objects", "group-objects"}

    def test_modernization_adapters_top_level_key(self, tmp_path):
        path = tmp_path / "mod.yaml"
        path.write_text(
            yaml.safe_dump({"modernization_adapters": [{"id": "tf", "scope": ["resources"]}]}),
            encoding="utf-8",
        )
        envs = load_adapter_envelopes([path])
        assert envs == {"tf": {"resources"}}

    def test_adapters_without_scope_key_are_dropped(self, tmp_path):
        path = _write_registry(tmp_path / "r.yaml", [{"id": "skinny"}])
        envs = load_adapter_envelopes([path])
        # No "scope" key → no envelope. The validator's missing_declaration
        # signal handles this, not the loader.
        assert "skinny" not in envs

    def test_malformed_yaml_silently_skipped(self, tmp_path):
        path = tmp_path / "bad.yaml"
        path.write_text("::: not valid yaml :::", encoding="utf-8")
        envs = load_adapter_envelopes([path])
        assert envs == {}


# ---------------------------------------------------------------------------
# ConsentEnvelopeValidator
# ---------------------------------------------------------------------------


class TestConsentEnvelopeValidator:
    def test_in_scope_observation_no_violation(self):
        v = ConsentEnvelopeValidator(envelopes={"entra-id": {"user-objects", "group-objects"}})
        report = v.validate("entra-id", ["user-objects"])
        assert not report.has_violation
        assert report.in_scope == frozenset({"user-objects"})
        assert report.out_of_scope == frozenset()

    def test_out_of_scope_access_flagged(self):
        v = ConsentEnvelopeValidator(envelopes={"entra-id": {"user-objects"}})
        report = v.validate("entra-id", ["user-objects", "service-principals"])
        assert report.has_violation
        assert report.out_of_scope == frozenset({"service-principals"})
        assert report.in_scope == frozenset({"user-objects"})

    def test_missing_declaration_is_violation(self):
        v = ConsentEnvelopeValidator(envelopes={})
        report = v.validate("phantom-adapter", ["anything"])
        assert report.has_violation
        assert report.missing_declaration is True

    def test_explicit_empty_scope_not_missing_declaration(self):
        v = ConsentEnvelopeValidator(envelopes={"strict": set()})
        report = v.validate("strict", [])
        assert not report.has_violation
        assert report.missing_declaration is False
        assert report.declared_scope == frozenset()

    def test_explicit_empty_scope_with_observed_access_flagged(self):
        v = ConsentEnvelopeValidator(envelopes={"strict": set()})
        report = v.validate("strict", ["user-objects"])
        assert report.has_violation
        assert report.missing_declaration is False
        assert report.out_of_scope == frozenset({"user-objects"})

    def test_observed_scope_whitespace_normalized(self):
        v = ConsentEnvelopeValidator(envelopes={"a": {"users"}})
        report = v.validate("a", ["  users  ", " ", ""])
        assert report.observed_scope == frozenset({"users"})

    def test_validate_many(self):
        v = ConsentEnvelopeValidator(
            envelopes={
                "ok": {"x", "y"},
                "bad": {"x"},
            }
        )
        results = v.validate_many({"ok": ["x"], "bad": ["x", "z"], "missing": ["q"]})
        by_id = {r.adapter_id: r for r in results}
        assert not by_id["ok"].has_violation
        assert by_id["bad"].out_of_scope == frozenset({"z"})
        assert by_id["missing"].missing_declaration

    def test_as_drift_state_returns_none_when_clean(self, provenance):
        v = ConsentEnvelopeValidator(envelopes={"a": {"x"}})
        report = v.validate("a", ["x"])
        assert report.as_drift_state(provenance=provenance) is None

    def test_as_drift_state_emits_drift_authz(self, provenance):
        v = ConsentEnvelopeValidator(envelopes={"a": {"x"}})
        report = v.validate("a", ["x", "y"])
        ds = report.as_drift_state(provenance=provenance)
        assert ds is not None
        assert ds.drift_class == "DRIFT-AUTHZ"
        assert ds.classification == "unauthorized"
        assert ds.drift_detected is True
        assert ds.resource_id == "adapter:a"
        # Out-of-scope items surface in the delta as additions.
        assert "y" in ds.delta["added"]
        # Reasons cite the offending type.
        reasons = ds.delta.get("consent_envelope_reasons", [])
        assert any("y" in r for r in reasons)

    def test_as_drift_state_reasons_for_missing_declaration(self, provenance):
        v = ConsentEnvelopeValidator(envelopes={})
        report = v.validate("phantom", ["anything"])
        ds = report.as_drift_state(provenance=provenance)
        assert ds is not None
        reasons = ds.delta.get("consent_envelope_reasons", [])
        assert any("no scope: declaration" in r for r in reasons)

    def test_report_as_dict_round_trips_through_json(self):
        v = ConsentEnvelopeValidator(envelopes={"a": {"x", "y"}})
        report = v.validate("a", ["x", "z"])
        # has_violation surfaces in the dict view.
        d = report.as_dict()
        round = json.loads(json.dumps(d))
        assert round["has_violation"] is True
        assert round["out_of_scope"] == ["z"]


# ---------------------------------------------------------------------------
# observed_scope_for_run — scheduler-run extraction helper
# ---------------------------------------------------------------------------


def _write_evidence(adapter_dir: Path, payload: dict) -> None:
    adapter_dir.mkdir(parents=True, exist_ok=True)
    (adapter_dir / "evidence.json").write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


class TestObservedScopeForRun:
    def test_missing_run_dir_returns_empty(self, tmp_path):
        assert observed_scope_for_run(tmp_path / "nope") == {}

    def test_extracts_normalized_data_accessed_scope(self, tmp_path):
        run = tmp_path / "schedrun-x"
        _write_evidence(
            run / "adapters" / "entra-id",
            {"normalized_data": {"accessed_scope": ["user-objects", "group-objects"]}},
        )
        out = observed_scope_for_run(run)
        assert out["entra-id"] == ["user-objects", "group-objects"]

    def test_falls_back_to_raw_data_when_normalized_absent(self, tmp_path):
        run = tmp_path / "schedrun-y"
        _write_evidence(
            run / "adapters" / "scubagear",
            {"raw_data": {"accessed_scope": ["baseline"]}},
        )
        assert observed_scope_for_run(run) == {"scubagear": ["baseline"]}

    def test_empty_when_no_scope_field(self, tmp_path):
        run = tmp_path / "schedrun-z"
        _write_evidence(
            run / "adapters" / "quiet",
            {"normalized_data": {"probe": True}},
        )
        # Adapter exists in the run but emitted no scope hint → empty
        # observed (in-scope by definition, no false positive).
        assert observed_scope_for_run(run) == {"quiet": []}

    def test_observed_scope_round_trips_through_validator(self, tmp_path, provenance):
        # End-to-end: scheduler run → observed scope → validator → DriftState.
        run = tmp_path / "schedrun-e2e"
        _write_evidence(
            run / "adapters" / "rogue",
            {"normalized_data": {"accessed_scope": ["secrets-vault", "user-objects"]}},
        )
        observed = observed_scope_for_run(run)
        validator = ConsentEnvelopeValidator(
            envelopes={"rogue": {"user-objects"}},
        )
        report = validator.validate("rogue", observed["rogue"])
        ds = report.as_drift_state(provenance=provenance)
        assert ds is not None
        assert ds.drift_class == "DRIFT-AUTHZ"
        assert "secrets-vault" in ds.delta["added"]


# ---------------------------------------------------------------------------
# Substrate walker — registry-hygiene scan
# ---------------------------------------------------------------------------


class TestSubstrateWalkerConsentEnvelope:
    def test_active_adapter_missing_scope_is_p1(self, tmp_path, monkeypatch):
        # Build a minimal canon tree with a single active adapter that
        # has no scope: key.
        canon = tmp_path / "src" / "uiao" / "canon"
        canon.mkdir(parents=True)
        (canon / "substrate-manifest.yaml").write_text(yaml.safe_dump({"modules": []}), encoding="utf-8")
        (canon / "modernization-registry.yaml").write_text(
            yaml.safe_dump({"adapters": [{"id": "leaky", "status": "active"}]}),
            encoding="utf-8",
        )

        from uiao.substrate.walker import walk_substrate

        report = walk_substrate(workspace_root=tmp_path)
        authz = [f for f in report.findings if f.drift_class == "DRIFT-AUTHZ"]
        assert len(authz) == 1
        assert authz[0].severity == "P1"
        assert "leaky" in authz[0].path
        assert "scope" in authz[0].detail.lower()

    def test_active_adapter_empty_scope_is_p2(self, tmp_path):
        canon = tmp_path / "src" / "uiao" / "canon"
        canon.mkdir(parents=True)
        (canon / "substrate-manifest.yaml").write_text(yaml.safe_dump({"modules": []}), encoding="utf-8")
        (canon / "modernization-registry.yaml").write_text(
            yaml.safe_dump({"adapters": [{"id": "empty-env", "status": "active", "scope": []}]}),
            encoding="utf-8",
        )

        from uiao.substrate.walker import walk_substrate

        report = walk_substrate(workspace_root=tmp_path)
        authz = [f for f in report.findings if f.drift_class == "DRIFT-AUTHZ"]
        assert len(authz) == 1
        assert authz[0].severity == "P2"

    def test_reserved_adapter_skipped(self, tmp_path):
        canon = tmp_path / "src" / "uiao" / "canon"
        canon.mkdir(parents=True)
        (canon / "substrate-manifest.yaml").write_text(yaml.safe_dump({"modules": []}), encoding="utf-8")
        (canon / "modernization-registry.yaml").write_text(
            yaml.safe_dump({"adapters": [{"id": "future", "status": "reserved"}]}),
            encoding="utf-8",
        )

        from uiao.substrate.walker import walk_substrate

        report = walk_substrate(workspace_root=tmp_path)
        authz = [f for f in report.findings if f.drift_class == "DRIFT-AUTHZ"]
        assert authz == []

    def test_active_adapter_with_scope_clean(self, tmp_path):
        canon = tmp_path / "src" / "uiao" / "canon"
        canon.mkdir(parents=True)
        (canon / "substrate-manifest.yaml").write_text(yaml.safe_dump({"modules": []}), encoding="utf-8")
        (canon / "modernization-registry.yaml").write_text(
            yaml.safe_dump({"adapters": [{"id": "good", "status": "active", "scope": ["x", "y"]}]}),
            encoding="utf-8",
        )

        from uiao.substrate.walker import walk_substrate

        report = walk_substrate(workspace_root=tmp_path)
        authz = [f for f in report.findings if f.drift_class == "DRIFT-AUTHZ"]
        assert authz == []

    def test_real_canon_passes_consent_envelope_scan(self):
        """Smoke test against the live canon registries: every active
        adapter declares a scope. This guards against silent drift in the
        canon itself."""
        from uiao.substrate.walker import walk_substrate

        report = walk_substrate()
        authz_p1 = [f for f in report.findings if f.drift_class == "DRIFT-AUTHZ" and f.severity == "P1"]
        assert authz_p1 == [], f"Live canon has DRIFT-AUTHZ P1 findings — registry hygiene broken: {authz_p1}"
