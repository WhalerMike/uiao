#!/usr/bin/env python3
"""Block customer-facing .qmd pages with stub or drafting-prose defects.

Sibling to scan_publication_gaps.py — that scanner detects canon→site
*gaps* (publishable canon with no .qmd). This scanner detects content
*quality* defects already on the published surface:

  Gate A — Reserved-with-TODO stub
    Frontmatter declares status: reserved AND the body still carries a
    "Scaffold — awaiting authored content" callout or a literal
    "TODO — Author" placeholder. The pipeline currently ships these to
    the customer surface verbatim (~35 reserved adapters render literal
    "TODO — Author an overview of …" to readers).

  Gate B — LLM-drafting prose
    Body contains high-signal phrases that almost only occur in raw
    LLM drafting (e.g. "Let me reflect it back", "You're identifying",
    "Before I draft", "Let me actually browse"). The AD→Entra
    migration-problem whitepaper currently has both phrases on lines
    31 and 43.

Outputs:
  - stdout: human-readable summary
  - tools/publication-quality/report.md
  - tools/publication-quality/report.json

Exit codes:
  0  advisory mode (default), or strict mode with no defects
  1  --strict and any defect detected

Usage:
  python scripts/scan_publication_quality.py
  python scripts/scan_publication_quality.py --strict
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
SCAN_ROOT = REPO_ROOT / "docs"
REPORT_DIR = REPO_ROOT / "tools" / "publication-quality"
REPORT_MD = REPORT_DIR / "report.md"
REPORT_JSON = REPORT_DIR / "report.json"

FM_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", re.DOTALL)

# Gate A — reserved-with-TODO stub. The Scaffold callout and the
# "TODO — Author" placeholder both correlate strongly with unauthored
# stubs; either is sufficient evidence when status==reserved.
STUB_BODY_MARKERS: tuple[str, ...] = (
    "Scaffold — awaiting authored content",
    "Scaffold -- awaiting authored content",
    "TODO — Author",
    "TODO -- Author",
)

# Gate B — LLM-drafting prose. Phrases chosen to be vanishingly rare in
# legitimate federal-IT customer prose. Each match alone is sufficient.
# The pandoc-escaped variants (You\'re, We\'re) match the docx-rendered
# form seen in real leaked drafts.
DRAFTING_PROSE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"Let me reflect it back", re.IGNORECASE),
    re.compile(r"You\\?'re identifying", re.IGNORECASE),
    re.compile(r"Before I draft", re.IGNORECASE),
    re.compile(r"Let me actually browse", re.IGNORECASE),
    re.compile(r"Should I write the diagrams", re.IGNORECASE),
    re.compile(r"two quick questions", re.IGNORECASE),
)


@dataclass
class QualityFinding:
    """One published .qmd flagged by one or both gates."""

    path: str
    status: str | None
    gate_a_stub: bool = False
    gate_a_evidence: list[str] = field(default_factory=list)
    gate_b_drafting: bool = False
    gate_b_evidence: list[tuple[int, str]] = field(default_factory=list)

    @property
    def is_defect(self) -> bool:
        return self.gate_a_stub or self.gate_b_drafting


# Frontmatter values that mean "do not publish this page to the site".
# YAML's safe_load already yields a real bool for `false`; the string forms
# cover hand-written variants (`"false"`, `no`, `off`).
_UNPUBLISHED_VALUES: frozenset[str] = frozenset({"false", "no", "off", "0"})


def _is_unpublished(fm: dict[str, Any]) -> bool:
    """True if frontmatter sets publish_to_site to a false-y value."""
    val = fm.get("publish_to_site")
    if isinstance(val, bool):
        return val is False
    if isinstance(val, str):
        return val.strip().lower() in _UNPUBLISHED_VALUES
    return False


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str, int]:
    """Return (frontmatter_dict, body_text, body_line_offset).

    body_line_offset is the number of lines consumed by frontmatter, so
    file_line = body_line + body_line_offset.
    """
    m = FM_PATTERN.match(text)
    if not m:
        return {}, text, 0
    try:
        loaded = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return {}, text, 0
    body = text[m.end() :]
    body_line_offset = text.count("\n", 0, m.end())
    return (loaded or {}), body, body_line_offset


def evaluate(path: pathlib.Path) -> QualityFinding:
    """Apply both gates to a single .qmd file."""
    rel = path.relative_to(REPO_ROOT).as_posix()
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return QualityFinding(path=rel, status=None)

    fm, body, body_offset = parse_frontmatter(text)
    status = fm.get("status")
    status_str = str(status) if status is not None else None

    finding = QualityFinding(path=rel, status=status_str)

    # Off-surface pages are out of scope for both gates. A page declared
    # `publish_to_site: false` is pruned before the site render
    # (scripts/prune_unpublished_qmd.py), so its stub/drafting content never
    # reaches a customer — flagging it here would block --strict promotion
    # for content that does not publish. This makes the remediation the
    # report advertises ("add publish_to_site: false") actually clear a
    # finding. See issue #639.
    if _is_unpublished(fm):
        return finding

    # Gate A: status: reserved AND a stub marker in body.
    if status_str and status_str.lower() == "reserved":
        evidence = [m for m in STUB_BODY_MARKERS if m in body]
        if evidence:
            finding.gate_a_stub = True
            finding.gate_a_evidence = evidence

    # Gate B: drafting-prose pattern anywhere in body. Record line + excerpt.
    for pattern in DRAFTING_PROSE_PATTERNS:
        for m in pattern.finditer(body):
            line_no = body.count("\n", 0, m.start()) + 1 + body_offset
            start = max(0, m.start() - 30)
            end = min(len(body), m.end() + 60)
            excerpt = body[start:end].replace("\n", " ").strip()
            finding.gate_b_drafting = True
            finding.gate_b_evidence.append((line_no, excerpt))
            break  # one excerpt per pattern is enough

    return finding


def scan() -> list[QualityFinding]:
    """Evaluate every .qmd under docs/."""
    findings: list[QualityFinding] = []
    if not SCAN_ROOT.exists():
        return findings
    for path in sorted(SCAN_ROOT.rglob("*.qmd")):
        findings.append(evaluate(path))
    return findings


def render_summary(findings: list[QualityFinding]) -> str:
    defects = [f for f in findings if f.is_defect]
    gate_a = sum(1 for f in defects if f.gate_a_stub)
    gate_b = sum(1 for f in defects if f.gate_b_drafting)
    out: list[str] = []
    out.append("")
    out.append(f"Scanned:        {len(findings)} .qmd files under docs/")
    out.append(f"Defects:        {len(defects)}")
    out.append(f"  Gate A (reserved+stub):    {gate_a}")
    out.append(f"  Gate B (LLM drafting):     {gate_b}")
    out.append("")
    return "\n".join(out)


def render_markdown_report(findings: list[QualityFinding]) -> str:
    defects = [f for f in findings if f.is_defect]
    lines: list[str] = []
    lines.append("# Publication Quality Report")
    lines.append("")
    lines.append(
        "Generated by `scripts/scan_publication_quality.py`. "
        "Flags published `.qmd` pages with stub content or LLM-drafting prose."
    )
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("```")
    lines.append(render_summary(findings).strip())
    lines.append("```")
    lines.append("")

    gate_a = [f for f in defects if f.gate_a_stub]
    if gate_a:
        lines.append(f"## Gate A — Reserved-with-stub ({len(gate_a)})")
        lines.append("")
        lines.append(
            "These pages declare `status: reserved` in frontmatter and still carry "
            "scaffold/TODO placeholders in their body. They render literal "
            "`TODO — Author …` text to customer readers and should either be authored "
            "or have `publish_to_site: false` added until ready."
        )
        lines.append("")
        lines.append("| Source | Status | Evidence |")
        lines.append("|---|---|---|")
        for f in gate_a:
            evidence = "<br>".join(f"`{e}`" for e in f.gate_a_evidence)
            lines.append(f"| [`{f.path}`]({f.path}) | {f.status} | {evidence} |")
        lines.append("")

    gate_b = [f for f in defects if f.gate_b_drafting]
    if gate_b:
        lines.append(f"## Gate B — LLM-drafting prose ({len(gate_b)})")
        lines.append("")
        lines.append(
            "These pages contain phrases that almost only occur in raw LLM "
            'drafting output ("Let me reflect it back", "You\'re identifying", etc.). '
            "Treat as content that escaped from a scratchpad — review and rewrite."
        )
        lines.append("")
        lines.append("| Source | Line | Excerpt |")
        lines.append("|---|---|---|")
        for f in gate_b:
            for line_no, excerpt in f.gate_b_evidence:
                safe = excerpt.replace("|", "\\|")
                lines.append(f"| [`{f.path}`]({f.path}) | {line_no} | `{safe}` |")
        lines.append("")

    lines.append("## How to clear a finding")
    lines.append("")
    lines.append(
        "- **Gate A:** either author the stub content (replace every `_TODO — …_` "
        "block with real material), or add `publish_to_site: false` to the "
        "frontmatter until it is ready."
    )
    lines.append(
        "- **Gate B:** rewrite the offending passage in declarative, third-person "
        "customer-doc voice. The phrases this gate detects are conversational "
        "drafting tone that should never reach a published page."
    )
    lines.append("")
    return "\n".join(lines)


def render_json_report(findings: list[QualityFinding]) -> str:
    payload = {
        "schema_version": "1.0",
        "generated_by": "scripts/scan_publication_quality.py",
        "findings": [asdict(f) for f in findings if f.is_defect],
        "summary": {
            "scanned": len(findings),
            "defects": sum(1 for f in findings if f.is_defect),
            "gate_a_reserved_stub": sum(1 for f in findings if f.gate_a_stub),
            "gate_b_drafting_prose": sum(1 for f in findings if f.gate_b_drafting),
        },
    }
    return json.dumps(payload, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if any defect is detected. In strict mode the scanner is "
        "read-only by default; pass --write-reports to override.",
    )
    parser.add_argument(
        "--write-reports",
        action="store_true",
        help="Force writing tools/publication-quality/report.{md,json} even in strict mode.",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Suppress stdout summary; only write the JSON and markdown reports.",
    )
    args = parser.parse_args()

    findings = scan()
    defect_count = sum(1 for f in findings if f.is_defect)

    write_reports = args.write_reports or not args.strict
    if write_reports:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        REPORT_MD.write_text(render_markdown_report(findings), encoding="utf-8")
        REPORT_JSON.write_text(render_json_report(findings), encoding="utf-8")

    if not args.json_only:
        print(render_summary(findings))
        if write_reports:
            print(f"Full report:    {REPORT_MD.relative_to(REPO_ROOT)}")
            print(f"JSON report:    {REPORT_JSON.relative_to(REPO_ROOT)}")
        print(f"Defect count:   {defect_count}")
        if defect_count > 0 and not args.strict:
            print("Mode:           ADVISORY (use --strict to fail on defects)")
        elif defect_count > 0:
            print("Mode:           STRICT — exiting 1")

    if args.strict and defect_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
