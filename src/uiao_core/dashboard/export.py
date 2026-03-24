"""KSI dashboard exporter.

Renders the KSI score report as a JSON or YAML artefact suitable for
FedRAMP 20x Phase 2 continuous monitoring evidence submission.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from uiao_core.dashboard.ksi import KSICalculator

logger = logging.getLogger(__name__)


class DashboardExporter:
    """Exports KSI dashboard data as JSON or YAML.

    Uses :class:`~uiao_core.dashboard.ksi.KSICalculator` to compute
    current KSI scores and writes them to the specified output path.
    """

    def __init__(
        self,
        ksi_mappings_path: str | Path = "data/ksi-mappings.yml",
    ) -> None:
        self._calculator = KSICalculator(ksi_mappings_path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_report(self) -> dict[str, Any]:
        """Assemble the full dashboard report dict."""
        score = self._calculator.score()
        now = datetime.now(timezone.utc).isoformat()
        return {
            "title": "UIAO KSI Dashboard — FedRAMP 20x Phase 2 ConMon",
            "generated_at": now,
            "oscal_version": "1.0.4",
            "fedramp_impact_level": "moderate",
            "ksi_summary": {
                "total": score["total"],
                "implemented": score["implemented"],
                "partial": score["partial"],
                "planned": score["planned"],
                "readiness_percentage": score["percentage"],
            },
            "controls_covered": self._calculator.controls_covered(),
            "ksi_items": score["items"],
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def export_json(self, output_path: str | Path) -> Path:
        """Write KSI dashboard report as JSON.

        Parameters
        ----------
        output_path:
            Destination file path (created if absent).

        Returns
        -------
        Path
            Absolute path of the written file.
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        report = self._build_report()
        path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
        logger.info("KSI dashboard exported to %s", path)
        return path

    def export_yaml(self, output_path: str | Path) -> Path:
        """Write KSI dashboard report as YAML.

        Parameters
        ----------
        output_path:
            Destination file path (created if absent).

        Returns
        -------
        Path
            Absolute path of the written file.
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        report = self._build_report()
        path.write_text(yaml.dump(report, default_flow_style=False, allow_unicode=True))
        logger.info("KSI dashboard exported to %s", path)
        return path
