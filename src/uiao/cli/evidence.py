"""uiao.cli.evidence — Typer sub-app for the `uiao evidence` command group.

Mount point
-----------
    # in uiao/impl/cli/app.py
    from uiao.cli.evidence import evidence_app
    app.add_typer(evidence_app, name="evidence")

Usage (after `pip install -e .`)
---------------------------------
    uiao evidence build \\
        --input  ./output/ksi/tenant-a.ksi.json \\
        --output ./output/evidence/tenant-a/ \\
        --config ./config/evidence-build.json

    uiao evidence graph \\
        --input  ./output/scuba/normalized.json \\
        --trace  AC-2

Or via module invocation:
    python -m uiao.cli evidence build \\
        --input  ./output/ksi/tenant-a.ksi.json \\
        --output ./output/evidence/tenant-a/
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path

import typer
from rich.console import Console

from uiao.evidence.builder import build_evidence

evidence_app = typer.Typer(
    name="evidence",
    help="Evidence bundle operations.",
    add_completion=False,
)

_console = Console()


class EvidenceFormat(str, Enum):
    table = "table"
    json = "json"


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
    config: str | None = typer.Option(  # noqa: B008
        None,
        "--config",
        help="Optional path to evidence-build.json config file.",
        show_default=False,
    ),
) -> None:
    """Build a canonical evidence bundle from a KSI result JSON file.

    This command is the CLI surface for Plane 3 of the UIAO pipeline.
    It is a thin wrapper around
    `uiao.evidence.builder.build_evidence`, which is kept
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


@evidence_app.command("graph")
def graph_command(
    input: str = typer.Option(  # noqa: B008
        ...,
        "--input",
        "-i",
        help="Path to a normalized SCuBA JSON file (Plane 1 output).",
        show_default=False,
    ),
    trace: str | None = typer.Option(  # noqa: B008
        None,
        "--trace",
        "-t",
        help=(
            "Trace a specific control ID through the graph. "
            "SCuBA → IR bundles use KSI IDs (e.g. KSI-IA-02); "
            "use the same IDs shown in ``uiao ir-scuba-transform`` output."
        ),
    ),
    output: str | None = typer.Option(  # noqa: B008
        None,
        "--output",
        "-o",
        help="Write graph stats (or trace result) as JSON to this file.",
    ),
    fmt: EvidenceFormat = typer.Option(  # noqa: B008
        EvidenceFormat.table,
        "--format",
        "-f",
        help="Output format: table | json",
    ),
) -> None:
    """Build and inspect an Evidence Graph (UIAO_113) from a SCuBA run.

    The Evidence Graph is a directed property graph that links controls,
    IR objects, evidence nodes, provenance records, findings, and POA\\&M
    entries.  Every edge carries typed metadata so you can trace any
    compliance claim back to its raw assessment output.

    \\b
    Examples
    --------
    Print graph statistics for a SCuBA run:

        uiao evidence graph --input normalized.json

    Trace a specific control through the graph:

        uiao evidence graph --input normalized.json --trace KSI-IA-02

    Export graph statistics as JSON:

        uiao evidence graph --input normalized.json --format json --output graph.json
    """
    from uiao.adapters.scuba.ir.transformer import transform_scuba_to_ir
    from uiao.evidence.bundle import build_bundle_from_transform_result
    from uiao.evidence.graph import EvidenceGraph

    # ── Build graph ──────────────────────────────────────────────────────────
    input_path = Path(input)
    if not input_path.exists():
        _console.print(f"[red]Input file not found: {input_path}[/red]")
        raise typer.Exit(code=1)

    try:
        result = transform_scuba_to_ir(str(input_path))
        bundle = build_bundle_from_transform_result(result)
        graph = EvidenceGraph.from_evidence_bundle(bundle)
    except json.JSONDecodeError as exc:
        _console.print(f"[red]Invalid JSON in input file: {exc}[/red]")
        raise typer.Exit(code=1) from exc
    except (ValueError, KeyError) as exc:
        _console.print(f"[red]Failed to build evidence graph: {exc}[/red]")
        raise typer.Exit(code=1) from exc
    stats = graph.stats()

    # ── Trace or stats ────────────────────────────────────────────────────────
    if trace:
        trace_result = graph.trace_control(trace)
        if fmt is EvidenceFormat.json:
            out = json.dumps(trace_result, indent=2, ensure_ascii=False)
            if output:
                Path(output).parent.mkdir(parents=True, exist_ok=True)
                Path(output).write_text(out, encoding="utf-8")
                _console.print(f"[green]Trace written to {output}[/green]")
            else:
                typer.echo(out)
        else:
            _console.print(f"[bold]Trace: {trace}[/bold]")
            # Evidence nodes are nested inside ir_objects; flatten into a single list
            ir_objects = trace_result.get("ir_objects", [])
            all_evidence = [ev for iro in ir_objects for ev in iro.get("evidence", [])]
            findings = trace_result.get("findings", [])
            poam_entries = [po for f in findings for po in f.get("poam_entries", [])]
            _console.print(f"  Evidence nodes : {len(all_evidence)}")
            _console.print(f"  Findings       : {len(findings)}")
            _console.print(f"  POA\\&M entries : {len(poam_entries)}")
            if all_evidence:
                from rich.table import Table

                table = Table(show_header=True, header_style="bold blue")
                table.add_column("evidence_id")
                table.add_column("verdict")
                for ev in all_evidence:
                    verdict = ev.get("verdict", "")
                    style = {"pass": "green", "fail": "red", "warn": "yellow"}.get(verdict, "")
                    table.add_row(ev.get("id", ""), f"[{style}]{verdict}[/{style}]" if style else verdict)
                _console.print(table)
            if output:
                Path(output).parent.mkdir(parents=True, exist_ok=True)
                Path(output).write_text(json.dumps(trace_result, indent=2, ensure_ascii=False), encoding="utf-8")
                _console.print(f"[green]Trace written to {output}[/green]")
    else:
        if fmt is EvidenceFormat.json:
            out = json.dumps(stats, indent=2, ensure_ascii=False)
            if output:
                Path(output).parent.mkdir(parents=True, exist_ok=True)
                Path(output).write_text(out, encoding="utf-8")
                _console.print(f"[green]Graph stats written to {output}[/green]")
            else:
                typer.echo(out)
        else:
            _console.print("[bold]Evidence Graph Statistics[/bold]")
            _console.print(f"  Total nodes    : {stats['total_nodes']}")
            _console.print(f"  Total edges    : {stats['total_edges']}")
            _console.print("[bold]Nodes by type:[/bold]")
            for ntype, count in sorted(stats.get("nodes_by_type", {}).items()):
                _console.print(f"  {ntype:<15} {count}")
            _console.print("[bold]Edges by type:[/bold]")
            for etype, count in sorted(stats.get("edges_by_type", {}).items()):
                _console.print(f"  {etype:<20} {count}")
            if output:
                Path(output).parent.mkdir(parents=True, exist_ok=True)
                Path(output).write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
                _console.print(f"[green]Graph stats written to {output}[/green]")


