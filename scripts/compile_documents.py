#!/usr/bin/env python3
"""UDC Document Compiler - Renders templates with data into publication formats."""
import hashlib
import json
import subprocess
import shutil
from pathlib import Path
import yaml
from jinja2 import Environment, FileSystemLoader

DATA_DIR = Path('data')
TEMPLATE_DIR = Path('templates')
EXPORTS_DIR = Path('exports')
SITE_DIR = Path('site')


def load_all_data():
    """Load all YAML files from data/ into a unified context."""
    context = {}
    for yaml_file in sorted(DATA_DIR.rglob('*.yml')):
        key = yaml_file.stem.replace('-', '_')
        with open(yaml_file) as f:
            context[key] = yaml.safe_load(f)
    for yaml_file in sorted(DATA_DIR.rglob('*.yaml')):
        key = yaml_file.stem.replace('-', '_')
        with open(yaml_file) as f:
            context[key] = yaml.safe_load(f)
                    # Also load canon YAML files (templates reference leadership_briefing, etc.)
    canon_dir = Path('canon')
    if canon_dir.exists():
        for yaml_file in sorted(canon_dir.rglob('*.yaml')):
            with open(yaml_file) as f:
                canon_data = yaml.safe_load(f)
                if isinstance(canon_data, dict):
                    context.update(canon_data)
    return context


def compile_markdown(context):
    """Render Jinja2 templates to Markdown (existing pipeline)."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    generated = []
    for tmpl_path in sorted(TEMPLATE_DIR.rglob('*.md.j2')):
        rel = tmpl_path.relative_to(TEMPLATE_DIR)
        out_name = str(rel).replace('.j2', '')
        out_path = SITE_DIR / out_name
        out_path.parent.mkdir(parents=True, exist_ok=True)
        template = env.get_template(str(rel))
        rendered = template.render(**context)
        out_path.write_text(rendered)
        generated.append(out_path)
        print(f'  MD: {out_path}')
    return generated


def compile_docx(md_files):
    """Convert Markdown files to DOCX using pandoc."""
    if not shutil.which('pandoc'):
        print('  WARNING: pandoc not found, skipping DOCX generation')
        return []
    generated = []
    for md_file in md_files:
        docx_name = md_file.stem + '.docx'
        out_path = EXPORTS_DIR / docx_name
        try:
            subprocess.run(
                ['pandoc', str(md_file), '-o', str(out_path),
                 '--from=markdown', '--to=docx'],
                check=True, capture_output=True
            )
            generated.append(out_path)
            print(f'  DOCX: {out_path}')
        except subprocess.CalledProcessError as e:
            print(f'  ERROR: Failed to generate {out_path}: {e.stderr.decode()}')
    return generated


def compile_pdf(md_files):
    """Convert Markdown files to PDF using pandoc."""
    if not shutil.which('pandoc'):
        print('  WARNING: pandoc not found, skipping PDF generation')
        return []
    generated = []
    for md_file in md_files:
        pdf_name = md_file.stem + '.pdf'
        out_path = EXPORTS_DIR / pdf_name
        try:
            subprocess.run(
                ['pandoc', str(md_file), '-o', str(out_path),
                 '--from=markdown', '--pdf-engine=xelatex'],
                check=True, capture_output=True
            )
            generated.append(out_path)
            print(f'  PDF: {out_path}')
        except subprocess.CalledProcessError as e:
            print(f'  WARNING: PDF generation failed for {md_file.name} (LaTeX may not be installed)')
    return generated


def compile_html(md_files):
    """Convert Markdown files to HTML using pandoc."""
    if not shutil.which('pandoc'):
        print('  WARNING: pandoc not found, skipping HTML generation')
        return []
    generated = []
    for md_file in md_files:
        html_name = md_file.stem + '.html'
        out_path = EXPORTS_DIR / html_name
        try:
            subprocess.run(
                ['pandoc', str(md_file), '-o', str(out_path),
                 '--from=markdown', '--to=html5', '--standalone'],
                check=True, capture_output=True
            )
            generated.append(out_path)
            print(f'  HTML: {out_path}')
        except subprocess.CalledProcessError as e:
            print(f'  ERROR: Failed to generate {out_path}: {e.stderr.decode()}')
    return generated


def generate_manifest(all_exports):
    """Generate SHA-256 manifest for all exported files."""
    manifest = {}
    for export_file in sorted(all_exports):
        if export_file.exists():
            sha256 = hashlib.sha256(export_file.read_bytes()).hexdigest()
            manifest[str(export_file)] = {
                'sha256': sha256,
                'size_bytes': export_file.stat().st_size
            }
    manifest_path = EXPORTS_DIR / 'manifest.json'
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    print(f'  MANIFEST: {manifest_path} ({len(manifest)} files)')
    return manifest_path


def main():
    print('=== UDC Document Compilation ===')
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # Load data
    print('Loading YAML data...')
    context = load_all_data()
    print(f'Loaded {len(context)} data files')

    # Stage 1: Compile Markdown
    print('\nCompiling Markdown...')
    md_files = compile_markdown(context)

    # Stage 2: Compile DOCX
    print('\nCompiling DOCX...')
    docx_files = compile_docx(md_files)

    # Stage 3: Compile PDF
    print('\nCompiling PDF...')
    pdf_files = compile_pdf(md_files)

    # Stage 4: Compile HTML
    print('\nCompiling HTML...')
    html_files = compile_html(md_files)

    # Stage 5: Generate integrity manifest
    all_exports = docx_files + pdf_files + html_files
    if all_exports:
        print('\nGenerating integrity manifest...')
        generate_manifest(all_exports)

    print(f'\nCompilation complete.')
    print(f'  Markdown: {len(md_files)} files')
    print(f'  DOCX: {len(docx_files)} files')
    print(f'  PDF: {len(pdf_files)} files')
    print(f'  HTML: {len(html_files)} files')


if __name__ == '__main__':
    main()
