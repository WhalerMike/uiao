"""UIAO command-line interface.

Exposes the ``uiao`` console script defined in ``pyproject.toml``
(``[project.scripts] uiao = "uiao.cli:app"``).
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from . import __version__

app = typer.Typer(
    name="uiao",
    help="Unified Identity-Addressing-Overlay Architecture CLI.",
    rich_markup_mode="rich",
    no_args_is_help=True,
)

gos_app = typer.Typer(
    name="gos",
    help="Governance Operating System commands.",
    no_args_is_help=True,
)
app.add_typer(gos_app, name="gos")

console = Console()


def bundled_canon_path() -> Path:
    """Return the path to the canon/ directory bundled inside the package.

    Using ``importlib.resources`` means users never need to pass
    ``--canon-path`` — the YAML SSOT ships with the installed package.
    """
    return Path(str(resources.files("uiao").joinpath("canon")))


def _resolve_canon(canon_path: Optional[Path]) -> Path:
    return canon_path if canon_path is not None else bundled_canon_path()


@app.command()
def version() -> None:
    """Show UIAO version."""
    console.print(f"UIAO version [bold cyan]{__version__}[/bold cyan]")


@app.command()
def validate(
    canon_path: Optional[Path] = typer.Option(
        None,
        "--canon-path",
        help="Override the bundled canon directory (rarely needed).",
    ),
) -> None:
    """Validate the canon YAML SSOT against the UIAO schemas."""
    canon = _resolve_canon(canon_path)
    console.print(f"[bold]Validating canon:[/bold] {canon}")
    console.print("[yellow]validate[/yellow]: not yet implemented in the consolidated monorepo.")


@app.command("generate-ssp")
def generate_ssp(
    out: Path = typer.Option(Path("build/ssp.json"), "--out", help="Output OSCAL SSP path."),
    canon_path: Optional[Path] = typer.Option(None, "--canon-path"),
) -> None:
    """Generate a FedRAMP OSCAL SSP from the canon YAML."""
    canon = _resolve_canon(canon_path)
    console.print(f"[bold]Generating SSP[/bold] from {canon} -> {out}")
    console.print("[yellow]generate-ssp[/yellow]: not yet implemented in the consolidated monorepo.")


@app.command("drift-check")
def drift_check(
    canon_path: Optional[Path] = typer.Option(None, "--canon-path"),
) -> None:
    """Run drift detection against the live posture."""
    canon = _resolve_canon(canon_path)
    console.print(f"[bold]Drift check[/bold] against {canon}")
    console.print("[yellow]drift-check[/yellow]: not yet implemented in the consolidated monorepo.")


@gos_app.command("status")
def gos_status() -> None:
    """Show the current GOS (Governance Operating System) status."""
    console.print("[yellow]gos status[/yellow]: not yet implemented in the consolidated monorepo.")


if __name__ == "__main__":
    app()
