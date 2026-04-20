"""uiao.evidence.builder — KSI → Evidence Bundle (Plane 3).

Contract
--------
Input  : KSI result JSON file     (./output/ksi/{source}.ksi.json)
Config : optional build config    (./config/evidence-build.json)
Output : evidence bundle dir      (./output/evidence/{source}/)
           {source}/bundle.json       — canonical envelope
           {source}/evidence.jsonl    — one EvidenceRecord per line (NDJSON)
           {source}/hashes/           — per-record SHA-256 sidecar files
           {source}/provenance/       — per-record provenance JSON files
Log    : ./output/logs/{timestamp}-evidence-build.log

Public entry-point
------------------
    build_evidence(ksi_path, output_dir, config_path=None)

Functional guarantees
---------------------
* Deterministic — identical KSI JSON + config always produces identical output.
* No external calls — purely in-process transformation.
* No SCuBA knowledge — reads only the canonical KSI envelope from Plane 2.
* No IR knowledge — does not re-read the IR file.
* No POA&M / SSP logic — single-responsibility plane.
* No cross-layer imports beyond uiao.models.evidence and stdlib.
* Immutable records — each EvidenceRecord is written once; never overwritten.
* Stable hashing — SHA-256 of canonical JSON, sorted keys, no floats.

Mutation rules (mirrors Copilot Plane 3 spec)
---------------------------------------------
  KSI verdict = pass        -> EvidenceRecord status "satisfied",   fresh=True
  KSI verdict = fail        -> EvidenceRecord status "not-satisfied", fresh=True
  KSI verdict = inconclusive-> EvidenceRecord status "not-applicable", fresh=False
  KSI verdict = excluded    -> EvidenceRecord status "not-applicable", fresh=False
"""
from __future__ import annotations

import hashlib
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

# ---------------------------------------------------------------------------
# Status mapping
# ---------------------------------------------------------------------------

_VERDICT_TO_STATUS: Dict[str, str] = {
    "pass": "satisfied",
    "fail": "not-satisfied",
    "inconclusive": "not-applicable",
    "excluded": "not-applicable",
}

_VERDICT_FRESH: Dict[str, bool] = {
    "pass": True,
    "fail": True,
    "inconclusive": False,
    "excluded": False,
}


# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------

def _setup_logger(log_path: Path) -> logging.Logger:
    """Emit to both stderr and a timestamped log file."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(f"uiao.evidence.builder.{uuid4().hex[:8]}")
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
    """Derive log path: <output_dir>/../../logs/{ts}-evidence-build.log"""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return output_dir.parent.parent / "logs" / f"{ts}Z-evidence-build.log"


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def _load_ksi(ksi_path: Path) -> Dict[str, Any]:
    """Load and validate a canonical KSI JSON envelope."""
    with ksi_path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(
            f"KSI file must deserialize to a dict, got {type(data).__name__}"
        )
    if "ksi" not in data:
        raise ValueError("KSI envelope missing required top-level key: 'ksi'")
    return data  # type: ignore[return-value]


def _load_config(config_path: Optional[str]) -> Dict[str, Any]:
    """Load optional build config. Returns {} when path is None/missing."""
    if config_path is None:
        return {}
    cfg = Path(config_path)
    if not cfg.exists():
        return {}
    with cfg.open(encoding="utf-8") as fh:
        return json.load(fh)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Record construction
# ---------------------------------------------------------------------------

def _canonical_json(data: Any) -> str:
    """Deterministic JSON serialization (sorted keys, no trailing whitespace)."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


# Fields excluded from record hashing to ensure determinism across runs.
_VOLATILE_FIELDS = frozenset({"id", "run_id", "generated_at", "collected_at", "provenance"})


def _stable_hash(data: Any) -> str:
    """Stable SHA-256 hex digest of the canonical JSON representation.

    When *data* is a dict, volatile fields (run_id, generated_at, id,
    collected_at) are excluded so the hash is identical across independent
    runs that process the same KSI input.
    """
    if isinstance(data, dict):
        stable: Any = {k: v for k, v in data.items() if k not in _VOLATILE_FIELDS}
    else:
        stable = data
    return hashlib.sha256(_canonical_json(stable).encode("utf-8")).hexdigest()


