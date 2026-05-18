#!/usr/bin/env python3
"""Audit relative markdown/qmd links across the docs tree.

Resolves every ``[text](relative-path)`` link in ``*.qmd``/``*.md`` files
under the canonical docs roots against the filesystem. Classifies failures
into three buckets so the wrong-depth (mechanically defensible) ones can be
swept in a single PR while the truly broken or .html-site-render-time ones
go to a follow-up.

Classification
--------------

- ``ok``  — link resolves to an existing file
- ``wrong-depth`` — link points outside the repo root (``..`` count exceeds
  the file's depth from the repo root). Almost always a manual ``..``-count
  mistake by the original author. Mechanically defensible to fix by reducing
  the count until the path resolves.
- ``site-html`` — link ends in ``.html`` and refers to a doc that exists in
  ``.qmd`` form at the same path with the extension swapped. These resolve
  at Quarto site-render time (not at raw-filesystem time) and are excluded
  from lychee by the ``^file://`` rule in ``.lycheeignore``. Not a problem.
- ``broken`` — link does not resolve and is neither ``wrong-depth`` nor
  ``site-html``. Needs author judgment.

Usage
-----

::

    python scripts/audit_relative_links.py             # scan + write report
    python scripts/audit_relative_links.py --dry-run   # just print summary
    python scripts/audit_relative_links.py --apply-wrong-depth-fixes
                                                       # rewrite ``..``-overcount
                                                       # links in place

The report lands at
``inbox/drafts/relative-link-audit-<today>.md`` per the Pass 8 convention
(``scripts/triage_aspirational_signals.py``).

Scope: ``docs/**/*.qmd``, ``docs/**/*.md``, ``src/uiao/canon/**/*.md``,
``src/uiao/modernization/**/*.md``.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# File patterns to scan
SCAN_GLOBS = [
    "docs/**/*.qmd",
    "docs/**/*.md",
    "src/uiao/canon/**/*.md",
    "src/uiao/modernization/**/*.md",
]

# Markdown link regex: [text](url) — captures the url
_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")

# Skip these URL prefixes — they are not filesystem-relative
_SKIP_PREFIXES = ("http://", "https://", "mailto:", "#", "{{<", "data:")


@dataclass
class LinkRow:
    source: Path
    line: int
    url: str
    bucket: str  # ok | wrong-depth | site-html | broken
    suggested_fix: str = ""  # for wrong-depth: the corrected ``..``-count


@dataclass
class Report:
    rows: list[LinkRow] = field(default_factory=list)

    def by_bucket(self) -> dict[str, list[LinkRow]]:
        out: dict[str, list[LinkRow]] = {}
        for row in self.rows:
            out.setdefault(row.bucket, []).append(row)
        return out


def _classify_link(source: Path, url: str) -> tuple[str, str]:
    """Return (bucket, suggested_fix). suggested_fix is empty unless wrong-depth."""
    url_no_anchor = url.split("#", 1)[0]
    if not url_no_anchor:
        return ("ok", "")

    src_dir = source.parent
    target = (src_dir / url_no_anchor).resolve()

    # Wrong-depth detection: target is outside the repo root entirely.
    try:
        target.relative_to(ROOT)
    except ValueError:
        # target falls outside the repo. Find the smallest number of ``..``
        # that still resolves inside the repo root and matches a real file.
        if not url_no_anchor.startswith(".."):
            return ("broken", "")
        parts = url_no_anchor.split("/")
        # Count leading ``..`` segments
        dotdots = 0
        for p in parts:
            if p == "..":
                dotdots += 1
            else:
                break
        # Try removing one ``..`` at a time
        tail = "/".join(parts[dotdots:])
        for reduced in range(dotdots - 1, 0, -1):
            candidate_url = "/".join([".."] * reduced + [tail])
            candidate_target = (src_dir / candidate_url).resolve()
            try:
                candidate_target.relative_to(ROOT)
            except ValueError:
                continue
            if candidate_target.exists():
                return ("wrong-depth", candidate_url)
        return ("broken", "")

    if target.exists():
        return ("ok", "")

    # .html target that has a .qmd sibling at the same path
    if url_no_anchor.endswith(".html"):
        qmd_target = target.with_suffix(".qmd")
        if qmd_target.exists():
            return ("site-html", "")

    return ("broken", "")


def scan() -> Report:
    report = Report()
    for pattern in SCAN_GLOBS:
        for fp in ROOT.glob(pattern):
            text = fp.read_text(encoding="utf-8", errors="ignore")
            for lineno, line in enumerate(text.splitlines(), 1):
                for m in _LINK_RE.finditer(line):
                    url = m.group(1).strip()
                    if url.startswith(_SKIP_PREFIXES):
                        continue
                    bucket, fix = _classify_link(fp, url)
                    report.rows.append(LinkRow(fp, lineno, url, bucket, fix))
    return report


def write_report(report: Report, out_path: Path) -> None:
    buckets = report.by_bucket()
    counts = Counter({b: len(rows) for b, rows in buckets.items()})

    lines: list[str] = []
    lines.append("# Relative-link audit report")
    lines.append("")
    lines.append(f"Generated by `scripts/audit_relative_links.py` on {date.today().isoformat()}.")
    lines.append("")
    lines.append(
        "Scans every `[text](relative-path)` link in `*.qmd`/`*.md` files under "
        "`docs/**`, `src/uiao/canon/**`, and `src/uiao/modernization/**`. "
        "Classifies failures so the mechanically-fixable bucket can be swept "
        "in one PR."
    )
    lines.append("")
    lines.append("## Bucket summary")
    lines.append("")
    lines.append("| Bucket | Links | Recommended action |")
    lines.append("|---|---:|---|")
    lines.append(f"| `ok` | {counts.get('ok', 0)} | no action — link resolves to an existing file |")
    lines.append(
        f"| `wrong-depth` | {counts.get('wrong-depth', 0)} | mechanical fix — reduce the `..` count to the suggested value below |"
    )
    lines.append(
        f"| `site-html` | {counts.get('site-html', 0)} | no action — Quarto site-render-time path; excluded by `^file://` in `.lycheeignore` |"
    )
    lines.append(f"| `broken` | {counts.get('broken', 0)} | manual author judgment — link target is missing |")
    lines.append("")

    for bucket_name, header in [
        ("wrong-depth", "wrong-depth (mechanically fixable)"),
        ("broken", "broken (manual judgment needed)"),
    ]:
        rows = buckets.get(bucket_name, [])
        if not rows:
            continue
        lines.append(f"## {header} ({len(rows)} links)")
        lines.append("")
        lines.append("| File | Line | URL | Suggested fix |")
        lines.append("|---|---:|---|---|")
        for r in sorted(rows, key=lambda x: (str(x.source), x.line)):
            rel = r.source.relative_to(ROOT)
            fix = f"`{r.suggested_fix}`" if r.suggested_fix else "—"
            lines.append(f"| `{rel}` | {r.line} | `{r.url}` | {fix} |")
        lines.append("")

    if counts.get("site-html"):
        lines.append(f"## site-html ({counts['site-html']} links — no action)")
        lines.append("")
        lines.append(
            "These point at `.html` paths whose corresponding `.qmd` source "
            "exists. Quarto resolves them at site-render time; lychee "
            "skips them via the `^file://` rule. Listed here for "
            "completeness only."
        )
        lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def apply_wrong_depth_fixes(report: Report) -> int:
    """Rewrite every wrong-depth link in place. Returns count of edits."""
    by_file: dict[Path, list[LinkRow]] = {}
    for row in report.rows:
        if row.bucket != "wrong-depth":
            continue
        by_file.setdefault(row.source, []).append(row)

    total = 0
    for fp, rows in by_file.items():
        text = fp.read_text(encoding="utf-8")
        for row in rows:
            # Replace only the exact link occurrence (URL inside parens after a ]).
            # Use a non-greedy regex anchored on the source URL string.
            pattern = re.compile(r"(\]\()" + re.escape(row.url) + r"(\))")
            new_text, n = pattern.subn(
                lambda m, fix=row.suggested_fix: m.group(1) + fix + m.group(2),
                text,
            )
            if n > 0:
                text = new_text
                total += n
        fp.write_text(text, encoding="utf-8")
    return total


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print summary; do not write the report or apply fixes",
    )
    parser.add_argument(
        "--apply-wrong-depth-fixes",
        action="store_true",
        help="Rewrite every wrong-depth link in place with the suggested fix",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=ROOT / "inbox" / "drafts" / f"relative-link-audit-{date.today().isoformat()}.md",
        help="Where to write the report (default: inbox/drafts/...)",
    )
    args = parser.parse_args()

    report = scan()
    counts = Counter(r.bucket for r in report.rows)
    print(f"Scanned {len(report.rows)} relative links.")
    print(f"  ok         : {counts.get('ok', 0)}")
    print(f"  wrong-depth: {counts.get('wrong-depth', 0)}")
    print(f"  site-html  : {counts.get('site-html', 0)}")
    print(f"  broken     : {counts.get('broken', 0)}")

    if args.dry_run:
        return 0

    write_report(report, args.report_path)
    print(f"Report written to {args.report_path.relative_to(ROOT)}")

    if args.apply_wrong_depth_fixes:
        n = apply_wrong_depth_fixes(report)
        print(f"Applied {n} wrong-depth fixes in place.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
