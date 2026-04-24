"""UIAO CLI application.

Provides command-line interface for OSCAL document generation,
validation, and canon management.
"""

from __future__ import annotations

import typer
from rich.console import Console

from uiao.__version__ import __version__

app = typer.Typer(
    name="uiao",
    help="UIAO: OSCAL compliance toolkit for US Government systems.",
    add_completion=False,
)

console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"uiao {__version__}")
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
    """UIAO OSCAL compliance toolkit."""


# ---------------------------------------------------------------------------
# Sub-app registrations (canonical CLI surface — see ADR-046)
# ---------------------------------------------------------------------------
from uiao.cli.adapter import adapter_app  # noqa: E402
from uiao.cli.canon import canon_app  # noqa: E402
from uiao.cli.conmon import conmon_app  # noqa: E402
from uiao.cli.cql import cql_app  # noqa: E402
from uiao.cli.evidence import evidence_app  # noqa: E402
from uiao.cli.generate import generate_app  # noqa: E402
from uiao.cli.ir import ir_app  # noqa: E402
from uiao.cli.ksi import ksi_app  # noqa: E402
from uiao.cli.orchestrator import orchestrator_app  # noqa: E402
from uiao.cli.oscal import oscal_app  # noqa: E402
from uiao.cli.scuba import scuba_app  # noqa: E402
from uiao.cli.substrate import substrate_app  # noqa: E402

app.add_typer(adapter_app, name="adapter")
app.add_typer(canon_app, name="canon")
app.add_typer(conmon_app, name="conmon")
app.add_typer(cql_app, name="cql")
app.add_typer(evidence_app, name="evidence")
app.add_typer(generate_app, name="generate")
app.add_typer(ir_app, name="ir")
app.add_typer(ksi_app, name="ksi")
app.add_typer(orchestrator_app, name="orchestrator")
app.add_typer(oscal_app, name="oscal")
app.add_typer(scuba_app, name="scuba")
app.add_typer(substrate_app, name="substrate")


if __name__ == "__main__":
    app()
