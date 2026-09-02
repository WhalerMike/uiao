#!/usr/bin/env python3
"""Fail a distribution kit build that carries agency identity.

WHY THIS EXISTS. Every OrgComp kit README states the same guarantee —
"FEDERAL EDITION. Written for any federal agency; no agency is named." Until
now nothing enforced it. The enforcement was an *assumption*, written into
build_orgcomp_download.py's own docstring:

    "the .docx it collects are the federal renders and the .pptx/kits carry
     no agency facts, so the download cannot leak the agency edition"

That assumption held for the book documents, which Quarto renders through
``{{< meta agency.* >}}`` against the federal ``_metadata.yml``. It did not
hold for the operator-kit directories, which ``KIT_DIRS`` sweeps with
``rglob("*")``: two committed ``.docx`` under ``OrgComp-Training-Program/``
were the *agency* edition — one titled "SSA Federal Application-Aware
Networking (FedAAN)" — and shipped in every build of
``orgcomp-federal-series-latest.zip``. A de-brand pass (PR #1377) swept that
directory and missed them, because a text sweep cannot see inside a ``.docx``.

So the control cannot be "remember that binaries exist." It has to be a gate
that opens the binaries and reads them, and it has to run on the assembled
member list — after every collection path has contributed, whatever that path
was. That is this module.

USAGE

    # standalone, against a built kit
    python scripts/check_kit_agency_leak.py _site/download/orgcomp-federal-series-latest.zip

    # or a directory
    python scripts/check_kit_agency_leak.py path/to/extracted-kit/

    # in-process, before a build script writes its zip
    from check_kit_agency_leak import scan_members, format_findings
    findings = scan_members(members, extra={"INDEX.md": index_text})
    if findings:
        print(format_findings(findings))
        return 1

Exit status is 1 when anything is found, 0 when clean, so CI can gate on it.
"""

from __future__ import annotations

import argparse
import io
import re
import sys
import zipfile
from pathlib import Path

# ---------------------------------------------------------------------------
# What counts as agency identity.
#
# These mirror inbox/aan-ssa-edition/_agency-ssa.yml, which is the ONLY place
# the agency's facts are supposed to live. Keep the two in step: a new key
# there needs a pattern here, or the gate silently stops covering it.
#
# Case-SENSITIVE on purpose. "SSA" is the identity; "ssa-attribute-service"
# is a technical identifier that appears legitimately in adapter code and must
# not trip the gate. Anchoring on the uppercase form separates them without an
# exclusion list.
# ---------------------------------------------------------------------------
AGENCY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("agency.short", re.compile(r"\bSSA\b")),
    ("agency.full", re.compile(r"\bSocial Security Administration\b")),
    ("agency.domain", re.compile(r"\bssa\.gov\b", re.IGNORECASE)),
    ("agency.tenant", re.compile(r"\bssagov\.onmicrosoft\.com\b", re.IGNORECASE)),
)

# Phrases that CONTAIN a pattern above but are not agency identity.
#
# "Social Security Number" is PII-detection vocabulary — Vol III Book 05's
# Purview DLP rules are full of it, correctly. "Social Security Act" is a
# statute anyone may cite; it is the agency's `statute` value, but a bare
# citation in prose does not name the agency, and sweeping it would gut the
# regulatory scholarship. Both are matched BEFORE the agency patterns and the
# span is removed, so a line can contain "SSN" and still be scanned for "SSA".
FALSE_POSITIVES = re.compile(
    r"\bSocial Security (?:Number|Numbers|Act|number|numbers)\b|\bSSN\b",
)

# Paths inside the kit that are known to carry the token and are NOT fixed.
#
# EMPTY, and it should stay that way. It briefly held Vol I Book 01's filename,
# ..._OrgComp_SSA_Landing_Zone_..., while the rename was pending; that rename
# has landed and the entry is gone. An entry here is a hole in the gate, so it
# needs a reason, a plan to remove it, and a reviewer who agrees the path is
# genuinely not a leak. Never add one to make a failing build pass.
PATH_ALLOWLIST: tuple[str, ...] = ()

# Members whose bytes are scanned. Office formats are unzipped and their text
# parts read; everything else in this set is decoded as UTF-8. Binaries not
# listed here (.png, .zip) carry no readable prose and are skipped.
TEXT_SUFFIXES = frozenset(
    {".md", ".txt", ".qmd", ".yml", ".yaml", ".json", ".html", ".csv", ".js", ".py", ".ps1", ".sh", ".tf", ".bicep"}
)
OOXML_SUFFIXES = frozenset({".docx", ".pptx", ".xlsx"})

# The XML parts of an OOXML package that hold author-visible text. Slide notes
# and footnotes are included deliberately — the leak can sit in a speaker note
# as easily as on the slide.
_OOXML_TEXT_PART = re.compile(
    r"^(?:word/(?:document|footnotes|endnotes|comments|header\d*|footer\d*)\.xml"
    r"|ppt/(?:slides/slide\d+|notesSlides/notesSlide\d+|slideMasters/slideMaster\d+)\.xml"
    r"|xl/(?:sharedStrings|worksheets/sheet\d+)\.xml)$"
)
_TAG = re.compile(r"<[^>]+>")


