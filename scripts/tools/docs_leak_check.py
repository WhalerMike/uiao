"""Blast-radius guardrail for the public UIAO Modernization Atlas.

Fails if anything that belongs in `evidence/` (tenant artifacts, POA&M
CSV rows, SAR drops, ConMon meeting minutes) leaks into `docs/` — the
tree that Quarto renders into the public website.

Rules enforced (see .github/workflows/docs-leak-check.yml for the
full rationale):

  R1. No file under `docs/**/` may live in a subdirectory literally
      named `evidence`.
  R2. No `docs/**/*.{md,qmd,yml,yaml}` file may reference an
      `evidence/<subpath>` path outside of inline-code (backticks).
      Backticked references are allowed as documentation; live
      references are not.
  R3. No `docs/_site/**` build output is committed.

Exit codes:
    0 — clean.
    1 — one or more violations (details printed).
"""

from __future__ import annotations

import pathlib
import re
import sys

DOCS_ROOT = pathlib.Path("docs")
SCAN_EXTENSIONS = {".md", ".qmd", ".yml", ".yaml"}

# Matches references to the *tenant-evidence data tree* — the subpaths
# under `evidence/` that hold real artifacts (per ADR-025 and ADR-043).
# Excludes legitimate references to the Python package
# `src/uiao/evidence/*` and generic CLI output paths like
# `evidence/latest.json` by requiring a known sensitive subdirectory
# AND requiring that the match is not preceded by another path
# segment (negative-lookbehind for word char or `/`).
EVIDENCE_SUBTREES = (
    "conformance",
    "conmon",
    "oscal",
    "sar",
    "ssp",
    "poam",
    "findings",
)
EVIDENCE_PATTERN = re.compile(
    r"(?<![\w/])evidence/(?:" + "|".join(EVIDENCE_SUBTREES) + r")(?:/[\w\-./]*)?"
)

# Backticked inline code spans AND fenced code blocks — allowed.
# Order matters: the fenced-block alternative must be tried first so
# that ``` ... ``` is consumed as a single span, not split into three
# inline spans that leak the interior content.
BACKTICK_SPAN = re.compile(r"```[\s\S]*?```|`[^`\n]*`")


def violations_r1(docs_root: pathlib.Path) -> list[str]:
    """Any path under docs/ that contains a literal `evidence` dir."""
    hits: list[str] = []
    if not docs_root.is_dir():
        return hits
    for path in docs_root.rglob("*"):
        if not path.is_file():
            continue
        parts = path.relative_to(docs_root).parts
        if "evidence" in parts:
            hits.append(f"R1: {path} lives inside a docs/ subdirectory named `evidence/`")
    return hits


def violations_r2(docs_root: pathlib.Path) -> list[str]:
    """Live references to `evidence/<subpath>` outside backtick spans."""
    hits: list[str] = []
    if not docs_root.is_dir():
        return hits
    for path in sorted(docs_root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SCAN_EXTENSIONS:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        # Mask out everything inside backtick spans, then scan what's left.
        masked = BACKTICK_SPAN.sub(lambda m: " " * len(m.group(0)), text)
        for match in EVIDENCE_PATTERN.finditer(masked):
            line_no = masked.count("\n", 0, match.start()) + 1
            snippet = match.group(0)
            hits.append(
                f"R2: {path}:{line_no} references `{snippet}` outside "
                f"an inline-code span — wrap in backticks if documentation."
            )
    return hits


def violations_r3(docs_root: pathlib.Path) -> list[str]:
    """docs/_site/** must not be committed."""
    hits: list[str] = []
    site_dir = docs_root / "_site"
    if not site_dir.exists():
        return hits
    # If _site is a directory AND has any tracked files, flag it.
    # We can't tell "tracked" from here without running git, so instead
    # we flag any file inside. CI checkout populates only tracked
    # content, so presence implies committed.
    for path in site_dir.rglob("*"):
        if path.is_file():
            hits.append(f"R3: {path} — docs/_site/** is build output and must not be committed")
            break  # one flag per repo is enough
    return hits


def main() -> int:
    all_hits: list[str] = []
    all_hits.extend(violations_r1(DOCS_ROOT))
    all_hits.extend(violations_r2(DOCS_ROOT))
    all_hits.extend(violations_r3(DOCS_ROOT))

    if not all_hits:
        print("docs-leak-check: clean — no evidence/** leaks into docs/**.")
        return 0

    print(f"docs-leak-check: {len(all_hits)} violation(s):", file=sys.stderr)
    for hit in all_hits:
        print(f"  - {hit}", file=sys.stderr)
    print(
        "\nSee .github/workflows/docs-leak-check.yml for the rule definitions "
        "and the backtick-allowlist convention.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
