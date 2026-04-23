"""UIAO_100 Compliance Orchestrator — Scheduler.

Roadmap anchor: docs/docs/uiao-substrate-roadmap.md §1.3 (aspirational → partial).

This module is the scheduler layer that the canon (UIAO_100) describes as:
    - Schedule SCuBA runs (e.g., nightly)
    - Trigger: Normalization, KSI evaluation, Drift engine, OSCAL emitters,
      POA&M generator
    - Notify: Operators and Auditors

Scope of this Phase-1 implementation (non-production-grade per roadmap):
    - Read the canonical adapter registry
    - Iterate adapters; call adapter.collect_evidence() + adapter.detect_drift()
      for each active entry
    - Persist per-adapter evidence + drift to a run directory
    - Aggregate drift findings across the run
    - Emit a deterministic run manifest (JSON)
    - Retry with exponential backoff per adapter (mirrors orchestrator.py)

Explicitly NOT in this pass:
    - Cron scheduling daemon (callers drive timing via GitHub Actions cron)
    - Dead-letter queue
    - Email/webhook alerting
    - Multi-tenant per-tenant schedule dispatch
    - Wiring every real adapter — the factory is injectable so tests can mock
      adapters and production can wire the full registry incrementally.

Canon contract:
    UIAO_003 §4.2–§4.7 — adapter classes
    UIAO_100          — this module's referent spec
    UIAO_113          — evidence graph (downstream consumer; not yet wired)
    UIAO_016          — drift detection standard (drift routing target)

File: src/uiao/orchestrator/scheduler.py
"""

from __future__ import annotations

import dataclasses
import hashlib
import importlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

from uiao.adapters.database_base import DatabaseAdapterBase, DriftReport, EvidenceObject

logger = logging.getLogger("uiao.orchestrator.scheduler")


# ---------------------------------------------------------------------------
# Constants + defaults
# ---------------------------------------------------------------------------

DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parents[2] / "uiao" / "canon" / "adapter-registry.yaml"
DEFAULT_OUTPUT_ROOT = Path("evidence/orchestrator-runs")
MANIFEST_SCHEMA_VERSION = "1.0.0"
DEFAULT_MAX_RETRIES = 2
DEFAULT_RETRY_BASE_SECONDS = 0.5  # tests override to 0 for speed

# Default adapter factory — maps registry IDs to (module, class). The scheduler
# uses this only when no factory is injected. Non-registered IDs are handled as
# "not wired yet" and recorded in the manifest without failing the run.
_BUILTIN_ADAPTER_CLASSES: dict[str, tuple[str, str]] = {
    "scubagear": ("uiao.adapters.scubagear_adapter", "ScubaGearAdapter"),
    "entra-id": ("uiao.adapters.entra_adapter", "EntraAdapter"),
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class AdapterRun:
    """Outcome of invoking one adapter in a scheduler run."""

    adapter_id: str
    status: str  # success | failed | skipped | not-wired
    started_at: str  # ISO-8601 UTC
    completed_at: str
    duration_secs: float
    retry_count: int
    evidence_path: Optional[str] = None  # repo-relative
    drift_path: Optional[str] = None  # repo-relative
    drift_severity: Optional[str] = None
    error: Optional[str] = None
    ksi_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class ScheduleRunManifest:
    """Summary of a complete scheduler run. Persisted as manifest.json."""

    run_id: str
    schema_version: str
    started_at: str
    completed_at: str
    duration_secs: float
    registry_path: str
    output_root: str
    run_dir: str
    adapters_total: int
    adapters_successful: int
    adapters_failed: int
    adapters_skipped: int
    adapters_not_wired: int
    drift_findings_total: int
    drift_by_severity: dict[str, int]
    runs: list[AdapterRun] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = dataclasses.asdict(self)
        d["runs"] = [r.to_dict() if isinstance(r, AdapterRun) else r for r in self.runs]
        return d


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_id_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _short_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]


def _default_adapter_factory(adapter_id: str) -> DatabaseAdapterBase | None:
    """Resolve a registered adapter ID to a `DatabaseAdapterBase` instance.

    Returns None when the adapter is not yet wired in the built-in map —
    callers should record this as `status=not-wired`, not as an error.
    """
    spec = _BUILTIN_ADAPTER_CLASSES.get(adapter_id)
    if spec is None:
        return None
    module_path, class_name = spec
    try:
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        return cls({})  # type: ignore[no-any-return]
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to instantiate %s: %s", adapter_id, exc)
        return None


