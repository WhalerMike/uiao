#!/usr/bin/env python3
"""fix_concept_lists.py - Replace old 7-item concept lists with new 8-item lists.

Scans all repository files for the old numbered concept list (starting with
"1. Conversation as the atomic unit") and prepends SSOT as #1, renumbering
the remaining items 2-8.

Usage:
    python scripts/fix_concept_lists.py [--fix] [--verbose]
"""

import argparse
import os
import re
import sys
from pathlib import Path


# The old pattern: a numbered list starting with "1. Conversation" or "1. **Conversation"
# We need to match variations: with/without bold, with/without markdown
OLD_LIST_PATTERN = re.compile(
    r'(1\.\s+\*{0,2}Conversation as the atomic unit\*{0,2})'
    r'(.*?)'
    r'(7\.\s+\*{0,2}Public service first\*{0,2}[^\n]*)',
    re.DOTALL
)

# New SSOT line to prepend
SSOT_LINE = "1. **Single Source of Truth (SSOT)** — UIAO operates on the principle that every claim has one authoritative origin. All other representations are pointers, not copies. This ensures provenance, prevents drift, and enables federated truth resolution across boundaries."

# Renumbering map
RENUMBER = {
    "1": "2",
    "2": "3",
    "3": "4",
    "4": "5",
    "5": "6",
    "6": "7",
    "7": "8",
}

SCAN_DIRS = ["docs", "canon", "adapters", "compliance", "templates", "01_Canon",
             "exports", "site", "rules", "data", "schemas", "src", "dashboard",
             "analytics", "reports", "assets", "_extensions"]

SCAN_EXTENSIONS = {".md", ".yml", ".yaml", ".html", ".j2", ".json", ".txt"}

SCAN_ROOT_FILES = [
    "README.md", "CONTRIBUTING.md", "AGENTS.md", "PROJECT-CONTEXT.md",
    "UIAO-MEMORY.md", "FORMAT-CANON.md", "USAGE.md",
]


def find_repo_root():
    current = Path(__file__).resolve().parent
    for _ in range(5):
        if (current / ".git").exists() or (current / "README.md").exists():
            return current
        current = current.parent
    return Path.cwd()


def collect_files(repo_root):
    files = []
    for root_file in SCAN_ROOT_FILES:
        p = repo_root / root_file
        if p.exists():
            files.append(p)
    for scan_dir in SCAN_DIRS:
        d = repo_root / scan_dir
        if not d.exists():
            continue
        for root, dirs, fnames in os.walk(d):
            for fname in fnames:
                ext = os.path.splitext(fname)[1].lower()
                if ext in SCAN_EXTENSIONS:
                    files.append(Path(root) / fname)
    return files


def fix_list_in_content(content):
    """Find the old 7-item list and replace with 8-item list."""
    changed = False

    # Pattern: find "1. Conversation" through "7. Public service"
    # and renumber while prepending SSOT
    def replacer(match):
        nonlocal changed
        full = match.group(0)
        # Renumber 1->2, 2->3, ..., 7->8
        lines = full.split('\n')
        new_lines = []
        for line in lines:
            # Match numbered items like "1. " "2. " etc
            m = re.match(r'^(\d+)\.\s', line)
            if m:
                old_num = m.group(1)
                if old_num in RENUMBER:
                    line = RENUMBER[old_num] + '. ' + line[len(m.group(0)):]
            new_lines.append(line)
        renumbered = '\n'.join(new_lines)
        changed = True
        return SSOT_LINE + '\n' + renumbered

    new_content = OLD_LIST_PATTERN.sub(replacer, content)
    return new_content, changed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    repo_root = find_repo_root()
    files = collect_files(repo_root)

    print(f"Scanning {len(files)} files...")

    found = []
    fixed = []

    for fpath in files:
        try:
            content = fpath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        # Check if file has old list pattern
        if OLD_LIST_PATTERN.search(content):
            rel = fpath.relative_to(repo_root)
            found.append(str(rel))
            if args.verbose:
                print(f"FOUND: {rel}")

            if args.fix:
                new_content, changed = fix_list_in_content(content)
                if changed:
                    fpath.write_text(new_content, encoding="utf-8")
                    fixed.append(str(rel))
                    print(f"FIXED: {rel}")

    print(f"\nFiles with old 7-item list: {len(found)}")
    if args.fix:
        print(f"Files fixed: {len(fixed)}")

    if found:
        print("\nFiles found:")
        for f in found:
            print(f"  - {f}")

    if found and not args.fix:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
