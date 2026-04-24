"""DRIFT-SEMANTIC freshness evaluator (roadmap §1.1).

Bridges the UIAO_100 scheduler's per-adapter evidence output to the
UIAO_016 drift engine by enforcing per-adapter staleness windows
declared in the canonical adapter registries.

Pipeline:
    schedrun-*/adapters/<id>/evidence.json          (UIAO_100)
            │  timestamp, source, ksi_id
            ▼
    load_adapter_windows(<registries>)              (this module)
            │  freshness-window-hours per adapter
            ▼
    evaluate_scheduler_run(run_dir, registries)     (this module)
            │  age vs window → fresh | stale-soon | stale
            ▼
    DRIFT-SEMANTIC findings (dict list)             (UIAO_016)

Fallbacks:
    1. Adapter's declared freshness-window-hours (canon).
    2. ``DEFAULT_WINDOW_HOURS_BY_FAMILY`` entry for the inferred NIST family.
    3. ``DEFAULT_WINDOW_HOURS`` last-resort (30 days).

File: src/uiao/freshness/drift_semantic.py
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

# Control-family → staleness window in hours. These are evaluator-of-last-
# resort values; every production adapter should declare an explicit
# ``freshness-window-hours`` in its registry entry.
DEFAULT_WINDOW_HOURS_BY_FAMILY: Dict[str, int] = {
    "AC": 24 * 30,
    "AU": 24 * 7,
    "CA": 24 * 90,
    "CM": 24 * 14,
    "IA": 24 * 30,
    "IR": 24 * 1,
    "RA": 24 * 90,
    "SC": 24 * 30,
    "SI": 24 * 7,
}

DEFAULT_WINDOW_HOURS = 24 * 30  # 30 days
DRIFT_TYPE = "DRIFT-SEMANTIC"
DEFAULT_SEVERITY = "P2"  # per roadmap §1.1


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AdapterFreshnessPolicy:
    """Per-adapter freshness contract resolved from canon registries."""

    adapter_id: str
    window_hours: int
    source: str  # "registry" | "family-default" | "global-default"
    family_hint: Optional[str] = None


@dataclass
class FreshnessFinding:
    """DRIFT-SEMANTIC finding emitted when evidence exceeds its window."""

    adapter_id: str
    run_id: str
    drift_type: str
    severity: str
    age_hours: float
    window_hours: int
    status: str  # fresh | stale-soon | stale | missing-timestamp
    evidence_timestamp: Optional[str]
    evaluated_at: str
    policy_source: str
    ksi_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "run_id": self.run_id,
            "drift_type": self.drift_type,
            "severity": self.severity,
            "age_hours": round(self.age_hours, 3),
            "window_hours": self.window_hours,
            "status": self.status,
            "evidence_timestamp": self.evidence_timestamp,
            "evaluated_at": self.evaluated_at,
            "policy_source": self.policy_source,
            "ksi_id": self.ksi_id,
            "details": self.details,
        }


# ---------------------------------------------------------------------------
# Registry + policy resolution
# ---------------------------------------------------------------------------


def _infer_family(ksi_id: Optional[str]) -> Optional[str]:
    """NIST family prefix (AC/AU/CA/...) from a KSI like ``ksi:AC-2``."""
    if not ksi_id:
        return None
    m = re.search(r"\b([A-Z]{2})-\d+", ksi_id)
    return m.group(1) if m else None


def _load_yaml(path: Path) -> Dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML not installed; cannot parse registry YAML.")
    if not path.is_file():
        raise FileNotFoundError(f"Registry not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Registry {path} is not a YAML mapping")
    return data


def load_adapter_windows(registries: Iterable[Path | str]) -> Dict[str, int]:
    """Return ``{adapter_id: window_hours}`` collected from the given canon
    registries. Later registries override earlier ones on collision."""
    merged: Dict[str, int] = {}
    for reg in registries:
        data = _load_yaml(Path(reg))
        for entry in data.get("adapters") or []:
            adapter_id = entry.get("id")
            window = entry.get("freshness-window-hours")
            if isinstance(adapter_id, str) and isinstance(window, int) and window >= 1:
                merged[adapter_id] = window
    return merged


def resolve_policy(
    adapter_id: str,
    *,
    windows: Dict[str, int],
    ksi_id: Optional[str] = None,
    family_defaults: Dict[str, int] | None = None,
    global_default: int = DEFAULT_WINDOW_HOURS,
) -> AdapterFreshnessPolicy:
    """Pick the tightest applicable window: registry → family → global."""
    if adapter_id in windows:
        return AdapterFreshnessPolicy(
            adapter_id=adapter_id,
            window_hours=windows[adapter_id],
            source="registry",
        )
    family = _infer_family(ksi_id)
    fam = family_defaults if family_defaults is not None else DEFAULT_WINDOW_HOURS_BY_FAMILY
    if family and family in fam:
        return AdapterFreshnessPolicy(
            adapter_id=adapter_id,
            window_hours=fam[family],
            source="family-default",
            family_hint=family,
        )
    return AdapterFreshnessPolicy(
        adapter_id=adapter_id,
        window_hours=global_default,
        source="global-default",
    )


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def _parse_iso(ts: str) -> datetime:
    try:
        dt = datetime.fromisoformat(ts)
    except ValueError:
        dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _classify(age_hours: float, window_hours: int) -> str:
    if age_hours <= window_hours:
        return "fresh"
    if age_hours <= window_hours * 1.5:
        return "stale-soon"
    return "stale"


def _severity_for_status(status: str) -> str:
    """Map evaluator status to a drift-severity label.

    fresh          → P5  (informational; no drift)
    stale-soon     → P3  (warn)
    stale          → P2  (default DRIFT-SEMANTIC severity per §1.1)
    missing-timestamp → P1 (can't reason about freshness → treat as high)
    """
    if status == "stale":
        return DEFAULT_SEVERITY
    if status == "stale-soon":
        return "P3"
    if status == "missing-timestamp":
        return "P1"
    return "P5"


def evaluate_evidence_payload(
    payload: Dict[str, Any],
    *,
    adapter_id: str,
    run_id: str,
    policy: AdapterFreshnessPolicy,
    now: Optional[datetime] = None,
) -> FreshnessFinding:
    """Evaluate a single scheduler-written ``evidence.json`` payload."""
    now = now or datetime.now(timezone.utc)
    ts = payload.get("timestamp")
    ksi_id = payload.get("ksi_id")

    if not ts:
        return FreshnessFinding(
            adapter_id=adapter_id,
            run_id=run_id,
            drift_type=DRIFT_TYPE,
            severity=_severity_for_status("missing-timestamp"),
            age_hours=float("inf"),
            window_hours=policy.window_hours,
            status="missing-timestamp",
            evidence_timestamp=None,
            evaluated_at=now.isoformat(),
            policy_source=policy.source,
            ksi_id=ksi_id,
            details={"reason": "evidence.json has no timestamp"},
        )

    age_hours = (now - _parse_iso(str(ts))).total_seconds() / 3600.0
    if age_hours < 0:
        # Future-dated evidence is suspicious but not stale. Treat as fresh
        # and record the anomaly in details so reviewers can catch it.
        status = "fresh"
        details: Dict[str, Any] = {"anomaly": "timestamp is in the future", "age_hours": age_hours}
    else:
        status = _classify(age_hours, policy.window_hours)
        details = {}

    return FreshnessFinding(
        adapter_id=adapter_id,
        run_id=run_id,
        drift_type=DRIFT_TYPE,
        severity=_severity_for_status(status),
        age_hours=max(0.0, age_hours),
        window_hours=policy.window_hours,
        status=status,
        evidence_timestamp=str(ts),
        evaluated_at=now.isoformat(),
        policy_source=policy.source,
        ksi_id=ksi_id,
        details=details,
    )


def evaluate_scheduler_run(
    run_dir: Path | str,
    *,
    registries: Iterable[Path | str],
    now: Optional[datetime] = None,
) -> List[FreshnessFinding]:
    """Evaluate every adapter in a scheduler run directory.

    Produces one :class:`FreshnessFinding` per adapter, covering both
    fresh and stale outcomes. Callers filter by ``status`` or ``severity``
    to materialize only the DRIFT-SEMANTIC findings they want to route.
    """
    run_path = Path(run_dir)
    if not run_path.is_dir():
        raise FileNotFoundError(f"Scheduler run directory not found: {run_path}")
    adapters_root = run_path / "adapters"
    if not adapters_root.is_dir():
        return []

    windows = load_adapter_windows(registries)
    run_id = _read_run_id(run_path)
    now = now or datetime.now(timezone.utc)
    findings: List[FreshnessFinding] = []

    for adapter_dir in sorted(adapters_root.iterdir()):
        if not adapter_dir.is_dir():
            continue
        evidence_path = adapter_dir / "evidence.json"
        if not evidence_path.is_file():
            continue
        try:
            payload = json.loads(evidence_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        policy = resolve_policy(
            adapter_dir.name,
            windows=windows,
            ksi_id=payload.get("ksi_id"),
        )
        findings.append(
            evaluate_evidence_payload(
                payload,
                adapter_id=adapter_dir.name,
                run_id=run_id,
                policy=policy,
                now=now,
            )
        )
    return findings


# ---------------------------------------------------------------------------
# Helpers shared with the scheduler layout
# ---------------------------------------------------------------------------


def _read_run_id(run_dir: Path) -> str:
    manifest = run_dir / "manifest.json"
    if manifest.is_file():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            rid = data.get("run_id")
            if isinstance(rid, str) and rid:
                return rid
        except (OSError, json.JSONDecodeError):
            pass
    return run_dir.name


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def drift_semantic_findings(findings: Iterable[FreshnessFinding]) -> List[FreshnessFinding]:
    """Filter to the subset that should route as DRIFT-SEMANTIC (not fresh)."""
    return [f for f in findings if f.status in {"stale", "stale-soon", "missing-timestamp"}]


def summarize(findings: Iterable[FreshnessFinding]) -> Dict[str, Any]:
    """Per-run rollup: counts by status + by severity."""
    by_status: Dict[str, int] = {}
    by_severity: Dict[str, int] = {}
    for f in findings:
        by_status[f.status] = by_status.get(f.status, 0) + 1
        by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
    return {
        "total": sum(by_status.values()),
        "by_status": dict(sorted(by_status.items())),
        "by_severity": dict(sorted(by_severity.items())),
    }


def write_findings(findings: Iterable[FreshnessFinding], path: Path | str) -> Path:
    """Persist ``findings`` as a JSON list at ``path`` for downstream pickup."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1.0.0",
        "drift_type": DRIFT_TYPE,
        "findings": [f.to_dict() for f in findings],
        "summary": summarize(findings),
    }
    out.write_text(json.dumps(payload, indent=2, sort_keys=False, default=str), encoding="utf-8")
    return out
