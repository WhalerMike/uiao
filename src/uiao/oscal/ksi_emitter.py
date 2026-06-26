"""KSI emission tagging for OSCAL artifacts.

Implements UIAO_133 §2 — injects ``fedramp:ksi-*`` props into OSCAL artifact
dicts at generation time.  No separate evidence pipeline is created; the four
props ride on the existing OSCAL artifact envelope (ADR-106 D1).

Usage::

    from uiao.oscal.ksi_emitter import tag_artifact, EMISSION_MAP

    artifact = {"uuid": "...", "title": "...", ...}
    tagged = tag_artifact(artifact, row=2)  # row from UIAO_133 §2.2
"""

from __future__ import annotations

import uuid as _uuid_mod
from datetime import datetime, timezone
from typing import Any

from ..models.fedramp import (
    DriftClass,
    DriftSeverity,
    FreshnessCadence,
    KsiDriftEvent,
    KsiEmissionProps,
    KsiEvidenceRecord,
    KsiTheme,
)

# ---------------------------------------------------------------------------
# Emission map — UIAO_133 §2.2
# Each entry is: (row, oscal_element, responsible_component, ksi_themes, cadence)
# ---------------------------------------------------------------------------

EMISSION_MAP: dict[int, dict[str, Any]] = {
    1: {
        "oscal_element": "component-definition",
        "responsible_component": "canon.baselines.publisher",
        "ksi_themes": [KsiTheme.CNA, KsiTheme.SVC],
        "cadence": FreshnessCadence.ON_PUBLISH,
        "mapping_source": "UIAO_022 §13.3 TBL-P2-011 row 1",
    },
    2: {
        "oscal_element": "assessment-results/finding",
        "responsible_component": "drift.engine.realtime",
        "ksi_themes": [KsiTheme.MLA, KsiTheme.CMT],
        "cadence": FreshnessCadence.REAL_TIME_CRITICAL,
        "mapping_source": "UIAO_022 §13.3 TBL-P2-011 row 2",
    },
    3: {
        "oscal_element": "assessment-results/finding",
        "responsible_component": "drift.engine.scheduled",
        "ksi_themes": [KsiTheme.MLA, KsiTheme.CMT],
        "cadence": FreshnessCadence.DAILY_ROUTINE,
        "mapping_source": "UIAO_022 §13.3 TBL-P2-011 row 3",
    },
    4: {
        "oscal_element": "poam-item",
        "responsible_component": "enforcement.workflows.opener",
        "ksi_themes": [KsiTheme.CMT, KsiTheme.MLA],
        "cadence": FreshnessCadence.ON_WORKFLOW,
        "mapping_source": "UIAO_022 §13.3 TBL-P2-011 row 4",
    },
    5: {
        "oscal_element": "poam-item",
        "responsible_component": "enforcement.workflows.closer",
        "ksi_themes": [KsiTheme.CMT, KsiTheme.MLA],
        "cadence": FreshnessCadence.ON_WORKFLOW,
        "mapping_source": "UIAO_022 §13.3 TBL-P2-011 row 5",
    },
    6: {
        "oscal_element": "assessment-plan/activity",
        "responsible_component": "provenance.recorder",
        "ksi_themes": [KsiTheme.MLA, KsiTheme.MLA],
        "cadence": FreshnessCadence.CONTINUOUS,
        "mapping_source": "UIAO_022 §13.3 TBL-P2-011 row 6",
    },
    7: {
        "oscal_element": "assessment-results/observation",
        "responsible_component": "adapters.entra.ca-evaluator",
        "ksi_themes": [KsiTheme.IAM],
        "cadence": FreshnessCadence.CONTINUOUS,
        "mapping_source": "UIAO_022 §13.3 TBL-P2-011 row 7",
    },
    8: {
        "oscal_element": "assessment-results/observation",
        "responsible_component": "telemetry.sentinel.health",
        "ksi_themes": [KsiTheme.MLA],
        "cadence": FreshnessCadence.CONTINUOUS,
        "mapping_source": "UIAO_022 §13.3 TBL-P2-011 row 8",
    },
    9: {
        "oscal_element": "assessment-results/observation",
        "responsible_component": "adapters.registry.health",
        "ksi_themes": [KsiTheme.MLA, KsiTheme.CMT],
        "cadence": FreshnessCadence.CONTINUOUS,
        "mapping_source": "UIAO_022 §13.3 TBL-P2-011 row 9",
    },
    10: {
        "oscal_element": "component-definition",
        "responsible_component": "scuba.conformance.reporter",
        "ksi_themes": [KsiTheme.CNA, KsiTheme.SVC, KsiTheme.IAM],
        "cadence": FreshnessCadence.ON_SCUBA,
        "mapping_source": "UIAO_022 §13.3 TBL-P2-011 row 10",
    },
    11: {
        "oscal_element": "system-security-plan",
        "responsible_component": "cato.package.aggregator",
        "ksi_themes": list(KsiTheme),  # aggregate — all themes
        "cadence": FreshnessCadence.QUARTERLY,
        "mapping_source": "UIAO_022 §13.3 TBL-P2-011 row 11",
    },
}

