"""Tests for the UIAO Self-Hosted Git Server Adapter (conformance / telemetry)."""

from __future__ import annotations

import pytest

from uiao.adapters.uiao_git_server_adapter import UiaoGitServerAdapter
from uiao.adapters.database_base import (
    ClaimSet,
    ConnectionProvenance,
    DriftReport,
    EvidenceObject,
    QueryProvenance,
    SchemaMappingObject,
)


# --------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------- #


@pytest.fixture
def adapter() -> UiaoGitServerAdapter:
    return UiaoGitServerAdapter(
        {
            "endpoint": "https://git.uiao.corp.contoso.com",
            "auth_method": "token",
            "tls_version": "TLSv1.3",
            "mtls_enabled": True,
        }
    )


@pytest.fixture
def empty_adapter() -> UiaoGitServerAdapter:
    """Adapter constructed with no config — exercises every default."""
    return UiaoGitServerAdapter()


@pytest.fixture
def repos_payload() -> dict:
    """A 3-repo response shaped like Gitea's /api/v1/repos/search."""
    return {
        "ok": True,
        "data": [
            {
                "id": 1,
                "full_name": "uiao/uiao",
                "default_branch": "main",
                "private": True,
                "archived": False,
                "size": 4096,
                "has_signed_commits": True,
            },
            {
                "id": 2,
                "full_name": "uiao/uiao-docs",
                "default_branch": "main",
                "private": True,
                "archived": False,
                "size": 1024,
                "has_signed_commits": False,
            },
            {
                "id": 3,
                "name": "legacy",  # full_name absent — adapter should fall back
                "private": False,
            },
        ],
    }


@pytest.fixture
def version_payload() -> dict:
    return {"version": "1.21.11", "health": "ok", "uptime_seconds": 86400}


@pytest.fixture
def cert_payload() -> dict:
    return {
        "subject": "CN=git.uiao.corp.contoso.com",
        "issuer": "CN=Contoso Issuing CA",
        "not_after": "2027-05-12T00:00:00Z",
        "sha256_fingerprint": "AB:CD:EF:01:23:45",
        "cipher_suite": "TLS_AES_256_GCM_SHA384",
    }


# --------------------------------------------------------------------- #
# Happy path
# --------------------------------------------------------------------- #


class TestBasics:
    def test_adapter_id(self, adapter: UiaoGitServerAdapter) -> None:
        assert adapter.ADAPTER_ID == "uiao-git-server"

    def test_evidence_outputs_contract(self, adapter: UiaoGitServerAdapter) -> None:
        # Must match the `outputs:` block of the adapter-registry entry.
        assert adapter.EVIDENCE_OUTPUTS == (
            "git-server-health.json",
            "git-tls-inventory.json",
            "git-repo-inventory.json",
        )

    def test_connect(self, adapter: UiaoGitServerAdapter) -> None:
        r = adapter.connect()
        assert isinstance(r, ConnectionProvenance)
        assert r.endpoint == "https://git.uiao.corp.contoso.com"
        assert r.mtls_enabled is True
        assert r.tls_version == "TLSv1.3"
        assert "uiao-git-server" in r.identity

    def test_schema(self, adapter: UiaoGitServerAdapter) -> None:
        s = adapter.discover_schema()
        assert isinstance(s, SchemaMappingObject)
        assert "repo.full_name" in s.vendor_schema
        assert "tls.not_after" in s.vendor_schema
        # canonical outputs match the registry contract
        assert s.canonical_schema["outputs"] == [
            "git-server-health.json",
            "git-tls-inventory.json",
            "git-repo-inventory.json",
        ]
        # version_hash is stable across calls (deterministic schema)
        assert adapter.discover_schema().version_hash == s.version_hash

    def test_query_routes_by_scope(self, adapter: UiaoGitServerAdapter) -> None:
        for scope, expect in [
            ("service-health", "/api/v1/version"),
            ("tls-inventory", "/api/v1/settings/ui"),
            ("repo-inventory", "/api/v1/repos/search"),
            ("access-audit", "/api/v1/admin/cron"),
        ]:
            r = adapter.execute_query({"from": scope})
            assert isinstance(r, QueryProvenance)
            assert expect in r.vendor_query

    def test_query_unknown_scope_falls_back(
        self, adapter: UiaoGitServerAdapter
    ) -> None:
        r = adapter.execute_query({"from": "nonexistent"})
        # Default fallback is the version endpoint
        assert "/api/v1/version" in r.vendor_query

    def test_drift(self, adapter: UiaoGitServerAdapter) -> None:
        d = adapter.detect_drift()
        assert isinstance(d, DriftReport)
        assert d.drift_type == "git-server-posture"
        assert d.details["endpoint"] == "https://git.uiao.corp.contoso.com"


