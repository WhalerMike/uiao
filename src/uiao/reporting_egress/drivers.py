"""Destination drivers for the reporting-egress actuator (ADR-128).

Each driver knows (a) which artifact types a destination accepts and (b) how to
transmit to it. In this scaffold every driver ships ``configured = False`` — no
live government endpoint is wired. A live, approved submission against an
unconfigured driver is *blocked* by the engine, never simulated as sent.

Wiring a real endpoint (URL, credentials, mutual TLS) is a per-destination
landing task gated on security review and the boundary decision (ADR-128 §7).
"""

from __future__ import annotations

import os
import urllib.request
from abc import ABC, abstractmethod

from uiao.reporting_egress.models import Destination, Submission


class EgressDriver(ABC):
    """Base class for a destination driver."""

    destination: Destination
    #: Human-readable destination name.
    label: str = ""
    #: Artifact types this destination accepts.
    accepts: tuple[str, ...] = ()
    #: True only when a live endpoint + credentials are wired. Scaffold: False.
    configured: bool = False

    def validate(self, submission: Submission) -> list[str]:
        """Return a list of problems; empty means the submission is well-formed."""
        problems: list[str] = []
        if not submission.artifact_path.exists():
            problems.append(f"artifact not found: {submission.artifact_path}")
        if self.accepts and submission.artifact_type not in self.accepts:
            problems.append(
                f"artifact type '{submission.artifact_type}' not accepted by "
                f"{self.destination.value} (accepts: {', '.join(self.accepts)})"
            )
        return problems

    @abstractmethod
    def transmit(self, submission: Submission) -> dict:
        """Transmit to the live endpoint and return a receipt.

        Only ever called by the engine when ``configured`` is True *and* an
        approval token is present. Scaffold drivers raise, because they are
        never configured.
        """
        raise NotImplementedError


class _UnwiredDriver(EgressDriver):
    """A driver whose live endpoint is not yet wired (scaffold default)."""

    def transmit(self, submission: Submission) -> dict:  # pragma: no cover - guarded
        raise RuntimeError(f"{self.destination.value}: no live endpoint wired (configured=False); refuse to transmit.")


class CdmDriver(_UnwiredDriver):
    destination = Destination.CDM
    label = "CDM Agency Dashboard"
    accepts = ("cdm-object", "asset-inventory", "vuln-findings")


class CyberScopeDriver(_UnwiredDriver):
    destination = Destination.CYBERSCOPE
    label = "CyberScope (FISMA / OMB)"
    accepts = ("fisma-metrics", "cyberscope-xml")


class FedRampRepoDriver(_UnwiredDriver):
    destination = Destination.FEDRAMP_REPO
    label = "FedRAMP repository"
    accepts = ("oscal-ar", "oscal-bundle", "poam", "monthly-conmon")


class CisaSbomDriver(EgressDriver):
    """CISA SBOM inbox driver (BOD 26-04) — HTTP POST to a configured endpoint.

    Wired via an explicit ``endpoint`` argument or the
    ``UIAO_CISA_SBOM_ENDPOINT`` environment variable. With no endpoint set it is
    ``configured=False`` and the engine blocks any live submission — the safe
    default. This is the one destination given a real transport so the live
    ``SUBMITTED`` path can be exercised against a test server.
    """

    destination = Destination.CISA_SBOM
    label = "CISA SBOM inbox (BOD 26-04)"
    accepts = ("cyclonedx-sbom", "openvex")

    def __init__(self, endpoint: str | None = None, timeout: float = 10.0) -> None:
        self.endpoint: str = endpoint or os.environ.get("UIAO_CISA_SBOM_ENDPOINT") or ""
        self.timeout = timeout
        # Instance attribute (not a property) so it stays a plain writeable
        # bool compatible with the base class attribute (mypy-clean override).
        self.configured = bool(self.endpoint)

    def transmit(self, submission: Submission) -> dict:
        data = submission.artifact_path.read_bytes()
        req = urllib.request.Request(
            self.endpoint,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-UIAO-Artifact-Type": submission.artifact_type,
            },
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
            status = getattr(resp, "status", 200)
            body = resp.read().decode("utf-8", "replace")
        return {"status": status, "endpoint": self.endpoint, "response": body}


class CisaIncidentDriver(_UnwiredDriver):
    destination = Destination.CISA_INCIDENT
    label = "CISA incident portal"
    accepts = ("incident-report",)


_REGISTRY: dict[Destination, EgressDriver] = {
    Destination.CDM: CdmDriver(),
    Destination.CYBERSCOPE: CyberScopeDriver(),
    Destination.FEDRAMP_REPO: FedRampRepoDriver(),
    Destination.CISA_SBOM: CisaSbomDriver(),
    Destination.CISA_INCIDENT: CisaIncidentDriver(),
}


def get_driver(destination: Destination) -> EgressDriver:
    """Return the registered driver for a destination."""
    return _REGISTRY[destination]


def list_destinations() -> list[EgressDriver]:
    """Return all registered destination drivers."""
    return list(_REGISTRY.values())