def _load_registry(path: Path) -> list[dict[str, Any]]:
    """Return the `adapters:` list from the canonical adapter registry YAML."""
    if yaml is None:
        raise RuntimeError("PyYAML not installed; cannot parse adapter registry.")
    if not path.is_file():
        raise FileNotFoundError(f"Adapter registry not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "adapters" not in data:
        raise ValueError(f"Registry {path} missing 'adapters' list")
    adapters = data.get("adapters") or []
    if not isinstance(adapters, list):
        raise ValueError(f"Registry {path} 'adapters' is not a list")
    return adapters


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------


class OrchestratorScheduler:
    """Dispatch all adapters in the registry; persist evidence + drift.

    The scheduler is deliberately thin: it knows how to read the registry,
    iterate adapters, invoke their ABC methods, persist outputs, and
    aggregate drift. It does NOT know about specific vendors, OPA/Rego, or
    SCuBA transforms — those are adapter-side concerns.

    Public entry points:
        - ``dispatch_all()``      — run every active adapter in the registry
        - ``dispatch_one(adapter_id)`` — targeted dispatch
        - ``load_registry()``     — introspect registry without dispatching

    The adapter factory is injectable (``adapter_factory`` kwarg). Tests
    inject mock adapters; the default factory uses a small built-in map
    that can grow as real adapter wiring lands in subsequent PRs.
    """

    def __init__(
        self,
        *,
        registry_path: Path | str = DEFAULT_REGISTRY_PATH,
        output_root: Path | str = DEFAULT_OUTPUT_ROOT,
        ksi_map: Optional[dict[str, str]] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_base_seconds: float = DEFAULT_RETRY_BASE_SECONDS,
        adapter_factory: Optional[Callable[[str], DatabaseAdapterBase | None]] = None,
        status_filter: tuple[str, ...] = ("active",),
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.registry_path = Path(registry_path)
        self.output_root = Path(output_root)
        self.ksi_map = dict(ksi_map or {})
        self.max_retries = max(0, int(max_retries))
        self.retry_base_seconds = max(0.0, float(retry_base_seconds))
        self.adapter_factory = adapter_factory or _default_adapter_factory
        self.status_filter = status_filter
        # Clock is injectable so tests produce deterministic run IDs.
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    # ------------------------------------------------------------------
    # Registry
    # ------------------------------------------------------------------

    def load_registry(self) -> list[dict[str, Any]]:
        return _load_registry(self.registry_path)

    def _filter_adapters(self, adapters: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Keep only entries whose status is in ``self.status_filter``."""
        if not self.status_filter:
            return list(adapters)
        keep = set(self.status_filter)
        return [a for a in adapters if a.get("status") in keep]

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def dispatch_all(self, *, dry_run: bool = False) -> ScheduleRunManifest:
        """Run every active adapter in the registry. Returns a manifest.

        Persists a run directory under ``output_root`` named
        ``schedrun-<utc-timestamp>-<hash>/``. Each adapter's evidence and
        drift land at ``<run_dir>/adapters/<adapter_id>/{evidence,drift}.json``.
        The manifest is written to ``<run_dir>/manifest.json``.
        """
        started = self._clock()
        started_iso = started.strftime("%Y-%m-%dT%H:%M:%SZ")
        registry = self._filter_adapters(self.load_registry())
        run_id = self._make_run_id(started, registry)
        run_dir = self.output_root / run_id

        if not dry_run:
            run_dir.mkdir(parents=True, exist_ok=True)

        runs: list[AdapterRun] = []
        t0 = time.monotonic()
        for entry in registry:
            adapter_id = entry.get("id", "")
            if not adapter_id:
                continue
            run = self._invoke_with_retry(
                adapter_id=adapter_id,
                ksi_id=self.ksi_map.get(adapter_id) or f"ksi:{adapter_id}",
                run_dir=run_dir,
                dry_run=dry_run,
            )
            runs.append(run)

        completed = self._clock()
        completed_iso = completed.strftime("%Y-%m-%dT%H:%M:%SZ")
        manifest = self._build_manifest(
            run_id=run_id,
            run_dir=run_dir,
            registry_path=self.registry_path,
            started_iso=started_iso,
            completed_iso=completed_iso,
            duration_secs=round(time.monotonic() - t0, 3),
            runs=runs,
        )
        if not dry_run:
            self._write_manifest(manifest, run_dir)
            self._write_drift_summary(manifest, run_dir)
        return manifest

    def dispatch_one(
        self,
        adapter_id: str,
        *,
        run_dir: Optional[Path] = None,
        dry_run: bool = False,
    ) -> AdapterRun:
        """Dispatch a single adapter by ID. Convenient for targeted retries."""
        target_dir = run_dir or (self.output_root / self._make_run_id(self._clock(), [{"id": adapter_id}]))
        if not dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)
        return self._invoke_with_retry(
            adapter_id=adapter_id,
            ksi_id=self.ksi_map.get(adapter_id) or f"ksi:{adapter_id}",
            run_dir=target_dir,
            dry_run=dry_run,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _make_run_id(self, started: datetime, registry: list[dict[str, Any]]) -> str:
        stamp = started.strftime("%Y%m%dT%H%M%SZ")
        seed = stamp + "|" + ",".join(sorted(str(a.get("id", "")) for a in registry))
        return f"schedrun-{stamp}-{_short_hash(seed)}"

    def _invoke_with_retry(
        self,
        *,
        adapter_id: str,
        ksi_id: str,
        run_dir: Path,
        dry_run: bool,
    ) -> AdapterRun:
        started_mono = time.monotonic()
        started_iso = _now_iso()
        adapter_dir = run_dir / "adapters" / adapter_id

        if dry_run:
            return AdapterRun(
                adapter_id=adapter_id,
                status="skipped",
                started_at=started_iso,
                completed_at=_now_iso(),
                duration_secs=round(time.monotonic() - started_mono, 3),
                retry_count=0,
                ksi_id=ksi_id,
                error=None,
            )

        adapter = self.adapter_factory(adapter_id)
        if adapter is None:
            return AdapterRun(
                adapter_id=adapter_id,
                status="not-wired",
                started_at=started_iso,
                completed_at=_now_iso(),
                duration_secs=round(time.monotonic() - started_mono, 3),
                retry_count=0,
                ksi_id=ksi_id,
                error="No adapter factory entry (Phase-2 work: wire real adapter class).",
            )

        last_error: Optional[str] = None
        for attempt in range(self.max_retries + 1):
            try:
                evidence = adapter.collect_evidence(ksi_id)
                drift = adapter.detect_drift()
                adapter_dir.mkdir(parents=True, exist_ok=True)
                evidence_path = self._persist_evidence(evidence, adapter_dir)
                drift_path = self._persist_drift(drift, adapter_dir)
                return AdapterRun(
                    adapter_id=adapter_id,
                    status="success",
                    started_at=started_iso,
                    completed_at=_now_iso(),
                    duration_secs=round(time.monotonic() - started_mono, 3),
                    retry_count=attempt,
                    ksi_id=ksi_id,
                    evidence_path=str(evidence_path),
                    drift_path=str(drift_path),
                    drift_severity=getattr(drift, "severity", None),
                )
            except Exception as exc:  # noqa: BLE001
                last_error = f"{type(exc).__name__}: {exc}"
                logger.warning(
                    "Adapter %s attempt %d/%d failed: %s",
                    adapter_id,
                    attempt + 1,
                    self.max_retries + 1,
                    last_error,
                )
                if attempt < self.max_retries and self.retry_base_seconds > 0:
                    time.sleep(self.retry_base_seconds * (2**attempt))

        return AdapterRun(
            adapter_id=adapter_id,
            status="failed",
            started_at=started_iso,
            completed_at=_now_iso(),
            duration_secs=round(time.monotonic() - started_mono, 3),
            retry_count=self.max_retries,
            ksi_id=ksi_id,
            error=last_error,
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _persist_evidence(self, evidence: EvidenceObject, adapter_dir: Path) -> Path:
        path = adapter_dir / "evidence.json"
        payload = evidence.to_dict() if hasattr(evidence, "to_dict") else dataclasses.asdict(evidence)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
        return path

    def _persist_drift(self, drift: DriftReport, adapter_dir: Path) -> Path:
        path = adapter_dir / "drift.json"
        payload = drift.to_dict() if hasattr(drift, "to_dict") else dataclasses.asdict(drift)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
        return path

    def _build_manifest(
        self,
        *,
        run_id: str,
        run_dir: Path,
        registry_path: Path,
        started_iso: str,
        completed_iso: str,
        duration_secs: float,
        runs: list[AdapterRun],
    ) -> ScheduleRunManifest:
        successful = sum(1 for r in runs if r.status == "success")
        failed = sum(1 for r in runs if r.status == "failed")
        skipped = sum(1 for r in runs if r.status == "skipped")
        not_wired = sum(1 for r in runs if r.status == "not-wired")
        drift_counts: dict[str, int] = {}
        for r in runs:
            if r.drift_severity:
                drift_counts[r.drift_severity] = drift_counts.get(r.drift_severity, 0) + 1
        return ScheduleRunManifest(
            run_id=run_id,
            schema_version=MANIFEST_SCHEMA_VERSION,
            started_at=started_iso,
            completed_at=completed_iso,
            duration_secs=duration_secs,
            registry_path=str(registry_path),
            output_root=str(self.output_root),
            run_dir=str(run_dir),
            adapters_total=len(runs),
            adapters_successful=successful,
            adapters_failed=failed,
            adapters_skipped=skipped,
            adapters_not_wired=not_wired,
            drift_findings_total=sum(drift_counts.values()),
            drift_by_severity=dict(sorted(drift_counts.items())),
            runs=runs,
        )

    def _write_manifest(self, manifest: ScheduleRunManifest, run_dir: Path) -> Path:
        path = run_dir / "manifest.json"
        path.write_text(
            json.dumps(manifest.to_dict(), indent=2, sort_keys=False, default=str),
            encoding="utf-8",
        )
        return path

    def _write_drift_summary(self, manifest: ScheduleRunManifest, run_dir: Path) -> Path:
        """Per-run drift summary. Downstream consumer: UIAO_113 evidence graph."""
        path = run_dir / "drift-summary.json"
        payload = {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "run_id": manifest.run_id,
            "total": manifest.drift_findings_total,
            "by_severity": manifest.drift_by_severity,
            "adapters_with_drift": [
                {"adapter_id": r.adapter_id, "severity": r.drift_severity, "drift_path": r.drift_path}
                for r in manifest.runs
                if r.drift_severity
            ],
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
        return path
