#!/usr/bin/env python3
"""Validate canonical YAML files against their JSON Schemas.

Mirrors the checks performed by .github/workflows/schema-validation.yml so
local `make schemas` agrees with CI.
"""
from __future__ import annotations

import json
import sys

import yaml
from jsonschema import Draft7Validator, Draft202012Validator


CHECKS = [
    (
        "adapter-registry",
        "core/canon/adapter-registry.yaml",
        "core/schemas/adapter-registry/adapter-registry.schema.json",
        Draft7Validator,
    ),
    (
        "modernization-registry",
        "core/canon/modernization-registry.yaml",
        "core/schemas/adapter-registry/adapter-registry.schema.json",
        Draft7Validator,
    ),
    (
        "substrate-manifest",
        "core/canon/substrate-manifest.yaml",
        "core/schemas/substrate-manifest/substrate-manifest.schema.json",
        Draft202012Validator,
    ),
    (
        "workspace-contract",
        "core/canon/workspace-contract.yaml",
        "core/schemas/workspace-contract/workspace-contract.schema.json",
        Draft202012Validator,
    ),
]

METADATA_SCHEMA = "core/schemas/metadata-schema.json"


def main() -> int:
    failed = False
    for name, data_path, schema_path, validator_cls in CHECKS:
        schema = json.load(open(schema_path))
        data = yaml.safe_load(open(data_path))
        errors = list(validator_cls(schema).iter_errors(data))
        status = "PASS" if not errors else "FAIL"
        print(f"  [{status}] {name}")
        if errors:
            failed = True
            for err in errors[:5]:
                loc = ".".join(str(p) for p in err.absolute_path) or "<root>"
                print(f"         [{loc}] {err.message}")

    meta_schema = json.load(open(METADATA_SCHEMA))
    meta_validator = Draft202012Validator(meta_schema)
    for name, data_path in [
        ("substrate-manifest.metadata", "core/canon/substrate-manifest.yaml"),
        ("workspace-contract.metadata", "core/canon/workspace-contract.yaml"),
    ]:
        data = yaml.safe_load(open(data_path)).get("metadata", {})
        errors = list(meta_validator.iter_errors(data))
        status = "PASS" if not errors else "FAIL"
        print(f"  [{status}] {name}")
        if errors:
            failed = True
            for err in errors[:5]:
                loc = ".".join(str(p) for p in err.absolute_path) or "<root>"
                print(f"         [{loc}] {err.message}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
