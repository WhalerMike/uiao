"""Normalize raw Invoke-SCuBA output into UIAO pipeline-ready format.

Real ScubaGear output comes in two forms:
  1. A single ScubaResults.json with a "TestResults" array
  2. Per-product files: MS.AAD.json, MS.EXO.json, MS.TEAMS.json, etc.

This module reads either form and produces the normalized JSON that
Plane 1's transform_scuba_to_ir() expects:

    {
      "assessment_metadata": { ... },
      "tenant": { ... },
      "ksi_results": [
        { "ksi_id": "KSI-AC-01", "status": "PASS", "severity": "...", "details": "..." },
        ...
      ]
    }

The mapping chain is:
  ScubaGear PolicyId  ──►  NIST SP 800-53 control  ──►  UIAO KSI ID

Usage:
    python -m uiao_impl.ir.adapters.scuba.normalize_scuba \\
        --input path/to/ScubaResults \\
        --output normalized.json

    Or programmatically:
        from uiao_impl.ir.adapters.scuba.normalize_scuba import normalize_scuba
        result = normalize_scuba("path/to/ScubaResults")
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Import the canonical mappings
# ---------------------------------------------------------------------------

# PolicyId -> NIST control (e.g. "MS.AAD.1.1v1" -> "IA-2(1)")
try:
    from uiao_impl.adapters.scuba_adapter import SCUBA_TO_KSI_MAP
except ImportError:
    # Fallback for standalone use — will be populated from file
    SCUBA_TO_KSI_MAP: Dict[str, str] = {}

# NIST control -> KSI metadata (loaded at runtime from rules/ksi/)
_CONTROL_TO_KSI: Optional[Dict[str, Dict[str, Any]]] = None


def _load_control_to_ksi(repo_root: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """Load the NIST control -> KSI mapping from the rules directory."""
    global _CONTROL_TO_KSI
    if _CONTROL_TO_KSI is not None:
        return _CONTROL_TO_KSI

    candidates = [
        repo_root / "rules" / "ksi" / "uiao-control-to-ksi-mapping.yaml" if repo_root else None,
        Path(__file__).resolve().parents[4] / "rules" / "ksi" / "uiao-control-to-ksi-mapping.yaml",
        Path.cwd() / "rules" / "ksi" / "uiao-control-to-ksi-mapping.yaml",
    ]
    for p in candidates:
        if p and p.exists():
            with open(p, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            _CONTROL_TO_KSI = data.get("control_to_ksi", {})
            logger.info("Loaded control-to-KSI mapping: %d controls from %s", len(_CONTROL_TO_KSI), p)
            return _CONTROL_TO_KSI

    logger.warning("control-to-ksi-mapping.yaml not found; KSI resolution will be limited")
    _CONTROL_TO_KSI = {}
    return _CONTROL_TO_KSI


# ---------------------------------------------------------------------------
# ScubaGear pass/fail interpretation
# ---------------------------------------------------------------------------

_PASS_VALUES = {"Pass", "pass", "PASS", "true", "True", True}
_WARN_VALUES = {"Warning", "warning", "WARN", "Warn"}


def _interpret_status(requirement_met: Any) -> str:
    """Convert ScubaGear RequirementMet to PASS/WARN/FAIL."""
    if requirement_met in _PASS_VALUES:
        return "PASS"
    if requirement_met in _WARN_VALUES:
        return "WARN"
    return "FAIL"


# ---------------------------------------------------------------------------
# Input discovery
# ---------------------------------------------------------------------------

def discover_scuba_input(input_path: Path) -> Tuple[str, List[Dict[str, Any]]]:
    """Discover and load ScubaGear output from a path.

    Returns:
        (format_description, list_of_test_result_dicts)
    """
    input_path = Path(input_path)

    # Case 1: Direct file
    if input_path.is_file():
        return _load_single_file(input_path)

    # Case 2: Directory — look for ScubaResults.json first
    if input_path.is_dir():
        combined = input_path / "ScubaResults.json"
        if combined.exists():
            return _load_single_file(combined)

        # Look for per-product files (MS.AAD.json, MS.EXO.json, etc.)
        product_files = sorted(input_path.glob("MS.*.json"))
        if product_files:
            all_results = []
            for pf in product_files:
                _, results = _load_single_file(pf)
                all_results.extend(results)
            return f"per-product ({len(product_files)} files)", all_results

        # Check nested directories (ScubaGear sometimes creates date-stamped subdirs)
        for subdir in sorted(input_path.iterdir()):
            if subdir.is_dir():
                sub_combined = subdir / "ScubaResults.json"
                if sub_combined.exists():
                    return _load_single_file(sub_combined)
                sub_products = sorted(subdir.glob("MS.*.json"))
                if sub_products:
                    all_results = []
                    for pf in sub_products:
                        _, results = _load_single_file(pf)
                        all_results.extend(results)
                    return f"nested per-product ({len(sub_products)} files in {subdir.name})", all_results

    raise FileNotFoundError(
        f"No ScubaGear output found at {input_path}. "
        "Expected ScubaResults.json or MS.*.json files."
    )


def _load_single_file(path: Path) -> Tuple[str, List[Dict[str, Any]]]:
    """Load a single ScubaGear JSON file and extract TestResults."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return f"direct-list ({path.name})", data

    # ScubaGear combined report: {"TestResults": [...]}
    if "TestResults" in data:
        return f"combined ({path.name})", data["TestResults"]

    # ScubaGear per-product: {"Results": [...]}
    if "Results" in data:
        return f"per-product ({path.name})", data["Results"]

    # Our existing normalized format (passthrough)
    if "ksi_results" in data:
        return f"already-normalized ({path.name})", data["ksi_results"]

    logger.warning("Unrecognized format in %s; attempting flat extraction", path)
    return f"unknown ({path.name})", []


