#!/usr/bin/env python3
"""UIAO Document Generator - Renders docs from YAML data + Jinja2 templates."""
import os
import yaml
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

DATA_DIR = Path('data')
TEMPLATE_DIR = Path('templates')
OUTPUT_DIR = Path('site')


def load_all_data():
    """Load all YAML files from data/ into a unified context dict."""
    context = {}
    for yaml_file in DATA_DIR.rglob('*.yml'):
        key = yaml_file.stem.replace('-', '_')
        with open(yaml_file) as f:
            context[key] = yaml.safe_load(f)
    for yaml_file in DATA_DIR.rglob('*.yaml'):
        key = yaml_file.stem.replace('-', '_')
        with open(yaml_file) as f:
            context[key] = yaml.safe_load(f)
    return context


def render_templates(context):
    """Render all Jinja2 templates with the unified data context."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for tmpl_path in TEMPLATE_DIR.rglob('*.md.j2'):
        rel = tmpl_path.relative_to(TEMPLATE_DIR)
        out_name = str(rel).replace('.j2', '')
        out_path = OUTPUT_DIR / out_name
        out_path.parent.mkdir(parents=True, exist_ok=True)

        template = env.get_template(str(rel))
        rendered = template.render(**context)
        out_path.write_text(rendered)
        print(f'Generated: {out_path}')


def main():
    print('Loading YAML data...')
    context = load_all_data()
    print(f'Loaded {len(context)} data files')

    print('Rendering templates...')
    render_templates(context)
    print('Done.')


if __name__ == '__main__':
    main()
