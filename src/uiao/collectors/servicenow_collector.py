"""
UIAO-Core ServiceNow Collector.

Focused on evidence collection only — pulls raw records from the
ServiceNow Table API for downstream alignment by ServiceNowAdapter.

Credentials must be supplied via config dict, environment variables,
or Azure Key Vault in production. Never hardcode tokens here.

File: src/uiao/impl/collectors/servicenow_collector.py
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

import requests  # type: ignore[import-untyped]


class ServiceNowCollector:
    """
    ServiceNow Table API collector — evidence collection only.

    Default table: 'incident'. Override via fetch_relevant_records(table=...).
    Uses Bearer token auth. OAuth2 client-credentials flow recommended for prod.
    """

    DEFAULT_TABLE = "incident"
    DEFAULT_FIELDS = "sys_id,short_description,state,uiao_control_id,opened_at"
    TIMEOUT = 30  # seconds

    # ServiceNow serves federal customers from the Government Community Cloud
    # (FedRAMP High / DoD IL-4) at servicenowservices.com — a different
    # environment from the commercial cloud at service-now.com, not an alias.
    # UIAO targets GCC by default; override for a commercial instance.
    GCC_DOMAIN = "servicenowservices.com"
    COMMERCIAL_DOMAIN = "service-now.com"
    DEFAULT_DOMAIN = GCC_DOMAIN

    def __init__(
        self,
        instance: str = "",
        token: str = "",
        base_url: str = "",
    ) -> None:
        # Prefer explicit args; fall back to environment variables
        self.instance = instance or os.environ.get("SERVICENOW_INSTANCE", "your-instance")
        self._token = token or os.environ.get("SERVICENOW_TOKEN", "")
        self.base_url = self._resolve_base_url(base_url)

    def _resolve_base_url(self, base_url: str) -> str:
        """
        Resolve the instance base URL.

        Precedence: explicit ``base_url`` arg, then ``SERVICENOW_BASE_URL``,
        then ``https://{instance}.{SERVICENOW_DOMAIN or GCC_DOMAIN}``.  The
        host is never compiled in — a federal GCC tenant and a commercial
        tenant differ only by domain, and getting it wrong sends both live
        requests and evidence provenance links to the wrong cloud.
        """
        explicit = base_url or os.environ.get("SERVICENOW_BASE_URL", "")
        if explicit:
            return explicit.rstrip("/")
        domain = os.environ.get("SERVICENOW_DOMAIN", self.DEFAULT_DOMAIN)
        return f"https://{self.instance}.{domain}"

    # ------------------------------------------------------------------
    # Primary collection method
    # ------------------------------------------------------------------

    def fetch_relevant_records(
        self,
        table: str = DEFAULT_TABLE,
        sysparm_query: str = "",
        sysparm_fields: str = DEFAULT_FIELDS,
        sysparm_limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Pull records from a ServiceNow table.

        Returns raw JSON response with 'result' list.
        The adapter (ServiceNowAdapter.normalize()) converts this to claims.

        Args:
            table: ServiceNow table name (default: 'incident').
            sysparm_query: encoded sysparm_query filter string (optional).
            sysparm_fields: comma-separated field list to return.
            sysparm_limit: max records per request (default: 100).

        Returns:
            dict with 'result' key containing list of records.
        """
        if not self._token:
            # Return empty scaffold so the adapter can still be instantiated
            # without live credentials (useful for unit tests and CI)
            return {"result": [], "_meta": {"warning": "No token configured — returning empty scaffold."}}

        url = f"{self.base_url}/api/now/table/{table}"
        params: Dict[str, Any] = {
            "sysparm_fields": sysparm_fields,
            "sysparm_limit": sysparm_limit,
        }
        if sysparm_query:
            params["sysparm_query"] = sysparm_query

        response = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/json",
            },
            params=params,
            timeout=self.TIMEOUT,
        )
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]

    # ------------------------------------------------------------------
    # Write helpers — POST and PATCH via Table API
    # ------------------------------------------------------------------

    def post_record(self, table: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        POST a new record to a ServiceNow table.

        Args:
            table: ServiceNow table name (e.g. 'incident', 'change_request').
            payload: JSON-serialisable dict of field values for the new record.

        Returns:
            Parsed JSON response from ServiceNow (contains 'result' with new record).
        """
        if not self._token:
            return {
                "result": {},
                "_meta": {"warning": "No token configured — returning empty scaffold."},
            }

        url = f"{self.base_url}/api/now/table/{table}"
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.TIMEOUT,
        )
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]

    def patch_record(self, table: str, sys_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        PATCH an existing record in a ServiceNow table.

        Args:
            table: ServiceNow table name (e.g. 'incident').
            sys_id: The sys_id of the record to update.
            payload: JSON-serialisable dict of field values to update.

        Returns:
            Parsed JSON response from ServiceNow (contains 'result' with updated record).
        """
        if not self._token:
            return {
                "result": {},
                "_meta": {"warning": "No token configured — returning empty scaffold."},
            }

        url = f"{self.base_url}/api/now/table/{table}/{sys_id}"
        response = requests.patch(
            url,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.TIMEOUT,
        )
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]

    # ------------------------------------------------------------------
    # Drift comparison helper (engine handles the full diff)
    # ------------------------------------------------------------------

    def compare_for_drift(
        self,
        current: List[Dict[str, Any]],
        expected: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Return list of records that differ between current and expected states.

        Lightweight comparison by sys_id + short_description.
        The engine compares full claim sets against the YAML canon.
        """
        expected_index: Dict[str, str] = {r.get("sys_id", ""): r.get("short_description", "") for r in expected}
        drifted = []
        for record in current:
            sys_id = record.get("sys_id", "")
            if sys_id not in expected_index:
                drifted.append({**record, "_drift": "new_record"})
            elif record.get("short_description", "") != expected_index[sys_id]:
                drifted.append({**record, "_drift": "changed"})
        return drifted
