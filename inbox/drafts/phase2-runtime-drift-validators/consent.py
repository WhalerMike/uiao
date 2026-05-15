"""Typed ConsentEnvelope model — promotes `17_ConsentEnvelope.qmd` §3.

Per ADR-072 §4, this model promotes the 15-field YAML schema in
`17_ConsentEnvelope.qmd` §3 into a pydantic v2 typed contract. The
runtime AUTHZ validator (`uiao.telemetry.validators.authz_validator`)
consumes this model; the §3 enforcement rules from
`17_ConsentEnvelope.qmd` are owned by methods on this class, not
re-implemented in the validator.

This file is a DRAFT skeleton. Promotion to `src/uiao/models/consent.py`
happens when ADR-072 is ACCEPTED.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ENVELOPE_ID_PATTERN = re.compile(r"^urn:uiao:consent:[A-Za-z0-9-]+$")
CLAIM_ID_PATTERN = re.compile(r"^urn:uiao:claim:[a-z0-9-]+:[a-z0-9-]+:[A-Za-z0-9-]+$")
HEX64_PATTERN = re.compile(r"^[0-9a-f]{64}$")

PurposeCode = Literal["ELIGIBILITY", "BENEFITS", "ENFORCEMENT", "AUDIT", "RESEARCH"]
UseScope = Literal["AGENCY", "PROGRAM", "SYSTEM"]


# ---------------------------------------------------------------------------
# Component models
# ---------------------------------------------------------------------------


class PermittedUse(BaseModel):
    """One entry in `permitted_uses[]` per `17_ConsentEnvelope.qmd` §3."""

    use: str = Field(..., min_length=1, description="Use code (e.g. SECONDARY_VERIFICATION).")
    scope: UseScope = Field(..., description="Scope at which the use is permitted.")

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# ConsentEnvelope
# ---------------------------------------------------------------------------


class ConsentEnvelope(BaseModel):
    """Federated authorization & consent envelope.

    Promotes the 15-field YAML schema in `17_ConsentEnvelope.qmd` §3 into
    a pydantic v2 typed contract. The `authz_validator` consumes this
    model at adapter emit time; the §3/§5 enforcement rules
    (`is_active`, `permits`, cross-boundary countersignature requirement)
    are methods on this class so the validator never re-implements them.
    """

    envelope_id: str = Field(..., description="urn:uiao:consent:{uuid}")
    claim_id: str = Field(..., description="The claim this consent envelope governs.")
    issuing_agency: str = Field(..., min_length=1)
    receiving_agency: str = Field(..., min_length=1)
    legal_authority: str = Field(
        ...,
        min_length=1,
        description="Citation (e.g. 'IRC § 6103(d)', 'Privacy Act 5 U.S.C. § 552a').",
    )
    purpose_code: PurposeCode
    purpose_description: str = Field(..., min_length=1)
    consent_granted_by: str = Field(
        ...,
        min_length=1,
        description="Individual identity or agency officer identity granting consent.",
    )
    consent_timestamp: str = Field(..., description="ISO-8601 UTC timestamp.")
    consent_expiry: str = Field(
        ...,
        description="ISO-8601 UTC timestamp OR the literal 'SESSION' for session-bound consent.",
    )
    permitted_uses: list[PermittedUse] = Field(default_factory=list)
    prohibited_uses: list[str] = Field(
        default_factory=list,
        description="Explicit prohibitions (e.g. SECONDARY_SALE, MARKETING).",
    )
    data_minimization: bool = Field(
        default=False,
        description="True when only the minimum fields required for the purpose are transmitted.",
    )
    cross_boundary_flag: bool = Field(
        default=False,
        description="True when the transmission crosses a FedRAMP authorization boundary. Per §5 requires Canon Steward countersignature.",
    )
    mou_reference: Optional[str] = Field(
        default=None,
        description="MOU identifier when a Memorandum of Understanding governs the transmission.",
    )
    signature: str = Field(
        ...,
        description="64-char hex SHA-256 thumbprint of the issuing agency officer's mTLS certificate.",
    )

    model_config = ConfigDict(extra="forbid")

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @field_validator("envelope_id")
    @classmethod
    def _validate_envelope_id(cls, v: str) -> str:
        if not ENVELOPE_ID_PATTERN.match(v):
            raise ValueError(f"envelope_id {v!r} must be of the form urn:uiao:consent:{{uuid}}")
        return v

    @field_validator("claim_id")
    @classmethod
    def _validate_claim_id(cls, v: str) -> str:
        if not CLAIM_ID_PATTERN.match(v):
            raise ValueError(
                f"claim_id {v!r} must be of the form urn:uiao:claim:{{domain}}:{{type}}:{{uuid}}"
            )
        return v

    @field_validator("signature")
    @classmethod
    def _validate_signature(cls, v: str) -> str:
        if not HEX64_PATTERN.match(v):
            raise ValueError(f"signature must be 64-char lowercase hex, got {v!r}")
        return v

    @field_validator("consent_expiry")
    @classmethod
    def _validate_expiry(cls, v: str) -> str:
        if v == "SESSION":
            return v
        try:
            datetime.fromisoformat(v)
        except ValueError as exc:
            raise ValueError(
                f"consent_expiry must be ISO-8601 timestamp or the literal 'SESSION', got {v!r}"
            ) from exc
        return v

    # ------------------------------------------------------------------
    # §3/§5 enforcement methods — called by authz_validator
    # ------------------------------------------------------------------

    def is_active(self, *, now: Optional[datetime] = None) -> bool:
        """Return True if `consent_expiry` has not elapsed.

        SESSION-bound consent always returns True from this check — its
        expiry is enforced at session teardown, not here. ISO-8601
        expiries are compared against `now` (UTC, defaulting to current
        time).
        """
        if self.consent_expiry == "SESSION":
            return True
        now = now or datetime.now(timezone.utc)
        expiry = datetime.fromisoformat(self.consent_expiry)
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        return now < expiry

    def permits(self, *, use_code: str, scope: Optional[UseScope] = None) -> bool:
        """Return True iff `use_code` is in `permitted_uses` AND not in `prohibited_uses`.

        Prohibited beats permitted — an entry in both lists is treated
        as prohibited, per `17_ConsentEnvelope.qmd` §3 (prohibited_uses
        is the harder constraint).
        """
        if use_code in self.prohibited_uses:
            return False
        for entry in self.permitted_uses:
            if entry.use != use_code:
                continue
            if scope is None or entry.scope == scope:
                return True
        return False

    @property
    def requires_canon_steward_countersignature(self) -> bool:
        """Per §5: cross-boundary transmissions need Canon Steward countersignature.

        The authz_validator uses this to require a non-empty
        `mou_reference` on cross-boundary envelopes — the countersignature
        is recorded against an MOU, so absence of an MOU when this is
        True is itself a P1 DRIFT-AUTHZ violation.
        """
        return self.cross_boundary_flag
