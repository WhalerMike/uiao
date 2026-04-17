"""uiao.impl.oscal.generator — Evidence Bundle → OSCAL Artifacts (Plane 4).

Contract
--------
Input  : Evidence bundle directory  (./output/evidence/{source}/)
           {source}/bundle.json
           {source}/evidence.jsonl
Config : optional generation config (./config/oscal-generate.json)
Output : artifacts directory        (./output/artifacts/{source}/)
           poam.json                — OSCAL-aligned Plan of Action & Milestones
           ssp.json                 — OSCAL-aligned System Security Plan excerpt
           artifact-index.json      — machine-readable manifest of all outputs
Log    : ./output/logs/{timestamp}-oscal-generate.log

Public entry-point
------------------
    generate_oscal(evidence_dir, output_dir, config_path=None)

Functional guarantees
---------------------
* Deterministic — identical evidence bundle + config always produces identical output.
* No external calls — purely in-process transformation.
* No SCuBA knowledge — reads only the canonical evidence bundle from Plane 3.
* No IR knowledge — does not re-read IR or KSI files.
* No cross-layer imports beyond stdlib.
* OSCAL-aligned structures — POA&M and SSP use OSCAL 1.0 field names.

OSCAL POA&M structure produced
-------------------------------
Each 'not-satisfied' evidence record -> one POA&M item:
  {
    "uuid": "<stable-deterministic-uuid>",
    "title": "Control <control_id> not satisfied",
    "description": "<rationale>",
    "status": "open",
    "risk-status": "<severity>",
    "sla-days": <int>,
    "control-id": "<control_id>",
    "evidence-id": "<evidence record id>",
    "evidence-hash": "<sha256>",
    "recommended-action": "<text>"
  }

OSCAL SSP structure produced
-----------------------------
Each evidence record -> one implemented-requirement entry:
  {
    "control-id": "<control_id>",
    "implementation-status": "implemented|partial|not-implemented|not-applicable",
    "remarks": "<rationale>",
    "evidence-id": "<evidence record id>",
    "evidence-hash": "<sha256>"
  }
"""
from __future__ import annotations

import hashlib
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

# ---------------------------------------------------------------------------
# Status / severity mappings
# ---------------------------------------------------------------------------

_STATUS_TO_IMPL: Dict[str, str] = {
    "satisfied": "implemented",
    "not-satisfied": "not-implemented",
    "not-applicable": "not-applicable",
}

_SEVERITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Info": 4}

_DEFAULT_SLA: Dict[str, int] = {
    "Critical": 15,
    "High": 30,
    "Medium": 60,
    "Low": 90,
    "Info": 180,
}


# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------

