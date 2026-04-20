"""uiao.ksi.evaluate — IR → KSI evaluation (Plane 2).

Contract
--------
Input  : IR JSON file             (./output/ir/{source}.ir.json)
Config : optional rules config    (./config/ksi-rules.json)
Output : KSI results JSON file    (./output/ksi/{source}.ksi.json)
Log    : ./output/logs/{timestamp}-ksi-eval.log

Public entry-point
------------------
    evaluate_ksi(ir_path, output_path, config_path=None)

Functional guarantees
---------------------
* Deterministic — identical IR + config always produces identical output.
* No external calls — purely in-process rule evaluation.
* No SCuBA knowledge — reads only the canonical IR envelope.
* No Evidence generation — results contain pass/fail metadata only.
* No POA&M / SSP logic — single-responsibility plane.
* No cross-layer imports — only stdlib + uiao.ir.models.core.

The evaluator walks the \"controls\" list in the IR envelope and runs
every control through `_evaluate_control`.  Each KSI result records the
control id, whether it passed, the verdict, the matched rule key (if
any), and a short rationale string so downstream planes can trace
decisions back to their inputs without needing to re-run the evaluator.
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
# Logging helpers (mirrors the pattern in scuba/transform.py)
# ---------------------------------------------------------------------------

def _setup_logger(log_path: Path) -> logging.Logger:
    """Emit to both stderr and a timestamped log file."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(f"uiao.ksi.evaluate.{uuid4().hex[:8]}")
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


def _derive_log_path(output_path: Path) -> Path:
    """Mirror the log-path convention: <out>/../logs/{ts}-ksi-eval.log"""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return output_path.parent.parent / "logs" / f"{ts}Z-ksi-eval.log"


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def _load_ir(ir_path: Path) -> Dict[str, Any]:
    """Load a canonical IR JSON envelope and return the raw dict."""
    with ir_path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(
            f"IR file must deserialize to a dict, got {type(data).__name__}"
        )
    return data  # type: ignore[return-value]


def _load_rules(config_path: Optional[str]) -> Dict[str, Any]:
    """Load optional KSI rules config.  Returns {} when path is None/missing."""
    if config_path is None:
        return {}
    cfg = Path(config_path)
    if not cfg.exists():
        return {}
    with cfg.open(encoding="utf-8") as fh:
        return json.load(fh)  # type: ignore[return-value]


