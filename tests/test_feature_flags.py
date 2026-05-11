"""Tests for UIAO_119 v2 feature flags."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from uiao.governance.feature_flags import (
    FeatureFlag,
    FeatureFlagRegistry,
    load_canonical_flags,
    load_flags,
    parse_expiry,
)
from uiao.governance.tenancy import (
    Environment,
    Tenant,
    TenantClass,
    TenantContext,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_flags(path: Path, flags: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"flags": flags}), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# FeatureFlag.is_enabled
# ---------------------------------------------------------------------------


class TestFeatureFlagEvaluation:
    def test_environment_match_no_tenant_enabled(self):
        flag = FeatureFlag(
            name="x",
            enabled_environments=frozenset({Environment.DEV}),
        )
        ctx = TenantContext(tenant_id="acme", environment=Environment.DEV)
        assert flag.is_enabled(ctx) is True

    def test_environment_mismatch_disabled(self):
        flag = FeatureFlag(
            name="x",
            enabled_environments=frozenset({Environment.PROD}),
        )
        ctx = TenantContext(tenant_id="acme", environment=Environment.DEV)
        assert flag.is_enabled(ctx) is False

    def test_tenant_class_gate_enabled(self):
        flag = FeatureFlag(
            name="x",
            enabled_environments=frozenset({Environment.DEV}),
            enabled_tenant_classes=frozenset({TenantClass.INTERNAL, TenantClass.CANARY}),
        )
        ctx = TenantContext(tenant_id="acme", environment=Environment.DEV)
        tenant = Tenant(id="acme", tenant_class=TenantClass.CANARY)
        assert flag.is_enabled(ctx, tenant) is True

    def test_tenant_class_gate_disabled_for_standard(self):
        flag = FeatureFlag(
            name="x",
            enabled_environments=frozenset({Environment.DEV}),
            enabled_tenant_classes=frozenset({TenantClass.INTERNAL}),
        )
        ctx = TenantContext(tenant_id="acme", environment=Environment.DEV)
        tenant = Tenant(id="acme", tenant_class=TenantClass.STANDARD)
        assert flag.is_enabled(ctx, tenant) is False

    def test_actor_override_wins_over_environment(self):
        flag = FeatureFlag(
            name="x",
            enabled_environments=frozenset(),  # no envs by default
            enabled_actors=frozenset({"oid:debug-actor"}),
        )
        ctx = TenantContext(
            tenant_id="acme",
            actor="oid:debug-actor",
            environment=Environment.PROD,
        )
        assert flag.is_enabled(ctx) is True

    def test_tenant_id_override_wins_over_class_gate(self):
        flag = FeatureFlag(
            name="x",
            enabled_environments=frozenset(),  # no envs
            enabled_tenant_classes=frozenset({TenantClass.INTERNAL}),
            enabled_tenant_ids=frozenset({"acme"}),
        )
        ctx = TenantContext(tenant_id="acme", environment=Environment.PROD)
        tenant = Tenant(id="acme", tenant_class=TenantClass.STANDARD)
        assert flag.is_enabled(ctx, tenant) is True

    def test_no_tenant_skips_class_gate(self):
        # Without a resolved Tenant, the class gate is bypassed; only
        # the environment gate (and overrides) decide.
        flag = FeatureFlag(
            name="x",
            enabled_environments=frozenset({Environment.DEV}),
            enabled_tenant_classes=frozenset({TenantClass.INTERNAL}),
        )
        ctx = TenantContext(tenant_id="acme", environment=Environment.DEV)
        assert flag.is_enabled(ctx, tenant=None) is True

    def test_empty_environments_denies_by_default(self):
        flag = FeatureFlag(name="x")  # nothing enabled
        ctx = TenantContext(tenant_id="acme", environment=Environment.DEV)
        assert flag.is_enabled(ctx) is False

    def test_as_dict_round_trips(self):
        flag = FeatureFlag(
            name="x",
            spec_ref="UIAO_119 v2",
            expires_at="2027-01-31",
            enabled_environments=frozenset({Environment.DEV, Environment.STAGE}),
            enabled_tenant_classes=frozenset({TenantClass.INTERNAL}),
            enabled_tenant_ids=frozenset({"acme"}),
            enabled_actors=frozenset({"oid:42"}),
        )
        d = flag.as_dict()
        assert d["name"] == "x"
        assert d["enabled_environments"] == ["dev", "stage"]
        assert d["enabled_tenant_classes"] == ["internal"]


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class TestFeatureFlagRegistry:
    def test_missing_flag_is_disabled(self):
        registry = FeatureFlagRegistry()
        ctx = TenantContext(tenant_id="acme", environment=Environment.DEV)
        assert registry.is_enabled("phantom", ctx) is False

    def test_evaluation_via_registry(self):
        flag = FeatureFlag(
            name="x",
            enabled_environments=frozenset({Environment.DEV}),
        )
        registry = FeatureFlagRegistry(flags={"x": flag})
        ctx = TenantContext(tenant_id="acme", environment=Environment.DEV)
        assert registry.is_enabled("x", ctx) is True


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


class TestLoadFlags:
    def test_missing_file_returns_empty(self, tmp_path):
        registry = load_flags([tmp_path / "nope.yaml"])
        assert registry.flags == {}

    def test_simple_load(self, tmp_path):
        path = _write_flags(
            tmp_path / "f.yaml",
            [
                {
                    "name": "epl.action.block.enabled",
                    "spec_ref": "UIAO_111 §3.3",
                    "expires_at": "2027-01-31",
                    "environments": ["dev", "stage"],
                    "tenant_classes": ["internal", "canary"],
                }
            ],
        )
        registry = load_flags([path])
        flag = registry.get("epl.action.block.enabled")
        assert flag is not None
        assert flag.spec_ref == "UIAO_111 §3.3"
        assert Environment.DEV in flag.enabled_environments
        assert TenantClass.CANARY in flag.enabled_tenant_classes

    def test_later_override(self, tmp_path):
        a = _write_flags(
            tmp_path / "a.yaml",
            [
                {
                    "name": "x",
                    "spec_ref": "v1",
                    "environments": ["dev"],
                }
            ],
        )
        b = _write_flags(
            tmp_path / "b.yaml",
            [
                {
                    "name": "x",
                    "spec_ref": "v2",
                    "environments": ["prod"],
                }
            ],
        )
        registry = load_flags([a, b])
        assert registry.flags["x"].spec_ref == "v2"
        assert Environment.PROD in registry.flags["x"].enabled_environments

    def test_invalid_yaml_skipped(self, tmp_path):
        path = tmp_path / "bad.yaml"
        path.write_text(":: not valid ::", encoding="utf-8")
        assert load_flags([path]).flags == {}

    def test_missing_name_dropped(self, tmp_path):
        path = _write_flags(tmp_path / "f.yaml", [{"environments": ["dev"]}])
        assert load_flags([path]).flags == {}

    def test_unknown_environment_string_falls_back_to_dev(self, tmp_path):
        # Environment.parse falls back to DEV on unknown strings.
        # That is intentional: the loader gives a usable record; the
        # walker emits the hygiene finding for the canon bug.
        path = _write_flags(
            tmp_path / "f.yaml",
            [{"name": "x", "environments": ["phantom"]}],
        )
        registry = load_flags([path])
        flag = registry.flags["x"]
        assert Environment.DEV in flag.enabled_environments


# ---------------------------------------------------------------------------
# Canonical loader
# ---------------------------------------------------------------------------


class TestLoadCanonicalFlags:
    def test_canonical_path_resolves(self, tmp_path):
        canon = tmp_path / "src" / "uiao" / "canon"
        canon.mkdir(parents=True)
        _write_flags(
            canon / "feature-flags.yaml",
            [
                {
                    "name": "x",
                    "spec_ref": "UIAO_119",
                    "expires_at": "2027-01-31",
                    "environments": ["dev"],
                }
            ],
        )
        registry = load_canonical_flags(workspace_root=tmp_path)
        assert registry.get("x") is not None

    def test_live_canonical_flags_load(self):
        # Smoke-test against the real canon file shipped in this repo.
        registry = load_canonical_flags()
        assert "epl.action.block.enabled" in registry.flags
        assert "data-lake.immutable.strict" in registry.flags
        # Every shipped reference flag declares a spec_ref.
        for flag in registry.flags.values():
            assert flag.spec_ref, f"reference flag '{flag.name}' missing spec_ref"


# ---------------------------------------------------------------------------
# parse_expiry
# ---------------------------------------------------------------------------


class TestParseExpiry:
    def test_iso_date(self):
        assert parse_expiry("2027-01-31") == date(2027, 1, 31)

    def test_empty_returns_none(self):
        assert parse_expiry("") is None
        assert parse_expiry("   ") is None

    def test_malformed_returns_none(self):
        assert parse_expiry("January 2027") is None
        assert parse_expiry("2027-13-99") is None


# ---------------------------------------------------------------------------
# Substrate walker hygiene
# ---------------------------------------------------------------------------


class TestWalkerFeatureFlagScan:
    def _scaffold(self, tmp_path: Path, flags: list[dict]) -> Path:
        canon = tmp_path / "src" / "uiao" / "canon"
        canon.mkdir(parents=True)
        (canon / "substrate-manifest.yaml").write_text(yaml.safe_dump({"modules": []}), encoding="utf-8")
        (canon / "feature-flags.yaml").write_text(yaml.safe_dump({"flags": flags}), encoding="utf-8")
        return tmp_path

    def test_missing_spec_ref_p3(self, tmp_path):
        root = self._scaffold(
            tmp_path,
            [{"name": "x", "expires_at": "2027-01-31", "environments": ["dev"]}],
        )
        from uiao.substrate.walker import walk_substrate

        report = walk_substrate(workspace_root=root)
        flag_findings = [f for f in report.findings if "spec_ref" in f.detail]
        assert len(flag_findings) == 1
        assert flag_findings[0].severity == "P3"

    def test_missing_expires_at_p3(self, tmp_path):
        root = self._scaffold(
            tmp_path,
            [{"name": "x", "spec_ref": "UIAO_119", "environments": ["dev"]}],
        )
        from uiao.substrate.walker import walk_substrate

        report = walk_substrate(workspace_root=root)
        flag_findings = [f for f in report.findings if "expires_at" in f.detail]
        assert len(flag_findings) == 1
        assert flag_findings[0].severity == "P3"

    def test_malformed_expires_at_p3(self, tmp_path):
        root = self._scaffold(
            tmp_path,
            [
                {
                    "name": "x",
                    "spec_ref": "UIAO_119",
                    "expires_at": "January 2027",
                    "environments": ["dev"],
                }
            ],
        )
        from uiao.substrate.walker import walk_substrate

        report = walk_substrate(workspace_root=root)
        flag_findings = [f for f in report.findings if "malformed expires_at" in f.detail]
        assert len(flag_findings) == 1
        assert flag_findings[0].severity == "P3"

    def test_unknown_environment_p3(self, tmp_path):
        root = self._scaffold(
            tmp_path,
            [
                {
                    "name": "x",
                    "spec_ref": "UIAO_119",
                    "expires_at": "2027-01-31",
                    "environments": ["phantom"],
                }
            ],
        )
        from uiao.substrate.walker import walk_substrate

        report = walk_substrate(workspace_root=root)
        flag_findings = [f for f in report.findings if "unknown environment" in f.detail]
        assert len(flag_findings) == 1
        assert flag_findings[0].severity == "P3"

    def test_well_formed_flag_clean(self, tmp_path):
        root = self._scaffold(
            tmp_path,
            [
                {
                    "name": "x",
                    "spec_ref": "UIAO_119 §rollout",
                    "expires_at": "2027-01-31",
                    "environments": ["dev", "stage"],
                    "tenant_classes": ["internal"],
                }
            ],
        )
        from uiao.substrate.walker import walk_substrate

        report = walk_substrate(workspace_root=root)
        # No feature-flag findings.
        flag_findings = [f for f in report.findings if "feature flag" in f.detail or "flag '" in f.detail]
        assert flag_findings == []

    def test_no_flags_file_no_findings(self, tmp_path):
        canon = tmp_path / "src" / "uiao" / "canon"
        canon.mkdir(parents=True)
        (canon / "substrate-manifest.yaml").write_text(yaml.safe_dump({"modules": []}), encoding="utf-8")
        from uiao.substrate.walker import walk_substrate

        report = walk_substrate(workspace_root=tmp_path)
        flag_findings = [f for f in report.findings if "feature flag" in f.detail]
        assert flag_findings == []
