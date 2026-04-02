#!/usr/bin/env python3
"""fix_concept_lists.py - Replace old 7-item concept lists with new 8-item lists.

Scans all repository files for:
1. The old numbered concept list (starting with "1. Conversation as the atomic unit")
   and prepends SSOT as #1, renumbering the remaining items 2-8.
2. Text references to "Seven Core Concepts" -> "Eight Core Concepts" (and variants).

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
    r"(1\.\s+\*{0,2}Conversation as the atomic unit\*{0,2})"
    r"(.*?)"
    r"(7\.\s+\*{0,2}Public service first\*{0,2}[^\n]*)",
    re.DOTALL,
)

# New SSOT line to prepend
SSOT_LINE = "1. **Single Source of Truth (SSOT)** \u2014 UIAO operates on the principle that every claim has one authoritative origin. All other representations are pointers, not copies. This ensures provenance, prevents drift, and enables federated truth resolution across boundaries."

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

# Text replacement patterns for "Seven" -> "Eight" references
TEXT_REPLACEMENTS = [
    (re.compile(r"\bseven\s+core\s+concepts?\b", re.IGNORECASE), "Eight Core Concepts"),
    (re.compile(r"\b7\s+core\s+concepts?\b", re.IGNORECASE), "8 Core Concepts"),
    (re.compile(r"\bSeven\s+Core\s+Concepts?\b"), "Eight Core Concepts"),
    (re.compile(r"\*\*Seven Core Concepts\*\*"), "**Eight Core Concepts**"),
    (re.compile(r"\*\*7 Core Concepts\*\*"), "**8 Core Concepts**"),
    (re.compile(r"built\s+on\s+(?:the\s+)?seven\b", re.IGNORECASE), "built on the Eight"),
    (re.compile(r'"seven\s+core\s+concepts?"', re.IGNORECASE), '"Eight Core Concepts"'),
    (re.compile(r"'seven\s+core\s+concepts?'", re.IGNORECASE), "'Eight Core Concepts'"),
    (re.compile(r"seven\s+\(7\)\s+core\s+concepts?", re.IGNORECASE), "Eight (8) Core Concepts"),
    (re.compile(r"\bseven\s+foundational\s+concepts?\b", re.IGNORECASE), "eight foundational concepts"),
    (re.compile(r"\bseven\s+pillars?\b", re.IGNORECASE), "eight pillars"),
]

SCAN_DIRS = [
    "docs",
    "canon",
    "adapters",
    "compliance",
    "templates",
    "01_Canon",
    "exports",
    "site",
    "rules",
    "data",
    "schemas",
    "src",
    "dashboard",
    "analytics",
    "reports",
    "assets",
    "_extensions",
    "tools",
    "tests",
    "deploy",
    "validation-targets",
]
SCAN_EXTENSIONS = {
    ".md",
    ".yml",
    ".yaml",
    ".html",
    ".j2",
    ".json",
    ".txt",
    ".py",
    ".ps1",
    ".sh",
    ".css",
    ".js",
    ".xml",
    ".toml",
}

SCAN_ROOT_FILES = [
    "README.md",
    "CONTRIBUTING.md",
    "AGENTS.md",
    "PROJECT-CONTEXT.md",
    "UIAO-MEMORY.md",
    "FORMAT-CANON.md",
    "USAGE.md",
    "CODE_OF_CONDUCT.md",
    "CHANGELOG.md",
    "NOTICE",
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
            # Skip hidden directories and node_modules
            dirs[:] = [dd for dd in dirs if not dd.startswith(".") and dd != "node_modules"]
            for fname in fnames:
                ext = os.path.splitext(fname)[1].lower()
                if ext in SCAN_EXTENSIONS:
                    files.append(Path(root) / fname)
    return sorted(set(files))


def fix_list_in_content(content):
    """Find the old 7-item list and replace with 8-item list."""
    changed = False

    def replacer(match):
        nonlocal changed
        full = match.group(0)
        lines = full.split("\n")
        new_lines = []
        for line in lines:
            m = re.match(r"^(\d+)\.\s", line)
            if m:
                old_num = m.group(1)
                if old_num in RENUMBER:
                    line = RENUMBER[old_num] + ". " + line[len(m.group(0)) :]
            new_lines.append(line)
        renumbered = "\n".join(new_lines)
        changed = True
        return SSOT_LINE + "\n" + renumbered

    new_content = OLD_LIST_PATTERN.sub(replacer, content)
    return new_content, changed


def fix_text_references(content):
    """Replace all 'Seven Core Concepts' text variants with 'Eight Core Concepts'."""
    changed = False
    for pattern, replacement in TEXT_REPLACEMENTS:
        new_content = pattern.sub(replacement, content)
        if new_content != content:
            changed = True
            content = new_content
    return content, changed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    repo_root = find_repo_root()
    files = collect_files(repo_root)
    print(f"Scanning {len(files)} files...")

    found_list = []
    found_text = []
    fixed = []

    for fpath in files:
        try:
            content = fpath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        rel = fpath.relative_to(repo_root)
        has_old_list = bool(OLD_LIST_PATTERN.search(content))
        has_old_text = any(p.search(content) for p, _ in TEXT_REPLACEMENTS)

        if has_old_list:
            found_list.append(str(rel))
            if args.verbose:
                print(f"FOUND LIST: {rel}")

        if has_old_text:
            found_text.append(str(rel))
            if args.verbose:
                print(f"FOUND TEXT: {rel}")

        if args.fix and (has_old_list or has_old_text):
            new_content = content
            any_changed = False

            if has_old_list:
                new_content, list_changed = fix_list_in_content(new_content)
                any_changed = any_changed or list_changed

            if has_old_text:
                new_content, text_changed = fix_text_references(new_content)
                any_changed = any_changed or text_changed

            if any_changed:
                fpath.write_text(new_content, encoding="utf-8")
                fixed.append(str(rel))
                print(f"FIXED: {rel}")

    print(f"\nFiles with old 7-item list: {len(found_list)}")
    print(f"Files with old 'Seven' text: {len(found_text)}")
    if args.fix:
        print(f"Files fixed: {len(fixed)}")

    if found_list:
        print("\nFiles with old list:")
        for f in found_list:
            print(f"  - {f}")

    if found_text:
        print("\nFiles with old text references:")
        for f in found_text:
            print(f"  - {f}")

    if (found_list or found_text) and not args.fix:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
