"""Pydantic v2 models for OSCAL evidence artifacts, mappings, and bundles.

Supports FedRAMP 20x machine-readable evidence requirements.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EvidenceArtifact(BaseModel):
    """A single evidence artifact that supports one or more OSCAL controls."""

    uuid: str = Field(..., description="Unique identifier for this evidence artifact.")
    title: str = Field(..., description="Human-readable title.")
    description: str = Field(default="", description="Detailed description of what this artifact proves.")
    file_path: str = Field(default="", description="Relative or absolute path to the artifact file.")
    media_type: str = Field(default="application/octet-stream", description="MIME type of the artifact.")
    hash_sha256: str = Field(default="", description="SHA-256 hex digest of the artifact file contents.")
    control_refs: list[str] = Field(default_factory=list, description="NIST control IDs this artifact supports.")
    remote_url: str = Field(default="", description="Remote URL for artifacts hosted externally.")
    collector: str = Field(default="manual", description="Source collector that produced this artifact.")
    collected_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 timestamp when the artifact was collected.",
    )

    model_config = ConfigDict(extra="allow")

    @field_validator("hash_sha256")
    @classmethod
    def validate_hex_digest(cls, v: str) -> str:
        """Ensure sha256 is either empty or a 64-char hex string."""
        if v and len(v) != 64:
            raise ValueError(f"hash_sha256 must be a 64-character hex string, got length {len(v)}")
        return v.lower()


class EvidenceMap(BaseModel):
    """Maps a single control ID to its supporting evidence artifacts."""

    control_id: str = Field(..., description="NIST control identifier (e.g. 'ac-2').")
    artifacts: list[EvidenceArtifact] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class EvidenceBundle(BaseModel):
    """Machine-readable evidence bundle for a set of controls (FedRAMP 20x)."""

    bundle_id: str = Field(..., description="Unique bundle identifier (UUID).")
    created_date: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 creation timestamp.",
    )
    control_family: str = Field(default="", description="Control family prefix (e.g. 'ac', 'au').")
    artifacts: list[EvidenceArtifact] = Field(default_factory=list)
    manifest: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON manifest of all artifacts with file names and hashes.",
    )

    model_config = ConfigDict(extra="allow")

    def artifact_count(self) -> int:
        """Return the number of artifacts in this bundle."""
        return len(self.artifacts)
