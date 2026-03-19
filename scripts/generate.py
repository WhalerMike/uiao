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
    """Load all YAML files and merge top-level keys into a unified context."""
    context = {}
    for yaml_file in sorted(DATA_DIR.rglob('*.yml')):
        with open(yaml_file) as f:
            data = yaml.safe_load(f)
        if isinstance(data, dict):
            context.update(data)
        else:
            key = yaml_file.stem.replace('-', '_')
            context[key] = data
    for yaml_file in sorted(DATA_DIR.rglob('*.yaml')):
        with open(yaml_file) as f:
            data = yaml.safe_load(f)
        if isinstance(data, dict):
            context.update(data)
        else:
            key = yaml_file.stem.replace('-', '_')
            context[key] = data
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
    print(f'Loaded {len(context)} top-level keys: {list(context.keys())}')

    print('Rendering templates...')
    render_templates(context)
    print('Done.')


if __name__ == '__main__':
    main()