def _write_ksi(dst: Path, payload: Dict[str, Any]) -> None:
    """Write the canonical KSI JSON envelope, creating parent dirs as needed."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Rule evaluation — the ONLY place where rule logic lives
# ---------------------------------------------------------------------------

# Default pass-criteria behaviour when no explicit rule is configured:
#   A control is considered passing when its evidence item's evaluation
#   block indicates success.  The transformer may use either:
#     - evaluation.result == "pass"   (string-based)
#     - evaluation.passed == True     (boolean-based)
#   Both are supported.  If no evidence is present, the verdict is
#   "inconclusive" rather than "fail" — absence of evidence != failure.

_VERDICT_PASS = "pass"
_VERDICT_FAIL = "fail"
_VERDICT_INCONCLUSIVE = "inconclusive"
_VERDICT_EXCLUDED = "excluded"


def _evidence_passes(ev: Dict[str, Any]) -> bool:
    """Check whether an evidence item indicates a passing result.

    Supports two serialization conventions used by IR transformers:
      - evaluation.result == "pass"   (string-based)
      - evaluation.passed == True     (boolean-based, used by SCuBA transformer)
    """
    evaluation = ev.get("evaluation", {})
    # String-based: evaluation.result == "pass"
    if evaluation.get("result") == _VERDICT_PASS:
        return True
    # Boolean-based: evaluation.passed == True
    if evaluation.get("passed") is True:
        return True
    # Also check data.status for direct SCuBA status passthrough
    if ev.get("data", {}).get("status") == "PASS":
        return True
    return False


def _evaluate_control(
    control: Dict[str, Any],
    evidence_index: Dict[str, List[Dict[str, Any]]],
    rules: Dict[str, Any],
) -> Dict[str, Any]:
    """Evaluate one IR control against KSI rules.

    Parameters
    ----------
    control:
        A single element from the IR envelope's \"controls\" list.
    evidence_index:
        Dict mapping control_id -> list of IR Evidence dicts for fast lookup.
    rules:
        The parsed ksi-rules.json config (may be empty).

    Returns
    -------
    A KSI result dict:
        {
          \"control_id\": str,
          \"verdict\":    \"pass\" | \"fail\" | \"inconclusive\" | \"excluded\",
          \"passed\":     bool,
          \"rule_key\":   str | null,
          \"rationale\":  str,
          \"evidence_count\": int,
        }
    """
    cid = control.get("id", "")

    # Exclusions from config take priority
    excluded_controls: List[str] = rules.get("exclude_controls", [])
    if cid in excluded_controls:
        return {
            "control_id": cid,
            "verdict": _VERDICT_EXCLUDED,
            "passed": False,
            "rule_key": "exclude_controls",
            "rationale": "Control explicitly excluded by ksi-rules.json",
            "evidence_count": 0,
        }

    evidence_items = evidence_index.get(cid, [])

    # -------------------------------------------------------------------
    # Override rules: per-control expected_state from ksi-rules.json
    # -------------------------------------------------------------------
    override_rules: Dict[str, Any] = rules.get("control_overrides", {})
    if cid in override_rules:
        override = override_rules[cid]
        expected = override.get("expected_result", _VERDICT_PASS)
        matched = any(
            _evidence_passes(ev) if expected == _VERDICT_PASS
            else ev.get("evaluation", {}).get("result") == expected
            for ev in evidence_items
        )
        verdict = _VERDICT_PASS if matched else _VERDICT_FAIL
        return {
            "control_id": cid,
            "verdict": verdict,
            "passed": verdict == _VERDICT_PASS,
            "rule_key": f"control_overrides.{cid}",
            "rationale": (
                f"Override rule: expected result='{expected}', "
                f"matched={matched} across {len(evidence_items)} evidence item(s)"
            ),
            "evidence_count": len(evidence_items),
        }

    # -------------------------------------------------------------------
    # Default evaluation logic
    # -------------------------------------------------------------------
    if not evidence_items:
        return {
            "control_id": cid,
            "verdict": _VERDICT_INCONCLUSIVE,
            "passed": False,
            "rule_key": None,
            "rationale": "No evidence items reference this control; cannot determine pass/fail",
            "evidence_count": 0,
        }

    # Pass if ANY evidence item indicates a passing result.
    # Supports both evaluation.result=="pass" and evaluation.passed==True.
    # Conservative: if mixed evidence, control still passes if at least one
    # item passes AND the config does not require all to pass.
    require_all: bool = rules.get("require_all_evidence_pass", False)

    passing = [ev for ev in evidence_items if _evidence_passes(ev)]

    if require_all:
        verdict = _VERDICT_PASS if len(passing) == len(evidence_items) else _VERDICT_FAIL
        rationale = (
            f"require_all_evidence_pass=true: "
            f"{len(passing)}/{len(evidence_items)} evidence items passed"
        )
    else:
        verdict = _VERDICT_PASS if passing else _VERDICT_FAIL
        rationale = (
            f"{len(passing)}/{len(evidence_items)} evidence items passed"
        )

    return {
        "control_id": cid,
        "verdict": verdict,
        "passed": verdict == _VERDICT_PASS,
        "rule_key": None,
        "rationale": rationale,
        "evidence_count": len(evidence_items),
    }


def _build_evidence_index(
    evidence: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """Build control_id -> [evidence, ...] lookup from the IR evidence list."""
    index: Dict[str, List[Dict[str, Any]]] = {}
    for ev in evidence:
        cid = ev.get("control_id")
        if cid:
            index.setdefault(cid, []).append(ev)
    return index


# ---------------------------------------------------------------------------
# Summary helpers
# ---------------------------------------------------------------------------

def _build_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute aggregate counts for the KSI envelope."""
    total = len(results)
    passing = sum(1 for r in results if r["verdict"] == _VERDICT_PASS)
    failing = sum(1 for r in results if r["verdict"] == _VERDICT_FAIL)
    inconclusive = sum(1 for r in results if r["verdict"] == _VERDICT_INCONCLUSIVE)
    excluded = sum(1 for r in results if r["verdict"] == _VERDICT_EXCLUDED)
    score = round(passing / total, 4) if total > 0 else 0.0
    return {
        "total_controls": total,
        "passing": passing,
        "failing": failing,
        "inconclusive": inconclusive,
        "excluded": excluded,
        "pass_rate": score,
    }


