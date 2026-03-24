"""OSCAL evidence linker — maps EvidenceArtifacts to OSCAL back-matter resources.

UIAO-MEMORY correction rule (2026-03-23):
  ALWAYS add prop:id on every link, generate fresh UUIDv4,
  validate against OSCAL 1.0.4 schema (matches current repo baseline).
"""
from __future__ import annotations

import uuid
from typing import Any

from uiao_core.models.evidence import EvidenceArtifact, EvidenceMap

#: FedRAMP OSCAL namespace used on all project props.
FEDRAMP_NS = "https://fedramp.gov/ns/oscal"


class EvidenceLinker:
    """Map collected EvidenceArtifacts to OSCAL back-matter resources and control links.

    OSCAL compliance rules (per UIAO-MEMORY):

    * Every back-matter resource receives a fresh UUIDv4.
    * Every ``prop`` carries its own UUIDv4 (``prop:id`` rule from UIAO-MEMORY).
    * Control references use lowercase NIST SP 800-53 Rev 5 identifiers.
    * ``rlinks`` entries carry the artifact ``media-type`` for OSCAL back-matter.

    Usage::

        linker = EvidenceLinker(artifacts)
        back_matter = linker.to_oscal_back_matter()
        # inject into an existing SSP dict
        updated_ssp = linker.inject_into_ssp(ssp_dict)
    """

    def __init__(self, artifacts: list[EvidenceArtifact] | None = None) -> None:
        self.artifacts: list[EvidenceArtifact] = artifacts or []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_control_map(self) -> dict[str, EvidenceMap]:
        """Return a mapping of ``control_id -> EvidenceMap`` from all artifacts."""
        control_map: dict[str, EvidenceMap] = {}
        for artifact in self.artifacts:
            for control_id in artifact.control_refs:
                cid = control_id.lower()
                if cid not in control_map:
                    control_map[cid] = EvidenceMap(control_id=cid)
                if artifact not in control_map[cid].artifacts:
                    control_map[cid].artifacts.append(artifact)
        return control_map

    def to_oscal_back_matter(self) -> dict[str, Any]:
        """Render artifacts as an OSCAL ``back-matter`` dict.

        Each resource contains:

        * ``uuid``        — the artifact's own UUID (UUIDv4, per UIAO-MEMORY)
        * ``title``       — human-readable title
        * ``description`` — detailed description
        * ``props``       — list of props, **each with its own uuid** (prop:id rule):

          - ``name="id"``          identifies this artifact by its UUID
          - ``name="type"``        marks the resource as FedRAMP evidence
          - ``name="control-ref"`` (one per control, each with its own uuid)

        * ``rlinks``      — one entry per artifact file/URL with ``media-type``
        """
        resources: list[dict[str, Any]] = []
        for artifact in self.artifacts:
            href = artifact.remote_url or artifact.file_path or "#"

            # --- props: UIAO-MEMORY rule — every prop gets its own UUIDv4 ---
            props: list[dict[str, Any]] = [
                {
                    "name": "id",
                    "uuid": str(uuid.uuid4()),   # prop:id — fresh UUIDv4
                    "value": artifact.uuid,
                    "ns": FEDRAMP_NS,
                },
                {
                    "name": "type",
                    "uuid": str(uuid.uuid4()),   # prop:id — fresh UUIDv4
                    "value": "evidence",
                    "ns": FEDRAMP_NS,
                },
            ]
            for control_ref in artifact.control_refs:
                props.append(
                    {
                        "name": "control-ref",
                        "uuid": str(uuid.uuid4()),   # prop:id — fresh UUIDv4 per ref
                        "value": control_ref.lower(),
                        "ns": FEDRAMP_NS,
                    }
                )

            resources.append(
                {
                    "uuid": artifact.uuid,
                    "title": artifact.title,
                    "description": artifact.description,
                    "props": props,
                    "rlinks": [
                        {
                            "href": href,
                            "media-type": artifact.media_type,
                        }
                    ],
                }
            )

        return {"resources": resources}

    def inject_into_ssp(self, ssp: dict[str, Any]) -> dict[str, Any]:
        """Add or merge back-matter evidence resources into an existing OSCAL SSP dict.

        The function operates on the inner ``system-security-plan`` key if
        present (i.e., it accepts either the raw SSP dict or the outer wrapper).

        Returns the updated SSP dict (modifies in place).
        """
        ssp_inner: dict[str, Any] = ssp.get("system-security-plan", ssp)
        back_matter: dict[str, Any] = ssp_inner.setdefault("back-matter", {"resources": []})
        existing_uuids = {r["uuid"] for r in back_matter.get("resources", [])}
        new_resources = self.to_oscal_back_matter()["resources"]
        for resource in new_resources:
            if resource["uuid"] not in existing_uuids:
                back_matter["resources"].append(resource)
                existing_uuids.add(resource["uuid"])
        return ssp
