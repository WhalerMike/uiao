from pydantic import BaseModel, Field
from typing import List, Optional

class OrgPathSegment(BaseModel):
    """
    A single segment of an OrgPath, representing a logical unit
    such as division, department, team, or function.
    """
    name: str
    type: str  # e.g., "division", "department", "team"
    code: Optional[str] = None


class OrgPath(BaseModel):
    """
    A canonical, hierarchical representation of where an identity,
    device, or resource lives within an organization.
    """
    segments: List[OrgPathSegment] = Field(default_factory=list)

    def to_string(self) -> str:
        """Return a slash-delimited OrgPath string."""
        return "/".join([seg.name for seg in self.segments])

    @classmethod
    def from_string(cls, path: str):
        """Parse a slash-delimited OrgPath string into segments."""
        parts = path.split("/")
        segments = [OrgPathSegment(name=p, type="unspecified") for p in parts]
        return cls(segments=segments)
