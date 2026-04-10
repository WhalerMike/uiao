"""uiao_core.cli.oscal — Typer sub-app for the `uiao oscal` command group.

Mount point
-----------
    # in uiao_core/cli/app.py
    from uiao_core.cli.oscal import oscal_app
    app.add_typer(oscal_app, name="oscal")

Usage (after `pip install -e .`)
---------------------------------
    uiao oscal generate \\
        --evidence ./output/evidence/tenant-a/ \\
        --output   ./output/artifacts/tenant-a/ \\
        --config   ./config/oscal-generate.json

Or via module invocation:
    python -m uiao_core.cli oscal generate \\
        --evidence ./output/evidence/tenant-a/ \\
        --output   ./output/artifacts/tenant-a/
"""
from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

from uiao_core.oscal.generator import generate_oscal

oscal_app = typer.Typer(
    name="oscal",
    help="OSCAL artifact generation operations.",
    add_completion=False,
)

_console = Console()


@oscal_app.command("generate")
def generate_command(
    evidence: str = typer.Option(
        ...,
        "--evidence",
        help=(
            "Path to the evidence bundle directory produced by Plane 3 "
            "(must contain bundle.json and evidence.jsonl)."
        ),
        show_default=False,
    ),
    output: str = typer.Option(
        ...,
        "--output",
        help=(
            "Destination directory for OSCAL artifacts "
            "(e.g. ./output/artifacts/tenant-a/).  Created automatically."
        ),
        show_default=False,
    ),
    config: Optional[str] = typer.Option(
        None,
        "--config",
        help="Optional path to oscal-generate.json config file.",
        show_default=False,
    ),
) -> None:
    """Generate OSCAL artifacts (POA&M + SSP) from a Plane 3 evidence bundle.

    This command is the CLI surface for Plane 4 of the UIAO pipeline.
    It is a thin wrapper around
    `uiao_core.oscal.generator.generate_oscal`, which is kept
    intentionally pure (no CLI, no side-effects beyond artifact I/O).

    \\b
    Output layout
    -------------
    The artifact directory will contain:

        <output>/poam.json            — OSCAL-aligned POA&M (not-satisfied controls)
        <output>/ssp.json             — OSCAL-aligned SSP implemented-requirements
        <output>/artifact-index.json  — machine-readable manifest + hashes

    \\b
    Examples
    --------
    Minimal (no config):

        uiao oscal generate \\
            --evidence ./output/evidence/tenant-a/ \\
            --output   ./output/artifacts/tenant-a/

    With config:

        uiao oscal generate \\
            --evidence ./output/evidence/tenant-a/ \\
            --output   ./output/artifacts/tenant-a/ \\
            --config   ./config/oscal-generate.json
    """
    try:
        generate_oscal(
            evidence_dir=evidence,
            output_dir=output,
            config_path=config,
        )
    except FileNotFoundError as exc:
        _console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    except ValueError as exc:
        _console.print(f"[red]Validation error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
