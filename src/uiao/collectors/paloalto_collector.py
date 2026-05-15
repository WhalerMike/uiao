"""
UIAO Palo Alto Networks Collector.

Collects raw PAN-OS XML API responses for downstream alignment by
PaloAltoAdapter. Supports mTLS authentication and falls back to an
empty-scaffold response when no API key is configured.

Credentials must be supplied via config dict or environment variables.
Never hardcode secrets here.

File: src/uiao/collectors/paloalto_collector.py
"""

from __future__ import annotations

import os
from typing import Optional, Tuple

import httpx

_EMPTY_SCAFFOLD = '<response status="success"><result></result></response>'

TIMEOUT = 30  # seconds


class PaloAltoCollector:
    """
    PAN-OS XML API collector — evidence collection only.

    Makes real HTTPS calls to the PAN-OS management plane using the
    XML API (/api/). Supports API-key authentication and mutual TLS
    (mTLS) via httpx certificate arguments.

    When no api_key is configured the collector returns an empty-scaffold
    XML response so the adapter can still be instantiated in CI/unit-test
    environments that have no live PAN-OS access.
    """

    def __init__(
        self,
        host: str = "",
        api_key: str = "",
        api_port: int = 443,
        vsys: str = "vsys1",
        tls_version: str = "TLSv1.3",
        mtls_enabled: bool = True,
        cert_path: Optional[str] = None,
        key_path: Optional[str] = None,
        verify_path: Optional[str] = None,
    ) -> None:
        # Prefer explicit args; fall back to environment variables
        self.host: str = host or os.environ.get("PANOS_HOST", "")
        self._api_key: str = api_key or os.environ.get("PANOS_API_KEY", "")
        self.api_port: int = api_port
        self.vsys: str = vsys
        self.tls_version: str = tls_version
        self.mtls_enabled: bool = mtls_enabled

        self.cert_path: Optional[str] = cert_path or os.environ.get("PANOS_CERT_PATH")
        self.key_path: Optional[str] = key_path or os.environ.get("PANOS_KEY_PATH")
        self.verify_path: Optional[str] = verify_path or os.environ.get("PANOS_VERIFY_PATH")

    # ------------------------------------------------------------------
    # Public collection methods
    # ------------------------------------------------------------------

    def fetch_running_config(self, rule_type: str) -> str:
        """Fetch the running (committed) configuration for *rule_type*.

        GETs ``/api/?type=config&action=show&key=...&xpath=...`` and returns
        the raw XML response body.

        Returns an empty-scaffold response when no api_key is configured.

        Args:
            rule_type: PAN-OS rule base name, e.g. ``"security"`` or
                ``"nat"``.  Embedded into the XPath expression.

        Returns:
            Raw XML string from the PAN-OS XML API.
        """
        if not self._api_key:
            return _EMPTY_SCAFFOLD

        xpath = (
            f"/config/devices/entry[@name='localhost.localdomain']"
            f"/vsys/entry[@name='{self.vsys}']/rulebase/{rule_type}/rules"
        )
        return self._request(
            "GET",
            {
                "type": "config",
                "action": "show",
                "key": self._api_key,
                "xpath": xpath,
            },
        )

    def fetch_candidate_config(self, rule_type: str) -> str:
        """Fetch the candidate (uncommitted) configuration for *rule_type*.

        Same shape as :meth:`fetch_running_config` but adds
        ``pending=yes`` to the query.

        Args:
            rule_type: PAN-OS rule base name.

        Returns:
            Raw XML string from the PAN-OS XML API.
        """
        if not self._api_key:
            return _EMPTY_SCAFFOLD

        xpath = (
            f"/config/devices/entry[@name='localhost.localdomain']"
            f"/vsys/entry[@name='{self.vsys}']/rulebase/{rule_type}/rules"
        )
        return self._request(
            "GET",
            {
                "type": "config",
                "action": "show",
                "pending": "yes",
                "key": self._api_key,
                "xpath": xpath,
            },
        )

    def post_config_edit(self, xpath: str, element: str) -> str:
        """POST a configuration edit to the PAN-OS XML API.

        Uses ``type=config&action=edit`` with the supplied XPath and XML
        element payload.  The change is staged in the candidate configuration
        and must be committed via :meth:`post_commit` to take effect.

        Args:
            xpath:   XPath addressing the configuration node to edit.
            element: XML fragment that replaces the addressed node.

        Returns:
            Raw XML response body from the PAN-OS XML API.
        """
        return self._request(
            "POST",
            {
                "type": "config",
                "action": "edit",
                "key": self._api_key,
                "xpath": xpath,
                "element": element,
            },
        )

    def post_commit(self, description: str = "") -> str:
        """Commit the candidate configuration on the firewall.

        Issues a ``type=commit`` operation.  Without a preceding edit this
        is a no-op on PAN-OS (the device reports "no changes").

        Args:
            description: Human-readable commit description embedded in the
                commit command XML.

        Returns:
            Raw XML response body from the PAN-OS XML API.
        """
        cmd = f"<commit><description>{description}</description></commit>"
        return self._request(
            "POST",
            {
                "type": "commit",
                "cmd": cmd,
                "key": self._api_key,
            },
        )

    # ------------------------------------------------------------------
    # Internal HTTP helper
    # ------------------------------------------------------------------

    def _request(self, method: str, params: dict) -> str:  # type: ignore[type-arg]
        """Send an HTTP request to the PAN-OS XML API.

        Handles mTLS when :attr:`mtls_enabled` is ``True`` and cert/key
        paths are available.  Always enforces a :data:`TIMEOUT`-second
        timeout and calls ``raise_for_status()`` on the response.

        Args:
            method: HTTP method string — ``"GET"`` or ``"POST"``.
            params: Query-string / form parameters to pass to the API.

        Returns:
            Response body as a decoded string.
        """
        url = f"https://{self.host}:{self.api_port}/api/"

        # Build mTLS kwargs
        cert: Optional[Tuple[str, str]] = None
        verify: bool | str = True
        if self.mtls_enabled and self.cert_path and self.key_path:
            cert = (self.cert_path, self.key_path)
        if self.verify_path:
            verify = self.verify_path

        with httpx.Client(cert=cert, verify=verify, timeout=TIMEOUT) as client:
            response = client.get(url, params=params) if method.upper() == "GET" else client.post(url, data=params)

        response.raise_for_status()
        return str(response.text)
