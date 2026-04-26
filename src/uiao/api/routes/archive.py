"""Data Lake archive router (UIAO_109, §3.7 surface in the Auditor API).

Endpoints:
  GET /api/v1/archive            — list archive entries (filterable)
  GET /api/v1/archive/{run_id}/{adapter_id}   — single entry detail

Read-only against the ``UIAO_ARCHIVE_ROOT`` env var (default
``output/archive``). Surfaces :class:`uiao.storage.data_lake.ArchiveEntry`
records via :class:`ArchiveManager.query`.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from uiao.api.routes._auth import require_auditor
from uiao.storage.data_lake import ArchiveManager, FilesystemArchive

router = APIRouter()


def _manager() -> ArchiveManager:
    root = Path(os.environ.get("UIAO_ARCHIVE_ROOT", "output/archive"))
    return ArchiveManager(backend=FilesystemArchive(root=root))


@router.get(
    "",
    summary="List archive entries (filterable)",
)
def list_archive(
    adapter_id: Optional[str] = Query(default=None),
    run_id: Optional[str] = Query(default=None),
    evidence_class: Optional[str] = Query(default=None),
    _subject: str = Depends(require_auditor),
) -> dict:
    entries = _manager().query(
        adapter_id=adapter_id or "",
        run_id=run_id or "",
        evidence_class=evidence_class or "",
    )
    return {
        "count": len(entries),
        "entries": [e.as_dict() for e in entries],
    }


@router.get(
    "/{run_id}/{adapter_id}",
    summary="Get a single archive entry by (run_id, adapter_id)",
)
def get_entry(
    run_id: str,
    adapter_id: str,
    _subject: str = Depends(require_auditor),
) -> dict:
    mgr = _manager()
    entries = mgr.query(adapter_id=adapter_id, run_id=run_id)
    if not entries:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"no archive entry for run_id={run_id} adapter_id={adapter_id}",
        )
    return entries[0].as_dict()
