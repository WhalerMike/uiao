"""HR duty-station → LocPath assignment — ADR-102 §D6 phase 2.

Per ADR-102 §D3 (extending ADR-088), the workforce HR system of record
is the authoritative source for a person's assigned place. This module
is the read-only conformance surface for that doctrine: it resolves the
Spec2-D1.1 ``locationCode`` carried on canonical HR records
(:class:`uiao.adapters.modernization.hrit.inventory.HRRecord`) through a
governed **duty-station map** into Primary-LocPath assignments against a
validated **location registry** (UIAO_194), emitting drift findings —
never writes — for anything that does not resolve.

Components:

* :class:`DutyStationMap` — the governed translation table from the HR
  locationCode vocabulary to canonical LocPath, loaded from
  ``src/uiao/canon/data/locpath/duty-station-map.yaml`` (the
  ``reference`` map) or an agency path. Load-time validation: the
  envelope + entries against ``duty-station-map.schema.json``, plus the
  integrity rules JSON Schema cannot express — case-insensitive code
  uniqueness, and every target locPath resolving in the paired location
  registry **at Site level or deeper** (ADR-102 §D1: Site is the
  minimum governance unit).
* :func:`assign_locpaths` — the assignment pass. For each HR record it
  produces a :class:`LocPathAssignment` (employee → Primary LocPath +
  its governing Site + provenance) or a
  :class:`~uiao.adapters.modernization.hrit.inventory.DriftFinding`
  (same shape as every other modernization survey, so findings merge
  into a single substrate report).

Drift classes: unresolvable or degraded assignments emit
``DRIFT-IDENTITY::location-assignment`` — the location-assignment drift
class shipped by ADR-102 §D6 phase 3
(:mod:`uiao.modernization.locpath.drift`), a sub-class of the canonical
``DRIFT-IDENTITY`` per the ADR-063 / UIAO_163 sub-class convention,
with stable ``GOV-LOCPATH-NNN`` error codes.

Read-only and dry-run by nature: no Entra exposure (phase 4), no
mutation of any system. Boundary: Moderate/Commercial only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import cache, lru_cache
from importlib import resources
from pathlib import Path
from typing import Iterable, Mapping

import yaml

from uiao.adapters.modernization.hrit.inventory import DriftFinding, HRRecord
from uiao.modernization.locpath.drift import DRIFT_LOCATION_ASSIGNMENT
from uiao.modernization.locpath.registry import (
    LocationRegistry,
    LocationRegistryValidationError,
    load_location_registry,
)

#: Packaged path of the canonical reference duty-station map.
CANONICAL_MAP_RESOURCE = "data/locpath/duty-station-map.yaml"

# Error codes (GOV-LOCPATH-NNN) — stable identifiers for the phase 3
# drift-taxonomy re-class.
ERROR_EMPTY_LOCATION_CODE = "GOV-LOCPATH-001"
ERROR_UNMAPPED_LOCATION_CODE = "GOV-LOCPATH-002"
ERROR_UNREGISTERED_TARGET = "GOV-LOCPATH-003"
ERROR_INACTIVE_TARGET = "GOV-LOCPATH-004"
ERROR_DUPLICATE_EMPLOYEE = "GOV-LOCPATH-005"


class DutyStationMapValidationError(ValueError):
    """Raised when a duty-station-map YAML fails schema or integrity validation."""


@dataclass(frozen=True)
class DutyStationMapping:
    """One governed locationCode → LocPath translation."""

    location_code: str
    loc_path: str
    description: str | None = None


@dataclass(frozen=True)
class DutyStationMap:
    """A validated duty-station map (envelope + entries)."""

    map_id: str
    schema_version: str
    status: str
    display_name: str
    updated: str
    entries: tuple[DutyStationMapping, ...]
    description: str | None = None

    def resolve(self, location_code: str) -> DutyStationMapping | None:
        """The mapping for ``location_code`` (case-insensitive), if declared."""
        needle = location_code.lower()
        for entry in self.entries:
            if entry.location_code.lower() == needle:
                return entry
        return None


@dataclass(frozen=True)
class LocPathAssignment:
    """One employee's resolved Primary LocPath (UIAO_194 §The two-layer location model)."""

    employee_id: str
    location_code: str
    loc_path: str
    loc_path_id: str
    site_path: str
    primary_duty_station: bool = True
    provenance: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class LocPathAssignmentPlan:
    """The read-only output of one assignment pass: assignments + findings."""

    map_id: str
    registry_id: str
    assignments: tuple[LocPathAssignment, ...]
    findings: tuple[DriftFinding, ...]

    def unmapped_codes(self) -> tuple[str, ...]:
        """Distinct locationCodes that produced unmapped findings, in first-seen order."""
        seen: list[str] = []
        for finding in self.findings:
            if finding.error_code == ERROR_UNMAPPED_LOCATION_CODE and finding.detail not in seen:
                seen.append(finding.detail)
        return tuple(seen)


