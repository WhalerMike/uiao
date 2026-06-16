"""uiao.cli.upgrade — Typer sub-app for the `uiao upgrade` command.

Mount point
-----------
    # in uiao/cli/app.py
    from uiao.cli.upgrade import upgrade_app
    app.add_typer(upgrade_app, name="upgrade")

Usage (after ``pip install -e .``)
-----------------------------------
    uiao upgrade
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import typer
from rich.console import Console

from uiao.__version__ import __version__

upgrade_app = typer.Typer(
    name="upgrade",
    help="Check GitHub Releases for a newer version of uiao.",
    add_completion=False,
    invoke_without_command=True,
)

_console = Console()

_RELEASES_URL = "https://api.github.com/repos/WhalerMike/uiao/releases/latest"


def _parse_version(tag: str) -> tuple[int, ...]:
    """Parse a semver tag like 'v0.6.1' or '0.6.1' into a comparable tuple."""
    tag = tag.lstrip("v")
    parts = []
    for part in tag.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(0)
    return tuple(parts)


@upgrade_app.callback()
def upgrade() -> None:
    """Check GitHub Releases API for a newer version of uiao."""
    _console.print(f"Current version: [bold]{__version__}[/bold]")

    try:
        req = urllib.request.Request(
            _RELEASES_URL,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": f"uiao/{__version__}",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.URLError as exc:
        _console.print(
            f"[yellow]Could not reach GitHub Releases API:[/yellow] {exc}\n"
            "Check your internet connection and try again."
        )
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        _console.print(f"[yellow]Unexpected error checking for updates:[/yellow] {exc}")
        raise typer.Exit(code=1) from exc

    tag = data.get("tag_name", "")
    html_url = data.get("html_url", _RELEASES_URL)

    if not tag:
        _console.print("[yellow]GitHub returned a release with no tag_name — cannot compare versions.[/yellow]")
        raise typer.Exit(code=1)

    latest_tuple = _parse_version(tag)
    current_tuple = _parse_version(__version__)

    if latest_tuple > current_tuple:
        latest_display = tag.lstrip("v")
        _console.print(
            f"\n[bold green]A newer version is available: {latest_display}[/bold green]\n"
            f"Release notes: {html_url}\n\n"
            f"To upgrade, run:\n"
            f"  [bold cyan]pip install --upgrade uiao[/bold cyan]\n"
        )
    else:
        _console.print(f"[bold green]Already at latest version {__version__}.[/bold green]")
