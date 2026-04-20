#!/usr/bin/env python
"""
UIAO Real SCuBA Dry-Run Script
===============================
Safely runs the full UIAO 4-plane compliance pipeline against real
Invoke-SCuBA output.

Usage
-----
    python scripts/run_real_scuba_dryrun.py --input ./scuba-real-run
    python scripts/run_real_scuba_dryrun.py --input ./scuba-real-run --output ./dryrun-output
    python scripts/run_real_scuba_dryrun.py --input ./scuba-real-run --planes plane1 plane2

What it does
------------
- Loads real SCuBA JSON reports (ScubaResults.json or individual MS.*.json)
- Runs selected planes of the UIAO compliance pipeline via the orchestrator
- Produces timestamped output: IR manifest, KSI results, evidence bundle,
  POA&M, SSP fragment, and dashboard metrics
- Logs everything for audit trail
- Does NOT modify any live systems, tenants, or cloud resources

Safety
------
- Read-only on the input side
- All output goes to the specified --output directory (default: ./dryrun-output)
- Uses the orchestrator's built-in dry_run=True flag
- No Graph API calls or tenant modifications

File: scripts/run_real_scuba_dryrun.py
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging(output_dir: Path) -> logging.Logger:
    """Configure file + stderr logging; return the root logger."""
    output_dir.mkdir(parents=True, exist_ok=True)
    log_file = output_dir / f"scuba_dryrun_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stderr),
        ],
    )
    logger = logging.getLogger("uiao.dryrun")
    logger.info("Log file: %s", log_file)
    return logger


# ---------------------------------------------------------------------------
# Input discovery
# ---------------------------------------------------------------------------

def find_scuba_input(input_dir: Path, logger: logging.Logger) -> Path | None:
    """Locate the normalized SCuBA JSON inside *input_dir*.

    The orchestrator's Plane 1 expects a single normalized JSON file.
    Invoke-SCuBA typically produces ``ScubaResults.json`` (combined) or
    per-product files like ``MS.AAD.json``.  We prefer the combined file.
    """
    # Prefer combined output
    combined = input_dir / "ScubaResults.json"
    if combined.exists():
        logger.info("Found combined SCuBA report: %s", combined)
        return combined

    # Fall back to first per-product file
    per_product = sorted(input_dir.glob("MS.*.json"))
    if per_product:
        logger.info("Found %d per-product SCuBA files; using %s", len(per_product), per_product[0])
        return per_product[0]

    # Look one level deeper (Invoke-SCuBA sometimes nests under a date folder)
    for sub in sorted(input_dir.iterdir()):
        if sub.is_dir():
            nested = sub / "ScubaResults.json"
            if nested.exists():
                logger.info("Found nested SCuBA report: %s", nested)
                return nested

    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="UIAO Real SCuBA Dry-Run — run the compliance pipeline safely",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input", required=True, type=Path,
        help="Path to folder containing SCuBA JSON output, or a single normalized JSON file",
    )
    parser.add_argument(
        "--output", default=Path("./dryrun-output"), type=Path,
        help="Directory for all generated artifacts (default: ./dryrun-output)",
    )
    parser.add_argument(
        "--tenant-id", default="boundary:tenant:m365:contoso",
        help="Tenant boundary identifier for provenance tags",
    )
    parser.add_argument(
        "--planes", nargs="+", default=["plane1", "plane2", "plane3", "plane4"],
        choices=["plane1", "plane2", "plane3", "plane4"],
        help="Which planes to execute (default: all four)",
    )
    parser.add_argument(
        "--max-retries", type=int, default=1,
        help="Per-plane retry count on transient failure (default: 1)",
    )
    parser.add_argument(
        "--execute", action="store_true", default=False,
        help="Actually execute the pipeline (default: dry-run validation only)",
    )
    args = parser.parse_args()

    output_dir: Path = args.output
    logger = setup_logging(output_dir)

    logger.info("=" * 60)
    logger.info("UIAO Real SCuBA Dry-Run")
    logger.info("=" * 60)
    logger.info("Input directory : %s", args.input.resolve())
    logger.info("Output directory: %s", output_dir.resolve())
    logger.info("Tenant ID       : %s", args.tenant_id)
    logger.info("Planes          : %s", ", ".join(args.planes))
    logger.info("Execute mode    : %s", "LIVE" if args.execute else "DRY-RUN (validation only)")

    # ---- Validate input ------------------------------------------------
    if not args.input.exists():
        logger.error("Input path not found: %s", args.input)
        return 2

    # Accept either a single JSON file or a directory containing SCuBA output
    if args.input.is_file() and args.input.suffix == ".json":
        scuba_json = args.input
        logger.info("Using direct file input: %s", scuba_json)
    else:
        scuba_json = find_scuba_input(args.input, logger)
        if scuba_json is None:
            logger.error(
                "No SCuBA JSON found in %s.  Expected ScubaResults.json or MS.*.json files.",
                args.input,
            )
            return 2

    # Quick sanity: is the file valid JSON?
    try:
        with scuba_json.open(encoding="utf-8") as f:
            data = json.load(f)
        record_count = len(data) if isinstance(data, list) else 1
        logger.info("Input validated: %s (%d top-level records)", scuba_json.name, record_count)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.error("Input file is not valid JSON: %s — %s", scuba_json, exc)
        return 2

    # ---- Import orchestrator (late import so --help works w/o deps) ----
    try:
        from orchestrator.orchestrator import orchestrate, PLANE_NAMES
    except ImportError:
        # If running from repo root, the orchestrator package may need a
        # sys.path tweak.  Try adding the repo root.
        repo_root = Path(__file__).resolve().parent.parent
        if repo_root not in [Path(p) for p in sys.path]:
            sys.path.insert(0, str(repo_root))
        try:
            from orchestrator.orchestrator import orchestrate, PLANE_NAMES
        except ImportError as exc:
            logger.error(
                "Could not import orchestrator.  Make sure you run from the "
                "uiao repo root or install the package.\n  %s", exc,
            )
            return 2

    logger.info("Orchestrator imported successfully")
    for p in args.planes:
        logger.info("  %s: %s", p, PLANE_NAMES.get(p, "unknown"))

    # ---- Execute -------------------------------------------------------
    logger.info("-" * 60)
    logger.info("Starting pipeline execution (dry_run=%s)", not args.execute)
    logger.info("-" * 60)

    try:
        success, manifest = orchestrate(
            input_path=scuba_json,
            output_base_dir=output_dir,
            tenant_id=args.tenant_id,
            config_dir=None,
            planes=args.planes,
            dry_run=not args.execute,
            max_retries=args.max_retries,
        )
    except Exception:
        logger.error("Pipeline execution failed with unhandled exception", exc_info=True)
        return 1

    # ---- Report --------------------------------------------------------
    logger.info("=" * 60)
    if success:
        logger.info("RESULT: ALL PLANES PASSED")
    else:
        logger.warning("RESULT: ONE OR MORE PLANES FAILED")

    logger.info("Run ID       : %s", manifest.run_id)
    logger.info("Run directory: %s", manifest.run_dir)

    for pr in manifest.results:
        status = "PASS" if pr.success else "FAIL"
        logger.info(
            "  [%s] %-25s  %6.2fs  output=%s",
            status, PLANE_NAMES.get(pr.plane_id, pr.plane_id),
            pr.duration_secs, pr.output_path or "(none)",
        )
        if pr.error:
            logger.warning("         error: %s", pr.error)

    # Save manifest
    manifest_path = manifest.run_dir / "manifest.json"
    manifest.save(manifest_path)
    logger.info("Manifest saved: %s", manifest_path)

    logger.info("=" * 60)
    logger.info("Dry-run complete.  Review artifacts in: %s", manifest.run_dir)
    logger.info("=" * 60)

    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
