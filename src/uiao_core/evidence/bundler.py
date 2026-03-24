"""Evidence bundler — packages EvidenceArtifacts into FedRAMP 20x ZIP bundles.

Output ZIP layout::

    <bundle_id>.zip
    ├── manifest.json            # index of all included artifacts
    ├── evidence/
    │   ├── <artifact-file>      # copied only when include_files=True
    │   └── ...
    └── oscal-back-matter.json   # OSCAL back-matter snippet ready for import
"""

from __future__ import annotations

import json
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from uiao_core.models.evidence import EvidenceArtifact, EvidenceBundle


class EvidenceBundler:
    """Package collected evidence into a machine-readable FedRAMP 20x ZIP bundle.

    Usage::

        bundler = EvidenceBundler(artifacts=artifacts, control_family="ac")
        bundle_path = bundler.write_zip("exports/evidence/ac-bundle.zip")
    """

    def __init__(
        self,
        artifacts: list[EvidenceArtifact] | None = None,
        control_family: str = "",
    ) -> None:
        self.artifacts: list[EvidenceArtifact] = artifacts or []
        self.control_family = control_family

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_manifest(self) -> dict[str, Any]:
        """Build a JSON manifest of all artifacts with metadata."""
        entries: list[dict[str, Any]] = []
        for artifact in self.artifacts:
            entries.append(
                {
                    "uuid": artifact.uuid,
                    "title": artifact.title,
                    "file_path": artifact.file_path,
                    "media_type": artifact.media_type,
                    "hash_sha256": artifact.hash_sha256,
                    "control_refs": artifact.control_refs,
                    "collector": artifact.collector,
                    "collected_at": artifact.collected_at,
                    "remote_url": artifact.remote_url,
                }
            )
        return {
            "bundle_id": str(uuid.uuid4()),
            "created_date": datetime.now(timezone.utc).isoformat(),
            "control_family": self.control_family,
            "artifact_count": len(entries),
            "artifacts": entries,
        }

    def build_bundle_model(self) -> EvidenceBundle:
        """Return an :class:`~uiao_core.models.evidence.EvidenceBundle` for this set of artifacts."""
        manifest = self.build_manifest()
        return EvidenceBundle(
            bundle_id=manifest["bundle_id"],
            created_date=manifest["created_date"],
            control_family=self.control_family,
            artifacts=self.artifacts,
            manifest=manifest,
        )

    def write_zip(
        self,
        output_path: str | Path,
        include_files: bool = False,
    ) -> Path:
        """Write a ZIP evidence bundle to *output_path*.

        Args:
            output_path:   Destination ``.zip`` file path.
            include_files: If ``True``, attempt to copy artifact files from
                           ``artifact.file_path`` into the ZIP under
                           ``evidence/``.  Files that do not exist are
                           silently skipped.

        Returns:
            Resolved :class:`~pathlib.Path` to the written ZIP file.
        """
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        manifest = self.build_manifest()

        with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            # 1. Write manifest
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))

            # 2. Optionally copy artifact files
            if include_files:
                for artifact in self.artifacts:
                    src = Path(artifact.file_path)
                    if src.exists():
                        zf.write(src, arcname=f"evidence/{src.name}")

            # 3. Write OSCAL back-matter snippet (with prop:id per UIAO-MEMORY rule)
            from uiao_core.evidence.linker import EvidenceLinker  # avoid circular at module level

            linker = EvidenceLinker(self.artifacts)
            back_matter = linker.to_oscal_back_matter()
            zf.writestr("oscal-back-matter.json", json.dumps(back_matter, indent=2))

        return out.resolve()
