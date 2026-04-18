#!/usr/bin/env python3
"""
cleanup_live_doc_links.py — scoped post-reorg path cleanup.

Updates live user-facing documentation to use the new src/uiao/ layout.
Operates on an EXPLICIT ALLOWLIST; leaves historical artifacts
(ADRs, session logs, CHANGELOG, appendices, canon body text) alone.

Uses a negative-lookbehind regex so pre-monorepo references with the
`uiao-core/` hyphenated form (cross-repo references from before the
consolidation) are NOT matched.

Usage (from the monorepo root):

    python scripts/cleanup_live_doc_links.py --dry-run
    python scripts/cleanup_live_doc_links.py
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Negative lookbehind (?<![\w-]) prevents matching the tail of
# `uiao-core/canon/` while still matching `core/canon/`, `/core/canon/`,
# `main/core/canon/`, `(core/canon/`, etc.
SUBS = [
    (re.compile(r"(?<![\w-])core/canon/"),   "src/uiao/canon/"),
    (re.compile(r"(?<![\w-])core/schemas/"), "src/uiao/schemas/"),
    (re.compile(r"(?<![\w-])core/rules/"),   "src/uiao/rules/"),
    (re.compile(r"(?<![\w-])core/ksi/"),     "src/uiao/ksi/"),
]

# Explicit allowlist — we only touch these.
ALLOWLIST = [
    # Top-level contributor / project docs
    "AGENTS.md",
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    # GitHub templates
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/ISSUE_TEMPLATE/adapter-activation.yml",
    ".github/ISSUE_TEMPLATE/canon-change-request.yml",
    # docs/ top-level
    "docs/README.md",
    # docs/academy/
    "docs/academy/comics.qmd",
    "docs/academy/contributor-tier-1-setup.qmd",
    "docs/academy/contributor-track.qmd",
    "docs/academy/document-generation-guide.qmd",
    "docs/academy/image-pipeline-guide.qmd",
    "docs/academy/index.qmd",
    "docs/academy/operator-track.qmd",
    "docs/academy/adapters/entra-id.qmd",
    # docs/docs/ architecture + glossary + substrate-status
    "docs/docs/00_ControlPlaneArchitecture.qmd",
    "docs/docs/01_UnifiedArchitecture.qmd",
    "docs/docs/02_CanonSpecification.qmd",
    "docs/docs/13_FIMF_AdapterRegistry.qmd",
    "docs/docs/glossary.qmd",
    "docs/docs/substrate-status.qmd",
    "docs/docs/canon/glossary.md",
    "docs/docs/adr/index.md",
    # docs/docs/customer-documents/ (hand-listed roots; per-adapter avs are globbed)
    "docs/docs/customer-documents/index.qmd",
    "docs/docs/customer-documents/adapter-technical-specifications/index.qmd",
    "docs/docs/customer-documents/adapter-validation-suites/index.qmd",
    # docs/findings/
    "docs/findings/README.md",
    "docs/findings/index.qmd",
    "docs/findings/fedramp-gcc-moderate-informed-network-routing.md",
    # docs/narrative/ (live program narratives — historical GOS narrative has its own refs)
    "docs/narrative/governance-os-directory-migration.md",
    "docs/narrative/program-education.qmd",
    "docs/narrative/program-project-plans.qmd",
    "docs/narrative/program-test-plans.qmd",
    "docs/narrative/program-training.qmd",
    # docs/programs/
    "docs/programs/index.qmd",
    "docs/programs/uiao_125.qmd",
    "docs/programs/uiao_126.qmd",
    "docs/programs/uiao_127.qmd",
    "docs/programs/uiao_128.qmd",
    # docs/series/
    "docs/series/index.qmd",
    "docs/series/application-aware-networking-book/index.qmd",
    "docs/series/series-01-federal-modernization/index.qmd",
    "docs/series/series-05-unified-architecture/index.qmd",
    # inbox/ (contributor-facing, not archival)
    "inbox/README.md",
    "inbox/drafts/README.md",
]

# Glob patterns added on top of the literal allowlist.
ALLOWLIST_GLOBS = [
    "docs/docs/customer-documents/adapter-validation-suites/*/avs-*.qmd",
]


def collect_files() -> list[Path]:
    files: list[Path] = []
    seen: set[str] = set()
    for rel in ALLOWLIST:
        p = REPO_ROOT / rel
        key = str(p.resolve()) if p.exists() else str(p)
        if p.exists() and key not in seen:
            files.append(p)
            seen.add(key)
    for pattern in ALLOWLIST_GLOBS:
        for p in REPO_ROOT.glob(pattern):
            key = str(p.resolve())
            if key not in seen:
                files.append(p)
                seen.add(key)
    return files


def process_file(path: Path, dry_run: bool) -> int:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  skip (unreadable): {path.relative_to(REPO_ROOT)} — {e}")
        return 0
    new_text = text
    hit_count = 0
    for pattern, replacement in SUBS:
        hit_count += len(pattern.findall(new_text))
        new_text = pattern.sub(replacement, new_text)
    if new_text == text:
        return 0
    rel = path.relative_to(REPO_ROOT)
    print(f"  update: {rel}  ({hit_count} substitution{'s' if hit_count != 1 else ''})")
    if not dry_run:
        path.write_text(new_text, encoding="utf-8", newline="\n")
    return hit_count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dry-run", action="store_true", help="Preview only, do not write.")
    args = parser.parse_args()

    print(f"=== cleanup_live_doc_links — repo root: {REPO_ROOT} ===")
    if args.dry_run:
        print("[DRY RUN — no files will be written]")
    print()

    files = collect_files()
    print(f"Allowlist resolved to {len(files)} file(s) on disk.\n")

    total_subs = 0
    touched_files = 0
    for f in files:
        n = process_file(f, args.dry_run)
        if n:
            total_subs += n
            touched_files += 1

    verb = "would change" if args.dry_run else "updated"
    print()
    print(f"{touched_files} file(s) {verb}, {total_subs} total substitution(s).")
    if total_subs == 0:
        print("(nothing to do — either already clean, or allowlist files missing)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
