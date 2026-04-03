#!/usr/bin/env python3
"""Validate the directory structure of the repository."""

import os
import sys
from pathlib import Path


REQUIRED_DIRS = [
    ".github",
    ".github/workflows",
    "docs",
    "data",
]

REQUIRED_FILES = [
    "README.md",
    ".gitignore",
    "_quarto.yml",
]


def validate_structure(repo_root):
    """Validate that required directories and files exist."""
    errors = []
    root = Path(repo_root)

    for dir_path in REQUIRED_DIRS:
        full_path = root / dir_path
        if not full_path.is_dir():
            errors.append(f"Missing required directory: {dir_path}")

    for file_path in REQUIRED_FILES:
        full_path = root / file_path
        if not full_path.is_file():
            errors.append(f"Missing required file: {file_path}")

    return errors


def main():
    """Main entry point."""
    repo_root = os.getcwd()
    print(f"Validating directory structure in: {repo_root}")

    errors = validate_structure(repo_root)

    if errors:
        print(f"Found {len(errors)} structural issue(s):")
        for error in errors:
            print(f"  ERROR: {error}")
        return 1

    print("Directory structure is valid!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
