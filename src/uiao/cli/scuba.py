"""uiao.cli.scuba — Typer sub-application for the SCuBA->IR plane.

Registered on the root ``uiao`` app as the ``scuba`` command group so
callers use::

    uiao scuba transform --input ./input/scuba/tenant-a.json \\
                         --out   ./output/ir/tenant-a.ir.json \\
                         --config ./config/scuba-transform.json

The module exposes ``scuba_app`` (a ``typer.Typer`` instance) which is
mounted by ``uiao.cli.app`` via ``app.add_typer()``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

scuba_app = typer.Typer(
    name="scuba",
    help="SCuBA assessment operations (Plane 1: SCuBA -> IR).",
    no_args_is_help=True,
)

console = Console()


@scuba_app.command("transform")
def transform_cmd(  # noqa: B008
    input_path: Path = typer.Option(  # noqa: B008
        ...,
        "--input",
        "-i",
        help="Path to SCuBA JSON or YAML assessment file.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
    ),
    output_path: Path = typer.Option(  # noqa: B008
        ...,
        "--out",
        "-o",
        help="Destination path for the IR JSON artefact.",
        resolve_path=True,
    ),
    config_path: Optional[Path] = typer.Option(  # noqa: B008
        None,
        "--config",
        "-c",
        help="Optional path to scuba-transform.json / .yaml config.",
        resolve_path=True,
    ),
) -> None:
    """Transform a SCuBA assessment file into canonical IR JSON (Plane 1).

    Reads a SCuBA normalized JSON/YAML artefact, applies optional config
    overrides, runs the canonical SCuBATransformResult pipeline, and writes
    the resulting IR evidence bundle to --out.

    A timestamped log file is written automatically to
    ``<out_parent>/../logs/<timestamp>-scuba-transform.log``.
    """
    from uiao.adapters.scuba.transform import transform_scuba_to_ir

    console.print(
        f"[bold cyan]SCuBA -> IR[/bold cyan]  "
        f"[dim]{input_path.name}[/dim] -> [dim]{output_path.name}[/dim]"
    )

    try:
        transform_scuba_to_ir(
            input_path=str(input_path),
            output_path=str(output_path),
            config_path=str(config_path) if config_path else None,
        )
    except FileNotFoundError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Unexpected error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print("[green]✓ Done.[/green]")

