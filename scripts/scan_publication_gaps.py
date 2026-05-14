#!/usr/bin/env python3
"""Scan src/uiao/ for content that should appear on the published site.

Implements the policy declared in ADR-068
(src/uiao/canon/adr/adr-068-canon-publication-policy.md):

  - Walks src/uiao/canon/, src/uiao/modernization/, and src/uiao/schemas/
  - Reads frontmatter (or applies path-pattern defaults) for publish_to_site
  - Parses docs/_quarto.yml to discover what is currently published
  - Reports the gap: documents intended for publication that have no
    .qmd page in the sidebar

Outputs:
  - stdout:  human-readable summary table
  - tools/publication-gaps/report.md   (full markdown report)
  - tools/publication-gaps/report.json (machine-readable equivalent)

Exit codes:
  0  always in advisory mode (default)
  1  if --strict and any gap is detected

Usage:
  python scripts/scan_publication_gaps.py
  python scripts/scan_publication_gaps.py --strict
  python scripts/scan_publication_gaps.py --json-only

Design notes:
  - The scanner is path-pattern-driven and does not modify any files.
  - Frontmatter parsing uses PyYAML (already a project dependency via
    scripts/validate_canon_frontmatter.py).
  - _quarto.yml is parsed as a generic YAML tree; the scanner walks it
    looking for href/contents leaves and treats anything ending in .qmd
    as a registered publication entry.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from dataclasses import asdict, dataclass, field
from typing import Any

import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
QUARTO_CONFIG = REPO_ROOT / "docs" / "_quarto.yml"
REPORT_DIR = REPO_ROOT / "tools" / "publication-gaps"
REPORT_MD = REPORT_DIR / "report.md"
REPORT_JSON = REPORT_DIR / "report.json"

FM_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", re.DOTALL)

# Roots scanned for publishable content. Paths are relative to REPO_ROOT.
SCAN_ROOTS: list[tuple[pathlib.Path, str]] = [
    (REPO_ROOT / "src" / "uiao" / "canon", "canon"),
    (REPO_ROOT / "src" / "uiao" / "modernization", "modernization"),
    (REPO_ROOT / "src" / "uiao" / "schemas", "schemas"),
]

# Content classes — used for grouping in the report.
CLASS_UIAO_SPEC = "uiao-spec"
CLASS_ADR = "adr"
CLASS_MODERNIZATION = "modernization"
CLASS_SCHEMA = "schema"
CLASS_OTHER = "other"


@dataclass
class CandidateDoc:
    """One repository document considered for publication."""

    path: pathlib.Path
    rel_path: str
    content_class: str
    publish_to_site: bool
    publish_intent_source: str  # "frontmatter" | "default" | "exclusion"
    publication_style: str | None
    document_id: str | None = None
    expected_qmd_paths: list[str] = field(default_factory=list)
    matched_qmd_path: str | None = None
    matched_via: str | None = None  # "expected-path" | "link-back-path" | "link-back-id"
    in_sidebar: bool = False
    gap_reason: str | None = None


def parse_frontmatter(text: str) -> dict[str, Any]:
    """Return frontmatter dict, or {} if no frontmatter is present."""
    m = FM_PATTERN.match(text)
    if not m:
        return {}
    try:
        loaded = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return {}
    return loaded or {}


def classify(path: pathlib.Path) -> str:
    """Categorize a path by content class for reporting."""
    rel = path.relative_to(REPO_ROOT).as_posix()
    if rel.startswith("src/uiao/canon/adr/"):
        return CLASS_ADR
    if rel.startswith("src/uiao/canon/") and path.name.startswith("UIAO_"):
        return CLASS_UIAO_SPEC
    if rel.startswith("src/uiao/canon/"):
        return CLASS_OTHER
    if rel.startswith("src/uiao/modernization/"):
        return CLASS_MODERNIZATION
    if rel.startswith("src/uiao/schemas/"):
        return CLASS_SCHEMA
    return CLASS_OTHER


def default_publish_intent(path: pathlib.Path) -> tuple[bool, str]:
    """Apply ADR-068 default publication intent when frontmatter is silent.

    Returns (publish_to_site, reason).
    """
    rel = path.relative_to(REPO_ROOT).as_posix()
    name = path.name

    # Explicit exclusions first.
    if name in {"README.md", "INDEX.md", "index.md"}:
        return (False, "exclusion: README/INDEX not published as standalone page")
    if name == "adr-000-adr-process.md":
        return (False, "exclusion: ADR process meta-document is internal")

    # Path-pattern defaults from ADR-068.
    if rel.startswith("src/uiao/canon/adr/") and name.startswith("adr-"):
        return (True, "default: ADR is publishable")
    if rel.startswith("src/uiao/canon/") and name.startswith("UIAO_"):
        return (True, "default: UIAO_NNN spec is publishable")
    if rel.startswith("src/uiao/modernization/") and name.endswith(".md"):
        return (True, "default: modernization-module doc is publishable")
    if rel.startswith("src/uiao/schemas/") and name.endswith(".schema.json"):
        return (True, "default: schema is publishable as developer reference")

    return (False, "default: not in a publication-default path pattern")


def default_publication_style(path: pathlib.Path) -> str:
    """Apply ADR-068 default publication style."""
    rel = path.relative_to(REPO_ROOT).as_posix()
    if rel.startswith("src/uiao/schemas/"):
        return "reference"
    # ADRs and modernization docs default to include; UIAO marquee
    # specs default to narrative because most have hand-authored .qmd
    # pages today.
    if rel.startswith("src/uiao/canon/UIAO_"):
        return "narrative"
    return "include"


def expected_qmd_paths_for(path: pathlib.Path) -> list[str]:
    """Heuristic mapping from canon source path to candidate .qmd paths.

    The mapping is plural because multiple naming conventions co-exist
    on the site today (e.g., docs/modernization/directory-migration.qmd
    for src/uiao/modernization/directory-migration/README.md). Returning
    multiple candidates lets the matcher accept any of them.
    """
    rel = path.relative_to(REPO_ROOT).as_posix()
    candidates: list[str] = []

    if rel.startswith("src/uiao/canon/adr/"):
        # ADRs: docs/adr/{stem}.qmd or docs/canon/adr/{stem}.qmd
        stem = path.stem
        candidates.append(f"docs/adr/{stem}.qmd")
        candidates.append(f"docs/canon/adr/{stem}.qmd")

    elif rel.startswith("src/uiao/canon/") and path.name.startswith("UIAO_"):
        # UIAO marquee specs: heuristic — extract NNN and short name
        stem = path.stem
        candidates.append(f"docs/canon/{stem}.qmd")
        # Also accept any docs/**/*{NNN}* page that mentions the doc id
        # (full text scan would be expensive; we leave that to the
        # matcher's link-based fallback below).

    elif rel.startswith("src/uiao/modernization/"):
        # Modernization-module docs: parallel path under docs/modernization/
        # Strip src/uiao/ prefix, append .qmd.
        # Special case: README.md collapses to the parent directory name.
        sub = pathlib.Path(rel).relative_to("src/uiao")
        if sub.name.lower() == "readme.md":
            candidates.append(f"docs/{sub.parent.as_posix()}.qmd")
            candidates.append(f"docs/{sub.parent.as_posix()}/index.qmd")
        else:
            candidates.append(f"docs/{sub.with_suffix('.qmd').as_posix()}")

    elif rel.startswith("src/uiao/schemas/"):
        # Schemas: docs/reference/schemas/{stem}.qmd
        candidates.append(f"docs/reference/schemas/{path.stem}.qmd")

    return candidates


def collect_sidebar_qmds(quarto_yml: pathlib.Path) -> set[str]:
    """Extract every .qmd path referenced by docs/_quarto.yml.

    Walks the YAML tree generically and collects any string value
    ending in .qmd. The result is the set of "currently published"
    pages from the scanner's perspective.
    """
    if not quarto_yml.exists():
        return set()
    with quarto_yml.open(encoding="utf-8") as fh:
        tree = yaml.safe_load(fh)
    found: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, str):
            if node.endswith(".qmd"):
                # Sidebar entries are relative to docs/, so prefix.
                if not node.startswith("docs/"):
                    found.add(f"docs/{node}")
                else:
                    found.add(node)
        elif isinstance(node, dict):
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(tree)
    return found


def index_sidebar_content(sidebar_qmds: set[str]) -> dict[str, str]:
    """Read each sidebar-listed .qmd and return {qmd_path: full_text}.

    Quarto resolves paths relative to docs/_quarto.yml's directory
    (i.e., docs/). So a YAML value of "modernization/orgtree.qmd"
    is at docs/modernization/orgtree.qmd, and a YAML value of
    "docs/quickstart.qmd" is at docs/docs/quickstart.qmd.

    The collect_sidebar_qmds() pre-pass ensures every entry already
    starts with "docs/". This function then tries:
      1. The path as-is (e.g., docs/modernization/orgtree.qmd)
      2. With an additional docs/ prefix (e.g., docs/docs/quickstart.qmd)

    Used by the link-back detector to find canon references inside
    published narrative pages.
    """
    index: dict[str, str] = {}
    for rel in sorted(sidebar_qmds):
        # Try the path as-is first (e.g., docs/modernization/orgtree.qmd
        # is at REPO_ROOT/docs/modernization/orgtree.qmd).
        candidates = [REPO_ROOT / rel]
        # If that misses, the YAML value was something like
        # "docs/quickstart.qmd" meaning relative to the docs/ project
        # root → actual file at REPO_ROOT/docs/docs/quickstart.qmd.
        if rel.startswith("docs/"):
            candidates.append(REPO_ROOT / "docs" / rel)

        path = next((c for c in candidates if c.exists()), None)
        if path is None:
            continue
        try:
            index[rel] = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
    return index


def scan() -> list[CandidateDoc]:
    """Walk SCAN_ROOTS and produce a CandidateDoc per file."""
    sidebar_qmds = collect_sidebar_qmds(QUARTO_CONFIG)
    sidebar_content = index_sidebar_content(sidebar_qmds)
    candidates: list[CandidateDoc] = []

    for root, _label in SCAN_ROOTS:
        if not root.exists():
            continue
        # Collect both .md and .schema.json
        files = list(root.rglob("*.md")) + list(root.rglob("*.schema.json"))
        for path in sorted(files):
            content_class = classify(path)
            rel_path = path.relative_to(REPO_ROOT).as_posix()

            # Read frontmatter for .md; .json files have no frontmatter.
            fm: dict[str, Any] = {}
            if path.suffix == ".md":
                try:
                    text = path.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    text = ""
                fm = parse_frontmatter(text)

            # Resolve publish_to_site
            if "publish_to_site" in fm:
                publish = bool(fm["publish_to_site"])
                intent_source = "frontmatter"
            else:
                publish, reason = default_publish_intent(path)
                intent_source = "exclusion" if reason.startswith("exclusion") else "default"

            style = fm.get("publication_style") or (default_publication_style(path) if publish else None)

            # Stable identifier for link-back detection (UIAO_NNN, adr-NNN, etc.)
            doc_id = fm.get("document_id") or fm.get("adr_id") or fm.get("uiao_id")

            cand = CandidateDoc(
                path=path,
                rel_path=rel_path,
                content_class=content_class,
                publish_to_site=publish,
                publish_intent_source=intent_source,
                publication_style=style,
                document_id=doc_id,
            )

            if publish:
                cand.expected_qmd_paths = expected_qmd_paths_for(path)

                # Detection 1: expected .qmd path appears in sidebar
                for candidate in cand.expected_qmd_paths:
                    if candidate in sidebar_qmds:
                        cand.matched_qmd_path = candidate
                        cand.in_sidebar = True
                        cand.matched_via = "expected-path"
                        break

                # Detection 2: a sidebar-listed .qmd references the canon path
                if not cand.in_sidebar:
                    for qmd_path, qmd_text in sidebar_content.items():
                        if rel_path in qmd_text:
                            cand.matched_qmd_path = qmd_path
                            cand.in_sidebar = True
                            cand.matched_via = "link-back-path"
                            break

                # Detection 3: a sidebar-listed .qmd references the document_id
                if not cand.in_sidebar and doc_id:
                    # Use word-boundary search to avoid UIAO_007 matching UIAO_0070
                    pat = re.compile(rf"\b{re.escape(doc_id)}\b")
                    for qmd_path, qmd_text in sidebar_content.items():
                        if pat.search(qmd_text):
                            cand.matched_qmd_path = qmd_path
                            cand.in_sidebar = True
                            cand.matched_via = "link-back-id"
                            break

                if not cand.in_sidebar:
                    cand.gap_reason = (
                        "no expected .qmd path, file path reference, or document_id found in any sidebar-listed .qmd"
                    )

            candidates.append(cand)

    return candidates


def render_summary_table(candidates: list[CandidateDoc]) -> str:
    """Per-class counts for stdout summary."""
    classes = [
        CLASS_UIAO_SPEC,
        CLASS_ADR,
        CLASS_MODERNIZATION,
        CLASS_SCHEMA,
        CLASS_OTHER,
    ]
    rows: list[tuple[str, int, int, int, int]] = []
    for cls in classes:
        items = [c for c in candidates if c.content_class == cls]
        publishable = [c for c in items if c.publish_to_site]
        published = [c for c in publishable if c.in_sidebar]
        gaps = [c for c in publishable if not c.in_sidebar]
        rows.append((cls, len(items), len(publishable), len(published), len(gaps)))

    out: list[str] = []
    out.append("")
    out.append(f"{'Class':<16} {'Total':>7} {'Publishable':>12} {'Published':>10} {'Gap':>6}")
    out.append(f"{'-' * 16} {'-' * 7} {'-' * 12} {'-' * 10} {'-' * 6}")
    for cls, total, pub, published, gap in rows:
        out.append(f"{cls:<16} {total:>7} {pub:>12} {published:>10} {gap:>6}")
    out.append(f"{'-' * 16} {'-' * 7} {'-' * 12} {'-' * 10} {'-' * 6}")
    out.append(
        f"{'TOTAL':<16} {sum(r[1] for r in rows):>7} {sum(r[2] for r in rows):>12} "
        f"{sum(r[3] for r in rows):>10} {sum(r[4] for r in rows):>6}"
    )
    out.append("")
    return "\n".join(out)


def render_markdown_report(candidates: list[CandidateDoc]) -> str:
    """Full markdown gap report committed to tools/publication-gaps/report.md."""
    lines: list[str] = []
    lines.append("# Publication Gap Report")
    lines.append("")
    lines.append(
        "Generated by `scripts/scan_publication_gaps.py` per ADR-068. "
        "Lists canon documents intended for the published site at "
        "<https://whalermike.github.io/uiao/> that have no corresponding "
        "`.qmd` entry in `docs/_quarto.yml`."
    )
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("```")
    lines.append(render_summary_table(candidates).strip())
    lines.append("```")
    lines.append("")

    classes_in_order = [
        (CLASS_UIAO_SPEC, "UIAO marquee specs"),
        (CLASS_ADR, "Architecture Decision Records"),
        (CLASS_MODERNIZATION, "Modernization-module docs"),
        (CLASS_SCHEMA, "Schemas"),
        (CLASS_OTHER, "Other"),
    ]
    for cls, label in classes_in_order:
        gaps = [c for c in candidates if c.content_class == cls and c.publish_to_site and not c.in_sidebar]
        if not gaps:
            continue
        lines.append(f"## Gaps — {label} ({len(gaps)})")
        lines.append("")
        lines.append("| Source | Intent source | Style | Expected .qmd candidates |")
        lines.append("|---|---|---|---|")
        for g in gaps:
            expected = "<br>".join(f"`{p}`" for p in g.expected_qmd_paths) or "_(none derived)_"
            style = g.publication_style or "—"
            lines.append(f"| [`{g.rel_path}`]({g.rel_path}) | {g.publish_intent_source} | {style} | {expected} |")
        lines.append("")

    lines.append("## Methodology")
    lines.append("")
    lines.append("1. Walk `src/uiao/canon/`, `src/uiao/modernization/`, and `src/uiao/schemas/`.")
    lines.append(
        "2. For each file, read frontmatter `publish_to_site` if present; otherwise "
        "apply ADR-068 path-pattern defaults."
    )
    lines.append(
        "3. For each file with `publish_to_site == true`, derive expected `.qmd` "
        "paths and check whether any of them appear in `docs/_quarto.yml`."
    )
    lines.append("4. Report files with `publish_to_site == true` and no matching `.qmd` as gaps.")
    lines.append("")
    lines.append("## How to close a gap")
    lines.append("")
    lines.append(
        "1. Decide the publication style (`narrative`, `include`, `reference`) and "
        "set it explicitly in the source document's frontmatter."
    )
    lines.append(
        "2. Author or generate the `.qmd` page at one of the expected paths "
        "(or any other path of your choice — then add it to `docs/_quarto.yml`)."
    )
    lines.append("3. Add the new `.qmd` to the sidebar in `docs/_quarto.yml`.")
    lines.append("4. Re-run this scanner to confirm the gap is closed.")
    lines.append("")
    lines.append("## How to suppress a false positive")
    lines.append("")
    lines.append(
        "If a document should NOT be published, add `publish_to_site: false` to its "
        "frontmatter with a brief justification in a comment. The scanner will then "
        "skip it on subsequent runs."
    )
    lines.append("")

    return "\n".join(lines)


def render_json_report(candidates: list[CandidateDoc]) -> str:
    """Machine-readable equivalent of the markdown report."""

    def to_dict(c: CandidateDoc) -> dict[str, Any]:
        d = asdict(c)
        d["path"] = str(c.path.relative_to(REPO_ROOT).as_posix())
        return d

    payload = {
        "schema_version": "1.0",
        "generated_by": "scripts/scan_publication_gaps.py",
        "adr_anchor": "ADR-068",
        "candidates": [to_dict(c) for c in candidates],
        "summary": {
            "total_scanned": len(candidates),
            "publishable": sum(1 for c in candidates if c.publish_to_site),
            "published": sum(1 for c in candidates if c.publish_to_site and c.in_sidebar),
            "gaps": sum(1 for c in candidates if c.publish_to_site and not c.in_sidebar),
        },
    }
    return json.dumps(payload, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if any gap is detected (otherwise always exit 0).",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Suppress stdout summary; only write the JSON and markdown report files.",
    )
    args = parser.parse_args()

    candidates = scan()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text(render_markdown_report(candidates), encoding="utf-8")
    REPORT_JSON.write_text(render_json_report(candidates), encoding="utf-8")

    gap_count = sum(1 for c in candidates if c.publish_to_site and not c.in_sidebar)

    if not args.json_only:
        print(render_summary_table(candidates))
        print(f"Full report:    {REPORT_MD.relative_to(REPO_ROOT)}")
        print(f"JSON report:    {REPORT_JSON.relative_to(REPO_ROOT)}")
        print(f"Gap count:      {gap_count}")
        if gap_count > 0 and not args.strict:
            print("Mode:           ADVISORY (use --strict to fail on gaps)")
        elif gap_count > 0:
            print("Mode:           STRICT — exiting 1")

    if args.strict and gap_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
