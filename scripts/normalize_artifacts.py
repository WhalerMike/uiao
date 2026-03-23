#!/usr/bin/env python3
"""UDC Artifact Normalizer - Canonical ordering, metadata expansion, field completion."""

import copy
import datetime
import warnings
from pathlib import Path

import yaml

warnings.warn(
    "scripts/normalize_artifacts.py is deprecated. Use `uiao` CLI instead.",
    DeprecationWarning,
    stacklevel=1,
)
DATA_DIR = Path('data')
NORMALIZED_DIR = Path('normalized')

# Canonical key ordering for UDC metadata
METADATA_KEY_ORDER = [
    'id', 'title', 'version', 'status', 'classification',
    'authors', 'created_date', 'modified_date',
    'canonical_path', 'tags', 'supersedes', 'sha256_hash'
]


def ordered_dump(data, stream=None, **kwargs):
    """Dump YAML with consistent formatting."""
    class OrderedDumper(yaml.SafeDumper):
        pass
    def _dict_representer(dumper, data):
        return dumper.represent_mapping(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
            data.items()
        )
    OrderedDumper.add_representer(dict, _dict_representer)
    return yaml.dump(data, stream, OrderedDumper, **kwargs)


def reorder_keys(data, key_order):
    """Reorder dictionary keys according to canonical order."""
    if not isinstance(data, dict):
        return data
    ordered = {}
    for key in key_order:
        if key in data:
            ordered[key] = data[key]
    for key in data:
        if key not in ordered:
            ordered[key] = data[key]
    return ordered


def expand_metadata(data, file_path):
    """Add or expand metadata fields with defaults."""
    normalized = copy.deepcopy(data)
    if not isinstance(normalized, dict):
        return normalized

    # Set modified_date to today if not present
    if 'modified_date' not in normalized:
        normalized['modified_date'] = datetime.date.today().isoformat()

    # Set canonical_path if not present
    if 'canonical_path' not in normalized:
        normalized['canonical_path'] = str(file_path)

    # Default classification
    if 'classification' not in normalized:
        normalized['classification'] = 'unclassified'

    # Default status
    if 'status' not in normalized:
        normalized['status'] = 'draft'

    # Ensure tags is a list
    if 'tags' in normalized and not isinstance(normalized['tags'], list):
        normalized['tags'] = [normalized['tags']]

    return normalized


def normalize_file(yaml_path):
    """Normalize a single YAML artifact."""
    with open(yaml_path) as f:
        data = yaml.safe_load(f)

    if data is None:
        return None

    if not isinstance(data, dict):
        return data

    # Expand metadata
    normalized = expand_metadata(data, yaml_path)

    # Reorder keys
    normalized = reorder_keys(normalized, METADATA_KEY_ORDER)

    return normalized


def main():
    print('=== UDC Artifact Normalization ===')
    NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)

    yaml_files = list(DATA_DIR.rglob('*.yml')) + list(DATA_DIR.rglob('*.yaml'))

    if not yaml_files:
        print('No YAML files found in data/')
        return

    print(f'Found {len(yaml_files)} YAML file(s)')

    for yaml_file in sorted(yaml_files):
        normalized = normalize_file(yaml_file)
        if normalized is None:
            print(f'  SKIP: {yaml_file} (empty)')
            continue

        # Preserve relative path structure
        rel_path = yaml_file.relative_to(DATA_DIR)
        out_path = NORMALIZED_DIR / rel_path
        out_path.parent.mkdir(parents=True, exist_ok=True)

        with open(out_path, 'w') as f:
            ordered_dump(normalized, f, default_flow_style=False, allow_unicode=True)

        print(f'  NORMALIZED: {yaml_file} -> {out_path}')

    print('Normalization complete.')


if __name__ == '__main__':
    main()
