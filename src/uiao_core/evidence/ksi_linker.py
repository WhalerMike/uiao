"""KSI Evidence Linker -- bridges KSI YAML library to OSCAL back-matter resources.

Reads enriched KSI YAML files from rules/ksi/<category>/*.yaml and converts
their evidence fields (pass_criteria, uiao_extensions, oscal_props) into
OSCAL-conformant back-matter resource elements suitable for injection into
an SSP or assessment-results document.

Integrates with the existing EvidenceLinker and EvidenceArtifact models.

Usage::

    linker = KsiEvidenceLinker(ksi_root=Path("rules/ksi"))
    linker.load_all()
    back_matter = linker.to_oscal_back_matter()
    ssp = linker.inject_into_ssp(ssp_dict)

File: src/uiao_core/evidence/ksi_linker.py
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import yaml

from uiao_core.models.evidence import EvidenceArtifact

from .linker import FEDRAMP_NS, EvidenceLinker  # noqa: F401

#: Default KSI root relative to project root
DEFAULT_KSI_ROOT = Path("rules/ksi")


class KsiEvidenceLinker:
    """Convert KSI YAML records into OSCAL back-matter resources.

    This class bridges the KSI library (rules/ksi/) and the OSCAL
    EvidenceLinker, so that every enriched KSI file produces a
    typed back-matter resource referencing its controlling NIST
    control and FedRAMP evidence type.
    """

    def __init__(
        self,
        ksi_root: Path | str = DEFAULT_KSI_ROOT,
        category_filter: list[str] | None = None,
    ) -> None:
        self.ksi_root = Path(ksi_root)
        self.category_filter = category_filter
        self._artifacts: list[EvidenceArtifact] = []
        self._linker: EvidenceLinker | None = None

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_all(self) -> int:
        """Load all KSI YAML files and build EvidenceArtifact list.

        Returns the number of KSI files successfully loaded.
        """
        loaded = 0
        for ksi_path in sorted(self.ksi_root.rglob("ksi-*.yaml")):
            category = ksi_path.parent.name
            if self.category_filter and category not in self.category_filter:
                continue
            try:
                with open(ksi_path, encoding="utf-8") as f:
                    ksi = yaml.safe_load(f)
                if isinstance(ksi, dict):
                    artifact = self._ksi_to_artifact(ksi, ksi_path, category)
                    self._artifacts.append(artifact)
                    loaded += 1
            except Exception:  # noqa: BLE001
                pass
        self._linker = EvidenceLinker(self._artifacts)
        return loaded

    def load_file(self, ksi_path: Path | str) -> EvidenceArtifact | None:
        """Load a single KSI YAML file and return its EvidenceArtifact."""
        ksi_path = Path(ksi_path)
        try:
            with open(ksi_path, encoding="utf-8") as f:
                ksi = yaml.safe_load(f)
            if isinstance(ksi, dict):
                category = ksi_path.parent.name
                artifact = self._ksi_to_artifact(ksi, ksi_path, category)
                self._artifacts.append(artifact)
                if self._linker is not None:
                    self._linker.artifacts.append(artifact)
                return artifact
        except Exception:  # noqa: BLE001
            pass
        return None

    # ------------------------------------------------------------------
    # OSCAL output
    # ------------------------------------------------------------------

    def to_oscal_back_matter(self) -> dict[str, Any]:
        """Generate OSCAL back-matter resources from loaded KSI artifacts."""
        if self._linker is None:
            self.load_all()
        assert self._linker is not None
        return self._linker.to_oscal_back_matter()

    def inject_into_ssp(self, ssp: dict[str, Any]) -> dict[str, Any]:
        """Inject KSI evidence resources into an existing OSCAL SSP dict."""
        if self._linker is None:
            self.load_all()
        assert self._linker is not None
        return self._linker.inject_into_ssp(ssp)

    def build_control_map(self) -> dict[str, Any]:
        """Return a dict mapping control_id -> list of KSI artifact titles."""
        if self._linker is None:
            self.load_all()
        assert self._linker is not None
        raw_map = self._linker.build_control_map()
        return {
            cid: [a.title for a in ev_map.artifacts]
            for cid, ev_map in raw_map.items()
        }

    def summary(self) -> dict[str, Any]:
        """Return a summary of loaded KSI artifacts for reporting."""
        categories: dict[str, int] = {}
        controls: set[str] = set()
        for artifact in self._artifacts:
            for tag in artifact.collector.split(":"):
                if tag.startswith("ksi-cat:"):
                    cat = tag[len("ksi-cat:"):]
                    categories[cat] = categories.get(cat, 0) + 1
            controls.update(c.lower() for c in artifact.control_refs)
        return {
            "total_ksis": len(self._artifacts),
            "categories": categories,
            "unique_controls": sorted(controls),
            "total_controls_covered": len(controls),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ksi_to_artifact(
        self,
        ksi: dict[str, Any],
        ksi_path: Path,
        category: str,
    ) -> EvidenceArtifact:
        """Convert a KSI YAML dict into an EvidenceArtifact."""
        ksi_id = ksi.get("id", ksi_path.stem)
        title = ksi.get("title", ksi_id)
        description = ksi.get("description", "")
        control_refs: list[str] = []
        if ksi.get("oscal_control_id"):
            control_refs.append(str(ksi["oscal_control_id"]).lower())
        if ksi.get("nist_controls"):
            for c in ksi["nist_controls"]:
                cid = str(c).lower()
                if cid not in control_refs:
                    control_refs.append(cid)
        if not control_refs:
            control_refs = [_CATEGORY_CONTROL_MAP.get(category, "ca-2")]
        remote_url = ksi.get("evidence_url", "")
        validation_type = ksi.get("validation_type", "manual")
        artifact = EvidenceArtifact(
            uuid=str(uuid.uuid5(uuid.NAMESPACE_URL, f"ksi:{ksi_id}")),
            title=f"KSI Evidence: {title}",
            description=(
                description
                or f"{ksi_id} -- {category} control evidence (validation: {validation_type})"
            ),
            file_path=str(ksi_path),
            media_type="application/yaml",
            control_refs=control_refs,
            remote_url=remote_url,
            collector=f"ksi-lib:ksi-cat:{category}",
            hash_sha256="",
        )
        return artifact


_CATEGORY_CONTROL_MAP: dict[str, str] = {
    "iam": "ac-2",
    "boundary-protection": "sc-7",
    "monitoring-logging": "au-2",
    "configuration-management": "cm-2",
    "incident-response": "ir-4",
    "risk-management": "ra-3",
    "supply-chain": "sr-3",
      }
