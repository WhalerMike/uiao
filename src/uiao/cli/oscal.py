"""uiao.cli.oscal — Typer sub-app for the `uiao oscal` command group.

Mount point
-----------
    # in uiao/impl/cli/app.py
    from uiao.cli.oscal import oscal_app
    app.add_typer(oscal_app, name="oscal")

Usage (after `pip install -e .`)
---------------------------------
    uiao oscal generate \\
        --evidence ./output/evidence/tenant-a/ \\
        --output   ./output/artifacts/tenant-a/ \\
        --config   ./config/oscal-generate.json

Or via module invocation:
    python -m uiao.cli oscal generate \\
        --evidence ./output/evidence/tenant-a/ \\
        --output   ./output/artifacts/tenant-a/
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

oscal_app = typer.Typer(
    name="oscal",
    help="OSCAL artifact generation operations.",
    add_completion=False,
)

_console = Console()


@oscal_app.command("generate")
def generate_command(
    evidence: str = typer.Option(  # noqa: B008
        ...,
        "--evidence",
        help=(
            "Path to the evidence bundle directory produced by Plane 3 (must contain bundle.json and evidence.jsonl)."
        ),
        show_default=False,
    ),
    output: str = typer.Option(  # noqa: B008
        ...,
        "--output",
        help=("Destination directory for OSCAL artifacts (e.g. ./output/artifacts/tenant-a/).  Created automatically."),
        show_default=False,
    ),
    config: str | None = typer.Option(  # noqa: B008
        None,
        "--config",
        help="Optional path to oscal-generate.json config file.",
        show_default=False,
    ),
) -> None:
    """Generate OSCAL artifacts (POA&M + SSP) from a Plane 3 evidence bundle.

    This command is the CLI surface for Plane 4 of the UIAO pipeline.
    It is a thin wrapper around
    `uiao.oscal.generator.generate_oscal`, which is kept
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
    from uiao.oscal.generator import generate_oscal

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


@oscal_app.command("ksi-ar")
def ksi_ar_command(
    output: str = typer.Option(  # noqa: B008
        "output/artifacts/ksi-ar.json",
        "--output",
        "-o",
        help="Destination path for the KSI OSCAL Assessment Results JSON.",
    ),
    system_name: str = typer.Option(  # noqa: B008
        "UIAO Federal AAN Assessment System",
        "--system-name",
        help="Human-readable name for the assessed system.",
    ),
    ap_href: str = typer.Option(  # noqa: B008
        "",
        "--ap-href",
        help="Optional href to an existing Assessment Plan (OSCAL import-ap).",
    ),
    slots_dir: str | None = typer.Option(  # noqa: B008
        None,
        "--slots-dir",
        help=("Path to the AAN slot evidence YAML directory. Defaults to the bundled fedramp_aan_catalog/mappings/."),
    ),
) -> None:
    """Generate an OSCAL Assessment Results document from KSI slot evidence.

    Reads ksi-mapping.yaml and all AAN slot evidence YAML files (slot-01..06)
    and emits an OSCAL AR with per-KSI satisfied / not-satisfied / not-evaluated
    verdicts based on mapping confidence and slot binding coverage.

    \\b
    Output
    ------
    A single OSCAL 1.0.4 Assessment Results JSON file at --output.

    \\b
    Examples
    --------
        uiao oscal ksi-ar

        uiao oscal ksi-ar --output exports/oscal/ksi-ar.json

        uiao oscal ksi-ar \\
            --output exports/oscal/ksi-ar.json \\
            --system-name "SSA GCC Moderate" \\
            --ap-href "#assessment-plan-uuid"
    """
    from pathlib import Path as _Path

    from uiao.oscal.ksi_ar import build_ksi_ar_summary, export_ksi_ar

    try:
        resolved_slots = _Path(slots_dir) if slots_dir else None
        path = export_ksi_ar(
            output_path=output,
            system_name=system_name,
            ap_href=ap_href,
            slots_dir=resolved_slots,
        )
        import json

        ar_doc = json.loads(_Path(path).read_text(encoding="utf-8"))
        _console.print(f"[green]Wrote KSI Assessment Results to {path}[/green]")
        _console.print(build_ksi_ar_summary(ar_doc))
    except FileNotFoundError as exc:
        _console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    except ValueError as exc:
        _console.print(f"[red]Validation error:[/red] {exc}")
        raise typer.Exit(code=1) from exc


@oscal_app.command("validate")
def validate(
    path: str = typer.Argument(..., help="Path to OSCAL JSON file."),
) -> None:
    """Validate an OSCAL document against its schema.

    Example::

        uiao oscal validate exports/oscal/uiao-ssp.json
    """
    _console.print(f"[bold]Validating {path}...[/bold]")
    _console.print("[red]OSCAL validate is not implemented yet.[/red]")
    raise typer.Exit(code=2)


@oscal_app.command("validate-ssp")
def validate_ssp(
    oscal_dir: str = typer.Option(
        "exports/oscal",
        "--oscal-dir",
        "-d",
        help="Directory containing OSCAL JSON artifacts.",
    ),
) -> None:
    """Validate OSCAL artifacts with compliance-trestle Pydantic models.

    Example::

        uiao oscal validate-ssp --oscal-dir exports/oscal
    """
    from uiao.generators.trestle import validate_oscal_artifacts

    _console.print(f"[bold]Validating OSCAL artifacts in {oscal_dir}...[/bold]")
    failures = validate_oscal_artifacts(Path(oscal_dir))
    if failures:
        _console.print(f"[red]{failures} validation failure(s)[/red]")
        raise typer.Exit(code=1)
    _console.print("[green]All artifacts passed validation.[/green]")
