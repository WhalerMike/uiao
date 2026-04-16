#!/usr/bin/env python3
# =============================================================================
# canon_triage.py
# READ-ONLY analyzer for Phase D Stage 4, Batch 5.1.5
# -----------------------------------------------------------------------------
# Consumes a metadata_validator JSON report and the schema, groups failures by
# pattern, and emits a markdown triage report. Does not modify any canon files.
#
# Usage:
#     python canon_triage.py <validator-report.json> <schema.json> <repo-root> <out.md>
# =============================================================================
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_findings(report: dict) -> list[dict]:
    """Be defensive — the validator has shipped a couple of report shapes."""
    for key in ("findings", "issues", "results", "errors"):
        if key in report and isinstance(report[key], list):
            return report[key]
    return []


def normalize(f: dict) -> tuple[str, str, str]:
    file_ = f.get("file") or f.get("path") or "?"
    issue = f.get("detail") or f.get("issue") or f.get("message") or str(f)
    severity = f.get("severity") or "?"
    return file_, issue, severity


def find_good_frontmatter(repo_root: Path, offending: set[str]) -> Path | None:
    """Find a canon .md that is NOT flagged — use it as a template exemplar."""
    canon = repo_root / "canon"
    if not canon.exists():
        return None
    offending_norm = {p.replace("\\", "/") for p in offending}
    for p in sorted(canon.rglob("*.md")):
        rel = p.relative_to(repo_root).as_posix()
        # Check both "canon/foo.md" and just "foo.md" styles
        rel_short = p.relative_to(canon).as_posix()
        if rel in offending_norm or rel_short in offending_norm:
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        if text.startswith("---"):
            return p
    return None


def extract_frontmatter(md_path: Path) -> str:
    text = md_path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    if end < 0:
        return text[:1000]
    return text[: end + 4]


