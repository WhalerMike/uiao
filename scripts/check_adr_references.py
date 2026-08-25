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

The guard also validates the **full ADR filename**, not just the number.
``ADR-NNN`` resolving to *some* ``adr-NNN-*.md`` is a weak assertion: it passes
for ``[ADR-047](adr-047-fedramp-20x-integration.md)`` even though ADR-047 is the
Continuous Monitoring Program and the FedRAMP 20x decision was renumbered to
ADR-106. That is the renumbering failure mode — the number survives a
renumbering, the slug does not, and a number-only gate never notices. So every
``adr-NNN-slug.ext`` spelled out anywhere in a scanned file (link target, inline
code, bare path) must match a real ADR filename stem exactly.

Two details make this check match how the corpus actually cites ADRs:

- **Both ADR directories count.** ``src/uiao/canon/adr/`` holds the canonical
  ``.md`` sources; ``docs/adr/`` holds the rendered ``.qmd`` mirror. A stem valid
  in either is valid, because docs legitimately cite the mirror.
- **The extension is not constrained.** ``.md``, ``.qmd``, and ``.html`` all
  address the same ADR — ``.html`` being the Quarto render-time target of a
  ``.qmd``. The stem carries the identity; the extension is a surface.

Scope notes:
- Only the canonical 3-digit form ``ADR-NNN`` is validated. Placeholders like
  ``ADR-NNN`` in templates don't match and are ignored by design.
- Non-canon scratch surfaces (``inbox/``, ``models/``) are excluded — drafts may
  legitimately reference proposed-but-unallocated ADR numbers.
- ``CHANGELOG.md`` is in scope. It was outside the original path filter, which
  is exactly why the v0.6.0 entry citing the deleted
  ``adr-058-hrit-productization-mission.md`` (renumbered to ADR-065 to clear an
  ADR-058 slot collision) survived every prior run of this gate.
- To exempt a single line, append the inline marker ``adr-ref-allow`` to it.
  Deliberate historical filename mentions — a renumbering note, a
  ``prior_filename:`` provenance field, a collision post-mortem — are the
  intended users of this marker: they cite a filename precisely *because* it no
  longer exists.

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
    "CHANGELOG.md",
]

ADR_DIR = Path("src/uiao/canon/adr")

# Both directories that hold real ADR files. canon/adr is the canonical `.md`
# source; docs/adr is the rendered `.qmd` mirror the published site links to.
# Filename validation accepts a stem present in either.
ADR_DIRS: tuple[Path, ...] = (ADR_DIR, Path("docs/adr"))

ADR_FILE_RE = re.compile(r"adr-(\d{3})-")
ADR_REF_RE = re.compile(r"\bADR-(\d{3})\b")

# An ADR filename spelled out anywhere in a line — inside a link target, inline
# code, or bare prose. `.html` is the Quarto render target of a `.qmd` and
# addresses the same ADR, so all three extensions are accepted and the stem
# alone is matched against the corpus.
ADR_FILENAME_RE = re.compile(r"\badr-(?P<num>\d{3})-(?P<slug>[A-Za-z0-9][A-Za-z0-9._-]*?)\.(?P<ext>md|qmd|html)\b")


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


def valid_adr_stems(root: Path) -> dict[str, set[str]]:
    """Map each allocated ADR number to the filename stems that really exist.

    A number maps to more than one stem only while a slot collision is
    unresolved, so the set is normally a singleton. Both ADR directories are
    read: canon holds `.md`, docs holds the `.qmd` mirror, and the stem is the
    same on both sides.
    """
    stems: dict[str, set[str]] = {}
    for adr_dir in ADR_DIRS:
        resolved = root / adr_dir
        if not resolved.is_dir():
            continue
        for path in resolved.iterdir():
            match = re.fullmatch(r"(adr-(\d{3})-.*?)\.(?:md|qmd)", path.name)
            if match:
                stems.setdefault(match.group(2), set()).add(match.group(1))
    return stems


def scan_file(path: Path, root: Path, valid: set[str], stems: dict[str, set[str]]) -> tuple[list[str], list[str]]:
    """Scan one file. Returns (dangling-number findings, wrong-filename findings)."""
    dangling: list[str] = []
    misnamed: list[str] = []
    rel = path.relative_to(root)
    for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        if ALLOW_MARKER in line:
            continue
        for match in ADR_REF_RE.finditer(line):
            if match.group(1) not in valid:
                dangling.append(f"{rel}:{lineno}: dangling ADR-{match.group(1)} — {line.strip()}")
        for match in ADR_FILENAME_RE.finditer(line):
            num = match.group("num")
            cited = f"adr-{num}-{match.group('slug')}"
            if num not in stems:
                # The number itself is unallocated. ADR_REF_RE already reports
                # that when the line also spells `ADR-NNN`; report it here too
                # so a bare filename citation is never silently accepted.
                misnamed.append(f"{rel}:{lineno}: {match.group(0)} — no ADR {num} exists")
            elif cited not in stems[num]:
                real = ", ".join(f"{s}.md" for s in sorted(stems[num]))
                misnamed.append(f"{rel}:{lineno}: {match.group(0)} — ADR-{num} is {real}")
    return dangling, misnamed


