"""UIAO AI Inventory governance package.

Applies OrgPath identity governance to federal AI systems reported under
OMB M-25-21 / EO 13960. The scanner ingests the OMB 2025 Federal AI Use
Case Inventory CSV and produces drift findings for systems that lack
organizational placement, authorization-to-operate, owner identity, or
PIA documentation.  The JML module detects lifecycle events (joiner,
mover, leaver) by diffing annual inventory vintages.

Canon reference: UIAO_196, UIAO_197, ADR-112, ADR-114
"""

from uiao.governance.ai_inventory.drift import (
    DRIFT_AI_AGENTIC_UNGOVERNED,
    DRIFT_AI_ATO_GAP,
    DRIFT_AI_NO_ORGPATH,
    DRIFT_AI_PII_NO_PIA,
    DRIFT_AI_SHADOW,
    DRIFT_AI_STALENESS,
    DRIFT_AI_UNOWNED,
)
from uiao.governance.ai_inventory.jml import (
    STALENESS_THRESHOLD_DAYS,
    JMLAction,
    JMLEvent,
    JMLEventSet,
    JMLEventType,
    detect_events,
    write_evidence_artifacts,
)
from uiao.governance.ai_inventory.scanner import ScanResult, scan_inventory
from uiao.governance.ai_inventory.schema import AgentClass, AISystemRecord, DevStage

__all__ = [
    # schema
    "AISystemRecord",
    "AgentClass",
    "DevStage",
    # drift constants
    "DRIFT_AI_NO_ORGPATH",
    "DRIFT_AI_ATO_GAP",
    "DRIFT_AI_UNOWNED",
    "DRIFT_AI_SHADOW",
    "DRIFT_AI_AGENTIC_UNGOVERNED",
    "DRIFT_AI_PII_NO_PIA",
    "DRIFT_AI_STALENESS",
    # scanner
    "scan_inventory",
    "ScanResult",
    # jml
    "detect_events",
    "write_evidence_artifacts",
    "JMLEventType",
    "JMLEvent",
    "JMLAction",
    "JMLEventSet",
    "STALENESS_THRESHOLD_DAYS",
]
