#!/usr/bin/env python3
"""Guard prose against the retired Model A/B OrgPath slot binding.

Under Model A/B, the whole OrgPath lived in one slot as a composite string
(``extensionAttribute1 = "CORP/US/EAST/BALTIMORE/IT"``). ADR-078 replaced that
with named facets — ``extensionAttribute1`` became the **region** facet — and
ADR-127 completed it as Hybrid-C+Path, moving the derived canonical path to
``extensionAttribute15``. The authoritative slot map is
``src/uiao/canon/data/orgpath/codebook.yaml``; this guard compares what the
corpus *says* against it.

The failure mode this exists for is silent and expensive: a spec that says
"stamp OrgPath into extensionAttribute1" reads perfectly, passes review, and
configures a mapping engine to write the full path into the region slot. Issue
#1426 found 46 files still carrying that binding, including the whole Spec 2
provisioning family — the sibling guard ``check_orgpath_prefix_delimiter.py``
could not catch them, because it validates prefix *expressions* and explicitly
excludes legacy path styles by construction.

Two rules, both scoped to lines naming exactly ONE slot (ranges like
``extensionAttribute1-14`` describe the family and are out of scope):

1. **Composite-path literal** — a line binding a slot to a Model A/B path
   literal (``ORG-FIN``, ``CORP/US/EAST``) must name the derived-path slot.
2. **Explicit OrgPath binding** — a line binding a slot to "OrgPath" with a
   binding token (``=``, ``(OrgPath)``, a table cell, "stamp/write/populate")
   must likewise name the derived-path slot.

Bare mentions of OrgPath as the *programme* name never trip either rule; the
word is everywhere in this corpus and only an asserted binding is a finding.

Scope: canon + published docs. Non-canon scratch surfaces (``inbox/``,
``downloads/``, ``session-logs/``, ``models/``, build output) are excluded,
matching the other repo guards. Historical ADRs that describe their own
pre-078 era are exempted with the inline marker ``orgpath-slot-allow``.

Exit codes follow the scan_lifecycle_consistency.py precedent:

  0  advisory mode (default) — findings are printed, the gate stays green
  1  --strict and any finding remains

Canon (``src/uiao/canon/**``) is clean and is enforced with ``--strict`` in CI
today. The authored ``docs/`` corpus still carries ~80 Model A examples whose
correction needs a per-example semantic remap (``ORG-FIN`` -> which facets?),
tracked separately; until that lands, a bare run stays advisory so the backlog
is visible without blocking unrelated PRs.

Run locally:  python scripts/check_orgpath_slot_binding.py
              python scripts/check_orgpath_slot_binding.py --strict
              python scripts/check_orgpath_slot_binding.py --strict --path src/uiao/canon
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ALLOW_MARKER = "orgpath-slot-allow"
# A whole document may legitimately describe the retired era — ADR-063 *is* the
# composite-path slot binding, ADR-078's comparison table quotes Model A/B
# verbatim. Line markers can't be used there: most such content is in markdown
# tables, where a trailing `<!-- ... -->` breaks the row. A file-level marker
# (in an HTML comment near the reconciliation banner, carrying its reason) exempts
# the document instead.
ALLOW_FILE_MARKER = "orgpath-slot-allow-file"

CODEBOOK = Path("src/uiao/canon/data/orgpath/codebook.yaml")

SCAN_GLOBS: list[str] = [
    "src/uiao/canon/**/*.md",
    "src/uiao/canon/**/*.yaml",
    "docs/**/*.md",
    "docs/**/*.qmd",
]

EXCLUDE_PARTS = {"inbox", "downloads", "session-logs", "models", ".quarto", "_site", "out"}

# One slot, e.g. extensionAttribute1 / extensionAttribute15.
SLOT_RE = re.compile(r"extensionAttribute(\d{1,2})\b", re.IGNORECASE)

# A slot range describes the family, not a binding: extensionAttribute1-14,
# extensionAttribute1–10, extensionAttribute3–5, extensionAttribute1..15, and
# the backticked prose form `extensionAttribute1`–`15`. The closing backtick
# before the dash is why this needs an explicit optional quote on both sides.
RANGE_RE = re.compile(
    r"extensionAttribute\d{1,2}[`\"']?\s*(?:[-–—]|\.\.|\bto\b)\s*[`\"']?\d{1,2}",
    re.IGNORECASE,
)

# Model A/B composite-path literals: ORG-FIN-AP, CORP/US/EAST/BALTIMORE/IT.
PATH_LITERAL_RE = re.compile(r"\bORG(?:-[A-Z]{2,8}){1,8}\b|\b[A-Z]{2,}(?:/[A-Z]{2,}){2,}\b")

# "OrgPath" as a stored value rather than the programme name.
BINDING_RE = re.compile(
    r"""(?:
          =\s*[\"'`]?\s*OrgPath          # extensionAttribute1 = OrgPath
        | \(\s*OrgPath\s*\)              # `extensionAttribute1` (OrgPath)
        | \|\s*OrgPath                   # | extensionAttribute1 | OrgPath ... |
        | OrgPath\s*(?:value|string|address)?\s*(?:=|→|->|in|into|to|on)\s
        | (?:stamp|write|writes|written|populate|populates|store|stores|carry|carries)
          [^.\n]{0,40}?OrgPath
        | OrgPath[^.\n]{0,40}?
          (?:stamp|stamped|written|write|populated|stored|carried|lives|selection)
    )""",
    re.IGNORECASE | re.VERBOSE,
)


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def org_path_slot(root: Path) -> str:
    """Read the derived-path slot from the codebook — the SSOT, not a constant."""
    text = (root / CODEBOOK).read_text(encoding="utf-8")
    match = re.search(r"^  org_path:\s*\n\s+attribute:\s*extensionAttribute(\d{1,2})", text, re.M)
    if not match:
        raise SystemExit(f"error: no org_path facet slot found in {CODEBOOK}")
    return match.group(1)


def facet_slots(root: Path) -> dict[str, str]:
    """Map facet name -> slot number from the codebook `facets:` block."""
    text = (root / CODEBOOK).read_text(encoding="utf-8")
    block = text.split("\nfacets:", 1)[-1]
    return {
        m.group(1): m.group(2)
        for m in re.finditer(r"^  ([a-z_]+):\s*\n\s+attribute:\s*extensionAttribute(\d{1,2})", block, re.M)
    }


def scan_text(text: str, rel: str, path_slot: str) -> list[str]:
    findings: list[str] = []
    if ALLOW_FILE_MARKER in text:
        return findings
    for lineno, line in enumerate(text.splitlines(), start=1):
        if ALLOW_MARKER in line or RANGE_RE.search(line):
            continue
        slots = {m.group(1) for m in SLOT_RE.finditer(line)}
        if len(slots) != 1:
            continue
        slot = slots.pop()
        if slot == path_slot:
            continue
        reason = None
        if PATH_LITERAL_RE.search(line):
            reason = "bound to a Model A/B composite-path literal"
        elif BINDING_RE.search(line):
            reason = "bound to OrgPath as a stored value"
        if reason:
            findings.append(
                f"{rel}:{lineno}: extensionAttribute{slot} {reason}; "
                f"the derived OrgPath lives on extensionAttribute{path_slot} (ADR-127) — {line.strip()[:110]}"
            )
    return findings


def iter_scan_files(root: Path, subpath: str | None = None) -> list[Path]:
    seen: set[Path] = set()
    for pattern in SCAN_GLOBS:
        for path in root.glob(pattern):
            if not path.is_file() or EXCLUDE_PARTS & set(path.relative_to(root).parts):
                continue
            if subpath and not path.relative_to(root).as_posix().startswith(subpath.rstrip("/") + "/"):
                continue
            seen.add(path)
    return sorted(seen)


def main(argv: list[str] | None = None) -> int:
    # Canon prose carries box-drawing, arrows, and en-dashes. On a Windows
    # cp1252 console an un-encodable char raises mid-print, truncating the
    # findings list — which reads as "fewer findings" rather than as a crash.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="exit 1 when any finding remains")
    parser.add_argument("--path", default=None, help="restrict the scan to a repo-relative subtree")
    args = parser.parse_args(argv)

    root = repo_root()
    path_slot = org_path_slot(root)
    files = iter_scan_files(root, args.path)

    findings: list[str] = []
    for path in files:
        findings.extend(
            scan_text(
                path.read_text(encoding="utf-8", errors="replace"),
                path.relative_to(root).as_posix(),
                path_slot,
            )
        )

    scope = args.path or "canon + docs"
    if findings:
        print("Retired OrgPath slot bindings — prose disagrees with codebook.yaml:\n")
        for finding in findings:
            print(f"  {finding}")
        print(
            f"\n{len(findings)} finding(s) in {scope}. The canonical map is "
            f"{CODEBOOK.as_posix()}: facets on the governance layer, derived path on "
            f"extensionAttribute{path_slot}.\n"
            "Fix the binding, or — for content deliberately describing the retired "
            f"Model A/B era — append '{ALLOW_MARKER}' to the line."
        )
        if args.strict:
            return 1
        print("\nAdvisory mode (no --strict): not failing the build.")
        return 0

    print(
        f"OrgPath slot-binding guard OK — scanned {len(files)} files in {scope}; "
        f"no prose binds a non-derived slot to the OrgPath value "
        f"(derived path = extensionAttribute{path_slot})."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
