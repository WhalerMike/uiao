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
    uiao conmon ato-cadence-check --award-date 2026-01-01 --ssp-draft-at 2026-01-25T00:00:00Z

Or via module invocation:
    python -m uiao.cli conmon process --alert-json alerts/alert.json
"""

from __future__ import annotations

import json as _json
from datetime import date as _date
from datetime import datetime as _datetime
from typing import Optional

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
    import json as _json_inner
    from pathlib import Path as _Path

    from uiao.monitoring.sentinel_hook import SentinelHook

    alert_path = _Path(alert_json)
    if not alert_path.exists():
        _console.print(f"[red]Alert JSON not found: {alert_path}[/red]")
        raise typer.Exit(code=1)

    _console.print(f"[bold]Processing Sentinel alert from {alert_json}...[/bold]")
    payload = _json_inner.loads(alert_path.read_text())

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


@conmon_app.command("ato-cadence-check")
def conmon_ato_cadence_check(
    award_date: str = typer.Option(
        ...,
        "--award-date",
        help="Contract award date in YYYY-MM-DD format.",
        metavar="YYYY-MM-DD",
    ),
    ssp_draft_at: Optional[str] = typer.Option(
        None,
        "--ssp-draft-at",
        help="ISO-8601 datetime when the draft SSP was submitted (optional).",
        metavar="ISO-DATETIME",
    ),
    ssp_final_at: Optional[str] = typer.Option(
        None,
        "--ssp-final-at",
        help="ISO-8601 datetime when the final SSP was submitted (optional).",
        metavar="ISO-DATETIME",
    ),
    current_ato_decision: Optional[str] = typer.Option(
        None,
        "--current-ato-decision",
        help="Date of the most recent ATO authorization decision (YYYY-MM-DD, optional).",
        metavar="YYYY-MM-DD",
    ),
    current_ato_expires: Optional[str] = typer.Option(
        None,
        "--current-ato-expires",
        help="Date the current ATO expires (YYYY-MM-DD, optional).",
        metavar="YYYY-MM-DD",
    ),
    emit_json: bool = typer.Option(
        False,
        "--json",
        help="Emit the CadenceReport as JSON instead of a rich table.",
    ),
    exit_on_fail: bool = typer.Option(
        False,
        "--exit-on-fail",
        help="Exit with code 1 if the overall verdict is FAIL.",
    ),
) -> None:
    """Validate ATO lifecycle SLA cadence (SSP submission windows + reauthorization).

    Enforces the three SLAs defined in UIAO_140 §4 and ADR-054 Q&A #44:

    \b
    * SSP-Draft-30      — Draft SSP must be submitted within 30 days of award.
    * SSP-Final-45      — Final SSP must be submitted within 45 days of award.
    * Reauthorization-30 — Reauth package due at least 30 days before ATO expiry.

    Verdicts: PASS | WARN | FAIL | N/A.  Overall is the worst-case severity.

    Example::

        uiao conmon ato-cadence-check \\
            --award-date 2026-01-01 \\
            --ssp-draft-at 2026-01-25T12:00:00Z \\
            --ssp-final-at 2026-02-10T12:00:00Z \\
            --current-ato-decision 2026-03-01 \\
            --current-ato-expires 2027-03-01 \\
            --exit-on-fail
    """
    from uiao.monitoring.ato_cadence import AtoCadenceInput, evaluate_ato_cadence

    # --- Parse inputs ---
    try:
        parsed_award: _date = _date.fromisoformat(award_date)
    except ValueError as exc:
        _console.print(f"[red]Invalid --award-date '{award_date}': expected YYYY-MM-DD.[/red]")
        raise typer.Exit(code=1) from exc

    def _parse_dt(value: Optional[str], flag: str) -> Optional[_datetime]:
        if value is None:
            return None
        try:
            return _datetime.fromisoformat(value)
        except ValueError as exc:
            _console.print(f"[red]Invalid {flag} '{value}': expected ISO-8601 datetime.[/red]")
            raise typer.Exit(code=1) from exc

    def _parse_date(value: Optional[str], flag: str) -> Optional[_date]:
        if value is None:
            return None
        try:
            return _date.fromisoformat(value)
        except ValueError as exc:
            _console.print(f"[red]Invalid {flag} '{value}': expected YYYY-MM-DD.[/red]")
            raise typer.Exit(code=1) from exc

    inp = AtoCadenceInput(
        award_date=parsed_award,
        ssp_draft_submitted_at=_parse_dt(ssp_draft_at, "--ssp-draft-at"),
        ssp_final_submitted_at=_parse_dt(ssp_final_at, "--ssp-final-at"),
        current_ato_decision_date=_parse_date(current_ato_decision, "--current-ato-decision"),
        current_ato_expires_at=_parse_date(current_ato_expires, "--current-ato-expires"),
    )

    report = evaluate_ato_cadence(inp)

    # --- JSON output ---
    if emit_json:
        _console.print(_json.dumps(_json.loads(report.model_dump_json()), indent=2))
        if exit_on_fail and report.overall == "FAIL":
            raise typer.Exit(code=1)
        return

    # --- Rich table output ---
    from rich.table import Table

    _VERDICT_STYLE: dict[str, str] = {
        "PASS": "green",
        "WARN": "yellow",
        "FAIL": "red",
        "N/A": "dim",
    }
    _OVERALL_STYLE: dict[str, str] = {
        "PASS": "bold green",
        "WARN": "bold yellow",
        "FAIL": "bold red",
    }

    table = Table(title="ATO Cadence SLA Report", show_header=True, header_style="bold")
    table.add_column("SLA", style="cyan", no_wrap=True)
    table.add_column("Threshold", justify="right")
    table.add_column("Actual (days)", justify="right")
    table.add_column("Verdict", justify="center")
    table.add_column("Message")

    for v in report.verdicts:
        style = _VERDICT_STYLE.get(v.verdict, "")
        actual_str = str(v.actual_days) if v.actual_days is not None else "—"
        table.add_row(
            v.name,
            f"{v.threshold_days}d",
            actual_str,
            f"[{style}]{v.verdict}[/{style}]",
            v.message,
        )

    _console.print(table)

    overall_style = _OVERALL_STYLE.get(report.overall, "bold")
    _console.print(
        f"\nOverall: [{overall_style}]{report.overall}[/{overall_style}]  "
        f"(evaluated at {report.evaluated_at.isoformat()})"
    )

    if exit_on_fail and report.overall == "FAIL":
        raise typer.Exit(code=1)
