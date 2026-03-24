"""Evidence collection framework with pluggable source connectors.

Each connector is a stub that documents the required configuration and
returns a list of :class:`~uiao_core.models.evidence.EvidenceArtifact`
objects.  Real integrations should subclass :class:`BaseCollector` and
implement :meth:`collect`.

Supported connectors (stubs):
- :class:`AzureSentinelCollector`  — Azure Sentinel / Microsoft Defender log export
- :class:`AzurePolicyCollector`    — Azure Policy compliance state export
- :class:`AWSConfigCollector`      — AWS Config snapshot import
- :class:`VulnScanCollector`       — Vulnerability scan result attachment (Nessus/Qualys)
- :class:`ManualUploadCollector`   — Manual upload registry from ``data/evidence_uploads.yaml``
"""
from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import yaml

from uiao_core.models.evidence import EvidenceArtifact

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------


class BaseCollector(ABC):
    """Abstract base for all evidence collectors."""

    #: Short identifier used in :attr:`~EvidenceArtifact.collector`.
    name: str = "base"

    @abstractmethod
    def collect(self) -> list[EvidenceArtifact]:
        """Run the collector and return a list of evidence artifacts."""

    def _make_artifact(self, **kwargs: Any) -> EvidenceArtifact:
        """Convenience factory that injects a UUID and collector name."""
        kwargs.setdefault("uuid", str(uuid.uuid4()))
        kwargs.setdefault("collector", self.name)
        return EvidenceArtifact(**kwargs)


# ---------------------------------------------------------------------------
# Azure Sentinel / Microsoft Defender
# ---------------------------------------------------------------------------


class AzureSentinelCollector(BaseCollector):
    """Stub: Export security incident logs from Azure Sentinel / Defender.

    Configuration keys (passed via ``config`` dict):
    - ``workspace_id``  — Log Analytics workspace ID
    - ``tenant_id``     — Azure AD tenant ID
    - ``client_id``     — Service principal client ID
    - ``client_secret`` — Service principal secret (use Key Vault reference)
    - ``query``         — KQL query to run against the workspace
    - ``output_dir``    — Local directory to write exported log files
    """

    name = "azure-sentinel"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config: dict[str, Any] = config or {}

    def collect(self) -> list[EvidenceArtifact]:
        """Return stub artifacts representing Azure Sentinel log exports.

        A real implementation would authenticate with ``azure-identity`` and
        call the Log Analytics Query API, then write results to
        ``config['output_dir']``.
        """
        logger.info(
            "[azure-sentinel] Stub connector called. "
            "Configure workspace_id/tenant_id/client_id/client_secret to enable real export."
        )
        artifact = self._make_artifact(
            title="Azure Sentinel Security Incident Log Export",
            description=(
                "Exported security incident and alert logs from Azure Sentinel workspace "
                f"{self.config.get('workspace_id', '<workspace_id>')}. "
                "Supports AU-2, AU-9, IR-4, SI-4 controls."
            ),
            file_path=str(
                Path(self.config.get("output_dir", "exports/evidence"))
                / "azure_sentinel_export.json"
            ),
            media_type="application/json",
            control_refs=["au-2", "au-9", "ir-4", "si-4"],
        )
        return [artifact]


# ---------------------------------------------------------------------------
# Azure Policy
# ---------------------------------------------------------------------------


