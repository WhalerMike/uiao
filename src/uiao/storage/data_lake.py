"""Data Lake Model — long-term evidence retention + archival (UIAO_109, §3.7).

UIAO collects evidence on every scheduler dispatch (UIAO_100). The lake
model gives that evidence a long-term home with a retention policy
attached, so:

  * compliance teams can serve audit requests months / years after a
    finding closed,
  * the substrate can prove freshness (UIAO_016) and provenance (chain
    of custody) for any claim still inside its retention window,
  * old evidence ages out automatically rather than accumulating
    indefinitely.

Per-adapter retention is already declared in canon as
``retention-years:`` on each adapter entry (modernization-registry +
adapter-registry). The lake reads those declarations to compute a
``retention_until`` timestamp for every archived run; an
:class:`ArchiveManager` scheduled in CI / cron expires entries past
their window.

Pipeline:

    schedrun-*/                                (UIAO_100 scheduler run)
            │
            ▼
    archive_scheduler_run(run_dir, lake_root, …)
            │
            ▼
    lake_root/<adapter_id>/<run_id>/{evidence.json,drift.json,…}
            +
    lake_root/_index/<run_id>.json             (ArchiveEntry manifest)
            │
            ├─ ArchiveManager.expire(now=…) → removes past-retention dirs
            └─ ArchiveManager.query(...)    → retrieval for the Auditor API

Severity policy and storage backend:
    Today the lake ships only a filesystem backend
    (:class:`FilesystemArchive`). The :class:`ArchiveBackend` abstract
    base class lets future PRs plug S3 / Azure Blob / GCS without
    touching the public API. Hot vs. cold tiering and compression are
    declared on the policy but not yet enforced — operators run the
    archive on a single tier today and revisit when storage cost
    becomes the bottleneck.
"""

from __future__ import annotations

import abc
import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

import yaml

# Default retention applied when an adapter declares no
# `retention-years:` (federal ConMon baseline: 3 years).
DEFAULT_RETENTION_YEARS = 3

# Default hot-tier window — runs younger than this are kept in fast
# storage. Cold tiering is declarative today; future PRs apply
# compression / move to slower storage at this boundary.
DEFAULT_HOT_PERIOD_DAYS = 30


# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _isoformat(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _parse_iso(value: str) -> Optional[datetime]:
    try:
        dt = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


# ---------------------------------------------------------------------------
# Retention policy
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RetentionPolicy:
    """Per-adapter retention declaration."""

    adapter_id: str
    retention_years: int = DEFAULT_RETENTION_YEARS
    hot_period_days: int = DEFAULT_HOT_PERIOD_DAYS

    @property
    def retention_period(self) -> timedelta:
        # Use 365.25 days/year so leap years average out across the window.
        return timedelta(days=int(self.retention_years * 365.25))

    @property
    def hot_period(self) -> timedelta:
        return timedelta(days=self.hot_period_days)


