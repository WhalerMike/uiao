#!/usr/bin/env python3
"""spec_test_audit.py — UIAO_103 Spec-Test Enforcement audit tool.

Scans canon spec markdown files for normative statements (MUST, SHALL,
REQUIRED, MUST NOT, SHALL NOT, RECOMMENDED, SHOULD) per RFC 2119 and
emits a structured inventory the coverage gate consumes.

The audit is intentionally syntactic: it counts invariants, not semantics.
It cannot tell you whether a given test actually validates the invariant —
that mapping lives in ``docs/docs/governance/spec-test-coverage.md`` and
is maintained by the author when a new test lands. The gate enforces that
the count of covered invariants per spec never decreases between PRs.

Pipeline:

    src/uiao/canon/specs/*.md                    (input)
    src/uiao/canon/UIAO_*.md                     (input — top-level docs)
            │
            ▼
    spec_test_audit.py                            (this tool)
            │  parse YAML frontmatter (document_id) + extract MUST/SHALL/...
            ▼
    {document_id, file, line, kind, statement}    (structured JSON)
            │
            ▼
    spec_test_coverage_check.py                   (CI gate)
            │  diff against committed coverage table
            ▼
    PR pass / fail

USAGE
    # Print per-spec invariant counts to stdout
    python scripts/tools/spec_test_audit.py

    # Emit full inventory as JSON
    python scripts/tools/spec_test_audit.py --json > audit.json

    # Audit a single spec
    python scripts/tools/spec_test_audit.py --spec src/uiao/canon/specs/Compliance-Orchestrator.md

Exit codes:
    0 — audit completed
    2 — bad input (missing dir, etc.)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPEC_ROOTS: tuple[Path, ...] = (
    REPO_ROOT / "src" / "uiao" / "canon" / "specs",
    REPO_ROOT / "src" / "uiao" / "canon",
)

# RFC 2119 normative keywords. We exclude lowercase to avoid prose like
# "you should consider" — only ALL-CAPS counts as a normative invariant.
# MUST NOT and SHALL NOT are recognized as separate invariant kinds.
_KEYWORDS = ("MUST NOT", "SHALL NOT", "MUST", "SHALL", "REQUIRED", "RECOMMENDED", "SHOULD")
_KEYWORD_PATTERN = re.compile(r"\b(MUST NOT|SHALL NOT|MUST|SHALL|REQUIRED|RECOMMENDED|SHOULD)\b")
_FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_DOCUMENT_ID_PATTERN = re.compile(r"^document_id:\s*(\S+)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class Invariant:
    """One normative statement extracted from a canon spec."""

    document_id: str
    file: str  # repo-relative
    line: int  # 1-indexed
    kind: str  # MUST | SHALL | REQUIRED | RECOMMENDED | SHOULD | MUST NOT | SHALL NOT
    statement: str  # trimmed sentence containing the keyword


@dataclass(frozen=True)
class SpecRollup:
    """Per-spec count of invariants by kind."""

    document_id: str
    file: str
    total: int
    by_kind: dict[str, int]


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _extract_document_id(text: str) -> str:
    m = _FRONTMATTER_PATTERN.match(text)
    if not m:
        return ""
    fm = m.group(1)
    m2 = _DOCUMENT_ID_PATTERN.search(fm)
    return m2.group(1).strip().strip('"').strip("'") if m2 else ""


def _strip_code_blocks(text: str) -> str:
    """Replace fenced code blocks with blank lines so line numbers are preserved
    but invariant keywords inside fences don't count."""
    out: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append("")
            continue
        out.append("" if in_fence else line)
    return "\n".join(out)


def _split_sentences(line: str) -> list[str]:
    """Coarse sentence split. Keeps it simple — every ``. ``, ``? `` or
    ``! `` followed by a capital letter starts a new sentence."""
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z(\[])", line.strip())
    return [p.strip() for p in parts if p.strip()]


