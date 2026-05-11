"""Re-triage aspirational-signal grep hits across docs/.

Re-runs the same grep the substrate-status §"Aspirational-content triage"
section ran on 2026-04-17, then classifies each match by file shape so
authors can act on the report rather than wade through 263 raw hits.

Classification:

- ``flagged-already`` — file already carries ``aspirational: true`` in its
  YAML frontmatter; the substrate banner fires; no further action.
- ``no-frontmatter`` — file has no YAML frontmatter block at all (raw
  Markdown, generated artifact, README, IMAGE-PROMPTS sidecar). Cannot
  carry the flag without a structural change; out of scope for mass
  flagging.
- ``draft-status`` — frontmatter sets ``status: Draft`` (or similar); the
  draft status is the canonical "this is in progress" signal already.
  Recommend flagging since the aspirational grep matched too.
- ``has-frontmatter-needs-review`` — frontmatter present, no flag,
  status not Draft; needs author judgment per the substrate-status §
  "Selective flagging preserves signal" rationale.
- ``session-log-or-inbox`` — file lives under session-logs/, inbox/, or a
  drafts/ folder; aspirational matches are expected and not actionable
  via mass flagging.

The script writes a refreshed report at
``inbox/drafts/aspirational-candidates-<today>.md`` with one row per
matched file, the hit count, the classification, and a one-line
recommended action.

Usage::

    python scripts/triage_aspirational_signals.py
    python scripts/triage_aspirational_signals.py --apply-flag-to draft-status

The optional ``--apply-flag-to`` flag adds ``aspirational: true`` to
files in the named classification bucket. Default is report-only.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCAN_ROOT = REPO_ROOT / "docs"

# Same phrase set the 2026-04-17 substrate-status triage used.
SIGNAL_PHRASES = [
    "not yet implemented",
    "not yet available",
    "coming soon",
    "TBD",
    "TODO",
    "placeholder",
    "aspirational",
    "proposed",
    "draft",
    "stub",
    "to be defined",
    "planned",
    "roadmap",
    "will be",
    "future",
    "intends to",
]

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(?P<body>.*?)\n---\s*\n", re.DOTALL)


def _grep_signal_files() -> dict[Path, int]:
    """Return {path: hit_count} for every file under SCAN_ROOT matching
    any of the signal phrases. Uses git grep for speed and to honor
    .gitignore (lychee/aspirational hits in build output don't matter)."""
    pattern = "|".join(re.escape(p) for p in SIGNAL_PHRASES)
    cmd = ["git", "grep", "-EIic", pattern, "--", "docs/"]
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, check=False)
    out: dict[Path, int] = {}
    for line in result.stdout.splitlines():
        if ":" not in line:
            continue
        rel, count_str = line.rsplit(":", 1)
        try:
            count = int(count_str)
        except ValueError:
            continue
        if count == 0:
            continue
        out[REPO_ROOT / rel] = count
    return out


def _classify(path: Path) -> tuple[str, str]:
    """Return (bucket, recommended_action) for one matched file.

    The buckets are stable strings that ``--apply-flag-to`` keys on.
    """
    rel = path.relative_to(REPO_ROOT).as_posix()

    # session-logs / inbox / drafts: aspirational hits are expected.
    if "/session-logs/" in rel or rel.startswith("inbox/") or "/drafts/" in rel:
        return "session-log-or-inbox", "no action — file is a scratch / log surface"

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return "unreadable", f"skip — could not read {rel}"

    fm_match = _FRONTMATTER_RE.match(text)
    if fm_match is None:
        # Not a frontmatter-bearing doc.
        return "no-frontmatter", "no action — file has no YAML frontmatter to flag"

    fm_body = fm_match.group("body")

    # Flagged already?
    if re.search(r"^aspirational:\s*true\b", fm_body, re.MULTILINE):
        return "flagged-already", "no action — aspirational: true already present"

    # Status: Draft (case-insensitive value)?
    status_match = re.search(r"^status:\s*([A-Za-z]+)", fm_body, re.MULTILINE)
    if status_match and status_match.group(1).lower() in {"draft", "proposed", "stub"}:
        return (
            "draft-status",
            "recommend flagging — frontmatter declares draft / proposed / stub status",
        )

    return (
        "has-frontmatter-needs-review",
        "needs author judgment — frontmatter present, no flag, not draft status",
    )


