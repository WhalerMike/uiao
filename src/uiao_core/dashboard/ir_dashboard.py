from __future__ import annotations

import dataclasses
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from uiao_core.freshness.engine import FreshnessRecord, build_freshness_records
from uiao_core.governance.actions import GovernanceAction
from uiao_core.ir.models.core import Evidence


def build_ir_dashboard(
      evidence_list: List[Evidence],
      actions: List[GovernanceAction],
      thresholds: Optional[Dict[str, int]] = None,
      now: Optional[datetime] = None,
) -> Dict:
      """Build a governance dashboard dict from evidence and actions."""
      now = now or datetime.now(timezone.utc)
      freshness_records = build_freshness_records(evidence_list, thresholds=thresholds, now=now)

    fresh = sum(1 for r in freshness_records if r.status == "fresh")
    stale_soon = sum(1 for r in freshness_records if r.status == "stale-soon")
    stale = sum(1 for r in freshness_records if r.status == "stale")

    by_severity: Dict[str, int] = {}
    for a in actions:
              by_severity[a.severity] = by_severity.get(a.severity, 0) + 1

    return {
              "generated_at": now.isoformat(),
              "evidence_total": len(evidence_list),
              "freshness_summary": {
                            "fresh": fresh,
                            "stale_soon": stale_soon,
                            "stale": stale,
              },
              "governance_summary": {
                            "total_actions": len(actions),
                            "by_severity": by_severity,
              },
              "freshness_records": [dataclasses.asdict(r) for r in freshness_records],
              "governance_actions": [
                            {
                                              "ksi_id": a.ksi_id,
                                              "control_id": a.control_id,
                                              "policy_id": a.policy_id,
                                              "severity": a.severity,
                                              "drift_classification": a.drift_classification,
                                              "owner": a.owner,
                                              "sla_days": a.sla_days,
                                              "action_type": a.action_type,
                                              "description": a.description,
                                              "evidence_id": a.evidence_id,
                            }
                            for a in actions
              ],
    }


def export_ir_dashboard(
      evidence_list: List[Evidence],
      actions: List[GovernanceAction],
      output_path: str,
      thresholds: Optional[Dict[str, int]] = None,
) -> str:
      """Build and write the IR dashboard JSON to output_path. Returns the path."""
      dashboard = build_ir_dashboard(evidence_list, actions, thresholds=thresholds)
      out = Path(output_path)
      out.parent.mkdir(parents=True, exist_ok=True)
      out.write_text(json.dumps(dashboard, indent=2, ensure_ascii=False), encoding="utf-8")
      return str(out)
