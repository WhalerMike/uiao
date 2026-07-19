#!/usr/bin/env python3
"""Guard the repo-config surface against references to retired path roots.

Post-ADR-032 the tree is a single ``src/uiao/`` package — the pre-flatten
``core/`` and ``impl/`` trees no longer exist. Tooling config that still points
at them (CODEOWNERS rules, devcontainer pytest/ruff settings, PR/issue
templates) becomes a silent no-op: the rule matches nothing, but nothing fails,
so the drift goes undetected. This is exactly the class of drift PR #946 fixed
by hand — this guard keeps it from reappearing.

Scope is deliberately the *config* surface that routes tooling or asserts a
real path (``.github/`` + ``.devcontainer/``), NOT prose docs: AGENTS.md's
"History" section legitimately names ``core/``/``impl/``/``uiao-core`` as the
consolidation narrative, and grepping it would be a false positive.

Add a new retired root to RETIRED_PATTERNS when a future ADR renames or removes
a top-level directory. To exempt a single legitimate line, append the inline
marker ``config-drift-allow`` to it.

Run locally:  python scripts/check_config_paths.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Inline escape hatch: a line containing this token is skipped.
ALLOW_MARKER = "config-drift-allow"

# Config surfaces that route tooling or assert a real repo path. Globs are
# resolved relative to the repo root (this file's grandparent).
SCAN_GLOBS: list[str] = [
    ".github/CODEOWNERS",
    ".github/**/*.md",
    ".github/**/*.yml",
    ".github/**/*.yaml",
    ".devcontainer/**/*.json",
]

# Retired path roots, as they appear in config. The negative lookbehind keeps
# "hardcore/" / "simple/" and similar substrings from matching — the token must
# start at a non-word boundary so only a genuine ``core/`` / ``impl/`` segment
# trips the guard.
RETIRED_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("core/", re.compile(r"(?<![\w-])core/")),
    ("impl/", re.compile(r"(?<![\w-])impl/")),
    # OrgComp rename (2026-07): the series tree moved to orgcomp-series/,
    # the engine volume to uiao-orgcomp-integration/, and the training
    # program to OrgComp-Training-Program/. Old roots must not reappear
    # in config; published-site URLs redirect via per-page aliases.
    ("federal-aan-series/", re.compile(r"federal-aan-series/")),
    ("uiao-aan-integration/", re.compile(r"uiao-aan-integration/")),
    ("AAN-Training-Program/", re.compile(r"AAN-Training-Program/")),
]


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def iter_config_files(root: Path) -> list[Path]:
    seen: set[Path] = set()
    for pattern in SCAN_GLOBS:
        for path in root.glob(pattern):
            if path.is_file():
                seen.add(path)
    return sorted(seen)


def scan_file(path: Path, root: Path) -> list[str]:
    findings: list[str] = []
    rel = path.relative_to(root)
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if ALLOW_MARKER in line:
            continue
        for label, pattern in RETIRED_PATTERNS:
            if pattern.search(line):
                findings.append(f"{rel}:{lineno}: retired path root '{label}' — {line.strip()}")
    return findings


def main() -> int:
    root = repo_root()
    findings: list[str] = []
    for path in iter_config_files(root):
        findings.extend(scan_file(path, root))

    if findings:
        print("Config-path drift detected — retired core/ or impl/ roots in repo config:\n")
        for finding in findings:
            print(f"  {finding}")
        print(
            "\nPost-ADR-032 the tree is a single src/uiao/ package. Re-point these "
            "to src/uiao/** (or tests/) so the rule resolves to a real path.\n"
            f"To exempt a genuinely-correct line, append '{ALLOW_MARKER}' to it."
        )
        return 1

    print(f"Config-path guard OK — scanned {len(iter_config_files(root))} config files, no retired path roots.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
