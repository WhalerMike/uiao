"""Substrate CLI: `uiao substrate ...` subcommands.

Exposes the repo-walker and drift bootstrap to the `uiao` Typer app.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from uiao_impl.substrate.walker import walk_substrate

substrate_app = typer.Typer(
    name="substrate",
    help="Substrate tooling (repo-walker, drift bootstrap) driven by the substrate manifest (UIAO_200) and workspace contract (UIAO_201).",
    no_args_is_help=True,
)

console = Console()


@substrate_app.command("walk")
def walk(
    workspace_root: Optional[Path] = typer.Option(
        None,
        "--workspace-root",
        "-w",
        help="Absolute workspace root. Overrides $UIAO_WORKSPACE_ROOT and git top-level.",
    ),
    as_json: bool = typer.Option(
        False,
        "--json",
        help="Emit findings as machine-readable JSON instead of a table.",
    ),
) -> None:
    """Walk the substrate: validate module paths and canon document registry."""
    report = walk_substrate(workspace_root=workspace_root)
    if as_json:
        json.dump(report.as_dict(), sys.stdout, indent=2)
        sys.stdout.write("\n")
        if report.blocking:
            raise typer.Exit(code=1)
        return

    console.print(f"[bold]Workspace:[/bold] {report.workspace_root}")
    console.print(
        f"  substrate-manifest: {'found' if report.manifest_present else '[red]MISSING[/red]'}"
    )
    console.print(
        f"  workspace-contract: {'found' if report.contract_present else 'absent (optional)'}"
    )
    console.print(f"  modules checked:    {report.modules_checked}")
    console.print(f"  documents checked:  {report.documents_checked}")
    console.print(f"  impl refs checked:  {report.impl_refs_checked}")

    if report.ok:
        console.print("\n[green]PASS[/green] — no drift detected.")
        return

    def _print_table(findings, style: str) -> None:
        table = Table(show_header=True, header_style=f"bold {style}")
        table.add_column("Class")
        table.add_column("Sev")
        table.add_column("Path")
        table.add_column("Detail")
        for f in findings:
            table.add_row(f.drift_class, f.severity, f.path, f.detail)
        console.print(table)

    if report.blockers:
        console.print(f"\n[red]FAIL[/red] — {len(report.blockers)} P1 blocking finding(s):")
        _print_table(report.blockers, "red")
    if report.warnings:
        console.print(
            f"\n[yellow]WARN[/yellow] — {len(report.warnings)} P2 non-blocking finding(s):"
        )
        _print_table(report.warnings, "yellow")

    if report.blocking:
        raise typer.Exit(code=1)


@substrate_app.command("drift")
def drift(
    workspace_root: Optional[Path] = typer.Option(
        None,
        "--workspace-root",
        "-w",
        help="Absolute workspace root. Overrides $UIAO_WORKSPACE_ROOT and git top-level.",
    ),
) -> None:
    """Bootstrap drift check: DRIFT-SCHEMA + DRIFT-PROVENANCE only.

    This is the minimum drift-scan declared by substrate-manifest.yaml.
    Full 5-class drift taxonomy (including semantic/authz/identity) is a
    runtime concern handled by uiao_impl.governance.drift.
    """
    report = walk_substrate(workspace_root=workspace_root)
    if report.ok:
        console.print("[green]PASS[/green] — no DRIFT-SCHEMA or DRIFT-PROVENANCE findings.")
        return
    if not report.blocking:
        console.print(
            f"[green]PASS[/green] with {len(report.warnings)} P2 warning(s). "
            "Run `uiao substrate walk` for detail."
        )
        return
    console.print(
        f"[red]FAIL[/red] — {len(report.blockers)} P1 blocker(s) + "
        f"{len(report.warnings)} warning(s). Run `uiao substrate walk` for detail."
    )
    raise typer.Exit(code=1)