class TestNormalization:
    def test_normalize_empty(self, adapter: UiaoGitServerAdapter) -> None:
        cs = adapter.normalize([])
        assert isinstance(cs, ClaimSet)
        assert cs.claims == []

    def test_normalize_three_repos(
        self, adapter: UiaoGitServerAdapter, repos_payload: dict
    ) -> None:
        cs = adapter.normalize(repos_payload["data"])
        assert len(cs.claims) == 3
        # full_name preserved when present
        assert cs.claims[0].fields["full_name"] == "uiao/uiao"
        assert cs.claims[0].fields["has_signed_commits"] is True
        # legacy entry without full_name falls back to name
        assert cs.claims[2].fields["full_name"] == "legacy"
        # private defaults to True when omitted (defense in depth)
        assert cs.claims[2].fields["private"] is False  # explicit False in payload
        # provenance hash present for every claim
        for c in cs.claims:
            assert c.provenance_hash
            assert c.source == "uiao-git-server"

    def test_normalize_handles_completely_missing_fields(
        self, adapter: UiaoGitServerAdapter
    ) -> None:
        cs = adapter.normalize([{}])
        assert len(cs.claims) == 1
        # No raises; defaults applied.
        assert cs.claims[0].fields["full_name"] == "unknown"
        assert cs.claims[0].fields["default_branch"] == "main"
        assert cs.claims[0].fields["private"] is True
        assert cs.claims[0].fields["size_kb"] == 0


# --------------------------------------------------------------------- #
# Evidence shaping (the three registry outputs)
# --------------------------------------------------------------------- #


class TestEvidenceShapes:
    def test_service_health_shape(
        self, adapter: UiaoGitServerAdapter, version_payload: dict
    ) -> None:
        out = adapter.shape_service_health(version_payload)
        assert out["adapter_id"] == "uiao-git-server"
        assert out["gitea_version"] == "1.21.11"
        assert out["uptime_seconds"] == 86400
        assert out["service_health"] == "ok"
        assert "timestamp" in out

    def test_service_health_handles_missing_payload(
        self, adapter: UiaoGitServerAdapter
    ) -> None:
        out = adapter.shape_service_health(None)
        assert out["gitea_version"] == "unknown"
        assert out["uptime_seconds"] == 0

    def test_tls_inventory_shape(
        self, adapter: UiaoGitServerAdapter, cert_payload: dict
    ) -> None:
        out = adapter.shape_tls_inventory(cert_payload)
        assert out["subject"] == "CN=git.uiao.corp.contoso.com"
        assert out["sha256_fingerprint"] == "AB:CD:EF:01:23:45"
        assert out["tls_version"] == "TLSv1.3"
        assert out["mtls_enabled"] is True
        assert out["cipher_suite"] == "TLS_AES_256_GCM_SHA384"

    def test_tls_inventory_with_no_cert(
        self, adapter: UiaoGitServerAdapter
    ) -> None:
        out = adapter.shape_tls_inventory(None)
        # Empty defaults; never raises.
        assert out["subject"] == ""
        assert out["issuer"] == ""
        assert out["sha256_fingerprint"] == ""

    def test_repo_inventory_shape(
        self, adapter: UiaoGitServerAdapter, repos_payload: dict
    ) -> None:
        out = adapter.shape_repo_inventory(repos_payload)
        assert out["repo_count"] == 3
        assert out["signed_commits_repos"] == 1
        assert len(out["claims"]["claims"]) == 3

    def test_repo_inventory_empty_payload(
        self, adapter: UiaoGitServerAdapter
    ) -> None:
        out = adapter.shape_repo_inventory({"data": []})
        assert out["repo_count"] == 0
        assert out["signed_commits_repos"] == 0

    def test_emit_evidence_produces_all_three_outputs(
        self,
        adapter: UiaoGitServerAdapter,
        version_payload: dict,
        cert_payload: dict,
        repos_payload: dict,
    ) -> None:
        bundle = adapter.emit_evidence(
            version_payload=version_payload,
            cert_payload=cert_payload,
            repos_payload=repos_payload,
        )
        # Filenames match the registry contract exactly
        assert set(bundle.keys()) == {
            "git-server-health.json",
            "git-tls-inventory.json",
            "git-repo-inventory.json",
        }
        # Each output is a non-empty dict
        for filename, content in bundle.items():
            assert isinstance(content, dict)
            assert content["adapter_id"] == "uiao-git-server"
            assert "timestamp" in content


