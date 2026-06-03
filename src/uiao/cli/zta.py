"""uiao.cli.zta — Typer sub-application for the Zero Trust Assessment adapter.

Registered on the root ``uiao`` app as the ``zta`` command group::

    uiao zta digest --input ZeroTrustAssessmentReport.html --out-dir ./out
    uiao zta digest -i report.json -o ./out --format xlsx --format csv --risk High --risk Medium

Digests a Microsoft Zero Trust Assessment report (``.html`` or ``.json``) into
human-facing artefacts: an executive summary, a full Markdown digest, an Excel
workbook, a slim annotated HTML companion, and a worklist CSV.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from uiao.adapters.zta import Triage, build_triage, load_report
from uiao.adapters.zta.ingest import ZtIngestError
from uiao.adapters.zta.model import STATUS_ORDER
from uiao.adapters.zta.render import resolve_formats, write_outputs
from uiao.adapters.zta.triage import RISK_ORDER

zta_app = typer.Typer(
    name="zta",
    help="Microsoft Zero Trust Assessment digest (ingest report -> human-facing artefacts).",
    no_args_is_help=True,
)

console = Console()


@zta_app.command("digest")
def digest_cmd(  # noqa: B008
    input_path: Path = typer.Option(  # noqa: B008
        ...,
        "--input",
        "-i",
        help="Path to a ZeroTrustAssessmentReport .html or .json file.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
    ),
    out_dir: Path = typer.Option(  # noqa: B008
        Path("./zt-digest"),
        "--out-dir",
        "-o",
        help="Directory to write digest artefacts into.",
        resolve_path=True,
    ),
    formats: list[str] = typer.Option(  # noqa: B008
        ["all"],
        "--format",
        "-f",
        help="Output formats: exec, md, xlsx, html, csv, or all. Repeatable.",
    ),
    risks: list[str] = typer.Option(  # noqa: B008
        ["High"],
        "--risk",
        "-r",
        help="Risk levels to include in the worklist (High/Medium/Low). Repeatable.",
    ),
) -> None:
    """Ingest a Zero Trust Assessment report and write digest artefacts."""
    try:
        chosen = resolve_formats(formats)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    try:
        report = load_report(input_path)
    except (ZtIngestError, ValueError) as exc:
        console.print(f"[red]Error:[/red] {input_path.name}: {exc}")
        raise typer.Exit(code=1) from exc

    risk_tuple = tuple(r for r in RISK_ORDER if r in set(risks)) or ("High",)
    triage = build_triage(report, risks=risk_tuple)

    _print_summary(triage)

    written = write_outputs(triage, out_dir, chosen)
    console.print(f"\n[green]✓[/green] wrote {len(written)} file(s) to [bold]{out_dir}[/bold]:")
    for path in written:
        console.print(f"  [dim]{path.name}[/dim]")

    if report.is_demo:
        console.print("\n[yellow]Note:[/yellow] this is Microsoft's DEMO report (IsDemo=true).")
    console.print("[dim]Findings are Controlled tenant data — keep in-boundary; do not publish raw results.[/dim]")


def _print_summary(triage: Triage) -> None:
    """Print the honest roll-up to the console."""
    r = triage.report
    demo = " [yellow](DEMO)[/yellow]" if r.is_demo else ""
    console.print(
        f"[bold cyan]Zero Trust Assessment[/bold cyan]{demo}  "
        f"[dim]{r.tenant_name} · v{r.current_version} · {len(r.tests)} checks[/dim]"
    )
    table = Table(show_header=True, header_style="bold")
    table.add_column("Status")
    table.add_column("Count", justify="right")
    table.add_column("Note", style="dim")
    notes = {
        "Failed": "finding",
        "Investigate": "finding",
        "Passed": "",
        "Skipped": "non-gap (not applicable / unlicensed)",
        "Planned": "non-gap (tool roadmap)",
        "Error": "could not run",
    }
    for status in STATUS_ORDER:
        count = triage.status_counts.get(status, 0)
        if count:
            table.add_row(status, str(count), notes.get(status, ""))
    console.print(table)
    console.print(
        f"[bold]{triage.actionable_total}[/bold] actionable · "
        f"[bold]{len(triage.worklist)}[/bold] in worklist (risk={'/'.join(triage.risks)}) · "
        f"[bold]{triage.premium_gated_total}[/bold] premium-SKU-gated of {len(r.tests)}"
    )