def _ksi_result_to_evidence_record(
    result: Dict[str, Any],
    run_id: str,
    generated_at: str,
    cfg: Dict[str, Any],
) -> Dict[str, Any]:
    """Convert a single KSI result dict to a canonical EvidenceRecord dict.

    The returned dict is serialisation-ready — all values are JSON-native types.

    Fields
    ------
    id              : deterministic "ev:{control_id}:{run_id[:8]}"
    control_id      : taken directly from the KSI result
    verdict         : original KSI verdict (pass/fail/inconclusive/excluded)
    status          : OSCAL-aligned status string
    fresh           : bool — whether the evidence is considered current
    rationale       : explanation from the KSI evaluator
    evidence_count  : number of IR evidence items that informed the verdict
    rule_key        : the rule key that triggered the verdict (may be null)
    generated_at    : ISO timestamp
    run_id          : parent KSI evaluation run id
    hash            : SHA-256 of this record's canonical JSON (self-referential
                      hash excluded to avoid circularity — see bundle hash)
    provenance      : { source, generated_at, version, collector_id }
    """
    collector_id: str = cfg.get("collector_id", "uiao-evidence-builder")
    version: str = cfg.get("version", "1.0")

    control_id = result.get("control_id", "")
    verdict = result.get("verdict", "inconclusive")
    status = _VERDICT_TO_STATUS.get(verdict, "not-applicable")
    fresh = _VERDICT_FRESH.get(verdict, False)

    record: Dict[str, Any] = {
        "id": f"ev:{control_id}:{run_id[:8]}",
        "control_id": control_id,
        "verdict": verdict,
        "status": status,
        "fresh": fresh,
        "rationale": result.get("rationale", ""),
        "evidence_count": result.get("evidence_count", 0),
        "rule_key": result.get("rule_key"),
        "generated_at": generated_at,
        "run_id": run_id,
        "provenance": {
            "source": "ksi-to-evidence-builder",
            "generated_at": generated_at,
            "version": version,
            "collector_id": collector_id,
        },
    }
    return record


# ---------------------------------------------------------------------------
# Bundle assembly
# ---------------------------------------------------------------------------

def _write_evidence_jsonl(records: List[Dict[str, Any]], dst: Path) -> None:
    """Write records as newline-delimited JSON (one record per line)."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(_canonical_json(rec) + "\n")


def _write_hash_sidecars(records: List[Dict[str, Any]], hashes_dir: Path) -> None:
    """Write one <id>.sha256 sidecar per record into hashes_dir."""
    hashes_dir.mkdir(parents=True, exist_ok=True)
    for rec in records:
        safe_id = rec["id"].replace(":", "_").replace("/", "_")
        sidecar = hashes_dir / f"{safe_id}.sha256"
        sidecar.write_text(_stable_hash(rec) + "\n", encoding="utf-8")


def _write_provenance_files(records: List[Dict[str, Any]], prov_dir: Path) -> None:
    """Write one <id>.provenance.json per record into prov_dir."""
    prov_dir.mkdir(parents=True, exist_ok=True)
    for rec in records:
        safe_id = rec["id"].replace(":", "_").replace("/", "_")
        prov_file = prov_dir / f"{safe_id}.provenance.json"
        prov_file.write_text(
            json.dumps(rec["provenance"], indent=2, sort_keys=True),
            encoding="utf-8",
        )


def _build_manifest(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build the bundle manifest: summary counts + per-record hash index."""
    total = len(records)
    by_verdict: Dict[str, int] = {}
    by_status: Dict[str, int] = {}
    hash_index: Dict[str, str] = {}

    for rec in records:
        by_verdict[rec["verdict"]] = by_verdict.get(rec["verdict"], 0) + 1
        by_status[rec["status"]] = by_status.get(rec["status"], 0) + 1
        hash_index[rec["id"]] = _stable_hash(rec)

    return {
        "total_records": total,
        "by_verdict": by_verdict,
        "by_status": by_status,
        "hash_index": hash_index,
    }


