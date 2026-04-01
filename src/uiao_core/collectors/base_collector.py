from __future__ import annotations

import abc
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class EvidenceProvenance:
    """
    Provenance envelope for a single evidence collection event.
    """
    collector_id: str
    hash: str
    collection_timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "collector_id": self.collector_id,
            "hash": self.hash,
            "collection_timestamp": self.collection_timestamp.isoformat(),
        }


@dataclass
class EvidenceObject:
    """
    Canonical evidence object returned by all collectors.

    This object is designed to align with the KSI schema and downstream
    OSCAL/Quarto evidence pipelines.
    """
    ksi_id: str
    source: str
    timestamp: datetime
    raw_data: Any
    normalized_data: Optional[Dict[str, Any]]
    provenance: EvidenceProvenance
    freshness_valid: bool = field(default=False)

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the evidence object to a JSON-serializable dictionary.
        """
        return {
            "ksi_id": self.ksi_id,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "raw_data": self.raw_data,
            "normalized_data": self.normalized_data,
            "provenance": self.provenance.to_dict(),
            "freshness_valid": self.freshness_valid,
        }


class BaseCollector(abc.ABC):
    """
    Abstract base class for all UIAO-Core evidence collectors.

    Each concrete collector is responsible for:
    - Connecting to a specific data source (e.g., Entra ID, Cisco SD-WAN, InfoBlox)
    - Collecting raw telemetry/logs/configuration
    - Normalizing the data into a canonical structure
    - Emitting an EvidenceObject that can be consumed by KSI validators
    """

    #: Stable identifier for this collector implementation.
    #: Subclasses MUST override this with a unique, lowercase string.
    COLLECTOR_ID: str = "base"

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize the collector with a configuration dictionary.

        The config dict is intentionally unstructured at this layer to allow
        each collector to define its own configuration schema (e.g., API keys,
        endpoints, scopes, filters).
        """
        self._config: Dict[str, Any] = config or {}

    @property
    def collector_id(self) -> str:
        """
        Return the stable collector identifier.

        This is used in:
        - Provenance envelopes
        - Registry lookups
        - Logging and diagnostics
        """
        return self.COLLECTOR_ID

    @abc.abstractmethod
    def collect(self, ksi_id: str) -> EvidenceObject:
        """
        Collect evidence for the given KSI and return a canonical EvidenceObject.

        Implementations should:
        - Fetch raw data from the underlying system
        - Normalize it into a structured form (if applicable)
        - Compute a provenance hash
        - Set freshness_valid based on the KSI's freshness window (if known)

        Parameters
        ----------
        ksi_id:
            Identifier of the KSI for which evidence is being collected.

        Returns
        -------
        EvidenceObject
            Canonical evidence object ready for validation and downstream export.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def health_check(self) -> bool:
        """
        Perform a lightweight health check for this collector.

        This should verify that:
        - Credentials are present and valid (as far as can be determined cheaply)
        - Required endpoints are reachable
        - Any critical configuration is present

        Returns
        -------
        bool
            True if the collector appears healthy and ready to collect evidence,
            False otherwise.
        """
        raise NotImplementedError

    # -------------------------------------------------------------------------
    # Helper methods for subclasses
    # -------------------------------------------------------------------------

    def _now(self) -> datetime:
        """
        Return the current UTC timestamp.

        Centralized here to make testing and overriding easier.
        """
        return datetime.now(timezone.utc)

    def _compute_hash(self, payload: Any) -> str:
        """
        Compute a SHA-256 hash of the given payload.

        The payload is first converted to a canonical JSON string (where possible)
        to ensure stable hashing across runs.
        """
        try:
            serialized = json.dumps(payload, sort_keys=True, default=str)
        except TypeError:
            # Fallback: use string representation if JSON serialization fails
            serialized = str(payload)

        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _build_provenance(self, raw_data: Any) -> EvidenceProvenance:
        """
        Build a provenance envelope for the given raw data payload.
        """
        return EvidenceProvenance(
            collector_id=self.collector_id,
            hash=self._compute_hash(raw_data),
            collection_timestamp=self._now(),
        )