# --------------------------------------------------------------------- #
# Evidence bundle + collect_and_align
# --------------------------------------------------------------------- #


class TestEvidenceBundle:
    def test_generate_evidence_bundle(
        self,
        adapter: UiaoGitServerAdapter,
        version_payload: dict,
        cert_payload: dict,
        repos_payload: dict,
    ) -> None:
        ev = adapter.generate_evidence_bundle(
            version_payload, cert_payload, repos_payload
        )
        assert isinstance(ev, EvidenceObject)
        assert ev.source == "uiao-git-server"
        assert ev.ksi_id == "KSI-CM-02-uiao-git-server"
        # raw_data carries all three outputs
        assert set(ev.raw_data["outputs"].keys()) == {
            "git-server-health.json",
            "git-tls-inventory.json",
            "git-repo-inventory.json",
        }
        assert ev.freshness_valid is True

    def test_evidence_bundle_with_no_inputs(
        self, adapter: UiaoGitServerAdapter
    ) -> None:
        ev = adapter.generate_evidence_bundle()
        assert isinstance(ev, EvidenceObject)
        assert ev.raw_data["outputs"]["git-server-health.json"][
            "gitea_version"
        ] == "unknown"

    def test_collect_and_align(self, adapter: UiaoGitServerAdapter) -> None:
        out = adapter.collect_and_align()
        assert out["adapter_id"] == "uiao-git-server"
        assert out["vendor"] == "Gitea"
        assert out["metadata"]["outputs"] == [
            "git-server-health.json",
            "git-tls-inventory.json",
            "git-repo-inventory.json",
        ]


# --------------------------------------------------------------------- #
# Failure modes — empty config, malformed payloads, network-shaped errors
# --------------------------------------------------------------------- #


class TestFailureModes:
    def test_empty_config_instantiates(
        self, empty_adapter: UiaoGitServerAdapter
    ) -> None:
        # The registry's conformance check passes empty config to every adapter.
        assert empty_adapter.ADAPTER_ID == "uiao-git-server"
        # default endpoint is the canonical placeholder
        assert (
            empty_adapter.connect().endpoint
            == "https://git.uiao.corp.contoso.com"
        )

    def test_malformed_repos_payload_is_tolerated(
        self, adapter: UiaoGitServerAdapter
    ) -> None:
        # Missing top-level `data` key
        out = adapter.shape_repo_inventory({"unexpected": "shape"})
        assert out["repo_count"] == 0
        # None payload
        out_none = adapter.shape_repo_inventory(None)
        assert out_none["repo_count"] == 0

    def test_partial_repo_records_do_not_crash_normalize(
        self, adapter: UiaoGitServerAdapter
    ) -> None:
        bad = [
            {"full_name": "uiao/ok", "size": 100},
            {"name": "fragment-only"},
            {},  # nothing at all
        ]
        cs = adapter.normalize(bad)
        assert len(cs.claims) == 3
        assert cs.claims[2].fields["full_name"] == "unknown"

    def test_drift_emits_with_no_data(
        self, empty_adapter: UiaoGitServerAdapter
    ) -> None:
        d = empty_adapter.detect_drift()
        assert d.drift_type == "git-server-posture"
        assert d.severity == "info"
