"""Shared YAML loader helpers for the Model C orgtree consumers.

Each consumer module (dynamic_groups, admin_units, policy_targeting,
device_orgpath) exposes a ``load_*_from_yaml()`` function that uses
these helpers to read its YAML library, validate against the matching
JSON Schema, and return a populated consumer object.

Per ADR-084 §C1 (Codebook-as-shared-dependency) the YAML loaders are
optional convenience — consumers can also be built programmatically via
each module's ``from_specs()``. The loaders exist so canon-shipped
starter libraries (in ``src/uiao/canon/data/orgpath/``) populate
consumers without the caller having to translate YAML themselves.
"""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any, Dict

import yaml


class YamlLibraryValidationError(ValueError):
    """Raised when a YAML library fails schema validation."""


def read_yaml_resource(package: str, name: str) -> Dict[str, Any]:
    """Read + parse a YAML resource shipped inside the uiao package."""
    raw = resources.files(package).joinpath(name).read_text(encoding="utf-8")
    doc = yaml.safe_load(raw)
    if not isinstance(doc, dict):
        raise YamlLibraryValidationError(f"Resource {package}/{name} must be a YAML mapping at the top level")
    return doc


def read_yaml_path(path: Path | str) -> Dict[str, Any]:
    """Read + parse a YAML file from an arbitrary path (used in tests / overrides)."""
    raw = Path(path).read_text(encoding="utf-8")
    doc = yaml.safe_load(raw)
    if not isinstance(doc, dict):
        raise YamlLibraryValidationError(f"YAML file {path} must be a mapping at the top level")
    return doc


def read_schema_resource(package: str, name: str) -> Dict[str, Any]:
    raw = resources.files(package).joinpath(name).read_text(encoding="utf-8")
    result: Dict[str, Any] = json.loads(raw)
    return result


def validate_against_schema(document: Dict[str, Any], schema: Dict[str, Any], label: str) -> None:
    """Run JSON Schema validation; raise YamlLibraryValidationError on failure."""
    try:
        import jsonschema
    except ImportError as exc:  # pragma: no cover
        raise YamlLibraryValidationError("jsonschema is required to validate YAML libraries") from exc
    try:
        jsonschema.validate(instance=document, schema=schema)
    except jsonschema.ValidationError as exc:
        path = "/".join(str(p) for p in exc.absolute_path)
        raise YamlLibraryValidationError(f"{label} YAML failed schema validation: {exc.message} at {path}") from exc
