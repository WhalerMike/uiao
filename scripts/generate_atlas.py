#!/usr/bin/env python3
"""
UIAO Modernization Atlas Generator
Renders Atlas docs from YAML data + Jinja2 templates (.j2).
Copies images from assets/images/ to docs/images/ for MkDocs.
"""

import warnings
warnings.warn(
    "scripts/generate_atlas.py is deprecated. Use `uiao generate-atlas` instead.",
    DeprecationWarning,
    stacklevel=1,
)

import os
import re
import yaml
import shutil
from jinja2 import Environment, FileSystemLoader

# --- CONFIGURATION ---
DATA_DIR = 'data'
TEMPLATE_DIR = 'templates'
OUTPUT_DIR = 'docs'
IMAGE_SRC = 'assets/images'
IMAGE_DEST = os.path.join(OUTPUT_DIR, 'images')


def normalize_key(value):
    """Filter to convert hyphens to underscores for Jinja2 variable safety."""
    if isinstance(value, str):
        return re.sub(r'-', '_', value)
    return value


def setup_environment():
    """Ensure output directories exist."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    if not os.path.exists(IMAGE_DEST):
        os.makedirs(IMAGE_DEST)


def copy_assets():
    """Copies PNG images from assets/ to docs/images/ for the build."""
    if os.path.exists(IMAGE_SRC):
        count = 0
        for filename in os.listdir(IMAGE_SRC):
            if filename.endswith(('.png', '.jpg', '.svg')):
                shutil.copy2(os.path.join(IMAGE_SRC, filename), IMAGE_DEST)
                count += 1
        print(f"✅ {count} assets copied to {IMAGE_DEST}")
    else:
        print(f"⚠️ Warning: {IMAGE_SRC} not found. Skipping image copy.")


def load_data():
    """Loads all YAML data sources into a unified context."""
    data = {}

    # Load all YAML files from data/
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(('.yml', '.yaml')):
            key = filename.rsplit('.', 1)[0].replace('-', '_')
            path = os.path.join(DATA_DIR, filename)
            with open(path, 'r') as f:
                loaded = yaml.safe_load(f)
                if loaded:
                    data[key] = loaded

    # Extract diagrams for direct template access (diagrams.unified_arch etc.)
    if 'diagrams' in data:
        diag = data['diagrams']
        # If diagrams are nested under a 'diagrams' key, flatten
        if isinstance(diag, dict) and 'diagrams' in diag:
            data['diagrams'] = diag['diagrams']

    # Extract atlas-appendices for template access
    if 'atlas_appendices' in data:
        atlas = data['atlas_appendices']
        if isinstance(atlas, dict) and 'appendices' in atlas:
            normalized = {normalize_key(k): v for k, v in atlas['appendices'].items()}
            data['appendices'] = normalized

    return data


def run_pipeline():
    setup_environment()
    copy_assets()

    all_context = load_data()
    print(f"📦 Loaded {len(all_context)} data sources")

    # Setup Jinja2
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    env.filters['normalize'] = normalize_key

    # Atlas template manifest (.j2 -> .md)
    manifest = {
        'index.j2': 'index.md',
        'architecture.j2': 'architecture.md',
        'appendices.j2': 'appendices.md',
        'telemetry.j2': 'telemetry.md',
        'logic.j2': 'logic.md',
        'comparison.j2': 'comparison.md',
        'scaling.j2': 'scaling.md',
        'roadmap.j2': 'roadmap.md',
    }

    success = 0
    errors = 0
    for template_name, output_name in manifest.items():
        try:
            template = env.get_template(template_name)
            output_path = os.path.join(OUTPUT_DIR, output_name)

            with open(output_path, 'w') as f:
                f.write(template.render(all_context))
            print(f"🚀 Generated: {output_path}")
            success += 1
        except Exception as e:
            print(f"❌ Error rendering {template_name}: {e}")
            errors += 1

    print(f"\n✨ Atlas build complete: {success} generated, {errors} errors.")
    if errors > 0:
        exit(1)


if __name__ == "__main__":
    run_pipeline()