def _envelope_hash(results: List[Dict[str, Any]]) -> str:
    """Stable SHA-256 of the sorted results payload."""
    canonical = json.dumps(results, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Public entry-point
# ---------------------------------------------------------------------------

def evaluate_ksi(
    ir_path: str,
    output_path: str,
    config_path: Optional[str] = None,
) -> None:
    """Evaluate an IR file against KSI rules and write canonical KSI JSON.

    This is the sole public interface of this module.  It is intentionally
    *pure* beyond the two file I/O operations: no CLI, no global state, no
    external network calls.

    Parameters
    ----------
    ir_path:
        Absolute or relative path to the IR JSON envelope produced by Plane 1.
    output_path:
        Destination path for the KSI result JSON.  Parent directories are
        created automatically.
    config_path:
        Optional path to a ksi-rules.json config file.  Silently ignored
        when absent.
    """
    src = Path(ir_path)
    dst = Path(output_path)
    log_path = _derive_log_path(dst)
    logger = _setup_logger(log_path)

    logger.info("evaluate_ksi started")
    logger.info("  ir_path     = %s", src)
    logger.info("  output_path = %s", dst)
    logger.info("  config_path = %s", config_path or "(none)")
    logger.info("  log_path    = %s", log_path)

    # 1. Load inputs
    logger.info("Loading IR envelope …")
    ir = _load_ir(src)
    logger.info(
        "IR loaded: schema_version=%s  plane=%s",
        ir.get("schema_version", "?"),
        ir.get("plane", "?"),
    )

    logger.info("Loading KSI rules config …")
    rules = _load_rules(config_path)
    logger.info("Rules loaded: %d top-level keys", len(rules))

    # 2. Extract controls + evidence from IR
    controls: List[Dict[str, Any]] = ir.get("controls", [])
    evidence: List[Dict[str, Any]] = ir.get("evidence", [])
    logger.info(
        "IR contains %d control(s) and %d evidence item(s)",
        len(controls),
        len(evidence),
    )

    # 3. Build evidence lookup
    evidence_index = _build_evidence_index(evidence)

    # 4. Evaluate each control
    results: List[Dict[str, Any]] = []
    for ctrl in controls:
        result = _evaluate_control(ctrl, evidence_index, rules)
        results.append(result)
        logger.debug(
            "  %-40s  verdict=%-14s  evidence=%d",
            result["control_id"],
            result["verdict"],
            result["evidence_count"],
        )

    # 5. Build summary
    summary = _build_summary(results)
    logger.info(
        "Evaluation complete: total=%d  pass=%d  fail=%d  "
        "inconclusive=%d  excluded=%d  pass_rate=%.2f%%",
        summary["total_controls"],
        summary["passing"],
        summary["failing"],
        summary["inconclusive"],
        summary["excluded"],
        summary["pass_rate"] * 100,
    )

    # 6. Write canonical KSI JSON
    run_id = f"ksi-eval-{uuid4().hex}"
    payload: Dict[str, Any] = {
        "schema_version": "1.0",
        "plane": "ir-to-ksi",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "run_id": run_id,
        "source_ir": str(src),
        "summary": summary,
        "results_hash": _envelope_hash(results),
        "ksi": results,
    }
    _write_ksi(dst, payload)
    logger.info("KSI output written to %s", dst)
    logger.info("evaluate_ksi complete — run_id=%s", run_id)

