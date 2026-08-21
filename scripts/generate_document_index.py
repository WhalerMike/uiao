#!/usr/bin/env python3
"""Regenerate the per-document tables for customer-documents/document-index.qmd.

Walks ``docs/customer-documents/**`` and emits a Markdown file with
**Document Families** and **Pillar Taxonomy** tables, one row per
real file (or per directory, for the pillar taxonomy). The
document-index.qmd page includes the output via Quarto's
``{{< include >}}`` shortcode, so the visible inventory cannot drift
from the tree.

This is the document-index analogue of
``generate_customer_docs_status.py``. The two serve different
audiences — the status surface is for authors tracking authoring
depth and integrity, while this is the customer-facing "what's
in the corpus" index — but they share the same anti-drift posture:
regenerate from frontmatter on every PR, gate with CI.

Sections emitted
----------------
**Document Families** (functional groupings):
  - Executive Briefs, Architecture Series, Modernization Specs,
    Case Studies, Whitepapers, Platform → one row per non-index .qmd
    in the section root.
  - Adapter Specifications → one row per ``adapter-specs/<slug>/<slug>.qmd``
    paired with ``validation-suites/adapters/<slug>/<slug>.qmd``.
  - Executive Governance Series → one row per ``chNN-*/index.qmd``.

**Pillar Taxonomy** (modernization / compliance / substrate):
  - One row per immediate sub-directory; description from that
    sub-directory's index.qmd ``subtitle:`` frontmatter; status from
    ``status:`` frontmatter when present, otherwise inferred from
    whether the sub-directory has authored sibling content (more
    than just the nav stub).

CI / drift
----------
Output is committed; ``.github/workflows/document-index-status.yml``
re-runs the script on every PR touching ``docs/customer-documents/``
or the script itself and fails if the committed file diverges.

Usage
-----
::

    python scripts/generate_document_index.py \\
        --output docs/data/document-index-tables.md
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

from _console import use_utf8_stdout


REPO_ROOT = Path(__file__).resolve().parent.parent
CUSTOMER_DOCS = REPO_ROOT / "docs" / "customer-documents"
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "data" / "document-index-tables.md"

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(?P<body>.*?)\n---\s*\n", re.DOTALL)

# Line count below which a non-index .qmd is reported as "Stub" when no
# explicit `status:` is set in frontmatter. Matches the threshold in
# generate_customer_docs_status.py.
STUB_LINE_THRESHOLD = 40

# Frontmatter status values that mean "this is a nav surface, not an
# authored landing page." For pillar-taxonomy rows, when the section
# index.qmd carries one of these, we infer the row's real status by
# whether the directory contains authored sibling content. Tracked
# values cover the conventions we've observed across the corpus.
NAV_STUB_STATUSES = {"Stub", "Scaffold", "scaffold", "stub"}


@dataclass
class FileMeta:
    """Frontmatter-derived metadata for one .qmd."""

    path: Path  # relative to REPO_ROOT
    title: str
    status: str
    audience: str
    subtitle: str
    lines: int


def _parse_frontmatter(text: str) -> dict | None:
    """Return parsed YAML frontmatter as a dict, or None if absent/malformed.

    Malformed YAML is treated as "no frontmatter" — the
    metadata-validator CI gate is the authority on that; this script
    just reports what it can read.
    """
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return None
    try:
        loaded = yaml.safe_load(m.group("body"))
    except yaml.YAMLError:
        return None
    if not isinstance(loaded, dict):
        return None
    return loaded


def _read_file_meta(path: Path) -> FileMeta:
    """Extract title / status / audience / subtitle from a .qmd's frontmatter.

    Missing fields fall back to derivable defaults: title from
    filename stem, status from line-count heuristic, audience and
    subtitle to empty strings.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.count("\n") + (0 if text.endswith("\n") or not text else 1)
    fm = _parse_frontmatter(text) or {}

    title = str(fm.get("title", path.stem))
    subtitle = str(fm.get("subtitle", "") or "")

    # Status: explicit `status:` wins. Otherwise heuristic by line
    # count, matching the generate_customer_docs_status.py thresholds.
    explicit_status = fm.get("status")
    if explicit_status:
        status = str(explicit_status)
    elif lines <= STUB_LINE_THRESHOLD:
        status = "Stub"
    else:
        status = "Active"

    # Audience can be a YAML list or a comma-separated string. Normalize
    # to a comma+space-separated string for the customer-facing table.
    audience_raw = fm.get("audience", "")
    audience = ", ".join(str(a) for a in audience_raw) if isinstance(audience_raw, list) else str(audience_raw)

    return FileMeta(
        path=path.relative_to(REPO_ROOT),
        title=title,
        status=status,
        audience=audience,
        subtitle=subtitle,
        lines=lines,
    )


