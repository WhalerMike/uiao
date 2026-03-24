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
        console.print(
            "[yellow]GEMINI_API_KEY not set — skipping Gemini image generation.[/yellow]"
        )

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


if __name__ == "__main__":
    app()
