"""OrgPath web console — the FastAPI-served, Azure-Portal-style governance UI.

Read-only (ADR-084 §C7) server-rendered console over the OrgPath Governance
Runtime (UIAO_163 / UIAO_174) and the per-facet Codebook (UIAO_151). See
:mod:`uiao.api.web.console` for the router and :func:`uiao.api.web.console.mount`
for wiring into the API app.
"""

from uiao.api.web.console import mount, router

__all__ = ["mount", "router"]
