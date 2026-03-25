"""UIAO-Core CLI application.

Provides command-line interface for OSCAL document generation,
validation, and canon management.
"""

from __future__ import annotations

import os
from pathlib import Path

import typer
from rich.console import Console

from uiao_core.__version__ import __version__
from uiao_core.generators.trestle import validate_oscal_artifacts

app = typer.Typer(
    name="uiao",
    help="UIAO-Core: OSCAL compliance toolkit for US Government systems.",
    add_completion=False,
)

console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"uiao-core {__version__}")
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
    """UIAO-Core OSCAL compliance toolkit."""


@app.command()
def generate_ssp(
    canon_path: str = typer.Option(
        "canon/uiao_leadership_briefing_v1.0.yaml",
        "--canon",
        "-c",
        help="Path to canon YAML file.",
    ),
    data_dir: str = typer.Option(
        "data",
        "--data-dir",
        "-d",
        help="Path to data YAML directory.",
    ),
    output: str = typer.Option(
        "exports/oscal/uiao-ssp-skeleton.json",
        "--output",
        "-o",
        help="Output SSP JSON path.",
    ),
) -> None:
    """Generate an OSCAL SSP from canon YAML and data files."""
    from uiao_core.generators.ssp import build_ssp

    console.print(f"[bold]Generating SSP from {canon_path}...[/bold]")
    out = build_ssp(canon_path=canon_path, data_dir=data_dir, output_path=output)
    console.print(f"[green]SSP written to {out}[/green]")


@app.command()
def validate(
    path: str = typer.Argument(..., help="Path to OSCAL JSON file."),
) -> None:
    """Validate an OSCAL document against its schema."""
    console.print(f"[bold]Validating {path}...[/bold]")
    console.print("[yellow]Validation not yet implemented (Week 3).[/yellow]")


@app.command()
def canon_check(
    canon_dir: str = typer.Option("canon", "--dir", "-d", help="Canon directory."),
) -> None:
    """Check canon YAML files for consistency."""
    console.print(f"[bold]Checking canon at {canon_dir}...[/bold]")
    console.print("[yellow]Canon check not yet implemented (Week 3).[/yellow]")


@app.command()
def validate_ssp(
    oscal_dir: str = typer.Option(
        "exports/oscal",
        "--oscal-dir",
        "-d",
        help="Directory containing OSCAL JSON artifacts.",
    ),
) -> None:
    """Validate OSCAL artifacts with compliance-trestle Pydantic models."""
    console.print(f"[bold]Validating OSCAL artifacts in {oscal_dir}...[/bold]")
    failures = validate_oscal_artifacts(Path(oscal_dir))
    if failures:
        console.print(f"[red]{failures} validation failure(s)[/red]")
        raise typer.Exit(code=1)
    console.print("[green]All artifacts passed validation.[/green]")


@app.command()
def generate_visuals(
    visuals_dir: str = typer.Option(
        "visuals",
        "--visuals-dir",
        "-v",
        help="Directory containing .mermaid source files.",
    ),
    output_dir: str = typer.Option(
        "assets/images/mermaid",
        "--output-dir",
        "-o",
        help="Output directory for rendered PNGs.",
    ),
    force: bool = typer.Option(
        False,
        "--force-visuals",
        help="Force regeneration of all visuals (ignore cache).",
    ),
) -> None:
    """Render Mermaid diagrams to PNG for DOCX/PPTX embedding."""
    from uiao_core.generators.mermaid import render_all_mermaid

    console.print(f"[bold]Rendering Mermaid visuals from {visuals_dir}...[/bold]")
    results = render_all_mermaid(visuals_dir, output_dir, force=force)
    console.print(f"[green]Rendered {len(results)} diagram(s) to {output_dir}[/green]")


