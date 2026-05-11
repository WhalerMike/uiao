"""
src/uiao/governance/config_latitude.py
----------------------------------------
Configuration-Latitude Drift Detector — UIAO_140 §5, WS-A7.

Implements DRIFT-SCHEMA detection for tenant configurations that fall
outside the enumerated latitude table in the controlling SSP.

Per UIAO_140 §5 (line 91): a tenant configuration key not present in the
SSP's latitude table, or whose observed value lies outside the table's
allowed set / pattern, produces a DRIFT-SCHEMA finding at severity P2.

References
----------
- UIAO_140 §5
- ADR-054 (Single-ATO Reciprocity Model)
- ADR-058 (HRIT Productization Mission)
- docs/docs/16_DriftDetectionStandard.qmd §2 (DRIFT-SCHEMA definition)
"""

from __future__ import annotations

import re
import uuid
from typing import Literal

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Data models — SSP latitude table side
# ---------------------------------------------------------------------------


class LatitudeTableEntry(BaseModel):
    """One row in the SSP-side configuration latitude table.

    Either ``allowed_values`` or ``allowed_pattern`` may constrain the
    tenant's election.  Both may be None, meaning any value is permitted
    for this key (the key must still appear in the table to avoid a
    NOT_ENUMERATED finding).
    """

    setting_key: str
    allowed_values: list[str] | None = None
    """Explicit whitelist of allowed values.  None = no list constraint."""

    allowed_pattern: str | None = None
    """Regex pattern the observed value must fully match.  None = no pattern constraint."""

    notes: str | None = None


class SspLatitudeTable(BaseModel):
    """The configuration latitude table extracted from the controlling SSP."""

    controlling_ato_id: str
    entries: list[LatitudeTableEntry]


# ---------------------------------------------------------------------------
# Data models — tenant configuration side
# ---------------------------------------------------------------------------


class TenantConfigEntry(BaseModel):
    """One observed configuration key/value pair from the consuming agency."""

    setting_key: str
    observed_value: str


class TenantConfig(BaseModel):
    """All observed configuration for a single consuming agency."""

    consuming_agency_code: str
    entries: list[TenantConfigEntry]


# ---------------------------------------------------------------------------
# Finding model
# ---------------------------------------------------------------------------

VerdictType = Literal["WITHIN_LATITUDE", "OUT_OF_LATITUDE", "NOT_ENUMERATED"]
SeverityType = Literal["P1", "P2", "P3", "P4"]


class LatitudeFinding(BaseModel):
    """A single configuration-latitude drift finding.

    Only OUT_OF_LATITUDE and NOT_ENUMERATED verdicts are emitted;
    WITHIN_LATITUDE items are dropped from the result list.
    """

    setting_key: str
    observed_value: str
    verdict: VerdictType
    severity: SeverityType | None
    drift_class: Literal["DRIFT-SCHEMA"] = "DRIFT-SCHEMA"
    message: str


# ---------------------------------------------------------------------------
# Core detector
# ---------------------------------------------------------------------------


