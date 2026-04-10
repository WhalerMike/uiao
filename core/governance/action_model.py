from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel


class Action(BaseModel):
      id: str
      action_type: str
      severity: str
      reason: str
      created_at: datetime
      details: Dict[str, Any]
      orgpath: Optional[str] = None
      notes: Optional[str] = None
  
