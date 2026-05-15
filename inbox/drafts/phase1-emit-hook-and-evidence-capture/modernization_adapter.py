"""ModernizationAdapter — emit() hook for the modernization adapter surface.

Per ADR-071, the substrate has three independent adapter surfaces:
collectors, enforcement adapters, and modernization adapters. This file
introduces the third surface's base class — until now, modernization
adapters had no shared ABC and emitted free-form per adapter.

Phase 1 ships the ABC + the `emit()` hook + the routing to
`uiao.telemetry.provenance`. Phase 2 (runtime drift) extends the sink's
sync validation with semantic / authz / identity checks. Existing
modernization adapters retrofit one PR at a time, gated by the
`uiao.envelope.modernization` feature flag.

This file is a DRAFT skeleton. Promotion to `src/uiao/adapters/base.py`
happens when ADR-071 is ACCEPTED.
"""

from __future__ import annotations

import abc
import logging
from typing import Any, ClassVar, Optional

# Imports below resolve once Phase 0 promotes to canon paths.
# Draft skeleton uses the drafts-folder import.
from uiao.models.provenance import Envelope
from uiao.telemetry.provenance import emit as sink_emit
from uiao.telemetry.provenance import EmitOutcome


logger = logging.getLogger(__name__)


class ModernizationAdapter(abc.ABC):
    """Abstract base class for modernization adapters.

    Per ADR-071, every modernization adapter (active-directory survey,
    gcc-boundary-probe, hrit, pki, future Login.gov / PIV / SCuBA, etc.)
    inherits from this class. The single public emission method is
    `emit()`; subclasses implement domain-specific logic and call `emit()`
    once per claim.

    The ABC carries the minimal contract — adapter_id, manifest path,
    and the emit() hook. Concrete adapters add their own collect/plan/
    apply methods (the engagement-specific verbs vary by adapter family).
    """

    #: Stable adapter identifier; MUST match an entry in
    #: `src/uiao/canon/modernization-registry.yaml` or
    #: `src/uiao/canon/adapter-registry.yaml`.
    ADAPTER_ID: ClassVar[str] = "base"

    #: Path (relative to package root) of the adapter's manifest JSON.
    #: Loaded once at __init__ time. Provides `issuer_identity` default,
    #: `source_system` default, and `consent_envelope` defaults.
    MANIFEST_PATH: ClassVar[Optional[str]] = None

    def __init__(self, config: Optional[dict[str, Any]] = None) -> None:
        if self.ADAPTER_ID == "base":
            raise TypeError(
                "Subclasses of ModernizationAdapter MUST override ADAPTER_ID "
                "with a registry-matching adapter ID"
            )
        self._config: dict[str, Any] = config or {}
        self._manifest: dict[str, Any] = self._load_manifest()

    # ------------------------------------------------------------------
    # Public emission API
    # ------------------------------------------------------------------

    def emit(self, claim: dict[str, Any], envelope: Envelope) -> EmitOutcome:
        """Emit a claim with its provenance envelope.

        The substrate refuses non-conforming envelopes (P1 DRIFT-PROVENANCE
        / DRIFT-IDENTITY / DRIFT-AUTHZ). On rejection, this method returns
        an `EmitOutcome` with the finding attached; the adapter is
        responsible for not propagating the claim downstream.

        Parameters
        ----------
        claim
            The canonical claim payload — domain-specific shape, must
            conform to `adr-005-canonical-claim-schema`.
        envelope
            A sealed Envelope. Construct via
            `Envelope.for_claim(...).seal(source_record=..., mtls_thumbprint=...)`.

        Returns
        -------
        EmitOutcome
            Carries the acceptance decision and any drift findings.
            See `uiao.telemetry.provenance.EmitOutcome` for shape.
        """
        if envelope.lineage_hash == "" or envelope.signature == "":
            # Envelope was not sealed before emit; treat as a P1 finding
            # rather than raising — keeps the failure shape uniform.
            return EmitOutcome.rejected_unsealed(
                claim=claim, envelope=envelope, adapter_id=self.ADAPTER_ID
            )

        return sink_emit(envelope, claim=claim, adapter_id=self.ADAPTER_ID)

    # ------------------------------------------------------------------
    # Manifest helpers — used by emit() and by subclasses
    # ------------------------------------------------------------------

    def _load_manifest(self) -> dict[str, Any]:
        """Load the adapter's manifest JSON.

        Returns an empty dict if no manifest path is declared; that's a
        valid state for adapters under active development. The substrate
        walker will emit a P3 DRIFT-SCHEMA finding for any active adapter
        without a manifest, so the gap is surfaced separately.
        """
        if self.MANIFEST_PATH is None:
            return {}
        # Real impl uses importlib.resources; skeleton omits for brevity.
        return {}

    @property
    def issuer_identity(self) -> str:
        """Manifest-declared issuer identity.

        Used by subclasses constructing envelopes; the manifest is the
        canonical source so the value is consistent across emissions.
        """
        return str(self._manifest.get("issuer_identity", ""))

    @property
    def source_system(self) -> str:
        """Manifest-declared source system identifier (`name:version`)."""
        return str(self._manifest.get("source_system", ""))

    # ------------------------------------------------------------------
    # Abstract methods — subclasses MUST implement
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def health_check(self) -> bool:
        """Lightweight liveness probe; same contract as `BaseCollector.health_check`."""
        raise NotImplementedError
