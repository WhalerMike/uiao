"""Tests for UIAO_112 / §3.4 Multi-Tenant Isolation."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from uiao.governance.tenancy import (
    DEFAULT_TENANT_ID,
    Tenant,
    TenantContext,
    TenantRegistry,
    assert_tenant_match,
    load_tenants,
    tenant_scoped_path,
)


# ---------------------------------------------------------------------------
# Tenant model
# ---------------------------------------------------------------------------


class TestTenantModel:
    def test_defaults(self):
        t = Tenant(id="acme")
        assert t.id == "acme"
        assert t.status == "active"
        assert t.is_active

    def test_inactive_status(self):
        t = Tenant(id="x", status="inactive")
        assert not t.is_active

    def test_as_dict(self):
        t = Tenant(
            id="x",
            name="X Org",
            credential_scope=frozenset({"a", "b"}),
            parent_org="parent",
            retention_years=5,
        )
        d = t.as_dict()
        assert d["id"] == "x"
        assert d["credential_scope"] == ["a", "b"]


# ---------------------------------------------------------------------------
# TenantContext
# ---------------------------------------------------------------------------


class TestTenantContext:
    def test_default(self):
        ctx = TenantContext.default()
        assert ctx.tenant_id == DEFAULT_TENANT_ID
        assert ctx.actor == "system"

    def test_explicit(self):
        ctx = TenantContext(tenant_id="acme", actor="oid:42")
        assert ctx.tenant_id == "acme"


# ---------------------------------------------------------------------------
# Registry loader
# ---------------------------------------------------------------------------


def _write(path: Path, body: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(body), encoding="utf-8")
    return path


class TestLoadTenants:
    def test_missing_file_returns_empty(self, tmp_path):
        registry = load_tenants([tmp_path / "nope.yaml"])
        assert registry.tenants == {}

    def test_simple_load(self, tmp_path):
        path = _write(
            tmp_path / "t.yaml",
            {
                "tenants": [
                    {
                        "id": "acme",
                        "name": "Acme Federal",
                        "credential_scope": ["entra-id", "scuba"],
                        "parent_org": "Acme",
                    },
                    {"id": "umbrella", "credential_scope": ["palo-alto"]},
                ]
            },
        )
        registry = load_tenants([path])
        assert {t.id for t in registry.tenants.values()} == {"acme", "umbrella"}
        assert "entra-id" in registry.tenants["acme"].credential_scope

    def test_later_override(self, tmp_path):
        a = _write(
            tmp_path / "a.yaml",
            {"tenants": [{"id": "x", "credential_scope": ["a"]}]},
        )
        b = _write(
            tmp_path / "b.yaml",
            {"tenants": [{"id": "x", "credential_scope": ["b"]}]},
        )
        registry = load_tenants([a, b])
        assert registry.tenants["x"].credential_scope == frozenset({"b"})

    def test_invalid_yaml_skipped(self, tmp_path):
        path = tmp_path / "bad.yaml"
        path.write_text(":: not valid ::", encoding="utf-8")
        assert load_tenants([path]).tenants == {}

    def test_missing_id_dropped(self, tmp_path):
        path = _write(tmp_path / "t.yaml", {"tenants": [{"name": "no id"}]})
        registry = load_tenants([path])
        assert registry.tenants == {}

    def test_invalid_retention_years_falls_back(self, tmp_path):
        path = _write(
            tmp_path / "t.yaml",
            {"tenants": [{"id": "x", "retention_years": "ages"}]},
        )
        assert load_tenants([path]).tenants["x"].retention_years == 0


# ---------------------------------------------------------------------------
# Registry require / active
# ---------------------------------------------------------------------------


class TestTenantRegistry:
    def test_require_default_synthesizes(self):
        registry = TenantRegistry()
        t = registry.require(DEFAULT_TENANT_ID)
        assert t.id == DEFAULT_TENANT_ID
        assert t.is_active

    def test_require_unknown_raises(self):
        registry = TenantRegistry()
        with pytest.raises(KeyError):
            registry.require("phantom")

    def test_active_filters_inactive(self):
        registry = TenantRegistry(
            tenants={
                "a": Tenant(id="a"),
                "b": Tenant(id="b", status="inactive"),
            }
        )
        ids = {t.id for t in registry.active()}
        assert ids == {"a"}


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


class TestPathHelpers:
    def test_tenant_scoped_path_default(self):
        assert tenant_scoped_path("/lake", None) == Path("/lake/default")

    def test_tenant_scoped_path_explicit(self):
        ctx = TenantContext(tenant_id="acme")
        assert tenant_scoped_path("/lake", ctx) == Path("/lake/acme")

    def test_tenant_scoped_path_empty_id_falls_back(self):
        ctx = TenantContext(tenant_id="")
        assert tenant_scoped_path("/lake", ctx) == Path("/lake/default")


# ---------------------------------------------------------------------------
# assert_tenant_match
# ---------------------------------------------------------------------------


class TestAssertTenantMatch:
    def test_matching_contexts_pass(self):
        a = TenantContext(tenant_id="acme")
        b = TenantContext(tenant_id="acme", actor="other")
        assert_tenant_match(a, b)  # no raise

    def test_mismatch_raises(self):
        with pytest.raises(PermissionError):
            assert_tenant_match(
                TenantContext(tenant_id="acme"),
                TenantContext(tenant_id="umbrella"),
            )

    def test_default_when_either_none(self):
        # Default tenant on either side passes against default on the other.
        assert_tenant_match(None, None)
        assert_tenant_match(TenantContext.default(), None)


# ---------------------------------------------------------------------------
# Substrate walker hygiene scan
# ---------------------------------------------------------------------------


class TestWalkerTenantScan:
    def _scaffold(self, tmp_path: Path, tenants: list[dict]) -> Path:
        canon = tmp_path / "src" / "uiao" / "canon"
        canon.mkdir(parents=True)
        (canon / "substrate-manifest.yaml").write_text(yaml.safe_dump({"modules": []}), encoding="utf-8")
        (canon / "tenants.yaml").write_text(yaml.safe_dump({"tenants": tenants}), encoding="utf-8")
        return tmp_path

    def test_active_tenant_no_credential_scope_p2(self, tmp_path):
        root = self._scaffold(tmp_path, [{"id": "acme", "status": "active"}])
        from uiao.substrate.walker import walk_substrate

        report = walk_substrate(workspace_root=root)
        tenant_findings = [f for f in report.findings if "credential_scope" in f.detail]
        assert len(tenant_findings) == 1
        assert tenant_findings[0].severity == "P2"

    def test_active_tenant_with_scope_clean(self, tmp_path):
        root = self._scaffold(
            tmp_path,
            [
                {
                    "id": "acme",
                    "status": "active",
                    "credential_scope": ["entra-id"],
                }
            ],
        )
        from uiao.substrate.walker import walk_substrate

        report = walk_substrate(workspace_root=root)
        tenant_findings = [f for f in report.findings if "credential_scope" in f.detail]
        assert tenant_findings == []

    def test_inactive_tenant_skipped(self, tmp_path):
        root = self._scaffold(tmp_path, [{"id": "old", "status": "inactive"}])
        from uiao.substrate.walker import walk_substrate

        report = walk_substrate(workspace_root=root)
        tenant_findings = [f for f in report.findings if "credential_scope" in f.detail]
        assert tenant_findings == []

    def test_no_tenants_file_no_findings(self, tmp_path):
        # Without tenants.yaml the scan returns zero findings — single-
        # tenant deployments don't require a declaration file.
        canon = tmp_path / "src" / "uiao" / "canon"
        canon.mkdir(parents=True)
        (canon / "substrate-manifest.yaml").write_text(yaml.safe_dump({"modules": []}), encoding="utf-8")
        from uiao.substrate.walker import walk_substrate

        report = walk_substrate(workspace_root=tmp_path)
        tenant_findings = [f for f in report.findings if "credential_scope" in f.detail]
        assert tenant_findings == []