# ---------------------------------------------------------------------------
# Duty-station map loading + validation
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _load_map_schema() -> dict[str, object]:
    schema_text = (
        resources.files("uiao.schemas").joinpath("locpath/duty-station-map.schema.json").read_text(encoding="utf-8")
    )
    loaded = json.loads(schema_text)
    if not isinstance(loaded, dict):
        raise DutyStationMapValidationError("duty-station-map.schema.json must be a JSON object")
    return loaded


def _validate_map_schema(doc: Mapping[str, object], source: str) -> None:
    import jsonschema

    validator = jsonschema.Draft202012Validator(_load_map_schema())
    errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path))
    if errors:
        details = "; ".join(f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}" for e in errors[:5])
        raise DutyStationMapValidationError(f"{source}: schema validation failed — {details}")


def _check_map_integrity(duty_map: DutyStationMap, registry: LocationRegistry, source: str) -> None:
    """Enforce the UIAO_194 invariants JSON Schema cannot express."""
    seen_codes: dict[str, str] = {}
    for entry in duty_map.entries:
        key = entry.location_code.lower()
        if key in seen_codes:
            raise DutyStationMapValidationError(
                f"{source}: locationCode '{entry.location_code}' collides with "
                f"'{seen_codes[key]}' (matching is case-insensitive)"
            )
        seen_codes[key] = entry.location_code
        node = registry.node_for(entry.loc_path)
        if node is None:
            raise DutyStationMapValidationError(
                f"{source}: locationCode '{entry.location_code}' maps to "
                f"'{entry.loc_path}' which is not in location registry '{registry.registry_id}'"
            )
        if node.depth < 3:
            raise DutyStationMapValidationError(
                f"{source}: locationCode '{entry.location_code}' maps to {node.level}-level "
                f"'{entry.loc_path}' — assignments must resolve at Site level or deeper (ADR-102 §D1)"
            )


def _map_from_doc(doc: Mapping[str, object], registry: LocationRegistry, source: str) -> DutyStationMap:
    _validate_map_schema(doc, source)
    entries_raw = doc["entries"]
    if not isinstance(entries_raw, list):
        raise DutyStationMapValidationError(f"{source}: 'entries' must be a list")
    entries = tuple(
        DutyStationMapping(
            location_code=str(entry["locationCode"]),
            loc_path=str(entry["locPath"]),
            description=entry.get("description"),
        )
        for entry in entries_raw
        if isinstance(entry, Mapping)
    )
    duty_map = DutyStationMap(
        map_id=str(doc["map_id"]),
        schema_version=str(doc["schema_version"]),
        status=str(doc["status"]),
        display_name=str(doc["display_name"]),
        updated=str(doc["updated"]),
        entries=entries,
        description=doc.get("description"),  # type: ignore[arg-type]
    )
    _check_map_integrity(duty_map, registry, source)
    return duty_map


def load_duty_station_map_from_path(path: Path | str, registry: LocationRegistry | None = None) -> DutyStationMap:
    """Load and validate a duty-station map from an explicit filesystem path."""
    source = str(path)
    doc = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(doc, Mapping):
        raise DutyStationMapValidationError(f"{source}: map YAML must be a mapping at the top level")
    return _map_from_doc(doc, registry or load_location_registry(), source)


@cache
def load_duty_station_map() -> DutyStationMap:
    """Load the canonical reference duty-station map from packaged canon."""
    source = f"uiao.canon:{CANONICAL_MAP_RESOURCE}"
    text = resources.files("uiao.canon").joinpath(CANONICAL_MAP_RESOURCE).read_text(encoding="utf-8")
    doc = yaml.safe_load(text)
    if not isinstance(doc, Mapping):
        raise DutyStationMapValidationError(f"{source}: map YAML must be a mapping at the top level")
    return _map_from_doc(doc, load_location_registry(), source)


# ---------------------------------------------------------------------------
# Assignment pass
# ---------------------------------------------------------------------------


