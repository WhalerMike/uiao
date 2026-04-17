"""uiao.impl.cli.evidence — Typer sub-app for the `uiao evidence` command group.

Mount point
-----------
    # in uiao/impl/cli/app.py
    from uiao.impl.cli.evidence import evidence_app
    app.add_typer(evidence_app, name="evidence")

Usage (after `pip install -e .`)
---------------------------------
    uiao evidence build \\
        --input  ./output/ksi/tenant-a.ksi.json \\
        --output ./output/evidence/tenant-a/ \\
        --config ./config/evidence-build.json

Or via module invocation:
    python -m uiao.impl.cli evidence build \\
        --input  ./output/ksi/tenant-a.ksi.json \\
        --output ./output/evidence/tenant-a/
"""
from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

from uiao.impl.evidence.builder import build_evidence

evidence_app = typer.Typer(
    name="evidence",
    help="Evidence bundle operations.",
    add_completion=False,
)

_console = Console()


@evidence_app.command("build")
def build_command(
    input: str = typer.Option(  # noqa: B008
        ...,
        "--input",
        help="Path to the KSI result JSON produced by Plane 2 (ksi evaluate).",
        show_default=False,
    ),
    output: str = typer.Option(  # noqa: B008
        ...,
        "--output",
        help=(
            "Destination directory for the evidence bundle "
            "(e.g. ./output/evidence/tenant-a/).  "
            "Created automatically if absent."
        ),
        show_default=False,
    ),
    config: Optional[str] = typer.Option(  # noqa: B008
        None,
        "--config",
        help="Optional path to evidence-build.json config file.",
        show_default=False,
    ),
) -> None:
    """Build a canonical evidence bundle from a KSI result JSON file.

    This command is the CLI surface for Plane 3 of the UIAO pipeline.
    It is a thin wrapper around
    `uiao.impl.evidence.builder.build_evidence`, which is kept
    intentionally pure (no CLI, no side-effects beyond bundle directory I/O).

    \\b
    Output layout
    -------------
    The bundle directory will contain:

        <output>/bundle.json        — canonical envelope + manifest
        <output>/evidence.jsonl     — one EvidenceRecord per line (NDJSON)
        <output>/hashes/            — per-record SHA-256 sidecar files
        <output>/provenance/        — per-record provenance JSON files

    \\b
    Examples
    --------
    Minimal (no config):

        uiao evidence build \\
            --input  ./output/ksi/tenant-a.ksi.json \\
            --output ./output/evidence/tenant-a/

    With config:

        uiao evidence build \\
            --input  ./output/ksi/tenant-a.ksi.json \\
            --output ./output/evidence/tenant-a/ \\
            --config ./config/evidence-build.json
    """
    try:
        build_evidence(
            ksi_path=input,
            output_dir=output,
            config_path=config,
        )
    except FileNotFoundError as exc:
        _console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    except ValueError as exc:
        _console.print(f"[red]Validation error:[/red] {exc}")
        raise typer.Exit(code=1) from exc