def _write_bundle_json(
    bundle_dir: Path,
    records: List[Dict[str, Any]],
    ksi_envelope: Dict[str, Any],
    run_id: str,
    generated_at: str,
    cfg: Dict[str, Any],
) -> None:
    """Write the canonical bundle.json envelope."""
    manifest = _build_manifest(records)
    # Bundle hash = SHA-256 of the sorted hash_index values (stable across reruns)
    sorted_hashes = _canonical_json(sorted(manifest["hash_index"].values()))
    bundle_hash = hashlib.sha256(sorted_hashes.encode("utf-8")).hexdigest()

    bundle: Dict[str, Any] = {
        "schema_version": "1.0",
        "plane": "ksi-to-evidence",
        "generated_at": generated_at,
        "run_id": run_id,
        "source_ksi_run_id": ksi_envelope.get("run_id", ""),
        "source_ksi_plane": ksi_envelope.get("plane", ""),
        "hashing_algorithm": cfg.get("hashing_algorithm", "sha256"),
        "collector_id": cfg.get("collector_id", "uiao-evidence-builder"),
        "bundle_hash": bundle_hash,
        "manifest": manifest,
    }
    dst = bundle_dir / "bundle.json"
    dst.write_text(json.dumps(bundle, indent=2, sort_keys=True), encoding="utf-8")


# ---------------------------------------------------------------------------
# Public entry-point
# ---------------------------------------------------------------------------

def build_evidence(
    ksi_path: str,
    output_dir: str,
    config_path: Optional[str] = None,
) -> None:
    """Build a canonical evidence bundle from a KSI result JSON file.

    This is the sole public interface of this module.  It is intentionally
    *pure* beyond the bundle directory I/O: no CLI, no global state, no
    external network calls.

    Parameters
    ----------
    ksi_path:
        Path to the KSI result JSON produced by Plane 2.
    output_dir:
        Destination directory for the evidence bundle.  The directory is
        created automatically.  Contents:
            bundle.json          — canonical envelope
            evidence.jsonl       — NDJSON evidence records
            hashes/              — per-record SHA-256 sidecars
            provenance/          — per-record provenance JSON files
    config_path:
        Optional path to evidence-build.json config file.
    """
    src = Path(ksi_path)
    dst_dir = Path(output_dir)
    log_path = _derive_log_path(dst_dir)
    logger = _setup_logger(log_path)

    logger.info("build_evidence started")
    logger.info("  ksi_path   = %s", src)
    logger.info("  output_dir = %s", dst_dir)
    logger.info("  config     = %s", config_path or "(none)")
    logger.info("  log_path   = %s", log_path)

    # 1. Load inputs
    logger.info("Loading KSI envelope …")
    ksi = _load_ksi(src)
    logger.info(
        "KSI loaded: plane=%s  run_id=%s  total_controls=%d",
        ksi.get("plane", "?"),
        ksi.get("run_id", "?"),
        ksi.get("summary", {}).get("total_controls", 0),
    )

    cfg = _load_config(config_path)
    logger.info("Config loaded: %d top-level keys", len(cfg))

    # 2. Build output directory tree
    dst_dir.mkdir(parents=True, exist_ok=True)
    hashes_dir = dst_dir / "hashes"
    prov_dir = dst_dir / "provenance"

    # 3. Convert each KSI result to an EvidenceRecord
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    run_id = f"ev-build-{uuid4().hex}"
    results: List[Dict[str, Any]] = ksi.get("ksi", [])

    records: List[Dict[str, Any]] = []
    for result in results:
        rec = _ksi_result_to_evidence_record(result, run_id, generated_at, cfg)
        records.append(rec)
        logger.debug(
            "  %-40s  verdict=%-14s  status=%s  fresh=%s",
            rec["control_id"],
            rec["verdict"],
            rec["status"],
            rec["fresh"],
        )

    logger.info("Built %d EvidenceRecord(s)", len(records))

    # 4. Write bundle artefacts
    logger.info("Writing evidence.jsonl …")
    _write_evidence_jsonl(records, dst_dir / "evidence.jsonl")

    logger.info("Writing hash sidecars …")
    _write_hash_sidecars(records, hashes_dir)

    logger.info("Writing provenance files …")
    _write_provenance_files(records, prov_dir)

    logger.info("Writing bundle.json …")
    _write_bundle_json(dst_dir, records, ksi, run_id, generated_at, cfg)

    # 5. Summary
    satisfied = sum(1 for r in records if r["status"] == "satisfied")
    not_satisfied = sum(1 for r in records if r["status"] == "not-satisfied")
    not_applicable = sum(1 for r in records if r["status"] == "not-applicable")
    logger.info(
        "Bundle complete: total=%d  satisfied=%d  not-satisfied=%d  not-applicable=%d",
        len(records),
        satisfied,
        not_satisfied,
        not_applicable,
    )
    logger.info("Output directory : %s", dst_dir)
    logger.info("build_evidence complete — run_id=%s", run_id)

