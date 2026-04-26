"""uiao.cli.conmon — Typer sub-app for the `uiao conmon` command group.

Mount point
-----------
    # in uiao/cli/app.py
    from uiao.cli.conmon import conmon_app
    app.add_typer(conmon_app, name="conmon")

Usage (after `pip install -e .`)
---------------------------------
    uiao conmon process --alert-json alerts/alert-001.json
    uiao conmon export-oa --output exports/oscal/uiao-ongoing-auth.json
    uiao conmon dashboard --output exports/conmon/ksi-dashboard.json

Or via module invocation:
    python -m uiao.cli conmon process --alert-json alerts/alert.json
"""

from __future__ import annotations

import typer
from rich.console import Console

conmon_app = typer.Typer(
    name="conmon",
    help="Continuous monitoring operations (Sentinel hooks, OA export, dashboards).",
    add_completion=False,
)

_console = Console()


@conmon_app.command("process")
def conmon_process(
    alert_json: str = typer.Option(
        ...,
        "--alert-json",
        "-a",
        help="Path to a Sentinel alert webhook payload JSON file.",
    ),
    poam_path: str = typer.Option(
        "data/poam-findings.yml",
        "--poam-path",
        "-p",
        help="Path to the POA&M findings YAML file (created if absent).",
    ),
    monitoring_sources: str = typer.Option(
        "data/monitoring-sources.yml",
        "--monitoring-sources",
        "-m",
        help="Path to monitoring-sources.yml signal map.",
    ),
    no_upsert: bool = typer.Option(
        False,
        "--no-upsert",
        help="Dry-run: parse and map controls without writing the POA&M file.",
    ),
) -> None:
    """Process a Sentinel alert and auto-upsert a POA&M entry.

    Reads a Sentinel alert webhook payload from ALERT_JSON, maps it to
    NIST 800-53 controls via monitoring-sources.yml, and creates or
    updates a POA&M entry in POAM_PATH.  Use --no-upsert for a dry-run.

    Example::

        uiao conmon process --alert-json alert.json --poam-path data/poam-findings.yml
    """
    import json as _json
    from pathlib import Path as _Path

    from uiao.monitoring.sentinel_hook import SentinelHook

    alert_path = _Path(alert_json)
    if not alert_path.exists():
        _console.print(f"[red]Alert JSON not found: {alert_path}[/red]")
        raise typer.Exit(code=1)

    _console.print(f"[bold]Processing Sentinel alert from {alert_json}...[/bold]")
    payload = _json.loads(alert_path.read_text())

    hook = SentinelHook(monitoring_sources_path=monitoring_sources)
    alert = hook.parse_alert(payload)
    control_ids = hook.map_alert_to_controls(alert)

    _console.print(f"  Alert ID : [cyan]{alert.alert_id}[/cyan]")
    _console.print(f"  Severity : [cyan]{alert.severity}[/cyan]")
    _console.print(f"  Controls : [cyan]{', '.join(control_ids) or 'SI-4 (default)'}[/cyan]")

    if no_upsert:
        _console.print("[yellow]Dry-run: POA&M file not updated.[/yellow]")
    else:
        poam_entry = hook.upsert_poam_entry(alert, poam_path=poam_path)
        _console.print(f"  POA&M ID : [green]{poam_entry['id']}[/green]")
        _console.print(f"[green]POA&M entry upserted -> {poam_path}[/green]")


@conmon_app.command("export-oa")
def conmon_export_oa(
    monitoring_sources: str = typer.Option(
        "data/monitoring-sources.yml",
        "--monitoring-sources",
        "-m",
        help="Path to monitoring-sources.yml signal map.",
    ),
    ksi_mappings: str = typer.Option(
        "data/ksi-mappings.yml",
        "--ksi-mappings",
        "-k",
        help="Path to ksi-mappings.yml.",
    ),
    output: str = typer.Option(
        "exports/oscal/uiao-ongoing-auth.json",
        "--output",
        "-o",
        help="Output path for the ongoing-authorization OSCAL JSON artifact.",
    ),
) -> None:
    """Export an OSCAL ongoing-authorization evidence artifact.

    Generates machine-readable control evidence linking every monitored
    NIST 800-53 control to its telemetry source, satisfying the FedRAMP
    20x Phase 2 ConMon requirement for ongoing authorization evidence.

    Example::

        uiao conmon export-oa --output /tmp/ongoing-auth.json
    """
    from uiao.monitoring.ongoing_auth import OngoingAuthGenerator

    _console.print("[bold]Generating ongoing-authorization evidence artifact...[/bold]")
    gen = OngoingAuthGenerator(
        monitoring_sources_path=monitoring_sources,
        ksi_mappings_path=ksi_mappings,
    )
    out = gen.export(output)
    _console.print(f"[green]Ongoing-authorization evidence written to {out}[/green]")


@conmon_app.command("dashboard")
def conmon_dashboard(
    ksi_mappings: str = typer.Option(
        "data/ksi-mappings.yml",
        "--ksi-mappings",
        "-k",
        help="Path to ksi-mappings.yml.",
    ),
    output: str = typer.Option(
        "exports/conmon/ksi-dashboard.json",
        "--output",
        "-o",
        help="Output path for the KSI dashboard artifact.",
    ),
    fmt: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Output format: json or yaml.",
    ),
) -> None:
    """Export the KSI continuous monitoring dashboard.

    Computes Key Security Indicator scores from ksi-mappings.yml and
    writes a FedRAMP 20x Phase 2 ConMon dashboard artifact in JSON or
    YAML format.

    Example::

        uiao conmon dashboard --output /tmp/ksi-dashboard.json --format json
    """
    from uiao.dashboard.export import DashboardExporter

    fmt_lower = fmt.lower()
    if fmt_lower not in ("json", "yaml"):
        _console.print(f"[red]Invalid format '{fmt}'. Choose 'json' or 'yaml'.[/red]")
        raise typer.Exit(code=1)

    _console.print("[bold]Generating KSI ConMon dashboard...[/bold]")
    exporter = DashboardExporter(ksi_mappings_path=ksi_mappings)

    out = exporter.export_yaml(output) if fmt_lower == "yaml" else exporter.export_json(output)

    _console.print(f"[green]KSI dashboard written to {out}[/green]")
