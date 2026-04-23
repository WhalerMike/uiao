"""Typer subcommand: ``uiao orchestrator`` — UIAO_100 scheduler CLI.

Provides a thin CLI over ``uiao.orchestrator.scheduler.OrchestratorScheduler``:

    uiao orchestrator schedule --dry-run
    uiao orchestrator schedule --output-root evidence/orchestrator-runs
    uiao orchestrator dispatch scubagear --output-root ...

Intended invocations:
  - Local authoring: ``--dry-run`` to see which adapters the registry would
    dispatch without instantiating anything.
  - CI (GitHub Actions cron): real dispatch — runs against the adapter
    factory and persists per-run directories.

The scheduler itself prints a structured summary via Rich. This module is
purely the CLI shim.

File: src/uiao/cli/orchestrator.py
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from uiao.orchestrator.scheduler import (
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_REGISTRY_PATH,
    OrchestratorScheduler,
)

orchestrator_app = typer.Typer(
    name="orchestrator",
    help="UIAO_100 Compliance Orchestrator — schedule adapter runs + route evidence.",
    add_completion=False,
)

console = Console()


def _render_summary(manifest_dict: dict) -> None:
    """Pretty-print a scheduler-run manifest to the console."""
    m = manifest_dict
    console.print(f"[bold]Run:[/bold]    {m['run_id']}")
    console.print(f"[bold]Dir:[/bold]    {m['run_dir']}")
    console.print(f"[bold]Window:[/bold] {m['started_at']} → {m['completed_at']}  ({m['duration_secs']}s)")
    console.print(
        f"[bold]Adapters:[/bold] total={m['adapters_total']}  "
        f"[green]ok={m['adapters_successful']}[/green]  "
        f"[red]failed={m['adapters_failed']}[/red]  "
        f"skipped={m['adapters_skipped']}  "
        f"not-wired={m['adapters_not_wired']}"
    )
    console.print(f"[bold]Drift:[/bold]    total={m['drift_findings_total']}  by_severity={m['drift_by_severity']}")

    table = Table(show_header=True, header_style="bold")
    table.add_column("adapter_id")
    table.add_column("status")
    table.add_column("retry", justify="right")
    table.add_column("drift")
    table.add_column("dur(s)", justify="right")
    for run in m.get("runs", []):
        status = run["status"]
        color = {
            "success": "green",
            "failed": "red",
            "skipped": "yellow",
            "not-wired": "bright_black",
        }.get(status, "white")
        table.add_row(
            run["adapter_id"],
            f"[{color}]{status}[/{color}]",
            str(run["retry_count"]),
            run.get("drift_severity") or "-",
            str(run["duration_secs"]),
        )
    console.print(table)


@orchestrator_app.command("schedule")
def schedule(
    registry: Path = typer.Option(
        DEFAULT_REGISTRY_PATH,
        "--registry",
        "-r",
        help="Path to the canonical adapter-registry.yaml",
    ),
    output_root: Path = typer.Option(
        DEFAULT_OUTPUT_ROOT,
        "--output-root",
        "-o",
        help="Root directory for per-run output trees.",
    ),
    status: str = typer.Option(
        "active",
        "--status",
        help="Comma-separated list of registry status values to include.",
    ),
    max_retries: int = typer.Option(
        2,
        "--max-retries",
        help="Per-adapter retry ceiling (exponential backoff).",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Report what would run; do not invoke adapters or write files.",
    ),
    emit_json: bool = typer.Option(
        False,
        "--json",
        help="Emit the manifest as JSON on stdout (suppresses the pretty table).",
    ),
) -> None:
    """Dispatch every active adapter in the registry; persist evidence + drift."""
    status_filter = tuple(s.strip() for s in status.split(",") if s.strip())
    scheduler = OrchestratorScheduler(
        registry_path=registry,
        output_root=output_root,
        status_filter=status_filter,
        max_retries=max_retries,
    )
    manifest = scheduler.dispatch_all(dry_run=dry_run)
    payload = manifest.to_dict()
    if emit_json:
        typer.echo(json.dumps(payload, indent=2, default=str))
        return
    _render_summary(payload)
    if manifest.adapters_failed > 0:
        raise typer.Exit(code=1)


@orchestrator_app.command("dispatch")
def dispatch(
    adapter_id: str = typer.Argument(..., help="Registry ID of the adapter to run."),
    registry: Path = typer.Option(
        DEFAULT_REGISTRY_PATH,
        "--registry",
        "-r",
        help="Path to the canonical adapter-registry.yaml",
    ),
    output_root: Path = typer.Option(
        DEFAULT_OUTPUT_ROOT,
        "--output-root",
        "-o",
        help="Root directory for per-run output trees.",
    ),
    max_retries: int = typer.Option(2, "--max-retries", help="Retry ceiling."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Plan only; no adapter invocation."),
) -> None:
    """Dispatch a single adapter by registry ID."""
    scheduler = OrchestratorScheduler(
        registry_path=registry,
        output_root=output_root,
        max_retries=max_retries,
    )
    run = scheduler.dispatch_one(adapter_id, dry_run=dry_run)
    console.print(
        f"[bold]{run.adapter_id}[/bold]  status={run.status}  retry={run.retry_count}  duration={run.duration_secs}s"
    )
    if run.error:
        console.print(f"[red]{run.error}[/red]")
    if run.evidence_path:
        console.print(f"evidence: {run.evidence_path}")
    if run.drift_path:
        console.print(f"drift:    {run.drift_path}  severity={run.drift_severity}")
    if run.status == "failed":
        raise typer.Exit(code=1)


@orchestrator_app.command("list")
def list_adapters(
    registry: Path = typer.Option(
        DEFAULT_REGISTRY_PATH,
        "--registry",
        "-r",
        help="Path to the canonical adapter-registry.yaml",
    ),
    status: str = typer.Option(
        "active",
        "--status",
        help="Comma-separated status filter, or 'all'.",
    ),
) -> None:
    """List adapters the scheduler would dispatch under the given status filter."""
    status_filter: tuple[str, ...]
    status_filter = () if status.strip().lower() == "all" else tuple(s.strip() for s in status.split(",") if s.strip())
    scheduler = OrchestratorScheduler(registry_path=registry, status_filter=status_filter)
    adapters = scheduler.load_registry()
    if status_filter:
        adapters = [a for a in adapters if a.get("status") in status_filter]

    table = Table(show_header=True, header_style="bold")
    table.add_column("id")
    table.add_column("status")
    table.add_column("class")
    table.add_column("mission-class")
    table.add_column("phase")
    for entry in adapters:
        table.add_row(
            str(entry.get("id", "")),
            str(entry.get("status", "")),
            str(entry.get("class", "")),
            str(entry.get("mission-class", "")),
            str(entry.get("phase", "")),
        )
    console.print(table)
    console.print(f"[dim]{len(adapters)} adapter(s) match filter {status_filter or '(all)'}[/dim]")
