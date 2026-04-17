import uuid
from datetime import datetime
from typing import Optional

from core.drift.drift_engine import DriftState
from core.governance.remediation_model import Remediation


class RemediationEngine:
    """
        Deterministic remediation wrapper.
            Adapters still perform the actual remediation.
                """

                    def perform(self, drift: DriftState, adapter) -> Optional[Remediation]:
                            result = adapter.remediate(drift)
                                    if result is None:
                                                return None

                                                        return Remediation(
                                                                    id=str(uuid.uuid4()),
                                                                                remediation_type="adapter-remediation",
                                                                                            created_at=datetime.utcnow(),
                                                                                                        details=result,
                                                                                                                    orgpath=drift.orgpath,
                                                                                                                            )
                                                                                                                            