def main() -> int:
    if len(sys.argv) != 5:
        print(__doc__)
        return 2
    report_path = Path(sys.argv[1])
    schema_path = Path(sys.argv[2])
    repo_root = Path(sys.argv[3])
    out_path = Path(sys.argv[4])

    report = load_json(report_path)
    schema = load_json(schema_path)
    findings = collect_findings(report)

    by_file: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for f in findings:
        file_, issue, severity = normalize(f)
        by_file[file_].append((severity, issue))

    # Group offending files by the set of issues they exhibit
    pattern_to_files: dict[tuple[str, ...], list[str]] = defaultdict(list)
    for file_, rows in by_file.items():
        key = tuple(sorted({issue for _, issue in rows}))
        pattern_to_files[key].append(file_)

    required = schema.get("required") or []
    properties = schema.get("properties") or {}

    good = find_good_frontmatter(repo_root, set(by_file.keys()))

    lines: list[str] = []
    lines.append("# Canon Backfill Triage — Batch 5.1.5")
    lines.append("")
    lines.append(
        "_Read-only analysis. No canon files were modified. Generated from a "
        "fresh `metadata_validator.py` run against `canon/` using the renamed "
        "`schemas/metadata-schema.json`._"
    )
    lines.append("")
    lines.append("## Headline numbers")
    lines.append("")
    lines.append(f"- **Files scanned:** {report.get('files_scanned', '?')}")
    lines.append(f"- **BLOCKING:** {report.get('blocking', 0)}")
    lines.append(f"- **WARNING:** {report.get('warning', 0)}")
    lines.append(f"- **INFO:** {report.get('info', 0)}")
    lines.append(f"- **Distinct offending files:** {len(by_file)}")
    lines.append(f"- **Distinct failure patterns:** {len(pattern_to_files)}")
    lines.append("")

    # Schema summary
    lines.append("## Schema contract")
    lines.append("")
    lines.append(
        f"Required fields: {', '.join(f'`{r}`' for r in required) if required else '_(none declared)_'}"
    )
    lines.append("")
    enum_fields = [(n, d["enum"]) for n, d in properties.items() if "enum" in d]
    if enum_fields:
        lines.append("Enumerated fields (valid values):")
        lines.append("")
        for name, values in enum_fields:
            shown = ", ".join(f"`{v}`" for v in values)
            lines.append(f"- `{name}`: {shown}")
        lines.append("")

    # Known-good exemplar
    lines.append("## Exemplar frontmatter")
    lines.append("")
    if good is not None:
        fm = extract_frontmatter(good)
        lines.append(f"Source: `{good.as_posix()}`")
        lines.append("")
        if fm:
            lines.append("```yaml")
            lines.append(fm.rstrip())
            lines.append("```")
        else:
            lines.append("_File has no `---` frontmatter block._")
    else:
        lines.append(
            "_No passing canon file found — every canon `.md` under "
            "`canon/` is in the offender list. Stubs must be derived from "
            "the schema alone._"
        )
    lines.append("")

    # Failure pattern buckets, biggest first
    lines.append("## Failure patterns (largest first)")
    lines.append("")
    sorted_patterns = sorted(
        pattern_to_files.items(), key=lambda kv: (-len(kv[1]), kv[0])
    )
    for idx, (issues, files) in enumerate(sorted_patterns, start=1):
        lines.append(f"### Pattern {idx}: {len(files)} file(s)")
        lines.append("")
        lines.append("Issues in this bucket:")
        lines.append("")
        for issue in issues:
            lines.append(f"- {issue}")
        lines.append("")
        lines.append("<details><summary>Files</summary>")
        lines.append("")
        for f in sorted(files):
            lines.append(f"- `{f}`")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    # Triage decisions the user now has to make
    lines.append("## Decisions required before backfill")
    lines.append("")
    lines.append(
        "1. **Scope of `canon/`.** The single biggest pattern is driven by "
        "`canon/specs/` — are those files meant to be canon, or were they "
        "copied in from an earlier architecture dump? If not canon, move "
        "them (to `docs/` or out to `uiao-docs`) and shrink the validator's "
        "target. If canon, they all need frontmatter."
    )
    lines.append("")
    lines.append(
        "2. **Status enum semantics.** Any file flagged `Invalid status: "
        "'CANONICAL'` or similar may just need `CANONICAL` added to the "
        "schema enum — or the file changed to use an existing value. Pick "
        "one: evolve the schema, or coerce the files."
    )
    lines.append("")
    lines.append(
        "3. **Encoding hygiene.** Mojibake sequences like `ΓÇô` in "
        "`classification` fields indicate a UTF-8 → cp1252 → UTF-8 round-trip "
        "somewhere upstream. Fix the source, not the symptom."
    )
    lines.append("")
    lines.append(
        "4. **Boundary violations in body text.** GCC-High references in a "
        "GCC-Moderate-only canon repo may be genuine policy statements (allowed) "
        "or accidental leaks (must be removed). These are per-file judgment calls."
    )
    lines.append("")
    lines.append(
        "5. **Branch protection ordering.** Do not flip `metadata-validator` "
        "to a required status check on `main` until BLOCKING count is zero. "
        "Alternative: enable as required + accept that `main` is red until "
        "backfill lands."
    )
    lines.append("")

    lines.append("## Proposed next batches")
    lines.append("")
    lines.append(
        "- **5.1.6 — scope decision.** One-line: is `canon/specs/` canon? "
        "Answer drives everything else."
    )
    lines.append(
        "- **5.1.7 — mechanical backfill.** Apply the agreed frontmatter stub "
        "to every file in Pattern 1, one file → verify → batch-apply the rest."
    )
    lines.append(
        "- **5.1.8 — judgment backfill.** Walk Patterns 2..N by hand, one "
        "commit per file so diffs review cleanly."
    )
    lines.append(
        "- **5.2 — branch protection.** Only after BLOCKING is zero, or with "
        "explicit acceptance of a red main."
    )
    lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote triage report: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