def detect_latitude_drift(
    ssp_table: SspLatitudeTable,
    tenant_config: TenantConfig,
) -> list[LatitudeFinding]:
    """Detect configuration-latitude drift between a controlling SSP's latitude
    table and a consuming agency's observed configuration.

    Rules (UIAO_140 §5):
    1. If a tenant setting_key has no entry in the SSP latitude table:
       emit NOT_ENUMERATED finding, severity P2, drift_class DRIFT-SCHEMA.
    2. If the key is found and ``allowed_values`` is set:
       check membership — if not in list, emit OUT_OF_LATITUDE, severity P2.
    3. If the key is found and ``allowed_pattern`` is set:
       check full-string regex match — if no match, emit OUT_OF_LATITUDE, P2.
    4. Otherwise (key found, no constraint violated): WITHIN_LATITUDE — not
       emitted.

    Returns a list of findings, excluding WITHIN_LATITUDE results.
    """
    # Build lookup index from the SSP table for O(1) key resolution.
    index: dict[str, LatitudeTableEntry] = {e.setting_key: e for e in ssp_table.entries}

    findings: list[LatitudeFinding] = []

    for entry in tenant_config.entries:
        key = entry.setting_key
        value = entry.observed_value

        if key not in index:
            # Rule 1: setting key absent from latitude table → NOT_ENUMERATED
            findings.append(
                LatitudeFinding(
                    setting_key=key,
                    observed_value=value,
                    verdict="NOT_ENUMERATED",
                    severity="P2",
                    drift_class="DRIFT-SCHEMA",
                    message=(
                        f"setting '{key}' is not enumerated in the SSP latitude table "
                        f"for controlling ATO '{ssp_table.controlling_ato_id}' "
                        f"(UIAO_140 §5)"
                    ),
                )
            )
            continue

        lat_entry = index[key]
        violated = False
        reason = ""

        # Rule 2: allowed_values constraint
        if lat_entry.allowed_values is not None:
            if value not in lat_entry.allowed_values:
                violated = True
                reason = f"value '{value}' is not in the allowed set {lat_entry.allowed_values!r} for setting '{key}'"

        # Rule 3: allowed_pattern constraint (applied if no list violation detected)
        if not violated and lat_entry.allowed_pattern is not None:
            if not re.fullmatch(lat_entry.allowed_pattern, value):
                violated = True
                reason = (
                    f"value '{value}' does not match allowed pattern '{lat_entry.allowed_pattern}' for setting '{key}'"
                )

        if violated:
            findings.append(
                LatitudeFinding(
                    setting_key=key,
                    observed_value=value,
                    verdict="OUT_OF_LATITUDE",
                    severity="P2",
                    drift_class="DRIFT-SCHEMA",
                    message=reason,
                )
            )
        # Rule 4: WITHIN_LATITUDE — emit nothing

    return findings


# ---------------------------------------------------------------------------
# OSCAL observation projection
# ---------------------------------------------------------------------------


def findings_to_oscal_observations(
    findings: list[LatitudeFinding],
    consuming_agency_code: str,
) -> list[dict]:
    """Convert a list of LatitudeFinding objects into OSCAL observation skeletons.

    Each observation contains the required OSCAL observation fields:
    ``uuid``, ``title``, ``description``, plus UIAO-specific extensions.

    The UUIDs are generated fresh per call; callers that need stable UUIDs
    should persist the returned observations or supply deterministic IDs
    via post-processing.

    References: NIST SP 800-53A Rev 5 OSCAL observation schema.
    """
    observations: list[dict] = []
    for finding in findings:
        obs_uuid = str(uuid.uuid4())
        observations.append(
            {
                "uuid": obs_uuid,
                "title": (f"Configuration-Latitude {finding.verdict}: {finding.setting_key}"),
                "description": finding.message,
                # UIAO extensions — downstream tools use these for routing
                "props": [
                    {"name": "consuming-agency-code", "value": consuming_agency_code},
                    {"name": "setting-key", "value": finding.setting_key},
                    {"name": "observed-value", "value": finding.observed_value},
                    {"name": "verdict", "value": finding.verdict},
                    {"name": "severity", "value": finding.severity or ""},
                    {"name": "drift-class", "value": finding.drift_class},
                    {"name": "tag", "value": "configuration-latitude"},
                ],
                "methods": ["EXAMINE"],
                "subjects": [
                    {
                        "subject-uuid": consuming_agency_code,
                        "type": "component",
                        "title": f"Consuming agency: {consuming_agency_code}",
                    }
                ],
                "relevant-evidence": [
                    {
                        "description": (
                            "UIAO_140 §5 — DRIFT-SCHEMA when tenant configuration is not in SSP latitude table"
                        )
                    }
                ],
            }
        )
    return observations


__all__ = [
    "LatitudeFinding",
    "LatitudeTableEntry",
    "SspLatitudeTable",
    "TenantConfig",
    "TenantConfigEntry",
    "detect_latitude_drift",
    "findings_to_oscal_observations",
]
