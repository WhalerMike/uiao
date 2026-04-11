"""uiao_core.scuba.transform — SCuBA → IR transformation (Plane 1).

Contract
--------
Input  : SCuBA JSON/YAML file  (./input/scuba/{source}.json|yaml)
Config : optional transform config (./config/scuba-transform.json)
Output : canonical IR JSON file    (./output/ir/{source}.ir.json)
Log    : ./output/logs/{timestamp}-scuba-transform.log

Public entry-point
------------------
    transform_scuba_to_ir(input_path, output_path, config_path=None)

    This module is intentionally *pure*: no CLI, no side-effects beyond
    writing the two output files. All I/O is funnelled through the three
    path parameters so the function is trivially testable without mocking.
"""
from __future__ import annotations

import json
import logging
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from uiao_core.ir.adapters.scuba.transformer import (
    SCuBATransformResult,
    transform_scuba_to_ir as _core_transform,
)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_LOG_FMT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_LOG_DATEFMT = "%Y-%m-%dT%H:%M:%S"


def _build_logger(log_path: Optional[Path]) -> logging.Logger:
    """Return a logger that writes to *log_path* (and stderr)."""
    logger = logging.getLogger("uiao.scuba.transform")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    formatter = logging.Formatter(_LOG_FMT, datefmt=_LOG_DATEFMT)

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)
    logger.addHandler(stderr_handler)

    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def _load_config(config_path: Optional[str]) -> Dict[str, Any]:
    """Load and return a config dict, or empty dict if absent/invalid."""
    if not config_path:
        return {}
    p = Path(config_path)
    if not p.exists():
        return {}
    with p.open(encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) if p.suffix in {".yaml", ".yml"} else json.load(fh)
    return cfg if isinstance(cfg, dict) else {}


def _resolve_log_path(output_path: Path) -> Path:
    """Derive the log file path from the IR output path."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_dir = output_path.parent.parent / "logs"
    return log_dir / f"{timestamp}-scuba-transform.log"


def _apply_config_overrides(
    cfg: Dict[str, Any],
    scuba: Dict[str, Any],
) -> Dict[str, Any]:
    """Apply config-driven field overrides to the raw SCuBA dict (non-destructive copy)."""
    if not cfg:
        return scuba
    result = dict(scuba)
    # Config key: drop_statuses → filter out ksi_results with these statuses
    drop = set(cfg.get("drop_statuses", []))
    if drop and "ksi_results" in result:
        result["ksi_results"] = [
            r for r in result["ksi_results"]
            if r.get("status", "").upper() not in drop
        ]
    return result


def _ir_result_to_dict(result: SCuBATransformResult) -> Dict[str, Any]:
    """Serialize a SCuBATransformResult to a canonical IR dict."""
    return {
        "schema_version": "1.0",
        "plane": "scuba-to-ir",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": result.run_id,
        "summary": {
            "total": len(result.evidence),
            "pass": result.pass_count,
            "warn": result.warn_count,
            "fail": result.fail_count,
            "unmapped_ksi_ids": result.unmapped_ksi_ids,
        },
        "evidence": [json.loads(e.to_canonical()) for e in result.evidence],
        "controls": [json.loads(c.to_canonical()) for c in result.controls],
        "policies": [json.loads(p.to_canonical()) for p in result.policies],
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def transform_scuba_to_ir(
    input_path: str,
    output_path: str,
    config_path: Optional[str] = None,
) -> None:
    """Transform a SCuBA JSON/YAML assessment file into canonical IR JSON.

    Parameters
    ----------
    input_path:
        Path to the SCuBA assessment file (JSON or YAML).
    output_path:
        Destination path for the IR JSON artefact. Parent directories
        are created automatically.
    config_path:
        Optional path to a transform config (JSON or YAML). When absent
        or pointing to a non-existent file the transform runs with defaults.

    Raises
    ------
    FileNotFoundError
        When *input_path* does not exist.
    ValueError
        When *input_path* cannot be parsed as JSON or YAML.
    """
    src = Path(input_path)
    dst = Path(output_path)

    if not src.exists():
        raise FileNotFoundError(f"SCuBA input not found: {src}")

    log_path = _resolve_log_path(dst)
    logger = _build_logger(log_path)
    logger.info("Starting SCuBA → IR transform: %s", src)

    # 1. Load config
    cfg = _load_config(config_path)
    tenant_boundary_id: Optional[str] = cfg.get("tenant_boundary_id")

    # 2. Parse SCuBA input
    with src.open(encoding="utf-8") as fh:
        scuba_data: Dict[str, Any] = (
            yaml.safe_load(fh) or {}
            if src.suffix in {".yaml", ".yml"}
            else json.load(fh)
        )

    # 3. Apply config overrides
    scuba_data = _apply_config_overrides(cfg, scuba_data)

    # 4. Write patched SCuBA to a temp file for the core transformer
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        delete=False,
        encoding="utf-8",
    ) as tmp:
        json.dump(scuba_data, tmp, ensure_ascii=False)
        tmp_path = Path(tmp.name)

    try:
        # 5. Run core transformer
        logger.debug("Running core transformer ...")
        result: SCuBATransformResult = _core_transform(
            tmp_path, tenant_boundary_id=tenant_boundary_id
        )
    finally:
        tmp_path.unlink(missing_ok=True)

    logger.info(
        "Transform complete: PASS=%d WARN=%d FAIL=%d unmapped=%d",
        result.pass_count,
        result.warn_count,
        result.fail_count,
        len(result.unmapped_ksi_ids),
    )

    # 6. Serialize IR to canonical JSON
    ir_dict = _ir_result_to_dict(result)

    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8") as fh:
        json.dump(ir_dict, fh, indent=2, ensure_ascii=False)

    logger.info("IR written to %s", dst)
