from pydantic import BaseModel, Field
from typing import List, Optional
from core.orgpath.orgpath_model import OrgPath, OrgPathSegment


class VirtualOU(BaseModel):
    """
    A logical organizational unit in the Governance OS.
    This is a commercial, cloud-agnostic abstraction that
    represents where governance boundaries apply.
    """
    name: str
    type: str  # e.g., "division", "department", "team", "function"
    children: List["VirtualOU"] = Field(default_factory=list)

    def add_child(self, child: "VirtualOU"):
        self.children.append(child)

    def find(self, name: str) -> Optional["VirtualOU"]:
        """
        Recursively search for a VirtualOU by name.
        """
        if self.name == name:
            return self
        for child in self.children:
            found = child.find(name)
            if found:
                return found
        return None


class VirtualOUTree(BaseModel):
    """
    A hierarchical tree of Virtual OUs that maps directly to OrgPath.
    This is the commercial equivalent of a logical OU structure.
    """
    root: VirtualOU

    def resolve_orgpath(self, orgpath: OrgPath) -> Optional[VirtualOU]:
        """
        Walk the tree using the OrgPath segments.
        """
        current = self.root
        for segment in orgpath.segments:
            next_node = None
            for child in current.children:
                if child.name == segment.name:
                    next_node = child
                    break
            if not next_node:
                return None
            current = next_node
        return current
