#!/usr/bin/env python3
"""
UIAO Document Review Scanner

Scans docs/customer-documents/** for documents whose lifecycle_review date
falls within --horizon days and outputs a structured JSON report.

Usage:
    python scripts/review_scanner.py                  # default 60-day horizon
    python scripts/review_scanner.py --horizon 30
    python scripts/review_scanner.py --horizon 90 --output report.json
    python scripts/review_scanner.py --all            # full inventory

Used by:
    .github/workflows/review-reminders.yml  (automated GitHub Issue creation)
    Local review planning
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml not installed. Run: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

REPO_ROOT = Path(__file__).parent.parent
DOCS_ROOT = REPO_ROOT / "docs" / "customer-documents"

SKIP_TYPES = {
    "orgpath-narrative-book",
    "orgpath-narrative-chapter",
    "sql-server-narrative-book",
    "sql-server-narrative-chapter",
    "sql-server-implementation-book",
    "subcategory-landing",
    "section-landing",
    "",
}

SKIP_STATUS = {"reserved", "scaffold", ""}

TYPE_WEIGHT = {
    "operational-guide": 10,
    "whitepaper": 9,
    "policy-library": 9,
    "compliance-assessment": 9,
    "runbook": 8,
    "technical-guide": 8,
    "architecture-reference": 8,
    "executive-brief": 7,
    "executive-governance-chapter": 7,
    "case-study-pattern": 6,
    "ats": 5,
    "avs": 5,
    "learning-reference": 5,
    "leaf": 4,
}

EFFORT_HOURS = {
    "operational-guide": 12,
    "whitepaper": 10,
    "policy-library": 10,
    "compliance-assessment": 10,
    "runbook": 8,
    "technical-guide": 8,
    "architecture-reference": 8,
    "executive-brief": 6,
    "executive-governance-chapter": 6,
    "case-study-pattern": 5,
    "ats": 4,
    "avs": 4,
    "learning-reference": 4,
    "leaf": 3,
}

REVIEWER = {
    "policy-library": "Compliance Officer",
    "compliance-assessment": "Compliance Officer",
    "whitepaper": "Compliance Officer",
    "ats": "SME – Infrastructure",
    "avs": "SME – Infrastructure",
    "technical-guide": "SME – Infrastructure",
    "runbook": "SME – Infrastructure",
    "architecture-reference": "SME – Infrastructure",
    "operational-guide": "SME – Infrastructure",
    "executive-brief": "Michael Stratton",
    "executive-governance-chapter": "Michael Stratton",
}


def git_last_commit(path: Path) -> str:
    r = subprocess.run(
        ["git", "log", "-1", "--format=%ci", str(path)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    return r.stdout.strip()[:10] if r.stdout.strip() else ""


def priority_score(doc_type: str, days_until_lr, days_stale) -> int:
    weight = TYPE_WEIGHT.get(doc_type, 3) * 10

    if days_until_lr is None:
        urgency = 5
    elif days_until_lr < 0:
        urgency = 150  # overdue
    elif days_until_lr < 30:
        urgency = 100
    elif days_until_lr < 60:
        urgency = 70
    elif days_until_lr < 90:
        urgency = 50
    elif days_until_lr < 180:
        urgency = 30
    else:
        urgency = 10

    if days_stale is None:
        staleness = 5
    elif days_stale > 180:
        staleness = 30
    elif days_stale > 90:
        staleness = 20
    elif days_stale > 30:
        staleness = 10
    else:
        staleness = 0

    return weight + urgency + staleness


def tier(score: int) -> str:
    if score >= 200:
        return "CRITICAL"
    if score >= 150:
        return "HIGH"
    if score >= 120:
        return "MEDIUM"
    return "LOW"


def scan(horizon_days: int | None = 60, include_all: bool = False) -> list[dict]:
    today = date.today()
    results = []

    for qmd in sorted(DOCS_ROOT.rglob("*.qmd")):
        text = qmd.read_text(encoding="utf-8", errors="ignore")
        m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
        if not m:
            continue
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except Exception:
            fm = {}

        status = fm.get("status", "")
        dtype = fm.get("doc-type", "")

        if status in SKIP_STATUS or dtype in SKIP_TYPES:
            continue

        lr_raw = str(fm.get("lifecycle_review", ""))
        try:
            lr_date = date.fromisoformat(lr_raw)
            days_until_lr = (lr_date - today).days
        except ValueError:
            lr_date = None
            days_until_lr = None

        # Filter by horizon unless --all
        if not include_all:
            if days_until_lr is None or days_until_lr > horizon_days:
                continue

        git_date_str = git_last_commit(qmd)
        try:
            git_date = date.fromisoformat(git_date_str)
            days_stale = (today - git_date).days
        except ValueError:
            days_stale = None

        score = priority_score(dtype, days_until_lr, days_stale)

        results.append(
            {
                "path": str(qmd.relative_to(DOCS_ROOT)).replace("\\", "/"),
                "title": fm.get("title", ""),
                "status": status,
                "doc_type": dtype,
                "lifecycle_review": lr_raw,
                "days_until_lr": days_until_lr,
                "git_last_commit": git_date_str,
                "days_stale": days_stale,
                "priority_score": score,
                "tier": tier(score),
                "est_hours": EFFORT_HOURS.get(dtype, 4),
                "reviewer": REVIEWER.get(dtype, "Michael Stratton"),
                "audience": str(fm.get("audience", "")),
                "pillar": fm.get("pillar", ""),
                "family": fm.get("family", ""),
            }
        )

    return sorted(results, key=lambda r: -r["priority_score"])


def main():
    parser = argparse.ArgumentParser(description="UIAO Document Review Scanner")
    parser.add_argument(
        "--horizon",
        type=int,
        default=60,
        help="Days ahead to scan for approaching lifecycle_review dates (default: 60)",
    )
    parser.add_argument(
        "--all", action="store_true", dest="all_docs", help="Output full inventory regardless of horizon"
    )
    parser.add_argument("--output", "-o", default="-", help="Output file path (default: stdout)")
    args = parser.parse_args()

    results = scan(
        horizon_days=args.horizon if not args.all_docs else None,
        include_all=args.all_docs,
    )

    today = date.today()
    report = {
        "generated": today.isoformat(),
        "horizon_days": args.horizon if not args.all_docs else None,
        "total_docs_scanned": sum(1 for _ in DOCS_ROOT.rglob("*.qmd")),
        "docs_in_window": len(results),
        "summary": {
            "critical": sum(1 for r in results if r["tier"] == "CRITICAL"),
            "high": sum(1 for r in results if r["tier"] == "HIGH"),
            "medium": sum(1 for r in results if r["tier"] == "MEDIUM"),
            "low": sum(1 for r in results if r["tier"] == "LOW"),
            "total_hours": sum(r["est_hours"] for r in results),
        },
        "docs": results,
    }

    output = json.dumps(report, indent=2)
    if args.output == "-":
        print(output)
    else:
        Path(args.output).write_text(output)
        print(f"Report written to {args.output} ({len(results)} docs)", file=sys.stderr)


if __name__ == "__main__":
    main()
