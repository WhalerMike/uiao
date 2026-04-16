#!/usr/bin/env python3
"""Check internal links in documentation files."""

import os
import re
import sys
from pathlib import Path


def find_markdown_files(root_dir):
    """Find all markdown files in the repository."""
    root = Path(root_dir)
    return [p for p in list(root.rglob("*.md")) + list(root.rglob("*.qmd")) if not (p.parent == root and p.name in ("index.md", "index-scuba.md", "SUMMARY.md"))]


def _strip_fenced_code(content):
    """Remove fenced code blocks (``` ... ```) so link syntax inside them
    isn't mistaken for a real link. Inline code spans are left alone; the
    upstream regex is permissive enough that stripping them isn't required
    for correctness on current inputs, and keeping them preserves the
    original line/column semantics for any future error messages.
    """
    return re.sub(r'```.*?```', '', content, flags=re.DOTALL)


def check_links(files):
    """Check for broken internal links in markdown files."""
    errors = []
    link_pattern = re.compile(r'\[([^\]]*)\]\(([^)]+)\)')

    for filepath in files:
        content = filepath.read_text(encoding='utf-8', errors='ignore')
        content = _strip_fenced_code(content)
        for match in link_pattern.finditer(content):
            link_text, link_target = match.groups()
            if link_target.startswith(('http://', 'https://', '#', 'mailto:')):
                continue
            base = link_target.split('#')[0]
            if base:
                target_path = filepath.parent / base
                if not target_path.exists():
                    errors.append(
                        f"{filepath}: broken link [{link_text}]({link_target})"
                    )

    return errors


def main():
    """Main entry point."""
    repo_root = os.getcwd()
    print(f"Checking internal links in: {repo_root}")

    files = find_markdown_files(repo_root)
    print(f"Found {len(files)} documentation files")

    errors = check_links(files)

    if errors:
        print(f"Found {len(errors)} broken link(s):")
        for error in errors:
            print(f"  ERROR: {error}")
        return 1

    print("All internal links are valid!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