# ---------------------------------------------------------------------------
# Relationship graph (supersedes / superseded_by / amends)
# ---------------------------------------------------------------------------

RELATION_FIELDS = ("supersedes", "superseded_by", "amends")
# Fields carrying an inverse that must also be recorded. `amends` has no
# `amended_by` counterpart in the corpus, so it is resolution-checked only.
INVERSE = {"supersedes": "superseded_by", "superseded_by": "supersedes"}


# Stdlib-only frontmatter reading, deliberately. This guard's workflow does a
# bare setup-python with no dependency install, matching its sibling guards, so
# importing PyYAML here would fail in CI while passing locally. Only three short
# scalar/list fields are needed, and the id regex below does the real work — a
# full YAML parse would buy nothing.
FRONTMATTER_KEY_RE = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_]*):(?P<rest>.*)$")
ADR_ID_IN_VALUE_RE = re.compile(r"[Aa][Dd][Rr]-(\d{3})\b")


def frontmatter_block(text: str) -> str | None:
    """Return the raw frontmatter block, or None when the file has none."""
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    return parts[1] if len(parts) >= 3 else None


def field_text(block: str, field: str) -> str | None:
    """Return one top-level field's raw value text, or None when absent.

    Captures the rest of the ``key:`` line plus any following indented list or
    continuation lines, so both the scalar form (``amends: adr-066``) and the
    block-list form (``amends:\\n  - adr-063-….md``) are covered. Absent is
    distinct from present-but-null — the presence rule needs to tell them apart.
    """
    collected: list[str] | None = None
    for line in block.splitlines():
        match = FRONTMATTER_KEY_RE.match(line)
        if match:
            if collected is not None:
                break  # next top-level key ends this value
            if match.group("key") == field:
                collected = [match.group("rest")]
        elif collected is not None:
            if line.strip() and not line[:1].isspace():
                break
            collected.append(line)
    return "\n".join(collected) if collected is not None else None


def adr_ids_in(value: str | None) -> set[str]:
    """Extract 3-digit ADR ids from a relationship field's raw value text.

    Tolerates every shape the corpus actually uses: ``null``, ``[]``, a bare id
    (``adr-066``), a filename (``adr-092-active-governance.md``), a block list,
    and prose entries like ``["ADR-025 §D7 (federal/commercial firewall)"]``.
    """
    if not value:
        return set()
    return {m.group(1) for m in ADR_ID_IN_VALUE_RE.finditer(value)}


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
        block = frontmatter_block(path.read_text(encoding="utf-8", errors="replace"))
        if block is None:
            warnings.append(f"{rel}: no frontmatter block — relationship fields not checked")
            continue

        raw = {field: field_text(block, field) for field in RELATION_FIELDS}
        graph[self_id] = {field: adr_ids_in(raw[field]) for field in RELATION_FIELDS}

        for field in ("supersedes", "superseded_by"):
            if raw[field] is None:
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

    stems = valid_adr_stems(root)
    files = iter_scan_files(root)
    findings: list[str] = []
    misnamed: list[str] = []
    for path in files:
        file_dangling, file_misnamed = scan_file(path, root, valid, stems)
        findings.extend(file_dangling)
        misnamed.extend(file_misnamed)

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

    if misnamed:
        print("\nWrong ADR filenames — the number is real, the filename is not:\n")
        for finding in misnamed:
            print(f"  {finding}")
        print(
            "\nThis is the renumbering failure mode: an ADR moved to a new number or\n"
            "slug and the citation kept the old filename. The number-only check above\n"
            "cannot see it. Point the citation at the real filename, or — if the line\n"
            "deliberately names a file that no longer exists (a renumbering note, a\n"
            f"'prior_filename:' field, a collision post-mortem) — append '{ALLOW_MARKER}'\n"
            "to it."
        )

    if rel_errors:
        print("\nADR relationship-graph errors — frontmatter edges that don't resolve or don't pair:\n")
        for finding in rel_errors:
            print(f"  {finding}")
        print(
            "\nRecord the relationship from BOTH ends: if A is superseded by B, A carries\n"
            "'superseded_by: adr-B-slug.md' and B carries 'supersedes: adr-A-slug.md'."
        )

    if findings or misnamed or rel_errors:
        return 1

    print(f"ADR-reference guard OK — scanned {len(files)} files, all ADR-NNN references resolve.")
    print(
        f"ADR-filename guard OK — every adr-NNN-slug.ext citation matches a real "
        f"filename across {len(ADR_DIRS)} ADR directories."
    )
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
