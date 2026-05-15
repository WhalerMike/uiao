"""Runtime provenance envelope — typed contract per ADR-070.

Promotes the prose envelope defined in `docs/docs/15_ProvenanceProfile.qmd`
§3 into a first-class pydantic v2 model. Adapter code constructs an
`Envelope` and passes it to `BaseAdapter.emit()`; the model carries the
deterministic lineage-hash computation and the telemetry-event projection
so adapter authors don't reimplement either.

Phase 0 ships the model and schema only. Phase 1 wires `Envelope` into
`BaseAdapter.emit()` and the `uiao.telemetry.provenance` sink. Phase 2
adds the three inline runtime drift checks (semantic / authz / identity)
that consume this envelope at emission.

This file is a DRAFT skeleton — method bodies are documented but not
fully implemented. Promotion to `src/uiao/models/provenance.py` happens
when the ADR is ACCEPTED.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION: Literal["1.0"] = "1.0"

CLAIM_ID_PATTERN = re.compile(r"^urn:uiao:claim:[a-z0-9-]+:[a-z0-9-]+:[A-Za-z0-9-]+$")
SOURCE_SYSTEM_PATTERN = re.compile(r"^[A-Za-z0-9._-]+:[A-Za-z0-9._-]+$")
HEX64_PATTERN = re.compile(r"^[0-9a-f]{64}$")

SourceClassification = Literal["authoritative", "derived", "synthesized"]
ExtractionMethod = Literal["api", "batch", "stream", "manual"]


# ---------------------------------------------------------------------------
# Component models
# ---------------------------------------------------------------------------


class TransformationStep(BaseModel):
    """One step in the transformation chain.

    Per ADR-070 and 15_ProvenanceProfile §5: steps may not be removed or
    reordered after sealing. The `step` field is the authoritative ordinal;
    list position is informative only.
    """

    step: int = Field(..., ge=1, description="1-based ordinal position; strictly increasing.")
    transform: str = Field(..., min_length=1, description="Canonical transform name.")
    applied_by: str = Field(..., min_length=1, description="Adapter ID that applied this transform.")
    applied_at: str = Field(..., description="ISO-8601 UTC timestamp of transform application.")

    model_config = ConfigDict(extra="forbid")


class ConsentEnvelopeRef(BaseModel):
    """Reference to a consent record that gates this claim.

    Optional — absent when the claim is not under consent governance.
    Validated against `17_ConsentEnvelope.qmd` at adapter emit (Phase 2).
    """

    consent_id: str = Field(..., min_length=1, description="URI of the consent record.")
    scope: list[str] = Field(default_factory=list, description="Authorized claim destinations.")

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Envelope
# ---------------------------------------------------------------------------


class Envelope(BaseModel):
    """Runtime provenance envelope.

    Every canonical claim emitted by a UIAO adapter MUST carry exactly one
    `Envelope` instance. The adapter's emit() pipeline validates this
    envelope inline per ADR-070; non-conforming envelopes are rejected
    with a P1 DRIFT-PROVENANCE finding before the claim reaches the
    telemetry sink.
    """

    claim_id: str = Field(..., description="urn:uiao:claim:{domain}:{claim_type}:{uuid}")
    issuer_identity: str = Field(..., min_length=1)
    source_system: str = Field(..., description="{system_name}:{version}")
    source_classification: SourceClassification
    extraction_timestamp: str
    extraction_method: ExtractionMethod
    transformation_chain: list[TransformationStep] = Field(default_factory=list)
    lineage_hash: str = Field(default="", description="64-char hex SHA-256; populated by seal().")
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    signature: str = Field(default="", description="64-char hex mTLS thumbprint; populated by seal().")
    consent_envelope: Optional[ConsentEnvelopeRef] = None

    model_config = ConfigDict(extra="forbid")

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @field_validator("claim_id")
    @classmethod
    def _validate_claim_id(cls, v: str) -> str:
        if not CLAIM_ID_PATTERN.match(v):
            raise ValueError(
                f"claim_id {v!r} does not match urn:uiao:claim:{{domain}}:{{claim_type}}:{{uuid}}"
            )
        return v

    @field_validator("source_system")
    @classmethod
    def _validate_source_system(cls, v: str) -> str:
        if not SOURCE_SYSTEM_PATTERN.match(v):
            raise ValueError(f"source_system {v!r} must be of the form {{system_name}}:{{version}}")
        return v

    @field_validator("lineage_hash", "signature")
    @classmethod
    def _validate_hex64_optional(cls, v: str) -> str:
        # Allow empty during construction; seal() populates before emit().
        if v == "":
            return v
        if not HEX64_PATTERN.match(v):
            raise ValueError(f"expected 64-character lowercase hex, got {v!r}")
        return v

    @field_validator("transformation_chain")
    @classmethod
    def _validate_chain_monotonic(cls, v: list[TransformationStep]) -> list[TransformationStep]:
        for expected, step in enumerate(v, start=1):
            if step.step != expected:
                raise ValueError(
                    f"transformation_chain step ordinals must be strictly increasing from 1; "
                    f"position {expected} carries step={step.step}"
                )
        return v

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def for_claim(
        cls,
        *,
        claim_id: str,
        issuer_identity: str,
        source_system: str,
        source_classification: SourceClassification = "authoritative",
        extraction_method: ExtractionMethod = "api",
        transformation_chain: Optional[list[TransformationStep]] = None,
        consent_envelope: Optional[ConsentEnvelopeRef] = None,
    ) -> "Envelope":
        """Construct an unsealed envelope with sensible defaults.

        The returned envelope has empty `lineage_hash` and `signature`;
        call `seal()` before passing it to `BaseAdapter.emit()`.
        """
        return cls(
            claim_id=claim_id,
            issuer_identity=issuer_identity,
            source_system=source_system,
            source_classification=source_classification,
            extraction_timestamp=datetime.now(timezone.utc).isoformat(),
            extraction_method=extraction_method,
            transformation_chain=transformation_chain or [],
            consent_envelope=consent_envelope,
        )

    # ------------------------------------------------------------------
    # Seal / verify
    # ------------------------------------------------------------------

    def seal(self, *, source_record: Any, mtls_thumbprint: str) -> "Envelope":
        """Populate `lineage_hash` and `signature`.

        The lineage hash is the SHA-256 of the canonical-JSON serialization
        of the source record at extraction time. Sorted keys + no
        whitespace gives a deterministic byte sequence across Python
        versions and OSes; matches the canonicalization used by the OSCAL
        evidence bundle hasher in `models/evidence.py`.

        After `seal()`, the envelope is immutable from the adapter's
        perspective — re-serializing and re-hashing the same source
        record on the verification side must produce the same digest.
        """
        canonical = json.dumps(source_record, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return self.model_copy(
            update={
                "lineage_hash": hashlib.sha256(canonical).hexdigest(),
                "signature": mtls_thumbprint,
            }
        )

    def verify_chain(self, *, source_record: Any) -> bool:
        """Re-hash a candidate source record and compare to lineage_hash.

        Used by the async chain-verification path at telemetry emit time.
        Returns True on match, False on mismatch. A False return MUST
        produce a `DRIFT-PROVENANCE` P2 finding via the remediation
        contract; the original emission is not rolled back (per ADR-009
        drift-ledger immutability).
        """
        canonical = json.dumps(source_record, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest() == self.lineage_hash

    # ------------------------------------------------------------------
    # Telemetry projection
    # ------------------------------------------------------------------

    def to_telemetry_event(self, *, event_type: Literal["accept", "reject", "chain_break"]) -> dict[str, Any]:
        """Project the envelope into a `uiao.provenance.{event_type}` event.

        Consumed by `uiao.telemetry.provenance` in Phase 1. The event shape
        is intentionally flat — every adapter emits the same fields, so
        SIEM ingestion does not need adapter-specific parsing.
        """
        return {
            "event": f"uiao.provenance.{event_type}",
            "claim_id": self.claim_id,
            "issuer_identity": self.issuer_identity,
            "source_system": self.source_system,
            "source_classification": self.source_classification,
            "extraction_timestamp": self.extraction_timestamp,
            "lineage_hash": self.lineage_hash,
            "signature": self.signature,
            "schema_version": self.schema_version,
            "emitted_at": datetime.now(timezone.utc).isoformat(),
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def new_claim_id(*, domain: str, claim_type: str) -> str:
    """Mint a fresh claim_id of the canonical urn:uiao:claim:* shape.

    Adapter authors typically call this once per source record and pass
    the result to `Envelope.for_claim(claim_id=...)`. Re-emitting the
    same logical claim MUST reuse the original claim_id, not mint a new
    one (per ADR-005).
    """
    return f"urn:uiao:claim:{domain}:{claim_type}:{uuid.uuid4()}"
