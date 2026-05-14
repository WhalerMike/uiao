"""Smoke tests for the `uiao.cli.adapter_oscal` Typer app.

The module exposes ``adapter_oscal_app`` — a standalone Typer
sub-application that turns adapter state/plan inputs into OSCAL
artifacts (SAR / POA&M / SSP). PR #481 surfaced three latent
runtime bugs in this module (the bogus ``console.print(file=...)``
that would have raised ``TypeError`` at runtime, plus two variable-
type narrowing collisions in ``_load_adapter_claims``) that hid
because there was no test coverage. This file locks the fixed
behavior in.

Note: ``adapter_oscal_app`` is currently **not wired** into the
main ``uiao`` CLI surface (``src/uiao/cli/app.py`` does not import
it). The tests invoke it directly via :class:`typer.testing.CliRunner`;
whether to expose ``adapter-oscal`` from the parent app — or delete
the module as dead code — is a separate design question.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from uiao.cli.adapter_oscal import (
    _load_adapter_claims,
    _load_adapter_drift,
    adapter_oscal_app,
)

runner = CliRunner()
FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Fixture paths — point at existing repo corpus, no synthesis needed.
# ---------------------------------------------------------------------------


@pytest.fixture
def terraform_state_path() -> Path:
    return FIXTURES / "terraform.tfstate"


@pytest.fixture
def terraform_plan_path() -> Path:
    return FIXTURES / "terraform-plan.json"


@pytest.fixture
def m365_config_path() -> Path:
    return FIXTURES / "m365-tenant-config.json"


@pytest.fixture
def palo_alto_xml_path() -> Path:
    return FIXTURES / "panos-security-rules.xml"


# ---------------------------------------------------------------------------
# `--help` smoke — validates the Typer app constructs without raising and
# that all three subcommands are reachable. Caught the original
# `console = Console()` constructor crash that #481 fixed (would have
# failed at module import time if regressed).
# ---------------------------------------------------------------------------


class TestHelp:
    def test_app_help_lists_subcommands(self) -> None:
        result = runner.invoke(adapter_oscal_app, ["--help"])
        assert result.exit_code == 0
        # Each of the three commands should be discoverable from --help.
        assert "sar" in result.stdout
        assert "poam" in result.stdout
        assert "ssp" in result.stdout

    @pytest.mark.parametrize("cmd", ["sar", "poam", "ssp"])
    def test_subcommand_help(self, cmd: str) -> None:
        result = runner.invoke(adapter_oscal_app, [cmd, "--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# End-to-end OSCAL emission: each subcommand against terraform fixtures.
# Asserts on the canonical top-level key of each artifact rather than the
# full body so the tests stay stable across future OSCAL skeleton changes.
# ---------------------------------------------------------------------------


class TestSarCommand:
    def test_terraform_state_emits_sar_to_stdout(self, terraform_state_path: Path) -> None:
        result = runner.invoke(adapter_oscal_app, ["sar", "terraform", str(terraform_state_path)])
        assert result.exit_code == 0, result.output
        doc = json.loads(result.stdout)
        assert "assessment-results" in doc

    def test_terraform_state_emits_sar_to_file(self, terraform_state_path: Path, tmp_path: Path) -> None:
        out = tmp_path / "sar.json"
        result = runner.invoke(
            adapter_oscal_app,
            ["sar", "terraform", str(terraform_state_path), "--output", str(out)],
        )
        assert result.exit_code == 0, result.output
        assert out.exists()
        doc = json.loads(out.read_text())
        assert "assessment-results" in doc


class TestPoamCommand:
    def test_terraform_plan_emits_poam_to_stdout(self, terraform_plan_path: Path) -> None:
        result = runner.invoke(adapter_oscal_app, ["poam", "terraform", str(terraform_plan_path)])
        assert result.exit_code == 0, result.output
        doc = json.loads(result.stdout)
        assert "poam-items" in doc


class TestSspCommand:
    def test_terraform_state_emits_ssp_to_stdout(self, terraform_state_path: Path) -> None:
        result = runner.invoke(adapter_oscal_app, ["ssp", "terraform", str(terraform_state_path)])
        assert result.exit_code == 0, result.output
        doc = json.loads(result.stdout)
        assert "system-security-plan" in doc


# ---------------------------------------------------------------------------
# Regression: _load_adapter_claims dispatch across all three adapter ids.
#
# PR #481 fixed a mypy `assignment` error rooted in real code: the function
# reused a single variable `a` across branches, so `a = TerraformAdapter(...)`
# narrowed `a` for the m365/palo-alto branches and the latter's call to
# `a.get_running_config()` would have failed at runtime had it ever been
# reached. The fix restructured the function to construct each adapter
# inline. Exercising all three branches here means any future re-introduction
# of a shared variable that mis-dispatches will fail loudly.
# ---------------------------------------------------------------------------


class TestLoadAdapterDispatch:
    def test_terraform_branch(self, terraform_state_path: Path) -> None:
        claims = _load_adapter_claims("terraform", terraform_state_path)
        assert hasattr(claims, "claims")
        assert len(claims.claims) > 0

    def test_m365_branch(self, m365_config_path: Path) -> None:
        claims = _load_adapter_claims("m365", m365_config_path)
        assert hasattr(claims, "claims")

    def test_palo_alto_branch(self, palo_alto_xml_path: Path) -> None:
        claims = _load_adapter_claims("palo-alto", palo_alto_xml_path)
        # PaloAlto adapter wraps its output as a ClaimSet too (via
        # `get_running_config` which normalizes to the same shape).
        assert hasattr(claims, "claims")

    def test_unknown_adapter_raises(self, terraform_state_path: Path) -> None:
        with pytest.raises(NotImplementedError, match="oracle"):
            _load_adapter_claims("oracle", terraform_state_path)


class TestLoadAdapterDrift:
    def test_terraform_branch(self, terraform_plan_path: Path) -> None:
        drift = _load_adapter_drift("terraform", terraform_plan_path)
        # DriftReport contract (uiao.adapters.database_base): every report
        # carries `drift_type`, `severity`, and `details`.
        assert hasattr(drift, "drift_type")
        assert hasattr(drift, "severity")
        assert hasattr(drift, "details")

    def test_unknown_adapter_raises(self, terraform_plan_path: Path) -> None:
        with pytest.raises(NotImplementedError, match="m365"):
            _load_adapter_drift("m365", terraform_plan_path)
