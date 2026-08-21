#!/usr/bin/env python3
"""Guard the corpus against OrgPath examples the codebook does not license.

Two guards already stand between the corpus and ``codebook.yaml``, and both
leave the same hole. ``check_orgpath_prefix_delimiter.py`` validates prefix
*expressions* and excludes legacy path styles by construction, so a bare
``/Root/Finance/AccountsPayable`` in a paragraph is invisible to it.
``check_orgpath_slot_binding.py`` only fires on a line that names exactly one
``extensionAttributeN`` slot, so the same literal in a figure caption — with no
slot in sight — is invisible to it too. Neither scans ``.svg`` at all: the
prefix guard excludes ``/images/`` outright.

That hole is not theoretical. Four consecutive lint-driven passes over the
Model A backlog each closed the class the previous pass could see, and each
left a class it could not: a parallel spec across nine appendices, ten figures
asserting stored attribute values, twenty-nine narrative diagrams drawing the
retired composite path, and prose asserting composite tag values beside code
that already stamped facets. This guard closes both rules that were missing.

Two rules, over prose, data and figures alike:

1. **Composite-path literal** — a Model A/B path token anywhere on the line
   (``ORG-FIN-AP-EAST``, ``/Root/Finance``, ``CORP/US/EAST``, ``/COMM/MKT``),
   whether or not a slot is named. Canon group names (``ORG-NODE-*``,
   ``ORG-BRANCH-*`` per ADR-036/ADR-039) are *not* path literals and never
   trip the rule.
2. **Unlicensed facet value** — a derived-path segment (``Division=Payroll|``)
   or a quoted slot comparison (``extensionAttribute3 -eq "Payroll"``) whose
   value is absent from that facet's enumeration in the codebook. Typed and
   reserved facets are skipped; ``allow_empty`` facets accept the empty value.

The point of rule 2 is that the codebook is the SSOT for what a facet may
hold, and a document that invents a value reads exactly like one that does
not. Extending an enumeration is a governed PR; inventing one in a figure is
not.

Scope: canon, published docs, examples, deploy and registry data, and the
committed SVG figures. Non-canon scratch surfaces (``inbox/``, ``downloads/``,
``session-logs/``, ``models/``, build output) are excluded, matching the other
repo guards. To exempt a line that names the retired era in order to declare
it retired, append ``orgpath-codebook-allow`` — or either sibling marker,
``orgpath-slot-allow`` / ``orgpath-prefix-allow``, since a line already marked
as deliberate Model A content is deliberate for this guard too. For a whole
historical document, ``orgpath-codebook-allow-file`` anywhere in it.

Exit codes follow the check_orgpath_slot_binding.py precedent:

  0  advisory mode (default) — findings are printed, the gate stays green
  1  --strict and any finding remains

Run locally:  python scripts/check_orgpath_codebook_conformance.py
              python scripts/check_orgpath_codebook_conformance.py --strict
              python scripts/check_orgpath_codebook_conformance.py --strict --path src/uiao/canon
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

from _console import use_utf8_stdout

ALLOW_MARKERS = (
    "orgpath-codebook-allow",
    "orgpath-slot-allow",
    "orgpath-prefix-allow",
)
ALLOW_FILE_MARKER = "orgpath-codebook-allow-file"

CODEBOOK = Path("src/uiao/canon/data/orgpath/codebook.yaml")

SCAN_GLOBS: list[str] = [
    "src/uiao/canon/**/*.md",
    "src/uiao/canon/**/*.svg",
    "src/uiao/canon/data/**/*.yaml",
    "src/uiao/canon/data/**/*.yml",
    "src/uiao/schemas/**/*.json",
    "docs/**/*.qmd",
    "docs/**/*.md",
    "docs/**/*.svg",
    "examples/**/*",
    "deploy/**/*.json",
    "deploy/**/*.bicep",
    "registry/**/*.json",
    "tools/**/*.ps1",
    "tools/**/*.psm1",
]

EXCLUDE_PARTS = {
    "inbox",
    "downloads",
    "session-logs",
    "models",
    "out",
    "output",
    "node_modules",
    ".venv",
}

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
    ".svg",
}

# --- Rule 1: retired composite-path literals --------------------------------
#
# Model A packed the hierarchy into one hyphenated code; Model B into one
# slash-delimited path. Both were replaced by ADR-078 / ADR-127. The slash
# families are anchored on their literal roots rather than matched generically,
# so ordinary file paths in the same corpus are out of scope by construction.
#
# ORG-NODE-* and ORG-BRANCH-* are canon dynamic-group names (ADR-036/ADR-039),
# not path values, and are carved out by the negative lookahead.
COMPOSITE_PATH_RES: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bORG(?!-(?:NODE|BRANCH)\b)(?:-[A-Z]{2,8}){1,6}\b"),
    re.compile(r"(?<![A-Za-z0-9_])/Root(?:/[A-Za-z0-9_.-]+)*(?![A-Za-z0-9_])"),
    re.compile(r"(?<![A-Za-z0-9_])/COMM(?:/[A-Za-z0-9_-]+)+"),
    re.compile(r"\bCORP/[A-Z]{2}(?:/[A-Z][A-Za-z0-9_-]*)+"),
)

# --- Rule 2: facet values the codebook does not license ---------------------
#
# Two shapes carry a facet value: a segment of the derived path, and a
# comparison against the slot that holds the facet. Both are quoted or
# delimiter-terminated in practice, which is what keeps prose about the facet
# ("extensionAttribute1 = Region facet") out of scope — only an asserted value
# is a finding.
# The value may not contain whitespace — no codebook enumeration does — which
# stops a run-on match swallowing prose up to a later delimiter. The optional
# backslash absorbs the pipe-escaping that Pandoc tables require.
SEGMENT_RE = re.compile(r"\b([A-Z][A-Za-z0-9]*)=([^|=\"'`\s\\]+)\\?\|")
SLOT_VALUE_RE = re.compile(
    r"""extensionAttribute(\d{1,2})\s*(?:-eq|-ne|[:=])\s*(["'`])([^"'`]*)\2""",
    re.IGNORECASE,
)


class Codebook:
    """The subset of codebook.yaml this guard compares the corpus against."""

    def __init__(self, data: dict) -> None:
        facets = data["facets"]
        self.enum_by_facet: dict[str, set[str]] = {}
        self.allow_empty: dict[str, bool] = {}
        self.facet_by_attribute: dict[str, str] = {}
        for name, facet in facets.items():
            attribute = facet.get("attribute")
            if attribute:
                self.facet_by_attribute[attribute] = name
            if facet.get("kind") != "enumerated":
                continue
            self.enum_by_facet[name] = {str(e["value"]) for e in facet.get("enumeration", [])}
            self.allow_empty[name] = bool(facet.get("allow_empty", False))

        labels = data["hybrid"]["inheritance_layer"]["segment_labels"]
        # Label -> facet name, e.g. "Division" -> "division".
        self.facet_by_label: dict[str, str] = {label: facet for facet, label in labels.items()}

    def licenses(self, facet: str, value: str) -> bool:
        """True when ``value`` is one the codebook permits for ``facet``."""
        enumeration = self.enum_by_facet.get(facet)
        if enumeration is None:  # typed or reserved — not this guard's business
            return True
        if value == "" and self.allow_empty.get(facet, False):
            return True
        return value in enumeration


def load_codebook(root: Path) -> Codebook:
    return Codebook(yaml.safe_load((root / CODEBOOK).read_text(encoding="utf-8")))


def scan_text(text: str, rel: str, codebook: Codebook) -> list[str]:
    if ALLOW_FILE_MARKER in text:
        return []

    findings: list[str] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if any(marker in line for marker in ALLOW_MARKERS):
            continue

        for pattern in COMPOSITE_PATH_RES:
            for match in pattern.finditer(line):
                findings.append(
                    f"{rel}:{lineno}: composite-path literal '{match.group(0)}' — the whole "
                    f"path in one value is the retired Model A/B shape (ADR-078, ADR-127). "
                    f"Use the facets, or the derived path on extensionAttribute15."
                )

        for label, value in SEGMENT_RE.findall(line):
            facet = codebook.facet_by_label.get(label)
            if facet and not codebook.licenses(facet, value.strip()):
                findings.append(
                    f"{rel}:{lineno}: derived-path segment '{label}={value}' — "
                    f"'{value}' is not in the {facet} enumeration. Extending an "
                    f"enumeration is a governed PR against {CODEBOOK.as_posix()}."
                )

        for slot, _quote, value in SLOT_VALUE_RE.findall(line):
            if not value.strip():
                # `-ne ""` and friends test whether the slot is populated at
                # all. That is a presence check, not an asserted value.
                continue
            facet = codebook.facet_by_attribute.get(f"extensionAttribute{slot}")
            if facet and not codebook.licenses(facet, value.strip()):
                findings.append(
                    f"{rel}:{lineno}: extensionAttribute{slot} compared to '{value}' — "
                    f"'{value}' is not in the {facet} enumeration. Extending an "
                    f"enumeration is a governed PR against {CODEBOOK.as_posix()}."
                )

    return findings


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def iter_scan_files(root: Path, subpath: str | None = None) -> list[Path]:
    seen: set[Path] = set()
    for pattern in SCAN_GLOBS:
        for path in root.glob(pattern):
            if not path.is_file():
                continue
            rel = path.relative_to(root)
            if EXCLUDE_PARTS & set(rel.parts):
                continue
            if path.suffix.lower() not in SCANNABLE_SUFFIXES:
                continue
            if subpath and not rel.as_posix().startswith(subpath.rstrip("/") + "/"):
                continue
            seen.add(path)
    return sorted(seen)


def main(argv: list[str] | None = None) -> int:
    use_utf8_stdout()

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="exit 1 when any finding remains")
    parser.add_argument("--path", default=None, help="restrict the scan to a repo-relative subtree")
    parser.add_argument(
        "--summary",
        action="store_true",
        help="print one line per file with a finding count instead of every finding",
    )
    args = parser.parse_args(argv)

    root = repo_root()
    codebook = load_codebook(root)
    files = iter_scan_files(root, args.path)

    findings: list[str] = []
    per_file: dict[str, int] = {}
    for path in files:
        rel = path.relative_to(root).as_posix()
        found = scan_text(path.read_text(encoding="utf-8", errors="replace"), rel, codebook)
        if found:
            per_file[rel] = len(found)
            findings.extend(found)

    scope = args.path or "canon + docs"
    if findings:
        print("OrgPath examples the codebook does not license:\n")
        if args.summary:
            for rel, count in sorted(per_file.items(), key=lambda kv: (-kv[1], kv[0])):
                print(f"  {count:5d}  {rel}")
        else:
            for finding in findings:
                print(f"  {finding}")
        print(
            f"\n{len(findings)} finding(s) across {len(per_file)} file(s) in {scope}. "
            f"The SSOT is {CODEBOOK.as_posix()}.\n"
            "Fix the example, or — for content deliberately naming the retired era in "
            f"order to declare it retired — append '{ALLOW_MARKERS[0]}' to the line "
            f"(or '{ALLOW_FILE_MARKER}' for a whole historical document)."
        )
        if args.strict:
            return 1
        print("\nAdvisory mode (no --strict): not failing the build.")
        return 0

    print(
        f"OrgPath codebook-conformance guard OK — scanned {len(files)} files in {scope}; "
        "no composite-path literals and no facet values outside their enumeration."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
