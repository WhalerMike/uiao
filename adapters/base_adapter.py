"""
UIAO Adapter Suite — Document 3 of 4
Canonical Python Abstract Base Class for UIAO Adapters

Scope constraint:
- UIAO Canon is frozen (no schema/governance changes here).
- This file is a code realization of the existing adapter contract.
- Vendor-specific adapters (e.g., uiao-adapter-entra) live in separate repos.
"""

from __future__ import annotations
import abc
import datetime
from typing import Any, Dict, Iterable, List, Optional, Protocol, Tuple, Union

ISO8601 = str  # For clarity in type hints


class HealthStatus:
    """Canonical health status values for adapters."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"


class ErrorClass:
    """Canonical error classes for adapter error semantics."""
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    DATA = "data"


class Claim(Protocol):
    """
    Protocol for a canonical claim object.

    NOTE: This is intentionally loose — the canonical shape is defined by
    the JSON Schemas in /schemas/. This protocol exists to make the base
    adapter interface explicit without redefining the canon.
    """
    def __getitem__(self, item: str) -> Any: ...
    def get(self, item: str, default: Any = None) -> Any: ...


class BaseAdapter(abc.ABC):
    """
    Canonical abstract base class for all UIAO adapters.

    This class encodes the adapter contract in Python, without changing
    the canonical schemas or governance model defined in uiao-core.

    Responsibility domains covered here:
      1. API structure
      2. Identity requirements (uiao_id/local_id handling)
      3. Certs/tokens (via configuration and implementer responsibility)
      4. Provenance encoding (helpers, not schema changes)
      5. Normalization/canonicalization (abstract hooks)
      6. Drift detection (abstract hooks)
      7. Confidence scoring (optional hooks)
      8. Error semantics/recovery (structured error reporting)
      9. Publication rules (interface only; transport is external)
     10. Security controls (boundary assumptions, not enforced here)
     11. Lifecycle/versioning (adapter metadata)
     12. Operational telemetry (health/metrics hooks)
     13. UAI automation hooks (introspection methods)
    """

    # -----------------------------------------------------------------
    # 0. Adapter identity and metadata
    # -----------------------------------------------------------------

    @property
    @abc.abstractmethod
    def adapter_id(self) -> str:
        """
        Canonical adapter identifier.
        Example: "uiao.adapter.microsoft.entra.v1"
        MUST be stable and unique per adapter implementation.
        """
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def source_system(self) -> str:
        """
        Canonical name of the source system.
        Example: "entra-id", "cisco-ise", "state-dmv-db"
        """
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def version(self) -> str:
        """
        Semantic version of the adapter implementation.
        Example: "1.0.0"
        """
        raise NotImplementedError

    # -----------------------------------------------------------------
    # 1. API structure
    # -----------------------------------------------------------------

    @abc.abstractmethod
    def discover(self) -> Dict[str, Any]:
        """
        Discover what the adapter can see.
        Returns a structured description of:
        - Tenants / scopes
        - Supported domains (identity, device, network, policy, telemetry)
        - Any relevant limits or constraints
        This MUST NOT change the source system; it is read-only.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def pull_state(self, scope: Optional[str] = None) -> Iterable[Dict[str, Any]]:
        """
        Pull current state for a given scope.
        Returns an iterable of raw source objects (vendor-native shape).
        Normalization is handled separately by normalize().
        :param scope: Optional logical scope (tenant, org, segment, etc.).
        """
        raise NotImplementedError

    @abc.abstractmethod
    def pull_changes(
        self,
        since: Optional[ISO8601] = None,
        scope: Optional[str] = None,
    ) -> Iterable[Dict[str, Any]]:
        """
        Pull incremental changes since a given timestamp or checkpoint.
        Returns an iterable of raw source objects (vendor-native shape).
        :param since: ISO8601 timestamp or checkpoint token.
        :param scope: Optional logical scope.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def normalize(self, raw: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Normalize a raw source object into one or more canonical UIAO objects.
        This method MUST:
        - Map source fields to canonical fields
        - Attach uiao_id/local_id
        - Attach provenance and drift envelopes (or delegate to helpers)
        - Produce objects that validate against the canonical JSON Schemas
        Returns a list of canonical objects (claims without transport wrapper).
        """
        raise NotImplementedError

    @abc.abstractmethod
    def publish(self, claims: Iterable[Claim]) -> None:
        """
        Publish canonical claims to the UIAO truth fabric.
        This method MUST:
        - Be idempotent (re-publishing the same claim is safe)
        - Preserve ordering per entity where required
        - Not mutate the canonical claim payloads
        Transport (HTTP, gRPC, message bus) is implementation-specific.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def health(self) -> Dict[str, Any]:
        """
        Report adapter health and recent error conditions.
        MUST include at least:
        - status: one of HealthStatus.HEALTHY/DEGRADED/FAILED
        - last_success_at: ISO8601 timestamp or None
        - error_counts: dict by ErrorClass
        - details: optional free-form diagnostics (non-sensitive)
        """
        raise NotImplementedError

    # -----------------------------------------------------------------
    # 2. Identity requirements (helpers)
    # -----------------------------------------------------------------

    @abc.abstractmethod
    def derive_uiao_id(self, raw: Dict[str, Any]) -> str:
        """
        Derive a deterministic uiao_id from raw source data.
        MUST be stable across runs for the same logical entity.
        Example pattern: "uiao:identity:{scope}:{namespace}:{id}"
        """
        raise NotImplementedError

    @abc.abstractmethod
    def extract_local_id(self, raw: Dict[str, Any]) -> str:
        """
        Extract the vendor-native identifier (local_id) from raw source data.
        MUST be stable and match the source system's primary key semantics.
        """
        raise NotImplementedError

    # -----------------------------------------------------------------
    # 3. Provenance encoding (helpers)
    # -----------------------------------------------------------------

    def build_provenance(
        self,
        method: str,
        evidence_pointer: Optional[str],
        observed_at: Optional[datetime.datetime] = None,
        collected_at: Optional[datetime.datetime] = None,
    ) -> Dict[str, Any]:
        """
        Build a provenance envelope conforming to /schemas/provenance.schema.json.
        :param method: "api_pull", "stream", or "webhook"
        :param evidence_pointer: URI or structured reference inside the boundary
        :param observed_at: When the event/state occurred (if known)
        :param collected_at: When the adapter collected the data (defaults to now)
        """
        now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
        collected = collected_at or now
        observed = observed_at or collected
        return {
            "source_system": self.source_system,
            "source_adapter": self.adapter_id,
            "collected_at": collected.isoformat(),
            "observed_at": observed.isoformat(),
            "method": method,
            "evidence_pointer": evidence_pointer or "",
        }

    # -----------------------------------------------------------------
    # 4. Drift detection (helpers)
    # -----------------------------------------------------------------

    @abc.abstractmethod
    def detect_drift(
        self,
        previous: Optional[Dict[str, Any]],
        current: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Detect drift between previous and current canonical objects.
        MUST return a dict that validates against /schemas/drift.schema.json.
        """
        raise NotImplementedError

    # -----------------------------------------------------------------
    # 5. Confidence scoring (optional hook)
    # -----------------------------------------------------------------

    def compute_confidence(
        self,
        raw: Dict[str, Any],
        normalized: Dict[str, Any],
    ) -> Optional[float]:
        """
        Optional hook to compute a confidence score (0.0–1.0).
        Default returns None (implicitly 1.0).
        """
        return None

    # -----------------------------------------------------------------
    # 6. Error semantics & recovery (helpers)
    # -----------------------------------------------------------------

    def classify_error(self, exc: Exception) -> str:
        """
        Classify an exception into one of the canonical error classes.
        Default is conservative; real adapters should refine it.
        """
        return ErrorClass.TRANSIENT

    # -----------------------------------------------------------------
    # 7. Operational telemetry (hooks)
    # -----------------------------------------------------------------

    def metrics(self) -> Dict[str, Any]:
        """
        Optional hook to expose adapter metrics.
        SHOULD include: objects_processed, last_run_duration_ms, etc.
        """
        return {}

    # -----------------------------------------------------------------
    # 8. UAI automation hooks (introspection)
    # -----------------------------------------------------------------

    def describe_capabilities(self) -> Dict[str, Any]:
        """
        Introspection hook for UAI-aligned automation.
        SHOULD describe supported_domains, schemas, mapping_strategy, etc.
        """
        return {
            "adapter_id": self.adapter_id,
            "source_system": self.source_system,
            "version": self.version,
            "supported_domains": [],
            "supported_schemas": [],
            "mapping_strategy": "mixed",
            "limitations": [],
            "schema_versions": {},
        }

    # -----------------------------------------------------------------
    # 9. Convenience: end-to-end run helpers (non-canonical)
    # -----------------------------------------------------------------

    def run_full_state_sync(self, scope: Optional[str] = None) -> Tuple[int, int]:
        """
        Convenience: discover -> pull_state -> normalize -> publish.
        Returns: (raw_count, claim_count)
        """
        raw_objects = list(self.pull_state(scope=scope))
        claims: List[Dict[str, Any]] = []
        for raw in raw_objects:
            normalized_objects = self.normalize(raw)
            claims.extend(normalized_objects)
        self.publish(claims)
        return len(raw_objects), len(claims)

    def run_incremental_sync(
        self,
        since: Optional[ISO8601] = None,
        scope: Optional[str] = None,
    ) -> Tuple[int, int]:
        """
        Convenience: pull_changes -> normalize -> publish.
        Returns: (raw_count, claim_count)
        """
        raw_objects = list(self.pull_changes(since=since, scope=scope))
        claims: List[Dict[str, Any]] = []
        for raw in raw_objects:
            normalized_objects = self.normalize(raw)
            claims.extend(normalized_objects)
        self.publish(claims)
        return len(raw_objects), len(claims)