# ---------------------------------------------------------------------------
# Policy -> KSI resolution
# ---------------------------------------------------------------------------

def _resolve_ksi(policy_id: str, nist_control: str, control_to_ksi: Dict) -> Dict[str, Any]:
    """Resolve a NIST control ID to KSI metadata.

    Returns dict with ksi_id, ksi_title, severity, category.
    Falls back to a synthetic KSI ID if no mapping exists.
    """
    # Try exact match first
    ksi_meta = control_to_ksi.get(nist_control)
    if ksi_meta:
        return ksi_meta

    # Try base control without enhancement (e.g. "SC-8(1)" -> "SC-8")
    base_control = nist_control.split("(")[0]
    ksi_meta = control_to_ksi.get(base_control)
    if ksi_meta:
        return ksi_meta

    # No mapping — return synthetic
    return {
        "ksi_id": f"KSI-UNMAPPED-{nist_control}",
        "ksi_title": f"Unmapped control {nist_control} (from {policy_id})",
        "severity": "Medium",
        "category": "other",
    }


# ---------------------------------------------------------------------------
# Main normalization function
# ---------------------------------------------------------------------------

def normalize_scuba(
    input_path: str | Path,
    tenant_id: str = "unknown-tenant",
    repo_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Normalize raw ScubaGear output into UIAO pipeline format.

    Args:
        input_path: Path to ScubaResults.json, a directory with MS.*.json,
                    or an already-normalized file.
        tenant_id: Tenant UUID for metadata.
        repo_root: Root of uiao-core repo (for finding KSI mapping file).

    Returns:
        Dict conforming to the scuba-normalized schema, ready for
        transform_scuba_to_ir().
    """
    input_path = Path(input_path)
    control_to_ksi = _load_control_to_ksi(repo_root)

    # Discover and load raw results
    format_desc, raw_results = discover_scuba_input(input_path)
    logger.info("Loaded %d raw results from %s (format: %s)", len(raw_results), input_path, format_desc)

    # Check if already in normalized format (has ksi_id field)
    if raw_results and "ksi_id" in raw_results[0]:
        logger.info("Input is already normalized; passing through")
        # Rebuild full envelope
        if input_path.is_file():
            with open(input_path, encoding="utf-8") as f:
                existing = json.load(f)
            if "ksi_results" in existing:
                return existing

    # Map each raw TestResult to a ksi_results entry
    ksi_results: List[Dict[str, str]] = []
    seen_ksi_ids: Dict[str, List[str]] = {}  # KSI ID -> list of policy IDs (for aggregation)
    unmapped_policies: List[str] = []

    now = datetime.now(timezone.utc).isoformat()

    for result in raw_results:
        policy_id = result.get("PolicyId", "")
        if not policy_id:
            continue

        # Step 1: PolicyId -> NIST control
        nist_control = SCUBA_TO_KSI_MAP.get(policy_id)
        if not nist_control:
            unmapped_policies.append(policy_id)
            continue

        # Step 2: NIST control -> KSI metadata
        ksi_meta = _resolve_ksi(policy_id, nist_control, control_to_ksi)
        ksi_id = ksi_meta["ksi_id"]

        # Step 3: Interpret pass/fail
        status = _interpret_status(result.get("RequirementMet", False))
        severity = ksi_meta.get("severity", "Medium").capitalize()

        # Step 4: Build details string
        description = result.get("Description", result.get("Requirement", ""))
        actual = result.get("ActualValue", "")
        details = f"{description}" if description else f"Policy {policy_id}"
        if actual:
            details += f" | Actual: {json.dumps(actual) if isinstance(actual, (dict, list)) else actual}"

        # Track for aggregation (multiple policies can map to same KSI)
        if ksi_id not in seen_ksi_ids:
            seen_ksi_ids[ksi_id] = []
        seen_ksi_ids[ksi_id].append(policy_id)

        ksi_results.append({
            "ksi_id": ksi_id,
            "status": status,
            "severity": severity,
            "details": details,
            "source_policy_id": policy_id,
            "nist_control": nist_control,
        })

    # Aggregate: when multiple policies map to the same KSI,
    # the KSI fails if ANY constituent policy fails (conservative)
    aggregated = _aggregate_by_ksi(ksi_results)

    # Build envelope
    normalized = {
        "assessment_metadata": {
            "assessment_date": now,
            "tool_version": "ScubaGear-normalized",
            "collector_host": "uiao-normalizer",
            "collector_user": "automated",
            "run_id": f"scuba-run-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
            "normalization": {
                "format_detected": format_desc,
                "raw_results_count": len(raw_results),
                "mapped_count": len(ksi_results),
                "unmapped_count": len(unmapped_policies),
                "unmapped_policies": unmapped_policies[:20],
                "aggregated_ksi_count": len(aggregated),
                "multi_policy_ksis": {
                    k: v for k, v in seen_ksi_ids.items() if len(v) > 1
                },
            },
        },
        "tenant": {
            "tenant_id": tenant_id,
        },
        "ksi_results": aggregated,
    }

    pass_count = sum(1 for r in aggregated if r["status"] == "PASS")
    warn_count = sum(1 for r in aggregated if r["status"] == "WARN")
    fail_count = sum(1 for r in aggregated if r["status"] == "FAIL")
    logger.info(
        "Normalization complete: %d KSIs (%d PASS, %d WARN, %d FAIL), %d unmapped policies",
        len(aggregated), pass_count, warn_count, fail_count, len(unmapped_policies),
    )

    return normalized


def _aggregate_by_ksi(results: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Aggregate multiple policy results into one entry per KSI.

    When multiple ScuBA policies map to the same KSI:
    - If ANY policy FAILS -> KSI = FAIL
    - Else if ANY policy WARNS -> KSI = WARN
    - Else -> KSI = PASS

    Details are concatenated. Source policy IDs are preserved.
    """
    from collections import OrderedDict

    buckets: OrderedDict[str, List[Dict[str, str]]] = OrderedDict()
    for r in results:
        ksi_id = r["ksi_id"]
        if ksi_id not in buckets:
            buckets[ksi_id] = []
        buckets[ksi_id].append(r)

    aggregated: List[Dict[str, str]] = []
    for ksi_id, entries in buckets.items():
        statuses = [e["status"] for e in entries]
        if "FAIL" in statuses:
            agg_status = "FAIL"
        elif "WARN" in statuses:
            agg_status = "WARN"
        else:
            agg_status = "PASS"

        # Use highest severity across constituent policies
        sev_order = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
        max_sev = max(entries, key=lambda e: sev_order.get(e.get("severity", "Medium"), 2))

        # Combine details
        if len(entries) == 1:
            details = entries[0]["details"]
            source_policies = entries[0].get("source_policy_id", "")
        else:
            detail_parts = [f"[{e.get('source_policy_id', '?')}:{e['status']}] {e['details']}" for e in entries]
            details = " || ".join(detail_parts)
            source_policies = ", ".join(e.get("source_policy_id", "") for e in entries)

        aggregated.append({
            "ksi_id": ksi_id,
            "status": agg_status,
            "severity": max_sev.get("severity", "Medium"),
            "details": details,
            "source_policies": source_policies,
            "nist_control": entries[0].get("nist_control", ""),
            "policy_count": str(len(entries)),
        })

    return aggregated


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Normalize raw Invoke-SCuBA output for the UIAO pipeline"
    )
    parser.add_argument("--input", "-i", required=True, help="Path to ScubaGear output (file or directory)")
    parser.add_argument("--output", "-o", help="Output path for normalized JSON (default: stdout)")
    parser.add_argument("--tenant-id", default="unknown-tenant", help="Tenant UUID")
    parser.add_argument("--repo-root", help="Path to uiao-core repo root")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(message)s")

    repo_root = Path(args.repo_root) if args.repo_root else None
    result = normalize_scuba(args.input, tenant_id=args.tenant_id, repo_root=repo_root)

    output_json = json.dumps(result, indent=2)
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output_json, encoding="utf-8")
        logger.info("Wrote normalized output to %s", out_path)
    else:
        print(output_json)


if __name__ == "__main__":
    main()

