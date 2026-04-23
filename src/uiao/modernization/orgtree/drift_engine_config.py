"""Drift engine configuration loader (MOD_M, ADR-040).

Loads ``src/uiao/canon/data/orgpath/drift-engine-config.yaml`` and exposes a
:class:`DriftEngineConfig` the :class:`OrgTreeDriftEngine` consumes to
drive its six-phase loop (Snapshot → Compare → Classify → Alert →
Remediate → Verify).

The loader enforces structural + schema validity and uniqueness on phase
names, but does **not** import the phase adapters — that stays lazy on
the engine side so a partial tenant environment (e.g., Phase 5 disabled)
can still run the engine against the subset it has.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Dict, Mapping, Optional, Set, Tuple

import yaml


class DriftEngineConfigValidationError(ValueError):
    """Raised when the drift engine config fails schema validation."""


@dataclass(frozen=True)
class OpEntry:
    op: str
    drift_class: str
    severity: str
    auto_remediate: bool


@dataclass(frozen=True)
class PhaseConfig:
    name: str
    adapter_module: str
    adapter_class: str
    op_map: Mapping[str, OpEntry]

    def entry_for(self, op: str) -> Optional[OpEntry]:
        return self.op_map.get(op)


@dataclass(frozen=True)
class DriftEngineDefaults:
    dry_run: bool
    severity_floor: str
    halt_on_critical: bool


@dataclass(frozen=True)
class SeverityPolicy:
    labels: Mapping[str, str]
    halt_at: str


@dataclass(frozen=True)
class DriftEngineConfig:
    schema_version: str
    document_id: str
    parent_canon: str
    defaults: DriftEngineDefaults
    phases: Tuple[PhaseConfig, ...]
    severity_policy: SeverityPolicy

    @property
    def phase_names(self) -> Set[str]:
        return {p.name for p in self.phases}

    def phase(self, name: str) -> Optional[PhaseConfig]:
        return next((p for p in self.phases if p.name == name), None)


_DEFAULT_CONFIG_RESOURCE = ("uiao.canon.data.orgpath", "drift-engine-config.yaml")
_DEFAULT_SCHEMA_RESOURCE = ("uiao.schemas.orgpath", "drift-engine-config.schema.json")


def _read_default_config() -> str:
    package, name = _DEFAULT_CONFIG_RESOURCE
    return resources.files(package).joinpath(name).read_text(encoding="utf-8")


def _read_default_schema() -> Dict:
    package, name = _DEFAULT_SCHEMA_RESOURCE
    return json.loads(resources.files(package).joinpath(name).read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _validate_schema(document: Dict) -> None:
    try:
        import jsonschema
    except ImportError as exc:  # pragma: no cover
        raise DriftEngineConfigValidationError("jsonschema is required to validate the drift engine config") from exc
    schema = _read_default_schema()
    try:
        jsonschema.validate(instance=document, schema=schema)
    except jsonschema.ValidationError as exc:
        raise DriftEngineConfigValidationError(
            f"drift-engine-config schema validation failed: {exc.message} "
            f"at {'/'.join(str(p) for p in exc.absolute_path)}"
        ) from exc


def _validate_integrity(document: Dict) -> None:
    phase_names: Set[str] = set()
    for phase in document["phases"]:
        if phase["name"] in phase_names:
            raise DriftEngineConfigValidationError(f"Duplicate phase name: {phase['name']}")
        phase_names.add(phase["name"])

        op_names: Set[str] = set()
        for entry in phase["op_map"]:
            if entry["op"] in op_names:
                raise DriftEngineConfigValidationError(f"Phase {phase['name']}: duplicate op '{entry['op']}'")
            op_names.add(entry["op"])


def _build(document: Dict) -> DriftEngineConfig:
    phases = tuple(
        PhaseConfig(
            name=p["name"],
            adapter_module=p["adapter_module"],
            adapter_class=p["adapter_class"],
            op_map={
                e["op"]: OpEntry(
                    op=e["op"],
                    drift_class=e["drift_class"],
                    severity=e["severity"],
                    auto_remediate=e["auto_remediate"],
                )
                for e in p["op_map"]
            },
        )
        for p in document["phases"]
    )
    defaults = DriftEngineDefaults(
        dry_run=document["defaults"]["dry_run"],
        severity_floor=document["defaults"]["severity_floor"],
        halt_on_critical=document["defaults"]["halt_on_critical"],
    )
    sp = document["severity_policy"]
    severity_policy = SeverityPolicy(
        labels={k: sp[k] for k in ("P1", "P2", "P3", "P4")},
        halt_at=sp["halt_at"],
    )
    return DriftEngineConfig(
        schema_version=document["schema_version"],
        document_id=document["document_id"],
        parent_canon=document["parent_canon"],
        defaults=defaults,
        phases=phases,
        severity_policy=severity_policy,
    )


def load_drift_engine_config(path: Optional[Path] = None) -> DriftEngineConfig:
    """Load and validate the drift engine configuration."""
    raw_text = _read_default_config() if path is None else Path(path).read_text(encoding="utf-8")
    document = yaml.safe_load(raw_text)
    if not isinstance(document, dict):
        raise DriftEngineConfigValidationError("drift-engine-config must be a YAML mapping at the top level")
    _validate_schema(document)
    _validate_integrity(document)
    return _build(document)


@lru_cache(maxsize=1)
def default_drift_engine_config() -> DriftEngineConfig:
    return load_drift_engine_config()
