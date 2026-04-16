from typing import Any, Dict, Optional

from core.drift.drift_engine import classify_drift
from core.governance.action_engine import determine_action
from core.governance.audit_log import AuditLog
from core.governance.remediation_engine import RemediationEngine
from core.evidence.evidence_model import Evidence
from core.evidence.evidence_store import EvidenceStore

import uuid
from datetime import datetime


class GovernancePipeline:
    """
        Canonical governance pipeline for UIAO-GOS.
            Runs: adapter -> drift -> action -> remediation -> evidence -> audit
                """

                    def __init__(self, adapter):
                            self.adapter = adapter
                                    self.audit = AuditLog()
                                            self.evidence_store = EvidenceStore()
                                                    self.remediation_engine = RemediationEngine()

                                                        def detect_only(self) -> Dict[str, Any]:
                                                                """Run drift detection only, no action or remediation."""
                                                                        expected = self.adapter.get_expected_state()
                                                                                actual = self.adapter.get_actual_state()
                                                                                        drift = classify_drift(expected, actual)
                                                                                                return drift.dict()

                                                                                                    def run(self) -> Dict[str, Any]:
                                                                                                            """Run the full governance pipeline."""
                                                                                                                    expected = self.adapter.get_expected_state()
                                                                                                                            actual = self.adapter.get_actual_state()
                                                                                                                                    drift = classify_drift(expected, actual)

                                                                                                                                            self.audit.write({"event": "drift-detected", "drift": drift.dict()})

                                                                                                                                                    action = determine_action(drift)
                                                                                                                                                            self.audit.write({"event": "action-determined", "action": action.dict()})

                                                                                                                                                                    remediation = self.remediation_engine.perform(drift, self.adapter)
                                                                                                                                                                            if remediation:
                                                                                                                                                                                        self.audit.write({
                                                                                                                                                                                                        "event": "remediation-performed",
                                                                                                                                                                                                                        "remediation": remediation.dict(),
                                                                                                                                                                                                                                    })

                                                                                                                                                                                                                                            evidence = Evidence(
                                                                                                                                                                                                                                                        id=str(uuid.uuid4()),
                                                                                                                                                                                                                                                                    action_id=action.id,
                                                                                                                                                                                                                                                                                collected_at=datetime.utcnow(),
                                                                                                                                                                                                                                                                                            source=getattr(self.adapter, "name", "unknown"),
                                                                                                                                                                                                                                                                                                        data={"drift": drift.dict(), "action": action.dict()},
                                                                                                                                                                                                                                                                                                                    orgpath=drift.orgpath,
                                                                                                                                                                                                                                                                                                                            )
                                                                                                                                                                                                                                                                                                                                    self.evidence_store.save(evidence)
                                                                                                                                                                                                                                                                                                                                            self.audit.write({"event": "evidence-created", "evidence": evidence.dict()})

                                                                                                                                                                                                                                                                                                                                                    return {
                                                                                                                                                                                                                                                                                                                                                                "drift": drift.dict(),
                                                                                                                                                                                                                                                                                                                                                                            "action": action.dict(),
                                                                                                                                                                                                                                                                                                                                                                                        "remediation": remediation.dict() if remediation else None,
                                                                                                                                                                                                                                                                                                                                                                                                    "evidence_id": evidence.id,
                                                                                                                                                                                                                                                                                                                                                                                                            }
                                                                                                                                                                                                                                                                                                                                                                                                            