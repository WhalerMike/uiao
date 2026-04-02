from __future__ import annotations

"""
KSI Validator Engine for UIAO-Core.

This module provides:
- ValidationResult dataclass
- KSIValidatorEngine for orchestrating collectors and rule evaluation
- Export helpers for OSCAL, JSON summaries, and Quarto-ready markdown
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

import yaml  # type: ignore

from ..collectors import create_collector
from ..collectors.base_collector import EvidenceObject

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """
    Result of validating a single KSI.

    Attributes
    ----------
    ksi_id:
        Identifier of the KSI.
    status:
        Validation status: 'pass', 'fail', 'error', or 'stale'.
    evidence:
        List of EvidenceObject instances (or their dict representations).
    drift_indicators:
        List of human-readable drift indicators detected during validation.
    timestamp:
        Timestamp when validation was performed.
    errors:
        List of error messages encountered during validation.
    """

    ksi_id: str
    status: str
    evidence: List[EvidenceObject] = field(default_factory=list)
    drift_indicators: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ksi_id": self.ksi_id,
            "status": self.status,
            "evidence": [e.to_dict() for e in self.evidence],
            "drift_indicators": self.drift_indicators,
            "timestamp": self.timestamp.isoformat(),
            "errors": self.errors,
        }


class KSIValidatorEngine:
    """
    KSI Validator Engine.

    Responsibilities:
    - Load KSI rule definitions from YAML files
    - Coordinate collectors based on KSI data_sources
    - Evaluate KSI pass/fail/stale/error
    - Emit OSCAL evidence bundles, JSON summaries, and Quarto markdown
    """

    # Mapping from KSI data_sources enum values to collector IDs
    DATA_SOURCE_TO_COLLECTOR_ID: Dict[str, str] = {
        "EntraID": "entra",
        "CiscoSDWAN": "sdwan",
        "InfoBlox": "infoblox",
        # Extend as additional collectors are implemented
    }

    def __init__(
        self,
        ksi_catalog: Dict[str, Dict[str, Any]],
        collector_configs: Dict[str, Dict[str, Any]],
        rules_root: str | Path = "rules",
    ) -> None:
        """
        Initialize the KSI validator engine.

        Parameters
        ----------
        ksi_catalog:
            Mapping of KSI ID -> KSI definition (as loaded from JSON/YAML
            conforming to ksi.schema.json).
        collector_configs:
            Mapping of collector_id -> configuration dict.
        rules_root:
            Root directory where KSI rule YAML files live.
        """
        self._ksi_catalog = ksi_catalog
        self._rules_root = Path(rules_root)
        self._collectors = self._init_collectors(collector_configs)
        self._results: Dict[str, ValidationResult] = {}

    # --------------------------------------------------------------------- #
    # Initialization helpers
    # --------------------------------------------------------------------- #

    def _init_collectors(self, collector_configs: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        collectors: Dict[str, Any] = {}
        for collector_id, cfg in collector_configs.items():
            try:
                collectors[collector_id] = create_collector(collector_id, cfg)
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("Failed to initialize collector %s: %s", collector_id, exc)
        return collectors

    # --------------------------------------------------------------------- #
    # Rule loading and duration parsing
    # --------------------------------------------------------------------- #

    def _load_rule(self, validation_logic_ref: str) -> Dict[str, Any]:
        """
        Load a KSI rule YAML file based on the validation_logic_ref path.

        The path is interpreted relative to rules_root.
        """
        rule_path = self._rules_root / validation_logic_ref
        with rule_path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _parse_iso8601_duration(self, duration: str) -> timedelta:
        """
        Parse a subset of ISO 8601 durations into a timedelta.

        Supported:
        - PnD
        - PTnH
        - PTnM
        - PTnS
        - Combinations like PT1H30M

        This is intentionally minimal and can be extended as needed.
        """
        if not duration.startswith("P"):
            raise ValueError(f"Invalid duration: {duration}")

        # Strip leading 'P'
        body = duration[1:]
        days = hours = minutes = seconds = 0

        if "T" in body:
            date_part, time_part = body.split("T", 1)
        else:
            date_part, time_part = body, ""

        # Days
        if date_part.endswith("D"):
            days = int(date_part[:-1]) if date_part[:-1] else 0

        # Time part
        num = ""
        for ch in time_part:
            if ch.isdigit():
                num += ch
            else:
                if ch == "H":
                    hours = int(num)
                elif ch == "M":
                    minutes = int(num)
                elif ch == "S":
                    seconds = int(num)
                num = ""

        return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)

    # --------------------------------------------------------------------- #
    # Core validation
    # --------------------------------------------------------------------- #

    def validate_ksi(self, ksi_id: str) -> ValidationResult:
        """
        Validate a single KSI.

        Steps:
        - Load KSI definition from catalog
        - Load rule YAML via validation_logic_ref
        - Resolve collectors from data_sources
        - Collect evidence
        - Evaluate rule logic and freshness_window
        - Produce ValidationResult
        """
        if ksi_id not in self._ksi_catalog:
            result = ValidationResult(
                ksi_id=ksi_id,
                status="error",
                errors=[f"KSI {ksi_id} not found in catalog"],
            )
            self._results[ksi_id] = result
            return result

        ksi_def = self._ksi_catalog[ksi_id]
        errors: List[str] = []
        evidence_list: List[EvidenceObject] = []
        drift_indicators: List[str] = []

        try:
            rule = self._load_rule(ksi_def["validation_logic_ref"])
        except Exception as exc:
            result = ValidationResult(
                ksi_id=ksi_id,
                status="error",
                errors=[f"Failed to load rule: {exc}"],
            )
            self._results[ksi_id] = result
            return result

        data_sources: List[str] = ksi_def.get("data_sources", [])
        freshness_window_str: str = ksi_def.get("freshness_window", "PT24H")
        expected_patterns: List[str] = ksi_def.get("expected_patterns", [])

        try:
            freshness_delta = self._parse_iso8601_duration(freshness_window_str)
        except Exception as exc:
            errors.append(f"Invalid freshness_window '{freshness_window_str}': {exc}")
            freshness_delta = timedelta(0)

        now = datetime.now(timezone.utc)

        # Collect evidence from all required data sources
        for ds in data_sources:
            collector_id = self.DATA_SOURCE_TO_COLLECTOR_ID.get(ds)
            if not collector_id:
                errors.append(f"No collector mapping for data source '{ds}'")
                continue

            collector = self._collectors.get(collector_id)
            if not collector:
                errors.append(f"Collector '{collector_id}' not initialized")
                continue

            try:
                ev = collector.collect(ksi_id=ksi_id)
                # Freshness check
                ev_age = now - ev.timestamp
                ev.freshness_valid = ev_age <= freshness_delta if freshness_delta > timedelta(0) else True
                evidence_list.append(ev)

                # Simple drift detection stub:
                # If normalized_data contains a key 'drift', surface it.
                if isinstance(ev.normalized_data, dict) and ev.normalized_data.get("drift"):
                    drift_indicators.append(f"Drift detected by {collector_id}: {ev.normalized_data['drift']}")
            except Exception as exc:  # pragma: no cover - defensive
                errors.append(f"Collector '{collector_id}' failed: {exc}")

        # Evaluate rule logic (stubbed)
        status = self._evaluate_rule(
            ksi_id=ksi_id,
            rule=rule,
            evidence=evidence_list,
            expected_patterns=expected_patterns,
            freshness_delta=freshness_delta,
            now=now,
        )

        # If any evidence is stale and status is still 'pass', downgrade to 'stale'
        if status == "pass" and any(not ev.freshness_valid for ev in evidence_list):
            status = "stale"

        if errors and status == "pass":
            status = "error"

        result = ValidationResult(
            ksi_id=ksi_id,
            status=status,
            evidence=evidence_list,
            drift_indicators=drift_indicators,
            errors=errors,
        )
        self._results[ksi_id] = result
        return result

    def _evaluate_rule(
        self,
        ksi_id: str,
        rule: Dict[str, Any],
        evidence: List[EvidenceObject],
        expected_patterns: List[str],
        freshness_delta: timedelta,
        now: datetime,
    ) -> str:
        """
        Evaluate rule logic for a KSI.

        This is a deliberately minimal placeholder that can be extended to
        support a richer DSL. For now, it:
        - Requires at least one evidence object
        - Requires all evidence to be within freshness_window (if > 0)
        - Optionally checks for simple pattern hints in normalized_data
        """
        if not evidence:
            return "error"

        # Freshness check
        if freshness_delta > timedelta(0):
            if any((now - ev.timestamp) > freshness_delta for ev in evidence):
                return "stale"

        # Simple pattern check stub:
        # If expected_patterns are defined, we just ensure we have normalized_data
        # present for each evidence object. Real logic would inspect fields.
        if expected_patterns:
            if not all(ev.normalized_data is not None for ev in evidence):
                return "fail"

        # Placeholder for rule["logic"] evaluation
        logic = rule.get("logic", {})
        if logic.get("type") == "all_of":
            # In a real implementation, iterate conditions and evaluate against evidence
            # Here we assume success if we reached this point.
            return "pass"
        elif logic.get("type") == "any_of":
            return "pass"
        else:
            # Unknown logic type; treat as error
            return "error"

    # --------------------------------------------------------------------- #
    # Bulk validation
    # --------------------------------------------------------------------- #

    def validate_all(self) -> Dict[str, ValidationResult]:
        """
        Validate all KSIs in the catalog.

        Returns
        -------
        Dict[str, ValidationResult]
            Mapping of KSI ID -> ValidationResult.
        """
        for ksi_id in self._ksi_catalog.keys():
            self.validate_ksi(ksi_id)
        return self._results

    # --------------------------------------------------------------------- #
    # Export helpers
    # --------------------------------------------------------------------- #

    def export_oscal(self) -> Dict[str, Any]:
        """
        Export validation results as an OSCAL-like evidence bundle.

        This is a simplified representation that can be adapted to full OSCAL
        assessment-results or observations as needed.
        """
        observations = []
        for res in self._results.values():
            for ev in res.evidence:
                observations.append(
                    {
                        "id": f"obs-{res.ksi_id}",
                        "title": f"KSI {res.ksi_id} validation",
                        "description": f"Validation result for KSI {res.ksi_id}",
                        "props": [
                            {"name": "status", "value": res.status},
                            {"name": "collector_id", "value": ev.provenance.collector_id},
                        ],
                        "collected": ev.timestamp.isoformat(),
                        "remarks": "; ".join(res.drift_indicators) if res.drift_indicators else "",
                    }
                )

        bundle = {
            "uiao_ksi_evidence_bundle": {
                "generated": datetime.now(timezone.utc).isoformat(),
                "observations": observations,
            }
        }
        return bundle

    def export_summary(self) -> Dict[str, Any]:
        """
        Export a JSON validation summary.

        Returns
        -------
        Dict[str, Any]
            Summary including per-KSI status and errors.
        """
        return {
            "generated": datetime.now(timezone.utc).isoformat(),
            "results": {k: v.to_dict() for k, v in self._results.items()},
        }

    def export_quarto(self) -> str:
        """
        Export a Quarto-ready markdown fragment summarizing KSI validation.

        Returns
        -------
        str
            Markdown table with KSI status and drift indicators.
        """
        lines: List[str] = []
        lines.append("## UIAO KSI Validation Summary")
        lines.append("")
        lines.append("| KSI ID | Status | Drift | Errors |")
        lines.append("|--------|--------|-------|--------|")

        for ksi_id, res in sorted(self._results.items()):
            drift = "<br>".join(res.drift_indicators) if res.drift_indicators else ""
            errors = "<br>".join(res.errors) if res.errors else ""
            lines.append(f"| {ksi_id} | {res.status} | {drift} | {errors} |")

        lines.append("")
        return "\n".join(lines)
