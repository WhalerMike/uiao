#!/usr/bin/env python3
"""Check internal links in documentation files."""

import os
import re
import sys
from pathlib import Path


def find_markdown_files(root_dir):
    """Find all markdown files in the repository."""
    root = Path(root_dir)
    return list(root.rglob("*.md")) + list(root.rglob("*.qmd"))


def check_links(files):
    """Check for broken internal links in markdown files."""
    errors = []
    link_pattern = re.compile(r'\[([^\]]*)\]\(([^)]+)\)')

    for filepath in files:
        content = filepath.read_text(encoding='utf-8', errors='ignore')
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
