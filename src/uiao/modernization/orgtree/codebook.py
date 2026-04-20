"""OrgPath codebook loader.

Loads ``src/uiao/canon/data/orgpath/codebook.yaml`` (the executable canon
bound to MOD_A by ADR-035) and exposes a :class:`Codebook` object the drift
engine and the Entra/AD adapters consume.

The loader:

* validates the YAML structure against
  ``src/uiao/schemas/orgpath/codebook.schema.json``;
* validates that every ``code`` matches the canonical regex;
* validates that every non-root ``parent`` exists in ``codes`` (hierarchy
  integrity — prevents *Hierarchy Drift* at the source);
* exposes helpers (``is_active``, ``is_deprecated``, ``parent_of``,
  ``replacement_for``) so the drift engine can emit the five drift classes
  MOD_A §Drift describes without re-parsing the YAML.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Dict, Iterable, Mapping, Optional, Set

import yaml


CANONICAL_REGEX = re.compile(r"^ORG(-[A-Z0-9]{2,6}){0,4}$")


class CodebookValidationError(ValueError):
    """Raised when the codebook YAML fails schema or integrity validation."""


@dataclass(frozen=True)
class CodebookEntry:
    code: str
    level: int
    description: str
    parent: Optional[str]


@dataclass(frozen=True)
class DeprecatedEntry:
    code: str
    replaced_by: str
    deprecated_at: Optional[str] = None
    reason: Optional[str] = None


@dataclass(frozen=True)
class Codebook:
    """In-memory view of the OrgPath codebook."""

    schema_version: str
    document_id: str
    parent_canon: str
    regex: str
    max_depth: int
    entries: Mapping[str, CodebookEntry]
    deprecated: Mapping[str, DeprecatedEntry] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Convenience accessors used by the drift engine + adapters
    # ------------------------------------------------------------------
    @property
    def codes(self) -> Set[str]:
        """Set of active OrgPath codes."""
        return set(self.entries.keys())

    @property
    def deprecated_codes(self) -> Set[str]:
        return set(self.deprecated.keys())

    def is_active(self, code: str) -> bool:
        return code in self.entries

    def is_deprecated(self, code: str) -> bool:
        return code in self.deprecated

    def parent_of(self, code: str) -> Optional[str]:
        entry = self.entries.get(code)
        return entry.parent if entry else None

    def replacement_for(self, code: str) -> Optional[str]:
        dep = self.deprecated.get(code)
        return dep.replaced_by if dep else None

    def has_format(self, code: str) -> bool:
        """True iff ``code`` matches the canonical format regex."""
        return bool(CANONICAL_REGEX.match(code))


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

_DEFAULT_CODEBOOK_RESOURCE = ("uiao.canon.data.orgpath", "codebook.yaml")
_DEFAULT_SCHEMA_RESOURCE = ("uiao.schemas.orgpath", "codebook.schema.json")


def _read_default_codebook() -> str:
    package, name = _DEFAULT_CODEBOOK_RESOURCE
    return resources.files(package).joinpath(name).read_text(encoding="utf-8")


def _read_default_schema() -> Dict:
    package, name = _DEFAULT_SCHEMA_RESOURCE
    return json.loads(resources.files(package).joinpath(name).read_text(encoding="utf-8"))


def _validate_schema(document: Dict) -> None:
    try:
        import jsonschema
    except ImportError as exc:  # pragma: no cover - jsonschema is a declared dep
        raise CodebookValidationError(
            "jsonschema is required to validate the OrgPath codebook"
        ) from exc
    schema = _read_default_schema()
    try:
        jsonschema.validate(instance=document, schema=schema)
    except jsonschema.ValidationError as exc:
        raise CodebookValidationError(
            f"OrgPath codebook schema validation failed: {exc.message} at "
            f"{'/'.join(str(p) for p in exc.absolute_path)}"
        ) from exc


def _validate_integrity(document: Dict) -> None:
    """Enforce referential integrity not expressible in JSON Schema."""
    codes = {c["code"] for c in document["codes"]}
    for entry in document["codes"]:
        parent = entry.get("parent")
        if parent is None:
            if entry["code"] != document["format"]["root"]:
                raise CodebookValidationError(
                    f"Code '{entry['code']}' has null parent but is not the root "
                    f"'{document['format']['root']}'"
                )
            continue
        if parent not in codes:
            raise CodebookValidationError(
                f"Code '{entry['code']}' references unknown parent '{parent}' "
                "(Hierarchy Drift at the source — codebook integrity violation)"
            )
        if not entry["code"].startswith(f"{parent}{document['format']['separator']}"):
            raise CodebookValidationError(
                f"Code '{entry['code']}' does not descend from declared parent "
                f"'{parent}' under the canonical separator"
            )
    # Every deprecated replacement must resolve to an active code.
    for dep in document.get("deprecated", []) or []:
        if dep["replaced_by"] not in codes:
            raise CodebookValidationError(
                f"Deprecated code '{dep['code']}' replaced_by "
                f"'{dep['replaced_by']}' which is not an active code"
            )


def _build(document: Dict) -> Codebook:
    entries = {
        c["code"]: CodebookEntry(
            code=c["code"],
            level=c["level"],
            description=c["description"],
            parent=c.get("parent"),
        )
        for c in document["codes"]
    }
    deprecated = {
        d["code"]: DeprecatedEntry(
            code=d["code"],
            replaced_by=d["replaced_by"],
            deprecated_at=d.get("deprecated_at"),
            reason=d.get("reason"),
        )
        for d in (document.get("deprecated") or [])
    }
    return Codebook(
        schema_version=document["schema_version"],
        document_id=document["document_id"],
        parent_canon=document["parent_canon"],
        regex=document["format"]["regex"],
        max_depth=document["format"]["max_depth"],
        entries=entries,
        deprecated=deprecated,
    )


def load_codebook(path: Optional[Path] = None) -> Codebook:
    """Load and validate the OrgPath codebook.

    Parameters
    ----------
    path:
        Optional override pointing at an alternate YAML file (typically used
        in tests). When omitted, the canonical codebook shipped inside the
        ``uiao.canon`` package is loaded via ``importlib.resources``.
    """
    if path is None:
        raw_text = _read_default_codebook()
    else:
        raw_text = Path(path).read_text(encoding="utf-8")
    document = yaml.safe_load(raw_text)
    if not isinstance(document, dict):
        raise CodebookValidationError("Codebook must be a YAML mapping at the top level")
    _validate_schema(document)
    _validate_integrity(document)
    return _build(document)


@lru_cache(maxsize=1)
def default_codebook() -> Codebook:
    """Return the cached canonical codebook (no path override)."""
    return load_codebook()


def active_codes(codebook: Optional[Codebook] = None) -> Set[str]:
    """Return the set of currently active OrgPath codes."""
    return (codebook or default_codebook()).codes