def _site_path(rel_path: Path) -> str:
    """Translate a repo-relative .qmd path into the site-relative .html
    URL used inside the document-index. Document-index.qmd is at
    ``docs/customer-documents/document-index.qmd``, so links are
    relative to that directory."""
    posix = rel_path.as_posix()
    # Strip the docs/customer-documents/ prefix — links are relative
    # to the document-index page itself.
    prefix = "docs/customer-documents/"
    if posix.startswith(prefix):
        posix = posix[len(prefix) :]
    return posix.replace(".qmd", ".html")


def _files_only(section: str) -> list[FileMeta]:
    """Return every non-index .qmd directly in the section root."""
    section_dir = CUSTOMER_DOCS / section
    if not section_dir.is_dir():
        return []
    out: list[FileMeta] = []
    for path in sorted(section_dir.glob("*.qmd")):
        if path.name == "index.qmd":
            continue
        out.append(_read_file_meta(path))
    return out


def _subdir_files(section: str) -> list[FileMeta]:
    """Return one entry per immediate sub-directory, using
    ``<subdir>/<subdir>.qmd`` as the canonical file (the
    modernization-specs convention)."""
    section_dir = CUSTOMER_DOCS / section
    if not section_dir.is_dir():
        return []
    out: list[FileMeta] = []
    for sub in sorted(p for p in section_dir.iterdir() if p.is_dir()):
        canonical = sub / f"{sub.name}.qmd"
        if canonical.is_file():
            out.append(_read_file_meta(canonical))
    return out


def _chapter_subdirs(section: str) -> list[FileMeta]:
    """Return one entry per ``chNN-*/index.qmd`` sub-directory."""
    section_dir = CUSTOMER_DOCS / section
    if not section_dir.is_dir():
        return []
    chapter_re = re.compile(r"^ch\d{2}-")
    out: list[FileMeta] = []
    for sub in sorted(p for p in section_dir.iterdir() if p.is_dir() and chapter_re.match(p.name)):
        index_qmd = sub / "index.qmd"
        if index_qmd.is_file():
            out.append(_read_file_meta(index_qmd))
    return out


def _adapter_paired() -> list[tuple[FileMeta, FileMeta | None]]:
    """For each ``adapter-specs/<slug>/<slug>.qmd``, pair with its
    matching ``validation-suites/adapters/<slug>/<slug>.qmd`` (or None
    if the validation suite is missing). Returns spec-first order."""
    specs_dir = CUSTOMER_DOCS / "adapter-specs"
    suites_dir = CUSTOMER_DOCS / "validation-suites" / "adapters"
    if not specs_dir.is_dir():
        return []
    pairs: list[tuple[FileMeta, FileMeta | None]] = []
    for sub in sorted(p for p in specs_dir.iterdir() if p.is_dir()):
        spec_path = sub / f"{sub.name}.qmd"
        if not spec_path.is_file():
            continue
        spec = _read_file_meta(spec_path)
        suite_path = suites_dir / sub.name / f"{sub.name}.qmd"
        suite = _read_file_meta(suite_path) if suite_path.is_file() else None
        pairs.append((spec, suite))
    return pairs


