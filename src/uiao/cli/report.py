"""uiao.cli.report — Typer sub-app for the `uiao report` command group (ADR-128).

Gated reporting-egress: submit already-generated ConMon evidence outward to
external federal destinations. Dry-run is the default; every live submission
requires an explicit ``--approver`` (the L3 human-approval gate).

Mount point
-----------
    # in uiao/cli/app.py
    from uiao.cli.report import report_app
    app.add_typer(report_app, name="report")

Usage
-----
    uiao report list-destinations
    uiao report submit -d cisa-sbom -a out/sbom.json -t cyclonedx-sbom            # dry-run
    uiao report submit -d cisa-sbom -a out/sbom.json -t cyclonedx-sbom \\
        --live --approver "jane.isso"                                            # L3-gated live
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from uiao.reporting_egress import (
    Approval,
    Destination,
    Disposition,
    Submission,
    list_destinations,
    submit,
)

report_app = typer.Typer(
    name="report",
    help="Gated reporting-egress: submit ConMon evidence to federal destinations (dry-run default, L3-gated).",
    add_completion=False,
)

_console = Console()

_DISPOSITION_STYLE = {
    Disposition.PLANNED: "cyan",
    Disposition.BLOCKED: "red",
    Disposition.SUBMITTED: "green",
}


@report_app.command("list-destinations")
def report_list_destinations() -> None:
    """List the registered reporting-egress destinations and their wiring state."""
    table = Table(title="Reporting-egress destinations", show_header=True, header_style="bold")
    table.add_column("id", style="cyan", no_wrap=True)
    table.add_column("destination")
    table.add_column("accepts")
    table.add_column("wired", justify="center")
    for drv in list_destinations():
        wired = "[green]yes[/green]" if drv.configured else "[yellow]no[/yellow]"
        table.add_row(drv.destination.value, drv.label, ", ".join(drv.accepts), wired)
    _console.print(table)
    _console.print(
        "\n[dim]All destinations ship unconfigured; a live submission to an "
        "unwired endpoint is blocked (ADR-128 §6).[/dim]"
    )


@report_app.command("submit")
def report_submit(
    destination: str = typer.Option(
        ..., "--destination", "-d", help="Destination id (see `report list-destinations`)."
    ),
    artifact: str = typer.Option(..., "--artifact", "-a", help="Path to the already-generated artifact to submit."),
    artifact_type: str = typer.Option(
        ..., "--artifact-type", "-t", help="Artifact type, e.g. oscal-ar, cyclonedx-sbom, openvex."
    ),
    live: bool = typer.Option(
        False, "--live", help="Attempt a real submission. Requires --approver (L3 gate). Default: dry-run."
    ),
    approver: str | None = typer.Option(
        None, "--approver", help="Named human approver for the L3 gate (required with --live)."
    ),
) -> None:
    """Plan (dry-run) or perform a gated outward submission.

    Without --live this validates and plans only, transmitting nothing. With
    --live it requires --approver; the submission is still blocked if the
    destination endpoint is not wired (scaffold), which is the safe default.
    """
    try:
        dest = Destination(destination)
    except ValueError as exc:
        valid = ", ".join(d.value for d in Destination)
        _console.print(f"[red]Unknown destination '{destination}'. Choose one of: {valid}.[/red]")
        raise typer.Exit(code=2) from exc

    approval = None
    if approver:
        approval = Approval(
            approver=approver,
            approved_at=datetime.now(timezone.utc).isoformat(),
            operation=f"submit:{dest.value}",
        )

    result = submit(
        Submission(destination=dest, artifact_path=Path(artifact), artifact_type=artifact_type),
        live=live,
        approval=approval,
    )

    style = _DISPOSITION_STYLE.get(result.disposition, "")
    _console.print(f"Destination : [cyan]{result.destination.value}[/cyan]")
    _console.print(f"Disposition : [{style}]{result.disposition.value}[/{style}]")
    _console.print(f"Reason      : {result.reason}")
    if result.problems:
        for p in result.problems:
            _console.print(f"  [yellow]- {p}[/yellow]")
    if result.approver:
        _console.print(f"Approver    : {result.approver}")
    if result.receipt is not None:
        _console.print(f"Receipt     : {result.receipt}")

    # Non-transmitted live attempts are failures for scripting/CI.
    if result.disposition is Disposition.BLOCKED:
        raise typer.Exit(code=1)
