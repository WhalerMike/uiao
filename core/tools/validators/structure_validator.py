#!/usr/bin/env python3
"""structure_validator.py - Validate repository structure against schema.

Loads tools/schema/directory_schema.json (the schema) together with
tools/schema/directory_structure.yaml (the payload that enumerates the
required directories, required files, and forbidden patterns for this
repository). Confirms:

  1. The payload itself conforms to directory_schema.json.
  2. Every required directory exists.
  3. Every required file exists.
  4. No path matches a forbidden pattern (shell-style glob).

Exit codes:
    0 - Repository structure is valid.
    1 - One or more structural invariants violated.
    2 - A fatal configuration problem (missing schema/payload).

Usage:
    python tools/validators/structure_validator.py
"""

from __future__ import annotations

import fnmatch
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "tools" / "schema" / "directory_schema.json"
PAYLOAD_PATH = REPO_ROOT / "tools" / "schema" / "directory_structure.yaml"

# Directories that should never be scanned for forbidden patterns when
# falling back to filesystem traversal. These are standard VCS/venv cruft
# or gitignored build artefacts that aren't part of the governed tree.
_EXCLUDED_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "build",
    "dist",
    "htmlcov",
    ".quarto",
    "_site",
}


def _load_schema() -> dict[str, Any]:
    """Load the directory-structure schema JSON from disk."""
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _validate_payload(payload: Any, schema: dict[str, Any]) -> list[str]:
    """Return a list of human-readable schema validation errors (empty on success)."""
    try:
        from jsonschema import Draft7Validator  # type: ignore[import-not-found]
    except ImportError:
        return ["jsonschema package not installed; skipping schema validation"]

    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path))
    return [
        f"{'.'.join(str(p) for p in err.absolute_path) or '<root>'}: {err.message}"
        for err in errors
    ]


def _check_required_directories(required: list[str]) -> list[str]:
    missing: list[str] = []
    for rel in required:
        path = REPO_ROOT / rel
        if not path.is_dir():
            missing.append(rel)
    return missing


def _check_required_files(required: list[str]) -> list[str]:
    missing: list[str] = []
    for rel in required:
        path = REPO_ROOT / rel
        if not path.is_file():
            missing.append(rel)
    return missing


def _git_tracked_paths() -> list[Path] | None:
    """Return tracked paths via ``git ls-files``; None if git is unavailable."""
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None
    tracked: list[Path] = []
    seen_dirs: set[Path] = set()
    for line in result.stdout.splitlines():
        rel = line.strip()
        if not rel:
            continue
        path = REPO_ROOT / rel
        tracked.append(path)
        # Also record every parent directory so forbidden-pattern checks can
        # catch disallowed directory names without us having to walk the FS.
        for parent in path.parents:
            if parent == REPO_ROOT:
                break
            if parent not in seen_dirs:
                seen_dirs.add(parent)
                tracked.append(parent)
    return tracked


def _iter_scan_paths() -> list[Path]:
    """Walk the repo, skipping excluded directories and unreadable entries.

    Prefers ``git ls-files`` to keep the scan aligned with the tracked tree
    (which is what CI enforces). Falls back to a filesystem walk so the
    validator remains usable outside a git checkout.
    """
    tracked = _git_tracked_paths()
    if tracked is not None:
        return tracked

    collected: list[Path] = []
    stack = [REPO_ROOT]
    while stack:
        current = stack.pop()
        try:
            entries = list(current.iterdir())
        except (PermissionError, OSError):
            continue
        for entry in entries:
            if entry.name in _EXCLUDED_DIR_NAMES:
                continue
            collected.append(entry)
            try:
                is_dir = entry.is_dir()
                is_link = entry.is_symlink()
            except (PermissionError, OSError):
                continue
            if is_dir and not is_link:
                stack.append(entry)
    return collected


def _check_forbidden_patterns(patterns: list[str]) -> list[str]:
    """Return repo-relative paths that match any forbidden glob pattern."""
    if not patterns:
        return []
    offenders: list[str] = []
    for path in _iter_scan_paths():
        name = path.name
        for pattern in patterns:
            if fnmatch.fnmatch(name, pattern):
                offenders.append(str(path.relative_to(REPO_ROOT)))
                break
    return sorted(offenders)


def main() -> int:
    """Validate repository structure. Returns 0 on success, 1 on failures, 2 on fatal errors."""
    if not SCHEMA_PATH.is_file():
        print(
            f"[structure_validator] FATAL: schema not found at {SCHEMA_PATH}",
            file=sys.stderr,
        )
        return 2
    if not PAYLOAD_PATH.is_file():
        print(
            f"[structure_validator] FATAL: payload not found at {PAYLOAD_PATH}",
            file=sys.stderr,
        )
        return 2

    try:
        schema = _load_schema()
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[structure_validator] FATAL: cannot load schema: {exc}", file=sys.stderr)
        return 2

    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        print(
            "[structure_validator] FATAL: PyYAML is required (pip install pyyaml).",
            file=sys.stderr,
        )
        return 2

    try:
        payload = yaml.safe_load(PAYLOAD_PATH.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        print(f"[structure_validator] FATAL: cannot load payload: {exc}", file=sys.stderr)
        return 2

    if not isinstance(payload, dict):
        print("[structure_validator] FAIL: payload is not a mapping")
        return 1

    schema_errors = _validate_payload(payload, schema)
    if schema_errors:
        print("[structure_validator] FAIL: payload does not conform to schema:")
        for err in schema_errors:
            print(f"    - {err}")
        return 1

    failures = 0

    required_dirs = payload.get("required_directories", []) or []
    missing_dirs = _check_required_directories(required_dirs)
    if missing_dirs:
        print("[structure_validator] FAIL: missing required directories:")
        for rel in missing_dirs:
            print(f"    - {rel}")
        failures += len(missing_dirs)

    required_files = payload.get("required_files", []) or []
    missing_files = _check_required_files(required_files)
    if missing_files:
        print("[structure_validator] FAIL: missing required files:")
        for rel in missing_files:
            print(f"    - {rel}")
        failures += len(missing_files)

    forbidden_patterns = payload.get("forbidden_patterns", []) or []
    offenders = _check_forbidden_patterns(forbidden_patterns)
    if offenders:
        print("[structure_validator] FAIL: forbidden patterns present:")
        for rel in offenders:
            print(f"    - {rel}")
        failures += len(offenders)

    if failures == 0:
        print(
            f"[structure_validator] OK: {len(required_dirs)} required directories, "
            f"{len(required_files)} required files, "
            f"{len(forbidden_patterns)} forbidden patterns — all invariants satisfied."
        )
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