# Staleness budgets in seconds per cadence
_CADENCE_BUDGET_SECONDS: dict[FreshnessCadence, float] = {
    FreshnessCadence.REAL_TIME_CRITICAL: 300,  # 5 min
    FreshnessCadence.DAILY_ROUTINE: 86_400,  # 24 h
    FreshnessCadence.ON_PUBLISH: 7 * 86_400,  # 7 days
    FreshnessCadence.ON_SCUBA: 7 * 86_400,  # 7 days
    FreshnessCadence.ON_WORKFLOW: 3_600,  # 1 h
    FreshnessCadence.CONTINUOUS: 600,  # 10 min
    FreshnessCadence.QUARTERLY: 95 * 86_400,  # ~95 days
}


def tag_artifact(artifact: dict[str, Any], row: int) -> dict[str, Any]:
    """Inject ``fedramp:ksi-*`` props into an OSCAL artifact dict.

    Modifies *artifact* in-place and returns it.  The ``props`` key is
    created if absent; existing props are preserved.

    Args:
        artifact: Mutable OSCAL artifact dict (will be modified in-place).
        row: Emission map row number (1–11 per UIAO_133 §2.2).

    Returns:
        The same ``artifact`` dict with ``fedramp:ksi-*`` props injected.

    Raises:
        KeyError: If ``row`` is not in EMISSION_MAP (1–11).
    """
    entry = EMISSION_MAP[row]
    props = KsiEmissionProps(
        ksi_themes=entry["ksi_themes"],
        ksi_mapping_source=entry["mapping_source"],
        ksi_freshness_cadence=entry["cadence"],
    )
    if "props" not in artifact:
        artifact["props"] = []
    artifact["props"].extend(props.to_oscal_props())
    return artifact


def build_ksi_evidence_record(
    row: int,
    payload: dict[str, Any],
    namespace: str = "uiao-fedramp",
) -> KsiEvidenceRecord:
    """Build a ``KsiEvidenceRecord`` for a given emission map row and payload.

    The UUID is deterministic (UUID5) so re-emitting the same payload for the
    same row produces the same UUID (ADR-106 D1 — no re-emission; stable IDs).
    """
    entry = EMISSION_MAP[row]
    props = KsiEmissionProps(
        ksi_themes=entry["ksi_themes"],
        ksi_mapping_source=entry["mapping_source"],
        ksi_freshness_cadence=entry["cadence"],
    )
    uid = str(
        _uuid_mod.uuid5(
            _uuid_mod.NAMESPACE_DNS,
            f"{namespace}:{row}:{props.ksi_emitted_at.isoformat()[:16]}",
        )
    )
    return KsiEvidenceRecord(
        uuid=uid,
        artifact_row=row,
        responsible_component=entry["responsible_component"],
        oscal_element=entry["oscal_element"],
        emission_props=props,
        payload=payload,
    )


def check_staleness(record: KsiEvidenceRecord) -> KsiDriftEvent | None:
    """Return a ``DRIFT-EVIDENCE-STALE`` event if the record is stale, else None."""
    cadence = record.emission_props.ksi_freshness_cadence
    budget = _CADENCE_BUDGET_SECONDS.get(cadence, 86_400)
    age = (datetime.now(timezone.utc) - record.emission_props.ksi_emitted_at).total_seconds()
    if age <= budget:
        return None

    return KsiDriftEvent(
        event_id=str(_uuid_mod.uuid4()),
        drift_class=DriftClass.EVIDENCE_STALE,
        severity=DriftSeverity.P2,
        subject=record.responsible_component,
        expected_cadence=cadence,
        actual_age_seconds=age,
        ksi_themes=record.emission_props.ksi_themes,
        detail=(
            f"Artifact {record.uuid!r} (row {record.artifact_row}) is {age:.0f}s old; "
            f"budget is {budget}s ({cadence.value})."
        ),
    )


def staleness_report(records: list[KsiEvidenceRecord]) -> list[KsiDriftEvent]:
    """Return all staleness drift events across a set of KSI evidence records."""
    events = []
    for rec in records:
        event = check_staleness(rec)
        if event:
            rec.is_stale = True
            rec.staleness_age_seconds = event.actual_age_seconds
            events.append(event)
    return events
