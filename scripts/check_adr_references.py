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

The guard also validates the **ADR relationship graph** in frontmatter
(``supersedes`` / ``superseded_by`` / ``amends``). Prose asserts these
relationships freely — "this ADR supersedes ADR-048" — while the frontmatter
that would make them machine-readable stays null, so nothing can answer "what
supersedes this?" without reading bodies. Three rules:

1. **Resolution** — every id named in a relationship field must resolve to a
   real ``adr-NNN-*.md``, and no ADR may name itself.
2. **Symmetry** — if A declares ``superseded_by: B`` then B must declare
   ``supersedes: A``, and vice versa. A supersession recorded on one side only
   is a half-edge the graph can't be walked from.
3. **Presence** (advisory) — every ADR should carry both ``supersedes`` and
   ``superseded_by``, even if null. Reported as a warning, not a failure, so the
   63 files currently missing one or both (91 gaps) don't land this gate red;
   promote to an error once backfilled.

``amends`` is validated for resolution only. There is no ``amended_by``
convention in the corpus, and inventing one is out of scope for a metadata
guard — so amendment is a one-way edge here by design.

Run locally:  python scripts/check_adr_references.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

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


# ---------------------------------------------------------------------------
# Relationship graph (supersedes / superseded_by / amends)
# ---------------------------------------------------------------------------

RELATION_FIELDS = ("supersedes", "superseded_by", "amends")
# Fields carrying an inverse that must also be recorded. `amends` has no
# `amended_by` counterpart in the corpus, so it is resolution-checked only.
INVERSE = {"supersedes": "superseded_by", "superseded_by": "supersedes"}


def parse_frontmatter(text: str) -> dict | None:
    """Return the YAML frontmatter block as a dict, or None if absent/unparseable."""
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        loaded = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None
    return loaded if isinstance(loaded, dict) else None


def adr_ids_in(value: object) -> set[str]:
    """Extract 3-digit ADR ids from a relationship value.

    Tolerates every shape the corpus actually uses: ``null``, ``[]``, a bare id
    (``adr-066``), a filename (``adr-092-active-governance.md``), a list, and
    prose entries like ``["ADR-025 §D7 (federal/commercial firewall)"]``.
    """
    if value is None:
        return set()
    items = value if isinstance(value, (list, tuple)) else [value]
    ids: set[str] = set()
    for item in items:
        if not isinstance(item, str):
            continue
        ids.update(m.group(1) for m in re.finditer(r"[Aa][Dd][Rr]-(\d{3})\b", item))
    return ids


def scan_relationships(root: Path, valid: set[str]) -> tuple[list[str], list[str]]:
    """Validate the relationship graph. Returns (errors, warnings)."""
    errors: list[str] = []
    warnings: list[str] = []
    graph: dict[str, dict[str, set[str]]] = {}

    for path in sorted((root / ADR_DIR).glob("adr-*.md")):
        match = ADR_FILE_RE.match(path.name)
        if not match:
            continue
        self_id = match.group(1)
        rel = path.relative_to(root).as_posix()
        frontmatter = parse_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
        if frontmatter is None:
            warnings.append(f"{rel}: frontmatter missing or unparseable — relationship fields not checked")
            continue

        graph[self_id] = {field: adr_ids_in(frontmatter.get(field)) for field in RELATION_FIELDS}

        for field in ("supersedes", "superseded_by"):
            if field not in frontmatter:
                warnings.append(f"{rel}: no '{field}:' field (backfill pending, issue #1427)")

        for field in RELATION_FIELDS:
            for target in sorted(graph[self_id][field]):
                if target not in valid:
                    errors.append(f"{rel}: {field} names ADR-{target}, which has no adr-{target}-*.md")
                elif target == self_id:
                    errors.append(f"{rel}: {field} names itself (ADR-{self_id})")

    # Symmetry: every recorded edge must be recorded from the other end too.
    for self_id, fields in graph.items():
        for field, inverse in INVERSE.items():
            for target in sorted(fields[field]):
                if target not in graph or target == self_id:
                    continue
                if self_id not in graph[target][inverse]:
                    errors.append(
                        f"adr-{self_id}: declares {field}: ADR-{target}, but "
                        f"adr-{target} does not declare {inverse}: ADR-{self_id}"
                    )
    return errors, warnings


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

    rel_errors, rel_warnings = scan_relationships(root, valid)

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

    if rel_errors:
        print("\nADR relationship-graph errors — frontmatter edges that don't resolve or don't pair:\n")
        for finding in rel_errors:
            print(f"  {finding}")
        print(
            "\nRecord the relationship from BOTH ends: if A is superseded by B, A carries\n"
            "'superseded_by: adr-B-slug.md' and B carries 'supersedes: adr-A-slug.md'."
        )

    if findings or rel_errors:
        return 1

    print(f"ADR-reference guard OK — scanned {len(files)} files, all ADR-NNN references resolve.")
    print(f"ADR relationship graph OK — {len(valid)} ADRs, all frontmatter edges resolve and pair.")
    if rel_warnings:
        print(f"\nAdvisory — {len(rel_warnings)} relationship-metadata gaps (non-blocking):")
        for warning in rel_warnings[:10]:
            print(f"  {warning}")
        if len(rel_warnings) > 10:
            print(f"  … and {len(rel_warnings) - 10} more")
    return 0


if __name__ == "__main__":
    sys.exit(main())
