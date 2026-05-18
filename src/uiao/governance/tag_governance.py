"""
src/uiao/governance/tag_governance.py
-------------------------------------
Canonical tag governance per UIAO_177.

Defines the canonical `uiao.*` tag namespace, the validation policy for
canonical vs. non-canonical keys, and the drift-mapping rule that turns
tag deltas into `DriftRecord` instances on the UIAO_179 schema.

The source of truth for each canonical tag is documented in UIAO_177
§Canonical tag namespace. `uiao.org.path` is derived from Entra
`extensionAttribute1` (UIAO_151); UIAO does not dual-write that value.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional

from uiao.governance.drift_output import DriftRecord

# Canonical boundary enum, sourced from UIAO substrate-manifest (ADR-033,
# ADR-059). The bare strings are encoded here to avoid a runtime
# dependency on the manifest loader from inside the tag validator.
CANONICAL_BOUNDARY_VALUES = frozenset(
    {
        "GCC-Moderate",
        "GCC-Moderate-Exception:AmazonConnect",
        "GCC-Moderate-Exception:SailPointNERM",
    }
)

CANONICAL_LIFECYCLE_VALUES = frozenset({"active", "leave", "disabled"})


class CanonicalTagKey(str, Enum):
    """The four canonical `uiao.*` tag keys defined by UIAO_177."""

    ORG_PATH = "uiao.org.path"
    IDENTITY_LIFECYCLE = "uiao.identity.lifecycle"
    OWNER = "uiao.owner"
    BOUNDARY = "uiao.boundary"


CANONICAL_KEYS = frozenset(k.value for k in CanonicalTagKey)

# Keys in the `uiao.*` namespace that are reserved-but-forbidden. The
# bare `uiao.lifecycle` collides with UIAO_169's artifact lifecycle and
# is explicitly forbidden so emitters use `uiao.identity.lifecycle`
# instead (UIAO_177 §Canonical tag namespace).
FORBIDDEN_KEYS = frozenset({"uiao.lifecycle"})


@dataclass
class CanonicalTagState:
    """Computed canonical state for an object's `uiao.*` tags.

    `tags` holds the values the object SHOULD carry, derived from the
    sources of truth documented in UIAO_177. Missing keys mean the
    source of truth did not provide a value.
    """

    object_id: str
    tags: Dict[str, str]


def is_canonical_key(key: str) -> bool:
    """Return True if `key` is a recognised canonical `uiao.*` key."""
    return key in CANONICAL_KEYS


def is_forbidden_key(key: str) -> bool:
    """Return True if `key` is in the reserved-but-forbidden set."""
    return key in FORBIDDEN_KEYS


def is_non_canonical_key(key: str) -> bool:
    """Return True if `key` is permitted but outside the canonical namespace."""
    return not is_canonical_key(key) and not is_forbidden_key(key)


def validate_canonical_value(key: str, value: Any) -> Optional[str]:
    """Return an error string if `value` is invalid for canonical `key`, else None."""
    if key == CanonicalTagKey.IDENTITY_LIFECYCLE.value:
        if value not in CANONICAL_LIFECYCLE_VALUES:
            return f"{key} must be one of {sorted(CANONICAL_LIFECYCLE_VALUES)}"
    elif key == CanonicalTagKey.BOUNDARY.value:
        if value not in CANONICAL_BOUNDARY_VALUES:
            return f"{key} must be one of {sorted(CANONICAL_BOUNDARY_VALUES)}"
    elif key in (CanonicalTagKey.ORG_PATH.value, CanonicalTagKey.OWNER.value):
        if not isinstance(value, str) or not value:
            return f"{key} must be a non-empty string"
    return None


def compute_tag_drift(
    object_id: str,
    *,
    desired: Mapping[str, str],
    actual: Mapping[str, str],
    source_adapter: str,
    correlation_id: Optional[str] = None,
) -> List[DriftRecord]:
    """Compute `DriftRecord`s for canonical tag differences.

    Args:
        object_id: canonical principal or resource ID.
        desired: canonical state computed from sources of truth (a
            `CanonicalTagState.tags` view).
        actual: tags observed on the target object (including non-
            canonical keys).
        source_adapter: identifier of the adapter producing the records.
        correlation_id: optional caller correlation key.

    Returns a list of records mapped per UIAO_177 §Drift mapping. The
    returned list is empty when actual matches desired and no forbidden
    keys are present.
    """
    records: List[DriftRecord] = []

    # 1. Forbidden uiao.* keys present -> DRIFT-SCHEMA
    for key, value in actual.items():
        if is_forbidden_key(key):
            records.append(
                DriftRecord(
                    object_id=object_id,
                    drift_class="DRIFT-SCHEMA",
                    object_facet="tag",
                    expected_value=None,
                    actual_value={key: value},
                    severity="medium",
                    recommended_action="remove-forbidden-key",
                    source_adapter=source_adapter,
                    correlation_id=correlation_id,
                )
            )

    # 2. Canonical keys: missing, mismatched value, or invalid value
    for key, expected in desired.items():
        if not is_canonical_key(key):
            # The desired map should only contain canonical keys; skip
            # anything caller-supplied that isn't.
            continue

        invalid = validate_canonical_value(key, expected)
        if invalid is not None:
            # Bug in the caller's desired-state computation. Emit a
            # SCHEMA finding so it surfaces.
            records.append(
                DriftRecord(
                    object_id=object_id,
                    drift_class="DRIFT-SCHEMA",
                    object_facet="tag",
                    expected_value=expected,
                    actual_value=None,
                    severity="high",
                    recommended_action=f"fix-desired-state: {invalid}",
                    source_adapter=source_adapter,
                    correlation_id=correlation_id,
                )
            )
            continue

        if key not in actual:
            records.append(
                DriftRecord(
                    object_id=object_id,
                    drift_class="DRIFT-SCHEMA",
                    object_facet="tag",
                    expected_value=expected,
                    actual_value=None,
                    severity="medium",
                    recommended_action="overwrite-canonical-tag",
                    source_adapter=source_adapter,
                    correlation_id=correlation_id,
                )
            )
        elif actual[key] != expected:
            drift_class = (
                "DRIFT-BOUNDARY"
                if key == CanonicalTagKey.BOUNDARY.value
                else "DRIFT-SEMANTIC"
            )
            severity = "critical" if drift_class == "DRIFT-BOUNDARY" else "medium"
            records.append(
                DriftRecord(
                    object_id=object_id,
                    drift_class=drift_class,
                    object_facet="tag",
                    expected_value=expected,
                    actual_value=actual[key],
                    severity=severity,
                    recommended_action="overwrite-canonical-tag",
                    source_adapter=source_adapter,
                    correlation_id=correlation_id,
                )
            )

    return records


def split_tags(tags: Mapping[str, str]) -> Dict[str, Dict[str, str]]:
    """Partition a tag map into canonical / non-canonical / forbidden buckets."""
    canonical: Dict[str, str] = {}
    non_canonical: Dict[str, str] = {}
    forbidden: Dict[str, str] = {}
    for key, value in tags.items():
        if is_canonical_key(key):
            canonical[key] = value
        elif is_forbidden_key(key):
            forbidden[key] = value
        else:
            non_canonical[key] = value
    return {
        "canonical": canonical,
        "non_canonical": non_canonical,
        "forbidden": forbidden,
    }
