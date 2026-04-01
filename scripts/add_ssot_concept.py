#!/usr/bin/env python3
"""add_ssot_concept.py - Add SSOT concept to files missing it.

Scans all files that reference 'core concepts' but are missing
Single Source of Truth (SSOT) keywords, and injects the SSOT
concept as the first core concept.

Usage:
    python scripts/add_ssot_concept.py [--fix] [--verbose]
"""
import argparse
import os
import re
import sys
from pathlib import Path

SSOT_KEYWORDS = ["single source of truth", "ssot", "authoritative origin"]

SCAN_DIRS = [
    "docs", "canon", "adapters", "compliance", "templates",
    "01_Canon", "exports", "site", "rules", "data",
    "schemas", "src", "dashboard", "analytics", "assets",
]
SCAN_EXTENSIONS = {".md", ".yml", ".yaml", ".html", ".j2", ".json", ".txt"}

# --- SSOT injection templates by file type ---

SSOT_MD_SECTION = """### {num}. Single Source of Truth (SSOT)

The README.md serves as the authoritative origin for all canonical definitions,
concept lists, and architectural decisions. All other documents derive from and
must remain consistent with this single source of truth (SSOT).

"""

SSOT_YAML_ENTRY = '  - "Single Source of Truth (SSOT)"\n'

SSOT_HTML_LI = '      <li><strong>Single Source of Truth (SSOT)</strong> &mdash; The README.md is the authoritative origin for all canonical definitions.</li>\n'


def find_repo_root():
    current = Path(__file__).resolve().parent
    for _ in range(5):
        if (current / ".git").exists() or (current / "README.md").exists():
            return current
        current = current.parent
    return Path.cwd()


def collect_files(repo_root):
    files = []
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


def file_needs_ssot(content):
    """Return True if file mentions core concepts but lacks SSOT."""
    lower = content.lower()
    if "core concepts" not in lower:
        return False
    for kw in SSOT_KEYWORDS:
        if kw in lower:
            return False
    return True


def inject_ssot_md(content):
    """Inject SSOT as first concept in Markdown concept lists."""
    # Pattern: ### N.1. Conversation as the Atomic Unit
    # We insert SSOT before it and renumber
    pattern = re.compile(
        r"(###\s+)(\d+)(\.1\.\s+Conversation\s+as\s+the\s+Atomic\s+Unit)",
        re.IGNORECASE,
    )
    match = pattern.search(content)
    if match:
        prefix = match.group(1)
        section = match.group(2)
        ssot_block = SSOT_MD_SECTION.format(num=f"{section}.1")
        # Insert SSOT block before the match and renumber .1 -> .2
        new_content = content[: match.start()]
        new_content += ssot_block
        new_content += f"{prefix}{section}.2. Conversation as the Atomic Unit"
        rest = content[match.end() :]
        # Renumber subsequent subsections .2->.3, .3->.4, etc.
        for old in range(7, 1, -1):
            rest = rest.replace(
                f"{section}.{old}.", f"{section}.{old + 1}."
            )
        new_content += rest
        return new_content

    # Fallback: just add SSOT mention near "core concepts" phrase
    marker = re.search(r"(?i)(eight\s+core\s+concepts|core\s+concepts)", content)
    if marker:
        pos = content.find("\n", marker.end())
        if pos > 0:
            insert = "\n\n> **Single Source of Truth (SSOT):** The README.md is the authoritative origin for all canonical definitions.\n"
            return content[:pos] + insert + content[pos:]
    return content


def inject_ssot_yaml(content):
    """Inject SSOT into YAML concept lists."""
    # Look for concept list patterns
    pattern = re.compile(
        r'(concepts?:\s*\n)(\s*-\s*"?Conversation)',
        re.IGNORECASE,
    )
    match = pattern.search(content)
    if match:
        return (
            content[: match.end(1)]
            + SSOT_YAML_ENTRY
            + content[match.start(2) :]
        )
    # Fallback: add SSOT keyword near core concepts mention
    marker = re.search(r"(?i)core.concepts", content)
    if marker:
        pos = content.find("\n", marker.end())
        if pos > 0:
            return (
                content[:pos]
                + "\n# Single Source of Truth (SSOT): README.md is the authoritative origin"
                + content[pos:]
            )
    return content


def inject_ssot_html(content):
    """Inject SSOT into HTML concept lists."""
    # Look for <li> with Conversation
    pattern = re.compile(
        r"(<[ou]l>\s*\n)(\s*<li>.*?Conversation)",
        re.IGNORECASE,
    )
    match = pattern.search(content)
    if match:
        return (
            content[: match.end(1)]
            + SSOT_HTML_LI
            + content[match.start(2) :]
        )
    # Fallback: add SSOT meta comment
    marker = re.search(r"(?i)core.concepts", content)
    if marker:
        pos = content.find("\n", marker.end())
        if pos > 0:
            return (
                content[:pos]
                + '\n<!-- SSOT: Single Source of Truth - README.md is the authoritative origin -->'
                + content[pos:]
            )
    return content


def inject_ssot_j2(content):
    """Inject SSOT into Jinja2 templates."""
    marker = re.search(r"(?i)core.concepts", content)
    if marker:
        pos = content.find("\n", marker.end())
        if pos > 0:
            return (
                content[:pos]
                + '\n{# SSOT: Single Source of Truth (SSOT) - README.md is the authoritative origin #}'
                + content[pos:]
            )
    return content


def inject_ssot(content, filepath):
    """Route to the appropriate injection function."""
    ext = filepath.suffix.lower()
    if ext == ".md":
        return inject_ssot_md(content)
    elif ext in (".yml", ".yaml"):
        return inject_ssot_yaml(content)
    elif ext == ".html":
        return inject_ssot_html(content)
    elif ext == ".j2":
        return inject_ssot_j2(content)
    elif ext == ".json":
        # Add ssot keyword in JSON
        marker = re.search(r'(?i)core.concepts', content)
        if marker:
            pos = content.find('"', marker.end())
            if pos > 0 and 'ssot' not in content[marker.start():pos].lower():
                return content[:pos] + ' (includes Single Source of Truth / SSOT)' + content[pos:]
        return content
    return content


def main():
    parser = argparse.ArgumentParser(
        description="Add SSOT concept to files missing it"
    )
    parser.add_argument("--fix", action="store_true", help="Apply fixes")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    repo_root = find_repo_root()
    files = collect_files(repo_root)
    needs_fix = []

    for fpath in files:
        try:
            content = fpath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if file_needs_ssot(content):
            rel = str(fpath.relative_to(repo_root))
            needs_fix.append((fpath, rel, content))
            if args.verbose:
                print(f"  MISSING SSOT: {rel}")

    print(f"Files needing SSOT: {len(needs_fix)}")

    if args.fix:
        fixed = 0
        for fpath, rel, content in needs_fix:
            new_content = inject_ssot(content, fpath)
            if new_content != content:
                fpath.write_text(new_content, encoding="utf-8")
                print(f"  FIXED: {rel}")
                fixed += 1
            else:
                print(f"  SKIPPED (no injection point): {rel}")
        print(f"Fixed {fixed} of {len(needs_fix)} files")
    else:
        print("Run with --fix to apply changes.")

    return 0 if not needs_fix else 1


if __name__ == "__main__":
    sys.exit(main())
