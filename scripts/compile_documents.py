#!/usr/bin/env python3
"""UDC Document Compiler - Renders templates with data into publication formats.

Improvements:
- Fixes image paths for pandoc (../visuals/ -> visuals/)
- Adds --resource-path so pandoc finds images
- Pre-renders Mermaid code blocks to PNG when mmdc is available
- Adds DOCX formatting: TOC, margins, metadata
- Adds PDF formatting: TOC, geometry, colored links
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import warnings
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, Undefined

warnings.warn(
    "scripts/compile_documents.py is deprecated. Use `uiao` CLI instead.",
    DeprecationWarning,
    stacklevel=1,
)
ROOT = Path.cwd()
DATA_DIR = Path("data")
TEMPLATE_DIR = Path("templates")
EXPORTS_DIR = Path("exports")
SITE_DIR = Path("site")
VISUALS_DIR = Path("visuals")


def load_all_data():
    """Load all YAML files from data/ and canon/ into a unified context."""
    context = {}
    for yaml_file in sorted(DATA_DIR.rglob("*.yml")):
        key = yaml_file.stem.replace("-", "_")
        with open(yaml_file) as f:
            content = yaml.safe_load(f)
            if content:
                if isinstance(content, dict):
                    context.update(content)
                context["_src_" + key] = content
    for yaml_file in sorted(DATA_DIR.rglob("*.yaml")):
        key = yaml_file.stem.replace("-", "_")
        with open(yaml_file) as f:
            content = yaml.safe_load(f)
            if content:
                if isinstance(content, dict):
                    context.update(content)
                context["_src_" + key] = content
    canon_dir = Path("canon")
    if canon_dir.exists():
        for yaml_file in sorted(canon_dir.rglob("*.yaml")):
            with open(yaml_file) as f:
                canon_data = yaml.safe_load(f)
                if isinstance(canon_data, dict):
                    context.update(canon_data)
    return context


def fix_image_paths(md_text):
    """Rewrite relative image paths so pandoc can find them from repo root.

    Templates use ../visuals/foo.png (relative to templates/).
    When rendered into site/, the path ../visuals/ still works for local browsing,
    but pandoc runs from the repo root, so we rewrite to visuals/foo.png.
    """
    md_text = md_text.replace("../visuals/", "visuals/")
    md_text = md_text.replace("./visuals/", "visuals/")
    return md_text


def render_mermaid_blocks(md_text, out_dir):
    """Replace ```mermaid code blocks with rendered PNG images.

    If mmdc (mermaid-cli) is available, renders each block to a PNG
    and replaces the code block with an image reference.
    If mmdc is not available, wraps the code in a styled text block.
    """
    if not shutil.which("mmdc"):
        # No mermaid-cli: convert to plaintext diagram description
        def replace_with_text(match):
            return "> *[Diagram: Mermaid chart — see source Markdown for diagram code]*"

        return re.sub(r"```mermaid\n(.*?)```", replace_with_text, md_text, flags=re.DOTALL)

    counter = [0]

    def replace_with_image(match):
        counter[0] += 1
        mermaid_code = match.group(1)
        img_name = f"mermaid_diagram_{counter[0]}.png"
        img_path = out_dir / img_name
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".mmd", delete=False) as tmp:
                tmp.write(mermaid_code)
                tmp_path = tmp.name
            subprocess.run(
                ["mmdc", "-i", tmp_path, "-o", str(img_path), "-b", "transparent", "-w", "1200"],
                check=True,
                capture_output=True,
                timeout=30,
            )
            os.unlink(tmp_path)
            return f"![Diagram {counter[0]}]({img_path})"
        except Exception as e:
            print(f"    WARNING: Mermaid render failed: {e}")
            return "> *[Diagram: Mermaid chart — render failed]*"

    return re.sub(r"```mermaid\n(.*?)```", replace_with_image, md_text, flags=re.DOTALL)


def compile_markdown(context):
    """Render Jinja2 templates to Markdown."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), undefined=Undefined)
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    generated = []
    for tmpl_path in sorted(TEMPLATE_DIR.rglob("*.md.j2")):
        rel = tmpl_path.relative_to(TEMPLATE_DIR)
        out_name = str(rel).replace(".j2", "")
        out_path = SITE_DIR / out_name
        out_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            template = env.get_template(str(rel))
            rendered = template.render(data=context, **context)
            # Fix image paths and render mermaid diagrams
            rendered = fix_image_paths(rendered)
            rendered = render_mermaid_blocks(rendered, EXPORTS_DIR)
            out_path.write_text(rendered)
            generated.append(out_path)
            print(f"  MD: {out_path}")
        except Exception as e:
            print(f"  WARNING: Skipping {rel} due to template error: {e}")
    return generated


def compile_docx(md_files):
    """Convert Markdown files to DOCX using pandoc with formatting."""
    if not shutil.which("pandoc"):
        print("  WARNING: pandoc not found, skipping DOCX generation")
        return []
    generated = []
    for md_file in md_files:
        docx_name = md_file.stem + ".docx"
        out_path = EXPORTS_DIR / docx_name
        try:
            cmd = [
                "pandoc",
                str(md_file),
                "-o",
                str(out_path),
                "--from=markdown",
                "--to=docx",
                "--resource-path=.",
                "--toc",
                "--toc-depth=3",
                "--highlight-style=tango",
            ]
            # Add reference doc if it exists
            ref_doc = Path("templates/reference.docx")
            if ref_doc.exists():
                cmd.append(f"--reference-doc={ref_doc}")
            subprocess.run(cmd, check=True, capture_output=True)
            generated.append(out_path)
            print(f"  DOCX: {out_path}")
        except subprocess.CalledProcessError as e:
            print(f"  ERROR: Failed to generate {out_path}: {e.stderr.decode()}")
    return generated


def compile_pdf(md_files):
    """Convert Markdown files to PDF using pandoc with formatting."""
    if not shutil.which("pandoc"):
        print("  WARNING: pandoc not found, skipping PDF generation")
        return []
    generated = []
    for md_file in md_files:
        pdf_name = md_file.stem + ".pdf"
        out_path = EXPORTS_DIR / pdf_name
        try:
            cmd = [
                "pandoc",
                str(md_file),
                "-o",
                str(out_path),
                "--from=markdown",
                "--pdf-engine=xelatex",
                "--resource-path=.",
                "--toc",
                "--toc-depth=3",
                "--highlight-style=tango",
                "-V",
                "geometry:margin=1in",
                "-V",
                "colorlinks=true",
                "-V",
                "linkcolor=blue",
                "-V",
                "urlcolor=blue",
                "-V",
                "toccolor=gray",
                "-V",
                "mainfont=DejaVu Sans",
                "-V",
                "monofont=DejaVu Sans Mono",
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            generated.append(out_path)
            print(f"  PDF: {out_path}")
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode()
            if "Missing character" in stderr or "Font" in stderr:
                # Retry without custom fonts
                try:
                    cmd_retry = [
                        "pandoc",
                        str(md_file),
                        "-o",
                        str(out_path),
                        "--from=markdown",
                        "--pdf-engine=xelatex",
                        "--resource-path=.",
                        "--toc",
                        "-V",
                        "geometry:margin=1in",
                        "-V",
                        "colorlinks=true",
                    ]
                    subprocess.run(cmd_retry, check=True, capture_output=True)
                    generated.append(out_path)
                    print(f"  PDF: {out_path} (fallback fonts)")
                except subprocess.CalledProcessError as e2:
                    print(f"  WARNING: PDF failed for {md_file.name}: {e2.stderr.decode()[:200]}")
            else:
                print(f"  WARNING: PDF failed for {md_file.name}: {stderr[:200]}")
    return generated


def compile_html(md_files):
    """Convert Markdown files to standalone HTML with styling."""
    if not shutil.which("pandoc"):
        print("  WARNING: pandoc not found, skipping HTML generation")
        return []
    generated = []
    for md_file in md_files:
        html_name = md_file.stem + ".html"
        out_path = EXPORTS_DIR / html_name
        try:
            subprocess.run(
                [
                    "pandoc",
                    str(md_file),
                    "-o",
                    str(out_path),
                    "--from=markdown",
                    "--to=html5",
                    "--standalone",
                    "--resource-path=.",
                    "--toc",
                    "--toc-depth=3",
                    "--highlight-style=tango",
                    "--metadata",
                    "pagetitle=" + md_file.stem.replace("_", " ").replace("-", " ").title(),
                    "--css=https://cdn.jsdelivr.net/npm/water.css@2/out/water.min.css",
                    "--self-contained",
                ],
                check=True,
                capture_output=True,
            )
            generated.append(out_path)
            print(f"  HTML: {out_path}")
        except subprocess.CalledProcessError:
            # Retry without --self-contained (older pandoc)
            try:
                subprocess.run(
                    [
                        "pandoc",
                        str(md_file),
                        "-o",
                        str(out_path),
                        "--from=markdown",
                        "--to=html5",
                        "--standalone",
                        "--resource-path=.",
                        "--toc",
                        "--metadata",
                        "pagetitle=" + md_file.stem.replace("_", " ").title(),
                    ],
                    check=True,
                    capture_output=True,
                )
                generated.append(out_path)
                print(f"  HTML: {out_path} (basic)")
            except subprocess.CalledProcessError as e2:
                print(f"  ERROR: HTML failed for {out_path}: {e2.stderr.decode()[:200]}")
    return generated


def generate_manifest(all_exports):
    """Generate SHA-256 manifest for all exported files."""
    manifest = {}
    for export_file in sorted(all_exports):
        if export_file.exists():
            sha256 = hashlib.sha256(export_file.read_bytes()).hexdigest()
            manifest[str(export_file)] = {"sha256": sha256, "size_bytes": export_file.stat().st_size}
    manifest_path = EXPORTS_DIR / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"  MANIFEST: {manifest_path} ({len(manifest)} files)")
    return manifest_path


def main():
    print("=== UDC Document Compilation ===")
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # Load data
    print("Loading YAML data...")
    context = load_all_data()
    print(f"Loaded {len(context)} data keys")

    # Stage 1: Compile Markdown
    print("\nCompiling Markdown...")
    md_files = compile_markdown(context)

    # Stage 2: Compile DOCX
    print("\nCompiling DOCX...")
    docx_files = compile_docx(md_files)

    # Stage 3: Compile PDF
    print("\nCompiling PDF...")
    pdf_files = compile_pdf(md_files)

    # Stage 4: Compile HTML
    print("\nCompiling HTML...")
    html_files = compile_html(md_files)

    # Stage 5: Generate integrity manifest
    all_exports = docx_files + pdf_files + html_files
    if all_exports:
        print("\nGenerating integrity manifest...")
        generate_manifest(all_exports)

    print("\nCompilation complete.")
    print(f"  Markdown: {len(md_files)} files")
    print(f"  DOCX:     {len(docx_files)} files")
    print(f"  PDF:      {len(pdf_files)} files")
    print(f"  HTML:     {len(html_files)} files")


if __name__ == "__main__":
    main()