def _ooxml_text(data: bytes) -> str:
    """Return the author-visible text of an OOXML package."""
    try:
        pkg = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        return ""
    chunks: list[str] = []
    for name in pkg.namelist():
        if not _OOXML_TEXT_PART.match(name):
            continue
        xml = pkg.read(name).decode("utf-8", "replace")
        # Paragraph and break tags become newlines first, so a hit reports a
        # sensible excerpt instead of the whole document on one line.
        xml = re.sub(r"</w:p>|<w:br/>|</a:p>", "\n", xml)
        chunks.append(_TAG.sub("", xml))
    return "\n".join(chunks)


def _decode(name: str, data: bytes) -> str | None:
    suffix = Path(name).suffix.lower()
    if suffix in OOXML_SUFFIXES:
        return _ooxml_text(data)
    if suffix in TEXT_SUFFIXES:
        return data.decode("utf-8", "replace")
    return None


def _allowlisted(arcname: str) -> bool:
    return any(token in arcname for token in PATH_ALLOWLIST)


# Underscore is a word character, so ``\bSSA\b`` does NOT match inside
# ``Vol_I_Book_01_OrgComp_SSA_Landing_Zone`` — which is exactly the shape every
# filename in this corpus has. Path separators are normalised to spaces before
# matching so the word-boundary patterns see the segments. Content is scanned
# unmodified: loosening the boundary there would start matching inside ordinary
# words and identifiers.
_PATH_SEP = re.compile(r"[_\-./\\]+")


def _path_as_words(arcname: str) -> str:
    return _PATH_SEP.sub(" ", arcname)


def _scan_text(arcname: str, text: str) -> list[tuple[str, str, str]]:
    """Return (arcname, key, excerpt) for every agency hit in ``text``."""
    found: list[tuple[str, str, str]] = []
    for line in text.splitlines():
        # Blank out the legitimate phrases so their substrings cannot match,
        # keeping the rest of the line scannable.
        scannable = FALSE_POSITIVES.sub(lambda m: " " * len(m.group(0)), line)
        for key, pattern in AGENCY_PATTERNS:
            m = pattern.search(scannable)
            if not m:
                continue
            start = max(0, m.start() - 60)
            excerpt = " ".join(line[start : m.end() + 60].split())
            found.append((arcname, key, excerpt))
            break
    return found


def scan_one(arcname: str, data: bytes) -> list[tuple[str, str, str]]:
    """Scan a single kit member. Returns [] for allowlisted or unreadable members."""
    if _allowlisted(arcname):
        return []
    hits = _scan_text(arcname, _path_as_words(arcname))  # the path itself can name the agency
    text = _decode(arcname, data)
    if text:
        hits += _scan_text(arcname, text)
    return hits


def scan_members(
    members: dict[str, Path],
    extra: dict[str, str] | None = None,
) -> list[tuple[str, str, str]]:
    """Scan a build script's assembled {archive_path: source_file} map.

    ``extra`` carries members the build generates in memory (README.txt,
    INDEX.md, concatenated bundles) — those never touch disk, so they would
    otherwise ship unscanned. INDEX.md in particular reproduces every archive
    path, which is how a leaking FILENAME reaches a reader.
    """
    findings: list[tuple[str, str, str]] = []
    for arc, src in sorted(members.items()):
        try:
            findings += scan_one(arc, src.read_bytes())
        except OSError as exc:  # unreadable input is a build problem, not a pass
            findings.append((arc, "unreadable", f"{exc}"))
    for arc, text in sorted((extra or {}).items()):
        findings += scan_one(arc, text.encode("utf-8"))
    return findings


def scan_zip(path: Path) -> list[tuple[str, str, str]]:
    findings: list[tuple[str, str, str]] = []
    with zipfile.ZipFile(path) as z:
        for name in sorted(z.namelist()):
            if name.endswith("/"):
                continue
            findings += scan_one(name, z.read(name))
    return findings


def scan_dir(path: Path) -> list[tuple[str, str, str]]:
    findings: list[tuple[str, str, str]] = []
    for f in sorted(path.rglob("*")):
        if f.is_file():
            findings += scan_one(f.relative_to(path).as_posix(), f.read_bytes())
    return findings


def format_findings(findings: list[tuple[str, str, str]]) -> str:
    lines = [
        "",
        "FATAL: agency identity found in the federal kit — refusing to ship.",
        "",
        "  The kit README states 'no agency is named'. These members contradict it.",
        "  Fix the source (de-brand it, or move it to inbox/aan-ssa-edition/),",
        "  then rebuild. Do NOT add an allowlist entry to silence a real leak.",
        "",
    ]
    by_member: dict[str, list[tuple[str, str]]] = {}
    for arc, key, excerpt in findings:
        by_member.setdefault(arc, []).append((key, excerpt))
    for arc, hits in by_member.items():
        lines.append(f"  {arc}  ({len(hits)} hit(s))")
        for key, excerpt in hits[:3]:
            lines.append(f"      [{key}] …{excerpt}…")
        if len(hits) > 3:
            lines.append(f"      … and {len(hits) - 3} more")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Fail a kit that carries agency identity.")
    ap.add_argument("targets", nargs="+", type=Path, help="kit .zip file(s) or extracted directory(ies)")
    args = ap.parse_args(argv)

    status = 0
    for target in args.targets:
        if not target.exists():
            print(f"ERROR: {target} does not exist")
            status = 1
            continue
        findings = scan_zip(target) if target.is_file() else scan_dir(target)
        if findings:
            print(f"=== {target} ===")
            print(format_findings(findings))
            status = 1
        else:
            print(f"OK: {target} — no agency identity found")
    return status


if __name__ == "__main__":
    sys.exit(main())
