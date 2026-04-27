"""Tests for UIAO_105 / §3.1 Auditor API v1 routers (ZTMM, EPL,
Enforcement, Archive).

These tests build a minimal FastAPI app with just the §3.1 routers
attached so the test surface stays decoupled from the larger Windows-
hosted ``uiao.api.app`` (which pulls in MSAL / kerberos auth + other
machinery that doesn't matter here).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI

pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

from uiao.api.routes import archive, enforcement, epl, ztmm  # noqa: E402
from uiao.governance.enforcement import EnforcementAction, EnforcementJournal  # noqa: E402
from uiao.governance.epl import EPLAction  # noqa: E402
from uiao.storage.data_lake import (  # noqa: E402
    ArchiveManager,
    FilesystemArchive,
    RetentionPolicy,
)


AUTH_HEADERS = {"Authorization": "Bearer test-token"}


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(ztmm.router, prefix="/api/v1/ztmm")
    app.include_router(epl.router, prefix="/api/v1/epl")
    app.include_router(enforcement.router, prefix="/api/v1/enforcement")
    app.include_router(archive.router, prefix="/api/v1/archive")
    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(_make_app())


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class TestAuth:
    def test_no_bearer_returns_401(self, client):
        # Hitting any endpoint without auth → 401.
        r = client.get("/api/v1/ztmm")
        assert r.status_code == 401

    def test_empty_bearer_returns_401(self, client):
        r = client.get("/api/v1/ztmm", headers={"Authorization": "Bearer "})
        assert r.status_code == 401

    def test_dev_token_accepted(self, client):
        r = client.get("/api/v1/ztmm", headers=AUTH_HEADERS)
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# ZTMM
# ---------------------------------------------------------------------------


class TestZTMMRouter:
    def test_full_report_shape(self, client):
        r = client.get("/api/v1/ztmm", headers=AUTH_HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert "scores" in body
        assert "overall_rank" in body
        # All five canonical pillars present.
        for pillar in (
            "identity",
            "devices",
            "networks",
            "applications-and-workloads",
            "data",
        ):
            assert pillar in body["scores"]

    def test_single_pillar(self, client):
        r = client.get("/api/v1/ztmm/identity", headers=AUTH_HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert body["pillar"] == "identity"
        assert "maturity" in body

    def test_synonym_pillar_resolves(self, client):
        # "endpoints" → DEVICES
        r = client.get("/api/v1/ztmm/endpoints", headers=AUTH_HEADERS)
        assert r.status_code == 200
        assert r.json()["pillar"] == "devices"

    def test_unknown_pillar_404(self, client):
        r = client.get("/api/v1/ztmm/phantom", headers=AUTH_HEADERS)
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# EPL
# ---------------------------------------------------------------------------


class TestEPLRouter:
    def test_list_policies_returns_canonical_set(self, client):
        r = client.get("/api/v1/epl/policies", headers=AUTH_HEADERS)
        assert r.status_code == 200
        body = r.json()
        ids = {p["id"] for p in body["policies"]}
        # Five canonical refs shipped in §3.5.
        assert "epl:enforce-mfa" in ids
        assert "epl:block-out-of-scope" in ids

    def test_get_policy_by_id(self, client):
        r = client.get("/api/v1/epl/policies/epl:enforce-mfa", headers=AUTH_HEADERS)
        assert r.status_code == 200
        assert r.json()["id"] == "epl:enforce-mfa"

    def test_unknown_policy_404(self, client):
        r = client.get("/api/v1/epl/policies/epl:phantom", headers=AUTH_HEADERS)
        assert r.status_code == 404

    def test_evaluate_drift_authz_matches_block_policy(self, client):
        r = client.post(
            "/api/v1/epl/evaluate",
            headers=AUTH_HEADERS,
            json={
                "drift_class": "DRIFT-AUTHZ",
                "controls": ["AC-2"],
                "adapter_id": "rogue",
                "severity": "High",
            },
        )
        assert r.status_code == 200
        body = r.json()
        ids = {m["policy_id"] for m in body["matches"]}
        assert "epl:block-out-of-scope" in ids

    def test_evaluate_no_match_returns_zero(self, client):
        r = client.post(
            "/api/v1/epl/evaluate",
            headers=AUTH_HEADERS,
            json={
                "drift_class": "DRIFT-PROVENANCE",
                "severity": "Low",
            },
        )
        assert r.status_code == 200
        assert r.json()["matched"] == 0


# ---------------------------------------------------------------------------
# Enforcement
# ---------------------------------------------------------------------------


class TestEnforcementRouter:
    def test_journal_empty_when_no_path_or_records(self, tmp_path, client, monkeypatch):
        monkeypatch.setenv("UIAO_ENFORCEMENT_JOURNAL_PATH", str(tmp_path / "j.jsonl"))
        r = client.get("/api/v1/enforcement/journal", headers=AUTH_HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert body["count"] == 0

    def test_journal_lists_existing_records(self, tmp_path, client, monkeypatch):
        path = tmp_path / "j.jsonl"
        journal = EnforcementJournal(path=path)
        journal.record(
            EnforcementAction(
                policy_id="epl:t",
                action=EPLAction.LOG,
                actor="x",
                sla_hours=0,
                target="AC-2",
                dispatched_at="2026-04-26T00:00:00+00:00",
                status="dispatched",
            )
        )
        monkeypatch.setenv("UIAO_ENFORCEMENT_JOURNAL_PATH", str(path))
        r = client.get("/api/v1/enforcement/journal", headers=AUTH_HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert body["count"] == 1
        assert body["records"][0]["policy_id"] == "epl:t"

    def test_journal_filters(self, tmp_path, client, monkeypatch):
        path = tmp_path / "j.jsonl"
        j = EnforcementJournal(path=path)
        for pid in ("epl:a", "epl:b"):
            j.record(
                EnforcementAction(
                    policy_id=pid,
                    action=EPLAction.LOG,
                    actor="x",
                    sla_hours=0,
                    target="t",
                    dispatched_at="2026-04-26T00:00:00+00:00",
                    status="dispatched",
                )
            )
        monkeypatch.setenv("UIAO_ENFORCEMENT_JOURNAL_PATH", str(path))
        r = client.get(
            "/api/v1/enforcement/journal?policy_id=epl:a",
            headers=AUTH_HEADERS,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["count"] == 1
        assert body["records"][0]["policy_id"] == "epl:a"

    def test_dispatch_appends_to_journal(self, tmp_path, client, monkeypatch):
        path = tmp_path / "j.jsonl"
        monkeypatch.setenv("UIAO_ENFORCEMENT_JOURNAL_PATH", str(path))
        r = client.post(
            "/api/v1/enforcement/dispatch",
            headers=AUTH_HEADERS,
            json={
                "drift_class": "DRIFT-AUTHZ",
                "adapter_id": "rogue",
                "severity": "High",
            },
        )
        assert r.status_code == 200
        body = r.json()
        # Canonical block-out-of-scope policy fires + lands in journal.
        assert body["dispatched"] >= 1
        ids = {a["policy_id"] for a in body["actions"]}
        assert "epl:block-out-of-scope" in ids
        # Read the journal back via the API.
        r2 = client.get("/api/v1/enforcement/journal", headers=AUTH_HEADERS)
        assert any(rec["policy_id"] == "epl:block-out-of-scope" for rec in r2.json()["records"])


# ---------------------------------------------------------------------------
# Archive
# ---------------------------------------------------------------------------


class TestArchiveRouter:
    def _seed(self, tmp_path: Path) -> Path:
        run_dir = tmp_path / "schedrun-x"
        adapters = run_dir / "adapters"
        adapters.mkdir(parents=True)
        for adapter_id in ("entra-id", "scuba"):
            d = adapters / adapter_id
            d.mkdir()
            (d / "evidence.json").write_text(
                json.dumps({"source": adapter_id, "evidence_class": "baseline"}),
                encoding="utf-8",
            )
        return run_dir

    def test_empty_archive_lists_zero(self, tmp_path, client, monkeypatch):
        monkeypatch.setenv("UIAO_ARCHIVE_ROOT", str(tmp_path / "lake"))
        r = client.get("/api/v1/archive", headers=AUTH_HEADERS)
        assert r.status_code == 200
        assert r.json()["count"] == 0

    def test_lists_archived_runs(self, tmp_path, client, monkeypatch):
        run = self._seed(tmp_path)
        lake = tmp_path / "lake"
        mgr = ArchiveManager(
            backend=FilesystemArchive(root=lake),
            policies={"entra-id": RetentionPolicy(adapter_id="entra-id", retention_years=7)},
        )
        mgr.archive_run(run, now=datetime(2026, 4, 26, tzinfo=timezone.utc))
        monkeypatch.setenv("UIAO_ARCHIVE_ROOT", str(lake))
        r = client.get("/api/v1/archive", headers=AUTH_HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert body["count"] == 2
        ids = {(e["run_id"], e["adapter_id"]) for e in body["entries"]}
        assert ("schedrun-x", "entra-id") in ids

    def test_filter_by_adapter(self, tmp_path, client, monkeypatch):
        run = self._seed(tmp_path)
        lake = tmp_path / "lake"
        ArchiveManager(backend=FilesystemArchive(root=lake)).archive_run(run)
        monkeypatch.setenv("UIAO_ARCHIVE_ROOT", str(lake))
        r = client.get("/api/v1/archive?adapter_id=entra-id", headers=AUTH_HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert body["count"] == 1
        assert body["entries"][0]["adapter_id"] == "entra-id"

    def test_get_single_entry(self, tmp_path, client, monkeypatch):
        run = self._seed(tmp_path)
        lake = tmp_path / "lake"
        ArchiveManager(backend=FilesystemArchive(root=lake)).archive_run(run)
        monkeypatch.setenv("UIAO_ARCHIVE_ROOT", str(lake))
        r = client.get("/api/v1/archive/schedrun-x/entra-id", headers=AUTH_HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert body["adapter_id"] == "entra-id"

    def test_unknown_entry_404(self, tmp_path, client, monkeypatch):
        monkeypatch.setenv("UIAO_ARCHIVE_ROOT", str(tmp_path / "lake"))
        r = client.get("/api/v1/archive/phantom-run/phantom-adapter", headers=AUTH_HEADERS)
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# UIAO_119 v2 — tenant_id + environment filter wire-up on /journal + /archive
# ---------------------------------------------------------------------------


class TestJournalTenantFilter:
    def _seed_tagged(self, path, tenant_id: str, environment: str, policy_id: str = "epl:t"):
        from uiao.governance.enforcement import EnforcementAction, EnforcementJournal
        from uiao.governance.epl import EPLAction

        journal = EnforcementJournal(path=path)
        journal.record(
            EnforcementAction(
                policy_id=policy_id,
                action=EPLAction.LOG,
                actor="x",
                sla_hours=0,
                target="t",
                dispatched_at="2026-04-26T00:00:00+00:00",
                status="dispatched",
                extra={"tenant_id": tenant_id, "environment": environment},
            )
        )

    def test_tenant_id_filter(self, tmp_path, client, monkeypatch):
        path = tmp_path / "j.jsonl"
        self._seed_tagged(path, "acme", "stage", policy_id="epl:a")
        self._seed_tagged(path, "umbrella", "stage", policy_id="epl:b")
        monkeypatch.setenv("UIAO_ENFORCEMENT_JOURNAL_PATH", str(path))
        r = client.get(
            "/api/v1/enforcement/journal?tenant_id=acme",
            headers=AUTH_HEADERS,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["count"] == 1
        assert body["records"][0]["policy_id"] == "epl:a"
        # total_unfiltered still reports both records.
        assert body["total_unfiltered"] == 2

    def test_environment_filter(self, tmp_path, client, monkeypatch):
        path = tmp_path / "j.jsonl"
        self._seed_tagged(path, "acme", "dev", policy_id="epl:dev")
        self._seed_tagged(path, "acme", "prod", policy_id="epl:prod")
        monkeypatch.setenv("UIAO_ENFORCEMENT_JOURNAL_PATH", str(path))
        r = client.get(
            "/api/v1/enforcement/journal?environment=prod",
            headers=AUTH_HEADERS,
        )
        body = r.json()
        assert body["count"] == 1
        assert body["records"][0]["policy_id"] == "epl:prod"

    def test_compound_filter(self, tmp_path, client, monkeypatch):
        path = tmp_path / "j.jsonl"
        self._seed_tagged(path, "acme", "dev", policy_id="epl:1")
        self._seed_tagged(path, "acme", "prod", policy_id="epl:2")
        self._seed_tagged(path, "umbrella", "prod", policy_id="epl:3")
        monkeypatch.setenv("UIAO_ENFORCEMENT_JOURNAL_PATH", str(path))
        r = client.get(
            "/api/v1/enforcement/journal?tenant_id=acme&environment=prod",
            headers=AUTH_HEADERS,
        )
        body = r.json()
        assert body["count"] == 1
        assert body["records"][0]["policy_id"] == "epl:2"

    def test_filter_misses_untagged_records(self, tmp_path, client, monkeypatch):
        # Untagged records (extra has no tenant_id key) are excluded
        # when the filter is supplied. The flag-disabled path produces
        # untagged records, so this is the consistent default.
        from uiao.governance.enforcement import EnforcementAction, EnforcementJournal
        from uiao.governance.epl import EPLAction

        path = tmp_path / "j.jsonl"
        journal = EnforcementJournal(path=path)
        journal.record(
            EnforcementAction(
                policy_id="epl:legacy",
                action=EPLAction.LOG,
                actor="x",
                sla_hours=0,
                target="t",
                dispatched_at="2026-04-26T00:00:00+00:00",
                status="dispatched",
            )
        )
        monkeypatch.setenv("UIAO_ENFORCEMENT_JOURNAL_PATH", str(path))
        r = client.get(
            "/api/v1/enforcement/journal?tenant_id=acme",
            headers=AUTH_HEADERS,
        )
        body = r.json()
        assert body["count"] == 0
        # But the unfiltered tally still sees the legacy record.
        assert body["total_unfiltered"] == 1


class TestArchiveTenantFilter:
    def _seed_lake(self, lake_root: Path) -> None:
        # Build the lake by hand so we can plant tagged extras directly.
        from uiao.storage.data_lake import (
            ArchiveEntry,
            FilesystemArchive,
        )

        backend = FilesystemArchive(root=lake_root)
        for run, aid, tenant, env in [
            ("r1", "entra-id", "acme", "stage"),
            ("r2", "entra-id", "umbrella", "stage"),
            ("r3", "scuba", "acme", "prod"),
        ]:
            backend.write_index(
                ArchiveEntry(
                    run_id=run,
                    adapter_id=aid,
                    archived_at="2026-04-26T00:00:00+00:00",
                    retention_until="2030-04-26T00:00:00+00:00",
                    archive_path=f"/lake/{aid}/{run}",
                    extra={"tenant_id": tenant, "environment": env},
                )
            )

    def test_tenant_id_filter(self, tmp_path, client, monkeypatch):
        lake = tmp_path / "lake"
        self._seed_lake(lake)
        monkeypatch.setenv("UIAO_ARCHIVE_ROOT", str(lake))
        r = client.get("/api/v1/archive?tenant_id=acme", headers=AUTH_HEADERS)
        body = r.json()
        assert body["count"] == 2
        assert {e["run_id"] for e in body["entries"]} == {"r1", "r3"}

    def test_environment_filter(self, tmp_path, client, monkeypatch):
        lake = tmp_path / "lake"
        self._seed_lake(lake)
        monkeypatch.setenv("UIAO_ARCHIVE_ROOT", str(lake))
        r = client.get("/api/v1/archive?environment=prod", headers=AUTH_HEADERS)
        body = r.json()
        assert body["count"] == 1
        assert body["entries"][0]["run_id"] == "r3"

    def test_compound_filter(self, tmp_path, client, monkeypatch):
        lake = tmp_path / "lake"
        self._seed_lake(lake)
        monkeypatch.setenv("UIAO_ARCHIVE_ROOT", str(lake))
        r = client.get(
            "/api/v1/archive?tenant_id=acme&environment=stage",
            headers=AUTH_HEADERS,
        )
        body = r.json()
        assert body["count"] == 1
        assert body["entries"][0]["run_id"] == "r1"

    def test_filter_misses_untagged_entries(self, tmp_path, client, monkeypatch):
        from uiao.storage.data_lake import ArchiveEntry, FilesystemArchive

        lake = tmp_path / "lake"
        backend = FilesystemArchive(root=lake)
        backend.write_index(
            ArchiveEntry(
                run_id="legacy",
                adapter_id="a",
                archived_at="2026-04-26T00:00:00+00:00",
                retention_until="2030-04-26T00:00:00+00:00",
                archive_path="/x",
            )
        )
        monkeypatch.setenv("UIAO_ARCHIVE_ROOT", str(lake))
        r = client.get("/api/v1/archive?tenant_id=acme", headers=AUTH_HEADERS)
        body = r.json()
        assert body["count"] == 0
