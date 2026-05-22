#!/usr/bin/env python3
"""Validate `lifecycle:` frontmatter consistency across docs/ pages per ADR-082.

Per ADR-082, .qmd and .md pages under `docs/` declare adoption state in
frontmatter:

    lifecycle: aspirational | adopted | superseded | deprecated
    tiers_adopted: [1, 3]          # required when lifecycle=adopted
    lifecycle_review: 2026-11-22   # ISO date; review trigger
    superseded_by: ...             # required when lifecycle=superseded
    deprecated_replacement: ...    # optional when lifecycle=deprecated

This scanner walks docs/ and validates:

  1. lifecycle=adopted requires non-empty tiers_adopted
  2. lifecycle=superseded requires non-null superseded_by resolving to a file
  3. tiers_adopted values must be in [1, 2, 3, 4, 5] per ADR-076
  4. lifecycle_review date in the past emits a non-blocking advisory
  5. lifecycle value must be one of the four canonical states
  6. lifecycle_review must parse as ISO 8601 YYYY-MM-DD

Pages without `lifecycle:` are NOT flagged here — ADR-082 backfill is
incremental (Phase 5). Defaults are documented in the metadata schema
but not enforced until backfill completes.

Sibling to scripts/scan_publication_gaps.py (publication intent scanner).
Kept separate because scan roots differ: that script walks src/uiao/;
this one walks docs/.

ADR-082 Phase 1's literal wording said "extend scan_publication_gaps.py";
this script is a new sibling instead. The deviation is intentional:
publication intent (presence) and lifecycle consistency (correctness) are
different concerns with different scan roots, and combining them would
bloat the publication-gap scanner.

Outputs:
  - stdout: human-readable summary
  - tools/lifecycle-consistency/report.md   (full markdown report)
  - tools/lifecycle-consistency/report.json (machine-readable equivalent)

Exit codes:
  0  always in advisory mode (default)
  1  if --strict and any error-severity finding is detected

Usage:
  python scripts/scan_lifecycle_consistency.py
  python scripts/scan_lifecycle_consistency.py --strict
  python scripts/scan_lifecycle_consistency.py --json-only
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any

import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS_ROOT = REPO_ROOT / "docs"
REPORT_DIR = REPO_ROOT / "tools" / "lifecycle-consistency"
REPORT_MD = REPORT_DIR / "report.md"
REPORT_JSON = REPORT_DIR / "report.json"

FM_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", re.DOTALL)

VALID_LIFECYCLE = {"aspirational", "adopted", "superseded", "deprecated"}
VALID_TIERS = {1, 2, 3, 4, 5}

# Build outputs and other paths we never want to scan.
EXCLUDE_PARTS = {"_site", "_freeze", ".quarto", "node_modules", ".venv", "__pycache__"}


@dataclass
class LifecycleFinding:
    """One consistency violation."""

    path: str
    rule: str
    severity: str  # "error" | "advisory"
    detail: str


@dataclass
class PageReport:
    """Per-page summary."""

    path: str
    lifecycle: str | None
    tiers_adopted: list[int]
    lifecycle_review: str | None
    superseded_by: str | None
    deprecated_replacement: str | None
    findings: list[LifecycleFinding] = field(default_factory=list)


def parse_frontmatter(text: str) -> dict[str, Any]:
    """Return frontmatter dict, or {} if no frontmatter is present."""
    m = FM_PATTERN.match(text)
    if not m:
        return {}
    try:
        loaded = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return {}
    return loaded or {}


def _is_excluded(path: pathlib.Path) -> bool:
    return any(part in EXCLUDE_PARTS for part in path.parts)


def validate_page(rel_path: str, fm: dict[str, Any]) -> PageReport:
    """Validate frontmatter against ADR-082 rules; return per-page report."""
    lifecycle = fm.get("lifecycle")
    raw_tiers = fm.get("tiers_adopted", []) or []
    tiers_adopted = list(raw_tiers) if isinstance(raw_tiers, list) else []
    lifecycle_review = fm.get("lifecycle_review")
    superseded_by = fm.get("superseded_by")
    deprecated_replacement = fm.get("deprecated_replacement")

    report = PageReport(
        path=rel_path,
        lifecycle=lifecycle,
        tiers_adopted=tiers_adopted,
        lifecycle_review=str(lifecycle_review) if lifecycle_review is not None else None,
        superseded_by=superseded_by,
        deprecated_replacement=deprecated_replacement,
    )

    if lifecycle is None:
        # No lifecycle declared — backfill not yet done; skip per-rule checks.
        return report

    # Rule 5: lifecycle value must be valid.
    if lifecycle not in VALID_LIFECYCLE:
        report.findings.append(
            LifecycleFinding(
                path=rel_path,
                rule="lifecycle_value",
                severity="error",
                detail=f"lifecycle='{lifecycle}' not in {sorted(VALID_LIFECYCLE)}",
            )
        )
        # Continue validating other fields so author sees the full picture
        # in one pass — don't short-circuit.

    # Rule 1: adopted requires non-empty tiers_adopted.
    if lifecycle == "adopted" and not tiers_adopted:
        report.findings.append(
            LifecycleFinding(
                path=rel_path,
                rule="adopted_requires_tiers",
                severity="error",
                detail="lifecycle=adopted but tiers_adopted is empty or missing",
            )
        )

    # Rule 3: tiers_adopted values must be in [1,2,3,4,5].
    if tiers_adopted:
        for t in tiers_adopted:
            if not isinstance(t, int) or t not in VALID_TIERS:
                report.findings.append(
                    LifecycleFinding(
                        path=rel_path,
                        rule="tiers_adopted_range",
                        severity="error",
                        detail=f"tiers_adopted contains '{t}'; must be in {sorted(VALID_TIERS)}",
                    )
                )

    # Rule 2: superseded requires non-null superseded_by resolving to a file.
    if lifecycle == "superseded":
        if not superseded_by:
            report.findings.append(
                LifecycleFinding(
                    path=rel_path,
                    rule="superseded_requires_link",
                    severity="error",
                    detail="lifecycle=superseded but superseded_by is empty or missing",
                )
            )
        else:
            successor_path = REPO_ROOT / superseded_by
            if not successor_path.exists():
                report.findings.append(
                    LifecycleFinding(
                        path=rel_path,
                        rule="superseded_link_unresolved",
                        severity="error",
                        detail=f"superseded_by='{superseded_by}' does not resolve to an existing file",
                    )
                )

    # Rule 4 + 6: lifecycle_review must be valid ISO; past dates emit advisory.
    if lifecycle_review is not None:
        try:
            review_date = date.fromisoformat(str(lifecycle_review))
            if review_date < date.today():
                report.findings.append(
                    LifecycleFinding(
                        path=rel_path,
                        rule="lifecycle_review_past",
                        severity="advisory",
                        detail=f"lifecycle_review={lifecycle_review} is in the past; re-validation due",
                    )
                )
        except ValueError:
            report.findings.append(
                LifecycleFinding(
                    path=rel_path,
                    rule="lifecycle_review_format",
                    severity="error",
                    detail=f"lifecycle_review='{lifecycle_review}' is not ISO 8601 YYYY-MM-DD",
                )
            )

    return report


def scan() -> list[PageReport]:
    """Walk docs/ for .qmd and .md files; validate each."""
    if not DOCS_ROOT.exists():
        return []
    reports: list[PageReport] = []
    files = sorted(list(DOCS_ROOT.rglob("*.qmd")) + list(DOCS_ROOT.rglob("*.md")))
    for path in files:
        if _is_excluded(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        fm = parse_frontmatter(text)
        rel = path.relative_to(REPO_ROOT).as_posix()
        reports.append(validate_page(rel, fm))
    return reports


def write_reports(reports: list[PageReport]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    json_data = {
        "schema_version": "1.0.0",
        "generator": "scripts/scan_lifecycle_consistency.py (ADR-082 Phase 1)",
        "pages": [asdict(r) for r in reports],
    }
    REPORT_JSON.write_text(
        json.dumps(json_data, indent=2, default=str),
        encoding="utf-8",
    )

    pages_with_lifecycle = [r for r in reports if r.lifecycle is not None]
    pages_with_findings = [r for r in reports if r.findings]
    errors = sum(1 for r in reports for f in r.findings if f.severity == "error")
    advisories = sum(1 for r in reports for f in r.findings if f.severity == "advisory")

    lines: list[str] = [
        "# Lifecycle Consistency Report",
        "",
        "Generated by `scripts/scan_lifecycle_consistency.py` (ADR-082 Phase 1).",
        "",
        "## Summary",
        "",
        f"- Pages scanned: {len(reports)}",
        f"- Pages with `lifecycle:` field: {len(pages_with_lifecycle)}",
        f"- Pages with findings: {len(pages_with_findings)}",
        f"- Errors: {errors}",
        f"- Advisories: {advisories}",
        "",
    ]

    if pages_with_findings:
        lines.append("## Findings")
        lines.append("")
        for r in pages_with_findings:
            lines.append(f"### `{r.path}`")
            lines.append("")
            for f in r.findings:
                badge = "**ERROR**" if f.severity == "error" else "*advisory*"
                lines.append(f"- {badge} ({f.rule}): {f.detail}")
            lines.append("")

    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if any error-severity finding is detected (advisories don't fail).",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Suppress stdout summary; still writes report files.",
    )
    args = parser.parse_args(argv)

    reports = scan()
    write_reports(reports)

    pages_with_lifecycle = [r for r in reports if r.lifecycle is not None]
    errors = sum(1 for r in reports for f in r.findings if f.severity == "error")
    advisories = sum(1 for r in reports for f in r.findings if f.severity == "advisory")

    if not args.json_only:
        print(f"Pages scanned:                    {len(reports)}")
        print(f"Pages with lifecycle field:       {len(pages_with_lifecycle)}")
        print(f"Errors (lifecycle inconsistency): {errors}")
        print(f"Advisories (review-due):          {advisories}")
        print()
        print("Reports:")
        print(f"  {REPORT_MD.relative_to(REPO_ROOT)}")
        print(f"  {REPORT_JSON.relative_to(REPO_ROOT)}")

    if args.strict and errors > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
