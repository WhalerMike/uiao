"""EPL router (UIAO_116, §3.5 surface in the Auditor API).

Endpoints:
  GET  /api/v1/epl/policies         — list canonical policies
  GET  /api/v1/epl/policies/{id}    — single policy
  POST /api/v1/epl/evaluate         — match a context against EPL

Read-only except for ``/evaluate``, which is also non-mutating —
running a finding through the evaluator returns matched policies
without dispatching any action. Use the enforcement router to
actually dispatch.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from uiao.api.routes._auth import require_auditor
from uiao.governance.epl import (
    EPLContext,
    EPLEvaluator,
    EPLPolicy,
    load_canonical_policies,
)

router = APIRouter()


def _policies() -> list[EPLPolicy]:
    return load_canonical_policies()


def _evaluator() -> EPLEvaluator:
    return EPLEvaluator(policies=_policies())


class EvaluateRequest(BaseModel):
    """Request body for /api/v1/epl/evaluate.

    Mirrors :class:`uiao.governance.epl.EPLContext` — every field is
    optional; empty fields are wildcards.
    """

    drift_class: str = ""
    controls: list[str] = Field(default_factory=list)
    adapter_id: str = ""
    pillars: list[str] = Field(default_factory=list)
    severity: str = ""


@router.get("/policies", summary="List canonical EPL policies")
def list_policies(_subject: str = Depends(require_auditor)) -> dict:
    policies = _policies()
    return {
        "count": len(policies),
        "policies": [p.as_dict() for p in policies],
    }


@router.get("/policies/{policy_id}", summary="Get a single EPL policy by id")
def get_policy(
    policy_id: str,
    _subject: str = Depends(require_auditor),
) -> dict:
    found: Optional[EPLPolicy] = next((p for p in _policies() if p.id == policy_id), None)
    if found is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"unknown policy '{policy_id}'",
        )
    return found.as_dict()


@router.post(
    "/evaluate",
    summary="Evaluate a context against EPL — returns matched policies (no dispatch)",
)
def evaluate(
    request: EvaluateRequest,
    _subject: str = Depends(require_auditor),
) -> dict:
    ctx = EPLContext(
        drift_class=request.drift_class,
        controls=frozenset(request.controls),
        adapter_id=request.adapter_id,
        pillars=frozenset(request.pillars),
        severity=request.severity,
    )
    matches = _evaluator().evaluate(ctx)
    return {
        "matched": len(matches),
        "matches": [m.as_dict() for m in matches],
    }
