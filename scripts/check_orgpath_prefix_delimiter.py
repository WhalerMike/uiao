#!/usr/bin/env python3
"""Guard OrgPath prefix expressions against the missing-trailing-delimiter bug.

Under the Hybrid-C+Path model (ADR-127), the derived canonical OrgPath on
``extensionAttribute15`` (and the ``OrgPath`` ARM tag) terminates EVERY
segment — including the last — with ``|``. A subtree prefix used with Entra's
``-startsWith`` or Azure Policy's ``like`` must therefore end in ``|``
(optionally followed by the single ``like`` wildcard ``*``); otherwise the
prefix ``Division=East`` silently also matches ``Division=Eastern`` and
``Division=Easton``. The rule *looks* correct in review — that is exactly the
failure mode this guard exists for.

What counts as an OrgPath prefix: a quoted string of ``Facet=Value`` segments
(``Region=NCR|Department=IT``). Legacy Model A/B path styles (``ORG-FIN``,
``/Root/Finance/``, ``CORP/US/EAST``) contain no ``=`` segments and are out of
scope by construction — grandfathered narrative content does not trip the gate.

Scope: policy definitions, dynamic-group-rule files, canon data, examples, and
published docs. Non-canon scratch surfaces (``inbox/``, ``downloads/``,
``session-logs/``, ``models/``, build output) are excluded, matching the other
repo guards. To exempt a single line (e.g., a doc deliberately showing the
broken form), append the inline marker ``orgpath-prefix-allow`` to it.

Run locally:  python scripts/check_orgpath_prefix_delimiter.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ALLOW_MARKER = "orgpath-prefix-allow"

# Files that may carry -startsWith / like OrgPath prefix expressions.
SCAN_GLOBS: list[str] = [
    "src/uiao/canon/data/**/*.yaml",
    "src/uiao/canon/data/**/*.yml",
    "src/uiao/canon/**/*.md",
    "src/uiao/schemas/**/*.json",
    "docs/**/*.qmd",
    "docs/**/*.md",
    "examples/**/*",
    "deploy/**/*.json",
    "deploy/**/*.bicep",
    "registry/**/*.json",
    "tools/**/*.ps1",
    "tools/**/*.psm1",
    "tests/fixtures/**/*.json",
]

EXCLUDE_SEGMENTS = (
    "/inbox/",
    "/downloads/",
    "/session-logs/",
    "/TedTalk/",
    "/models/",
    "/out/",
    "/output/",
    "/node_modules/",
    "/.venv/",
    "/images/",
)

SCANNABLE_SUFFIXES = {
    ".yaml",
    ".yml",
    ".json",
    ".qmd",
    ".md",
    ".ps1",
    ".psm1",
    ".bicep",
    ".kql",
    ".txt",
    ".sh",
}

# A prefix-match operator followed by a quoted value:
#   -startsWith "…"      (Entra dynamic group rules)
#   startswith "…"       (Kusto / Azure Resource Graph)
#   "like": "…"          (Azure Policy condition JSON)
#   like: "…"  / -like "…"  (YAML rule files, PowerShell)
#   op: -startsWith, value: "…"  (canon predicate YAML, UIAO_152/UIAO_153)
_QUOTED = r"""["']([^"']+)["']"""
PREFIX_EXPR_RE = re.compile(
    rf"""(?:
        -startsWith \s* ,? \s* value: \s* {_QUOTED}  # op: -startsWith, value: "…"
        |
        -?startsWith \s* [,(]? \s* {_QUOTED}      # -startsWith "…" / startswith("…")
        |
        ["']?like["']? \s* [:=]? \s* {_QUOTED}    # "like": "…" / like: "…" / -like "…"
    )""",
    re.IGNORECASE | re.VERBOSE,
)

# A hybrid OrgPath prefix: one or more Facet=Value segments. Values may not
# contain the delimiter or '='; the final segment may be delimiter-terminated.
ORGPATH_PREFIX_RE = re.compile(r"^(?:[A-Za-z][A-Za-z0-9]*=[^|=]+\|)*[A-Za-z][A-Za-z0-9]*=[^|=]*\|?$")
DELIMITER = "|"


def is_orgpath_prefix(value: str) -> bool:
    """True when ``value`` is a Facet=Value-style OrgPath prefix expression.

    A single trailing ``*`` (the Azure Policy ``like`` wildcard) is
    stripped before matching, so both ``…|*`` and the buggy ``…IT*``
    forms are classified in scope.
    """
    if value.endswith("*"):
        value = value[:-1]
    return "=" in value and bool(ORGPATH_PREFIX_RE.match(value))


def is_terminated(value: str) -> bool:
    """True when the prefix carries its trailing delimiter.

    Azure Policy ``like`` values may end with the single ``*`` wildcard;
    the character before it must still be the delimiter.
    """
    if value.endswith("*"):
        value = value[:-1]
    return value.endswith(DELIMITER)


def scan_text(text: str, rel: str) -> list[str]:
    findings: list[str] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if ALLOW_MARKER in line:
            continue
        for match in PREFIX_EXPR_RE.finditer(line):
            value = next((g for g in match.groups() if g), None)
            if not value or not is_orgpath_prefix(value):
                continue
            if not is_terminated(value):
                findings.append(
                    f"{rel}:{lineno}: OrgPath prefix '{value}' is missing the trailing "
                    f"'{DELIMITER}' — 'Division=East' also matches 'Division=Eastern'. "
                    f"Terminate the prefix (Get-OrgPathPrefix) per ADR-127."
                )
    return findings


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def iter_scan_files(root: Path) -> list[Path]:
    seen: set[Path] = set()
    for pattern in SCAN_GLOBS:
        for path in root.glob(pattern):
            if not path.is_file():
                continue
            posix = "/" + path.relative_to(root).as_posix()
            if any(seg in posix + "/" for seg in EXCLUDE_SEGMENTS):
                continue
            if path.suffix.lower() not in SCANNABLE_SUFFIXES:
                continue
            seen.add(path)
    return sorted(seen)


def main() -> int:
    root = repo_root()
    files = iter_scan_files(root)
    findings: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        findings.extend(scan_text(text, str(path.relative_to(root))))

    if findings:
        print(f"OrgPath prefix guard FAILED — {len(findings)} unterminated prefix(es):\n")
        for finding in findings:
            print(f"  {finding}")
        return 1

    print(
        f"OrgPath prefix guard OK — scanned {len(files)} files, every -startsWith/like OrgPath prefix carries its trailing '{DELIMITER}'."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
