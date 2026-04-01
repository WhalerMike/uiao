#!/usr/bin/env python3
"""detect_drift.py - Detect canonical drift across the UIAO repository.

Compares all Markdown documents against the canonical Eight Core Concepts
defined in README.md (the Single Source of Truth). Detects:

1. Stale concept counts (e.g. "seven core concepts" instead of "eight")
2. Missing canonical concept keywords
3. Outdated concept labels or numbering
4. Files referencing deprecated terminology

Outputs:
    - Console summary with per-file drift details
    - reports/drift-report.json (machine-readable)

Usage:
    python scripts/detect_drift.py [--fix] [--verbose]

Exit codes:
    0 - No drift detected
    1 - Drift detected (details in report)
    2 - Error during execution
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Canonical definitions — the Single Source of Truth for drift detection.
# These MUST match the Eight Core Concepts in README.md Section 3.
# ---------------------------------------------------------------------------

CANONICAL_CONCEPT_COUNT = 8
CANONICAL_CONCEPT_COUNT_WORD = "eight"

CANONICAL_CONCEPTS = [
    {
        "number": 1,
        "short_name": "Single Source of Truth (SSOT)",
        "keywords": ["single source of truth", "ssot", "authoritative origin"],
    },
    {
        "number": 2,
        "short_name": "Conversation as the atomic unit",
        "keywords": ["conversation", "atomic unit"],
    },
    {
        "number": 3,
        "short_name": "Identity as the root namespace",
        "keywords": ["identity", "root namespace"],
    },
    {
        "number": 4,
        "short_name": "Deterministic addressing",
        "keywords": ["deterministic addressing", "identity-derived"],
    },
    {
        "number": 5,
        "short_name": "Certificate-anchored overlay",
        "keywords": ["certificate-anchored", "mtls", "certificate"],
    },
    {
        "number": 6,
        "short_name": "Telemetry as control",
        "keywords": ["telemetry as control", "telemetry"],
    },
    {
        "number": 7,
        "short_name": "Embedded governance and automation",
        "keywords": ["embedded governance", "automation"],
    },
    {
        "number": 8,
        "short_name": "Public service first",
        "keywords": ["public service first", "citizen experience"],
    },
]

# Deprecated terms that indicate drift
DEPRECATED_PATTERNS = [
    {
        "pattern": re.compile(r"\bseven\s+core\s+concepts?\b", re.IGNORECASE),
        "replacement": "Eight Core Concepts",
        "severity": "critical",
        "description": "Stale concept count: 'seven' should be 'eight'",
    },
    {
        "pattern": re.compile(r"\b7\s+core\s+concepts?\b", re.IGNORECASE),
        "replacement": "8 Core Concepts",
        "severity": "critical",
        "description": "Stale numeric concept count: '7' should be '8'",
    },
    {
        "pattern": re.compile(
            r"built\s+on\s+(?:the\s+)?seven\b", re.IGNORECASE
        ),
        "replacement": "built on the Eight",
        "severity": "critical",
        "description": "Stale phrase referencing seven concepts",
    },

        {
        "pattern": re.compile(r"\bsix\s+core\s+concepts?\b", re.IGNORECASE),
        "replacement": "Eight Core Concepts",
        "severity": "critical",
        "description": "Stale concept count: 'six' should be 'eight'",
    },
    {
        "pattern": re.compile(r"\b6\s+core\s+concepts?\b", re.IGNORECASE),
        "replacement": "8 Core Concepts",
        "severity": "critical",
        "description": "Stale numeric concept count: '6' should be '8'",
    },
]

# Directories and extensions to scan
SCAN_DIRS = ["docs", "canon", "adapters", "compliance", "templates", "01_Canon", "exports", "site", "rules", "data", "schemas", "src", "dashboard", "analytics", "assets", "_extensions"]
SCAN_ROOT_FILES = [
    "README.md",
    "CONTRIBUTING.md",
    "AGENTS.md",
    "PROJECT-CONTEXT.md",
    "UIAO-MEMORY.md",
    "FORMAT-CANON.md",
    "USAGE.md",
]
SCAN_EXTENSIONS = {".md", ".yml", ".yaml", ".html", ".j2", ".json", ".txt"}


def find_repo_root() -> Path:
    """Walk up from script location to find repository root."""
    current = Path(__file__).resolve().parent
    for _ in range(5):
        if (current / ".git").exists() or (current / "README.md").exists():
            return current
        current = current.parent
    # Fallback: assume we are run from repo root
    return Path.cwd()


def collect_files(repo_root: Path) -> list[Path]:
    """Collect all scannable files in the repository."""
    files = []

    # Root-level files
    for name in SCAN_ROOT_FILES:
        p = repo_root / name
        if p.exists():
            files.append(p)

    # Directory trees
    for dirname in SCAN_DIRS:
        dirpath = repo_root / dirname
        if not dirpath.exists():
            continue
        for root, _dirs, filenames in os.walk(dirpath):
            for fname in filenames:
                fpath = Path(root) / fname
                if fpath.suffix.lower() in SCAN_EXTENSIONS:
                    files.append(fpath)

    return sorted(set(files))


def check_deprecated_patterns(
    content: str, filepath: Path, repo_root: Path
) -> list[dict]:
    """Check a file for deprecated terminology."""
    findings = []
    lines = content.splitlines()
    rel = filepath.relative_to(repo_root)

    for rule in DEPRECATED_PATTERNS:
        for i, line in enumerate(lines, start=1):
            for match in rule["pattern"].finditer(line):
                findings.append(
                    {
                        "file": str(rel),
                        "line": i,
                        "column": match.start() + 1,
                        "matched_text": match.group(),
                        "replacement": rule["replacement"],
                        "severity": rule["severity"],
                        "description": rule["description"],
                        "category": "deprecated_term",
                    }
                )
    return findings


def check_concept_coverage(
    content: str, filepath: Path, repo_root: Path
) -> list[dict]:
    """Check whether a file that claims to list core concepts has all eight."""
    findings = []
    rel = filepath.relative_to(repo_root)
    content_lower = content.lower()

    # Only check files that actually reference "core concepts"
    if "core concepts" not in content_lower:
        return findings

            # Skip Jinja2 templates - they reference concepts generically
    if filepath.suffix.lower() == ".j2":
        return findings
    # Check each canonical concept for presence
    missing = []
    for concept in CANONICAL_CONCEPTS:
        found = False
        for kw in concept["keywords"]:
            if kw.lower() in content_lower:
                found = True
                break
        if not found:
            missing.append(concept)

    if missing:
        names = [c["short_name"] for c in missing]
        findings.append(
            {
                "file": str(rel),
                "line": 0,
                "column": 0,
                "matched_text": "",
                "replacement": "",
                "severity": "warning",
                "description": (
                    f"File references 'core concepts' but is missing: "
                    f"{', '.join(names)}"
                ),
                "category": "missing_concept",
            }
        )

    return findings


def check_concept_count_consistency(
    content: str, filepath: Path, repo_root: Path
) -> list[dict]:
    """Detect if a file states a concept count that disagrees with canonical."""
    findings = []
    rel = filepath.relative_to(repo_root)
    lines = content.splitlines()

    count_pattern = re.compile(
        r"(\w+)\s+[Cc]ore\s+[Cc]oncepts?", re.IGNORECASE
    )

    number_words = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    }

    for i, line in enumerate(lines, start=1):
        for match in count_pattern.finditer(line):
            word = match.group(1).lower()
            num = number_words.get(word)
            if num is None:
                try:
                    num = int(word)
                except ValueError:
                    continue

            if num != CANONICAL_CONCEPT_COUNT:
                findings.append(
                    {
                        "file": str(rel),
                        "line": i,
                        "column": match.start() + 1,
                        "matched_text": match.group(),
                        "replacement": f"{CANONICAL_CONCEPT_COUNT_WORD.title()} Core Concepts",
                        "severity": "critical",
                        "description": (
                            f"Concept count mismatch: found {num}, "
                            f"canonical is {CANONICAL_CONCEPT_COUNT}"
                        ),
                        "category": "count_mismatch",
                    }
                )

    return findings


def apply_fixes(content: str, findings: list[dict]) -> str:
    """Apply automatic fixes for deprecated patterns."""
    for rule in DEPRECATED_PATTERNS:
        content = rule["pattern"].sub(rule["replacement"], content)
    return content


def generate_report(
    all_findings: list[dict], files_scanned: int, repo_root: Path
) -> dict:
    """Generate the structured drift report."""
    critical = [f for f in all_findings if f["severity"] == "critical"]
    warnings = [f for f in all_findings if f["severity"] == "warning"]

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "canonical_concept_count": CANONICAL_CONCEPT_COUNT,
        "files_scanned": files_scanned,
        "total_findings": len(all_findings),
        "critical_count": len(critical),
        "warning_count": len(warnings),
        "drift_detected": len(all_findings) > 0,
        "findings": all_findings,
        "summary": {
            "files_with_drift": sorted(
                set(f["file"] for f in all_findings)
            ),
            "categories": {},
        },
    }

    for f in all_findings:
        cat = f["category"]
        report["summary"]["categories"][cat] = (
            report["summary"]["categories"].get(cat, 0) + 1
        )

    return report


def print_summary(report: dict, verbose: bool = False) -> None:
    """Print a human-readable summary to stdout."""
    print("=" * 60)
    print("UIAO Canon Drift Detection Report")
    print("=" * 60)
    print(f"Generated: {report['generated_at']}")
    print(f"Files scanned: {report['files_scanned']}")
    print(f"Canonical concept count: {report['canonical_concept_count']}")
    print(f"Total findings: {report['total_findings']}")
    print(f"  Critical: {report['critical_count']}")
    print(f"  Warnings: {report['warning_count']}")
    print()

    if not report["drift_detected"]:
        print("STATUS: NO DRIFT DETECTED")
        print("All files are consistent with the canonical Eight Core Concepts.")
        return

    print("STATUS: DRIFT DETECTED")
    print()

    files_with_drift = report["summary"]["files_with_drift"]
    print(f"Files with drift ({len(files_with_drift)}):")
    for fpath in files_with_drift:
        print(f"  - {fpath}")

    print()
    print("Category breakdown:")
    for cat, count in report["summary"]["categories"].items():
        print(f"  {cat}: {count}")

    if verbose:
        print()
        print("-" * 60)
        print("Detailed findings:")
        print("-" * 60)
        for f in report["findings"]:
            loc = f"{f['file']}:{f['line']}"
            print(f"  [{f['severity'].upper()}] {loc}")
            print(f"    {f['description']}")
            if f["matched_text"]:
                print(f"    Found: \"{f['matched_text']}\"")
            if f["replacement"]:
                print(f"    Suggested: \"{f['replacement']}\"")
            print()


def main() -> int:
    """Run drift detection. Returns 0 if no drift, 1 if drift detected."""
    parser = argparse.ArgumentParser(
        description="Detect canonical drift across UIAO repository"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Automatically fix deprecated patterns in-place",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed per-finding output",
    )
    parser.add_argument(
        "--output", "-o",
        default="reports/drift-report.json",
        help="Path for JSON report output (default: reports/drift-report.json)",
    )
    args = parser.parse_args()

    repo_root = find_repo_root()
    files = collect_files(repo_root)

    if not files:
        print("ERROR: No files found to scan.", file=sys.stderr)
        return 2

    all_findings: list[dict] = []
    fixed_files: list[str] = []

    for fpath in files:
        try:
            content = fpath.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            print(f"WARNING: Could not read {fpath}: {exc}", file=sys.stderr)
            continue

        # Run all checks
        findings = []
        findings.extend(check_deprecated_patterns(content, fpath, repo_root))
        findings.extend(check_concept_coverage(content, fpath, repo_root))
        findings.extend(
            check_concept_count_consistency(content, fpath, repo_root)
        )

        all_findings.extend(findings)

        # Auto-fix if requested
        if args.fix and findings:
            new_content = apply_fixes(content, findings)
            if new_content != content:
                fpath.write_text(new_content, encoding="utf-8")
                rel = str(fpath.relative_to(repo_root))
                fixed_files.append(rel)
                print(f"FIXED: {rel}")

    # Generate report
    report = generate_report(all_findings, len(files), repo_root)

    if fixed_files:
        report["fixed_files"] = fixed_files

    # Write JSON report
    output_path = repo_root / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )

    # Print summary
    print_summary(report, verbose=args.verbose)
    print()
    print(f"Report written to: {args.output}")

    return 1 if report["drift_detected"] else 0


if __name__ == "__main__":
    sys.exit(main())