class AzurePolicyCollector(BaseCollector):
    """Stub: Export Azure Policy compliance state for a subscription.

    Configuration keys:
    - ``subscription_id`` — Azure subscription ID
    - ``tenant_id``       — Azure AD tenant ID
    - ``client_id``       — Service principal client ID
    - ``client_secret``   — Service principal secret
    - ``output_dir``      — Local directory to write compliance snapshots
    """

    name = "azure-policy"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config: dict[str, Any] = config or {}

    def collect(self) -> list[EvidenceArtifact]:
        """Return stub artifacts representing Azure Policy compliance exports.

        A real implementation would call the Azure Policy Insights REST API
        (``/providers/Microsoft.PolicyInsights/policyStates/latest/queryResults``)
        and serialise the response to JSON.
        """
        logger.info(
            "[azure-policy] Stub connector called. "
            "Configure subscription_id/tenant_id/client_id/client_secret to enable real export."
        )
        artifact = self._make_artifact(
            title="Azure Policy Compliance State Snapshot",
            description=(
                "Compliance state export for Azure subscription "
                f"{self.config.get('subscription_id', '<subscription_id>')}. "
                "Supports CM-6, CM-7, SA-10 controls."
            ),
            file_path=str(
                Path(self.config.get("output_dir", "exports/evidence"))
                / "azure_policy_compliance.json"
            ),
            media_type="application/json",
            control_refs=["cm-6", "cm-7", "sa-10"],
        )
        return [artifact]


# ---------------------------------------------------------------------------
# AWS Config
# ---------------------------------------------------------------------------


class AWSConfigCollector(BaseCollector):
    """Stub: Import an AWS Config configuration snapshot.

    Configuration keys:
    - ``aws_region``         — AWS region (e.g. ``us-east-1``)
    - ``delivery_channel``   — S3 bucket name where Config delivers snapshots
    - ``snapshot_s3_key``    — S3 object key of the snapshot to import
    - ``output_dir``         — Local directory to write downloaded snapshot
    """

    name = "aws-config"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config: dict[str, Any] = config or {}

    def collect(self) -> list[EvidenceArtifact]:
        """Return stub artifacts representing an AWS Config snapshot import.

        A real implementation would use ``boto3`` to call
        ``ConfigService.deliver_config_snapshot`` and download the resulting
        snapshot file from S3.
        """
        logger.info(
            "[aws-config] Stub connector called. "
            "Configure aws_region/delivery_channel/snapshot_s3_key to enable real import."
        )
        artifact = self._make_artifact(
            title="AWS Config Configuration Snapshot",
            description=(
                "AWS Config configuration snapshot from region "
                f"{self.config.get('aws_region', '<aws_region>')}. "
                "Supports CM-8, CM-6, AC-3 controls."
            ),
            file_path=str(
                Path(self.config.get("output_dir", "exports/evidence"))
                / "aws_config_snapshot.json"
            ),
            media_type="application/json",
            control_refs=["cm-8", "cm-6", "ac-3"],
        )
        return [artifact]


# ---------------------------------------------------------------------------
# Vulnerability Scan (Nessus / Qualys)
# ---------------------------------------------------------------------------


class VulnScanCollector(BaseCollector):
    """Attach vulnerability scan result files (Nessus .nessus or Qualys XML).

    Configuration keys:
    - ``scan_files`` — list of paths to scan output files
    - ``output_dir`` — destination directory (files are copied here)
    """

    name = "vuln-scan"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config: dict[str, Any] = config or {}

    def collect(self) -> list[EvidenceArtifact]:
        """Attach existing scan result files as evidence artifacts.

        If ``scan_files`` is non-empty, each file is registered.
        Otherwise a stub placeholder is returned.
        """
        scan_files: list[str] = self.config.get("scan_files", [])
        if not scan_files:
            logger.info(
                "[vuln-scan] No scan_files configured — returning stub artifact. "
                "Set config['scan_files'] to a list of .nessus or Qualys XML paths."
            )
            return [
                self._make_artifact(
                    title="Vulnerability Scan Results (Stub)",
                    description=(
                        "Placeholder for Nessus or Qualys vulnerability scan output. "
                        "Supports RA-5, SI-2 controls."
                    ),
                    file_path="exports/evidence/vuln_scan_results.xml",
                    media_type="application/xml",
                    control_refs=["ra-5", "si-2"],
                )
            ]

        artifacts: list[EvidenceArtifact] = []
        for scan_path in scan_files:
            p = Path(scan_path)
            media = "application/xml" if p.suffix in {".xml", ".nessus"} else "application/octet-stream"
            artifacts.append(
                self._make_artifact(
                    title=f"Vulnerability Scan: {p.name}",
                    description=f"Vulnerability scan result file: {p.name}. Supports RA-5, SI-2.",
                    file_path=str(p),
                    media_type=media,
                    control_refs=["ra-5", "si-2"],
                )
            )
        return artifacts


