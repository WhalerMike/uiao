"""
UIAO-Core Database Adapter Abstract Base Class
Canonical implementation of all 7 responsibility domains defined in the
Database Adapter Specification.

File: src/uiao_core/adapters/database_base.py
"""

from __future__ import annotations

import abc
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Dataclasses for Provenance, Schema Mapping, Queries, Claims, Drift, Evidence
# ---------------------------------------------------------------------------

@dataclass
class ConnectionProvenance:
    """
    Provenance envelope for database connections.
    """
    identity: str
    auth_method: str
    endpoint: str
    tls_version: Optional[str]
    mtls_enabled: bool
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "identity": self.identity,
            "auth_method": self.auth_method,
            "endpoint": self.endpoint,
            "tls_version": self.tls_version,
            "mtls_enabled": self.mtls_enabled,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class SchemaMappingObject:
    """
    Canonical mapping between vendor schema and UIAO canonical schema.
    """
    vendor_schema: Dict[str, Any]
    canonical_schema: Dict[str, Any]
    mapping_rules: Dict[str, Any]
    unmapped_fields: List[str]
    version_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vendor_schema": self.vendor_schema,
            "canonical_schema": self.canonical_schema,
            "mapping_rules": self.mapping_rules,
            "unmapped_fields": self.unmapped_fields,
            "version_hash": self.version_hash,
        }


@dataclass
class QueryProvenance:
    """
    Provenance envelope for deterministic query execution.
    """
    canonical_query: Dict[str, Any]
    vendor_query: str
    execution_plan_hash: str
    row_count: int
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "canonical_query": self.canonical_query,
            "vendor_query": self.vendor_query,
            "execution_plan_hash": self.execution_plan_hash,
            "row_count": self.row_count,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ClaimObject:
    """
    Minimal, authoritative claim derived from database rows.
    """
    claim_id: str
    entity: str
    fields: Dict[str, Any]
    source: str
    provenance_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "entity": self.entity,
            "fields": self.fields,
            "source": self.source,
            "provenance_hash": self.provenance_hash,
        }


@dataclass
class ClaimSet:
    """
    A collection of ClaimObjects produced from normalized database rows.
    """
    claims: List[ClaimObject]
    source_reference: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claims": [c.to_dict() for c in self.claims],
            "source_reference": self.source_reference,
        }


@dataclass
class DriftReport:
    """
    Drift detection report for schema, constraints, cardinality, or semantics.
    """
    drift_type: str
    severity: str
    first_observed: datetime
    last_observed: datetime
    details: Dict[str, Any]
    remediation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "drift_type": self.drift_type,
            "severity": self.severity,
            "first_observed": self.first_observed.isoformat(),
            "last_observed": self.last_observed.isoformat(),
            "details": self.details,
            "remediation": self.remediation,
        }


@dataclass
class EvidenceObject:
    """
    Canonical evidence object aligned with the KSI Evidence Bundle Schema.
    """
    ksi_id: str
    source: str
    timestamp: datetime
    raw_data: Any
    normalized_data: Optional[Dict[str, Any]]
    provenance: Dict[str, Any]
    freshness_valid: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ksi_id": self.ksi_id,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "raw_data": self.raw_data,
            "normalized_data": self.normalized_data,
            "provenance": self.provenance,
            "freshness_valid": self.freshness_valid,
        }


# ---------------------------------------------------------------------------
# Abstract Base Class for Database Adapters
# ---------------------------------------------------------------------------

class DatabaseAdapterBase(abc.ABC):
    """
    Abstract Base Class for all UIAO Database Adapters.

    Implements the 7 canonical responsibility domains:

    2.1 Connection & Identity
    2.2 Schema Discovery & Canonical Mapping
    2.3 Query Normalization & Deterministic Extraction
    2.4 Data Normalization & Claim Construction
    2.5 Drift Detection & Version Integrity
    2.6 Evidence Packaging & KSI Integration
    2.7 Security, Privacy, and Operational Controls
    """

    ADAPTER_ID: str = "database-base"

    def __init__(self, config: Dict[str, Any]) -> None:
        self._config = config or {}

    # ----------------------------------------------------------------------
    # Helper utilities
    # ----------------------------------------------------------------------

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _hash(self, payload: Any) -> str:
        try:
            serialized = json.dumps(payload, sort_keys=True, default=str)
        except Exception:
            serialized = str(payload)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    # ----------------------------------------------------------------------
    # 2.1 Connection & Identity Domain
    # ----------------------------------------------------------------------

    @abc.abstractmethod
    def connect(self) -> ConnectionProvenance:
        """
        Establish a secure, authenticated connection and return provenance.
        """
        raise NotImplementedError

    # ----------------------------------------------------------------------
    # 2.2 Schema Discovery & Canonical Mapping Domain
    # ----------------------------------------------------------------------

    @abc.abstractmethod
    def discover_schema(self) -> SchemaMappingObject:
        """
        Discover vendor schema and map to UIAO canonical schema.
        """
        raise NotImplementedError

    # ----------------------------------------------------------------------
    # 2.3 Query Normalization & Deterministic Extraction Domain
    # ----------------------------------------------------------------------

    @abc.abstractmethod
    def execute_query(self, canonical_query: Dict[str, Any]) -> QueryProvenance:
        """
        Translate canonical query → vendor query and execute deterministically.
        """
        raise NotImplementedError

    # ----------------------------------------------------------------------
    # 2.4 Data Normalization & Claim Construction Domain
    # ----------------------------------------------------------------------

    @abc.abstractmethod
    def normalize(self, raw_rows: List[Dict[str, Any]]) -> ClaimSet:
        """
        Convert raw database rows into canonical ClaimObjects.
        """
        raise NotImplementedError

    # ----------------------------------------------------------------------
    # 2.5 Drift Detection & Version Integrity Domain
    # ----------------------------------------------------------------------

    @abc.abstractmethod
    def detect_drift(self) -> DriftReport:
        """
        Detect schema, constraint, cardinality, or semantics drift.
        """
        raise NotImplementedError

    # ----------------------------------------------------------------------
    # 2.6 Evidence Packaging & KSI Integration Domain
    # ----------------------------------------------------------------------

    def collect_evidence(self, ksi_id: str) -> EvidenceObject:
        """
        Produce a canonical EvidenceObject for a given KSI.

        This method orchestrates:
        - connection provenance
        - schema mapping
        - deterministic query execution
        - claim construction
        - drift detection
        - evidence packaging
        """
        conn_prov = self.connect()
        schema_map = self.discover_schema()

        # Minimal canonical query for demonstration
        canonical_query = {"select": ["*"], "from": "canonical_entity"}

        query_prov = self.execute_query(canonical_query)

        # Placeholder: raw rows would come from vendor query execution
        raw_rows = []  # Real implementation populates this
        claim_set = self.normalize(raw_rows)

        drift = self.detect_drift()

        evidence = EvidenceObject(
            ksi_id=ksi_id,
            source=self.ADAPTER_ID,
            timestamp=self._now(),
            raw_data={
                "connection": conn_prov.to_dict(),
                "schema_mapping": schema_map.to_dict(),
                "query": query_prov.to_dict(),
                "drift": drift.to_dict(),
            },
            normalized_data=claim_set.to_dict(),
            provenance={
                "adapter_id": self.ADAPTER_ID,
                "hash": self._hash(claim_set.to_dict()),
                "timestamp": self._now().isoformat(),
            },
            freshness_valid=False,
        )

        return evidence