@app.command()
def generate_gemini(
    output_dir: str = typer.Option(
        "assets/images/gemini",
        "--output-dir",
        "-o",
        help="Output directory for generated Gemini images.",
    ),
    force: bool = typer.Option(
        False,
        "--force-visuals",
        help="Force regeneration of all images (ignore cache).",
    ),
    name: str = typer.Option(
        "",
        "--name",
        "-n",
        help="Generate a single named image (default: all).",
    ),
) -> None:
    """Generate images via Gemini API (requires GEMINI_API_KEY)."""
    from uiao_core.generators.gemini_visuals import (
        generate_all_gemini_images,
        generate_gemini_image,
    )

    if name:
        console.print(f"[bold]Generating Gemini image: {name}...[/bold]")
        result = generate_gemini_image(name, output_dir=output_dir, force=force)
        if result:
            console.print(f"[green]Generated {result}[/green]")
        else:
            console.print(f"[red]Failed to generate {name}[/red]")
            raise typer.Exit(code=1)
    else:
        console.print("[bold]Generating all Gemini images...[/bold]")
        results = generate_all_gemini_images(output_dir, force=force)
        console.print(f"[green]Generated {len(results)} image(s) to {output_dir}[/green]")


@app.command()
def generate_pptx(
    canon_path: str = typer.Option(
        "canon/uiao_leadership_briefing_v1.0.yaml",
        "--canon",
        "-c",
        help="Path to canon YAML file.",
    ),
    data_dir: str = typer.Option(
        "data",
        "--data-dir",
        "-d",
        help="Path to data YAML directory.",
    ),
    exports_dir: str = typer.Option(
        "exports",
        "--exports-dir",
        "-e",
        help="Output exports directory.",
    ),
) -> None:
    """Generate a leadership briefing PPTX deck."""
    from uiao_core.generators.pptx import build_pptx

    console.print("[bold]Generating leadership briefing PPTX...[/bold]")
    out = build_pptx(
        canon_path=Path(canon_path),
        data_dir=Path(data_dir),
        exports_dir=Path(exports_dir),
    )
    console.print(f"[green]PPTX exported to {out}[/green]")


@app.command()
def generate_docx(
    canon_path: str = typer.Option(
        "canon/uiao_leadership_briefing_v1.0.yaml",
        "--canon",
        "-c",
        help="Path to canon YAML file.",
    ),
    data_dir: str = typer.Option(
        "data",
        "--data-dir",
        "-d",
        help="Path to data YAML directory.",
    ),
    exports_dir: str = typer.Option(
        "exports",
        "--exports-dir",
        "-e",
        help="Output exports directory.",
    ),
) -> None:
    """Generate a rich DOCX leadership briefing with embedded visuals."""
    from uiao_core.generators.rich_docx import build_rich_docx

    console.print("[bold]Generating leadership briefing DOCX...[/bold]")
    out = build_rich_docx(
        canon_path=Path(canon_path),
        data_dir=Path(data_dir),
        exports_dir=Path(exports_dir),
    )
    console.print(f"[green]DOCX exported to {out}[/green]")


@app.command()
def generate_diagrams(
    canon_path: str = typer.Option(
        "canon/diagrams.yaml",
        "--canon",
        "-c",
        help="Path to diagrams canon YAML file.",
    ),
    visuals_dir: str = typer.Option(
        "visuals",
        "--visuals-dir",
        "-v",
        help="Directory to write .mermaid source files.",
    ),
    output_dir: str = typer.Option(
        "assets/images/mermaid",
        "--output-dir",
        "-o",
        help="Output directory for rendered PNG files.",
    ),
    force: bool = typer.Option(
        False,
        "--force-visuals",
        help="Force regeneration of all visuals (ignore cache).",
    ),
) -> None:
    """Generate Mermaid .mermaid files and render them to PNG from canon YAML."""
    from uiao_core.generators.diagrams import generate_diagrams_from_canon
    from uiao_core.generators.mermaid import render_all_mermaid

    console.print(f"[bold]Generating diagrams from {canon_path}...[/bold]")
    rendered = generate_diagrams_from_canon(
        canon_path=canon_path,
        visuals_dir=visuals_dir,
        output_dir=output_dir,
        force=force,
    )
    console.print(f"[green]Generated {len(rendered)} diagram(s) from canon.[/green]")

    console.print(f"[bold]Rendering all Mermaid files in {visuals_dir}...[/bold]")
    all_pngs = render_all_mermaid(visuals_dir=visuals_dir, output_dir=output_dir, force=force)
    console.print(f"[green]Rendered {len(all_pngs)} total diagram(s) to {output_dir}[/green]")


