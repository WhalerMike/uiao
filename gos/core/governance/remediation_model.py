from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel


class Remediation(BaseModel):
    id: str
        remediation_type: str
            created_at: datetime
                details: Dict[str, Any]
                    orgpath: Optional[str] = None
                    