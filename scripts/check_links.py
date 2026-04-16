#!/usr/bin/env python3
# <!-- NEW (Proposed) -->
"""check_links.py — Validate internal Markdown links and anchors.

Purpose
-------
The ``repo-hygiene`` workflow runs this on every PR and on a weekly cron to
catch broken intra-repo links before they reach published canon. External
URL reachability is handled by the dedicated ``link-check`` workflow
(``.github/workflows/link-check.yml``); this script intentionally skips
``http(s)://`` targets to stay fast and network-free.

Scope
-----
* Scans all ``*.md`` files tracked in the repo (excluding ``.git`` and any
  directory starting with a dot).
* Extracts Markdown link targets of the form ``[text](target)``.
* Skips external links (``http://``, ``https://``), anchors-only
  (``#section``), and ``mailto:`` / ``tel:`` schemes.
* For each relative link, resolves it against the containing file and
  checks the target path exists on disk.

Behaviour
---------
Broken links are printed and contribute to a non-zero exit code. Files with
unreadable encodings are reported but do not fail the run.

Usage
-----
    python scripts/check_links.py

Exit codes
----------
0 — no broken internal links found.
1 — one or more broken internal links.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "tel:", "ftp://")


def is_external(target: str) -> bool:
    return target.startswith(EXTERNAL_PREFIXES)


def iter_markdown_files() -> list[Path]:
    return sorted(
        p for p in REPO_ROOT.rglob("*.md")
        if not any(part.startswith(".") for part in p.relative_to(REPO_ROOT).parts)
    )


def _strip_fenced_code(text: str) -> str:
    """Remove fenced code blocks so link syntax inside them is not checked."""
    return re.sub(r'```.*?```', '', text, flags=re.DOTALL)


def check_file(md_path: Path) -> list[tuple[Path, str]]:
    try:
        text = md_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        print(f"[check_links] warn: cannot read {md_path}: {exc}")
        return []

    text = _strip_fenced_code(text)

    broken: list[tuple[Path, str]] = []
    for match in LINK_RE.finditer(text):
        raw = match.group(1).strip()
        if not raw or raw.startswith("#") or is_external(raw):
            continue
        # Strip optional title and fragment.
        target = raw.split(" ", 1)[0].split("#", 1)[0]
        if not target:
            continue
        resolved = (md_path.parent / target).resolve()
        if not resolved.exists():
            broken.append((md_path, raw))
    return broken


def main() -> int:
    md_files = iter_markdown_files()
    print(f"[check_links] scanning {len(md_files)} markdown files")
    all_broken: list[tuple[Path, str]] = []
    for md in md_files:
        all_broken.extend(check_file(md))

    if all_broken:
        print(f"[check_links] FAIL — {len(all_broken)} broken internal link(s):")
        for md, link in all_broken:
            rel = md.relative_to(REPO_ROOT).as_posix()
            print(f"  {rel}: {link}")
        return 1

    print("[check_links] OK — no broken internal links")
    return 0


if __name__ == "__main__":
    sys.exit(main())
