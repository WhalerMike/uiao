from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


def canonical_json(data: Any) -> str:
    """Deterministic JSON serialization."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_hash(data: Any) -> str:
    """Stable SHA256 hash of canonical JSON."""
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


class IRBase(BaseModel):
    """Canonical, immutable IR base."""

    model_config = ConfigDict(frozen=True)

    def to_canonical(self) -> str:
        return canonical_json(self.model_dump(mode="json", exclude_none=True))

    def hash(self) -> str:
        return canonical_hash(self.model_dump(mode="json", exclude_none=True))


class ProvenanceRecord(IRBase):
    source: str
    timestamp: str
    version: str
    content_hash: Optional[str] = None
    actor: Optional[str] = None


class Identity(IRBase):
    id: str
    kind: Literal["user", "service", "device", "group"] = "user"
    namespace: Literal["entra", "onprem", "workload", "external"] = "entra"
    attributes: Dict[str, Any] = Field(default_factory=dict)
    provenance: ProvenanceRecord


class Resource(IRBase):
    id: str
    kind: Literal["site", "mailbox", "app", "api", "segment", "other"] = "other"
    attributes: Dict[str, Any] = Field(default_factory=dict)
    provenance: ProvenanceRecord


class Boundary(IRBase):
    id: str
    description: Optional[str] = None
    constraints: Dict[str, Any] = Field(default_factory=dict)
    provenance: ProvenanceRecord


class Control(IRBase):
    id: str
    source: Literal["scuba", "nist", "fedramp", "overlay", "ksi", "custom"] = "custom"
    description: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    mappings: Dict[str, List[str]] = Field(default_factory=dict)
    provenance: ProvenanceRecord


class Policy(IRBase):
    id: str
    control_ref: str
    description: Optional[str] = None
    scope: Dict[str, List[str]] = Field(default_factory=dict)
    conditions: Dict[str, Any] = Field(default_factory=dict)
    expected_state: Dict[str, Any] = Field(default_factory=dict)
    provenance: ProvenanceRecord


class EnforcementTarget(IRBase):
    id: str
    platform: Literal["azure", "m365", "aws", "gcp", "network-overlay", "onprem", "custom"] = "custom"
    capability: str
    config: Dict[str, Any] = Field(default_factory=dict)
    provenance: ProvenanceRecord


class Evidence(IRBase):
    id: str
    source: str
    control_id: Optional[str] = None
    policy_id: Optional[str] = None
    timestamp: str
    data: Dict[str, Any] = Field(default_factory=dict)
    evaluation: Dict[str, Any] = Field(default_factory=dict)
    provenance: ProvenanceRecord


class DriftState(IRBase):
    id: str
    resource_id: str
    policy_ref: str
    expected_hash: str
    actual_hash: str
    drift_detected: bool
    classification: Literal["benign", "risky", "unauthorized"] = "risky"
    delta: Dict[str, List[str]] = Field(default_factory=dict)
    provenance: ProvenanceRecord


class BoundPolicy(IRBase):
    id: str
    policy: Policy
    identity: Identity
    resource: Resource
    boundary: Boundary
    enforcement_targets: List[EnforcementTarget] = Field(default_factory=list)
    provenance: ProvenanceRecord


def bind_policy(
    policy: Policy,
    identity: Identity,
    resource: Resource,
    boundary: Boundary,
    targets: Optional[List[EnforcementTarget]] = None,
    provenance: Optional[ProvenanceRecord] = None,
) -> BoundPolicy:
    """Pure deterministic binding function."""
    sorted_targets = sorted(targets or [], key=lambda t: t.id)
    prov = provenance or ProvenanceRecord(
        source="uiao-binding",
        timestamp="1970-01-01T00:00:00Z",
        version="0.1.0",
        content_hash=None,
    )
    return BoundPolicy(
        id=f"bpg:{policy.id}:{identity.id}:{resource.id}:{boundary.id}",
        policy=policy,
        identity=identity,
        resource=resource,
        boundary=boundary,
        enforcement_targets=sorted_targets,
        provenance=prov,
    )
