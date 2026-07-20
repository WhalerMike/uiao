#!/usr/bin/env python3
"""Every customer-document figure carries alt text — presence gate.

Repo-review round 2 (2026-07-20) named figure alt-text as the one fully
manual drift surface: the status generator counts broken image refs but
never inspects alt text, so regressions were invisible to CI. Measured
at gate-creation time the debt was ZERO across 1,100 figure references
(the fig-alt-as-prompt program's discipline) — this gate pins it there.

Rules, per tracked ``docs/customer-documents/**/*.qmd``:

1. A markdown image ``![...](...)`` targeting a raster/vector file must
   have non-empty bracket alt text, or a non-empty ``fig-alt="..."``
   attribute on the same line.
2. ``fig-alt=""`` (empty/whitespace) is a violation anywhere.
3. An executable cell that declares ``#| fig-cap:`` must also declare
   ``#| fig-alt:`` (captions are not alt text).

Exit 0 when clean; exit 1 listing every violation as file:line.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOT = "docs/customer-documents"

IMAGE_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<target>[^)]+?\.(?:png|svg|jpe?g|gif|webp))(?:\s+\"[^\"]*\")?\)")
FIG_ALT_ATTR_RE = re.compile(r"fig-alt=\"(?P<value>[^\"]*)\"")
EMPTY_FIG_ALT_RE = re.compile(r"fig-alt=\"\s*\"")
CELL_OPT_CAP_RE = re.compile(r"^#\|\s*fig-cap\s*:")
CELL_OPT_ALT_RE = re.compile(r"^#\|\s*fig-alt\s*:")


def tracked_qmds() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "--", f"{SCAN_ROOT}/**/*.qmd", f"{SCAN_ROOT}/*.qmd"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [REPO_ROOT / line for line in out.stdout.splitlines() if line.strip()]


def check_file(path: Path) -> list[str]:
    violations: list[str] = []
    rel = path.relative_to(REPO_ROOT).as_posix()
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    in_cell = False
    cell_start = 0
    cell_has_cap = False
    cell_has_alt = False

    for lineno, line in enumerate(lines, start=1):
        if line.strip().startswith("```"):
            if in_cell:
                if cell_has_cap and not cell_has_alt:
                    violations.append(f"{rel}:{cell_start}: cell declares '#| fig-cap' without '#| fig-alt'")
                in_cell = False
            elif re.match(r"^```\{", line.strip()):
                in_cell = True
                cell_start = lineno
                cell_has_cap = False
                cell_has_alt = False
            continue

        if in_cell:
            if CELL_OPT_CAP_RE.match(line.strip()):
                cell_has_cap = True
            if CELL_OPT_ALT_RE.match(line.strip()):
                cell_has_alt = True
            continue

        if EMPTY_FIG_ALT_RE.search(line):
            violations.append(f'{rel}:{lineno}: empty fig-alt=""')

        for match in IMAGE_RE.finditer(line):
            if match.group("alt").strip():
                continue
            attr = FIG_ALT_ATTR_RE.search(line, match.end())
            if attr and attr.group("value").strip():
                continue
            violations.append(
                f"{rel}:{lineno}: image {match.group('target')!r} has no alt text (empty ![] and no same-line fig-alt)"
            )

    return violations


def main() -> int:
    files = tracked_qmds()
    all_violations: list[str] = []
    for path in files:
        all_violations.extend(check_file(path))

    if all_violations:
        print(f"FIGURE ALT-TEXT GATE: {len(all_violations)} violation(s) across {len(files)} files:")
        for v in all_violations:
            print(f"  {v}")
        print("\nEvery figure needs alt text: bracket text, a fig-alt attribute, or '#| fig-alt' in the cell.")
        return 1

    print(f"OK: all figure references in {len(files)} customer-document files carry alt text.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
