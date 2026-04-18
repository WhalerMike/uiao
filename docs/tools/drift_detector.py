#!/usr/bin/env python3
"""
UIAO Drift Detector
====================
Detects, classifies, and reports metadata drift between canonical sources
and derived artifacts. Supports full, targeted, diff, and cross-repo modes.
Usage:
python drift_detector.py --path . --mode full --schema schemas/metadata-schema.json
python drift_detector.py --path canon/UIAO_001.md --mode targeted
python drift_detector.py --base main --head feature/update --mode diff
python drift_detector.py --path . --mode full --cross-repo ../uiao-core
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
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
DRIFT_CATEGORIES = {
    "SCHEMA_DRIFT": SEVERITY_BLOCKING,
    "PROVENANCE_DRIFT": SEVERITY_BLOCKING,
    "BOUNDARY_DRIFT": SEVERITY_BLOCKING,
    "CROSS_REPO_DRIFT": SEVERITY_BLOCKING,
    "VERSION_DRIFT": SEVERITY_WARNING,
    "OWNER_DRIFT": SEVERITY_WARNING,
    "NAMING_DRIFT": SEVERITY_WARNING,
    "FORMAT_DRIFT": SEVERITY_WARNING,
    "COSMETIC_DRIFT": SEVERITY_INFO,
}
VALID_STATUSES = {"Current", "Draft", "Deprecated", "Needs Replacing", "Needs Creating"}
VALID_CLASSIFICATIONS = {"CANONICAL", "DERIVED", "OPERATIONAL"}
DOCUMENT_ID_PATTERN = re.compile(r"^UIAO_\d{3}$")
VERSION_PATTERN = re.compile(r"^\d+\.\d+$")
NAMING_PATTERN = re.compile(r"^UIAO_\d{3}_[\w_]+_v\d+\.\d+\.md$")
BOUNDARY_VIOLATIONS = re.compile(
    r"GCC[\s-]?High|DoD|IL[456]|Azure\s+(IaaS|PaaS)|azure\.com",
    re.IGNORECASE,
)
MERMAID_PATTERN = re.compile(r"```mermaid", re.IGNORECASE)


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


def content_hash(filepath: Path) -> str:
    """Compute SHA-256 hash of file content."""
    try:
        return hashlib.sha256(filepath.read_bytes()).hexdigest()[:16]
    except Exception:
        return ""


# ─── Drift Detectors ─────────────────────────────────────────────────────────
def detect_schema_drift(filepath: Path, fm: dict, base_path: Path) -> list[dict]:
    """Detect schema-level drift in frontmatter."""
    findings = []
    rel = str(filepath.relative_to(base_path))

    def add(category, detail, remediation=""):
        findings.append({
            "file": rel,
            "category": category,
            "severity": DRIFT_CATEGORIES.get(category, SEVERITY_WARNING),
            "detail": detail,
            "remediation": remediation,
        })

    if fm is None:
        add("SCHEMA_DRIFT", "No YAML frontmatter found",
            "Add YAML frontmatter between --- delimiters")
        return findings
    # Required fields check
    required = ["document_id", "title", "version", "status", "classification",
                "owner", "created_at", "updated_at", "boundary"]
    for field in required:
        if field not in fm or fm[field] is None or str(fm[field]).strip() == "":
            add("SCHEMA_DRIFT", f"Missing required field: {field}",
                f"Add {field}: <value>")
    # Format checks
    doc_id = str(fm.get("document_id", ""))
    if doc_id and not DOCUMENT_ID_PATTERN.match(doc_id):
        add("SCHEMA_DRIFT", f"Invalid document_id: '{doc_id}'",
            "Use format UIAO_NNN")
    ver = str(fm.get("version", ""))
    if ver and not VERSION_PATTERN.match(ver):
        add("SCHEMA_DRIFT", f"Invalid version: '{ver}'", "Use format N.N")
    status = fm.get("status", "")
    if status and status not in VALID_STATUSES:
        add("SCHEMA_DRIFT", f"Invalid status: '{status}'",
            f"Use: {', '.join(sorted(VALID_STATUSES))}")
    classification = fm.get("classification", "")
    if classification and classification not in VALID_CLASSIFICATIONS:
        add("SCHEMA_DRIFT", f"Invalid classification: '{classification}'",
            f"Use: {', '.join(sorted(VALID_CLASSIFICATIONS))}")
    return findings


def detect_provenance_drift(filepath: Path, fm: dict, base_path: Path) -> list[dict]:
    """Detect provenance chain drift for DERIVED artifacts."""
    findings = []
    if fm is None:
        return findings
    rel = str(filepath.relative_to(base_path))
    classification = fm.get("classification", "")
    if classification != "DERIVED":
        return findings
    prov = fm.get("provenance", {})
    if not prov or not isinstance(prov, dict):
        findings.append({
            "file": rel,
            "category": "PROVENANCE_DRIFT",
            "severity": SEVERITY_BLOCKING,
            "detail": "DERIVED artifact missing provenance block",
            "remediation": "Add provenance: {source, version, derived_at, derived_by}",
        })
        return findings
    for pf in ["source", "version", "derived_at", "derived_by"]:
        if pf not in prov or not prov[pf]:
            findings.append({
                "file": rel,
                "category": "PROVENANCE_DRIFT",
                "severity": SEVERITY_BLOCKING,
                "detail": f"Provenance missing field: {pf}",
                "remediation": f"Add provenance.{pf}",
            })
    source = prov.get("source", "")
    if source:
        source_path = base_path / source
        if not source_path.exists():
            alt_path = base_path.parent / source
            if not alt_path.exists():
                findings.append({
                    "file": rel,
                    "category": "PROVENANCE_DRIFT",
                    "severity": SEVERITY_BLOCKING,
                    "detail": f"Provenance source not found: {source}",
                    "remediation": "Verify provenance.source path",
                })
    return findings


def detect_boundary_drift(filepath: Path, fm: dict, body: str, base_path: Path) -> list[dict]:
    """Detect cloud boundary violations in content."""
    findings = []
    if fm is None:
        return findings
    rel = str(filepath.relative_to(base_path))
    boundary = fm.get("boundary", "")
    has_exception = fm.get("boundary-exception", False)
    if boundary and boundary != "GCC-Moderate" and not has_exception:
        findings.append({
            "file": rel,
            "category": "BOUNDARY_DRIFT",
            "severity": SEVERITY_BLOCKING,
            "detail": f"Boundary is '{boundary}', expected GCC-Moderate",
            "remediation": "Set boundary: GCC-Moderate or add boundary-exception: true",
        })
    if BOUNDARY_VIOLATIONS.search(body) and not has_exception:
        matches = BOUNDARY_VIOLATIONS.findall(body)
        findings.append({
            "file": rel,
            "category": "BOUNDARY_DRIFT",
            "severity": SEVERITY_BLOCKING,
            "detail": f"Body contains boundary violations: {', '.join(set(matches))}",
            "remediation": "Remove references or add boundary-exception: true",
        })
    return findings


def detect_version_drift(filepath: Path, body: str, base_path: Path) -> list[dict]:
    """Detect references to prior version epochs."""
    findings = []
    rel = str(filepath.relative_to(base_path))
    prior_refs = re.findall(r"v0\.\d+|version\s+0\.\d+|prior\s+version|previous\s+version",
                            body, re.IGNORECASE)
    if prior_refs:
        findings.append({
            "file": rel,
            "category": "VERSION_DRIFT",
            "severity": SEVERITY_WARNING,
            "detail": f"References to prior versions found: {', '.join(set(prior_refs[:5]))}",
            "remediation": "Update to current version references",
        })
    return findings


def detect_naming_drift(filepath: Path, base_path: Path) -> list[dict]:
    """Detect filename naming convention violations."""
    findings = []
    rel = str(filepath.relative_to(base_path))
    # Only check files in canon/ directory
    if "canon" in filepath.parts and not filepath.name.startswith("INDEX"):
        if not NAMING_PATTERN.match(filepath.name):
            findings.append({
                "file": rel,
                "category": "NAMING_DRIFT",
                "severity": SEVERITY_WARNING,
                "detail": f"Filename '{filepath.name}' doesn't match convention",
                "remediation": "Use format: UIAO_NNN_Short_Title_vN.N.md",
            })
    return findings


def detect_cosmetic_drift(filepath: Path, body: str, base_path: Path) -> list[dict]:
    """Detect formatting inconsistencies."""
    findings = []
    rel = str(filepath.relative_to(base_path))
    if MERMAID_PATTERN.search(body):
        findings.append({
            "file": rel,
            "category": "COSMETIC_DRIFT",
            "severity": SEVERITY_INFO,
            "detail": "Uses Mermaid diagrams (PlantUML preferred)",
            "remediation": "Convert to PlantUML",
        })
    return findings


def detect_owner_drift(filepath: Path, fm: dict, base_path: Path) -> list[dict]:
    """Detect missing or stale owner assignments."""
    findings = []
    if fm is None:
        return findings
    rel = str(filepath.relative_to(base_path))
    if not fm.get("owner"):
        findings.append({
            "file": rel,
            "category": "OWNER_DRIFT",
            "severity": SEVERITY_WARNING,
            "detail": "No owner assigned",
            "remediation": "Assign an owner in frontmatter",
        })
    return findings


# ─── Cross-Repo Drift ────────────────────────────────────────────────────────
def detect_cross_repo_drift(filepath: Path, fm: dict, base_path: Path,
                            core_path: Path) -> list[dict]:
    """Detect drift between derived doc and its uiao-core canonical source."""
    findings = []
    if fm is None:
        return findings
    rel = str(filepath.relative_to(base_path))
    prov = fm.get("provenance", {})
    if not prov or not isinstance(prov, dict):
        return findings
    source = prov.get("source", "")
    if not source:
        return findings
    # Resolve source in uiao-core
    source_clean = source.replace("uiao-core/", "")
    source_path = core_path / source_clean
    if not source_path.exists():
        findings.append({
            "file": rel,
            "category": "CROSS_REPO_DRIFT",
            "severity": SEVERITY_BLOCKING,
            "detail": f"Canonical source not found in uiao-core: {source_clean}",
            "remediation": "Verify provenance.source path in uiao-core",
        })
        return findings
    # Compare versions
    core_fm, _ = parse_frontmatter(source_path)
    if core_fm:
        core_version = str(core_fm.get("version", ""))
        local_version = str(prov.get("version", ""))
        if core_version and local_version and core_version != local_version:
            findings.append({
                "file": rel,
                "category": "CROSS_REPO_DRIFT",
                "severity": SEVERITY_BLOCKING,
                "detail": f"Version mismatch: local={local_version}, core={core_version}",
                "remediation": f"Re-derive from uiao-core version {core_version}",
            })
    return findings


# ─── Scan Orchestrator ────────────────────────────────────────────────────────
def scan_file(filepath: Path, base_path: Path, core_path: Path = None) -> list[dict]:
    """Run all drift detectors on a single file."""
    fm, body = parse_frontmatter(filepath)
    findings = []
    findings.extend(detect_schema_drift(filepath, fm, base_path))
    findings.extend(detect_provenance_drift(filepath, fm, base_path))
    findings.extend(detect_boundary_drift(filepath, fm, body, base_path))
    findings.extend(detect_version_drift(filepath, body, base_path))
    findings.extend(detect_naming_drift(filepath, base_path))
    findings.extend(detect_owner_drift(filepath, fm, base_path))
    findings.extend(detect_cosmetic_drift(filepath, body, base_path))
    if core_path:
        findings.extend(detect_cross_repo_drift(filepath, fm, base_path, core_path))
    return findings


def scan_directory(target: Path, base_path: Path, core_path: Path = None) -> tuple[int, list[dict]]:
    """Scan all markdown files in a directory."""
    all_findings = []
    file_count = 0
    if target.is_file():
        if target.suffix == ".md":
            file_count = 1
            all_findings.extend(scan_file(target, base_path, core_path))
    else:
        for md_file in sorted(target.rglob("*.md")):
            if md_file.name in ("INDEX.md", "README.md", "CLAUDE.md"):
                continue
            if ".claude" in md_file.parts or ".github" in md_file.parts:
                continue
            file_count += 1
            all_findings.extend(scan_file(md_file, base_path, core_path))
    return file_count, all_findings


def scan_diff(base_ref: str, head_ref: str, base_path: Path,
              core_path: Path = None) -> tuple[int, list[dict]]:
    """Scan only files changed between two Git refs."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", base_ref, head_ref, "--", "*.md"],
            capture_output=True, text=True, cwd=str(base_path)
        )
        changed_files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    except Exception:
        changed_files = []
    all_findings = []
    file_count = 0
    for rel_path in changed_files:
        filepath = base_path / rel_path
        if filepath.exists() and filepath.suffix == ".md":
            file_count += 1
            all_findings.extend(scan_file(filepath, base_path, core_path))
    return file_count, all_findings


