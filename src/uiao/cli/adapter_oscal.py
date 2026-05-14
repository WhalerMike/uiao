"""
CLI commands for adapter -> OSCAL artifact generation.

Provides subcommands for generating SAR, POA&M, and SSP from adapter
data. Each command accepts an adapter ID, state/config file paths,
and optional control IDs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

try:
    import typer
    from rich.console import Console

    HAS_TYPER = True
except ImportError:
    HAS_TYPER = False


def _create_app() -> Any:
    """Create the adapter-oscal typer app (deferred to avoid import errors)."""
    if not HAS_TYPER:
        return None

    app = typer.Typer(
        name="adapter-oscal",
        help="Generate OSCAL artifacts (SAR/POA&M/SSP) from adapter data.",
    )
    # `Console(stderr=True)` directs diagnostic output to stderr so the JSON
    # OSCAL document printed by `_write_output` stays the only thing on stdout.
    console = Console(stderr=True)

    @app.command()
    def sar(
        adapter: str = typer.Argument(..., help="Adapter ID (e.g., terraform, m365, palo-alto)"),
        state_file: Path = typer.Argument(..., help="Path to state/config file (JSON/XML)"),
        controls: str = typer.Option("CM-8", help="Comma-separated NIST 800-53 control IDs"),
        system_name: str = typer.Option("UIAO Adapter Assessment", help="System name for SAR metadata"),
        output: Optional[Path] = typer.Option(None, help="Output file (default: stdout)"),
    ) -> None:
        """Generate an OSCAL Assessment Results (SAR) from adapter data."""
        from uiao.adapters.adapter_to_oscal import build_adapter_bundle
        from uiao.generators.sar import build_sar

        claims = _load_adapter_claims(adapter, state_file)
        ctrl_ids = [c.strip() for c in controls.split(",")]

        bundle = build_adapter_bundle(adapter, claims, control_ids=ctrl_ids)
        sar_doc = build_sar(bundle=bundle, system_name=system_name)

        _write_output(sar_doc, output, console)
        console.print(f"[green]SAR generated: {len(bundle.evidence)} observations, controls: {ctrl_ids}[/green]")

    @app.command()
    def poam(
        adapter: str = typer.Argument(..., help="Adapter ID"),
        plan_file: Path = typer.Argument(..., help="Path to plan/drift JSON"),
        controls: str = typer.Option("CM-3", help="Comma-separated control IDs"),
        output: Optional[Path] = typer.Option(None, help="Output file"),
    ) -> None:
        """Generate an OSCAL POA&M from adapter drift data."""
        from uiao.adapters.adapter_to_oscal import build_adapter_poam

        drift = _load_adapter_drift(adapter, plan_file)
        ctrl_ids = [c.strip() for c in controls.split(",")]

        poam_doc = build_adapter_poam(adapter, drift, ctrl_ids)
        _write_output(poam_doc, output, console)
        items = len(poam_doc.get("poam-items", []))
        console.print(f"[green]POA&M generated: {items} item(s)[/green]")

    @app.command()
    def ssp(
        adapter: str = typer.Argument(..., help="Adapter ID"),
        state_file: Path = typer.Argument(..., help="Path to state/config file"),
        controls: str = typer.Option("CM-8", help="Comma-separated control IDs"),
        system_name: str = typer.Option("UIAO System", help="SSP system name"),
        output: Optional[Path] = typer.Option(None, help="Output file"),
    ) -> None:
        """Generate an OSCAL SSP from adapter claims."""
        from uiao.adapters.adapter_to_oscal import build_adapter_ssp

        claims = _load_adapter_claims(adapter, state_file)
        ctrl_ids = [c.strip() for c in controls.split(",")]

        ssp_doc = build_adapter_ssp(adapter, claims, ctrl_ids, system_name)
        _write_output(ssp_doc, output, console)
        reqs = len(
            ssp_doc.get("system-security-plan", {})
            .get("control-implementation", {})
            .get("implemented-requirements", [])
        )
        console.print(f"[green]SSP generated: {reqs} implemented requirement(s)[/green]")

    return app


def _load_adapter_claims(adapter_id: str, state_file: Path) -> Any:
    """Load adapter and extract claims from a state/config file."""
    if adapter_id == "terraform":
        from uiao.adapters.terraform_adapter import TerraformAdapter

        return TerraformAdapter({}).extract_terraform_state(str(state_file))
    elif adapter_id == "m365":
        from uiao.adapters.m365_adapter import M365Adapter
        from uiao.adapters.m365_parser import parse_tenant_config

        config = json.loads(state_file.read_text())
        return M365Adapter({"_tenant_config": config}).normalize(parse_tenant_config(config))
    elif adapter_id == "palo-alto":
        from uiao.adapters.paloalto_adapter import PaloAltoAdapter

        return PaloAltoAdapter({"_security_rules_xml": state_file.read_text()}).get_running_config()
    else:
        raise NotImplementedError(
            f"Generic adapter loading for '{adapter_id}' not yet implemented. Use terraform, m365, or palo-alto."
        )


def _load_adapter_drift(adapter_id: str, plan_file: Path) -> Any:
    """Load drift data from a plan/drift file."""
    from uiao.adapters.terraform_adapter import TerraformAdapter

    plan = json.loads(plan_file.read_text())
    if adapter_id == "terraform":
        return TerraformAdapter({}).consume_terraform_plan(plan)
    else:
        raise NotImplementedError(f"Drift loading for '{adapter_id}' not yet implemented.")


def _write_output(doc: dict, output: Optional[Path], console: Any) -> None:
    """Write JSON output to file or stdout."""
    json_str = json.dumps(doc, indent=2)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json_str)
        console.print(f"[dim]Written to {output}[/dim]")
    else:
        print(json_str)


# Create the app for import by the main CLI
adapter_oscal_app = _create_app()