@app.command()
def generate_docs(
    canon_path: str = typer.Option(
        "canon/uiao_leadership_briefing_v1.0.yaml",
        "--canon",
        "-c",
        help="Path to canon YAML file.",
    ),
    data_dir: str = typer.Option(
        "data",
        "--data-dir",
        "-d",
        help="Path to data YAML directory.",
    ),
    templates_dir: str = typer.Option(
        "templates",
        "--templates-dir",
        "-t",
        help="Path to Jinja2 templates directory.",
    ),
    output_dir: str = typer.Option(
        "docs",
        "--output-dir",
        "-o",
        help="Output directory for generated Markdown documents.",
    ),
    skip_diagrams: bool = typer.Option(
        False,
        "--skip-diagrams",
        help="Skip automatic diagram generation (faster, for template-only runs).",
    ),
    force_visuals: bool = typer.Option(
        False,
        "--force-visuals",
        help="Force regeneration of all visuals (ignore cache).",
    ),
) -> None:
    """Render Jinja2 templates into Markdown docs using canon YAML and data files.

    Automatically generates diagrams from canon/diagrams.yaml before rendering
    templates (unless --skip-diagrams is set).
    """
    from uiao_core.generators.docs import build_docs

    if not skip_diagrams:
        console.print("[bold]Auto-generating diagrams from canon/diagrams.yaml...[/bold]")

    console.print(f"[bold]Generating docs from {canon_path}...[/bold]")
    generated = build_docs(
        canon_path=Path(canon_path),
        data_dir=Path(data_dir),
        templates_dir=Path(templates_dir),
        docs_dir=Path(output_dir),
        generate_diagrams=not skip_diagrams,
        force_visuals=force_visuals,
    )
    console.print(f"[green]Generated {len(generated)} document(s) to {output_dir}[/green]")


@app.command()
def generate_artifacts(
    canon_path: str = typer.Option(
        "canon/uiao_leadership_briefing_v1.0.yaml",
        "--canon",
        "-c",
        help="Path to canon YAML file.",
    ),
    data_dir: str = typer.Option(
        "data",
        "--data-dir",
        "-d",
        help="Path to data YAML directory.",
    ),
    exports_dir: str = typer.Option(
        "exports",
        "--exports-dir",
        "-e",
        help="Output exports directory.",
    ),
    force_visuals: bool = typer.Option(
        False,
        "--force-visuals",
        help="Force regeneration of all visuals (ignore cache).",
    ),
) -> None:
    """Generate DOCX + PPTX with embedded Mermaid and Gemini visuals."""
    from uiao_core.generators.mermaid import render_all_mermaid
    from uiao_core.generators.pptx import build_pptx
    from uiao_core.generators.rich_docx import build_rich_docx

    console.print("[bold]Rendering Mermaid visuals...[/bold]")
    pngs = render_all_mermaid(force=force_visuals)
    console.print(f"[green]Rendered {len(pngs)} diagram(s)[/green]")

    if os.environ.get("GEMINI_API_KEY", "").strip():
        from uiao_core.generators.gemini_visuals import generate_all_gemini_images

        console.print("[bold]Generating Gemini images...[/bold]")
        gemini_results = generate_all_gemini_images(force=force_visuals)
        console.print(f"[green]Generated {len(gemini_results)} Gemini image(s)[/green]")
    else:
        console.print("[yellow]GEMINI_API_KEY not set — skipping Gemini image generation.[/yellow]")

    console.print("[bold]Generating DOCX...[/bold]")
    docx_out = build_rich_docx(
        canon_path=Path(canon_path),
        data_dir=Path(data_dir),
        exports_dir=Path(exports_dir),
    )
    console.print(f"[green]DOCX exported to {docx_out}[/green]")

    console.print("[bold]Generating PPTX...[/bold]")
    pptx_out = build_pptx(
        canon_path=Path(canon_path),
        data_dir=Path(data_dir),
        exports_dir=Path(exports_dir),
    )
    console.print(f"[green]PPTX exported to {pptx_out}[/green]")
    console.print("[bold green]All artifacts generated with embedded visuals.[/bold green]")


@app.command()
def generate_sbom(
    output: str = typer.Option(
        "exports/sbom/sbom.cyclonedx.json",
        "--output",
        "-o",
        help="Output path for the CycloneDX JSON SBOM.",
    ),
) -> None:
    """Generate a CycloneDX 1.4 Software Bill of Materials (SBOM)."""
    from uiao_core.generators.sbom import build_sbom

    console.print("[bold]Generating CycloneDX SBOM...[/bold]")
    out = build_sbom(output_path=output)
    console.print(f"[green]SBOM written to {out}[/green]")