def _pillar_subdirs(pillar: str) -> list[tuple[Path, FileMeta | None, list[FileMeta]]]:
    """For a pillar root (e.g. ``modernization``), return each immediate
    sub-directory with its ``index.qmd`` metadata (if present) and the
    list of non-index .qmd metadata found anywhere beneath it. Lets
    the caller infer "is this sub-directory actually populated, or
    just a nav stub?"."""
    pillar_dir = CUSTOMER_DOCS / pillar
    if not pillar_dir.is_dir():
        return []
    out: list[tuple[Path, FileMeta | None, list[FileMeta]]] = []
    for sub in sorted(p for p in pillar_dir.iterdir() if p.is_dir()):
        # Skip pure-asset directories (images/, attachments/, etc.) that
        # have no .qmd descendants at all. They're not content
        # sub-categories; including them inflates the pillar tables with
        # noise like an "Images" row.
        if not any(sub.rglob("*.qmd")):
            continue
        index_qmd = sub / "index.qmd"
        index_meta = _read_file_meta(index_qmd) if index_qmd.is_file() else None
        children: list[FileMeta] = []
        for qmd in sorted(sub.rglob("*.qmd")):
            if qmd.name == "index.qmd":
                continue
            children.append(_read_file_meta(qmd))
        out.append((sub, index_meta, children))
    return out


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _row_link(meta: FileMeta) -> str:
    """Markdown link to a file's rendered page."""
    return f"[{meta.title}]({_site_path(meta.path)})"


def _files_table(label: str, items: list[FileMeta]) -> str:
    lines = [f"### {label}", ""]
    if not items:
        lines.append("_No files in this section._")
        lines.append("")
        return "\n".join(lines)
    lines.extend(
        [
            "| Title | Status | Audience |",
            "|-------|--------|----------|",
        ]
    )
    for m in items:
        lines.append(f"| {_row_link(m)} | {m.status or '—'} | {m.audience or '—'} |")
    lines.append("")
    return "\n".join(lines)


def _adapter_table(label: str, pairs: list[tuple[FileMeta, FileMeta | None]]) -> str:
    lines = [
        f"### {label}",
        "",
        "Each adapter has a paired specification and validation suite."
        " The spec describes the adapter's contract; the suite documents"
        " the validation evidence the adapter must produce.",
        "",
    ]
    if not pairs:
        lines.append("_No adapters registered._")
        lines.append("")
        return "\n".join(lines)
    lines.extend(
        [
            "| Adapter | Spec | Validation Suite |",
            "|---------|------|------------------|",
        ]
    )
    for spec, suite in pairs:
        suite_cell = f"[Suite]({_site_path(suite.path)})" if suite else "_(missing)_"
        # Adapter name = spec frontmatter title (without trailing "Adapter Spec" suffix if present).
        name = re.sub(r"\s+(Adapter Spec|Spec)$", "", spec.title).strip() or spec.path.stem
        lines.append(f"| {name} | [Spec]({_site_path(spec.path)}) | {suite_cell} |")
    lines.append("")
    return "\n".join(lines)


def _chapter_table(label: str, items: list[FileMeta]) -> str:
    lines = [f"### {label}", ""]
    if not items:
        lines.append("_No chapters in this series._")
        lines.append("")
        return "\n".join(lines)
    chapter_num_re = re.compile(r"ch(\d{2})-")
    lines.extend(
        [
            "| Chapter | Title | Status |",
            "|---------|-------|--------|",
        ]
    )
    for m in items:
        # Chapter number from the parent directory name (chNN-...).
        m2 = chapter_num_re.match(m.path.parent.name)
        ch = f"Ch {m2.group(1)}" if m2 else m.path.parent.name
        lines.append(f"| {ch} | {_row_link(m)} | {m.status or '—'} |")
    lines.append("")
    return "\n".join(lines)