def _adapter_entries(doc: Optional[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    if not doc:
        return []
    if isinstance(doc, list):
        return [a for a in doc if isinstance(a, Mapping)]
    candidates = doc.get("adapters") or doc.get("modernization_adapters")
    if isinstance(candidates, list):
        return [a for a in candidates if isinstance(a, Mapping)]
    return []


def load_retention_policies(
    registries: Iterable[str | Path],
    *,
    default_retention_years: int = DEFAULT_RETENTION_YEARS,
    hot_period_days: int = DEFAULT_HOT_PERIOD_DAYS,
) -> dict[str, RetentionPolicy]:
    """Read ``retention-years:`` declarations from canon registries.

    Adapters without an explicit ``retention-years:`` use
    ``default_retention_years``. Later registries override earlier.
    """
    out: dict[str, RetentionPolicy] = {}
    for path in registries:
        p = Path(path)
        if not p.is_file():
            continue
        try:
            doc = yaml.safe_load(p.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        for entry in _adapter_entries(doc):
            adapter_id = str(entry.get("id", "")).strip()
            if not adapter_id:
                continue
            raw = entry.get("retention-years")
            try:
                years = int(raw) if raw is not None else default_retention_years
            except (TypeError, ValueError):
                years = default_retention_years
            out[adapter_id] = RetentionPolicy(
                adapter_id=adapter_id,
                retention_years=max(1, years),
                hot_period_days=hot_period_days,
            )
    return out


def policy_for(
    adapter_id: str,
    policies: Mapping[str, RetentionPolicy],
    *,
    default_retention_years: int = DEFAULT_RETENTION_YEARS,
    hot_period_days: int = DEFAULT_HOT_PERIOD_DAYS,
) -> RetentionPolicy:
    """Resolve a retention policy with sane fallbacks.

    Returns the declared policy when present; otherwise synthesizes a
    default policy for the adapter.
    """
    if adapter_id in policies:
        return policies[adapter_id]
    return RetentionPolicy(
        adapter_id=adapter_id,
        retention_years=default_retention_years,
        hot_period_days=hot_period_days,
    )


# ---------------------------------------------------------------------------
# Archive entry model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ArchiveEntry:
    """One archived (run_id, adapter_id) pair's metadata."""

    run_id: str
    adapter_id: str
    archived_at: str  # ISO-8601 UTC
    retention_until: str  # ISO-8601 UTC
    archive_path: str  # repo-relative or absolute, backend-defined
    evidence_class: str = ""  # e.g. baseline / signal / spot-check
    extra: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "adapter_id": self.adapter_id,
            "archived_at": self.archived_at,
            "retention_until": self.retention_until,
            "archive_path": self.archive_path,
            "evidence_class": self.evidence_class,
            "extra": dict(self.extra),
        }

    @property
    def retention_until_dt(self) -> Optional[datetime]:
        return _parse_iso(self.retention_until)

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        ru = self.retention_until_dt
        if ru is None:
            return False
        return (now or _now_utc()) >= ru


# ---------------------------------------------------------------------------
# Backend interface + filesystem implementation
# ---------------------------------------------------------------------------


class ArchiveBackend(abc.ABC):
    """Storage backend interface. Filesystem is the only impl today."""

    @abc.abstractmethod
    def put(self, source: Path, key: str) -> str:
        """Copy/move ``source`` into the backend keyed at ``key``.

        Returns the final backend-defined location string (used by
        ``ArchiveEntry.archive_path``).
        """

    @abc.abstractmethod
    def remove(self, key: str) -> bool:
        """Remove the object at ``key``. Returns ``True`` when removed."""

    @abc.abstractmethod
    def exists(self, key: str) -> bool: ...


@dataclass
class FilesystemArchive(ArchiveBackend):
    """Filesystem-backed archive rooted at ``root``.

    Layout::

        root/
            <adapter_id>/<run_id>/                 # per-adapter run dir
                evidence.json
                drift.json
                ...
            _index/<run_id>__<adapter_id>.json     # ArchiveEntry manifest
    """

    root: Path

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "_index").mkdir(exist_ok=True)

    def put(self, source: Path, key: str) -> str:
        target = self.root / key
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
        return str(target)

    def remove(self, key: str) -> bool:
        target = self.root / key
        if not target.exists():
            return False
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        return True

    def exists(self, key: str) -> bool:
        return (self.root / key).exists()

    def _index_path(self, run_id: str, adapter_id: str) -> Path:
        return self.root / "_index" / f"{run_id}__{adapter_id}.json"

    def write_index(self, entry: ArchiveEntry) -> Path:
        path = self._index_path(entry.run_id, entry.adapter_id)
        path.write_text(json.dumps(entry.as_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return path

    def read_index(self, run_id: str, adapter_id: str) -> Optional[ArchiveEntry]:
        path = self._index_path(run_id, adapter_id)
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(data, dict):
            return None
        return ArchiveEntry(
            run_id=str(data.get("run_id", "")),
            adapter_id=str(data.get("adapter_id", "")),
            archived_at=str(data.get("archived_at", "")),
            retention_until=str(data.get("retention_until", "")),
            archive_path=str(data.get("archive_path", "")),
            evidence_class=str(data.get("evidence_class", "")),
            extra=data.get("extra", {}) if isinstance(data.get("extra"), dict) else {},
        )

    def list_index(self) -> list[ArchiveEntry]:
        out: list[ArchiveEntry] = []
        idx = self.root / "_index"
        if not idx.is_dir():
            return out
        for p in sorted(idx.glob("*.json")):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(data, dict):
                continue
            out.append(
                ArchiveEntry(
                    run_id=str(data.get("run_id", "")),
                    adapter_id=str(data.get("adapter_id", "")),
                    archived_at=str(data.get("archived_at", "")),
                    retention_until=str(data.get("retention_until", "")),
                    archive_path=str(data.get("archive_path", "")),
                    evidence_class=str(data.get("evidence_class", "")),
                    extra=data.get("extra", {}) if isinstance(data.get("extra"), dict) else {},
                )
            )
        return out


# ---------------------------------------------------------------------------
# ArchiveManager — orchestration
# ---------------------------------------------------------------------------


@dataclass
class ArchiveManager:
    """Orchestrates archival of scheduler runs into a backend."""

    backend: FilesystemArchive
    policies: Mapping[str, RetentionPolicy] = field(default_factory=dict)
    default_retention_years: int = DEFAULT_RETENTION_YEARS

    def _resolve_policy(self, adapter_id: str) -> RetentionPolicy:
        return policy_for(
            adapter_id,
            self.policies,
            default_retention_years=self.default_retention_years,
        )

    def archive_run(
        self,
        run_dir: Path | str,
        *,
        now: Optional[datetime] = None,
    ) -> list[ArchiveEntry]:
        """Archive every adapter under ``run_dir/adapters/`` into the
        backend and write an index manifest per adapter.

        Returns the list of :class:`ArchiveEntry` written. Adapters
        with no evidence.json are skipped (nothing to archive).
        """
        root = Path(run_dir)
        adapters_dir = root / "adapters"
        if not adapters_dir.is_dir():
            return []
        run_id = root.name
        archived_at = now or _now_utc()
        results: list[ArchiveEntry] = []
        for adapter_dir in sorted(adapters_dir.iterdir()):
            if not adapter_dir.is_dir():
                continue
            evidence_path = adapter_dir / "evidence.json"
            if not evidence_path.is_file():
                continue
            adapter_id = adapter_dir.name
            policy = self._resolve_policy(adapter_id)
            retention_until = archived_at + policy.retention_period
            evidence_class = ""
            try:
                payload = json.loads(evidence_path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    evidence_class = str(payload.get("evidence_class", "") or "")
            except (OSError, json.JSONDecodeError):
                pass
            archive_path = self.backend.put(adapter_dir, f"{adapter_id}/{run_id}")
            entry = ArchiveEntry(
                run_id=run_id,
                adapter_id=adapter_id,
                archived_at=_isoformat(archived_at),
                retention_until=_isoformat(retention_until),
                archive_path=archive_path,
                evidence_class=evidence_class,
                extra={"retention_years": policy.retention_years},
            )
            self.backend.write_index(entry)
            results.append(entry)
        return results

    def expire(self, *, now: Optional[datetime] = None) -> list[ArchiveEntry]:
        """Remove every archive entry whose retention_until ≤ now.

        Returns the list of expired entries (after removal). The
        per-adapter directory and the index manifest are both cleaned up.
        """
        cutoff = now or _now_utc()
        expired: list[ArchiveEntry] = []
        for entry in self.backend.list_index():
            if entry.is_expired(cutoff):
                self.backend.remove(f"{entry.adapter_id}/{entry.run_id}")
                idx = self.backend._index_path(entry.run_id, entry.adapter_id)
                if idx.is_file():
                    idx.unlink()
                expired.append(entry)
        return expired

    def query(
        self,
        *,
        adapter_id: str = "",
        run_id: str = "",
        evidence_class: str = "",
    ) -> list[ArchiveEntry]:
        """Filter the index by any combination of fields. Empty filter
        fields are wildcards. Returns id-stable order (run_id, adapter_id)."""
        out: list[ArchiveEntry] = []
        for entry in self.backend.list_index():
            if adapter_id and entry.adapter_id != adapter_id:
                continue
            if run_id and entry.run_id != run_id:
                continue
            if evidence_class and entry.evidence_class != evidence_class:
                continue
            out.append(entry)
        out.sort(key=lambda e: (e.run_id, e.adapter_id))
        return out


__all__ = [
    "DEFAULT_HOT_PERIOD_DAYS",
    "DEFAULT_RETENTION_YEARS",
    "ArchiveBackend",
    "ArchiveEntry",
    "ArchiveManager",
    "FilesystemArchive",
    "RetentionPolicy",
    "load_retention_policies",
    "policy_for",
]
