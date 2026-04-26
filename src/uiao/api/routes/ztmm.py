"""ZTMM router (UIAO_120, §3.6 surface in the Auditor API).

Endpoints:
  GET /api/v1/ztmm                — full ZTMM report (all 5 pillars)
  GET /api/v1/ztmm/{pillar}       — single pillar score

Read-only. Wraps :class:`uiao.governance.ztmm.ZTMMScoreCalculator`
against canon declarations + an EvidenceGraph (when available).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from uiao.api.routes._auth import require_auditor
from uiao.governance.ztmm import (
    ZTMMPillar,
    ZTMMScoreCalculator,
    load_ztmm_declarations,
)

router = APIRouter()


CANON_REGISTRIES = (
    Path("src/uiao/canon/modernization-registry.yaml"),
    Path("src/uiao/canon/adapter-registry.yaml"),
)


def _calculator() -> ZTMMScoreCalculator:
    return ZTMMScoreCalculator(declarations=load_ztmm_declarations(CANON_REGISTRIES))


@router.get(
    "",
    summary="ZTMM report — all 5 pillars",
    response_description="ZTMMReport.as_dict() — per-pillar maturity + adapter rollups",
)
def get_ztmm_report(_subject: str = Depends(require_auditor)) -> dict:
    return _calculator().score().as_dict()


@router.get(
    "/{pillar}",
    summary="ZTMM single-pillar score",
)
def get_ztmm_pillar(pillar: str, _subject: str = Depends(require_auditor)) -> dict:
    parsed: Optional[ZTMMPillar] = ZTMMPillar.parse(pillar)
    if parsed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(f"unknown pillar '{pillar}'. Valid: identity, devices, networks, applications-and-workloads, data"),
        )
    return _calculator().score_pillar(parsed).as_dict()
