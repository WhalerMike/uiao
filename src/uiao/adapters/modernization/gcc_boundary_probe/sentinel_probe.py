"""
src/uiao/adapters/modernization/gcc_boundary_probe/sentinel_probe.py
--------------------------------------------------------------------
GCC Boundary Probe — Sentinel / Log Analytics surface.

Companion to ``probe.py``. Where ``probe.py`` exercises the Graph and ARM
control planes to detect feature-level boundary drift, this module
exercises the *evidence-pipeline* control plane: the seven KQL queries in
``queries/`` validate whether the telemetry routing assumed by the
GCC-Moderate Boundary Assessment is actually configured in the agency's
Sentinel / Log Analytics workspace.

The seven queries are sourced from
``inbox/New_FedRAMP_Boundary/M365_GCC-Moderate_Telemetry_and_Boundary_Assessment_External_with_images.docx``
§13.3. Each maps to one of the symptoms catalogued in §10.1 of that
assessment; the aggregate scorecard reproduces §10.2.

Outputs
-------
- ``SentinelFinding`` objects (analogous to ``BoundaryFinding`` in
  ``probe.py``) with ``boundary_class="DRIFT-EVIDENCE-PIPELINE"``.
- ``DashboardCompletenessScore`` objects per data source, reproducing
  the §10.2 0-100 dashboard-completeness rubric.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx


# ----------------------------------------------------------------------
# Findings + scorecard models
# ----------------------------------------------------------------------


@dataclass
class SentinelFinding:
    """A DRIFT-EVIDENCE-PIPELINE finding from the Sentinel / KQL probe."""

    query_id: str
    symptom_id: str
    description: str
    boundary_class: str = "DRIFT-EVIDENCE-PIPELINE"
    severity: str = "P2"
    probe_timestamp: str = ""
    probe_result: str = ""
    probe_detail: str = ""
    rows_returned: int = 0
    raw_response: dict = field(default_factory=dict)

    @property
    def drift_class(self) -> str:
        return self.boundary_class

    @property
    def path(self) -> str:
        return f"sentinel-evidence/{self.query_id}"

    def as_dict(self) -> dict:
        d = {**self.__dict__, "drift_class": self.drift_class, "path": self.path}
        # Drop the raw response from the dict export - too large for findings ledger.
        d.pop("raw_response", None)
        return d


@dataclass
class DashboardCompletenessScore:
    """Per-source completeness score reproducing assessment §10.2."""

    product: str
    score: int
    primary_remaining_gap: str
    components: dict[str, float] = field(default_factory=dict)


# ----------------------------------------------------------------------
# KQL loader
# ----------------------------------------------------------------------


_QUERIES_DIR = Path(__file__).parent / "queries"


# Query id -> (filename in queries/, symptom id from §10.1, severity, description).
# Matches the README in queries/. Keeps probe-side metadata next to the query
# definition so adding a new query is a one-place edit.
QUERY_REGISTRY: dict[str, dict[str, str]] = {
    "entra-diagnostic-completeness": {
        "filename": "01-entra-diagnostic-completeness.kql",
        "symptom_id": "SYMPTOM-01",
        "severity": "P1",
        "description": (
            "Validate Entra ID diagnostic-setting completeness — non-interactive, "
            "service-principal, managed-identity sign-in tables routed to Sentinel."
        ),
    },
    "mailitemsaccessed-operationalization": {
        "filename": "02-mailitemsaccessed-operationalization.kql",
        "symptom_id": "SYMPTOM-02",
        "severity": "P1",
        "description": (
            "Validate CISA Expanded Cloud Logs operationalization — MailItemsAccessed "
            "events present in OfficeActivity over a 7-day window."
        ),
    },
    "intune-ingestion": {
        "filename": "03-intune-ingestion.kql",
        "symptom_id": "SYMPTOM-04",
        "severity": "P2",
        "description": (
            "Validate IntuneOperationalLogs ingestion — diagnostic settings configured "
            "and DCRs not over-filtering Win32-detection events."
        ),
    },
    "master-telemetry-health": {
        "filename": "04-master-telemetry-health.kql",
        "symptom_id": "SYMPTOM-06",
        "severity": "P1",
        "description": (
            "Master telemetry health check — data volume by table over 24h. Catches "
            "silent ingestion drops that would break analytic-rule joins."
        ),
    },
    "ca-evaluation-completeness": {
        "filename": "05-ca-evaluation-completeness.kql",
        "symptom_id": "SYMPTOM-05",
        "severity": "P2",
        "description": (
            "Conditional Access evaluation completeness — top 20 policies with high "
            "notApplied volume (likely scope or exclusion misconfiguration)."
        ),
    },
    "power-platform-audit": {
        "filename": "06-power-platform-audit.kql",
        "symptom_id": "SYMPTOM-07",
        "severity": "P3",
        "description": (
            "Power Platform activity in unified audit — Power Apps, Power Automate, "
            "and Power BI events present over a 30-day window."
        ),
    },
    "exchange-security-baseline": {
        "filename": "07-exchange-security-baseline.kql",
        "symptom_id": "SYMPTOM-EX",
        "severity": "P2",
        "description": (
            "Exchange security baseline — surfaces high-impact admin operations: "
            "RBAC delegation, transport rules, mailbox permissions, remote domains."
        ),
    },
}


def load_kql_query(query_id: str) -> str:
    """Return the KQL text for a registered query id."""
    if query_id not in QUERY_REGISTRY:
        raise KeyError(f"Unknown query id: {query_id}")
    path = _QUERIES_DIR / QUERY_REGISTRY[query_id]["filename"]
    return path.read_text()


# ----------------------------------------------------------------------
# Sentinel probe
# ----------------------------------------------------------------------


class SentinelProbe:
    """Executes registered KQL queries against a Log Analytics workspace.

    Parameters
    ----------
    access_token
        OAuth bearer token with ``Data.Read`` scope on
        ``https://api.loganalytics.io``.
    workspace_id
        Log Analytics workspace GUID.
    timeout
        Per-request timeout in seconds (default 30 — KQL queries can be
        slower than Graph calls).
    """

    _LA_BASE = "https://api.loganalytics.io/v1/workspaces"

    def __init__(self, access_token: str, workspace_id: str, timeout: int = 30):
        self._token = access_token
        self._workspace_id = workspace_id
        self._timeout = timeout
        self._headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    async def _execute(self, kql: str) -> tuple[int, dict]:
        url = f"{self._LA_BASE}/{self._workspace_id}/query"
        body = {"query": kql}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(url, headers=self._headers, content=json.dumps(body))
                try:
                    return resp.status_code, resp.json()
                except Exception:
                    return resp.status_code, {"raw": resp.text[:500]}
            except httpx.TimeoutException:
                return 0, {"error": "timeout"}
            except Exception as e:  # pragma: no cover - network surface
                return 0, {"error": str(e)}

    @staticmethod
    def _row_count(response: dict) -> int:
        tables = response.get("tables") or []
        if not tables:
            return 0
        return len(tables[0].get("rows") or [])

    async def run_query(self, query_id: str) -> SentinelFinding:
        """Run one registered query and return a finding.

        Probe-result vocabulary (mirrors ``probe.py``):
          ``OPERATIONAL``           Query returned >0 rows.
          ``NOT_DETECTED``          Query returned 0 rows — symptom present.
          ``QUERY_FAILED``          HTTP error or KQL parse error.
        """
        meta = QUERY_REGISTRY[query_id]
        kql = load_kql_query(query_id)
        ts = datetime.now(timezone.utc).isoformat()

        status_code, body = await self._execute(kql)

        if status_code != 200:
            return SentinelFinding(
                query_id=query_id,
                symptom_id=meta["symptom_id"],
                description=meta["description"],
                severity=meta["severity"],
                probe_timestamp=ts,
                probe_result="QUERY_FAILED",
                probe_detail=f"HTTP {status_code}: {str(body)[:200]}",
                raw_response=body,
            )

        rows = self._row_count(body)
        result = "OPERATIONAL" if rows > 0 else "NOT_DETECTED"
        detail = (
            f"{rows} rows returned"
            if rows > 0
            else f"No rows for {meta['symptom_id']} — action required"
        )
        return SentinelFinding(
            query_id=query_id,
            symptom_id=meta["symptom_id"],
            description=meta["description"],
            severity=meta["severity"],
            probe_timestamp=ts,
            probe_result=result,
            probe_detail=detail,
            rows_returned=rows,
            raw_response=body,
        )

    async def run_all(self) -> list[SentinelFinding]:
        """Execute every registered query in parallel."""
        results = await asyncio.gather(
            *(self.run_query(qid) for qid in QUERY_REGISTRY),
            return_exceptions=True,
        )
        out: list[SentinelFinding] = []
        ts = datetime.now(timezone.utc).isoformat()
        for qid, r in zip(QUERY_REGISTRY, results):
            if isinstance(r, Exception):
                meta = QUERY_REGISTRY[qid]
                out.append(
                    SentinelFinding(
                        query_id=qid,
                        symptom_id=meta["symptom_id"],
                        description=meta["description"],
                        severity=meta["severity"],
                        probe_timestamp=ts,
                        probe_result="QUERY_FAILED",
                        probe_detail=f"exception: {r!r}",
                    )
                )
            else:
                out.append(r)
        return out


# ----------------------------------------------------------------------
# Dashboard completeness scorecard — assessment §10.2
# ----------------------------------------------------------------------


# §10.2 baseline scores anchor each product in the rubric. The probe adjusts
# the score downward when the corresponding KQL query reports NOT_DETECTED.
# Source: M365 GCC-Moderate Telemetry & Boundary Assessment §10.2.
_BASELINE_SCORES: dict[str, tuple[int, str]] = {
    "Entra ID (P2)": (75, "NonInteractive, ServicePrincipal, ManagedIdentity logs not on by default"),
    "Exchange Online": (70, "MailItemsAccessed newly available in Standard, requires operationalization"),
    "SharePoint Online": (65, "SearchQueryInitiatedSharePoint requires enablement"),
    "Microsoft Teams": (55, "CQD / QER outside Sentinel; PSTN / Direct Routing telemetry incomplete"),
    "Microsoft Intune": (60, "Diagnostic settings manual; Win32-detection event volume forces aggressive filtering"),
    "Defender for Endpoint": (85, "Generally well-instrumented; some advanced tables may lag in GCC"),
    "Defender for Office 365": (80, "Some Defender XDR connector data types may have limited GCC support"),
    "Defender for Identity": (80, "On-prem sensor required; hybrid gaps"),
    "Defender for Cloud Apps": (70, "CloudAppEvents requires Purview unified audit enabled"),
    "Purview Audit": (60, "Standard 180-day cliff; Premium needed for forensic-grade depth"),
    "Microsoft Sentinel": (75, "Platform audit requires CloudAppEvents via Defender XDR connector"),
    "Power Platform (Apps / Automate / BI)": (45, "No native Sentinel connectors; relies on Purview unified audit"),
    "Dynamics 365": (40, "Heavy reliance on Application Insights; limited native security event coverage"),
    "Microsoft Stream": (25, "No native Sentinel connector"),
    "Windows Autopilot": (30, "No direct Sentinel connector; deployment telemetry siloed in Intune"),
}


# Map each registered query id to the products whose score it adjusts when
# the query reports NOT_DETECTED.
_QUERY_PRODUCT_IMPACT: dict[str, list[tuple[str, int]]] = {
    "entra-diagnostic-completeness": [("Entra ID (P2)", 25)],
    "mailitemsaccessed-operationalization": [("Exchange Online", 20)],
    "intune-ingestion": [("Microsoft Intune", 30)],
    "master-telemetry-health": [("Microsoft Sentinel", 25)],
    "ca-evaluation-completeness": [("Entra ID (P2)", 10)],
    "power-platform-audit": [("Power Platform (Apps / Automate / BI)", 20)],
    "exchange-security-baseline": [("Exchange Online", 5)],
}


def dashboard_completeness_score(
    findings: list[SentinelFinding],
) -> list[DashboardCompletenessScore]:
    """Produce the §10.2 dashboard-completeness scorecard from probe findings.

    For each product in the rubric, the baseline score is preserved if every
    query that contributes to it reports OPERATIONAL. Each NOT_DETECTED
    deducts the configured impact, floored at 0.
    """
    deductions: dict[str, int] = {p: 0 for p in _BASELINE_SCORES}
    by_id: dict[str, SentinelFinding] = {f.query_id: f for f in findings}

    for query_id, impacts in _QUERY_PRODUCT_IMPACT.items():
        f = by_id.get(query_id)
        if f is None or f.probe_result == "OPERATIONAL":
            continue
        # NOT_DETECTED or QUERY_FAILED both deduct.
        for product, deduction in impacts:
            deductions[product] += deduction

    out: list[DashboardCompletenessScore] = []
    for product, (baseline, gap) in _BASELINE_SCORES.items():
        adjusted = max(0, baseline - deductions[product])
        out.append(
            DashboardCompletenessScore(
                product=product,
                score=adjusted,
                primary_remaining_gap=gap,
                components={"baseline": baseline, "deduction": deductions[product]},
            )
        )
    return out
