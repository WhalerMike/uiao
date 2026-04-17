from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel


class Evidence(BaseModel):
      """
          Represents a single piece of governance evidence
              linked to an action and drift event.
                  """
      id: str
      action_id: str
      collected_at: datetime
      source: str
      data: Dict[str, Any]
      orgpath: Optional[str] = None
      notes: Optional[str] = None
  