# ─── Report ───────────────────────────────────────────────────────────────────
def generate_report(mode: str, file_count: int, findings: list[dict]) -> dict:
    """Generate structured drift report."""
    blocking = sum(1 for f in findings if f["severity"] == SEVERITY_BLOCKING)
    warning = sum(1 for f in findings if f["severity"] == SEVERITY_WARNING)
    info = sum(1 for f in findings if f["severity"] == SEVERITY_INFO)
    return {
        "mode": mode,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "files_scanned": file_count,
        "drift_count": len(findings),
        "blocking": blocking,
        "warning": warning,
        "info": info,
        "findings": findings,
    }


# ─── CLI ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="UIAO Drift Detector")
    parser.add_argument("--path", default=".", help="Target directory or file")
    parser.add_argument("--mode", default="full",
                        choices=["full", "targeted", "diff", "format"],
                        help="Scan mode")
    parser.add_argument("--base", help="Base Git ref for diff mode")
    parser.add_argument("--head", default="HEAD", help="Head Git ref for diff mode")
    parser.add_argument("--schema", help="Path to metadata schema")
    parser.add_argument("--cross-repo", help="Path to uiao-core for cross-repo drift")
    parser.add_argument("--template", help="Formatting template name")
    parser.add_argument("--output", help="Output report JSON file")
    parser.add_argument("--ci", action="store_true", help="CI mode: exit 1 on BLOCKING")
    parser.add_argument("--metrics-only", action="store_true", help="Metrics only output")
    args = parser.parse_args()
    target = Path(args.path)
    base_path = target if target.is_dir() else target.parent
    core_path = Path(args.cross_repo) if args.cross_repo else None
    print("UIAO Drift Detector")
    print(f"{'='*50}")
    print(f"Mode: {args.mode}")
    print(f"Target: {args.path}")
    if core_path:
        print(f"Cross-repo: {args.cross_repo}")
    print(f"Timestamp: {datetime.utcnow().isoformat()}Z")
    print()
    if args.mode == "diff" and args.base:
        file_count, findings = scan_diff(args.base, args.head, base_path, core_path)
    else:
        file_count, findings = scan_directory(target, base_path, core_path)
    blocking = sum(1 for f in findings if f["severity"] == SEVERITY_BLOCKING)
    warning = sum(1 for f in findings if f["severity"] == SEVERITY_WARNING)
    info = sum(1 for f in findings if f["severity"] == SEVERITY_INFO)
    print(f"Files scanned: {file_count}")
    print(f"Drift instances: {len(findings)}")
    print(f"BLOCKING: {blocking} | WARNING: {warning} | INFO: {info}")
    print()
    if findings:
        print(f"{'#':<4} {'File':<35} {'Category':<20} {'Severity':<10} {'Detail':<40}")
        print("-" * 109)
        for i, f in enumerate(findings, 1):
            print(f"{i:<4} {f['file'][:35]:<35} {f['category']:<20} "
                  f"{f['severity']:<10} {f['detail'][:40]}")
    else:
        print("✅ No drift detected.")
    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        report = generate_report(args.mode, file_count, findings)
        with open(args.output, "w") as out:
            json.dump(report, out, indent=2)
        print(f"\nReport written to: {args.output}")
    if args.ci and blocking > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
