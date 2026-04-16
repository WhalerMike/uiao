#!/usr/bin/env python3
"""
UIAO Appendix Indexer
======================
Manages appendix lifecycle — auditing integrity, rebuilding the index,
syncing state, and cross-repo alignment checking.
Usage:
python appendix_indexer.py --path appendices/ --mode audit
python appendix_indexer.py --path appendices/ --mode rebuild
python appendix_indexer.py --path appendices/ --mode sync
python appendix_indexer.py --path appendices/ --mode cross-repo --core-path ../uiao-core/appendices/
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


# ─── Constants ────────────────────────────────────────────────────────────────
SEVERITY_BLOCKING = "BLOCKING"
SEVERITY_WARNING = "WARNING"
SEVERITY_INFO = "INFO"
REQUIRED_FIELDS = ["appendix_id", "title", "parent_document", "status", "owner"]
VALID_STATUSES = {"Current", "Draft", "Deprecated"}
COPY_SECTION_PATTERN = re.compile(r"^##\s+Copy\b", re.MULTILINE)


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


# ─── Appendix Scanner ────────────────────────────────────────────────────────
def scan_appendices(appendix_dir: Path) -> list[dict]:
    """Scan appendix directory and extract metadata from each appendix."""
    entries = []
    for md_file in sorted(appendix_dir.rglob("*.md")):
        if md_file.name == "INDEX.md":
            continue
        fm, body = parse_frontmatter(md_file)
        has_copy = bool(COPY_SECTION_PATTERN.search(body))
        entry = {
            "file": str(md_file.relative_to(appendix_dir)),
            "filepath": md_file,
            "frontmatter": fm,
            "has_copy": has_copy,
        }
        if fm:
            entry["appendix_id"] = fm.get("appendix_id", "")
            entry["title"] = fm.get("title", "")
            entry["parent_document"] = fm.get("parent_document", "")
            entry["status"] = fm.get("status", "")
            entry["owner"] = fm.get("owner", "")
            entry["last_updated"] = fm.get("last_updated", fm.get("updated_at", ""))
        else:
            entry["appendix_id"] = ""
            entry["title"] = md_file.stem
            entry["parent_document"] = ""
            entry["status"] = ""
            entry["owner"] = ""
            entry["last_updated"] = ""
        entries.append(entry)
    return entries


# ─── Audit ────────────────────────────────────────────────────────────────────
def audit_appendices(entries: list[dict]) -> list[dict]:
    """Audit appendix integrity — frontmatter, Copy sections, uniqueness."""
    findings = []
    seen_ids = {}
    for entry in entries:
        fm = entry["frontmatter"]
        app_id = entry.get("appendix_id", entry["file"])
        # No frontmatter
        if fm is None:
            findings.append({
                "appendix_id": app_id or entry["file"],
                "file": entry["file"],
                "issue": "No valid YAML frontmatter",
                "severity": SEVERITY_BLOCKING,
            })
            continue
        # Required fields
        for field in REQUIRED_FIELDS:
            val = fm.get(field)
            if val is None or str(val).strip() == "":
                findings.append({
                    "appendix_id": app_id,
                    "file": entry["file"],
                    "issue": f"Missing required field: {field}",
                    "severity": SEVERITY_BLOCKING,
                })
        # Status validation
        status = fm.get("status", "")
        if status and status not in VALID_STATUSES:
            findings.append({
                "appendix_id": app_id,
                "file": entry["file"],
                "issue": f"Invalid status: '{status}'",
                "severity": SEVERITY_WARNING,
            })
        # Copy section
        if not entry["has_copy"]:
            findings.append({
                "appendix_id": app_id,
                "file": entry["file"],
                "issue": "Missing ## Copy section",
                "severity": SEVERITY_BLOCKING,
            })
        # ID uniqueness
        if app_id:
            if app_id in seen_ids:
                findings.append({
                    "appendix_id": app_id,
                    "file": entry["file"],
                    "issue": f"Duplicate appendix_id (also in {seen_ids[app_id]})",
                    "severity": SEVERITY_BLOCKING,
                })
            else:
                seen_ids[app_id] = entry["file"]
    return findings


# ─── Index Management ─────────────────────────────────────────────────────────
def parse_existing_index(index_path: Path) -> set[str]:
    """Parse existing INDEX.md and return set of indexed appendix IDs."""
    if not index_path.exists():
        return set()
    indexed = set()
    try:
        content = index_path.read_text(encoding="utf-8")
        # Parse table rows (skip header)
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("|") and not line.startswith("| ID") and not line.startswith("|--"):
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 3 and parts[1]:
                    indexed.add(parts[1])
    except Exception:
        pass
    return indexed


def generate_index(entries: list[dict], appendix_dir: Path) -> str:
    """Generate INDEX.md content from scanned entries."""
    timestamp = datetime.utcnow().isoformat() + "Z"
    lines = [
        "# Appendix Index",
        "",
        "> Auto-generated by appendix-indexer. Manual edits will be overwritten on next sync.",
        f"> Last rebuilt: {timestamp}",
        "",
        "| ID | Title | Parent Document | Status | Owner | Has Copy | Last Updated |",
        "|----|-------|-----------------|--------|-------|----------|--------------|",
    ]
    sorted_entries = sorted(entries, key=lambda e: e.get("appendix_id", ""))
    for entry in sorted_entries:
        app_id = entry.get("appendix_id", "—")
        title = entry.get("title", "—")
        parent = entry.get("parent_document", "—")
        status = entry.get("status", "—")
        owner = entry.get("owner", "—")
        has_copy = "✅" if entry.get("has_copy", False) else "❌"
        updated = entry.get("last_updated", "—")
        lines.append(f"| {app_id} | {title} | {parent} | {status} | {owner} | {has_copy} | {updated} |")
    lines.append("")
    return "\n".join(lines)


def sync_check(entries: list[dict], appendix_dir: Path) -> dict:
    """Compare existing index against directory contents."""
    index_path = appendix_dir / "INDEX.md"
    indexed_ids = parse_existing_index(index_path)
    directory_ids = {e.get("appendix_id", "") for e in entries if e.get("appendix_id")}
    orphans = directory_ids - indexed_ids  # In directory, not in index
    ghosts = indexed_ids - directory_ids  # In index, not in directory
    return {
        "indexed": len(indexed_ids),
        "in_directory": len(directory_ids),
        "orphans": len(orphans),
        "orphan_ids": sorted(orphans),
        "ghosts": len(ghosts),
        "ghost_ids": sorted(ghosts),
        "aligned": len(indexed_ids & directory_ids),
    }


# ─── Cross-Repo Alignment ────────────────────────────────────────────────────
def cross_repo_check(entries: list[dict], core_path: Path) -> dict:
    """Check alignment between docs appendices and core appendices."""
    if not core_path or not core_path.exists():
        return {"error": "Core appendix path not found"}
    core_entries = scan_appendices(core_path)
    core_parents = {e.get("parent_document", ""): e for e in core_entries if e.get("parent_document")}
    doc_parents = {e.get("parent_document", ""): e for e in entries if e.get("parent_document")}
    aligned = 0
    misaligned = 0
    details = []
    for parent, doc_entry in doc_parents.items():
        if parent in core_parents:
            aligned += 1
        else:
            misaligned += 1
            details.append({
                "appendix_id": doc_entry.get("appendix_id", ""),
                "parent": parent,
                "issue": "Parent document not found in uiao-core",
            })
    return {
        "aligned": aligned,
        "misaligned": misaligned,
        "details": details,
    }


# ─── Report ───────────────────────────────────────────────────────────────────
def generate_report(entries: list[dict], findings: list[dict],
                    sync_result: dict = None) -> dict:
    """Generate structured audit report."""
    with_copy = sum(1 for e in entries if e.get("has_copy", False))
    missing_copy = len(entries) - with_copy
    valid_fm = sum(1 for e in entries if e.get("frontmatter") is not None)
    invalid_fm = len(entries) - valid_fm
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "total_appendices": len(entries),
        "with_copy": with_copy,
        "missing_copy": missing_copy,
        "valid_frontmatter": valid_fm,
        "invalid_frontmatter": invalid_fm,
        "total_findings": len(findings),
        "blocking": sum(1 for f in findings if f["severity"] == SEVERITY_BLOCKING),
        "warning": sum(1 for f in findings if f["severity"] == SEVERITY_WARNING),
        "info": sum(1 for f in findings if f["severity"] == SEVERITY_INFO),
        "findings": findings,
        "sync": sync_result,
    }


# ─── CLI ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="UIAO Appendix Indexer")
    parser.add_argument("--path", required=True, help="Target appendix directory")
    parser.add_argument("--mode", default="audit",
                        choices=["audit", "rebuild", "sync", "cross-repo"],
                        help="Operation mode")
    parser.add_argument("--core-path", help="Path to uiao-core appendices (for cross-repo)")
    parser.add_argument("--output", help="Output report JSON file")
    parser.add_argument("--ci", action="store_true", help="CI mode: exit 1 on BLOCKING")
    parser.add_argument("--metrics-only", action="store_true", help="Metrics only")
    args = parser.parse_args()
    appendix_dir = Path(args.path)
    if not appendix_dir.exists():
        print(f"WARNING: Appendix directory not found: {args.path}", file=sys.stderr)
        print("Creating empty report.")
        if args.output:
            os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
            report = generate_report([], [], None)
            with open(args.output, "w") as f:
                json.dump(report, f, indent=2)
        sys.exit(0)
    print("UIAO Appendix Indexer")
    print(f"{'='*50}")
    print(f"Mode: {args.mode}")
    print(f"Target: {args.path}")
    print(f"Timestamp: {datetime.utcnow().isoformat()}Z")
    print()
    entries = scan_appendices(appendix_dir)
    findings = audit_appendices(entries)
    sync_result = None
    print(f"Appendices found: {len(entries)}")
    print(f"With Copy section: {sum(1 for e in entries if e.get('has_copy'))}")
    print(f"Missing Copy: {sum(1 for e in entries if not e.get('has_copy'))}")
    print()
    if args.mode == "rebuild":
        index_content = generate_index(entries, appendix_dir)
        index_path = appendix_dir / "INDEX.md"
        index_path.write_text(index_content, encoding="utf-8")
        print(f"INDEX.md rebuilt with {len(entries)} entries.")
        print(f"Written to: {index_path}")
        print()
    if args.mode in ("sync", "rebuild"):
        sync_result = sync_check(entries, appendix_dir)
        print("Sync Status:")
        print(f"  Indexed: {sync_result['indexed']}")
        print(f"  In directory: {sync_result['in_directory']}")
        print(f"  Orphans: {sync_result['orphans']}")
        print(f"  Ghosts: {sync_result['ghosts']}")
        print()
    if args.mode == "cross-repo" and args.core_path:
        xr = cross_repo_check(entries, Path(args.core_path))
        print("Cross-Repo Alignment:")
        print(f"  Aligned: {xr.get('aligned', 0)}")
        print(f"  Misaligned: {xr.get('misaligned', 0)}")
        print()
    # Print findings
    blocking = sum(1 for f in findings if f["severity"] == SEVERITY_BLOCKING)
    if findings:
        print(f"Findings: {len(findings)} (BLOCKING: {blocking})")
        print(f"{'#':<4} {'Appendix':<15} {'Issue':<45} {'Severity':<10}")
        print("-" * 74)
        for i, f in enumerate(findings, 1):
            print(f"{i:<4} {f['appendix_id'][:15]:<15} "
                  f"{f['issue'][:45]:<45} {f['severity']:<10}")
    else:
        print("✅ All appendices passed integrity check.")
    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        report = generate_report(entries, findings, sync_result)
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport written to: {args.output}")
    if args.ci and blocking > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
