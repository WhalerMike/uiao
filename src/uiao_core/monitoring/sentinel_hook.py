"""Microsoft Sentinel integration stub.

Provides a webhook/API interface for receiving Sentinel alerts,
mapping alert severity to POA&M impact levels, and auto-creating
or updating POA&M entries when alerts fire.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Sentinel severity → POA&M impact level mapping
SEVERITY_TO_IMPACT: dict[str, str] = {
    "High": "high",
    "Medium": "medium",
    "Low": "low",
    "Informational": "low",
}


@dataclass
class SentinelAlert:
    """Represents a parsed Microsoft Sentinel alert."""

    alert_id: str
    title: str
    severity: str
    rule_name: str
    description: str
    entities: list[dict[str, Any]] = field(default_factory=list)
    tactics: list[str] = field(default_factory=list)
    techniques: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "sentinel"

    @property
    def impact_level(self) -> str:
        """Return POA&M impact level derived from alert severity."""
        return SEVERITY_TO_IMPACT.get(self.severity, "medium")


@dataclass
class SentinelConfig:
    """Sentinel workspace and alert-rule configuration."""

    workspace_id: str
    subscription_id: str
    resource_group: str
    alert_rules: list[str] = field(default_factory=list)
    severity_mapping: dict[str, str] = field(default_factory=lambda: dict(SEVERITY_TO_IMPACT))
    poam_auto_create: bool = True
    poam_data_path: str = "data/poam-findings.yml"

    @classmethod
    def from_yaml(cls, config_path: str | Path) -> SentinelConfig:
        """Load Sentinel configuration from YAML file."""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Sentinel config not found: {path}")
        raw = yaml.safe_load(path.read_text())
        cfg = raw.get("sentinel", raw)
        return cls(
            workspace_id=cfg.get("workspace_id", ""),
            subscription_id=cfg.get("subscription_id", ""),
            resource_group=cfg.get("resource_group", ""),
            alert_rules=cfg.get("alert_rules", []),
            severity_mapping=cfg.get("severity_mapping", dict(SEVERITY_TO_IMPACT)),
            poam_auto_create=cfg.get("poam_auto_create", True),
            poam_data_path=cfg.get("poam_data_path", "data/poam-findings.yml"),
        )


class SentinelHook:
    """Microsoft Sentinel webhook/API integration stub.

    Receives alert payloads from Sentinel (via Logic App webhook or
    Azure Function), maps them to NIST 800-53 controls via
    ``data/monitoring-sources.yml``, and optionally auto-creates or
    updates POA&M entries in ``data/poam-findings.yml``.
    """

    def __init__(
        self,
        config: SentinelConfig | None = None,
        monitoring_sources_path: str | Path = "data/monitoring-sources.yml",
    ) -> None:
        self.config = config
        self._signal_map: dict[str, dict[str, Any]] = {}
        self._load_signal_map(monitoring_sources_path)

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------

    def _load_signal_map(self, path: str | Path) -> None:
        """Build signal → control mapping from monitoring-sources.yml."""
        p = Path(path)
        if not p.exists():
            logger.warning("monitoring-sources.yml not found at %s; signal map empty", p)
            return
        raw = yaml.safe_load(p.read_text())
        for source in raw.get("monitoring_sources", []):
            for telemetry in source.get("telemetry", []):
                signal = telemetry.get("signal", "")
                if signal:
                    self._signal_map[signal] = telemetry

    # ------------------------------------------------------------------
    # Alert parsing
    # ------------------------------------------------------------------

    def parse_alert(self, payload: dict[str, Any]) -> SentinelAlert:
        """Parse a raw Sentinel alert webhook payload into a SentinelAlert.

        Supports both the native Sentinel alert schema and the simplified
        test/stub schema used in this project.
        """
        # Native Sentinel Logic App schema (AlertsV3)
        props = payload.get("properties", payload)
        return SentinelAlert(
            alert_id=str(props.get("systemAlertId", props.get("alert_id", "unknown"))),
            title=props.get("alertDisplayName", props.get("title", "Unknown Alert")),
            severity=props.get("severity", props.get("severity", "Medium")),
            rule_name=props.get("productName", props.get("rule_name", "Unknown Rule")),
            description=props.get("description", props.get("description", "")),
            entities=props.get("entities", []),
            tactics=props.get("tactics", []),
            techniques=props.get("techniques", []),
            timestamp=props.get(
                "timeGenerated",
                props.get(
                    "timestamp",
                    datetime.now(timezone.utc).isoformat(),
                ),
            ),
            source="sentinel",
        )

    def parse_alert_from_json(self, json_path: str | Path) -> SentinelAlert:
        """Load and parse a Sentinel alert payload from a JSON file."""
        path = Path(json_path)
        payload = json.loads(path.read_text())
        return self.parse_alert(payload)

    # ------------------------------------------------------------------
    # Control mapping
    # ------------------------------------------------------------------

    def map_alert_to_controls(self, alert: SentinelAlert) -> list[str]:
        """Return NIST 800-53 control IDs associated with the alert.

        Looks up the alert rule name against the signal map from
        monitoring-sources.yml.  Falls back to an empty list.
        """
        # Try direct rule-name lookup
        key = alert.rule_name.lower().replace(" ", "_")
        if key in self._signal_map:
            ctrl = self._signal_map[key].get("maps_to_control")
            return [ctrl] if ctrl else []

        # Partial match
        for signal, meta in self._signal_map.items():
            if signal in alert.title.lower() or signal in alert.description.lower():
                ctrl = meta.get("maps_to_control")
                if ctrl:
                    return [ctrl]

        return []

    # ------------------------------------------------------------------
    # POA&M integration
    # ------------------------------------------------------------------

    def build_poam_entry(self, alert: SentinelAlert, control_ids: list[str]) -> dict[str, Any]:
        """Build a POA&M finding dict from a Sentinel alert.

        Uses the UIAO-required ``POAM-UIAO-`` ID prefix and the exact
        FedRAMP POA&M status enum values: ``Open``, ``In-Progress``,
        ``Closed``.
        """
        import uuid as _uuid

        poam_id = f"POAM-UIAO-{_uuid.uuid4().hex[:8].upper()}"
        return {
            "id": poam_id,
            "title": f"[Sentinel] {alert.title}",
            "control-ids": control_ids or ["SI-4"],
            "description": alert.description or alert.title,
            "severity": alert.impact_level,
            "status": "Open",
            "remediation": "Investigate and remediate per Sentinel playbook",
            "source": f"sentinel:{alert.alert_id}",
            "detected_at": alert.timestamp,
        }

    def upsert_poam_entry(
        self,
        alert: SentinelAlert,
        poam_path: str | Path | None = None,
    ) -> dict[str, Any]:
        """Create or update a POA&M entry for the given alert.

        Reads existing findings from the YAML file, checks whether an
        entry for this alert ID already exists (by ``source`` field),
        and appends or updates accordingly.  Returns the entry dict.
        """
        p = Path(poam_path or (self.config.poam_data_path if self.config else "data/poam-findings.yml"))
        control_ids = self.map_alert_to_controls(alert)
        entry = self.build_poam_entry(alert, control_ids)

        findings: list[dict[str, Any]] = []
        if p.exists():
            findings = yaml.safe_load(p.read_text()) or []

        # Check for existing entry with same source alert ID
        source_key = entry["source"]
        updated = False
        for i, f in enumerate(findings):
            if f.get("source") == source_key:
                findings[i] = entry
                updated = True
                break

        if not updated:
            findings.append(entry)

        p.write_text(yaml.dump(findings, default_flow_style=False, allow_unicode=True))
        action = "Updated" if updated else "Created"
        logger.info("%s POA&M entry for alert %s", action, alert.alert_id)
        return entry

    # ------------------------------------------------------------------
    # Webhook handler
    # ------------------------------------------------------------------

    def handle_webhook(
        self,
        payload: dict[str, Any],
        auto_upsert_poam: bool | None = None,
    ) -> dict[str, Any]:
        """Handle an incoming Sentinel webhook payload end-to-end.

        Parses the alert, maps it to controls, optionally upserts a
        POA&M entry, and returns a result summary dict.
        """
        alert = self.parse_alert(payload)
        control_ids = self.map_alert_to_controls(alert)

        do_upsert = auto_upsert_poam
        if do_upsert is None:
            do_upsert = self.config.poam_auto_create if self.config else False

        poam_entry: dict[str, Any] | None = None
        if do_upsert:
            poam_entry = self.upsert_poam_entry(alert)

        return {
            "alert_id": alert.alert_id,
            "title": alert.title,
            "severity": alert.severity,
            "impact_level": alert.impact_level,
            "control_ids": control_ids,
            "poam_entry": poam_entry,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }
