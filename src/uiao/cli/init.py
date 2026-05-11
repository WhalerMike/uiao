"""UIAO ``init`` — new-user entry point.

``uiao init`` is the 10-minute new-adopter on-ramp. It does two things:

- **Default mode** — prints a welcome banner, a five-step walkthrough,
  and the canon-doc links a new reader should open first.
- ``--demo`` mode — runs the bundled quickstart auditor-bundle pipeline
  against ``examples/quickstart/scuba-normalized.json`` and prints the
  output artifact paths.

This command is read-only against the user's environment: it never
writes to ``$HOME``, never touches the user's shell config, and never
mutates the repo. The ``--demo`` mode writes only to the directory
passed via ``--out-dir`` (default ``/tmp/uiao-quickstart``).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console

init_app = typer.Typer(name="init", help="Welcome + 10-minute new-user walkthrough.")
_console = Console()


_WELCOME_BANNER = """
[bold cyan]UIAO — Universal Identity-Addressing-Overlay Architecture[/bold cyan]

Governance OS for FedRAMP-Moderate identity, telemetry, policy, and
enforcement modernization. Identity-first. Canon-anchored. Drift-detected.

This is an OSS reference architecture, not a hosted service. Everything
runs locally from this repo.
"""

_WALKTHROUGH_STEPS = [
    (
        "1. Verify the substrate is healthy",
        "uiao substrate walk",
        (
            "Reads the canonical substrate manifest (`UIAO_200`) and the workspace contract "
            "(`UIAO_201`), walks the declared module paths, and reports drift findings. "
            "Should exit 0 on a clean checkout."
        ),
    ),
    (
        "2. Run the bundled quickstart pipeline",
        "uiao init --demo",
        (
            "Builds an auditor bundle from `examples/quickstart/scuba-normalized.json` — a "
            "synthetic ScubaGear assessment for a 10-user test tenant. Produces real "
            "Evidence, POA&M, and SSP narrative artifacts you can inspect. No Azure tenant, "
            "no API keys, no live data required."
        ),
    ),
    (
        "3. Read the canon entry points",
        None,
        (
            "Repository invariants and the agent integration guide live in "
            "[underline]AGENTS.md[/underline]. The substrate manifest "
            "([underline]src/uiao/canon/substrate-manifest.yaml[/underline]) declares "
            "every module the substrate governs. The drift taxonomy is formalized in "
            "[underline]docs/docs/16_DriftDetectionStandard.qmd[/underline]."
        ),
    ),
    (
        "4. Walk the OrgPath Narrative",
        None,
        (
            "The 15-chapter narrative at "
            "[underline]docs/customer-documents/orgpath-narrative/[/underline] is the "
            "explanatory companion to the canon. Read in order; each chapter walks the "
            "OrgPath attribute through one Microsoft surface (Intune, Defender, Purview, "
            "Application Identity, Azure Policy, ...). Chapter 07a covers the Azure SSOT "
            "stack identity foundation."
        ),
    ),
    (
        "5. Try an adapter conformance pass",
        "uiao adapter run --help",
        (
            "Conformance and modernization adapters are the substrate's interface to the "
            "outside world. The ScubaGear adapter is the canonical Phase-1 conformance "
            "adapter; the AD survey adapter is the canonical Phase-1 modernization "
            "adapter. Try `uiao adapter run --help` for available adapters."
        ),
    ),
]


_CANON_REFS = [
    ("Federal SSOT alignment whitepaper", "docs/customer-documents/whitepapers/federal-ssot-alignment.qmd"),
    ("Drift Detection Standard", "docs/docs/16_DriftDetectionStandard.qmd"),
    (
        "Reference deployment pattern",
        "docs/customer-documents/case-studies/reference-deployment-fedciv-ad-to-entra.qmd",
    ),
    ("NIST + FICAM cross-walk", "docs/customer-documents/compliance/federal-mandates/nist-icam-crosswalk.qmd"),
    (
        "GCC-Moderate boundary model",
        "docs/customer-documents/compliance/boundary-authorization/B1-gcc-moderate-boundary-model.qmd",
    ),
    (
        "Three-way GCC-Moderate compliance conflict",
        "docs/customer-documents/compliance/boundary-authorization/B1-1-gcc-moderate-three-way-conflict.qmd",
    ),
]


def _print_walkthrough() -> None:
    """Emit the five-step new-user walkthrough."""
    _console.print(_WELCOME_BANNER)
    _console.print("[bold]10-minute new-user walkthrough[/bold]")
    _console.print("")
    for title, command, description in _WALKTHROUGH_STEPS:
        _console.print(f"[bold green]{title}[/bold green]")
        if command is not None:
            _console.print(f"  [cyan]$ {command}[/cyan]")
        _console.print(f"  {description}")
        _console.print("")
    _console.print("[bold]Canon entry points[/bold]")
    _console.print("")
    for label, path in _CANON_REFS:
        _console.print(f"  • {label} — [underline]{path}[/underline]")
    _console.print("")
    _console.print(
        "[dim]This command is read-only against your environment. It never writes "
        "to $HOME, never edits shell config, never mutates the repo. The "
        "--demo mode writes only to the directory passed via --out-dir.[/dim]"
    )


def _run_demo(out_dir: Path) -> int:
    """Invoke the auditor-bundle pipeline against the bundled quickstart fixture.

    Uses subprocess.run so the demo path is identical to what a user would
    type at the shell. Returns the subprocess exit code.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    fixture = repo_root / "examples" / "quickstart" / "scuba-normalized.json"

    if not fixture.exists():
        _console.print(
            f"[red]Quickstart fixture not found at {fixture}[/red]\n"
            "This usually means uiao was installed without the bundled "
            "examples — run from a git checkout."
        )
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    _console.print("[bold]Running auditor-bundle pipeline...[/bold]")
    _console.print(f"  fixture : [cyan]{fixture}[/cyan]")
    _console.print(f"  out-dir : [cyan]{out_dir}[/cyan]")
    _console.print("")

    cmd = [
        sys.executable,
        "-m",
        "uiao.cli.app",
        "ir",
        "auditor-bundle",
        str(fixture),
        "--out-dir",
        str(out_dir),
    ]
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        _console.print(f"\n[red]Pipeline failed with exit code {result.returncode}.[/red]")
        return result.returncode

    _console.print("")
    _console.print(f"[green]Pipeline complete.[/green] Output artifacts in [cyan]{out_dir}[/cyan]:")
    for path in sorted(out_dir.rglob("*")):
        if path.is_file():
            _console.print(f"  • {path.relative_to(out_dir)}")
    _console.print("")
    _console.print(
        "[bold]Next:[/bold] open the generated artifacts to see what the substrate "
        "produced for a 10-user synthetic tenant. The POA&M, SSP narrative, and "
        "evidence bundle are all OSCAL-aligned."
    )
    return 0


@init_app.callback(invoke_without_command=True)
def init(
    ctx: typer.Context,
    demo: bool = typer.Option(
        False,
        "--demo",
        help="Run the bundled quickstart auditor-bundle pipeline end-to-end.",
    ),
    out_dir: Path = typer.Option(
        Path("/tmp/uiao-quickstart"),
        "--out-dir",
        "-o",
        help="Output directory for --demo mode artifacts.",
    ),
) -> None:
    """Welcome + 10-minute new-user walkthrough. Optionally run a demo pipeline."""
    # If a subcommand was invoked, defer to it (none currently registered, but
    # this keeps the callback non-blocking for future extension to --check etc.).
    if ctx.invoked_subcommand is not None:
        return

    if demo:
        rc = _run_demo(out_dir)
        if rc != 0:
            raise typer.Exit(code=rc)
        return

    _print_walkthrough()
