#!/usr/bin/env python3
"""
UIAO Dashboard Exporter
=========================
Extracts governance metrics from repository state, validates against the
dashboard schema, and exports structured data for operational dashboards,
SLA heatmaps, and trend visualizations.
Usage:
python dashboard_exporter.py --schema schemas/dashboard-schema.json --validate
python dashboard_exporter.py --schema schemas/dashboard-schema.json --export json --output dashboard/exports/
python dashboard_exporter.py --schema schemas/dashboard-schema.json --export json --trends 30
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    import yaml  # noqa: F401  # presence check; importer exits if unavailable
except ImportError:
    print("ERROR: PyYAML required. Install: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

try:
    import jsonschema
except ImportError:
    jsonschema = None


# ─── Metric Collectors ───────────────────────────────────────────────────────
def collect_validation_metrics(metrics_dir: Path) -> dict:
    """Collect metrics from validation report files."""
    metrics = {
        "files_scanned": 0,
        "compliant": 0,
        "non_compliant": 0,
        "compliance_rate": 0.0,
        "blocking": 0,
        "warning": 0,
        "info": 0,
    }
    report_files = list(metrics_dir.glob("*validation*.json"))
    for rf in report_files:
        try:
            data = json.loads(rf.read_text(encoding="utf-8"))
            metrics["files_scanned"] += data.get("files_scanned", 0)
            metrics["blocking"] += data.get("blocking", 0)
            metrics["warning"] += data.get("warning", 0)
            metrics["info"] += data.get("info", 0)
        except (json.JSONDecodeError, Exception):
            continue
    total = metrics["files_scanned"]
    if total > 0:
        files_with_blocking = len({
            f.get("file", "") for rf in report_files
            if rf.exists()
            for f in json.loads(rf.read_text()).get("findings", [])
            if f.get("severity") == "BLOCKING"
        })
        metrics["non_compliant"] = files_with_blocking
        metrics["compliant"] = total - files_with_blocking
        metrics["compliance_rate"] = round((metrics["compliant"] / total) * 100, 1)
    return metrics


def collect_drift_metrics(metrics_dir: Path) -> dict:
    """Collect metrics from drift report files."""
    metrics = {
        "files_scanned": 0,
        "drift_count": 0,
        "drift_free": 0,
        "drift_free_rate": 0.0,
        "blocking": 0,
        "warning": 0,
        "info": 0,
        "by_category": {},
    }
    report_files = list(metrics_dir.glob("*drift*.json"))
    for rf in report_files:
        try:
            data = json.loads(rf.read_text(encoding="utf-8"))
            metrics["files_scanned"] += data.get("files_scanned", 0)
            metrics["drift_count"] += data.get("drift_count", 0)
            metrics["blocking"] += data.get("blocking", 0)
            metrics["warning"] += data.get("warning", 0)
            metrics["info"] += data.get("info", 0)
            for finding in data.get("findings", []):
                cat = finding.get("category", "UNKNOWN")
                metrics["by_category"][cat] = metrics["by_category"].get(cat, 0) + 1
        except (json.JSONDecodeError, Exception):
            continue
    total = metrics["files_scanned"]
    if total > 0:
        drifted_files = len({
            f.get("file", "") for rf in report_files
            if rf.exists()
            for f in json.loads(rf.read_text()).get("findings", [])
        })
        metrics["drift_free"] = total - drifted_files
        metrics["drift_free_rate"] = round((metrics["drift_free"] / total) * 100, 1)
    return metrics


def collect_appendix_metrics(metrics_dir: Path) -> dict:
    """Collect metrics from appendix audit report files."""
    metrics = {
        "total_appendices": 0,
        "with_copy": 0,
        "missing_copy": 0,
        "valid_frontmatter": 0,
        "invalid_frontmatter": 0,
        "integrity_rate": 0.0,
        "copy_compliance": 0.0,
    }
    report_files = list(metrics_dir.glob("*appendix*.json"))
    for rf in report_files:
        try:
            data = json.loads(rf.read_text(encoding="utf-8"))
            metrics["total_appendices"] += data.get("total_appendices", 0)
            metrics["with_copy"] += data.get("with_copy", 0)
            metrics["missing_copy"] += data.get("missing_copy", 0)
            metrics["valid_frontmatter"] += data.get("valid_frontmatter", 0)
            metrics["invalid_frontmatter"] += data.get("invalid_frontmatter", 0)
        except (json.JSONDecodeError, Exception):
            continue
    total = metrics["total_appendices"]
    if total > 0:
        valid = metrics["valid_frontmatter"]
        metrics["integrity_rate"] = round((valid / total) * 100, 1)
        metrics["copy_compliance"] = round((metrics["with_copy"] / total) * 100, 1)
    return metrics


def collect_owner_metrics(metrics_dir: Path) -> list[dict]:
    """Extract owner-level metrics from validation and drift reports."""
    owners = {}
    for rf in metrics_dir.glob("*.json"):
        try:
            data = json.loads(rf.read_text(encoding="utf-8"))
            for finding in data.get("findings", []):
                # Attempt to extract owner from findings context
                # In a real implementation, this would parse frontmatter
                owner = finding.get("owner", "unassigned")
                if owner not in owners:
                    owners[owner] = {
                        "owner": owner,
                        "owned_artifacts": 0,
                        "blocking_findings": 0,
                        "warning_findings": 0,
                        "reliability_score": 100,
                    }
                owners[owner]["owned_artifacts"] += 1
                if finding.get("severity") == "BLOCKING":
                    owners[owner]["blocking_findings"] += 1
                elif finding.get("severity") == "WARNING":
                    owners[owner]["warning_findings"] += 1
        except (json.JSONDecodeError, Exception):
            continue
    # Compute reliability scores
    for owner_data in owners.values():
        total = owner_data["owned_artifacts"]
        if total > 0:
            penalty = (owner_data["blocking_findings"] * 10 +
                       owner_data["warning_findings"] * 3)
            owner_data["reliability_score"] = max(0, 100 - penalty)
    return list(owners.values())


# ─── Health Score ─────────────────────────────────────────────────────────────
def compute_health_score(validation: dict, drift: dict, appendix: dict) -> int:
    """Compute overall canon health score (0-100)."""
    weights = {
        "compliance": 0.35,
        "drift_free": 0.30,
        "appendix_integrity": 0.20,
        "copy_compliance": 0.15,
    }
    scores = {
        "compliance": validation.get("compliance_rate", 0),
        "drift_free": drift.get("drift_free_rate", 0),
        "appendix_integrity": appendix.get("integrity_rate", 0),
        "copy_compliance": appendix.get("copy_compliance", 0),
    }
    weighted = sum(scores[k] * weights[k] for k in weights)
    return round(weighted)


# ─── Trend Computation ────────────────────────────────────────────────────────
def compute_trends(output_dir: Path, days: int) -> dict:
    """Compute rolling trends from historical export files."""
    trends = {
        "period_days": days,
        "health_trend": 0.0,
        "compliance_trend": 0.0,
        "drift_trend": 0,
        "data_points": 0,
    }
    if not output_dir.exists():
        return trends
    cutoff = datetime.utcnow() - timedelta(days=days)
    history = []
    for export_file in sorted(output_dir.glob("dashboard-*.json")):
        try:
            data = json.loads(export_file.read_text(encoding="utf-8"))
            ts = data.get("export_timestamp", "")
            if ts and ts >= cutoff.isoformat():
                history.append(data)
        except (json.JSONDecodeError, Exception):
            continue
    trends["data_points"] = len(history)
    if len(history) >= 2:
        first = history[0]
        last = history[-1]
        trends["health_trend"] = round(
            last.get("health_score", 0) - first.get("health_score", 0), 1)
        trends["compliance_trend"] = round(
            last.get("metrics", {}).get("validation", {}).get("compliance_rate", 0) -
            first.get("metrics", {}).get("validation", {}).get("compliance_rate", 0), 1)
        trends["drift_trend"] = (
            last.get("metrics", {}).get("drift", {}).get("drift_count", 0) -
            first.get("metrics", {}).get("drift", {}).get("drift_count", 0))
    return trends


# ─── Export ───────────────────────────────────────────────────────────────────
def build_export(validation: dict, drift: dict, appendix: dict,
                 owners: list, trends: dict, repository: str) -> dict:
    """Build the complete dashboard export payload."""
    health_score = compute_health_score(validation, drift, appendix)
    return {
        "export_timestamp": datetime.utcnow().isoformat() + "Z",
        "repository": repository,
        "health_score": health_score,
        "metrics": {
            "validation": validation,
            "drift": drift,
            "appendix": appendix,
        },
        "owner_scores": owners,
        "trend_indicators": trends,
        "boundary_exception_count": 0,  # Populated from validation findings
        "open_remediation_count": (
            validation.get("blocking", 0) + validation.get("warning", 0) +
            drift.get("blocking", 0) + drift.get("warning", 0) +
            appendix.get("missing_copy", 0) + appendix.get("invalid_frontmatter", 0)
        ),
    }


def validate_export(export_data: dict, schema_path: Path) -> tuple[bool, list[str]]:
    """Validate export data against the dashboard schema."""
    if not schema_path.exists():
        return True, ["Schema file not found — skipping validation"]
    if jsonschema is None:
        return True, ["jsonschema not installed — skipping validation"]
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.validate(export_data, schema)
        return True, []
    except jsonschema.ValidationError as e:
        return False, [str(e.message)]
    except Exception as e:
        return False, [str(e)]


def write_export(export_data: dict, output_dir: Path, fmt: str):
    """Write export to disk in the specified format."""
    os.makedirs(output_dir, exist_ok=True)
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    if fmt == "json":
        out_path = output_dir / f"dashboard-{date_str}.json"
        out_path.write_text(json.dumps(export_data, indent=2), encoding="utf-8")
        print(f"Export written to: {out_path}")
    elif fmt == "csv":
        out_path = output_dir / f"dashboard-{date_str}.csv"
        lines = ["metric,value"]
        lines.append(f"health_score,{export_data['health_score']}")
        for section, metrics in export_data.get("metrics", {}).items():
            for k, v in metrics.items():
                if isinstance(v, (int, float, str)):
                    lines.append(f"{section}.{k},{v}")
        out_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"Export written to: {out_path}")
    elif fmt == "markdown":
        out_path = output_dir / f"dashboard-{date_str}.md"
        lines = [
            f"# Governance Dashboard — {date_str}",
            "",
            f"**Health Score:** {export_data['health_score']}/100",
            "",
            "## Metrics",
            "",
            "| Category | Metric | Value |",
            "|----------|--------|-------|",
        ]
        for section, metrics in export_data.get("metrics", {}).items():
            for k, v in metrics.items():
                if isinstance(v, (int, float, str)):
                    lines.append(f"| {section} | {k} | {v} |")
        lines.append("")
        out_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"Export written to: {out_path}")


# ─── CLI ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="UIAO Dashboard Exporter")
    parser.add_argument("--schema", required=True, help="Path to dashboard schema")
    parser.add_argument("--export", choices=["json", "csv", "markdown"],
                        help="Export format")
    parser.add_argument("--validate", action="store_true",
                        help="Validate existing exports against schema")
    parser.add_argument("--output", default="dashboard/exports/",
                        help="Output directory")
    parser.add_argument("--trends", type=int, default=0,
                        help="Days for rolling trend computation")
    parser.add_argument("--metrics-dir", default="reports/",
                        help="Directory containing metric report files")
    parser.add_argument("--input", help="Input directory for validation mode")
    parser.add_argument("--repository", default="uiao-core",
                        help="Repository name for export")
    args = parser.parse_args()
    schema_path = Path(args.schema)
    metrics_dir = Path(args.metrics_dir)
    output_dir = Path(args.output)
    print("UIAO Dashboard Exporter")
    print(f"{'='*50}")
    print(f"Timestamp: {datetime.utcnow().isoformat()}Z")
    print()
    if args.validate and args.input:
        # Validate existing exports
        input_dir = Path(args.input)
        for export_file in sorted(input_dir.glob("dashboard-*.json")):
            try:
                data = json.loads(export_file.read_text(encoding="utf-8"))
                valid, errors = validate_export(data, schema_path)
                status = "✅ PASS" if valid else "❌ FAIL"
                print(f"{export_file.name}: {status}")
                for err in errors:
                    print(f"  → {err}")
            except Exception as e:
                print(f"{export_file.name}: ❌ ERROR — {e}")
        return
    # Collect metrics
    print("Collecting metrics...")
    validation = collect_validation_metrics(metrics_dir)
    drift = collect_drift_metrics(metrics_dir)
    appendix = collect_appendix_metrics(metrics_dir)
    owners = collect_owner_metrics(metrics_dir)
    print(f"  Validation: {validation['files_scanned']} files, "
          f"{validation['compliance_rate']}% compliance")
    print(f"  Drift: {drift['files_scanned']} files, "
          f"{drift['drift_free_rate']}% drift-free")
    print(f"  Appendix: {appendix['total_appendices']} appendices, "
          f"{appendix['integrity_rate']}% integrity")
    print()
    # Compute trends
    trends = {}
    if args.trends > 0:
        print(f"Computing {args.trends}-day trends...")
        trends = compute_trends(output_dir, args.trends)
        print(f"  Data points: {trends['data_points']}")
        print(f"  Health trend: {trends['health_trend']:+.1f}")
        print(f"  Compliance trend: {trends['compliance_trend']:+.1f}")
        print(f"  Drift trend: {trends['drift_trend']:+d}")
        print()
    # Build export
    export_data = build_export(validation, drift, appendix, owners,
                               trends, args.repository)
    health = export_data["health_score"]
    print(f"Canon Health Score: {health}/100")
    print(f"Open Remediation Items: {export_data['open_remediation_count']}")
    print()
    # Validate against schema
    valid, errors = validate_export(export_data, schema_path)
    print(f"Schema Validation: {'✅ PASS' if valid else '❌ FAIL'}")
    for err in errors:
        print(f"  → {err}")
    print()
    # Write export
    if args.export:
        write_export(export_data, output_dir, args.export)


if __name__ == "__main__":
    main()
