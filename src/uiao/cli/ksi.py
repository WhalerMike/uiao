"""uiao.cli.ksi — Typer sub-app for the `uiao ksi` command group.

Mount point
-----------
    # in uiao/impl/cli/app.py
    from uiao.cli.ksi import ksi_app
    app.add_typer(ksi_app, name="ksi")

Usage (after `pip install -e .`)
---------------------------------
    uiao ksi evaluate \\
        --ir  ./output/ir/tenant-a.ir.json \\
        --out ./output/ksi/tenant-a.ksi.json \\
        --config ./config/ksi-rules.json

Or via module invocation:
    python -m uiao.cli ksi evaluate \\
        --ir  ./output/ir/tenant-a.ir.json \\
        --out ./output/ksi/tenant-a.ksi.json
"""
from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

from uiao.ksi.evaluate import evaluate_ksi

ksi_app = typer.Typer(
    name="ksi",
    help="KSI evaluation operations.",
    add_completion=False,
)

_console = Console()


@ksi_app.command("evaluate")
def evaluate_command(
    ir: str = typer.Option(  # noqa: B008
        ...,
        "--ir",
        help="Path to the IR JSON envelope produced by Plane 1 (scuba transform).",
        show_default=False,
    ),
    out: str = typer.Option(  # noqa: B008
        ...,
        "--out",
        help="Destination path for the KSI result JSON (e.g. ./output/ksi/source.ksi.json).",
        show_default=False,
    ),
    config: Optional[str] = typer.Option(  # noqa: B008
        None,
        "--config",
        help="Optional path to ksi-rules.json config file.",
        show_default=False,
    ),
) -> None:
    """Evaluate an IR file against KSI rules and emit a canonical KSI result JSON.

    This command is the CLI surface for Plane 2 of the UIAO pipeline.
    It is a thin wrapper around `uiao.ksi.evaluate.evaluate_ksi`,
    which is kept intentionally pure (no CLI, no side-effects beyond file I/O).

    \\b
    Examples
    --------
    Minimal (no config):

        uiao ksi evaluate \\
            --ir  ./output/ir/tenant-a.ir.json \\
            --out ./output/ksi/tenant-a.ksi.json

    With config:

        uiao ksi evaluate \\
            --ir    ./output/ir/tenant-a.ir.json \\
            --out   ./output/ksi/tenant-a.ksi.json \\
            --config ./config/ksi-rules.json
    """
    try:
        evaluate_ksi(
            ir_path=ir,
            output_path=out,
            config_path=config,
        )
    except FileNotFoundError as exc:
        _console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    except ValueError as exc:
        _console.print(f"[red]Validation error:[/red] {exc}")
        raise typer.Exit(code=1) from exc


