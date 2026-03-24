"""Pydantic v2 models for POA&M entities.

Defines POAMEntry, ScanFinding, RemediationMilestone, and POAMRule models
used by the rule engine, scan importer, and POA&M generator.
"""
from __future__ import annotations

import uuid as _uuid_mod
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RiskRating(str, Enum):
    """Risk / severity rating."""

    CRITICAL = "Critical"
    HIGH = "High"
    MODERATE = "Moderate"
    LOW = "Low"


class RemediationStatus(str, Enum):
    """Current remediation lifecycle status."""

    OPEN = "Open"
    IN_PROGRESS = "In-Progress"
    CLOSED = "Closed"
    DELAYED = "Delayed"


class RemediationMilestone(BaseModel):
    """A single milestone within a POA&M remediation plan."""

    description: str = ""
    due_date: date | None = None
    status: RemediationStatus = RemediationStatus.OPEN
    model_config = ConfigDict(extra="allow")


class ScanFinding(BaseModel):
    """A raw finding imported from an external scanner."""

    plugin_id: str = ""
    title: str = ""
    severity: str = ""
    host: str = ""
    description: str = ""
    recommendation: str = ""
    scan_format: str = ""  # nessus | qualys_csv | qualys_xml | json | oscal
    cve_ids: list[str] = Field(default_factory=list)
    related_controls: list[str] = Field(default_factory=list)
    raw_data: dict[str, Any] = Field(default_factory=dict)
    model_config = ConfigDict(extra="allow")


class POAMRule(BaseModel):
    """A single configurable rule that generates a POA&M finding."""

    id: str
    name: str
    description: str = ""
    condition_type: str = ""   # missing_control | low_maturity | missing_evidence | custom
    condition_value: str = ""  # value to match against
    risk_rating: RiskRating = RiskRating.MODERATE
    recommendation: str = ""
    responsible_party: str = ""
    model_config = ConfigDict(extra="allow")


class POAMEntry(BaseModel):
    """A single POA&M finding, fully populated for export."""

    uuid: str = ""
    finding_id: str = ""
    title: str = ""
    description: str = ""
    risk_rating: RiskRating = RiskRating.MODERATE
    remediation_status: RemediationStatus = RemediationStatus.OPEN
    scheduled_completion_date: date | None = None
    responsible_party: str = ""
    milestone_description: str = ""
    affected_asset: str = ""
    related_controls: list[str] = Field(default_factory=list)
    milestones: list[RemediationMilestone] = Field(default_factory=list)
    source: str = ""  # "rule_engine" | "nessus" | "qualys" | "json" | "oscal" | "manual"
    source_finding_id: str = ""
    model_config = ConfigDict(extra="allow")

    # Convenience helpers ---------------------------------------------------

    def to_oscal_item(self) -> dict[str, Any]:
        """Serialize this entry as an OSCAL POA&M item dict."""
        props: list[dict[str, str]] = [
            {"uuid": str(_uuid_mod.uuid4()), "name": "risk-rating", "value": self.risk_rating.value},
            {"uuid": str(_uuid_mod.uuid4()), "name": "finding-id", "value": self.finding_id},
            {"uuid": str(_uuid_mod.uuid4()), "name": "remediation-status", "value": self.remediation_status.value},
        ]
        if self.responsible_party:
            props.append({"uuid": str(_uuid_mod.uuid4()), "name": "responsible-party", "value": self.responsible_party})
        if self.affected_asset:
            props.append({"uuid": str(_uuid_mod.uuid4()), "name": "affected-asset", "value": self.affected_asset})
        if self.source:
            props.append({"uuid": str(_uuid_mod.uuid4()), "name": "source", "value": self.source})
        if self.scheduled_completion_date:
            props.append(
                {"uuid": str(_uuid_mod.uuid4()), "name": "scheduled-completion-date", "value": str(self.scheduled_completion_date)}
            )

        item: dict[str, Any] = {
            "uuid": self.uuid,
            "title": self.title,
            "description": self.description,
            "props": props,
        }
        if self.related_controls:
            item["related-observations"] = [
                {"description": f"Related NIST controls: {', '.join(self.related_controls)}"}
            ]
        if self.milestone_description:
            item["remarks"] = self.milestone_description
        return item

    def to_csv_row(self) -> dict[str, str]:
        """Serialize to a FedRAMP PMO CSV row dict."""
        return {
            "POA&M ID": self.finding_id,
            "Controls": ", ".join(self.related_controls),
            "Weakness Name": self.title,
            "Weakness Description": self.description,
            "Detection Source": self.source,
            "Asset Identifier": self.affected_asset,
            "Point of Contact": self.responsible_party,
            "Resources Required": "",
            "Scheduled Completion Date": str(self.scheduled_completion_date) if self.scheduled_completion_date else "",
            "Milestones with Completion Dates": self.milestone_description,
            "Milestone Changes": "",
            "Status Date": str(datetime.now(tz=timezone.utc).date()),
            "CVSS Score": "",
            "Risk Rating": self.risk_rating.value,
            "Remediation Status": self.remediation_status.value,
        }
