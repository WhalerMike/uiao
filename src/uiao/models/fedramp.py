"""Pydantic v2 models for FedRAMP 20x KSI evidence, drift, and 3PAO packaging.

Covers the evidence surface described in UIAO_138 and the emission contract
defined in UIAO_133 §2.  These models are the wire format between the KSI
emitter, the drift engine, the OSCAL generator, and the API / CLI layers.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class KsiTheme(str, Enum):
    """Ten KSI themes from the CR26 Moderate catalog (UIAO_137 §2)."""

    CMT = "KSI-CMT"  # Change Management
    CNA = "KSI-CNA"  # Cloud Native Architecture
    CED = "KSI-CED"  # Cybersecurity Education
    IAM = "KSI-IAM"  # Identity and Access Management
    INR = "KSI-INR"  # Incident Response
    MLA = "KSI-MLA"  # Monitoring, Logging, and Auditing
    PIY = "KSI-PIY"  # Policy and Inventory
    RPL = "KSI-RPL"  # Recovery Planning
    SVC = "KSI-SVC"  # Service Configuration
    SCR = "KSI-SCR"  # Supply Chain Risk


ALL_KSI_THEMES: tuple[KsiTheme, ...] = tuple(KsiTheme)

# KSI themes required for GCC-Moderate (full set per UIAO_137 §4)
MODERATE_REQUIRED_THEMES: frozenset[KsiTheme] = frozenset(ALL_KSI_THEMES)


class MasScopeValue(str, Enum):
    """RFC-0005 Minimum Assessment Scope classification values (ADR-106 D2)."""

    IN_SCOPE = "in-scope"
    METADATA_OUT = "metadata-out-of-scope"
    AGENCY_SIDE_OUT = "agency-side-out-of-scope"


class DriftClass(str, Enum):
    """Drift classes emitted by the FedRAMP 20x evidence surface (UIAO_133 §4)."""

    EVIDENCE_STALE = "DRIFT-EVIDENCE-STALE"
    EVIDENCE_STALE_AGGREGATE = "DRIFT-EVIDENCE-STALE-AGGREGATE"
    SCHEMA = "DRIFT-SCHEMA"
    PROVENANCE = "DRIFT-PROVENANCE"


class DriftSeverity(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"


class FreshnessCadence(str, Enum):
    """Freshness cadence values for KSI artifacts (UIAO_133 §2.2)."""

    REAL_TIME_CRITICAL = "real-time-critical"
    DAILY_ROUTINE = "daily-routine"
    ON_PUBLISH = "on-baseline-publish"
    ON_SCUBA = "on-scubagear-cycle"
    ON_WORKFLOW = "on-workflow-event"
    CONTINUOUS = "continuous"
    QUARTERLY = "quarterly"


class FedRampBaseline(str, Enum):
    LOW = "fedramp-low"
    MODERATE = "fedramp-moderate"
    HIGH = "fedramp-high"
    GCC_MODERATE = "gcc-moderate"


# ---------------------------------------------------------------------------
# KSI emission props (UIAO_133 §2.1)
# ---------------------------------------------------------------------------


class KsiEmissionProps(BaseModel):
    """The four required fedramp:ksi-* props injected into every OSCAL artifact."""

    ksi_themes: list[KsiTheme] = Field(
        ...,
        description="KSI themes this artifact backs (fedramp:ksi-themes).",
    )
    ksi_mapping_source: str = Field(
        ...,
        description="Canon row authorising this mapping, e.g. 'UIAO_022 §13.3 TBL-P2-011 row 2'.",
    )
    ksi_freshness_cadence: FreshnessCadence = Field(
        ...,
        description="Cadence budget for freshness staleness checks.",
    )
    ksi_emitted_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="ISO-8601 timestamp of artifact generation.",
    )

    model_config = ConfigDict(extra="forbid")

    def to_oscal_props(self) -> list[dict[str, str]]:
        """Serialise to the OSCAL props array format."""
        ns = "https://fedramp.gov/ns/oscal"
        return [
            {
                "name": "fedramp:ksi-themes",
                "ns": ns,
                "value": ",".join(t.value for t in self.ksi_themes),
            },
            {
                "name": "fedramp:ksi-mapping-source",
                "ns": ns,
                "value": self.ksi_mapping_source,
            },
            {
                "name": "fedramp:ksi-freshness-cadence",
                "ns": ns,
                "value": self.ksi_freshness_cadence.value,
            },
            {
                "name": "fedramp:ksi-emitted-at",
                "ns": ns,
                "value": self.ksi_emitted_at.isoformat(),
            },
        ]


# ---------------------------------------------------------------------------
# KSI evidence record (persisted in the evidence store)
# ---------------------------------------------------------------------------


class KsiEvidenceRecord(BaseModel):
    """A KSI evidence record in the OSCAL artifact store."""

    uuid: str = Field(..., description="Deterministic UUID5 of this record.")
    artifact_row: int = Field(
        ...,
        ge=1,
        le=11,
        description="Row number from UIAO_133 §2.2 emission map (1-11).",
    )
    responsible_component: str = Field(
        ...,
        description="Substrate component that emitted this record (e.g. 'drift.engine.realtime').",
    )
    oscal_element: str = Field(
        ...,
        description="OSCAL element type (e.g. 'assessment-results/finding').",
    )
    emission_props: KsiEmissionProps
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="OSCAL artifact payload (the full element body).",
    )
    is_stale: bool = Field(default=False)
    staleness_age_seconds: float | None = Field(default=None)

    model_config = ConfigDict(extra="allow")


# ---------------------------------------------------------------------------
# Drift events
# ---------------------------------------------------------------------------


class KsiDriftEvent(BaseModel):
    """A drift event emitted by the FedRAMP 20x evidence surface."""

    event_id: str = Field(..., description="UUID of this event.")
    drift_class: DriftClass
    severity: DriftSeverity
    subject: str = Field(..., description="Responsible component from UIAO_133 §2.2.")
    expected_cadence: FreshnessCadence | None = None
    actual_age_seconds: float | None = None
    ksi_themes: list[KsiTheme] = Field(default_factory=list)
    detail: str = Field(default="", description="Human-readable description.")
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    remediated_at: datetime | None = None

    model_config = ConfigDict(extra="allow")

    @property
    def is_open(self) -> bool:
        return self.remediated_at is None


# ---------------------------------------------------------------------------
# MAS scope classification
# ---------------------------------------------------------------------------


class MasScopeClassification(BaseModel):
    """RFC-0005 MAS scope classification for a substrate component."""

    component_path: str = Field(..., description="Path to the canon document.")
    component_id: str = Field(default="", description="UIAO_NNN identifier if applicable.")
    mas_scope: MasScopeValue
    justification: str = Field(
        ...,
        description="Written justification citing the specific data the component touches.",
    )
    classified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    classified_by: str = Field(default="canon-steward")
    dispute_open: bool = Field(default=False)
    dispute_detail: str = Field(default="")

    model_config = ConfigDict(extra="allow")


# ---------------------------------------------------------------------------
# Dry-run result (ADR-106 ratification gate 3)
# ---------------------------------------------------------------------------


class KsiThemeCoverage(BaseModel):
    theme: KsiTheme
    artifact_count: int
    is_stale: bool
    oldest_artifact_age_seconds: float | None = None


class DryRunResult(BaseModel):
    """Result of an ADR-106 ratification gate 3 dry-run execution."""

    run_id: str = Field(..., description="UUID of this dry-run.")
    baseline: FedRampBaseline = FedRampBaseline.GCC_MODERATE
    cr26_snapshot_sha: str = Field(default="", description="Pinned CR26 snapshot SHA used.")
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Per-criterion results (UIAO_138 §7.2)
    criterion_1_all_themes_present: bool = False
    criterion_2_no_stale_artifacts: bool = False
    criterion_3_cato_covers_all_themes: bool = False
    passed: bool = False

    theme_coverage: list[KsiThemeCoverage] = Field(default_factory=list)
    p0_events: list[KsiDriftEvent] = Field(default_factory=list)
    p1_events: list[KsiDriftEvent] = Field(default_factory=list)
    missing_themes: list[KsiTheme] = Field(default_factory=list)

    notes: str = Field(default="")

    model_config = ConfigDict(extra="allow")

    def summary(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "passed": self.passed,
            "baseline": self.baseline.value,
            "criteria": {
                "1_all_themes_present": self.criterion_1_all_themes_present,
                "2_no_stale_artifacts": self.criterion_2_no_stale_artifacts,
                "3_cato_covers_all_themes": self.criterion_3_cato_covers_all_themes,
            },
            "missing_themes": [t.value for t in self.missing_themes],
            "p0_count": len(self.p0_events),
            "p1_count": len(self.p1_events),
            "theme_coverage": {c.theme.value: c.artifact_count for c in self.theme_coverage},
        }


# ---------------------------------------------------------------------------
# 3PAO evidence package (UIAO_138 §2)
# ---------------------------------------------------------------------------


class ThreePaoEvidenceArtifactEntry(BaseModel):
    artifact_row: int
    artifact_type: str
    oscal_element: str
    ksi_themes: list[KsiTheme]
    cadence: FreshnessCadence
    responsible_component: str
    is_present: bool
    is_stale: bool
    latest_record_uuid: str | None = None
    latest_emitted_at: datetime | None = None


class ThreePaoPackage(BaseModel):
    """A 3PAO evidence package produced per UIAO_138 §2 and §5."""

    package_id: str = Field(..., description="UUID of this package.")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    baseline: FedRampBaseline = FedRampBaseline.GCC_MODERATE
    cr26_snapshot_sha: str = Field(default="")

    # Artifact index (§2 of UIAO_138)
    artifact_entries: list[ThreePaoEvidenceArtifactEntry] = Field(default_factory=list)

    # Compliance state (§5.1)
    all_artifacts_present: bool = False
    all_props_valid: bool = False
    all_mappings_resolve: bool = False
    no_stale_artifacts: bool = False
    cato_covers_all_themes: bool = False
    compliant: bool = False

    # Open drift events
    open_drift_events: list[KsiDriftEvent] = Field(default_factory=list)

    # MAS scope classifications
    mas_classifications: list[MasScopeClassification] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")

    def compliance_summary(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "compliant": self.compliant,
            "checks": {
                "all_artifacts_present": self.all_artifacts_present,
                "all_props_valid": self.all_props_valid,
                "all_mappings_resolve": self.all_mappings_resolve,
                "no_stale_artifacts": self.no_stale_artifacts,
                "cato_covers_all_themes": self.cato_covers_all_themes,
            },
            "open_p0": sum(1 for e in self.open_drift_events if e.severity == DriftSeverity.P0),
            "open_p1": sum(1 for e in self.open_drift_events if e.severity == DriftSeverity.P1),
            "open_p2": sum(1 for e in self.open_drift_events if e.severity == DriftSeverity.P2),
            "artifact_count": len(self.artifact_entries),
            "mas_in_scope": sum(1 for c in self.mas_classifications if c.mas_scope == MasScopeValue.IN_SCOPE),
            "mas_out_of_scope": sum(1 for c in self.mas_classifications if c.mas_scope != MasScopeValue.IN_SCOPE),
        }
