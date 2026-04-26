"""uiao.cli.generate — Typer sub-app for the `uiao generate` command group.

Mount point
-----------
    # in uiao/cli/app.py
    from uiao.cli.generate import generate_app
    app.add_typer(generate_app, name="generate")

Usage (after `pip install -e .`)
---------------------------------
    uiao generate ssp --canon generation-inputs/uiao_leadership_briefing_v1.0.yaml
    uiao generate docs --output-dir docs
    uiao generate all --skip-sbom

Or via module invocation:
    python -m uiao.cli generate all
"""

from __future__ import annotations

import os
from pathlib import Path

import typer
from rich.console import Console

generate_app = typer.Typer(
    name="generate",
    help="Artifact generation operations (SSP, docs, DOCX/PPTX, diagrams, SBOM, briefings).",
    add_completion=False,
)

_console = Console()


@generate_app.command("ssp")
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
    """Generate an OSCAL SSP from canon YAML and data files.

    Example::

        uiao generate ssp --output /tmp/uiao-ssp.json
    """
    from uiao.generators.ssp import build_ssp

    _console.print(f"[bold]Generating SSP from {canon_path}...[/bold]")
    out = build_ssp(canon_path=canon_path, data_dir=data_dir, output_path=output, enhanced=enhanced)
    _console.print(f"[green]SSP written to {out}[/green]")


@generate_app.command("visuals")
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
    """Render PlantUML diagrams to PNG for DOCX/PPTX embedding.

    Example::

        uiao generate visuals --output-dir /tmp/visuals
    """
    from uiao.generators.mermaid import render_all_plantuml

    _console.print(f"[bold]Rendering PlantUML visuals from {visuals_dir}...[/bold]")
    results = render_all_plantuml(visuals_dir, output_dir, force=force)
    _console.print(f"[green]Rendered {len(results)} diagram(s) to {output_dir}[/green]")


@generate_app.command("gemini")
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
    """Generate images via Gemini API (requires GEMINI_API_KEY).

    Example::

        uiao generate gemini --name some-diagram
    """
    from uiao.generators.gemini_visuals import (
        generate_all_gemini_images,
        generate_gemini_image,
    )

    if name:
        _console.print(f"[bold]Generating Gemini image: {name}...[/bold]")
        result = generate_gemini_image(name, output_dir=Path(output_dir), force=force)
        if result:
            _console.print(f"[green]Generated {result}[/green]")
        else:
            _console.print(f"[red]Failed to generate {name}[/red]")
            raise typer.Exit(code=1)
    else:
        _console.print("[bold]Generating all Gemini images...[/bold]")
        results = generate_all_gemini_images(output_dir, force=force)
        _console.print(f"[green]Generated {len(results)} image(s) to {output_dir}[/green]")


@generate_app.command("pptx")
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
    """Generate a leadership briefing PPTX deck.

    Example::

        uiao generate pptx --exports-dir /tmp/exports
    """
    from uiao.generators.pptx import build_pptx

    _console.print("[bold]Generating leadership briefing PPTX...[/bold]")
    out = build_pptx(
        canon_path=Path(canon_path),
        data_dir=Path(data_dir),
        exports_dir=Path(exports_dir),
    )
    _console.print(f"[green]PPTX exported to {out}[/green]")


@generate_app.command("docx")
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
    """Generate a rich DOCX leadership briefing with embedded visuals.

    Example::

        uiao generate docx --exports-dir /tmp/exports
    """
    from uiao.generators.rich_docx import build_rich_docx

    _console.print("[bold]Generating leadership briefing DOCX...[/bold]")
    out = build_rich_docx(
        canon_path=Path(canon_path),
        data_dir=Path(data_dir),
        exports_dir=Path(exports_dir),
    )
    _console.print(f"[green]DOCX exported to {out}[/green]")