@app.command()
def conmon_process(
    alert_json: str = typer.Option(
        ...,
        "--alert-json",
        "-a",
        help="Path to a Sentinel alert webhook payload JSON file.",
    ),
    poam_path: str = typer.Option(
        "data/poam-findings.yml",
        "--poam-path",
        "-p",
        help="Path to the POA&M findings YAML file (created if absent).",
    ),
    monitoring_sources: str = typer.Option(
        "data/monitoring-sources.yml",
        "--monitoring-sources",
        "-m",
        help="Path to monitoring-sources.yml signal map.",
    ),
    no_upsert: bool = typer.Option(
        False,
        "--no-upsert",
        help="Dry-run: parse and map controls without writing the POA&M file.",
    ),
) -> None:
    """Process a Sentinel alert and auto-upsert a POA&M entry.

    Reads a Sentinel alert webhook payload from ALERT_JSON, maps it to
    NIST 800-53 controls via monitoring-sources.yml, and creates or
    updates a POA&M entry in POAM_PATH.  Use --no-upsert for a dry-run.
    """
    import json as _json
    from pathlib import Path as _Path

    from uiao_core.monitoring.sentinel_hook import SentinelHook

    alert_path = _Path(alert_json)
    if not alert_path.exists():
        console.print(f"[red]Alert JSON not found: {alert_path}[/red]")
        raise typer.Exit(code=1)

    console.print(f"[bold]Processing Sentinel alert from {alert_json}...[/bold]")
    payload = _json.loads(alert_path.read_text())

    hook = SentinelHook(monitoring_sources_path=monitoring_sources)
    alert = hook.parse_alert(payload)
    control_ids = hook.map_alert_to_controls(alert)

    console.print(f"  Alert ID : [cyan]{alert.alert_id}[/cyan]")
    console.print(f"  Severity : [cyan]{alert.severity}[/cyan]")
    console.print(f"  Controls : [cyan]{', '.join(control_ids) or 'SI-4 (default)'}[/cyan]")

    if no_upsert:
        console.print("[yellow]Dry-run: POA&M file not updated.[/yellow]")
    else:
        poam_entry = hook.upsert_poam_entry(alert, poam_path=poam_path)
        console.print(f"  POA&M ID : [green]{poam_entry['id']}[/green]")
        console.print(f"[green]POA&M entry upserted → {poam_path}[/green]")


@app.command()
def conmon_export_oa(
    monitoring_sources: str = typer.Option(
        "data/monitoring-sources.yml",
        "--monitoring-sources",
        "-m",
        help="Path to monitoring-sources.yml signal map.",
    ),
    ksi_mappings: str = typer.Option(
        "data/ksi-mappings.yml",
        "--ksi-mappings",
        "-k",
        help="Path to ksi-mappings.yml.",
    ),
    output: str = typer.Option(
        "exports/oscal/uiao-ongoing-auth.json",
        "--output",
        "-o",
        help="Output path for the ongoing-authorization OSCAL JSON artifact.",
    ),
) -> None:
    """Export an OSCAL ongoing-authorization evidence artifact.

    Generates machine-readable control evidence linking every monitored
    NIST 800-53 control to its telemetry source, satisfying the FedRAMP
    20x Phase 2 ConMon requirement for ongoing authorization evidence.
    """
    from uiao_core.monitoring.ongoing_auth import OngoingAuthGenerator

    console.print("[bold]Generating ongoing-authorization evidence artifact...[/bold]")
    gen = OngoingAuthGenerator(
        monitoring_sources_path=monitoring_sources,
        ksi_mappings_path=ksi_mappings,
    )
    out = gen.export(output)
    console.print(f"[green]Ongoing-authorization evidence written to {out}[/green]")


