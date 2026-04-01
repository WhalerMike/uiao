"""BaseAdapter ABC - every adapter implements this contract."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List

@dataclass
class AdapterMetadata:
    adapter_id: str
    name: str
    version: str
    certification_level: int = 1
    plane: str = "Identity"
    capabilities: List[str] = field(default_factory=list)

@dataclass
class CanonicalClaim:
    claim_id: str
    source_system: str
    claim_type: str = ""
    value: Any = None

@dataclass
class ClaimFilter:
    source_system: str = ""
    claim_type: str = ""

@dataclass
class DriftReport:
    adapter_id: str
    drifted: bool = False
    details: str = ""

@dataclass
class KSIBundle:
    bundle_id: str
    adapter_id: str

@dataclass
class ProvenanceRecord:
    record_id: str
    adapter_id: str
    source_system: str = ""

class BaseAdapter(ABC):
    @abstractmethod
    async def connect(self, config: dict) -> bool: ...
    @abstractmethod
    async def extract_claims(self, filter: ClaimFilter) -> List[CanonicalClaim]: ...
    @abstractmethod
    async def detect_drift(self) -> DriftReport: ...
    @abstractmethod
    async def transform_to_canonical(self, raw: Any) -> CanonicalClaim: ...
    @abstractmethod
    async def generate_lineage(self) -> ProvenanceRecord: ...
    @abstractmethod
    async def generate_ksi_bundle(self) -> KSIBundle: ...
    @abstractmethod
    def get_metadata(self) -> AdapterMetadata: ...
