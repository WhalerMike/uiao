#!/usr/bin/env python3
"""Guard canon + docs against references to non-existent ADRs.

Every ``ADR-NNN`` (canonical 3-digit zero-padded form) mentioned in canon, docs,
or the root agent files must resolve to a real ``src/uiao/canon/adr/adr-NNN-*.md``
file. A dangling reference means either a typo or — the failure mode this guard
exists for — a hallucinated decision record: an agent confidently citing
``ADR-142`` for a decision that was never made. Tests don't exercise prose, so
without this guard such a citation merges silently and corrodes the provenance
chain the substrate depends on.

The whole corpus resolves cleanly today (4,900+ references, 0 dangling), so this
gate is green from day one and purely guards against regressions.

Scope notes:
- Only the canonical 3-digit form ``ADR-NNN`` is validated. Placeholders like
  ``ADR-NNN`` in templates don't match and are ignored by design.
- Non-canon scratch surfaces (``inbox/``, ``models/``) are excluded — drafts may
  legitimately reference proposed-but-unallocated ADR numbers.
- To exempt a single line, append the inline marker ``adr-ref-allow`` to it.

Run locally:  python scripts/check_adr_references.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ALLOW_MARKER = "adr-ref-allow"

# Files whose ADR references must resolve. Globs are relative to the repo root.
SCAN_GLOBS: list[str] = [
    "src/uiao/canon/**/*.md",
    "docs/**/*.md",
    "docs/**/*.qmd",
    "AGENTS.md",
    "AGENTS-public-surface.md",
    "README.md",
    "CONTRIBUTING.md",
]

ADR_DIR = Path("src/uiao/canon/adr")
ADR_FILE_RE = re.compile(r"adr-(\d{3})-")
ADR_REF_RE = re.compile(r"\bADR-(\d{3})\b")


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def valid_adr_ids(root: Path) -> set[str]:
    ids: set[str] = set()
    for path in (root / ADR_DIR).iterdir():
        match = ADR_FILE_RE.match(path.name)
        if match:
            ids.add(match.group(1))
    return ids


def iter_scan_files(root: Path) -> list[Path]:
    seen: set[Path] = set()
    for pattern in SCAN_GLOBS:
        for path in root.glob(pattern):
            if path.is_file():
                seen.add(path)
    return sorted(seen)


def scan_file(path: Path, root: Path, valid: set[str]) -> list[str]:
    findings: list[str] = []
    rel = path.relative_to(root)
    for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        if ALLOW_MARKER in line:
            continue
        for match in ADR_REF_RE.finditer(line):
            if match.group(1) not in valid:
                findings.append(f"{rel}:{lineno}: dangling ADR-{match.group(1)} — {line.strip()}")
    return findings


def main() -> int:
    root = repo_root()
    valid = valid_adr_ids(root)
    if not valid:
        print(f"error: no ADR files found under {ADR_DIR} — wrong working directory?")
        return 2

    files = iter_scan_files(root)
    findings: list[str] = []
    for path in files:
        findings.extend(scan_file(path, root, valid))

    if findings:
        print("Dangling ADR references — cited ADR-NNN has no adr-NNN-*.md file:\n")
        for finding in findings:
            print(f"  {finding}")
        print(
            f"\nValid ADR ids range over {min(valid)}..{max(valid)} "
            f"({len(valid)} files under {ADR_DIR}).\n"
            "Fix the reference (typo / wrong number) or add the missing ADR. For a "
            f"genuinely-intended placeholder, append '{ALLOW_MARKER}' to the line."
        )
        return 1

    print(f"ADR-reference guard OK — scanned {len(files)} files, all ADR-NNN references resolve.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
