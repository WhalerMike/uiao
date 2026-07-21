"""OrgPath web console — Azure-Portal-style, read-only governance UI.

A server-rendered (Jinja2) web app over the OrgPath Governance Runtime
(:mod:`uiao.governance.orgpath_runtime`, UIAO_163 / UIAO_174) and the
per-facet Codebook (UIAO_151). It is **read-only** per ADR-084 §C7: it
observes the codebook, drift findings, and principal facet values, and
renders dry-run governance reports — it performs no writes to Graph/ARM.

Views (mounted under ``/orgpath`` by :func:`mount`):

* ``GET  /orgpath/``           — Drift dashboard (Azure "Overview" blade)
* ``GET  /orgpath/codebook``   — Codebook explorer (the OrgPath resource tree)
* ``GET  /orgpath/principals`` — Principal lookup (``?id=…`` resource detail)
* ``GET  /orgpath/govern``     — Run-a-governance-pass page
* ``POST /orgpath/api/govern`` — JSON: run the runtime over a posted snapshot,
  set it as the active snapshot, and return the ``GovernanceReport`` dict

Static assets (CSS/JS) are served from ``/orgpath/static`` by :func:`mount`.

The console keeps a small process-local :class:`ConsoleState` (active
snapshot + cached report). It defaults to a representative
:func:`sample_snapshot` so the UI renders meaningfully out of the box;
running a governance pass replaces the active snapshot. Wiring a live
Microsoft Graph snapshot supplier is a follow-up (it needs credentials +
network and would ship behind the same ``[api]`` extra).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from uiao.governance.orgpath_runtime import (
    GovernanceReport,
    OrgPathGovernanceRuntime,
    SnapshotError,
    snapshot_from_dict,
)
from uiao.modernization.orgtree.codebook import Codebook
from uiao.modernization.orgtree.types import PrincipalSnapshot, Snapshot

# Resolve template/static dirs relative to this module so they work from both
# an editable checkout and an installed wheel (shipped via package-data).
_WEB_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = _WEB_DIR / "templates"
STATIC_DIR = _WEB_DIR / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter()

# Left-nav blades: (key, label, href). The active key drives the highlight.
NAV: tuple[tuple[str, str, str], ...] = (
    ("dashboard", "Overview", "/orgpath/"),
    ("codebook", "Codebook", "/orgpath/codebook"),
    ("principals", "Principals", "/orgpath/principals"),
    ("govern", "Run governance", "/orgpath/govern"),
)


# ---------------------------------------------------------------------------
# Sample snapshot — representative data so the console isn't empty on boot
# ---------------------------------------------------------------------------

_CLEAN = {
    "extensionAttribute1": "NCR",
    "extensionAttribute2": "IT",
    "extensionAttribute3": "CyberOps",
    "extensionAttribute4": "Analyst",
    "extensionAttribute5": "CC-4100",
    "extensionAttribute6": "Employee",
    "extensionAttribute7": "2020-01-15",
    "extensionAttribute9": "Secret",
    "extensionAttribute10": "Standard",
}


def _attrs(**overrides: str) -> dict[str, str]:
    merged = dict(_CLEAN)
    merged.update(overrides)
    return merged


def sample_snapshot() -> Snapshot:
    """A small, representative tenant snapshot for the default console view.

    Two clean principals and two with Value drift (an unknown department and
    an unknown clearance) — enough to exercise the dashboard, principal
    lookup, and a non-halting governance pass.
    """
    return Snapshot(
        generated_at="2026-06-02T00:00:00+00:00",
        principals=(
            PrincipalSnapshot("u-1001", "user", _CLEAN),
            PrincipalSnapshot("u-1002", "user", _attrs(extensionAttribute1="EASTUS", extensionAttribute2="HR")),
            PrincipalSnapshot("u-1003", "user", _attrs(extensionAttribute2="Marketing")),
            PrincipalSnapshot("u-1004", "user", _attrs(extensionAttribute9="Cosmic")),
        ),
    )


# ---------------------------------------------------------------------------
# ConsoleState — process-local active snapshot + cached report
# ---------------------------------------------------------------------------


class ConsoleState:
    """Holds the console's active snapshot and the runtime that governs it.

    Single-process state (fine for the single-worker IIS deployment). The
    report is cached and invalidated whenever the snapshot changes.
    """

    def __init__(
        self,
        runtime: OrgPathGovernanceRuntime | None = None,
        snapshot: Snapshot | None = None,
    ) -> None:
        self.runtime = runtime or OrgPathGovernanceRuntime.with_canon_adapters()
        self._snapshot = snapshot or sample_snapshot()
        self._report: GovernanceReport | None = None

    @property
    def codebook(self) -> Codebook:
        return self.runtime.codebook

    @property
    def snapshot(self) -> Snapshot:
        return self._snapshot

    def set_snapshot(self, snapshot: Snapshot) -> None:
        self._snapshot = snapshot
        self._report = None

    @property
    def report(self) -> GovernanceReport:
        if self._report is None:
            self._report = self.runtime.govern(self._snapshot)
        return self._report


_state: ConsoleState | None = None


def get_state() -> ConsoleState:
    """Return the process-local console state, constructing it on first use."""
    global _state
    if _state is None:
        _state = ConsoleState()
    return _state


def set_state(state: ConsoleState | None) -> None:
    """Override (or reset to ``None``) the console state — used by tests."""
    global _state
    _state = state


# ---------------------------------------------------------------------------
# View helpers
# ---------------------------------------------------------------------------


def _ctx(active: str, **extra: Any) -> dict[str, Any]:
    """Build the shared template context (nav + the active blade)."""
    return {"nav": NAV, "active": active, **extra}


def _facet_status(codebook: Codebook, attribute: str, value: str) -> str:
    """Classify one principal facet value: ok | deprecated | empty | drift | reserved."""
    facet = codebook.facet_by_attribute(attribute)
    if facet is None:
        return "drift"
    if facet.kind == "reserved":
        return "reserved" if not value else "drift"
    if facet.is_active(value):
        return "ok"
    if facet.is_deprecated(value):
        return "deprecated"
    if value == "":
        return "empty"
    return "drift"


def _principal_rows(codebook: Codebook, principal: PrincipalSnapshot) -> list[dict[str, str]]:
    """Per-facet rows for the principal-detail blade, in slot order."""
    rows: list[dict[str, str]] = []
    for name, facet in codebook.facets.items():
        value = principal.attributes.get(facet.attribute, "")
        rows.append(
            {
                "facet": name,
                "attribute": facet.attribute,
                "kind": facet.kind,
                "value": value,
                "status": _facet_status(codebook, facet.attribute, value),
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request) -> HTMLResponse:
    """Drift dashboard — the Azure 'Overview' blade for OrgPath governance."""
    state = get_state()
    report = state.report
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=_ctx(
            "dashboard",
            report=report,
            severity_counts=report.severity_counts,
            findings=report.scan.findings,
            events=report.events,
        ),
    )


@router.get("/codebook", response_class=HTMLResponse)
def codebook_explorer(request: Request) -> HTMLResponse:
    """Codebook explorer — the OrgPath 'resource tree' (UIAO_151, 15 facets)."""
    codebook = get_state().codebook
    facets = list(codebook.facets.values())
    return templates.TemplateResponse(
        request=request,
        name="codebook.html",
        context=_ctx("codebook", codebook=codebook, facets=facets),
    )


@router.get("/principals", response_class=HTMLResponse)
def principals(request: Request, id: str = "") -> HTMLResponse:
    """Principal lookup — pick a principal to view its 10 facet values."""
    snapshot = get_state().snapshot
    codebook = get_state().codebook
    ids = [p.principal_id for p in snapshot.principals]
    selected = next((p for p in snapshot.principals if p.principal_id == id), None)
    rows = _principal_rows(codebook, selected) if selected else []
    not_found = bool(id) and selected is None
    return templates.TemplateResponse(
        request=request,
        name="principals.html",
        context=_ctx(
            "principals",
            ids=ids,
            query=id,
            principal=selected,
            rows=rows,
            not_found=not_found,
        ),
    )


@router.get("/govern", response_class=HTMLResponse)
def govern_page(request: Request) -> HTMLResponse:
    """Run-a-governance-pass page — paste a snapshot, run it, see the report."""
    return templates.TemplateResponse(request=request, name="govern.html", context=_ctx("govern"))


# ---------------------------------------------------------------------------
# JSON action — run the runtime over a posted snapshot (read-only / dry-run)
# ---------------------------------------------------------------------------


@router.post("/api/govern")
def run_governance(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    """Run one dry-run governance pass over the posted snapshot.

    Sets the posted snapshot as the console's active snapshot (so the
    dashboard and principal views reflect it) and returns the
    ``GovernanceReport`` as JSON. "Read-only" here means no writes to
    external systems (Graph/ARM) — the call DOES replace the
    process-global active snapshot every other console viewer renders
    (deliberate; pinned by test_orgpath_console.py). In the documented
    deployment IIS Windows Auth fronts this endpoint; anywhere the
    Python port is directly reachable, an anonymous caller can swap the
    view state (never persisted; resets on restart).
    """
    try:
        snapshot = snapshot_from_dict(payload)
    except SnapshotError as exc:
        return JSONResponse(status_code=400, content={"error": "invalid_snapshot", "message": str(exc)})
    state = get_state()
    state.set_snapshot(snapshot)
    return JSONResponse(content=state.report.to_dict())


# ---------------------------------------------------------------------------
# Wiring
# ---------------------------------------------------------------------------


def mount(app: FastAPI, *, prefix: str = "/orgpath") -> None:
    """Mount the console router + static assets onto ``app`` under ``prefix``."""
    app.include_router(router, prefix=prefix, tags=["OrgPath Console (Web UI)"])
    app.mount(f"{prefix}/static", StaticFiles(directory=str(STATIC_DIR)), name="orgpath-console-static")
