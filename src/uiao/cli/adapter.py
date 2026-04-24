"""uiao.cli.adapter — Typer sub-app for the `uiao adapter` command group.

Mount point
-----------
    # in uiao/cli/app.py
    from uiao.cli.adapter import adapter_app
    app.add_typer(adapter_app, name="adapter")

Usage (after `pip install -e .`)
---------------------------------
    uiao adapter run servicenow --output exports/alignment.json
    uiao adapter run-scuba exports/scuba/M365BaselineConformance.json

Or via module invocation:
    python -m uiao.cli adapter run servicenow
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

adapter_app = typer.Typer(
    name="adapter",
    help="Vendor adapter operations (claim alignment, ScubaGear ingestion).",
    add_completion=False,
)

_console = Console()


@adapter_app.command("run")
def adapter_run(
    vendor: str = typer.Argument(..., help="Vendor adapter name (servicenow, entra)."),
    output: str = typer.Option(
        "",
        "--output",
        "-o",
        help="Optional JSON output path for alignment results.",
    ),
) -> None:
    """Run a vendor adapter and align claims (DNS-style, no heavy OSCAL conversion)."""

    import json as _json

    adapter_registry = {
        "servicenow": "uiao.adapters.servicenow_adapter.ServiceNowAdapter",
        "entra": "uiao.adapters.entra_adapter.EntraAdapter",
    }

    vendor_lower = vendor.lower()
    if vendor_lower not in adapter_registry:
        _console.print(f"[red]Unknown vendor: {vendor}[/red]")
        _console.print(f"[dim]Available: {', '.join(adapter_registry.keys())}[/dim]")
        raise typer.Exit(code=1)

    # Lazy import to avoid circular dependencies
    import importlib

    module_path, class_name = adapter_registry[vendor_lower].rsplit(".", 1)
    module = importlib.import_module(module_path)
    adapter_class = getattr(module, class_name)
    adapter = adapter_class()

    _console.print(f"[bold green]> Running {vendor} adapter...[/bold green]")
    aligned = adapter.collect_and_align()

    _console.print(f"[bold]Aligned {aligned['metadata']['total_records']} claims[/bold]")
    _console.print(f"[dim]Metadata: {aligned['metadata']}[/dim]")

    if output:
        with open(output, "w") as f:
            _json.dump(aligned, f, indent=2, default=str)
        _console.print(f"[green]Saved to {output}[/green]")


@adapter_app.command("run-scuba")
def adapter_run_scuba(
    report: str = typer.Argument(
        ...,
        help="Path to ScubaGear output file (.json or .yaml)",
    ),
    output: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output JSON file path for alignment results",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Parse report and print summary without writing output",
    ),
) -> None:
    """
    Run SCuBA adapter: ingest a ScubaGear assessment report and map
    policy results to UIAO KSI evidence.

    Reads ScubaGear JSON or YAML output and produces OSCAL-aligned
    claim records for each M365 policy baseline finding.

    Example::

        uiao adapter run-scuba exports/scuba/M365BaselineConformance.json
    """
    import json as _json

    from uiao.adapters.scubagear_adapter import ScubaGearAdapter

    typer.echo(f"\U0001f50d Reading SCuBA report: {report}")
    adapter = ScubaGearAdapter(config={"report_path": report})
    result = adapter.collect_and_align()

    meta = result.get("metadata", {})
    total = meta.get("total_policies", 0)
    passing = meta.get("passing", 0)
    failing = meta.get("failing", 0)

    typer.echo(f"  Total policies : {total}")
    typer.echo(f"  Passing        : {passing}")
    typer.echo(f"  Failing        : {failing}")

    if dry_run:
        typer.echo("\nDry-run mode — no output written.")
        return

    if output:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            _json.dump(result, f, indent=2, default=str)
        typer.echo(f"\n✅ Alignment written to {output}")
    else:
        typer.echo("\n" + _json.dumps(result["metadata"], indent=2, default=str))
