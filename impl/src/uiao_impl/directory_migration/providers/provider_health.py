from datetime import datetime
from typing import Dict, Any
from pydantic import BaseModel


class ProviderHealth(BaseModel):
    provider: str
        healthy: bool
            checked_at: datetime
                details: Dict[str, Any]
                