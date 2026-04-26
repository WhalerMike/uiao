"""CQL router (UIAO_108, §3.2 surface in the Auditor API).

Endpoints:
  GET  /api/v1/cql/queries           — list canonical queries
  GET  /api/v1/cql/queries/{name}    — fetch a parsed canonical query
  POST /api/v1/cql/evaluate          — evaluate an ad-hoc query
  POST /api/v1/cql/evaluate/{name}   — evaluate a canonical query

All endpoints are read-only against in-memory views of the live
substrate state (graph + journal + archive + canon registries).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from fastapi import APIRouter, Body, Depends, HTTPException, status

from uiao.api.routes._auth import require_auditor
from uiao.governance.cql import (
    CQLEvaluator,
    CQLParseError,
    CQLQuery,
    adapters_resolver,
    journal_records_resolver,
    load_canonical_queries,
    make_default_resolver,
    parse_query,
)
from uiao.governance.enforcement import EnforcementJournal
from uiao.storage.data_lake import ArchiveManager, FilesystemArchive

router = APIRouter()


CANON_REGISTRIES = (
    Path("src/uiao/canon/modernization-registry.yaml"),
    Path("src/uiao/canon/adapter-registry.yaml"),
)


def _journal_path() -> Path:
    return Path(
        os.environ.get(
            "UIAO_ENFORCEMENT_JOURNAL_PATH",
            "output/enforcement/journal.jsonl",
        )
    )


def _archive_root() -> Path:
    return Path(os.environ.get("UIAO_ARCHIVE_ROOT", "output/archive"))


def _load_adapter_records() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for path in CANON_REGISTRIES:
        if not path.is_file():
            continue
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        if not doc:
            continue
        adapters = doc.get("adapters") or doc.get("modernization_adapters") or []
        if isinstance(adapters, list):
            out.extend(a for a in adapters if isinstance(a, dict))
    return adapters_resolver(out)


def _build_evaluator() -> CQLEvaluator:
    """Wire CQL to the substrate's live data sources for v1 read-only."""
    journal = EnforcementJournal(path=_journal_path())
    archive = ArchiveManager(backend=FilesystemArchive(root=_archive_root())).query()
    resolver = make_default_resolver(
        # findings: empty for v1 — the next PR threads in EvidenceGraph
        # via a configurable on-disk graph snapshot. Today the runtime
        # graph is request-scoped; CQL doesn't yet have a persistent
        # graph dump to read from.
        findings=[],
        enforcement=journal_records_resolver(journal.read_all()),
        archive=journal_records_resolver(archive),
        adapters=_load_adapter_records(),
    )
    return CQLEvaluator(resolver=resolver)


@router.get("/queries", summary="List canonical CQL queries")
def list_queries(_subject: str = Depends(require_auditor)) -> dict:
    queries = load_canonical_queries()
    return {
        "count": len(queries),
        "queries": [{"name": k, **q.as_dict()} for k, q in sorted(queries.items())],
    }


@router.get("/queries/{name}", summary="Fetch a single canonical CQL query")
def get_query(
    name: str,
    _subject: str = Depends(require_auditor),
) -> dict:
    queries = load_canonical_queries()
    found: Optional[CQLQuery] = queries.get(name)
    if found is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"unknown canonical query '{name}'",
        )
    return {"name": name, **found.as_dict()}


@router.post("/evaluate", summary="Evaluate an ad-hoc CQL query")
def evaluate(
    body: dict = Body(...),
    _subject: str = Depends(require_auditor),
) -> dict:
    try:
        query = parse_query(body)
    except CQLParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    evaluator = _build_evaluator()
    result = evaluator.evaluate(query)
    return result.as_dict()


@router.post(
    "/evaluate/{name}",
    summary="Evaluate a canonical CQL query by name",
)
def evaluate_named(
    name: str,
    _subject: str = Depends(require_auditor),
) -> dict:
    queries = load_canonical_queries()
    query = queries.get(name)
    if query is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"unknown canonical query '{name}'",
        )
    evaluator = _build_evaluator()
    result = evaluator.evaluate(query)
    return result.as_dict()