@generate_app.command("diagrams")
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
    """Generate PlantUML .puml files and render them to PNG from canon YAML.

    Example::

        uiao generate diagrams --output-dir /tmp/diagrams
    """
    from uiao.generators.diagrams import generate_diagrams_from_canon
    from uiao.generators.mermaid import render_all_plantuml

    _console.print(f"[bold]Generating diagrams from {canon_path}...[/bold]")
    rendered = generate_diagrams_from_canon(
        canon_path=canon_path,
        visuals_dir=visuals_dir,
        output_dir=output_dir,
        force=force,
    )
    _console.print(f"[green]Generated {len(rendered)} diagram(s) from canon.[/green]")

    _console.print(f"[bold]Rendering all PlantUML files in {visuals_dir}...[/bold]")
    all_pngs = render_all_plantuml(visuals_dir=visuals_dir, output_dir=output_dir, force=force)
    _console.print(f"[green]Rendered {len(all_pngs)} total diagram(s) to {output_dir}[/green]")


@generate_app.command("docs")
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

    Example::

        uiao generate docs --output-dir /tmp/docs
    """
    from uiao.generators.docs import build_docs

    if not skip_diagrams:
        _console.print("[bold]Auto-generating diagrams from generation-inputs/diagrams.yaml...[/bold]")

    _console.print(f"[bold]Generating docs from {canon_path}...[/bold]")
    generated = build_docs(
        canon_path=Path(canon_path),
        data_dir=Path(data_dir),
        templates_dir=Path(templates_dir),
        docs_dir=Path(output_dir),
        generate_diagrams=not skip_diagrams,
        force_visuals=force_visuals,
    )
    _console.print(f"[green]Generated {len(generated)} document(s) to {output_dir}[/green]")


@generate_app.command("artifacts")
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
    """Generate DOCX + PPTX with embedded PlantUML and Gemini visuals.

    Example::

        uiao generate artifacts --exports-dir /tmp/exports
    """
    from uiao.generators.mermaid import render_all_plantuml
    from uiao.generators.pptx import build_pptx
    from uiao.generators.rich_docx import build_rich_docx

    _console.print("[bold]Rendering PlantUML visuals...[/bold]")
    pngs = render_all_plantuml(force=force_visuals)
    _console.print(f"[green]Rendered {len(pngs)} diagram(s)[/green]")

    if os.environ.get("GEMINI_API_KEY", "").strip():
        from uiao.generators.gemini_visuals import generate_all_gemini_images

        _console.print("[bold]Generating Gemini images...[/bold]")
        gemini_results = generate_all_gemini_images(force=force_visuals)
        _console.print(f"[green]Generated {len(gemini_results)} Gemini image(s)[/green]")
    else:
        _console.print("[yellow]GEMINI_API_KEY not set — skipping Gemini image generation.[/yellow]")

    _console.print("[bold]Generating DOCX...[/bold]")
    docx_out = build_rich_docx(
        canon_path=Path(canon_path),
        data_dir=Path(data_dir),
        exports_dir=Path(exports_dir),
    )
    _console.print(f"[green]DOCX exported to {docx_out}[/green]")

    _console.print("[bold]Generating PPTX...[/bold]")
    pptx_out = build_pptx(
        canon_path=Path(canon_path),
        data_dir=Path(data_dir),
        exports_dir=Path(exports_dir),
    )
    _console.print(f"[green]PPTX exported to {pptx_out}[/green]")
    _console.print("[bold green]All artifacts generated with embedded visuals.[/bold green]")


@generate_app.command("sbom")
def generate_sbom(
    output: str = typer.Option(
        "exports/sbom/sbom.cyclonedx.json",
        "--output",
        "-o",
        help="Output path for the CycloneDX JSON SBOM.",
    ),
) -> None:
    """Generate a CycloneDX 1.4 Software Bill of Materials (SBOM).

    Example::

        uiao generate sbom --output /tmp/sbom.json
    """
    from uiao.generators.sbom import build_sbom

    _console.print("[bold]Generating CycloneDX SBOM...[/bold]")
    out = build_sbom(output_path=output)
    _console.print(f"[green]SBOM written to {out}[/green]")


@generate_app.command("all")
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
    """Run the full UIAO generation pipeline: YAML canon -> all output artifacts.

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

    Example::

        uiao generate all
    """
    import time

    from uiao.generators.docs import build_docs
    from uiao.generators.mermaid import render_all_plantuml
    from uiao.generators.oscal import build_oscal
    from uiao.generators.poam import build_poam_export
    from uiao.generators.pptx import build_pptx
    from uiao.generators.rich_docx import build_rich_docx, generate_all_topic_docs
    from uiao.generators.sbom import build_sbom
    from uiao.generators.ssp import build_ssp

    start = time.monotonic()
    errors: list[str] = []
    context_classification = "Public"  # classification marking for topic DOCX headers

    _console.print("[bold blue]━━━ UIAO generate-all ━━━[/bold blue]")
    _console.print(f"[dim]Canon: {canon_path}  |  Data: {data_dir}[/dim]\n")

    # ── 1. PlantUML diagrams ──────────────────────────────────────────────────
    _console.print("[bold][ 1/9 ] Rendering PlantUML diagrams...[/bold]")
    try:
        pngs = render_all_plantuml(force=force_visuals)
        _console.print(f"[green]✓ Rendered {len(pngs)} diagram(s)[/green]")
    except Exception as exc:  # noqa: BLE001
        _console.print(f"[yellow]⚠ Diagrams skipped: {exc}[/yellow]")

    # ── 2. Markdown docs ─────────────────────────────────────────────────────
    _console.print("[bold][ 2/9 ] Generating Markdown documentation...[/bold]")
    try:
        generated = build_docs(
            canon_path=Path(canon_path),
            data_dir=Path(data_dir),
            templates_dir=Path(templates_dir),
            docs_dir=Path(docs_dir),
            generate_diagrams=False,
            force_visuals=False,
        )
        _console.print(f"[green]✓ Generated {len(generated)} document(s) -> {docs_dir}/[/green]")
    except Exception as exc:  # noqa: BLE001
        msg = f"Docs generation failed: {exc}"
        errors.append(msg)
        _console.print(f"[red]✗ {msg}[/red]")

    # ── 3. OSCAL Component Definition ────────────────────────────────────────
    _console.print("[bold][ 3/9 ] Building OSCAL Component Definition...[/bold]")
    try:
        oscal_out = build_oscal(
            canon_path=Path(canon_path),
            data_dir=Path(data_dir),
            output_dir=Path(exports_dir),
        )
        _console.print(f"[green]✓ OSCAL CD -> {oscal_out}[/green]")
    except Exception as exc:  # noqa: BLE001
        msg = f"OSCAL CD failed: {exc}"
        errors.append(msg)
        _console.print(f"[red]✗ {msg}[/red]")

    # ── 4. SSP Skeleton ──────────────────────────────────────────────────────
    _console.print("[bold][ 4/9 ] Building SSP Skeleton...[/bold]")
    try:
        ssp_out = build_ssp(
            canon_path=Path(canon_path),
            data_dir=Path(data_dir),
            output_path=Path(exports_dir) / "oscal" / "uiao-ssp-skeleton.json",
        )
        _console.print(f"[green]✓ SSP -> {ssp_out}[/green]")
    except Exception as exc:  # noqa: BLE001
        msg = f"SSP failed: {exc}"
        errors.append(msg)
        _console.print(f"[red]✗ {msg}[/red]")

    # ── 5. POA&M Template ────────────────────────────────────────────────────
    _console.print("[bold][ 5/9 ] Building POA&M Template...[/bold]")
    try:
        poam_out = build_poam_export(
            canon_path=Path(canon_path),
            data_dir=Path(data_dir),
            output_dir=Path(exports_dir),
        )
        _console.print(f"[green]✓ POA&M -> {poam_out}[/green]")
    except Exception as exc:  # noqa: BLE001
        msg = f"POA&M failed: {exc}"
        errors.append(msg)
        _console.print(f"[red]✗ {msg}[/red]")

    # ── 6. DOCX ──────────────────────────────────────────────────────────────
    _console.print("[bold][ 6/9 ] Generating DOCX leadership briefing...[/bold]")
    try:
        docx_out = build_rich_docx(
            canon_path=Path(canon_path),
            data_dir=Path(data_dir),
            exports_dir=Path(exports_dir),
        )
        _console.print(f"[green]✓ DOCX -> {docx_out}[/green]")
    except Exception as exc:  # noqa: BLE001
        msg = f"DOCX failed: {exc}"
        errors.append(msg)
        _console.print(f"[red]✗ {msg}[/red]")

    # ── 7. PPTX ──────────────────────────────────────────────────────────────
    _console.print("[bold][ 7/9 ] Generating PPTX leadership deck...[/bold]")
    try:
        pptx_out = build_pptx(
            canon_path=Path(canon_path),
            data_dir=Path(data_dir),
            exports_dir=Path(exports_dir),
        )
        _console.print(f"[green]✓ PPTX -> {pptx_out}[/green]")
    except Exception as exc:  # noqa: BLE001
        msg = f"PPTX failed: {exc}"
        errors.append(msg)
        _console.print(f"[red]✗ {msg}[/red]")

    # ── 8. Topic DOCX suite ─────────────────────────────────────────────────
    _console.print("[bold][ 8/9 ] Generating topic DOCX suite from docs/...[/bold]")
    try:
        topic_docs = generate_all_topic_docs(
            docs_dir=Path(docs_dir),
            exports_dir=Path(exports_dir),
            classification=context_classification,
        )
        _console.print(f"[green]✓ Generated {len(topic_docs)} topic DOCX(s) -> {exports_dir}/docx/[/green]")
    except Exception as exc:  # noqa: BLE001
        msg = f"Topic DOCX failed: {exc}"
        errors.append(msg)
        _console.print(f"[red]✗ {msg}[/red]")

    # ── 9. SBOM ──────────────────────────────────────────────────────────────
    if not skip_sbom:
        _console.print("[bold][ 9/9 ] Generating CycloneDX SBOM...[/bold]")
        try:
            sbom_out = build_sbom(
                output_path=f"{exports_dir}/sbom/sbom.cyclonedx.json",
            )
            _console.print(f"[green]✓ SBOM -> {sbom_out}[/green]")
        except Exception as exc:  # noqa: BLE001
            msg = f"SBOM failed: {exc}"
            errors.append(msg)
            _console.print(f"[red]✗ {msg}[/red]")
    else:
        _console.print("[dim][ 9/9 ] SBOM skipped (--skip-sbom)[/dim]")

    # ── Summary ───────────────────────────────────────────────────────────────
    elapsed = time.monotonic() - start
    _console.print()
    if errors:
        _console.print(f"[bold yellow]Pipeline finished in {elapsed:.1f}s with {len(errors)} error(s):[/bold yellow]")
        for err in errors:
            _console.print(f"  [red]• {err}[/red]")
        raise typer.Exit(code=1)

    _console.print(f"[bold green]✓ All artifacts generated in {elapsed:.1f}s[/bold green]")


@generate_app.command("briefing")
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

    Example::

        uiao generate briefing
    """
    from uiao.config import Settings
    from uiao.generators.briefing import build_briefing

    typer.echo("\U0001f4cb Generating UIAO personal briefing...")
    typer.echo("   Reading: MEMORY.md, vendor-overlays/, control-library/,")
    typer.echo("            PROJECT-CONTEXT.md, CHANGELOG.md, exports/oscal/")
    settings = Settings()
    output_path = build_briefing(settings, include_history=history)
    typer.echo(f"✅ Briefing saved: {output_path}")
    typer.echo("   Open this document before starting any agent session.")
