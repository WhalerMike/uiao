"""Tests for `uiao tenant promote-preview` (UIAO_119 wave 2 consumer)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from uiao.cli.app import app
from uiao.cli.tenant import PROD_PROMOTE_FLAG


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def tmp_canon(tmp_path: Path, monkeypatch) -> Path:
    """Build a synthetic canon overlay and point the loader at it.

    The CLI loads canon via :func:`load_canonical_flags`, which reads
    from ``Path.cwd() / "src/uiao/canon/feature-flags.yaml"`` by default.
    We pin cwd at a tmp_path-rooted workspace.
    """
    canon = tmp_path / "src" / "uiao" / "canon"
    canon.mkdir(parents=True)
    flags = [
        {
            "name": PROD_PROMOTE_FLAG,
            "spec_ref": "test",
            "expires_at": "2030-01-01",
            "environments": ["dev", "stage"],
            "tenant_classes": ["internal"],
        },
        {
            "name": "epl.action.block.enabled",
            "spec_ref": "test",
            "expires_at": "2030-01-01",
            "environments": ["dev", "stage"],
            "tenant_classes": ["internal", "canary"],
        },
        {
            "name": "data-lake.immutable.strict",
            "spec_ref": "test",
            "expires_at": "2030-01-01",
            "environments": ["dev", "stage", "prod"],
            "tenant_classes": ["internal", "canary"],
        },
        {
            "name": "policy.regulated-only-feature",
            "spec_ref": "test",
            "expires_at": "2030-01-01",
            "environments": ["prod"],
            "tenant_classes": ["regulated"],
        },
    ]
    (canon / "feature-flags.yaml").write_text(yaml.safe_dump({"flags": flags}), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# Permission gate
# ---------------------------------------------------------------------------


class TestPromotePreviewPermissions:
    def test_dev_actor_allowed(self, runner: CliRunner, tmp_canon: Path) -> None:
        result = runner.invoke(
            app,
            [
                "tenant",
                "promote-preview",
                "--tenant-id",
                "internal-test",
                "--tenant-class",
                "internal",
                "--from",
                "dev",
                "--to",
                "stage",
            ],
        )
        # exit_code 0 only when there's a non-empty diff. Internal moves
        # dev→stage may be no-op for some flag canons; this test just
        # verifies the permission gate doesn't reject. Exit codes 0 or
        # 1 (no-change) are both "passed the gate"; 2 = denied.
        assert result.exit_code in (0, 1), f"output: {result.output}"

    def test_prod_actor_denied(self, runner: CliRunner, tmp_canon: Path) -> None:
        # Calling from prod with an internal tenant-class context — the
        # gate canon enables prod-promote only in dev / stage, so this
        # is a denial.
        result = runner.invoke(
            app,
            [
                "tenant",
                "promote-preview",
                "--tenant-id",
                "internal-test",
                "--tenant-class",
                "internal",
                "--from",
                "prod",
                "--to",
                "prod",
            ],
        )
        assert result.exit_code == 2
        assert "Permission denied" in result.output

    def test_no_canon_flag_denies(self, runner: CliRunner, tmp_path: Path, monkeypatch) -> None:
        # Empty canon — flag missing — defaults to False.
        canon = tmp_path / "src" / "uiao" / "canon"
        canon.mkdir(parents=True)
        (canon / "feature-flags.yaml").write_text(yaml.safe_dump({"flags": []}), encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app,
            [
                "tenant",
                "promote-preview",
                "--tenant-id",
                "x",
                "--from",
                "dev",
                "--to",
                "stage",
            ],
        )
        assert result.exit_code == 2

    def test_non_internal_operator_class_denied(self, runner: CliRunner, tmp_canon: Path) -> None:
        # Canon enables `tenancy.environment.prod-promote` only for
        # tenant_classes: [internal]. A standard or regulated operator
        # must be denied so the canon policy is actually enforced
        # (regression catch for the bug where the gate's is_enabled
        # was called without a Tenant — silently bypassing the class
        # constraint).
        result = runner.invoke(
            app,
            [
                "tenant",
                "promote-preview",
                "--tenant-id",
                "regulated-tenant",
                "--tenant-class",
                "regulated",
                "--operator-tenant-class",
                "standard",
                "--from",
                "dev",
                "--to",
                "stage",
            ],
        )
        assert result.exit_code == 2, f"output: {result.output}"
        assert "Permission denied" in result.output

    def test_regulated_operator_class_denied(self, runner: CliRunner, tmp_canon: Path) -> None:
        # Same gate behavior for regulated operator class.
        result = runner.invoke(
            app,
            [
                "tenant",
                "promote-preview",
                "--tenant-id",
                "regulated-tenant",
                "--tenant-class",
                "regulated",
                "--operator-tenant-class",
                "regulated",
                "--from",
                "dev",
                "--to",
                "stage",
            ],
        )
        assert result.exit_code == 2
        assert "Permission denied" in result.output


# ---------------------------------------------------------------------------
# Diff output
# ---------------------------------------------------------------------------


class TestPromotePreviewDiff:
    def test_dev_to_stage_no_change(self, runner: CliRunner, tmp_canon: Path) -> None:
        # The synthetic canon enables flags identically in dev and stage
        # for the internal/canary classes — so an internal-class
        # dev→stage promotion is a no-op. Default behavior: exit 1.
        result = runner.invoke(
            app,
            [
                "tenant",
                "promote-preview",
                "--tenant-id",
                "internal-x",
                "--tenant-class",
                "internal",
                "--from",
                "dev",
                "--to",
                "stage",
            ],
        )
        assert result.exit_code == 1
        assert "No flag-evaluation changes" in result.output

    def test_dev_to_stage_no_change_allow_flag(self, runner: CliRunner, tmp_canon: Path) -> None:
        # Same as above but with --allow-no-change → exit 0.
        result = runner.invoke(
            app,
            [
                "tenant",
                "promote-preview",
                "--tenant-id",
                "internal-x",
                "--tenant-class",
                "internal",
                "--from",
                "dev",
                "--to",
                "stage",
                "--allow-no-change",
            ],
        )
        assert result.exit_code == 0

    def test_dev_to_prod_lights_up_prod_only_flags(self, runner: CliRunner, tmp_canon: Path) -> None:
        # Promote a regulated-class tenant from dev → prod. The
        # `policy.regulated-only-feature` flag (env=prod, class=regulated)
        # turns ON; `epl.action.block.enabled` (env=dev/stage only)
        # turns OFF. Operator is in dev so the gate passes.
        result = runner.invoke(
            app,
            [
                "tenant",
                "promote-preview",
                "--tenant-id",
                "regulated-tenant",
                "--tenant-class",
                "regulated",
                "--from",
                "dev",
                "--to",
                "prod",
            ],
        )
        # Operator-side gate is in dev → allowed. The diff is non-empty
        # → exit 0.
        assert result.exit_code == 0, f"output: {result.output}"
        assert "policy.regulated-only-feature" in result.output

    def test_json_output(self, runner: CliRunner, tmp_canon: Path) -> None:
        result = runner.invoke(
            app,
            [
                "tenant",
                "promote-preview",
                "--tenant-id",
                "regulated-tenant",
                "--tenant-class",
                "regulated",
                "--from",
                "dev",
                "--to",
                "prod",
                "--output",
                "json",
            ],
        )
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["before"]["environment"] == "dev"
        assert payload["after"]["environment"] == "prod"
        assert payload["before"]["tenant_id"] == "regulated-tenant"
        assert "added" in payload
        assert "removed" in payload
        assert "is_clean" in payload
