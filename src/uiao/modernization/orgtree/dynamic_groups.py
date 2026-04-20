"""Dynamic group library loader (MOD_B, ADR-036).

Loads ``src/uiao/canon/data/orgpath/dynamic-groups.yaml`` and exposes a
:class:`DynamicGroupLibrary` object that the entra-dynamic-groups adapter
consumes to reconcile the tenant against the canon.

The loader:

* validates the YAML against ``schemas/orgpath/dynamic-groups.schema.json``;
* enforces that every OrgPath referenced by a group rule exists in the
  active codebook (MOD_A / ADR-035) — a reference to an unknown or
  deprecated code is caught at load, so the drift engine never emits a
  provisioning plan against a broken dependency;
* exposes lookup helpers (``get``, ``names``, ``by_category``,
  ``referenced_codes``).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Set

import yaml

from .codebook import Codebook, default_codebook


class DynamicGroupValidationError(ValueError):
    """Raised when the dynamic-group library fails schema or integrity validation."""


@dataclass(frozen=True)
class DynamicGroupSpec:
    """A single canonical dynamic group definition."""

    name: str
    category: str
    rule: str
    orgpath_refs: tuple[str, ...]
    description: str

    def to_graph_body(self) -> Dict[str, object]:
        """Return a POST /groups request body ready for Microsoft Graph.

        Uses the attribute shape documented at
        https://learn.microsoft.com/graph/api/group-post-groups — dynamic
        membership requires ``groupTypes: ["DynamicMembership"]`` plus
        ``membershipRule`` and ``membershipRuleProcessingState``.
        """
        return {
            "displayName": self.name,
            "mailEnabled": False,
            "mailNickname": self.name.lower(),
            "securityEnabled": True,
            "groupTypes": ["DynamicMembership"],
            "membershipRule": self.rule,
            "membershipRuleProcessingState": "On",
            "description": self.description,
        }


@dataclass(frozen=True)
class DynamicGroupLibrary:
    """In-memory view of the dynamic-group library."""

    schema_version: str
    document_id: str
    parent_canon: str
    naming_regex: str
    purpose_suffixes: tuple[str, ...]
    groups: Mapping[str, DynamicGroupSpec]

    @property
    def names(self) -> Set[str]:
        return set(self.groups.keys())

    def get(self, name: str) -> Optional[DynamicGroupSpec]:
        return self.groups.get(name)

    def by_category(self, category: str) -> List[DynamicGroupSpec]:
        return [g for g in self.groups.values() if g.category == category]

    def referenced_codes(self) -> Set[str]:
        """Union of every OrgPath code referenced across the library."""
        return {code for g in self.groups.values() for code in g.orgpath_refs}

    def matches_naming(self, candidate: str) -> bool:
        """True iff ``candidate`` matches the library naming regex."""
        return bool(re.match(self.naming_regex, candidate))


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

_DEFAULT_LIBRARY_RESOURCE = ("uiao.canon.data.orgpath", "dynamic-groups.yaml")
_DEFAULT_SCHEMA_RESOURCE = ("uiao.schemas.orgpath", "dynamic-groups.schema.json")


def _read_default_library() -> str:
    package, name = _DEFAULT_LIBRARY_RESOURCE
    return resources.files(package).joinpath(name).read_text(encoding="utf-8")


def _read_default_schema() -> Dict:
    package, name = _DEFAULT_SCHEMA_RESOURCE
    return json.loads(resources.files(package).joinpath(name).read_text(encoding="utf-8"))


def _validate_schema(document: Dict) -> None:
    try:
        import jsonschema
    except ImportError as exc:  # pragma: no cover - jsonschema is a declared dep
        raise DynamicGroupValidationError(
            "jsonschema is required to validate the dynamic-group library"
        ) from exc
    schema = _read_default_schema()
    try:
        jsonschema.validate(instance=document, schema=schema)
    except jsonschema.ValidationError as exc:
        raise DynamicGroupValidationError(
            f"Dynamic-group library schema validation failed: {exc.message} at "
            f"{'/'.join(str(p) for p in exc.absolute_path)}"
        ) from exc


def _validate_integrity(document: Dict, codebook: Codebook) -> None:
    """Enforce cross-canon integrity not expressible in JSON Schema.

    * Every OrgPath referenced by a group must be active in the codebook.
    * Every group rule must literally contain each of its declared refs
      (prevents drift between the structured ``orgpath_refs`` list and
      the opaque ``rule`` string a Graph API call sends).
    * Group names must be unique.
    """
    seen_names: Set[str] = set()
    for group in document["groups"]:
        name = group["name"]
        if name in seen_names:
            raise DynamicGroupValidationError(f"Duplicate group name: {name}")
        seen_names.add(name)

        for code in group["orgpath_refs"]:
            if codebook.is_deprecated(code):
                raise DynamicGroupValidationError(
                    f"Group '{name}' references deprecated OrgPath '{code}' "
                    f"(replaced by '{codebook.replacement_for(code)}')"
                )
            if not codebook.is_active(code):
                raise DynamicGroupValidationError(
                    f"Group '{name}' references unknown OrgPath '{code}' "
                    "— codebook (MOD_A) does not contain this entry"
                )

        rule = group["rule"]
        for code in group["orgpath_refs"]:
            if f'"{code}"' not in rule:
                raise DynamicGroupValidationError(
                    f"Group '{name}' declares orgpath_refs={group['orgpath_refs']} "
                    f"but its membership rule does not quote '{code}' — "
                    "structured refs and rule must agree"
                )


def _build(document: Dict) -> DynamicGroupLibrary:
    groups = {
        g["name"]: DynamicGroupSpec(
            name=g["name"],
            category=g["category"],
            rule=g["rule"],
            orgpath_refs=tuple(g["orgpath_refs"]),
            description=g["description"],
        )
        for g in document["groups"]
    }
    naming = document["naming"]
    return DynamicGroupLibrary(
        schema_version=document["schema_version"],
        document_id=document["document_id"],
        parent_canon=document["parent_canon"],
        naming_regex=naming["regex"],
        purpose_suffixes=tuple(naming["purpose_suffixes"]),
        groups=groups,
    )


def load_dynamic_group_library(
    path: Optional[Path] = None,
    codebook: Optional[Codebook] = None,
) -> DynamicGroupLibrary:
    """Load and validate the dynamic-group library.

    Parameters
    ----------
    path:
        Optional override pointing at an alternate YAML file (used in tests).
    codebook:
        Optional codebook override. Defaults to the canonical codebook
        loaded by :func:`uiao.modernization.orgtree.codebook.default_codebook`.
    """
    if path is None:
        raw_text = _read_default_library()
    else:
        raw_text = Path(path).read_text(encoding="utf-8")
    document = yaml.safe_load(raw_text)
    if not isinstance(document, dict):
        raise DynamicGroupValidationError(
            "Dynamic-group library must be a YAML mapping at the top level"
        )
    _validate_schema(document)
    _validate_integrity(document, codebook or default_codebook())
    return _build(document)


@lru_cache(maxsize=1)
def default_dynamic_group_library() -> DynamicGroupLibrary:
    """Return the cached canonical library (no path override)."""
    return load_dynamic_group_library()