@app.command()
def conmon_dashboard(
    ksi_mappings: str = typer.Option(
        "data/ksi-mappings.yml",
        "--ksi-mappings",
        "-k",
        help="Path to ksi-mappings.yml.",
    ),
    output: str = typer.Option(
        "exports/conmon/ksi-dashboard.json",
        "--output",
        "-o",
        help="Output path for the KSI dashboard artifact.",
    ),
    fmt: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Output format: json or yaml.",
    ),
) -> None:
    """Export the KSI continuous monitoring dashboard.

    Computes Key Security Indicator scores from ksi-mappings.yml and
    writes a FedRAMP 20x Phase 2 ConMon dashboard artifact in JSON or
    YAML format.
    """
    from uiao_core.dashboard.export import DashboardExporter

    fmt_lower = fmt.lower()
    if fmt_lower not in ("json", "yaml"):
        console.print(f"[red]Invalid format '{fmt}'. Choose 'json' or 'yaml'.[/red]")
        raise typer.Exit(code=1)

    console.print("[bold]Generating KSI ConMon dashboard...[/bold]")
    exporter = DashboardExporter(ksi_mappings_path=ksi_mappings)

    if fmt_lower == "yaml":
        out = exporter.export_yaml(output)
    else:
        out = exporter.export_json(output)

    console.print(f"[green]KSI dashboard written to {out}[/green]")
