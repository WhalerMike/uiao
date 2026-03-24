"""KSI (Key Security Indicator) calculator.

Loads KSI mappings from ``data/ksi-mappings.yml`` and evaluates
compliance status for FedRAMP 20x Phase 2 continuous monitoring.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Ordered status values (ascending maturity)
KSI_STATUS_ORDER = ("Planned", "Partial", "Implemented")



class KSICalculator:
    """Calculates Key Security Indicator scores from KSI mappings data.

    Loads ``data/ksi-mappings.yml``, evaluates each KSI entry against
    its status, and returns summary metrics for the FedRAMP 20x
    continuous monitoring dashboard.
    """

    def __init__(
        self,
        ksi_mappings_path: str | Path = "data/ksi-mappings.yml",
    ) -> None:
        self._path = Path(ksi_mappings_path)
        self._mappings: list[dict[str, Any]] = []
        self._load()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load KSI mappings from YAML file."""
        if not self._path.exists():
            logger.warning("ksi-mappings.yml not found at %s; no KSIs loaded", self._path)
            return
        raw = yaml.safe_load(self._path.read_text())
        self._mappings = raw.get("ksi_mappings", []) if isinstance(raw, dict) else []

    # ------------------------------------------------------------------
    # Computation
    # ------------------------------------------------------------------

    def score(self) -> dict[str, Any]:
        """Return an aggregate KSI score dict.

        Returns a dict with keys:
          - ``total``: total number of KSIs
          - ``implemented``: count with status ``Implemented``
          - ``partial``: count with status ``Partial``
          - ``planned``: count with status ``Planned``
          - ``percentage``: float 0-100 representing overall readiness
          - ``items``: list of per-KSI dicts
        """
        implemented = 0
        partial = 0
        planned = 0
        items: list[dict[str, Any]] = []

        for ksi in self._mappings:
            status = ksi.get("status", "Planned")
            items.append(
                {
                    "ksi_id": ksi.get("ksi_id", ""),
                    "title": ksi.get("title", ""),
                    "status": status,
                    "control_ids": ksi.get("control_ids", []),
                    "evidence_source": ksi.get("evidence_source", ""),
                }
            )
            if status == "Implemented":
                implemented += 1
            elif status == "Partial":
                partial += 1
            else:
                planned += 1

        total = len(self._mappings)
        # Weight: Implemented=1.0, Partial=0.5, Planned=0.0
        weighted = implemented * 1.0 + partial * 0.5
        percentage = (weighted / total * 100) if total else 0.0

        return {
            "total": total,
            "implemented": implemented,
            "partial": partial,
            "planned": planned,
            "percentage": round(percentage, 1),
            "items": items,
        }

    def controls_covered(self) -> list[str]:
        """Return deduplicated list of NIST control IDs covered by KSIs."""
        seen: set[str] = set()
        out: list[str] = []
        for ksi in self._mappings:
            for ctrl in ksi.get("control_ids", []):
                if ctrl not in seen:
                    seen.add(ctrl)
                    out.append(ctrl)
        return out
