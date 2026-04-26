"""Enforcement Runtime router (UIAO_111, §3.3 surface in the Auditor API).

Endpoints:
  GET  /api/v1/enforcement/journal       — list journal entries
  POST /api/v1/enforcement/dispatch      — dispatch a context now

Reads from a configurable journal path
(``UIAO_ENFORCEMENT_JOURNAL_PATH`` env var; default
``output/enforcement/journal.jsonl``). The /dispatch endpoint actually
runs the runtime, so production deployments gate it with stricter
RBAC than read-only routes — for v1.0 that gating is the same Bearer
auth as the rest of the Auditor API; harden in a follow-up PR.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from uiao.api.routes._auth import require_auditor
from uiao.governance.enforcement import (
    EnforcementJournal,
    EnforcementRuntime,
)
from uiao.governance.epl import (
    EPLContext,
    EPLEvaluator,
    load_canonical_policies,
)

router = APIRouter()


def _journal_path() -> Path:
    return Path(
        os.environ.get(
            "UIAO_ENFORCEMENT_JOURNAL_PATH",
            "output/enforcement/journal.jsonl",
        )
    )


def _runtime() -> EnforcementRuntime:
    journal = EnforcementJournal(path=_journal_path())
    return EnforcementRuntime(
        evaluator=EPLEvaluator(policies=load_canonical_policies()),
        journal=journal,
    )


class DispatchRequest(BaseModel):
    """Request body for /api/v1/enforcement/dispatch.

    Same shape as :class:`uiao.governance.epl.EPLContext`. Returns the
    list of dispatched :class:`EnforcementAction` records (also written
    to the journal on disk).
    """

    drift_class: str = ""
    controls: list[str] = Field(default_factory=list)
    adapter_id: str = ""
    pillars: list[str] = Field(default_factory=list)
    severity: str = ""
    target: str = ""


@router.get(
    "/journal",
    summary="List enforcement journal entries (newest last)",
)
def get_journal(
    limit: int = Query(default=200, ge=1, le=10_000),
    policy_id: Optional[str] = Query(default=None),
    target: Optional[str] = Query(default=None),
    _subject: str = Depends(require_auditor),
) -> dict:
    journal = EnforcementJournal(path=_journal_path())
    records = journal.read_all()
    if policy_id:
        records = [r for r in records if r.policy_id == policy_id]
    if target:
        records = [r for r in records if r.target == target]
    sliced = records[-limit:]
    return {
        "count": len(sliced),
        "total_unfiltered": len(journal.read_all()),
        "records": [r.as_dict() for r in sliced],
    }


@router.post(
    "/dispatch",
    summary="Dispatch a context now — appends to the on-disk journal",
)
def dispatch(
    request: DispatchRequest,
    _subject: str = Depends(require_auditor),
) -> dict:
    ctx = EPLContext(
        drift_class=request.drift_class,
        controls=frozenset(request.controls),
        adapter_id=request.adapter_id,
        pillars=frozenset(request.pillars),
        severity=request.severity,
    )
    runtime = _runtime()
    actions = runtime.dispatch_context(ctx, target=request.target)
    return {
        "dispatched": len(actions),
        "actions": [a.as_dict() for a in actions],
    }