def _pillar_status(index_meta: FileMeta | None, children: list[FileMeta]) -> str:
    """Compute a row-level status for a pillar sub-directory.

    Authored or Substantial sub-directories are reported as "Active"
    in the customer-facing index; nav-stubs with no authored children
    are reported as "Stub". This matches the user-perceived state and
    avoids surprising "Stub" rows on heavily-populated trees.
    """
    if index_meta and index_meta.status and index_meta.status not in NAV_STUB_STATUSES:
        return index_meta.status
    # Index is a nav stub (`Stub` / `scaffold` / etc.); defer to whether
    # the directory actually contains authored sibling content.
    substantive = [c for c in children if c.lines > STUB_LINE_THRESHOLD]
    return "Active" if substantive else "Stub"


def _pillar_description(index_meta: FileMeta | None) -> str:
    if not index_meta:
        return "_(no index)_"
    return index_meta.subtitle or "_(no description)_"


def _pillar_table(label: str, entries: list[tuple[Path, FileMeta | None, list[FileMeta]]]) -> str:
    lines = [f"### {label}", ""]
    if not entries:
        lines.append("_No sub-categories._")
        lines.append("")
        return "\n".join(lines)
    lines.extend(
        [
            "| Sub-Category | Description | Status |",
            "|--------------|-------------|--------|",
        ]
    )
    for sub, index_meta, children in entries:
        rel = sub.relative_to(CUSTOMER_DOCS)
        link = f"[{sub.name.replace('-', ' ').title()}]({rel.as_posix()}/index.html)"
        desc = _pillar_description(index_meta)
        status = _pillar_status(index_meta, children)
        lines.append(f"| {link} | {desc} | {status} |")
    lines.append("")
    return "\n".join(lines)


def render() -> str:
    out: list[str] = []
    out.append("<!-- GENERATED by scripts/generate_document_index.py — do not hand-edit. -->")
    out.append(
        "<!-- Regenerate: python scripts/generate_document_index.py --output docs/data/document-index-tables.md -->"
    )
    out.append("")
    out.append("## Document Families")
    out.append("")
    out.append(_files_table("Executive Briefs", _files_only("executive-briefs")))
    out.append(_files_table("Architecture Series", _files_only("architecture-series")))
    out.append(_adapter_table("Adapter Specifications", _adapter_paired()))
    out.append(_files_table("Modernization Specs (by domain)", _subdir_files("modernization-specs")))
    out.append(_files_table("Case Studies", _files_only("case-studies")))
    out.append(_files_table("Whitepapers", _files_only("whitepapers")))
    out.append(_chapter_table("Executive Governance Series", _chapter_subdirs("executive-governance-series")))
    out.append(_files_table("Platform", _files_only("platform")))
    out.append("")
    out.append("## Pillar Taxonomy")
    out.append("")
    out.append(_pillar_table("Modernization", _pillar_subdirs("modernization")))
    out.append(_pillar_table("Compliance", _pillar_subdirs("compliance")))
    out.append(_pillar_table("Substrate", _pillar_subdirs("substrate")))
    return "\n".join(out).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    use_utf8_stdout()
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Write output to this path (default: stdout). Conventional location: "
            f"{DEFAULT_OUTPUT.relative_to(REPO_ROOT)}"
        ),
    )
    args = parser.parse_args(argv)

    rendered = render()

    if args.output is None:
        sys.stdout.write(rendered)
    else:
        out_path = args.output.resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        # Force LF newlines so output is byte-identical between Windows
        # authoring and Linux CI (matches the convention adopted in
        # generate_customer_docs_status.py).
        out_path.write_bytes(rendered.encode("utf-8"))
        try:
            shown = out_path.relative_to(REPO_ROOT)
        except ValueError:
            shown = out_path
        print(f"wrote document-index tables to {shown}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
