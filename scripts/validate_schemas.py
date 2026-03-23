#!/usr/bin/env python3
"""UDC Schema Validator - Validates YAML data files against UDC JSON schemas."""
import json
import sys
import warnings
from pathlib import Path

import yaml
from jsonschema import SchemaError, ValidationError, validate

warnings.warn(
    "scripts/validate_schemas.py is deprecated. Use `uiao` CLI instead.",
    DeprecationWarning,
    stacklevel=1,
)

DATA_DIR = Path('data')
SCHEMA_DIR = Path('schemas/udc')


def load_schema(schema_name):
    """Load a JSON schema from schemas/udc/."""
    schema_path = SCHEMA_DIR / f'{schema_name}.schema.json'
    if not schema_path.exists():
        print(f'  WARNING: Schema not found: {schema_path}')
        return None
    with open(schema_path) as f:
        return json.load(f)


def validate_file(yaml_path, schema):
    """Validate a single YAML file against a JSON schema."""
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    if data is None:
        print(f'  SKIP: {yaml_path} (empty file)')
        return True
    try:
        validate(instance=data, schema=schema)
        print(f'  PASS: {yaml_path}')
        return True
    except ValidationError as e:
        print(f'  FAIL: {yaml_path}')
        print(f'        {e.message}')
        return False
    except SchemaError as e:
        print(f'  ERROR: Invalid schema - {e.message}')
        return False


def detect_schema_for_file(yaml_path):
    """Detect which schema to use based on file content metadata."""
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    if data is None:
        return None
    # Check if file has UDC metadata fields
    if isinstance(data, dict):
        if 'id' in data and 'version' in data and 'status' in data:
            return 'udc_metadata'
        if 'template_id' in data and 'template_type' in data:
            return 'udc_templates'
        if 'pipeline_stages' in data:
            return 'udc_pipeline'
        if 'export_config' in data:
            return 'udc_export'
    return None


def main():
    print('=== UDC Schema Validation ===')
    print(f'Data directory: {DATA_DIR}')
    print(f'Schema directory: {SCHEMA_DIR}')
    print()

    errors = 0
    validated = 0
    skipped = 0

    # Collect all YAML files
    yaml_files = list(DATA_DIR.rglob('*.yml')) + list(DATA_DIR.rglob('*.yaml'))

    if not yaml_files:
        print('No YAML files found in data/')
        return

    print(f'Found {len(yaml_files)} YAML file(s)')
    print()

    for yaml_file in sorted(yaml_files):
        schema_name = detect_schema_for_file(yaml_file)
        if schema_name:
            schema = load_schema(schema_name)
            if schema:
                if not validate_file(yaml_file, schema):
                    errors += 1
                validated += 1
            else:
                skipped += 1
        else:
            print(f'  SKIP: {yaml_file} (no matching schema detected)')
            skipped += 1

    print()
    print(f'Results: {validated} validated, {errors} errors, {skipped} skipped')

    if errors > 0:
        print('VALIDATION FAILED')
        sys.exit(1)
    else:
        print('VALIDATION PASSED')


if __name__ == '__main__':
    main()
