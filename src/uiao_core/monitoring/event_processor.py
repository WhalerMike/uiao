"""Event-driven gap detection processor.

Accepts events from Sentinel, Defender, or generic webhooks,
evaluates them against control requirements loaded from
``data/monitoring-sources.yml``, and generates findings when
events indicate control failures.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Supported event sources
KNOWN_SOURCES = frozenset({"sentinel", "defender", "generic"})


@dataclass
class IncomingEvent:
    """Normalized representation of an incoming security event."""

    event_id: str
    source: str
    signal: str
    severity: str
    title: str
    description: str
    raw_payload: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class Finding:
    """A control-failure finding produced by the EventProcessor."""

    event_id: str
    signal: str
    control_id: str
    title: str
    description: str
    severity: str
    source: str
    detected_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_poam_dict(self) -> dict[str, Any]:
        """Convert this finding to a POA&M entry dict.

        Uses the UIAO-required ``POAM-UIAO-`` ID prefix and the exact
        FedRAMP POA&M status enum values: ``Open``, ``In-Progress``,
        ``Closed``.
        """
        import uuid as _uuid

        poam_id = f"POAM-UIAO-{_uuid.uuid4().hex[:8].upper()}"
        return {
            "id": poam_id,
            "title": f"[{self.source.upper()}] {self.title}",
            "control-ids": [self.control_id],
            "description": self.description,
            "severity": self.severity,
            "status": "Open",
            "remediation": "Investigate and remediate per incident response procedure",
            "source": f"{self.source}:{self.event_id}",
            "detected_at": self.detected_at,
        }


class EventProcessor:
    """Evaluates incoming security events against control requirements.

    Loads the signal→control mapping from ``data/monitoring-sources.yml``
    and generates :class:`Finding` objects when events indicate that a
    control requirement has failed or is at risk.
    """

    def __init__(
        self,
        monitoring_sources_path: str | Path = "data/monitoring-sources.yml",
    ) -> None:
        self._signal_map: dict[str, dict[str, Any]] = {}
        self._load_signal_map(monitoring_sources_path)

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------

    def _load_signal_map(self, path: str | Path) -> None:
        """Build signal → control/description mapping."""
        p = Path(path)
        if not p.exists():
            logger.warning(
                "monitoring-sources.yml not found at %s; signal map empty", p
            )
            return
        raw = yaml.safe_load(p.read_text())
        for source in raw.get("monitoring_sources", []):
            for telemetry in source.get("telemetry", []):
                signal = telemetry.get("signal", "")
                if signal:
                    self._signal_map[signal] = telemetry

    # ------------------------------------------------------------------
    # Event normalisation
    # ------------------------------------------------------------------

    def normalise_event(
        self, payload: dict[str, Any], source: str = "generic"
    ) -> IncomingEvent:
        """Normalise a raw webhook payload into an IncomingEvent.

        Supports Sentinel, Defender, and generic schemas.
        """
        source = source.lower()

        if source == "sentinel":
            props = payload.get("properties", payload)
            return IncomingEvent(
                event_id=str(
                    props.get("systemAlertId", props.get("alert_id", "unknown"))
                ),
                source="sentinel",
                signal=self._extract_signal(props),
                severity=props.get("severity", "Medium"),
                title=props.get(
                    "alertDisplayName", props.get("title", "Unknown")
                ),
                description=props.get("description", ""),
                raw_payload=payload,
                timestamp=props.get(
                    "timeGenerated",
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

        if source == "defender":
            return IncomingEvent(
                event_id=str(payload.get("id", "unknown")),
                source="defender",
                signal=self._extract_signal(payload),
                severity=payload.get("severity", "Medium"),
                title=payload.get("title", "Unknown"),
                description=payload.get("description", ""),
                raw_payload=payload,
                timestamp=payload.get(
                    "creationTime", datetime.now(timezone.utc).isoformat()
                ),
            )

        # generic fallback
        return IncomingEvent(
            event_id=str(payload.get("event_id", payload.get("id", "unknown"))),
            source=source,
            signal=payload.get("signal", ""),
            severity=payload.get("severity", "Medium"),
            title=payload.get("title", "Unknown Event"),
            description=payload.get("description", ""),
            raw_payload=payload,
            timestamp=payload.get(
                "timestamp", datetime.now(timezone.utc).isoformat()
            ),
        )

    def _extract_signal(self, props: dict[str, Any]) -> str:
        """Heuristically extract a signal name from alert properties."""
        # Try explicit signal field first
        if "signal" in props:
            return str(props["signal"])
        # Derive from title / rule name via signal map keys
        title_lower = props.get(
            "alertDisplayName", props.get("title", "")
        ).lower()
        for signal in self._signal_map:
            if signal in title_lower:
                return signal
        # Fall back to sanitised title
        return title_lower.replace(" ", "_")

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(self, event: IncomingEvent) -> list[Finding]:
        """Evaluate a normalised event against control requirements.

        Returns a list of :class:`Finding` objects (one per matched
        control) if the event indicates a control failure.  Returns an
        empty list if no matching control is found.
        """
        findings: list[Finding] = []
        meta = self._signal_map.get(event.signal)
        if meta:
            findings.append(
                Finding(
                    event_id=event.event_id,
                    signal=event.signal,
                    control_id=meta.get("maps_to_control", "SI-4"),
                    title=event.title or meta.get("description", event.signal),
                    description=event.description
                    or meta.get("description", "Control failure detected"),
                    severity=event.severity.lower(),
                    source=event.source,
                    detected_at=event.timestamp,
                )
            )
        else:
            # No direct match — emit a generic SI-4 finding for visibility
            if event.signal or event.title:
                logger.debug(
                    "No signal map entry for '%s'; emitting generic SI-4 finding",
                    event.signal,
                )
                findings.append(
                    Finding(
                        event_id=event.event_id,
                        signal=event.signal or "unknown",
                        control_id="SI-4",
                        title=event.title,
                        description=event.description or "Unclassified security event",
                        severity=event.severity.lower(),
                        source=event.source,
                        detected_at=event.timestamp,
                    )
                )
        return findings

    # ------------------------------------------------------------------
    # High-level processing
    # ------------------------------------------------------------------

    def process(
        self, payload: dict[str, Any], source: str = "generic"
    ) -> list[Finding]:
        """Normalise *payload* then evaluate it; return findings."""
        event = self.normalise_event(payload, source=source)
        return self.evaluate(event)