@evidence_app.command("links")
def links_command(
    control: list[str] = typer.Option(  # noqa: B008
        [],
        "--control",
        help="Control(s) to render (CA-3, CA-9, SA-9, AC-20). Default: all four.",
    ),
    fmt: EvidenceFormat = typer.Option(  # noqa: B008
        EvidenceFormat.table,
        "--format",
        help="Output format: table (markdown appendix) or json.",
    ),
    output: str = typer.Option(  # noqa: B008
        "",
        "--output",
        help="Optional path to write the rendered inventory.",
    ),
    include_inactive: bool = typer.Option(  # noqa: B008
        False,
        "--include-inactive",
        help="Include proposed/retired links in the inventory.",
    ),
) -> None:
    """Render the external-interconnection inventory from the link registry.

    The registry (UIAO_145 / ADR-132) is the authoritative CA-3 evidence
    source; this command renders the per-control inventory that replaces
    the retired document-library pointer pattern.
    """
    from uiao.evidence.links import link_evidence_inventory, render_markdown

    try:
        inventory = link_evidence_inventory(
            tuple(control) if control else None,
            include_inactive=include_inactive,
        )
    except ValueError as exc:
        _console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    except OSError as exc:
        _console.print(f"[red]Error loading link registry:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    if fmt is EvidenceFormat.json:
        rendered = json.dumps(inventory, indent=2, ensure_ascii=False)
    else:
        rendered = render_markdown(inventory)

    if output:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(rendered + "\n", encoding="utf-8")
        _console.print(f"[green]Link evidence inventory written to {output}[/green]")
    else:
        typer.echo(rendered)