def _apply_flag(path: Path) -> bool:
    """Add ``aspirational: true`` to the file's YAML frontmatter (immediately
    before the closing ``---``). Returns True if the file was modified.
    Idempotent: refuses to add a duplicate flag."""
    text = path.read_text(encoding="utf-8")
    fm_match = _FRONTMATTER_RE.match(text)
    if fm_match is None:
        return False
    fm_body = fm_match.group("body")
    if re.search(r"^aspirational:\s*true\b", fm_body, re.MULTILINE):
        return False
    new_fm_body = fm_body.rstrip() + "\naspirational: true\n"
    new_text = text.replace(f"---\n{fm_body}\n---\n", f"---\n{new_fm_body}---\n", 1)
    if new_text == text:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


def _write_report(classified: list[tuple[Path, int, str, str]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    bucket_counts: dict[str, int] = {}
    for _path, _count, bucket, _action in classified:
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1

    lines: list[str] = []
    lines.append("# Aspirational-signal triage report (refreshed)")
    lines.append("")
    lines.append(f"Generated by `scripts/triage_aspirational_signals.py` on {date.today().isoformat()}.")
    lines.append("")
    lines.append(
        "Refreshes the 2026-04-17 substrate-status triage with current-tree counts and per-file classification."
    )
    lines.append("")
    lines.append("## Bucket summary")
    lines.append("")
    lines.append("| Bucket | Files | Recommended action |")
    lines.append("|---|---:|---|")
    for bucket in sorted(bucket_counts):
        action_hint = {
            "flagged-already": "no action",
            "no-frontmatter": "no action (structural)",
            "session-log-or-inbox": "no action (scratch surface)",
            "draft-status": "auto-flag candidate",
            "has-frontmatter-needs-review": "manual author judgment",
            "unreadable": "investigate",
        }.get(bucket, "—")
        lines.append(f"| `{bucket}` | {bucket_counts[bucket]} | {action_hint} |")
    lines.append("")

    for bucket in sorted(bucket_counts):
        lines.append(f"## {bucket} ({bucket_counts[bucket]} files)")
        lines.append("")
        lines.append("| Hits | Path | Action |")
        lines.append("|---:|---|---|")
        for path, count, b, action in sorted(classified, key=lambda x: (-x[1], str(x[0]))):
            if b != bucket:
                continue
            lines.append(f"| {count} | `{path.relative_to(REPO_ROOT).as_posix()}` | {action} |")
        lines.append("")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument(
        "--apply-flag-to",
        choices=["draft-status"],
        default=None,
        help="Bucket whose files should have aspirational: true added to frontmatter. Idempotent.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "inbox" / "drafts" / f"aspirational-candidates-{date.today().isoformat()}.md",
        help="Path to write the refreshed report (default: inbox/drafts/aspirational-candidates-<today>.md).",
    )
    args = parser.parse_args(argv)

    files = _grep_signal_files()
    classified = [(path, count, *_classify(path)) for path, count in files.items()]

    if args.apply_flag_to is not None:
        modified = 0
        for path, _count, bucket, _action in classified:
            if bucket == args.apply_flag_to and _apply_flag(path):
                modified += 1
        print(f"applied aspirational: true to {modified} files in bucket {args.apply_flag_to!r}")
        # Re-classify after mutation so the report reflects the new state.
        classified = [(path, count, *_classify(path)) for path, count in files.items()]

    _write_report(classified, args.output)
    print(f"wrote triage report: {args.output.relative_to(REPO_ROOT).as_posix()}")
    print(f"covered {len(classified)} files with {sum(c for _p, c, _b, _a in classified)} total hits")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
