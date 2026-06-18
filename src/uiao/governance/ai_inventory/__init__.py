"""UIAO AI Inventory governance package.

Applies OrgPath identity governance to federal AI systems reported under
OMB M-25-21 / EO 13960. The scanner ingests the OMB 2025 Federal AI Use
Case Inventory CSV and produces drift findings for systems that lack
organizational placement, authorization-to-operate, owner identity, or
PIA documentation.

Canon reference: UIAO_196, ADR-112
"""

from uiao.governance.ai_inventory.drift import (
    DRIFT_AI_AGENTIC_UNGOVERNED,
    DRIFT_AI_ATO_GAP,
    DRIFT_AI_NO_ORGPATH,
    DRIFT_AI_PII_NO_PIA,
    DRIFT_AI_SHADOW,
    DRIFT_AI_UNOWNED,
)
from uiao.governance.ai_inventory.scanner import ScanResult, scan_inventory
from uiao.governance.ai_inventory.schema import AgentClass, AISystemRecord, DevStage

__all__ = [
    "AISystemRecord",
    "AgentClass",
    "DevStage",
    "DRIFT_AI_NO_ORGPATH",
    "DRIFT_AI_ATO_GAP",
    "DRIFT_AI_UNOWNED",
    "DRIFT_AI_SHADOW",
    "DRIFT_AI_AGENTIC_UNGOVERNED",
    "DRIFT_AI_PII_NO_PIA",
    "scan_inventory",
    "ScanResult",
]
