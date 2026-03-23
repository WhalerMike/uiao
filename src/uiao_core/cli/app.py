"""UIAO-Core CLI application.

Provides command-line interface for OSCAL document generation,
validation, and canon management.
"""
from __future__ import annotations

import typer
from rich.console import Console

from uiao_core.__version__ import __version__

app = typer.Typer(
    name="uiao",
    help="UIAO-Core: OSCAL compliance toolkit for US Government systems.",
    add_completion=False,
)
console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"uiao-core {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """UIAO-Core OSCAL compliance toolkit."""


@app.command()
def generate_ssp(
    canon_path: str = typer.Option(
        "canon/uiao_leadership_briefing_v1.0.yaml",
        "--canon", "-c",
        help="Path to canon YAML file.",
    ),
    data_dir: str = typer.Option(
        "data",
        "--data-dir", "-d",
        help="Path to data YAML directory.",
    ),
    output: str = typer.Option(
        "exports/oscal/uiao-ssp-skeleton.json",
        "--output", "-o",
        help="Output SSP JSON path.",
    ),
) -> None:
    """Generate an OSCAL SSP from canon YAML and data files."""
    from uiao_core.generators.ssp import build_ssp

    console.print(f"[bold]Generating SSP from {canon_path}...[/bold]")
    out = build_ssp(canon_path=canon_path, data_dir=data_dir, output_path=output)
    console.print(f"[green]SSP written to {out}[/green]")


@app.command()
def validate(
    path: str = typer.Argument(..., help="Path to OSCAL JSON file."),
) -> None:
    """Validate an OSCAL document against its schema."""
    console.print(f"[bold]Validating {path}...[/bold]")
    console.print("[yellow]Validation not yet implemented (Week 3).[/yellow]")


@app.command()
def canon_check(
    canon_dir: str = typer.Option("canon", "--dir", "-d", help="Canon directory."),
) -> None:
    """Check canon YAML files for consistency."""
    console.print(f"[bold]Checking canon at {canon_dir}...[/bold]")
    console.print("[yellow]Canon check not yet implemented (Week 3).[/yellow]")


if __name__ == "__main__":
    app()
