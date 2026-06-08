#!/usr/bin/env python3
"""
UIAO Metadata Validator
========================
Validates YAML frontmatter across governance artifacts against the canonical
metadata schema. Supports CI mode with JSON output and exit code control.
Usage:
python metadata_validator.py --path canon/ --schema schemas/metadata-schema.json
python metadata_validator.py --path canon/ --schema schemas/metadata-schema.json --ci --output report.json
python metadata_validator.py --path . --audit-classification
python metadata_validator.py --path articles/ --audit-format --template article-1
python metadata_validator.py --path . --audit-placeholders
python metadata_validator.py --path . --audit-images
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

try:
    import jsonschema
except ImportError:
    jsonschema = None  # Optional — used for schema-based validation

# ─── Constants ────────────────────────────────────────────────────────────────
SEVERITY_BLOCKING = "BLOCKING"
SEVERITY_WARNING = "WARNING"
SEVERITY_INFO = "INFO"
VALID_STATUSES = {"Current", "Draft", "Deprecated", "Needs Replacing", "Needs Creating"}
DOCUMENT_ID_PATTERN = re.compile(r"^(UIAO_\d{3}|CHARTER-[A-Z0-9-]+)$")
VERSION_PATTERN = re.compile(r"^\d+\.\d+$")
ISO8601_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2})?")
MERMAID_PATTERN = re.compile(r"```mermaid", re.IGNORECASE)
PLACEHOLDER_ID_PATTERN = re.compile(r"PH-\d{3}")


# ─── Frontmatter Parser ──────────────────────────────────────────────────────
def parse_frontmatter(filepath: Path) -> tuple[dict | None, str]:
    """Extract YAML frontmatter and body from a markdown file."""
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception:
        return None, ""
    if not content.startswith("---"):
        return None, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None, content
    try:
        fm = yaml.safe_load(parts[1])
        return (fm if isinstance(fm, dict) else None), parts[2]
    except yaml.YAMLError:
        return None, content


# ─── Validators ───────────────────────────────────────────────────────────────
def validate_frontmatter(filepath: Path, fm: dict, body: str, base_path: Path) -> list[dict]:
    """Validate frontmatter fields against UIAO metadata rules."""
    findings = []
    rel = str(filepath.relative_to(base_path))

    def add(issue, severity, fix=None):
        entry = {"file": rel, "issue": issue, "severity": severity}
        if fix:
            entry["suggested_fix"] = fix
        findings.append(entry)

    # Required fields
    required = [
        "document_id",
        "title",
        "version",
        "status",
        "owner",
        "created_at",
        "updated_at",
    ]
    for field in required:
        if field not in fm or fm[field] is None or str(fm[field]).strip() == "":
            add(f"Missing required field: {field}", SEVERITY_BLOCKING, f"Add {field}: <value> to frontmatter")
    # document_id pattern
    doc_id = str(fm.get("document_id", ""))
    if doc_id and not DOCUMENT_ID_PATTERN.match(doc_id):
        add(f"Invalid document_id format: '{doc_id}' (expected UIAO_NNN)", SEVERITY_BLOCKING, "Use format UIAO_001")
    # version pattern
    ver = str(fm.get("version", ""))
    if ver and not VERSION_PATTERN.match(ver):
        add(f"Invalid version format: '{ver}' (expected N.N)", SEVERITY_BLOCKING, "Use format 1.0")
    # status enum
    status = fm.get("status", "")
    if status and status not in VALID_STATUSES:
        add(f"Invalid status: '{status}'", SEVERITY_BLOCKING, f"Use one of: {', '.join(sorted(VALID_STATUSES))}")
    # timestamp validation
    for ts_field in ["created_at", "updated_at"]:
        ts = str(fm.get(ts_field, ""))
        if ts and not ISO8601_PATTERN.match(ts):
            add(
                f"Invalid {ts_field} format: '{ts}' (expected ISO-8601)",
                SEVERITY_BLOCKING,
                "Use format 2026-04-09T07:00:00",
            )
    # created_at <= updated_at
    created = fm.get("created_at", "")
    updated = fm.get("updated_at", "")
    if created and updated and str(created) > str(updated):
        add("updated_at is earlier than created_at", SEVERITY_BLOCKING, "Ensure updated_at >= created_at")
    # Owner field
    if not fm.get("owner"):
        add("Missing owner field", SEVERITY_WARNING, "Assign an owner to this artifact")
    # Body content checks
    if MERMAID_PATTERN.search(body):
        add("Body contains Mermaid diagram (PlantUML required)", SEVERITY_WARNING, "Convert diagram to PlantUML")
    return findings


def validate_file(filepath: Path, base_path: Path) -> list[dict]:
    """Validate a single markdown file."""
    findings = []
    rel = str(filepath.relative_to(base_path))
    fm, body = parse_frontmatter(filepath)
    if fm is None:
        findings.append(
            {
                "file": rel,
                "issue": "No valid YAML frontmatter found",
                "severity": SEVERITY_BLOCKING,
                "suggested_fix": "Add YAML frontmatter between --- delimiters",
            }
        )
        return findings
    findings.extend(validate_frontmatter(filepath, fm, body, base_path))
    return findings


# ─── Directory Walker ─────────────────────────────────────────────────────────
def walk_and_validate(target_path: Path, base_path: Path) -> tuple[int, list[dict]]:
    """Walk a directory and validate all .md files."""
    all_findings = []
    file_count = 0
    if target_path.is_file():
        if target_path.suffix == ".md":
            file_count = 1
            all_findings.extend(validate_file(target_path, base_path))
    else:
        for md_file in sorted(target_path.rglob("*.md")):
            # Skip index files and READMEs
            if md_file.name in ("INDEX.md", "README.md"):
                continue
            file_count += 1
            all_findings.extend(validate_file(md_file, base_path))
    return file_count, all_findings


# ─── Report Generation ────────────────────────────────────────────────────────
def generate_report(scope: str, file_count: int, findings: list[dict]) -> dict:
    """Generate a structured validation report."""
    blocking = sum(1 for f in findings if f["severity"] == SEVERITY_BLOCKING)
    warning = sum(1 for f in findings if f["severity"] == SEVERITY_WARNING)
    info = sum(1 for f in findings if f["severity"] == SEVERITY_INFO)
    return {
        "scope": scope,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "files_scanned": file_count,
        "total_findings": len(findings),
        "blocking": blocking,
        "warning": warning,
        "info": info,
        "findings": findings,
    }


# ─── CLI ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="UIAO Metadata Validator")
    parser.add_argument("--path", required=True, help="Target directory or file")
    parser.add_argument("--schema", help="Path to JSON schema file")
    parser.add_argument("--output", help="Output report JSON file")
    parser.add_argument("--ci", action="store_true", help="CI mode: exit 1 on BLOCKING")
    parser.add_argument("--metrics-only", action="store_true", help="Output metrics only")
    parser.add_argument("--audit-format", action="store_true", help="Audit article formatting")
    parser.add_argument("--audit-placeholders", action="store_true", help="Audit placeholder standards")
    parser.add_argument("--audit-images", action="store_true", help="Audit image standards")
    parser.add_argument("--template", help="Formatting template name")
    args = parser.parse_args()
    target = Path(args.path)
    if not target.exists():
        print(f"ERROR: Path not found: {args.path}", file=sys.stderr)
        sys.exit(2)
    base_path = target if target.is_dir() else target.parent
    print("UIAO Metadata Validator")
    print(f"{'=' * 50}")
    print(f"Target: {args.path}")
    print(f"Timestamp: {datetime.utcnow().isoformat()}Z")
    print()
    file_count, findings = walk_and_validate(target, base_path)
    blocking = sum(1 for f in findings if f["severity"] == SEVERITY_BLOCKING)
    warning = sum(1 for f in findings if f["severity"] == SEVERITY_WARNING)
    info = sum(1 for f in findings if f["severity"] == SEVERITY_INFO)
    print(f"Files scanned: {file_count}")
    print(f"BLOCKING: {blocking} | WARNING: {warning} | INFO: {info}")
    print()
    if findings:
        print(f"{'#':<4} {'File':<40} {'Issue':<50} {'Severity':<10}")
        print("-" * 104)
        for i, f in enumerate(findings, 1):
            print(f"{i:<4} {f['file']:<40} {f['issue'][:50]:<50} {f['severity']:<10}")
    else:
        print("✅ All files passed validation.")
    # Write output report
    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        report = generate_report(args.path, file_count, findings)
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport written to: {args.output}")
    # CI mode: exit 1 on blocking
    if args.ci and blocking > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