def _governing_site_path(registry: LocationRegistry, loc_path: str) -> str:
    """The Site-level path governing ``loc_path`` (itself, for Site nodes)."""
    node = registry.node_for(loc_path)
    if node is not None and node.level == "Site":
        return node.loc_path
    for ancestor in registry.ancestors_of(loc_path):
        if ancestor.level == "Site":
            return ancestor.loc_path
    # Map integrity guarantees Site-or-deeper targets under a registered
    # Site, so this is unreachable for validated inputs.
    raise LocationRegistryValidationError(f"no Site-level ancestor registered for '{loc_path}'")


def assign_locpaths(
    records: Iterable[HRRecord],
    duty_station_map: DutyStationMap | None = None,
    registry: LocationRegistry | None = None,
) -> LocPathAssignmentPlan:
    """Resolve HR records to Primary-LocPath assignments — read-only.

    Each record's ``location_code`` is resolved through the duty-station
    map into a registered location node; the result carries the node's
    governing Site and full provenance (HR source ``extracted_at``,
    ``adapter_metadata``, map + registry ids). Records that do not
    resolve produce :class:`DriftFinding` entries instead — the pass
    never raises on record-level problems and never mutates anything.
    """
    duty_map = duty_station_map or load_duty_station_map()
    reg = registry or load_location_registry()

    assignments: list[LocPathAssignment] = []
    findings: list[DriftFinding] = []
    seen_employees: set[str] = set()

    for record in records:
        anchor = record.employee_id
        if anchor in seen_employees:
            findings.append(
                DriftFinding(
                    drift_class=DRIFT_LOCATION_ASSIGNMENT,
                    severity="P3",
                    path=anchor,
                    detail=f"duplicate employeeId '{anchor}' — first record wins; at most one "
                    "Primary LocPath per identity (UIAO_194 §The two-layer location model)",
                    error_code=ERROR_DUPLICATE_EMPLOYEE,
                    object_type="HRRecord",
                )
            )
            continue
        seen_employees.add(anchor)

        code = record.location_code.strip()
        if not code:
            findings.append(
                DriftFinding(
                    drift_class=DRIFT_LOCATION_ASSIGNMENT,
                    severity="P2",
                    path=anchor,
                    detail="HR record carries no locationCode — Primary LocPath cannot be derived",
                    error_code=ERROR_EMPTY_LOCATION_CODE,
                    object_type="HRRecord",
                )
            )
            continue

        mapping = duty_map.resolve(code)
        if mapping is None:
            findings.append(
                DriftFinding(
                    drift_class=DRIFT_LOCATION_ASSIGNMENT,
                    severity="P2",
                    path=anchor,
                    detail=code,
                    error_code=ERROR_UNMAPPED_LOCATION_CODE,
                    object_type="HRRecord",
                )
            )
            continue

        node = reg.node_for(mapping.loc_path)
        if node is None:
            findings.append(
                DriftFinding(
                    drift_class=DRIFT_LOCATION_ASSIGNMENT,
                    severity="P1",
                    path=anchor,
                    detail=f"duty-station map '{duty_map.map_id}' targets '{mapping.loc_path}' "
                    f"which is not in location registry '{reg.registry_id}'",
                    error_code=ERROR_UNREGISTERED_TARGET,
                    object_type="HRRecord",
                )
            )
            continue

        if node.status != "Active":
            findings.append(
                DriftFinding(
                    drift_class=DRIFT_LOCATION_ASSIGNMENT,
                    severity="P3",
                    path=anchor,
                    detail=f"assigned location '{node.loc_path}' has status '{node.status}' — "
                    "assignment recorded; remap before the node is retired (UIAO_194 §Governance)",
                    error_code=ERROR_INACTIVE_TARGET,
                    object_type="HRRecord",
                )
            )

        assignments.append(
            LocPathAssignment(
                employee_id=anchor,
                location_code=code,
                loc_path=node.loc_path,
                loc_path_id=node.loc_path_id,
                site_path=_governing_site_path(reg, node.loc_path),
                primary_duty_station=True,
                provenance={
                    "hr_extracted_at": record.extracted_at,
                    "hr_adapter_metadata": dict(record.adapter_metadata),
                    "duty_station_map": duty_map.map_id,
                    "location_registry": reg.registry_id,
                },
            )
        )

    return LocPathAssignmentPlan(
        map_id=duty_map.map_id,
        registry_id=reg.registry_id,
        assignments=tuple(assignments),
        findings=tuple(findings),
    )
