"""Tests for UIAO_110 DRIFT-IDENTITY IssuerResolver (§0.5).

Closes the runtime-issuer-chain half of DRIFT-IDENTITY: when an
adapter's observed certificate chain doesn't reach its declared
trust anchor — or when an adapter claims certificate-anchored=true
but declares no anchor — the validator emits a DRIFT-IDENTITY
DriftState. The state-diff half lives in
``tests/test_drift_classifiers.py`` and remains unchanged.

The substrate walker is wired to flag missing ``trust-anchor:``
declarations on certificate-anchored adapters so registry-hygiene
drift is caught at PR time.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from uiao.governance.issuer_resolution import (
    CertificateLink,
    IssuerResolver,
    TrustAnchor,
    load_trust_anchors,
    observed_chain_for_run,
)
from uiao.ir.models.core import ProvenanceRecord


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def provenance() -> ProvenanceRecord:
    return ProvenanceRecord(
        source="test",
        timestamp="2026-04-25T00:00:00+00:00",
        version="1.0",
        content_hash="probe",
        actor="test",
    )


def _write_registry(path: Path, adapters: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"adapters": adapters}), encoding="utf-8")
    return path


def _well_linked_chain(
    *,
    leaf_subject: str = "CN=service.contoso.com",
    leaf_issuer: str = "CN=Contoso Intermediate CA",
    intermediate_subject: str = "CN=Contoso Intermediate CA",
    intermediate_issuer: str = "CN=Contoso Root CA",
    root_subject: str = "CN=Contoso Root CA",
    root_issuer: str = "CN=Contoso Root CA",
    leaf_fp: str = "11" * 32,
    intermediate_fp: str = "22" * 32,
    root_fp: str = "33" * 32,
) -> list[dict]:
    return [
        {"subject": leaf_subject, "issuer": leaf_issuer, "fingerprint_sha256": leaf_fp},
        {
            "subject": intermediate_subject,
            "issuer": intermediate_issuer,
            "fingerprint_sha256": intermediate_fp,
        },
        {"subject": root_subject, "issuer": root_issuer, "fingerprint_sha256": root_fp},
    ]


# ---------------------------------------------------------------------------
# load_trust_anchors
# ---------------------------------------------------------------------------


class TestLoadTrustAnchors:
    def test_missing_files_return_empty(self, tmp_path):
        anchors = load_trust_anchors([tmp_path / "nope.yaml"])
        assert anchors == {}

    def test_mapping_anchor_load(self, tmp_path):
        path = _write_registry(
            tmp_path / "r.yaml",
            [
                {
                    "id": "entra-id",
                    "trust-anchor": {
                        "subject": "CN=MS Root",
                        "fingerprint_sha256": "AB" * 32,
                    },
                }
            ],
        )
        anchors = load_trust_anchors([path])
        assert anchors["entra-id"].subject == "CN=MS Root"
        assert anchors["entra-id"].fingerprint_sha256 == "ab" * 32  # lowercased

    def test_bare_string_anchor_treated_as_subject(self, tmp_path):
        path = _write_registry(
            tmp_path / "r.yaml",
            [{"id": "tf", "trust-anchor": "CN=HashiCorp Root"}],
        )
        anchors = load_trust_anchors([path])
        assert anchors["tf"].subject == "CN=HashiCorp Root"
        assert anchors["tf"].fingerprint_sha256 == ""

    def test_adapters_without_anchor_key_dropped(self, tmp_path):
        path = _write_registry(tmp_path / "r.yaml", [{"id": "skinny"}])
        anchors = load_trust_anchors([path])
        assert "skinny" not in anchors

    def test_later_registry_overrides_earlier(self, tmp_path):
        early = _write_registry(
            tmp_path / "a.yaml",
            [{"id": "x", "trust-anchor": {"subject": "CN=Old"}}],
        )
        late = _write_registry(
            tmp_path / "b.yaml",
            [{"id": "x", "trust-anchor": {"subject": "CN=New"}}],
        )
        anchors = load_trust_anchors([early, late])
        assert anchors["x"].subject == "CN=New"

    def test_modernization_adapters_top_level_key(self, tmp_path):
        path = tmp_path / "mod.yaml"
        path.write_text(
            yaml.safe_dump({"modernization_adapters": [{"id": "tf", "trust-anchor": "CN=Root"}]}),
            encoding="utf-8",
        )
        anchors = load_trust_anchors([path])
        assert anchors == {"tf": TrustAnchor(subject="CN=Root")}

    def test_malformed_yaml_silently_skipped(self, tmp_path):
        path = tmp_path / "bad.yaml"
        path.write_text(":: not valid yaml ::", encoding="utf-8")
        assert load_trust_anchors([path]) == {}


# ---------------------------------------------------------------------------
# IssuerResolver
# ---------------------------------------------------------------------------


class TestIssuerResolver:
    def test_well_linked_chain_reaching_subject_anchor_clean(self):
        r = IssuerResolver(anchors={"a": TrustAnchor(subject="CN=Contoso Root CA")})
        report = r.validate("a", _well_linked_chain())
        assert report.chain_reaches_anchor
        assert report.broken_at == -1
        assert not report.has_violation

    def test_well_linked_chain_reaching_fingerprint_anchor(self):
        r = IssuerResolver(anchors={"a": TrustAnchor(fingerprint_sha256="33" * 32)})
        report = r.validate("a", _well_linked_chain())
        assert report.chain_reaches_anchor
        assert not report.has_violation

    def test_unanchored_chain_flagged(self):
        r = IssuerResolver(anchors={"a": TrustAnchor(subject="CN=Other Root", fingerprint_sha256="ff" * 32)})
        report = r.validate("a", _well_linked_chain())
        assert report.has_violation
        assert report.unanchored_chain
        assert report.broken_at == -1

    def test_broken_chain_flagged(self):
        r = IssuerResolver(anchors={"a": TrustAnchor(subject="CN=Contoso Root CA")})
        chain = _well_linked_chain()
        # Break: middle link's issuer no longer matches the root's subject.
        chain[1]["issuer"] = "CN=Phantom CA"
        report = r.validate("a", chain)
        assert report.has_violation
        assert report.broken_at == 1
        assert not report.chain_reaches_anchor

    def test_missing_declaration_is_violation(self):
        r = IssuerResolver(anchors={})
        report = r.validate("phantom", _well_linked_chain())
        assert report.has_violation
        assert report.missing_declaration

    def test_empty_chain_is_in_scope(self):
        r = IssuerResolver(anchors={"a": TrustAnchor(subject="CN=Anchor")})
        report = r.validate("a", [])
        assert not report.has_violation
        assert report.chain == ()

    def test_validate_many(self):
        r = IssuerResolver(
            anchors={
                "ok": TrustAnchor(subject="CN=Contoso Root CA"),
                "bad": TrustAnchor(subject="CN=Other"),
            }
        )
        results = r.validate_many(
            {
                "ok": _well_linked_chain(),
                "bad": _well_linked_chain(),
                "missing": _well_linked_chain(),
            }
        )
        by_id = {x.adapter_id: x for x in results}
        assert not by_id["ok"].has_violation
        assert by_id["bad"].unanchored_chain
        assert by_id["missing"].missing_declaration

    def test_as_drift_state_returns_none_when_clean(self, provenance):
        r = IssuerResolver(anchors={"a": TrustAnchor(subject="CN=Contoso Root CA")})
        report = r.validate("a", _well_linked_chain())
        assert report.as_drift_state(provenance=provenance) is None

    def test_as_drift_state_for_broken_chain(self, provenance):
        r = IssuerResolver(anchors={"a": TrustAnchor(subject="CN=Contoso Root CA")})
        chain = _well_linked_chain()
        chain[1]["issuer"] = "CN=Phantom CA"
        report = r.validate("a", chain)
        ds = report.as_drift_state(provenance=provenance)
        assert ds is not None
        assert ds.drift_class == "DRIFT-IDENTITY"
        assert ds.classification == "unauthorized"
        assert ds.resource_id == "adapter:a"
        reasons = ds.delta.get("issuer_chain_reasons", [])
        assert any("Phantom CA" in r for r in reasons)

    def test_as_drift_state_for_unanchored_chain(self, provenance):
        r = IssuerResolver(anchors={"a": TrustAnchor(subject="CN=Other Root")})
        report = r.validate("a", _well_linked_chain())
        ds = report.as_drift_state(provenance=provenance)
        assert ds is not None
        reasons = ds.delta.get("issuer_chain_reasons", [])
        assert any("does not match declared trust anchor" in r for r in reasons)

    def test_as_drift_state_for_missing_declaration(self, provenance):
        r = IssuerResolver(anchors={})
        report = r.validate("phantom", _well_linked_chain())
        ds = report.as_drift_state(provenance=provenance)
        assert ds is not None
        reasons = ds.delta.get("issuer_chain_reasons", [])
        assert any("no trust-anchor:" in r for r in reasons)

    def test_report_as_dict_round_trips_through_json(self):
        r = IssuerResolver(anchors={"a": TrustAnchor(subject="CN=Contoso Root CA")})
        report = r.validate("a", _well_linked_chain())
        d = report.as_dict()
        roundtrip = json.loads(json.dumps(d))
        assert roundtrip["chain_reaches_anchor"] is True
        assert roundtrip["adapter_id"] == "a"


# ---------------------------------------------------------------------------
# observed_chain_for_run — scheduler-run extraction helper
# ---------------------------------------------------------------------------


def _write_evidence(adapter_dir: Path, payload: dict) -> None:
    adapter_dir.mkdir(parents=True, exist_ok=True)
    (adapter_dir / "evidence.json").write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


class TestObservedChainForRun:
    def test_missing_run_dir_returns_empty(self, tmp_path):
        assert observed_chain_for_run(tmp_path / "nope") == {}

    def test_extracts_normalized_certificate_chain(self, tmp_path):
        run = tmp_path / "schedrun-x"
        _write_evidence(
            run / "adapters" / "entra-id",
            {"normalized_data": {"certificate_chain": _well_linked_chain()}},
        )
        out = observed_chain_for_run(run)
        assert len(out["entra-id"]) == 3
        assert out["entra-id"][0]["subject"] == "CN=service.contoso.com"

    def test_falls_back_to_raw_data(self, tmp_path):
        run = tmp_path / "schedrun-y"
        _write_evidence(
            run / "adapters" / "scubagear",
            {"raw_data": {"issuer_chain": _well_linked_chain()}},
        )
        out = observed_chain_for_run(run)
        assert len(out["scubagear"]) == 3

    def test_empty_when_no_chain_field(self, tmp_path):
        run = tmp_path / "schedrun-z"
        _write_evidence(
            run / "adapters" / "quiet",
            {"normalized_data": {"probe": True}},
        )
        assert observed_chain_for_run(run) == {"quiet": []}

    def test_round_trips_through_resolver(self, tmp_path, provenance):
        run = tmp_path / "schedrun-e2e"
        _write_evidence(
            run / "adapters" / "rogue",
            {"normalized_data": {"certificate_chain": _well_linked_chain()}},
        )
        observed = observed_chain_for_run(run)
        resolver = IssuerResolver(anchors={"rogue": TrustAnchor(subject="CN=Adversary Root")})
        report = resolver.validate("rogue", observed["rogue"])
        ds = report.as_drift_state(provenance=provenance)
        assert ds is not None
        assert ds.drift_class == "DRIFT-IDENTITY"


# ---------------------------------------------------------------------------
# CertificateLink coercion
# ---------------------------------------------------------------------------


class TestCertificateLink:
    def test_from_dict_lowercases_fingerprint(self):
        link = CertificateLink.from_dict({"subject": "CN=A", "issuer": "CN=B", "fingerprint_sha256": "ABCDEF"})
        assert link.fingerprint_sha256 == "abcdef"

    def test_from_dict_handles_missing_keys(self):
        link = CertificateLink.from_dict({})
        assert link.subject == ""
        assert link.issuer == ""
        assert link.fingerprint_sha256 == ""


# ---------------------------------------------------------------------------
# Substrate walker — registry-hygiene scan
# ---------------------------------------------------------------------------


class TestSubstrateWalkerIssuerChain:
    def test_active_adapter_anchored_no_trust_anchor_is_p1(self, tmp_path):
        canon = tmp_path / "src" / "uiao" / "canon"
        canon.mkdir(parents=True)
        (canon / "substrate-manifest.yaml").write_text(yaml.safe_dump({"modules": []}), encoding="utf-8")
        (canon / "modernization-registry.yaml").write_text(
            yaml.safe_dump(
                {
                    "adapters": [
                        {
                            "id": "anchored-no-anchor",
                            "status": "active",
                            "scope": ["x"],
                            "certificate-anchored": True,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        from uiao.substrate.walker import walk_substrate

        report = walk_substrate(workspace_root=tmp_path)
        ident = [f for f in report.findings if f.drift_class == "DRIFT-IDENTITY"]
        assert len(ident) == 1
        assert ident[0].severity == "P1"
        assert "anchored-no-anchor" in ident[0].path
        assert "trust-anchor" in ident[0].detail.lower()

    def test_active_adapter_anchored_with_trust_anchor_clean(self, tmp_path):
        canon = tmp_path / "src" / "uiao" / "canon"
        canon.mkdir(parents=True)
        (canon / "substrate-manifest.yaml").write_text(yaml.safe_dump({"modules": []}), encoding="utf-8")
        (canon / "modernization-registry.yaml").write_text(
            yaml.safe_dump(
                {
                    "adapters": [
                        {
                            "id": "good",
                            "status": "active",
                            "scope": ["x"],
                            "certificate-anchored": True,
                            "trust-anchor": {"subject": "CN=Root"},
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        from uiao.substrate.walker import walk_substrate

        report = walk_substrate(workspace_root=tmp_path)
        ident = [f for f in report.findings if f.drift_class == "DRIFT-IDENTITY"]
        assert ident == []

    def test_certificate_anchored_false_skipped(self, tmp_path):
        canon = tmp_path / "src" / "uiao" / "canon"
        canon.mkdir(parents=True)
        (canon / "substrate-manifest.yaml").write_text(yaml.safe_dump({"modules": []}), encoding="utf-8")
        (canon / "modernization-registry.yaml").write_text(
            yaml.safe_dump(
                {
                    "adapters": [
                        {
                            "id": "not-anchored",
                            "status": "active",
                            "scope": ["x"],
                            "certificate-anchored": False,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        from uiao.substrate.walker import walk_substrate

        report = walk_substrate(workspace_root=tmp_path)
        ident = [f for f in report.findings if f.drift_class == "DRIFT-IDENTITY"]
        assert ident == []

    def test_reserved_adapter_skipped(self, tmp_path):
        canon = tmp_path / "src" / "uiao" / "canon"
        canon.mkdir(parents=True)
        (canon / "substrate-manifest.yaml").write_text(yaml.safe_dump({"modules": []}), encoding="utf-8")
        (canon / "modernization-registry.yaml").write_text(
            yaml.safe_dump(
                {
                    "adapters": [
                        {
                            "id": "future",
                            "status": "reserved",
                            "certificate-anchored": True,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        from uiao.substrate.walker import walk_substrate

        report = walk_substrate(workspace_root=tmp_path)
        ident = [f for f in report.findings if f.drift_class == "DRIFT-IDENTITY"]
        assert ident == []

    def test_real_canon_no_drift_identity_findings(self):
        """Live canon smoke: every active certificate-anchored adapter
        declares a trust-anchor:, so the now-blocking P1 gate stays
        clean. Regressing this test means an adapter lost its anchor
        declaration and the substrate's runtime issuer-chain validator
        can no longer be enforced against it."""
        from uiao.substrate.walker import walk_substrate

        report = walk_substrate()
        ident = [f for f in report.findings if f.drift_class == "DRIFT-IDENTITY"]
        assert ident == [], f"Live canon has DRIFT-IDENTITY findings: {ident}"
