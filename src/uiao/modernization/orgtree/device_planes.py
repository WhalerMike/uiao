"""Device OrgPath plane registry loader (MOD_C, ADR-038).

Loads ``src/uiao/canon/data/orgpath/device-planes.yaml`` which declares,
for every ``ComputerDisposition.orgpath_plane`` value, the write mechanism
(transport + endpoint template + body template) the
``entra-device-orgpath`` adapter dispatches on.

The loader enforces three integrity checks beyond JSON Schema:

1. **Plane ↔ disposition coverage** — every non-skip disposition value
   surfaced by :mod:`...active_directory.disposition` is referenced by
   at least one plane entry; every plane references at least one
   known disposition.
2. **Disposition uniqueness** — no two planes claim the same disposition
   (a disposition lands on exactly one plane).
3. **ARM tag regex agreement** — the ARM-tag ``value_regex`` matches the
   canonical OrgPath regex shipped with MOD_A (ADR-035); they must stay
   in lock-step.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Dict, Mapping, Optional, Set, Tuple

import yaml

from .codebook import Codebook, default_codebook

_KNOWN_DISPOSITIONS: Set[str] = {
    "ENTRA-DEVICE",
    "ARC-SERVER",
    "MANAGED-IDENTITY-CANDIDATE",
    "STAY-AD-DEPENDENCY",
    "STAY-AD-DC",
    "DECOMMISSION",
}


class DevicePlaneValidationError(ValueError):
    """Raised when the device-plane registry fails schema or integrity validation."""


@dataclass(frozen=True)
class DevicePlane:
    name: str
    transport: str
    target_object: str
    http_method: str
    endpoint_template: str
    body_template: Dict[str, object]
    read_endpoint_template: str
    read_value_path: str
    dispositions: Tuple[str, ...]
    description: str


@dataclass(frozen=True)
class SkipDisposition:
    name: str
    reason: str


@dataclass(frozen=True)
class ArmTagSpec:
    key: str
    key_regex: str
    value_regex: str


@dataclass(frozen=True)
class DevicePlaneRegistry:
    schema_version: str
    document_id: str
    parent_canon: str
    planes: Mapping[str, DevicePlane]
    skip_dispositions: Mapping[str, SkipDisposition]
    arm_tag: ArmTagSpec

    @property
    def plane_names(self) -> Set[str]:
        return set(self.planes.keys())

    def plane_for_disposition(self, disposition: str) -> Optional[DevicePlane]:
        for plane in self.planes.values():
            if disposition in plane.dispositions:
                return plane
        return None

    def is_skip(self, disposition: str) -> bool:
        return disposition in self.skip_dispositions


_DEFAULT_REGISTRY_RESOURCE = ("uiao.canon.data.orgpath", "device-planes.yaml")
_DEFAULT_SCHEMA_RESOURCE = ("uiao.schemas.orgpath", "device-planes.schema.json")


def _read_default_registry() -> str:
    package, name = _DEFAULT_REGISTRY_RESOURCE
    return resources.files(package).joinpath(name).read_text(encoding="utf-8")


def _read_default_schema() -> Dict:
    package, name = _DEFAULT_SCHEMA_RESOURCE
    return json.loads(resources.files(package).joinpath(name).read_text(encoding="utf-8"))


def _validate_schema(document: Dict) -> None:
    try:
        import jsonschema
    except ImportError as exc:  # pragma: no cover
        raise DevicePlaneValidationError("jsonschema is required to validate the device-plane registry") from exc
    schema = _read_default_schema()
    try:
        jsonschema.validate(instance=document, schema=schema)
    except jsonschema.ValidationError as exc:
        raise DevicePlaneValidationError(
            f"Device-plane registry schema validation failed: {exc.message} "
            f"at {'/'.join(str(p) for p in exc.absolute_path)}"
        ) from exc


def _validate_integrity(document: Dict, codebook: Codebook) -> None:
    planes = document["planes"]
    plane_names: Set[str] = set()
    claimed_dispositions: Dict[str, str] = {}

    for plane in planes:
        if plane["name"] in plane_names:
            raise DevicePlaneValidationError(f"Duplicate plane name: {plane['name']}")
        plane_names.add(plane["name"])
        for disposition in plane["dispositions"]:
            if disposition in claimed_dispositions:
                raise DevicePlaneValidationError(
                    f"Disposition '{disposition}' claimed by two planes: "
                    f"'{claimed_dispositions[disposition]}' and '{plane['name']}'"
                )
            claimed_dispositions[disposition] = plane["name"]

    skip_names = {d["name"] for d in document.get("skip_dispositions", [])}
    overlap = claimed_dispositions.keys() & skip_names
    if overlap:
        raise DevicePlaneValidationError(
            f"Dispositions {sorted(overlap)} appear in both planes[] and skip_dispositions[] — pick exactly one"
        )

    covered = set(claimed_dispositions.keys()) | skip_names
    missing = _KNOWN_DISPOSITIONS - covered
    if missing:
        raise DevicePlaneValidationError(f"Registry is missing coverage for dispositions: {sorted(missing)}")

    # ARM tag regex must agree with the canonical OrgPath regex. We compare
    # against a reference copy shipped with MOD_A so a divergence between
    # canon files gets caught at load, not at runtime.
    canonical_regex = codebook.regex
    arm_regex = document["arm_tag"]["value_regex"]
    if arm_regex != canonical_regex:
        raise DevicePlaneValidationError(
            f"arm_tag.value_regex ({arm_regex!r}) does not match the "
            f"canonical MOD_A regex ({canonical_regex!r}) — cross-canon drift"
        )


def _build(document: Dict) -> DevicePlaneRegistry:
    planes = {
        p["name"]: DevicePlane(
            name=p["name"],
            transport=p["transport"],
            target_object=p["target_object"],
            http_method=p["http_method"],
            endpoint_template=p["endpoint_template"],
            body_template=p["body_template"],
            read_endpoint_template=p["read_endpoint_template"],
            read_value_path=p["read_value_path"],
            dispositions=tuple(p["dispositions"]),
            description=p["description"],
        )
        for p in document["planes"]
    }
    skips = {
        s["name"]: SkipDisposition(name=s["name"], reason=s["reason"])
        for s in document.get("skip_dispositions", []) or []
    }
    arm = document["arm_tag"]
    return DevicePlaneRegistry(
        schema_version=document["schema_version"],
        document_id=document["document_id"],
        parent_canon=document["parent_canon"],
        planes=planes,
        skip_dispositions=skips,
        arm_tag=ArmTagSpec(
            key=arm["key"],
            key_regex=arm["key_regex"],
            value_regex=arm["value_regex"],
        ),
    )


def load_device_plane_registry(
    path: Optional[Path] = None,
    codebook: Optional[Codebook] = None,
) -> DevicePlaneRegistry:
    """Load and validate the device-plane registry."""
    raw_text = _read_default_registry() if path is None else Path(path).read_text(encoding="utf-8")
    document = yaml.safe_load(raw_text)
    if not isinstance(document, dict):
        raise DevicePlaneValidationError("Device-plane registry must be a YAML mapping at the top level")
    _validate_schema(document)
    _validate_integrity(document, codebook or default_codebook())
    return _build(document)


@lru_cache(maxsize=1)
def default_device_plane_registry() -> DevicePlaneRegistry:
    return load_device_plane_registry()
