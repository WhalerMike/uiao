"""Identity Governance CLI: ``uiao identity ...`` subcommands.

Operator surface for the human JML lifecycle detector, service identity
orphan detection, and the pipeline gate that makes governance observable.

Commands:

- ``run``   — run the full JML + orphan pipeline, write evidence artifacts
- ``gate``  — read the last gate-report.json; exit 1 if P1 findings exist
- ``diff``  — diff two HRIT snapshots and show human JML events
- ``scan``  — scan service identity snapshot for orphans and expiring credentials

Examples::

    uiao identity run --hrit current.json --services svc.json --out evidence/
    uiao identity run --hrit current.json --prior-hrit prior.json --services svc.json --out evidence/
    uiao identity gate --evidence evidence/
    uiao identity diff --current hrit-2026-06.json --prior hrit-2026-05.json
    uiao identity scan --services svc.json --leavers leavers.json

Actuation tier: L2 — all commands are read-only (observe + advise).
``gate`` exits 1 on P1 findings; it does not remediate.  See UIAO_200.

Canon: governance/identity/jml.py, service_identity.py, pipeline.py, UIAO_200.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

identity_app = typer.Typer(
    name="identity",
    help="Human + service identity lifecycle governance (JML, orphan detection, gate).",
    no_args_is_help=True,
)

console = Console()
err = Console(stderr=True)

_SEVERITY_COLOR = {"P1": "bold red", "P2": "yellow", "P3": "cyan"}


# ---------------------------------------------------------------------------
# run — full pipeline
# ---------------------------------------------------------------------------


@identity_app.command("run")
def run_pipeline(
    hrit: Annotated[Path, typer.Option("--hrit", help="Current HRIT snapshot JSON")] = Path("hrit-current.json"),
    prior_hrit: Annotated[Path | None, typer.Option("--prior-hrit", help="Prior HRIT snapshot JSON")] = None,
    services: Annotated[Path | None, typer.Option("--services", help="Service identity snapshot JSON")] = None,
    prior_services: Annotated[
        Path | None, typer.Option("--prior-services", help="Prior service identity snapshot JSON")
    ] = None,
    out: Annotated[Path, typer.Option("--out", help="Output directory for evidence artifacts")] = Path(
        "evidence/identity"
    ),
    no_fail: Annotated[bool, typer.Option("--no-fail", help="Do not exit 1 on P1 findings")] = False,
) -> None:
    """Run the identity governance pipeline.

    Diffs HRIT snapshots to detect human JML events, then cross-references
    service identity accounts to find orphaned accounts.  Writes evidence
    artifacts and gate-report.json to --out.

    Exits 1 if P1 findings are present (use --no-fail to suppress).
    """
    from uiao.governance.identity.pipeline import (
        hrit_records_from_json,
        service_records_from_json,
    )
    from uiao.governance.identity.pipeline import (
        run_pipeline as _run,
    )

    if not hrit.exists():
        err.print(f"[red]HRIT file not found: {hrit}[/red]")
        raise typer.Exit(2)

    console.print(f"[bold]Loading HRIT snapshot:[/bold] {hrit}")
    current_hrit = hrit_records_from_json(hrit)
    prior_hrit_records = hrit_records_from_json(prior_hrit) if prior_hrit and prior_hrit.exists() else None

    current_services = []
    prior_services_records = None
    if services and services.exists():
        console.print(f"[bold]Loading service identity snapshot:[/bold] {services}")
        current_services = service_records_from_json(services)
        if prior_services and prior_services.exists():
            prior_services_records = service_records_from_json(prior_services)

    console.print(f"[bold]Running pipeline → {out}[/bold]")
    result = _run(
        current_hrit,
        current_services,
        prior_hrit=prior_hrit_records,
        prior_services=prior_services_records,
        output_dir=out,
        fail_on_p1=not no_fail,
    )

    for line in result.summary_lines:
        style = "bold red" if "FAILED" in line else "bold green" if "PASSED" in line else ""
        console.print(line, style=style)

    _print_findings_table(result)

    if not result.gate_passed:
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# gate — read last report, exit 1 on P1
# ---------------------------------------------------------------------------


@identity_app.command("gate")
def gate(
    evidence: Annotated[Path, typer.Option("--evidence", help="Evidence directory containing gate-report.json")] = Path(
        "evidence/identity"
    ),
) -> None:
    """Check the last pipeline gate-report.json and exit 1 if it failed.

    Use this as the final step in a CI job or cron script.  If
    gate-report.json is absent, exits 2 (pipeline has not run).

    Example CI step::

        uiao identity gate --evidence evidence/identity
    """
    report_path = evidence / "gate-report.json"
    if not report_path.exists():
        err.print(f"[red]gate-report.json not found at {report_path}[/red]")
        err.print("Run [bold]uiao identity run[/bold] first.")
        raise typer.Exit(2)

    report = json.loads(report_path.read_text(encoding="utf-8"))
    p1 = report.get("p1_count", 0)
    p2 = report.get("p2_count", 0)
    passed = report.get("gate_passed", True)

    if passed:
        console.print(f"[bold green]GATE PASSED[/bold green] — {p1} P1, {p2} P2 findings.")
    else:
        err.print(f"[bold red]GATE FAILED[/bold red] — {p1} P1 finding(s) require immediate action.")
        _print_report_summary(report)
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# diff — human JML only
# ---------------------------------------------------------------------------


@identity_app.command("diff")
def diff(
    current: Annotated[Path, typer.Option("--current", help="Current HRIT snapshot JSON")] = Path("hrit-current.json"),
    prior: Annotated[Path | None, typer.Option("--prior", help="Prior HRIT snapshot JSON")] = None,
    out: Annotated[Path | None, typer.Option("--out", help="Write event log JSON here")] = None,
) -> None:
    """Diff two HRIT snapshots and show human JML lifecycle events.

    Useful for inspecting what a pipeline run would detect before committing
    to the full pipeline.
    """
    from uiao.governance.identity.jml import detect_events
    from uiao.governance.identity.pipeline import hrit_records_from_json

    if not current.exists():
        err.print(f"[red]File not found: {current}[/red]")
        raise typer.Exit(2)

    current_records = hrit_records_from_json(current)
    prior_records = hrit_records_from_json(prior) if prior and prior.exists() else None

    events = detect_events(current_records, prior_records)
    console.print(events.summary())

    table = Table(title="Human JML Events", show_lines=True)
    table.add_column("Type", style="bold")
    table.add_column("Employee ID")
    table.add_column("Name")
    table.add_column("Changed fields")
    table.add_column("Findings")

    for ev in events.all_events:
        sev = max((f.severity.value for f in ev.findings), default="")
        table.add_row(
            ev.event_type.value,
            ev.record.employee_id,
            ev.identity_label,
            ", ".join(ev.changed_fields) or "-",
            f"[{_SEVERITY_COLOR.get(sev, '')}]{sev}[/]" if sev else "-",
        )
    console.print(table)

    if out:
        from uiao.governance.identity.jml import write_evidence_artifacts

        paths = write_evidence_artifacts(events, out.parent)
        console.print(f"Evidence written to {[str(p) for p in paths]}")


# ---------------------------------------------------------------------------
# scan — service identity only
# ---------------------------------------------------------------------------


@identity_app.command("scan")
def scan(
    services: Annotated[Path, typer.Option("--services", help="Service identity snapshot JSON")] = Path(
        "services.json"
    ),
    leavers: Annotated[
        Path | None,
        typer.Option("--leavers", help='JSON file with leaver employee_ids: {"leavers": ["E001",...]}'),
    ] = None,
    out: Annotated[Path | None, typer.Option("--out", help="Write event log JSON here")] = None,
) -> None:
    """Scan service identity snapshot for orphaned and expiring accounts."""
    from uiao.governance.identity.pipeline import service_records_from_json
    from uiao.governance.identity.service_identity import detect_service_events

    if not services.exists():
        err.print(f"[red]File not found: {services}[/red]")
        raise typer.Exit(2)

    svc_records = service_records_from_json(services)

    leaver_ids: set[str] = set()
    if leavers and leavers.exists():
        data = json.loads(leavers.read_text(encoding="utf-8"))
        leaver_ids = set(data if isinstance(data, list) else data.get("leavers", []))

    events = detect_service_events(svc_records, leaver_employee_ids=leaver_ids)
    console.print(events.summary())

    if events.orphaned:
        table = Table(title="Orphaned Service Accounts (P1)", style="bold red", show_lines=True)
        table.add_column("Principal ID")
        table.add_column("Display Name")
        table.add_column("Owner (departed)")
        table.add_column("OrgPath")
        for ev in events.orphaned:
            table.add_row(
                ev.record.principal_id,
                ev.record.display_name,
                ev.orphaned_by_employee_id or "-",
                ev.record.orgpath or "-",
            )
        console.print(table)

    if events.expiring:
        table = Table(title="Expiring Credentials", show_lines=True)
        table.add_column("Principal ID")
        table.add_column("Expiry date")
        table.add_column("Severity")
        for ev in events.expiring:
            sev = ev.findings[0].severity.value if ev.findings else "-"
            table.add_row(
                ev.record.principal_id,
                ev.record.credential_expiry_date or "-",
                f"[{_SEVERITY_COLOR.get(sev, '')}]{sev}[/]",
            )
        console.print(table)

    if out:
        from uiao.governance.identity.service_identity import write_evidence_artifacts

        paths = write_evidence_artifacts(events, out.parent)
        console.print(f"Evidence written to {[str(p) for p in paths]}")


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------


def _print_findings_table(result: object) -> None:
    from uiao.governance.identity.pipeline import GateResult

    if not isinstance(result, GateResult):
        return
    all_findings = result.human_events.all_findings + result.service_events.all_findings
    if not all_findings:
        return
    table = Table(title="Governance Findings", show_lines=True)
    table.add_column("ID", no_wrap=True)
    table.add_column("Drift class")
    table.add_column("Severity")
    table.add_column("Finding")
    for f in all_findings:
        sev = f.severity.value
        table.add_row(
            f.finding_id,
            f.drift_class,
            f"[{_SEVERITY_COLOR.get(sev, '')}]{sev}[/]",
            f.observed[:100] + ("..." if len(f.observed) > 100 else ""),
        )
    console.print(table)


def _print_report_summary(report: dict) -> None:
    human = report.get("human", {})
    service = report.get("service", {})
    console.print(
        f"  Human: {human.get('joiners', 0)} joiners, "
        f"{human.get('movers', 0)} movers, "
        f"{human.get('leavers', 0)} leavers"
    )
    console.print(f"  Service: {service.get('orphaned', 0)} orphaned, {service.get('expiring', 0)} expiring")
