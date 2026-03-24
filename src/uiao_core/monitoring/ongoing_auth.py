"""Ongoing authorization artefact generator.

Generates OSCAL-formatted ongoing authorization (OA) evidence records
that cross-reference each monitored NIST 800-53 / FedRAMP Rev 5 control
to its telemetry evidence source, satisfying the FedRAMP 20x Phase 2
ConMon requirement for machine-readable control evidence.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class OngoingAuthGenerator:
    """Generates OSCAL-compatible ongoing authorization evidence records.

    Loads signal→control mappings from ``data/monitoring-sources.yml``
    and KSI mappings from ``data/ksi-mappings.yml``, then produces a
    JSON artefact that links every monitored control to its evidence
    source — satisfying the UIAO-MEMORY rule:
    *"ALWAYS cross-reference every monitored control to an OSCAL
    evidence record."*
    """

    def __init__(
        self,
        monitoring_sources_path: str | Path = "data/monitoring-sources.yml",
        ksi_mappings_path: str | Path = "data/ksi-mappings.yml",
    ) -> None:
        self._monitoring_path = Path(monitoring_sources_path)
        self._ksi_path = Path(ksi_mappings_path)
        self._signal_map: dict[str, dict[str, Any]] = {}
        self._ksi_map: dict[str, dict[str, Any]] = {}
        self._load_signal_map()
        self._load_ksi_map()

    # ------------------------------------------------------------------
    # Loading helpers
    # ------------------------------------------------------------------

    def _load_signal_map(self) -> None:
        """Build signal → control mapping from monitoring-sources.yml."""
        if not self._monitoring_path.exists():
            logger.warning(
                "monitoring-sources.yml not found at %s", self._monitoring_path
            )
            return
        raw = yaml.safe_load(self._monitoring_path.read_text())
        for source in raw.get("monitoring_sources", []):
            for telemetry in source.get("telemetry", []):
                signal = telemetry.get("signal", "")
                if signal:
                    self._signal_map[signal] = {
                        **telemetry,
                        "_source_name": source.get("name", ""),
                        "_source_type": source.get("type", ""),
                    }

    def _load_ksi_map(self) -> None:
        """Build KSI ID → KSI dict from ksi-mappings.yml."""
        if not self._ksi_path.exists():
            logger.warning("ksi-mappings.yml not found at %s", self._ksi_path)
            return
        raw = yaml.safe_load(self._ksi_path.read_text())
        for ksi in raw.get("ksi_mappings", []):
            kid = ksi.get("ksi_id", "")
            if kid:
                self._ksi_map[kid] = ksi

    # ------------------------------------------------------------------
    # Evidence record construction
    # ------------------------------------------------------------------

    def _build_observation(
        self,
        control_id: str,
        signal: str,
        description: str,
        evidence_source: str,
        source_system: str,
    ) -> dict[str, Any]:
        """Build a single OSCAL observation dict."""
        now = datetime.now(timezone.utc).isoformat()
        return {
            "uuid": str(uuid.uuid4()),
            "title": f"ConMon Evidence: {control_id} via {source_system}",
            "description": description,
            "props": [
                {
                    "name": "control-id",
                    "value": control_id,
                    "ns": "https://fedramp.gov/ns/oscal",
                },
                {
                    "name": "signal",
                    "value": signal,
                    "ns": "https://fedramp.gov/ns/oscal",
                },
                {
                    "name": "evidence-source",
                    "value": evidence_source,
                    "ns": "https://fedramp.gov/ns/oscal",
                },
            ],
            "methods": ["AUTOMATED"],
            "collected": now,
            "expires": None,
            "relevant-evidence": [
                {
                    "href": f"#signal:{signal}",
                    "description": f"Telemetry signal '{signal}' from {source_system}",
                    "props": [
                        {
                            "name": "prop:id",
                            "value": str(uuid.uuid4()),
                            "ns": "https://fedramp.gov/ns/oscal",
                        }
                    ],
                }
            ],
        }

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate(self) -> dict[str, Any]:
        """Generate the full ongoing-authorization evidence document.

        Returns an OSCAL-compatible dict with all control→evidence links.
        """
        now = datetime.now(timezone.utc).isoformat()
        observations: list[dict[str, Any]] = []

        # 1. From monitoring-sources signals
        for signal, meta in self._signal_map.items():
            control_id = meta.get("maps_to_control", "SI-4")
            observations.append(
                self._build_observation(
                    control_id=control_id,
                    signal=signal,
                    description=meta.get("description", f"Signal: {signal}"),
                    evidence_source=meta.get("_source_name", "Telemetry"),
                    source_system=meta.get("_source_name", "Telemetry"),
                )
            )

        # 2. From KSI mappings (additional coverage)
        seen_ksi_controls: set[str] = set()
        for ksi in self._ksi_map.values():
            for ctrl in ksi.get("control_ids", []):
                if ctrl not in seen_ksi_controls:
                    seen_ksi_controls.add(ctrl)
                    observations.append(
                        self._build_observation(
                            control_id=ctrl,
                            signal=f"ksi:{ksi.get('ksi_id', '')}",
                            description=ksi.get("description", ""),
                            evidence_source=ksi.get("evidence_source", "KSI"),
                            source_system=ksi.get("evidence_source", "KSI"),
                        )
                    )

        return {
            "ongoing-authorization": {
                "uuid": str(uuid.uuid4()),
                "metadata": {
                    "title": "UIAO Ongoing Authorization Evidence — FedRAMP 20x ConMon",
                    "published": now,
                    "last-modified": now,
                    "version": "1.0",
                    "oscal-version": "1.0.4",
                    "props": [
                        {
                            "name": "impact-level",
                            "value": "moderate",
                            "ns": "https://fedramp.gov/ns/oscal",
                        }
                    ],
                },
                "import-ssp": {"href": "../oscal/uiao-ssp-skeleton.json"},
                "observations": observations,
            }
        }

    def export(self, output_path: str | Path) -> Path:
        """Write ongoing-authorization evidence JSON to *output_path*.

        Parameters
        ----------
        output_path:
            Destination file path (parent dirs created if needed).

        Returns
        -------
        Path
            Absolute path of the written file.
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        doc = self.generate()
        path.write_text(json.dumps(doc, indent=2, ensure_ascii=False))
        logger.info("Ongoing authorization evidence exported to %s", path)
        return path
