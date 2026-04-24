"""uiao.cli.canon — Typer sub-app for the `uiao canon` command group.

Mount point
-----------
    # in uiao/cli/app.py
    from uiao.cli.canon import canon_app
    app.add_typer(canon_app, name="canon")

Usage (after `pip install -e .`)
---------------------------------
    uiao canon check --dir canon

Or via module invocation:
    python -m uiao.cli canon check --dir canon
"""

from __future__ import annotations

import typer
from rich.console import Console

canon_app = typer.Typer(
    name="canon",
    help="Canon authority operations (consistency checks, etc.).",
    add_completion=False,
)

_console = Console()


@canon_app.command("check")
def canon_check(
    canon_dir: str = typer.Option("canon", "--dir", "-d", help="Canon directory."),
) -> None:
    """Check canon YAML files for consistency.

    Example::

        uiao canon check --dir src/uiao/canon
    """
    _console.print(f"[bold]Checking canon at {canon_dir}...[/bold]")
    _console.print("[yellow]Canon check not yet implemented (Week 3).[/yellow]")
