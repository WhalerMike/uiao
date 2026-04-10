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
        "generation-inputs/uiao_leadership_briefing_v1.0.yaml",
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
    enhanced: bool = typer.Option(
        False,
        "--enhanced/--no-enhanced",
        help="Inject control-library narratives into implemented-requirements.",
    ),
) -> None:
    """Generate an OSCAL SSP from canon YAML and data files."""
    from uiao_core.generators.ssp import build_ssp

    console.print(f"[bold]Generating SSP from {canon_path}...[/bold]")
    out = build_ssp(canon_path=canon_path, data_dir=data_dir, output_path=output, enhanced=enhanced)
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
        help="Directory containing .puml source files.",
    ),
    output_dir: str = typer.Option(
        "assets/images/plantuml",
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
    """Render PlantUML diagrams to PNG for DOCX/PPTX embedding."""
    from uiao_core.generators.mermaid import render_all_plantuml

    console.print(f"[bold]Rendering PlantUML visuals from {visuals_dir}...[/bold]")
    results = render_all_plantuml(visuals_dir, output_dir, force=force)
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
        "generation-inputs/uiao_leadership_briefing_v1.0.yaml",
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
        "generation-inputs/uiao_leadership_briefing_v1.0.yaml",
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
        "generation-inputs/diagrams.yaml",
        "--canon",
        "-c",
        help="Path to diagrams canon YAML file.",
    ),
    visuals_dir: str = typer.Option(
        "visuals",
        "--visuals-dir",
        "-v",
        help="Directory to write .puml source files.",
    ),
    output_dir: str = typer.Option(
        "assets/images/plantuml",
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
    """Generate PlantUML .puml files and render them to PNG from canon YAML."""
    from uiao_core.generators.diagrams import generate_diagrams_from_canon
    from uiao_core.generators.mermaid import render_all_plantuml

    console.print(f"[bold]Generating diagrams from {canon_path}...[/bold]")
    rendered = generate_diagrams_from_canon(
        canon_path=canon_path,
        visuals_dir=visuals_dir,
        output_dir=output_dir,
        force=force,
    )
    console.print(f"[green]Generated {len(rendered)} diagram(s) from canon.[/green]")

    console.print(f"[bold]Rendering all PlantUML files in {visuals_dir}...[/bold]")
    all_pngs = render_all_plantuml(visuals_dir=visuals_dir, output_dir=output_dir, force=force)
    console.print(f"[green]Rendered {len(all_pngs)} total diagram(s) to {output_dir}[/green]")


@app.command()
def generate_docs(
    canon_path: str = typer.Option(
        "generation-inputs/uiao_leadership_briefing_v1.0.yaml",
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

    Automatically generates diagrams from generation-inputs/diagrams.yaml before rendering
    templates (unless --skip-diagrams is set).
    """
    from uiao_core.generators.docs import build_docs

    if not skip_diagrams:
        console.print("[bold]Auto-generating diagrams from generation-inputs/diagrams.yaml...[/bold]")

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
        "generation-inputs/uiao_leadership_briefing_v1.0.yaml",
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
    """Generate DOCX + PPTX with embedded PlantUML and Gemini visuals."""
    from uiao_core.generators.mermaid import render_all_plantuml
    from uiao_core.generators.pptx import build_pptx
    from uiao_core.generators.rich_docx import build_rich_docx

    console.print("[bold]Rendering PlantUML visuals...[/bold]")
    pngs = render_all_plantuml(force=force_visuals)
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

    out = exporter.export_yaml(output) if fmt_lower == "yaml" else exporter.export_json(output)

    console.print(f"[green]KSI dashboard written to {out}[/green]")


@app.command()
def generate_all(
    canon_path: str = typer.Option(
        "generation-inputs/uiao_leadership_briefing_v1.0.yaml",
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
    1. PlantUML diagram rendering (PNG)
    2. Markdown documentation (docs/)
    3. OSCAL Component Definition JSON
    4. SSP Skeleton JSON
    5. POA&M template JSON
    6. DOCX Leadership Briefing (rich, with embedded diagrams)
    7. PPTX leadership deck
    8. Topic DOCX suite (one per Markdown doc in docs/)
    9. CycloneDX SBOM (unless --skip-sbom)

    Note: The legacy lowercase 'leadership_briefing_v1.0.docx' in exports/docx/
    is no longer regenerated. The authoritative file is
    'UIAO_Leadership_Briefing_v1.0.docx' produced by step 6.
    """
    import time

    from uiao_core.generators.docs import build_docs
    from uiao_core.generators.mermaid import render_all_plantuml
    from uiao_core.generators.oscal import build_oscal
    from uiao_core.generators.poam import build_poam_export
    from uiao_core.generators.pptx import build_pptx
    from uiao_core.generators.rich_docx import build_rich_docx, generate_all_topic_docs
    from uiao_core.generators.sbom import build_sbom
    from uiao_core.generators.ssp import build_ssp

    start = time.monotonic()
    errors: list[str] = []
    context_classification = "CUI"  # classification marking for topic DOCX headers

    console.print("[bold blue]━━━ UIAO generate-all ━━━[/bold blue]")
    console.print(f"[dim]Canon: {canon_path}  |  Data: {data_dir}[/dim]\n")

    # ── 1. PlantUML diagrams ──────────────────────────────────────────────────
    console.print("[bold][ 1/9 ] Rendering PlantUML diagrams...[/bold]")
    try:
        pngs = render_all_plantuml(force=force_visuals)
        console.print(f"[green]✓ Rendered {len(pngs)} diagram(s)[/green]")
    except Exception as exc:  # noqa: BLE001
        console.print(f"[yellow]⚠ Diagrams skipped: {exc}[/yellow]")

    # ── 2. Markdown docs ─────────────────────────────────────────────────────
    console.print("[bold][ 2/9 ] Generating Markdown documentation...[/bold]")
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
    console.print("[bold][ 3/9 ] Building OSCAL Component Definition...[/bold]")
    try:
        oscal_out = build_oscal(
            canon_path=Path(canon_path),
            data_dir=Path(data_dir),
            output_dir=Path(exports_dir),
        )
        console.print(f"[green]✓ OSCAL CD → {oscal_out}[/green]")
    except Exception as exc:  # noqa: BLE001
        msg = f"OSCAL CD failed: {exc}"
        errors.append(msg)
        console.print(f"[red]✗ {msg}[/red]")

    # ── 4. SSP Skeleton ──────────────────────────────────────────────────────
    console.print("[bold][ 4/9 ] Building SSP Skeleton...[/bold]")
    try:
        ssp_out = build_ssp(
            canon_path=Path(canon_path),
            data_dir=Path(data_dir),
            output_path=Path(exports_dir) / "oscal" / "uiao-ssp-skeleton.json",
        )
        console.print(f"[green]✓ SSP → {ssp_out}[/green]")
    except Exception as exc:  # noqa: BLE001
        msg = f"SSP failed: {exc}"
        errors.append(msg)
        console.print(f"[red]✗ {msg}[/red]")

    # ── 5. POA&M Template ────────────────────────────────────────────────────
    console.print("[bold][ 5/9 ] Building POA&M Template...[/bold]")
    try:
        poam_out = build_poam_export(
            canon_path=Path(canon_path),
            data_dir=Path(data_dir),
            output_dir=Path(exports_dir),
        )
        console.print(f"[green]✓ POA&M → {poam_out}[/green]")
    except Exception as exc:  # noqa: BLE001
        msg = f"POA&M failed: {exc}"
        errors.append(msg)
        console.print(f"[red]✗ {msg}[/red]")

    # ── 6. DOCX ──────────────────────────────────────────────────────────────
    console.print("[bold][ 6/9 ] Generating DOCX leadership briefing...[/bold]")
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
    console.print("[bold][ 7/9 ] Generating PPTX leadership deck...[/bold]")
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

    # ── 8. Topic DOCX suite ─────────────────────────────────────────────────
    console.print("[bold][ 8/9 ] Generating topic DOCX suite from docs/...[/bold]")
    try:
        topic_docs = generate_all_topic_docs(
            docs_dir=Path(docs_dir),
            exports_dir=Path(exports_dir),
            classification=context_classification,
        )
        console.print(f"[green]✓ Generated {len(topic_docs)} topic DOCX(s) → {exports_dir}/docx/[/green]")
    except Exception as exc:  # noqa: BLE001
        msg = f"Topic DOCX failed: {exc}"
        errors.append(msg)
        console.print(f"[red]✗ {msg}[/red]")

    # ── 9. SBOM ──────────────────────────────────────────────────────────────
    if not skip_sbom:
        console.print("[bold][ 9/9 ] Generating CycloneDX SBOM...[/bold]")
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
        console.print("[dim][ 9/9 ] SBOM skipped (--skip-sbom)[/dim]")

    # ── Summary ───────────────────────────────────────────────────────────────
    elapsed = time.monotonic() - start
    console.print()
    if errors:
        console.print(f"[bold yellow]Pipeline finished in {elapsed:.1f}s with {len(errors)} error(s):[/bold yellow]")
        for err in errors:
            console.print(f"  [red]• {err}[/red]")
        raise typer.Exit(code=1)

    console.print(f"[bold green]✓ All artifacts generated in {elapsed:.1f}s[/bold green]")


@app.command()
def adapter_run(
    vendor: str = typer.Argument(..., help="Vendor adapter name (servicenow, entra)."),
    output: str = typer.Option(
        "",
        "--output",
        "-o",
        help="Optional JSON output path for alignment results.",
    ),
) -> None:
    """Run a vendor adapter and align claims (DNS-style, no heavy OSCAL conversion)."""

    import json as _json

    adapter_registry = {
        "servicenow": "uiao_core.adapters.servicenow_adapter.ServiceNowAdapter",
        "entra": "uiao_core.adapters.entra_adapter.EntraAdapter",
    }

    vendor_lower = vendor.lower()
    if vendor_lower not in adapter_registry:
        console.print(f"[red]Unknown vendor: {vendor}[/red]")
        console.print(f"[dim]Available: {', '.join(adapter_registry.keys())}[/dim]")
        raise typer.Exit(code=1)

    # Lazy import to avoid circular dependencies
    import importlib

    module_path, class_name = adapter_registry[vendor_lower].rsplit(".", 1)
    module = importlib.import_module(module_path)
    adapter_class = getattr(module, class_name)
    adapter = adapter_class()

    console.print(f"[bold green]> Running {vendor} adapter...[/bold green]")
    aligned = adapter.collect_and_align()

    console.print(f"[bold]Aligned {aligned['metadata']['total_records']} claims[/bold]")
    console.print(f"[dim]Metadata: {aligned['metadata']}[/dim]")

    if output:
        with open(output, "w") as f:
            _json.dump(aligned, f, indent=2, default=str)
        console.print(f"[green]Saved to {output}[/green]")


@app.command()
def generate_briefing(
    history: bool = typer.Option(
        True,
        "--history/--no-history",
        help="Include agent activity log on Page 6",
    ),
) -> None:
    """
    Generate personal briefing document from live repo state.

    Produces a 6-page DOCX covering system health, vendor stack,
    control coverage, pipeline, priorities, and agent activity.
    Quality target: matches 01_Canon/uiao-reference.docx visual standard.
    """
    from uiao_core.config import Settings
    from uiao_core.generators.briefing import build_briefing

    typer.echo("\U0001f4cb Generating UIAO personal briefing...")
    typer.echo("   Reading: MEMORY.md, vendor-overlays/, control-library/,")
    typer.echo("            PROJECT-CONTEXT.md, CHANGELOG.md, exports/oscal/")
    settings = Settings()
    output_path = build_briefing(settings, include_history=history)
    typer.echo(f"\u2705 Briefing saved: {output_path}")
    typer.echo("   Open this document before starting any agent session.")


@app.command()
def adapter_run_scuba(
    report: str = typer.Argument(
        ...,
        help="Path to ScubaGear output file (.json or .yaml)",
    ),
    output: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output JSON file path for alignment results",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Parse report and print summary without writing output",
    ),
) -> None:
    """
    Run SCuBA adapter: ingest a ScubaGear assessment report and map
    policy results to UIAO KSI evidence.

    Reads ScubaGear JSON or YAML output and produces OSCAL-aligned
    claim records for each M365 policy baseline finding.

    Example::

        uiao adapter-run-scuba exports/scuba/M365BaselineConformance.json
    """
    import json as _json

    from uiao_core.adapters.scuba_adapter import ScubaAdapter

    typer.echo(f"\U0001f50d Reading SCuBA report: {report}")
    adapter = ScubaAdapter(config={"report_path": report})
    result = adapter.collect_and_align()

    meta = result.get("metadata", {})
    total = meta.get("total_policies", 0)
    passing = meta.get("passing", 0)
    failing = meta.get("failing", 0)

    typer.echo(f"  Total policies : {total}")
    typer.echo(f"  Passing        : {passing}")
    typer.echo(f"  Failing        : {failing}")

    if dry_run:
        typer.echo("\nDry-run mode — no output written.")
        return

    if output:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            _json.dump(result, f, indent=2, default=str)
        typer.echo(f"\n\u2705 Alignment written to {output}")
    else:
        typer.echo("\n" + _json.dumps(result["metadata"], indent=2, default=str))


@app.command()
def ir_scuba_transform(
    normalized_json: str = typer.Argument(..., help="Path to normalized SCuBA JSON file."),
    out: str = typer.Option("", "--out", "-o", help="Write full evidence JSON to file."),
) -> None:
    """Transform normalized SCuBA JSON -> IR Evidence objects and print summary."""
    import json as _json

    from uiao_core.ir.adapters.scuba.transformer import transform_scuba_to_ir

    console.print(f"[bold]Transforming SCuBA JSON: {normalized_json}...[/bold]")
    result = transform_scuba_to_ir(normalized_json)
    console.print(result.summary())
    if out:
        from pathlib import Path as _Path

        _Path(out).parent.mkdir(parents=True, exist_ok=True)
        _Path(out).write_text(_json.dumps(result.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        console.print(f"[green]Evidence JSON written to {out}[/green]")


@app.command()
def ir_evidence_bundle(
    normalized_json: str = typer.Argument(..., help="Path to normalized SCuBA JSON file."),
    out: str = typer.Option("", "--out", "-o", help="Write canonical bundle JSON to file."),
) -> None:
    """Build a canonical EvidenceBundle from a SCuBA transform and print summary."""
    from uiao_core.evidence.bundle import build_bundle_from_transform_result
    from uiao_core.ir.adapters.scuba.transformer import transform_scuba_to_ir

    console.print(f"[bold]Building EvidenceBundle from: {normalized_json}...[/bold]")
    result = transform_scuba_to_ir(normalized_json)
    bundle = build_bundle_from_transform_result(result)
    console.print(bundle.summary())
    if out:
        from pathlib import Path as _Path

        _Path(out).parent.mkdir(parents=True, exist_ok=True)
        _Path(out).write_text(bundle.to_canonical(), encoding="utf-8")
        console.print(f"[green]Bundle JSON written to {out}[/green]")


@app.command()
def ir_poam_export(
    normalized_json: str = typer.Argument(..., help="Path to normalized SCuBA JSON file."),
    out: str = typer.Option("", "--out", "-o", help="Write POA&M JSON to file."),
) -> None:
    """Export POA&M rows (FAIL + WARN only) from a SCuBA run and print summary."""
    from uiao_core.evidence.bundle import build_bundle_from_transform_result
    from uiao_core.evidence.poam import build_poam, poam_summary, poam_to_json
    from uiao_core.ir.adapters.scuba.transformer import transform_scuba_to_ir

    console.print(f"[bold]Generating POA&M from: {normalized_json}...[/bold]")
    result = transform_scuba_to_ir(normalized_json)
    bundle = build_bundle_from_transform_result(result)
    rows = build_poam(bundle)
    console.print(poam_summary(rows))
    if out:
        from pathlib import Path as _Path

        _Path(out).parent.mkdir(parents=True, exist_ok=True)
        _Path(out).write_text(poam_to_json(rows), encoding="utf-8")
        console.print(f"[green]POA&M JSON written to {out}[/green]")


@app.command()
def ir_drift_detect(
    expected: str = typer.Argument(..., help="Path to expected-state JSON file."),
    actual: str = typer.Argument(..., help="Path to actual-state JSON file."),
    resource_id: str = typer.Option("resource", "--resource-id", "-r", help="Resource identifier."),
    policy_ref: str = typer.Option("policy", "--policy-ref", "-p", help="Policy reference."),
    out: str = typer.Option("", "--out", "-o", help="Write DriftState JSON to file."),
) -> None:
    """Detect drift between two IR state JSON files and print classification."""
    import json as _json
    from datetime import datetime, timezone
    from pathlib import Path as _Path

    from uiao_core.governance.drift import build_drift_state
    from uiao_core.ir.models.core import ProvenanceRecord

    expected_state = _json.loads(_Path(expected).read_text(encoding="utf-8"))
    actual_state = _json.loads(_Path(actual).read_text(encoding="utf-8"))
    prov = ProvenanceRecord(
        source="cli:drift-detect",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="cli",
        content_hash=None,
        actor="cli",
    )
    drift = build_drift_state(
        resource_id=resource_id,
        policy_ref=policy_ref,
        expected_state=expected_state,
        actual_state=actual_state,
        provenance=prov,
    )
    status = "[red]DRIFT DETECTED[/red]" if drift.drift_detected else "[green]NO DRIFT[/green]"
    console.print(f"Resource  : {drift.resource_id}")
    console.print(f"Policy    : {drift.policy_ref}")
    console.print(f"Status    : {status}")
    console.print(f"Class     : {drift.classification}")
    console.print(
        f"Delta     : added={drift.delta.get('added', [])} removed={drift.delta.get('removed', [])} changed={drift.delta.get('changed', [])}"
    )
    if out:
        _Path(out).parent.mkdir(parents=True, exist_ok=True)
        _Path(out).write_text(drift.to_canonical(), encoding="utf-8")
        console.print(f"[green]DriftState JSON written to {out}[/green]")


@app.command()
def ir_governance_report(
    normalized_json: str = typer.Argument(..., help="Path to normalized SCuBA JSON file."),
    out: str = typer.Option("", "--out", "-o", help="Write governance actions JSON to file."),
) -> None:
    """Run full governance pipeline: SCuBA -> IR -> Evidence -> Actions -> Report."""
    import json as _json
    from pathlib import Path as _Path

    from uiao_core.evidence.bundle import build_bundle_from_transform_result
    from uiao_core.governance.actions import build_governance_actions
    from uiao_core.governance.report import format_governance_report
    from uiao_core.ir.adapters.scuba.transformer import transform_scuba_to_ir

    console.print(f"[bold]Running governance pipeline for: {normalized_json}...[/bold]")
    result = transform_scuba_to_ir(normalized_json)
    bundle = build_bundle_from_transform_result(result)
    actions = build_governance_actions(bundle.evidence, bundle.drift_states)
    report = format_governance_report(actions)
    console.print(report)
    console.print(f"\nTotal actions: {len(actions)}")
    if out:
        _Path(out).parent.mkdir(parents=True, exist_ok=True)
        payload = [
            {
                "ksi_id": a.ksi_id,
                "control_id": a.control_id,
                "policy_id": a.policy_id,
                "severity": a.severity,
                "drift_classification": a.drift_classification,
                "owner": a.owner,
                "sla_days": a.sla_days,
                "action_type": a.action_type,
                "description": a.description,
                "evidence_id": a.evidence_id,
            }
            for a in actions
        ]
        _Path(out).write_text(_json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        console.print(f"[green]Governance report JSON written to {out}[/green]")


@app.command()
def ir_ssp_report(
    normalized_json: str = typer.Argument(..., help="Path to normalized SCuBA JSON file."),
    fmt: str = typer.Option("markdown", "--format", "-f", help="Output format: markdown | json"),
    out: str = typer.Option("", "--out", "-o", help="Write output to file."),
) -> None:
    """Generate SSP narrative + lineage from SCuBA -> IR -> Evidence -> Governance."""
    import json as _json
    from pathlib import Path as _Path

    from uiao_core.coverage.coverage import build_coverage_links
    from uiao_core.evidence.bundle import build_bundle_from_transform_result
    from uiao_core.governance.actions import build_governance_actions
    from uiao_core.ir.adapters.scuba.transformer import transform_scuba_to_ir
    from uiao_core.ssp.lineage import build_lineage_index
    from uiao_core.ssp.narrative import build_control_narratives, format_ssp_markdown

    result = transform_scuba_to_ir(normalized_json)
    bundle = build_bundle_from_transform_result(result)
    actions = build_governance_actions(bundle.evidence, bundle.drift_states)
    links = build_coverage_links(bundle.evidence)
    narratives = build_control_narratives(links, actions)
    if fmt.lower() == "json":
        lineage = build_lineage_index(links, actions)
        output_text = _json.dumps(lineage, indent=2)
    else:
        output_text = format_ssp_markdown(narratives)
    typer.echo(output_text)
    if out:
        _Path(out).parent.mkdir(parents=True, exist_ok=True)
        _Path(out).write_text(output_text, encoding="utf-8")
        console.print("[green]SSP report written to " + out + "[/green]")


@app.command()
def ir_auditor_bundle(
    normalized_json: str = typer.Argument(..., help="Path to normalized SCuBA JSON file."),
    out_dir: str = typer.Option("exports/auditor-bundle", "--out-dir", "-o", help="Output directory for artifacts."),
) -> None:
    """Run full pipeline and write all auditor artifacts to a directory."""
    from uiao_core.auditor.bundle import build_auditor_bundle

    console.print(f"[bold]Building auditor bundle from: {normalized_json}...[/bold]")
    manifest = build_auditor_bundle(normalized_json, out_dir)
    console.print(f"[green]Bundle written to {out_dir}[/green]")
    s = manifest["summary"]
    console.print(f"  Evidence : {s['evidence_total']}")
    console.print(f"  Actions  : {s['governance_actions']}")
    console.print(f"  POA&M    : {s['poam_items']}")


@app.command()
def ir_diff(
    run_a: str = typer.Argument(..., help="Path to first normalized SCuBA JSON file."),
    run_b: str = typer.Argument(..., help="Path to second normalized SCuBA JSON file."),
    fmt: str = typer.Option("markdown", "--format", "-f", help="Output format: markdown | json"),
    out: str = typer.Option("", "--out", "-o", help="Write output to file."),
) -> None:
    """Diff two SCuBA runs: KSI changes, evidence hash deltas, status changes."""
    from pathlib import Path as _Path

    from uiao_core.diff.engine import diff_runs, format_diff_json, format_diff_markdown
    from uiao_core.ir.adapters.scuba.transformer import transform_scuba_to_ir

    result_a = transform_scuba_to_ir(run_a)
    result_b = transform_scuba_to_ir(run_b)
    diff = diff_runs(result_a, result_b)
    output_text = format_diff_json(diff) if fmt.lower() == "json" else format_diff_markdown(diff)
    typer.echo(output_text)
    if out:
        _Path(out).parent.mkdir(parents=True, exist_ok=True)
        _Path(out).write_text(output_text, encoding="utf-8")
        console.print("[green]Diff written to " + out + "[/green]")


@app.command()
def ir_validate(
    normalized_json: str = typer.Argument(..., help="Path to normalized SCuBA JSON file to validate."),
    strict: bool = typer.Option(False, "--strict", help="Exit non-zero on warnings."),
) -> None:
    """Validate a normalized SCuBA JSON file for IR pipeline conformance."""
    from uiao_core.validators.ir_validator import validate_normalized_json

    result = validate_normalized_json(normalized_json)
    for err in result.errors:
        console.print(f"[red]ERROR: {err}[/red]")
    for warn in result.warnings:
        console.print(f"[yellow]WARN:  {warn}[/yellow]")
    if result.valid:
        console.print("[green]VALID[/green]")
        if result.warnings and strict:
            raise typer.Exit(code=1)
    else:
        console.print(f"[red]INVALID — {len(result.errors)} error(s)[/red]")
        raise typer.Exit(code=1)


@app.command()
def ir_freshness(
    normalized_json: str = typer.Argument(..., help="Path to normalized SCuBA JSON file."),
    out: str = typer.Option("", "--out", "-o", help="Write freshness JSON to file."),
    threshold_days: int = typer.Option(30, "--threshold-days", "-t", help="Default freshness threshold in days."),
) -> None:
    """Compute evidence freshness and generate refresh actions for stale evidence."""
    import json as _json
    from pathlib import Path as _Path

    from uiao_core.evidence.bundle import build_bundle_from_transform_result
    from uiao_core.freshness.engine import build_freshness_records, generate_refresh_actions
    from uiao_core.governance.actions import build_governance_actions
    from uiao_core.ir.adapters.scuba.transformer import transform_scuba_to_ir

    result = transform_scuba_to_ir(normalized_json)
    bundle = build_bundle_from_transform_result(result)
    existing_actions = build_governance_actions(bundle.evidence, bundle.drift_states)
    thresholds = {"default": threshold_days}
    records = build_freshness_records(bundle.evidence, thresholds=thresholds)
    fresh = sum(1 for r in records if r.status == "fresh")
    stale_soon = sum(1 for r in records if r.status == "stale-soon")
    stale = sum(1 for r in records if r.status == "stale")
    console.print(f"[bold]Freshness report for: {normalized_json}[/bold]")
    console.print(f"  Fresh      : [green]{fresh}[/green]")
    console.print(f"  Stale-soon : [yellow]{stale_soon}[/yellow]")
    console.print(f"  Stale      : [red]{stale}[/red]")
    refresh_actions = generate_refresh_actions(records, existing_actions=existing_actions)
    console.print(f"  Refresh actions generated: {len(refresh_actions)}")
    if out:
        import dataclasses as _dc

        payload = {
            "freshness_records": [_dc.asdict(r) for r in records],
            "refresh_actions": [
                {
                    "ksi_id": a.ksi_id,
                    "control_id": a.control_id,
                    "policy_id": a.policy_id,
                    "severity": a.severity,
                    "drift_classification": a.drift_classification,
                    "owner": a.owner,
                    "sla_days": a.sla_days,
                    "action_type": a.action_type,
                    "description": a.description,
                    "evidence_id": a.evidence_id,
                }
                for a in refresh_actions
            ],
        }
        _Path(out).parent.mkdir(parents=True, exist_ok=True)
        _Path(out).write_text(_json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        console.print("[green]Freshness report written to " + out + "[/green]")


@app.command()
def ir_dashboard(
    normalized_json: str = typer.Argument(..., help="Path to normalized SCuBA JSON file."),
    out: str = typer.Option("", "--out", "-o", help="Write dashboard JSON to file."),
    threshold_days: int = typer.Option(30, "--threshold-days", "-t", help="Default freshness threshold in days."),
) -> None:
    """Build IR governance dashboard: evidence freshness + governance action summary."""
    from uiao_core.dashboard.ir_dashboard import export_ir_dashboard
    from uiao_core.evidence.bundle import build_bundle_from_transform_result
    from uiao_core.governance.actions import build_governance_actions
    from uiao_core.ir.adapters.scuba.transformer import transform_scuba_to_ir

    result = transform_scuba_to_ir(normalized_json)
    bundle = build_bundle_from_transform_result(result)
    actions = build_governance_actions(bundle.evidence, bundle.drift_states)
    thresholds = {"default": threshold_days}
    console.print(f"[bold]Building IR dashboard for: {normalized_json}...[/bold]")
    if out:
        path = export_ir_dashboard(bundle.evidence, actions, out, thresholds=thresholds)
        console.print("[green]Dashboard written to " + path + "[/green]")
    else:
        from uiao_core.dashboard.ir_dashboard import build_ir_dashboard

        dashboard = build_ir_dashboard(bundle.evidence, actions, thresholds=thresholds)
        console.print(f"  Evidence total : {dashboard['evidence_total']}")
        fs = dashboard["freshness_summary"]
        console.print(f"  Fresh          : [green]{fs['fresh']}[/green]")
        console.print(f"  Stale-soon     : [yellow]{fs['stale_soon']}[/yellow]")
        console.print(f"  Stale          : [red]{fs['stale']}[/red]")
        gs = dashboard["governance_summary"]
        console.print(f"  Total actions  : {gs['total_actions']}")


@app.command()
def ir_freshness_schedule(
    normalized_json: str = typer.Argument(..., help="Path to normalized SCuBA JSON file."),
    out: str = typer.Option("", "--out", "-o", help="Write schedule JSON to file."),
    threshold_days: int = typer.Option(30, "--threshold-days", "-t", help="Default freshness threshold in days."),
) -> None:
    """Build a refresh job schedule from stale evidence and print the schedule summary."""
    import dataclasses as _dc
    import json as _json
    from pathlib import Path as _Path

    from uiao_core.evidence.bundle import build_bundle_from_transform_result
    from uiao_core.freshness.engine import build_freshness_records, generate_refresh_actions
    from uiao_core.freshness.scheduler import build_refresh_schedule, schedule_summary
    from uiao_core.governance.actions import build_governance_actions
    from uiao_core.ir.adapters.scuba.transformer import transform_scuba_to_ir

    result = transform_scuba_to_ir(normalized_json)
    bundle = build_bundle_from_transform_result(result)
    existing_actions = build_governance_actions(bundle.evidence, bundle.drift_states)
    thresholds = {"default": threshold_days}
    records = build_freshness_records(bundle.evidence, thresholds=thresholds)
    refresh_actions = generate_refresh_actions(records, existing_actions=existing_actions)
    jobs = build_refresh_schedule(records, refresh_actions)
    console.print(schedule_summary(jobs))
    if out:
        _Path(out).parent.mkdir(parents=True, exist_ok=True)
        payload = [_dc.asdict(j) for j in jobs]
        _Path(out).write_text(_json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        console.print("[green]Schedule written to " + out + "[/green]")


@app.command()
def ir_generate_sar(
    normalized_json: str = typer.Argument(..., help="Path to normalized SCuBA JSON file."),
    out: str = typer.Option("", "--out", "-o", help="Write OSCAL SAR JSON to file."),
    system_name: str = typer.Option(
        "UIAO SCuBA Assessment System", "--system-name", "-s", help="System name for SAR metadata."
    ),
    ap_href: str = typer.Option("", "--ap-href", help="Optional href to Assessment Plan document."),
) -> None:
    """Generate an OSCAL Assessment Results (SAR) document from a SCuBA run."""
    from uiao_core.evidence.bundle import build_bundle_from_transform_result
    from uiao_core.generators.sar import build_sar, build_sar_summary, export_sar
    from uiao_core.ir.adapters.scuba.transformer import transform_scuba_to_ir

    result = transform_scuba_to_ir(normalized_json)
    bundle = build_bundle_from_transform_result(result)
    tenant_id = result.evidence[0].data.get("tenant_id", "") if result.evidence else ""
    console.print("[bold]Generating OSCAL SAR...[/bold]")
    if out:
        path = export_sar(bundle, out, system_name=system_name, tenant_id=tenant_id, ap_href=ap_href)
        console.print("[green]SAR written to " + path + "[/green]")
    else:
        sar_doc = build_sar(bundle, system_name=system_name, tenant_id=tenant_id, ap_href=ap_href)
        console.print(build_sar_summary(sar_doc))


@app.command()
def ir_ssp_inject(
    normalized_json: str = typer.Argument(..., help="Path to normalized SCuBA JSON file."),
    out: str = typer.Option("exports/oscal/uiao-ssp-live.json", "--out", "-o", help="Output SSP JSON path."),
    canon_path: str = typer.Option("", "--canon", "-c", help="Canon YAML path (default: settings)."),
    data_dir: str = typer.Option("", "--data-dir", "-d", help="Data YAML directory (default: settings)."),
    enhanced: bool = typer.Option(False, "--enhanced/--no-enhanced", help="Also inject control-library narratives."),
) -> None:
    """Inject live SCuBA evidence into OSCAL SSP, writing uiao-ssp-live.json.

    Combines the canon SSP baseline with real SCuBA assessment evidence,
    producing an OSCAL SSP whose implemented-requirements carry live
    implementation-status props and evidence-hash annotations.
    """
    import json as _json
    from pathlib import Path as _Path

    from uiao_core.evidence.bundle import build_bundle_from_transform_result
    from uiao_core.generators.ssp_inject import build_live_ssp, live_ssp_summary
    from uiao_core.ir.adapters.scuba.transformer import transform_scuba_to_ir

    kw = {}
    if canon_path:
        kw["canon_path"] = canon_path
    if data_dir:
        kw["data_dir"] = data_dir
    console.print(f"[bold]Injecting SCuBA evidence into SSP: {normalized_json}...[/bold]")
    path = build_live_ssp(normalized_json_path=normalized_json, output_path=out, enhanced=enhanced, **kw)
    ssp_doc = _json.loads(_Path(out).read_text(encoding="utf-8"))
    ir_result = transform_scuba_to_ir(normalized_json)
    bundle = build_bundle_from_transform_result(ir_result)
    console.print(live_ssp_summary(ssp_doc, bundle))
    console.print(f"[green]Live SSP written to {path}[/green]")


if __name__ == "__main__":
    app()