def _setup_logger(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(f"uiao.oscal.generator.{uuid4().hex[:8]}")
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s %(levelname)-8s %(message)s", "%Y-%m-%dT%H:%M:%SZ")
    fmt.converter = lambda *_: datetime.now(timezone.utc).timetuple()  # type: ignore[assignment]
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    return logger


def _derive_log_path(output_dir: Path) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return output_dir.parent.parent / "logs" / f"{ts}Z-oscal-generate.log"


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def _load_bundle(evidence_dir: Path) -> Dict[str, Any]:
    """Load bundle.json from the evidence bundle directory."""
    bundle_path = evidence_dir / "bundle.json"
    if not bundle_path.exists():
        raise FileNotFoundError(f"bundle.json not found in: {evidence_dir}")
    with bundle_path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("bundle.json must deserialize to a dict")
    return data  # type: ignore[return-value]


def _load_evidence_records(evidence_dir: Path) -> List[Dict[str, Any]]:
    """Load all EvidenceRecords from evidence.jsonl (NDJSON)."""
    jsonl_path = evidence_dir / "evidence.jsonl"
    if not jsonl_path.exists():
        raise FileNotFoundError(f"evidence.jsonl not found in: {evidence_dir}")
    records: List[Dict[str, Any]] = []
    with jsonl_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _load_config(config_path: Optional[str]) -> Dict[str, Any]:
    if config_path is None:
        return {}
    cfg = Path(config_path)
    if not cfg.exists():
        return {}
    with cfg.open(encoding="utf-8") as fh:
        return json.load(fh)  # type: ignore[return-value]


def _write_json(dst: Path, payload: Any) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Deterministic UUID generation
# ---------------------------------------------------------------------------

def _det_uuid(namespace: str, name: str) -> str:
    """Stable UUID v5 for deterministic artifact IDs."""
    ns = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # DNS namespace
    return str(uuid.uuid5(ns, f"{namespace}:{name}"))


# ---------------------------------------------------------------------------
# POA&M generation
# ---------------------------------------------------------------------------

def _severity_for_record(rec: Dict[str, Any], cfg: Dict[str, Any]) -> str:
    """Derive severity from config overrides or default mapping."""
    overrides: Dict[str, str] = cfg.get("severity_overrides", {})
    if rec["control_id"] in overrides:
        return overrides[rec["control_id"]]
    default_severity: str = cfg.get("default_severity", "Medium")
    return default_severity


def _recommended_action(rec: Dict[str, Any], cfg: Dict[str, Any]) -> str:
    templates: Dict[str, str] = cfg.get("action_templates", {})
    status = rec.get("status", "not-applicable")
    cid = rec.get("control_id", "")
    if status == "not-satisfied":
        return templates.get(
            "not-satisfied",
            f"Remediate control {cid} — implementation gap identified."
        )
    if status == "not-applicable":
        return templates.get(
            "not-applicable",
            f"Review control {cid} — verdict inconclusive or excluded."
        )
    return templates.get("satisfied", "No remediation required.")


def _build_poam_items(
    records: List[Dict[str, Any]],
    cfg: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Build OSCAL-aligned POA&M items from not-satisfied evidence records.

    Only 'not-satisfied' records generate POA&M items.
    Items are sorted by severity then control_id.
    """
    include_statuses: List[str] = cfg.get(
        "poam_include_statuses", ["not-satisfied"]
    )

    items: List[Dict[str, Any]] = []
    for rec in records:
        if rec.get("status") not in include_statuses:
            continue
        severity = _severity_for_record(rec, cfg)
        sla_days = _DEFAULT_SLA.get(severity, 60)
        item: Dict[str, Any] = {
            "uuid": _det_uuid("poam-item", rec["id"]),
            "title": f"Control {rec['control_id']} not satisfied",
            "description": rec.get("rationale", ""),
            "status": "open",
            "risk-status": severity,
            "sla-days": sla_days,
            "control-id": rec["control_id"],
            "evidence-id": rec["id"],
            "evidence-hash": _stable_hash(rec),
            "verdict": rec.get("verdict", ""),
            "rule-key": rec.get("rule_key"),
            "recommended-action": _recommended_action(rec, cfg),
            "generated-at": rec.get("generated_at", ""),
        }
        items.append(item)

    items.sort(
        key=lambda i: (
            _SEVERITY_ORDER.get(i["risk-status"], 99),
            i["control-id"],
        )
    )
    return items


def _build_poam_envelope(
    items: List[Dict[str, Any]],
    bundle: Dict[str, Any],
    run_id: str,
    generated_at: str,
    cfg: Dict[str, Any],
) -> Dict[str, Any]:
    system_name: str = cfg.get("system_name", "UIAO-Managed System")
    return {
        "schema_version": "1.0",
        "oscal_version": "1.0.4",
        "plane": "evidence-to-oscal",
        "artifact": "poam",
        "generated_at": generated_at,
        "run_id": run_id,
        "system_name": system_name,
        "source_bundle_run_id": bundle.get("run_id", ""),
        "summary": {
            "total_items": len(items),
            "open_items": sum(1 for i in items if i["status"] == "open"),
            "by_severity": _count_by(items, "risk-status"),
        },
        "poam-items": items,
    }


# ---------------------------------------------------------------------------
# SSP generation
# ---------------------------------------------------------------------------

def _impl_status_for_record(rec: Dict[str, Any]) -> str:
    return _STATUS_TO_IMPL.get(rec.get("status", "not-applicable"), "not-applicable")


def _build_implemented_requirements(
    records: List[Dict[str, Any]],
    cfg: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Build OSCAL implemented-requirements from all evidence records."""
    requirements: List[Dict[str, Any]] = []
    for rec in records:
        req: Dict[str, Any] = {
            "uuid": _det_uuid("impl-req", rec["id"]),
            "control-id": rec["control_id"],
            "implementation-status": _impl_status_for_record(rec),
            "remarks": rec.get("rationale", ""),
            "evidence-id": rec["id"],
            "evidence-hash": _stable_hash(rec),
            "verdict": rec.get("verdict", ""),
            "fresh": rec.get("fresh", False),
            "generated-at": rec.get("generated_at", ""),
        }
        requirements.append(req)
    # Sort by control-id for determinism
    requirements.sort(key=lambda r: r["control-id"])
    return requirements


def _build_ssp_envelope(
    requirements: List[Dict[str, Any]],
    bundle: Dict[str, Any],
    run_id: str,
    generated_at: str,
    cfg: Dict[str, Any],
) -> Dict[str, Any]:
    system_name: str = cfg.get("system_name", "UIAO-Managed System")
    profile: str = cfg.get("oscal_profile", "fedramp-rev5-moderate")
    total = len(requirements)
    impl = sum(1 for r in requirements if r["implementation-status"] == "implemented")
    not_impl = sum(1 for r in requirements if r["implementation-status"] == "not-implemented")
    coverage = round(impl / total, 4) if total else 0.0
    return {
        "schema_version": "1.0",
        "oscal_version": "1.0.4",
        "plane": "evidence-to-oscal",
        "artifact": "ssp",
        "generated_at": generated_at,
        "run_id": run_id,
        "system_name": system_name,
        "oscal_profile": profile,
        "source_bundle_run_id": bundle.get("run_id", ""),
        "summary": {
            "total_controls": total,
            "implemented": impl,
            "not_implemented": not_impl,
            "not_applicable": total - impl - not_impl,
            "coverage": coverage,
        },
        "implemented-requirements": requirements,
    }


# ---------------------------------------------------------------------------
# Artifact index
# ---------------------------------------------------------------------------

def _stable_hash(data: Any) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _count_by(items: List[Dict[str, Any]], field: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for item in items:
        k = item.get(field, "unknown")
        counts[k] = counts.get(k, 0) + 1
    return counts


def _build_artifact_index(
    output_dir: Path,
    poam: Dict[str, Any],
    ssp: Dict[str, Any],
    run_id: str,
    generated_at: str,
) -> Dict[str, Any]:
    poam_path = output_dir / "poam.json"
    ssp_path = output_dir / "ssp.json"
    return {
        "schema_version": "1.0",
        "plane": "evidence-to-oscal",
        "generated_at": generated_at,
        "run_id": run_id,
        "artifacts": {
            "poam": {
                "path": str(poam_path),
                "hash": _stable_hash(poam),
                "total_items": poam["summary"]["total_items"],
            },
            "ssp": {
                "path": str(ssp_path),
                "hash": _stable_hash(ssp),
                "total_controls": ssp["summary"]["total_controls"],
                "coverage": ssp["summary"]["coverage"],
            },
        },
    }


# ---------------------------------------------------------------------------
# Public entry-point
# ---------------------------------------------------------------------------

def generate_oscal(
    evidence_dir: str,
    output_dir: str,
    config_path: Optional[str] = None,
) -> None:
    """Generate OSCAL artifacts (POA&M + SSP) from a Plane 3 evidence bundle.

    This is the sole public interface of this module.  Intentionally pure
    beyond the artifact I/O: no CLI, no global state, no network calls.

    Parameters
    ----------
    evidence_dir:
        Path to the evidence bundle directory produced by Plane 3
        (must contain bundle.json and evidence.jsonl).
    output_dir:
        Destination directory for OSCAL artifacts.  Created automatically.
        Writes: poam.json, ssp.json, artifact-index.json.
    config_path:
        Optional path to oscal-generate.json config file.
    """
    src_dir = Path(evidence_dir)
    dst_dir = Path(output_dir)
    log_path = _derive_log_path(dst_dir)
    logger = _setup_logger(log_path)

    logger.info("generate_oscal started")
    logger.info("  evidence_dir = %s", src_dir)
    logger.info("  output_dir   = %s", dst_dir)
    logger.info("  config_path  = %s", config_path or "(none)")
    logger.info("  log_path     = %s", log_path)

    # 1. Load inputs
    logger.info("Loading evidence bundle …")
    bundle = _load_bundle(src_dir)
    logger.info(
        "Bundle loaded: run_id=%s  total_records=%d",
        bundle.get("run_id", "?"),
        bundle.get("manifest", {}).get("total_records", 0),
    )

    logger.info("Loading evidence records …")
    records = _load_evidence_records(src_dir)
    logger.info("Loaded %d evidence record(s)", len(records))

    cfg = _load_config(config_path)
    logger.info("Config loaded: %d top-level keys", len(cfg))

    # 2. Generate artifacts
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    run_id = f"oscal-gen-{uuid4().hex}"

    logger.info("Generating POA&M …")
    poam_items = _build_poam_items(records, cfg)
    poam = _build_poam_envelope(poam_items, bundle, run_id, generated_at, cfg)
    logger.info(
        "POA&M: %d item(s) — by_severity=%s",
        len(poam_items),
        poam["summary"]["by_severity"],
    )

    logger.info("Generating SSP …")
    requirements = _build_implemented_requirements(records, cfg)
    ssp = _build_ssp_envelope(requirements, bundle, run_id, generated_at, cfg)
    logger.info(
        "SSP: %d control(s) — implemented=%d  coverage=%.1f%%",
        ssp["summary"]["total_controls"],
        ssp["summary"]["implemented"],
        ssp["summary"]["coverage"] * 100,
    )

    # 3. Write artifacts
    dst_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Writing poam.json …")
    _write_json(dst_dir / "poam.json", poam)

    logger.info("Writing ssp.json …")
    _write_json(dst_dir / "ssp.json", ssp)

    logger.info("Writing artifact-index.json …")
    index = _build_artifact_index(dst_dir, poam, ssp, run_id, generated_at)
    _write_json(dst_dir / "artifact-index.json", index)

    logger.info(
        "generate_oscal complete — run_id=%s  poam_items=%d  ssp_controls=%d",
        run_id,
        len(poam_items),
        ssp["summary"]["total_controls"],
    )