# ---------------------------------------------------------------------------
# Manual Upload Registry
# ---------------------------------------------------------------------------


class ManualUploadCollector(BaseCollector):
    """Register manually uploaded policy documents from ``data/evidence_uploads.yaml``.

    Each entry in the YAML file should have:
    - ``title``        — human-readable title
    - ``description``  — what the document proves
    - ``file_path``    — path to the uploaded file
    - ``media_type``   — MIME type (default: application/pdf)
    - ``control_refs`` — list of NIST control IDs

    Configuration keys:
    - ``uploads_yaml`` — path to the uploads registry YAML (default: data/evidence_uploads.yaml)
    """

    name = "manual-upload"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config: dict[str, Any] = config or {}

    def collect(self) -> list[EvidenceArtifact]:
        """Load manual upload entries from the YAML registry."""
        uploads_yaml = Path(
            self.config.get("uploads_yaml", "data/evidence_uploads.yaml")
        )
        if not uploads_yaml.exists():
            logger.warning(
                "[manual-upload] Registry not found at %s — returning empty list.", uploads_yaml
            )
            return []

        with uploads_yaml.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}

        entries: list[dict[str, Any]] = data.get("uploads", [])
        artifacts: list[EvidenceArtifact] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            artifacts.append(
                self._make_artifact(
                    title=entry.get("title", "Untitled Upload"),
                    description=entry.get("description", ""),
                    file_path=entry.get("file_path", ""),
                    media_type=entry.get("media_type", "application/pdf"),
                    control_refs=entry.get("control_refs", []),
                )
            )
        logger.info("[manual-upload] Registered %d artifact(s) from %s.", len(artifacts), uploads_yaml)
        return artifacts


# ---------------------------------------------------------------------------
# Aggregate collector
# ---------------------------------------------------------------------------


class EvidenceCollector:
    """Run all configured evidence collectors and aggregate results.

    Usage::

        collector = EvidenceCollector(
            connectors=[
                ManualUploadCollector({"uploads_yaml": "data/evidence_uploads.yaml"}),
                VulnScanCollector({"scan_files": ["exports/evidence/scan.nessus"]}),
            ]
        )
        artifacts = collector.run()
    """

    def __init__(self, connectors: list[BaseCollector] | None = None) -> None:
        self.connectors: list[BaseCollector] = connectors or []

    @classmethod
    def default(
        cls,
        data_dir: str | Path = "data",
        output_dir: str | Path = "exports/evidence",
    ) -> EvidenceCollector:
        """Build a collector with default connectors using standard data paths."""
        data_path = Path(data_dir)
        return cls(
            connectors=[
                ManualUploadCollector({"uploads_yaml": str(data_path / "evidence_uploads.yaml")}),
                AzureSentinelCollector({"output_dir": str(output_dir)}),
                AzurePolicyCollector({"output_dir": str(output_dir)}),
                AWSConfigCollector({"output_dir": str(output_dir)}),
                VulnScanCollector({"output_dir": str(output_dir)}),
            ]
        )

    def run(self) -> list[EvidenceArtifact]:
        """Execute all connectors and return combined artifact list."""
        all_artifacts: list[EvidenceArtifact] = []
        for connector in self.connectors:
            try:
                results = connector.collect()
                logger.info("Connector '%s' returned %d artifact(s).", connector.name, len(results))
                all_artifacts.extend(results)
            except Exception as exc:  # noqa: BLE001
                logger.error("Connector '%s' raised an error: %s", connector.name, exc)
        return all_artifacts
