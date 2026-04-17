import os
import json
from datetime import datetime
from typing import Any, Dict


class AuditLog:
    """
        Minimal append-only audit log.
            Writes JSON lines to core/governance/audit.log
                """

                    def __init__(self, path: str | None = None):
                            if path is None:
                                        path = os.path.join(os.path.dirname(__file__), "audit.log")
                                                self.path = path

                                                    def write(self, record: Dict[str, Any]):
                                                            record["timestamp"] = datetime.utcnow().isoformat()
                                                                    with open(self.path, "a", encoding="utf-8") as f:
                                                                                f.write(json.dumps(record, default=str) + "\n")
                                                                                