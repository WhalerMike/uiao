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

from uiao.dashboard.ksi import KSICalculator
from uiao.oscal.version import OSCAL_VERSION

logger = logging.getLogger(__name__)


class DashboardExporter:
    """Exports KSI dashboard data as JSON or YAML.

    Uses :class:`~uiao.dashboard.ksi.KSICalculator` to compute
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
            "oscal_version": OSCAL_VERSION,
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
            "external_interconnections": self._links_panel(),
        }

    @staticmethod
    def _links_panel() -> dict[str, Any]:
        """External-interconnections panel (UIAO_145 / ADR-132 Phase 2).

        Sourced from the canon link registry: every governed external
        interconnection with its agreement state, plus live gap counts
        from the link-gap detector. A registry load failure degrades to
        an explicit unavailable marker rather than sinking the KSI
        dashboard export.
        """
        try:
            from uiao.evidence.link_gaps import gap_summary, scan
            from uiao.evidence.links import cql_link_rows

            rows = cql_link_rows()
            gaps = scan()
        except (OSError, ValueError) as exc:
            return {"available": False, "reason": str(exc)}

        by_class: dict[str, int] = {}
        for row in rows:
            cls = str(row.get("counterparty_class") or "unknown")
            by_class[cls] = by_class.get(cls, 0) + 1

        return {
            "available": True,
            "source": "src/uiao/canon/link-registry.yaml (UIAO_145 / ADR-132)",
            "total_links": len(rows),
            "active_links": sum(1 for row in rows if row.get("status") == "active"),
            "by_counterparty_class": dict(sorted(by_class.items())),
            "gap_counts": gap_summary(gaps),
            "links": [
                {
                    "id": row["id"],
                    "counterparty_class": row["counterparty_class"],
                    "direction": row["direction"],
                    "ssot_stance": row["ssot_stance"],
                    "status": row["status"],
                    "agreement_type": row["agreement_type"],
                    "provenance_anchored": row["provenance_anchored"],
                    "next_review": row["next_review"],
                }
                for row in rows
            ],
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