def extract_invariants(path: Path) -> list[Invariant]:
    """Yield one Invariant per normative keyword occurrence in ``path``.

    Multiple keywords on one line produce multiple invariants. Code blocks
    are stripped before extraction so example syntax doesn't inflate counts.
    """
    raw = _read(path)
    if not raw:
        return []
    document_id = _extract_document_id(raw)
    if not document_id:
        return []

    body = _strip_code_blocks(raw)
    try:
        rel = str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        # Path is outside REPO_ROOT (e.g., tmp_path under tests). Use the
        # absolute path as-is — safer than crashing.
        rel = str(path)
    invariants: list[Invariant] = []
    for line_idx, line in enumerate(body.splitlines(), start=1):
        if not _KEYWORD_PATTERN.search(line):
            continue
        # One Invariant per (line, kind) — multiple kinds on same line are
        # recorded separately so the rollup matches what humans skim.
        seen_kinds: set[str] = set()
        for match in _KEYWORD_PATTERN.finditer(line):
            kind = match.group(1)
            if kind in seen_kinds:
                continue
            seen_kinds.add(kind)
            sentence = _statement_for(line, match.start())
            invariants.append(
                Invariant(
                    document_id=document_id,
                    file=rel,
                    line=line_idx,
                    kind=kind,
                    statement=sentence,
                )
            )
    return invariants


def _statement_for(line: str, keyword_start: int) -> str:
    """Trim the line to a sentence-ish chunk around the keyword."""
    sentences = _split_sentences(line)
    for s in sentences:
        if any(k in s for k in _KEYWORDS):
            return s[:240]
    return line.strip()[:240]


# ---------------------------------------------------------------------------
# Audit driver
# ---------------------------------------------------------------------------


def iter_spec_files(roots: Iterable[Path]) -> list[Path]:
    """Return every *.md file under ``roots`` whose frontmatter declares a
    ``document_id``. Non-canon markdown is silently skipped."""
    seen: set[Path] = set()
    out: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.md")):
            resolved = path.resolve()
            if resolved in seen:
                continue
            text = _read(path)
            if not _extract_document_id(text):
                continue
            seen.add(resolved)
            out.append(path)
    return out


def audit(roots: Iterable[Path] = DEFAULT_SPEC_ROOTS) -> list[Invariant]:
    invariants: list[Invariant] = []
    for spec in iter_spec_files(roots):
        invariants.extend(extract_invariants(spec))
    return invariants


def rollup(invariants: Iterable[Invariant]) -> list[SpecRollup]:
    """Return per-spec counts. Stable order: by document_id ascending."""
    by_spec: dict[tuple[str, str], dict[str, int]] = {}
    for inv in invariants:
        key = (inv.document_id, inv.file)
        by_spec.setdefault(key, {}).setdefault(inv.kind, 0)
        by_spec[key][inv.kind] += 1
    rollups = [
        SpecRollup(
            document_id=document_id,
            file=file,
            total=sum(counts.values()),
            by_kind=dict(sorted(counts.items())),
        )
        for (document_id, file), counts in by_spec.items()
    ]
    rollups.sort(key=lambda r: r.document_id)
    return rollups


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--spec",
        type=Path,
        action="append",
        help="Audit only this spec file (repeatable). Default: all canon specs.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit full invariant inventory as JSON on stdout.",
    )
    parser.add_argument(
        "--rollup",
        action="store_true",
        help="Emit per-spec rollup as JSON on stdout (counts by kind).",
    )
    parser.add_argument(
        "--root",
        type=Path,
        action="append",
        help="Override spec roots. Repeatable. Default: src/uiao/canon/specs + src/uiao/canon.",
    )
    args = parser.parse_args(argv)

    if args.spec:
        invariants: list[Invariant] = []
        for spec in args.spec:
            invariants.extend(extract_invariants(spec))
    else:
        roots = tuple(args.root) if args.root else DEFAULT_SPEC_ROOTS
        invariants = audit(roots)

    if args.json:
        json.dump([asdict(i) for i in invariants], sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    if args.rollup:
        json.dump([asdict(r) for r in rollup(invariants)], sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    # Default: human-readable rollup table.
    rolls = rollup(invariants)
    if not rolls:
        print("(no canon specs with normative statements found)")
        return 0
    print(f"{'document_id':<15} {'total':>5}  by kind")
    print("-" * 60)
    for r in rolls:
        kinds = ", ".join(f"{k}={v}" for k, v in r.by_kind.items())
        print(f"{r.document_id:<15} {r.total:>5}  {kinds}")
    print("-" * 60)
    print(f"{'TOTAL':<15} {sum(r.total for r in rolls):>5}  ({len(rolls)} specs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