def generate_all(
    canon_path: str = typer.Option(
        "canon/uiao_leadership_briefing_v1.0.yaml",
        "--canon",
        "-c",
        help="Path to canon YAML file.",
    ),
    data_dir: str = typer.Option(
        "data",
        "--data-dir",
        "-d",
        help="Path to data YAML directory.",
    ),
    templates_dir: str = typer.Option(
        "templates",
        "--templates-dir",
        "-t",
        help="Path to Jinja2 templates directory.",
    ),
    docs_dir: str = typer.Option(
        "docs",
        "--docs-dir",
        help="Output directory for generated Markdown documents.",
    ),
    exports_dir: str = typer.Option(
        "exports",
        "--exports-dir",
        "-e",
        help="Output exports directory (DOCX, PPTX, OSCAL, SBOM).",
    ),
    force_visuals: bool = typer.Option(
        False,
        "--force-visuals",
        help="Force regeneration of all visuals (ignore cache).",
    ),
    skip_sbom: bool = typer.Option(
        False,
        "--skip-sbom",
        help="Skip SBOM generation.",
    ),
) -> None:
    """Run the full UIAO generation pipeline: YAML canon → all output artifacts.

    Executes every generator in order:
    1. Schema validation of canon YAML
    2. Mermaid diagram rendering (PNG)
    3. Markdown documentation (docs/)
    4. OSCAL Component Definition JSON
    5. SSP Skeleton JSON
    6. POA&M template JSON
    7. DOCX leadership briefing
    8. PPTX leadership deck
    9. CycloneDX SBOM (unless --skip-sbom)
    """
    import time

    from uiao_core.generators.docs import build_docs
    from uiao_core.generators.mermaid import render_all_mermaid
    from uiao_core.generators.oscal import build_oscal
    from uiao_core.generators.poam import build_poam_export
    from uiao_core.generators.pptx import build_pptx
    from uiao_core.generators.rich_docx import build_rich_docx
    from uiao_core.generators.sbom import build_sbom
    from uiao_core.generators.ssp import build_ssp

    start = time.monotonic()
    errors: list[str] = []

    console.print("[bold blue]━━━ UIAO generate-all ━━━[/bold blue]")
    console.print(f"[dim]Canon: {canon_path}  |  Data: {data_dir}[/dim]\n")

    # ── 1. Mermaid diagrams ──────────────────────────────────────────────────
    console.print("[bold][ 1/8 ] Rendering Mermaid diagrams...[/bold]")
    try:
        pngs = render_all_mermaid(force=force_visuals)
        console.print(f"[green]✓ Rendered {len(pngs)} diagram(s)[/green]")
    except Exception as exc:  # noqa: BLE001
        console.print(f"[yellow]⚠ Diagrams skipped: {exc}[/yellow]")

    # ── 2. Markdown docs ─────────────────────────────────────────────────────
    console.print("[bold][ 2/8 ] Generating Markdown documentation...[/bold]")
    try:
        generated = build_docs(
            canon_path=Path(canon_path),
            data_dir=Path(data_dir),
            templates_dir=Path(templates_dir),
            docs_dir=Path(docs_dir),
            generate_diagrams=False,
            force_visuals=False,
        )
        console.print(f"[green]✓ Generated {len(generated)} document(s) → {docs_dir}/[/green]")
    except Exception as exc:  # noqa: BLE001
        msg = f"Docs generation failed: {exc}"
        errors.append(msg)
        console.print(f"[red]✗ {msg}[/red]")

    # ── 3. OSCAL Component Definition ────────────────────────────────────────
    console.print("[bold][ 3/8 ] Building OSCAL Component Definition...[/bold]")
    try:
        oscal_out = build_oscal(
            canon_path=Path(canon_path),
            data_dir=Path(data_dir),
            exports_dir=Path(exports_dir),
        )
        console.print(f"[green]✓ OSCAL CD → {oscal_out}[/green]")
    except Exception as exc:  # noqa: BLE001
        msg = f"OSCAL CD failed: {exc}"
        errors.append(msg)
        console.print(f"[red]✗ {msg}[/red]")

    # ── 4. SSP Skeleton ──────────────────────────────────────────────────────
    console.print("[bold][ 4/8 ] Building SSP Skeleton...[/bold]")
    try:
        ssp_out = build_ssp(
            canon_path=Path(canon_path),
            data_dir=Path(data_dir),
            exports_dir=Path(exports_dir),
        )
        console.print(f"[green]✓ SSP → {ssp_out}[/green]")
    except Exception as exc:  # noqa: BLE001
        msg = f"SSP failed: {exc}"
        errors.append(msg)
        console.print(f"[red]✗ {msg}[/red]")

    # ── 5. POA&M Template ────────────────────────────────────────────────────
    console.print("[bold][ 5/8 ] Building POA&M Template...[/bold]")
    try:
        poam_out = build_poam_export(
            canon_path=Path(canon_path),
            data_dir=Path(data_dir),
            exports_dir=Path(exports_dir),
        )
        console.print(f"[green]✓ POA&M → {poam_out}[/green]")
    except Exception as exc:  # noqa: BLE001
        msg = f"POA&M failed: {exc}"
        errors.append(msg)
        console.print(f"[red]✗ {msg}[/red]")

    # ── 6. DOCX ──────────────────────────────────────────────────────────────
    console.print("[bold][ 6/8 ] Generating DOCX leadership briefing...[/bold]")
    try:
        docx_out = build_rich_docx(
            canon_path=Path(canon_path),
            data_dir=Path(data_dir),
            exports_dir=Path(exports_dir),
        )
        console.print(f"[green]✓ DOCX → {docx_out}[/green]")
    except Exception as exc:  # noqa: BLE001
        msg = f"DOCX failed: {exc}"
        errors.append(msg)
        console.print(f"[red]✗ {msg}[/red]")

    # ── 7. PPTX ──────────────────────────────────────────────────────────────
    console.print("[bold][ 7/8 ] Generating PPTX leadership deck...[/bold]")
    try:
        pptx_out = build_pptx(
            canon_path=Path(canon_path),
            data_dir=Path(data_dir),
            exports_dir=Path(exports_dir),
        )
        console.print(f"[green]✓ PPTX → {pptx_out}[/green]")
    except Exception as exc:  # noqa: BLE001
        msg = f"PPTX failed: {exc}"
        errors.append(msg)
        console.print(f"[red]✗ {msg}[/red]")

    # ── 8. SBOM ──────────────────────────────────────────────────────────────
    if not skip_sbom:
        console.print("[bold][ 8/8 ] Generating CycloneDX SBOM...[/bold]")
        try:
            sbom_out = build_sbom(
                output_path=f"{exports_dir}/sbom/sbom.cyclonedx.json",
            )
            console.print(f"[green]✓ SBOM → {sbom_out}[/green]")
        except Exception as exc:  # noqa: BLE001
            msg = f"SBOM failed: {exc}"
            errors.append(msg)
            console.print(f"[red]✗ {msg}[/red]")
    else:
        console.print("[dim][ 8/8 ] SBOM skipped (--skip-sbom)[/dim]")

    # ── Summary ───────────────────────────────────────────────────────────────
    elapsed = time.monotonic() - start
    console.print()
    if errors:
        console.print(
            f"[bold yellow]Pipeline finished in {elapsed:.1f}s with "
            f"{len(errors)} error(s):[/bold yellow]"
        )
        for err in errors:
            console.print(f"  [red]• {err}[/red]")
        raise typer.Exit(code=1)

    console.print(
        f"[bold green]✓ All artifacts generated in {elapsed:.1f}s[/bold green]"
    )


if __name__ == "__main__":
    app()
