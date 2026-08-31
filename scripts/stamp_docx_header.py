#!/usr/bin/env python3
"""Stamp a rendered .docx with a first-page header carrying render time and Rev.

Two different questions get two different values, and keeping them apart is the
whole point of this script:

  Rendered   the build clock. Moves on every render, including a re-render of
             unchanged content. Tells a reader how fresh the artifact is.

  Rev        the last commit that changed *this document's own sources*. Does
             NOT move on a re-render. Tells a reader whether the content
             differs from the copy already on their desk.

Two people comparing printouts can settle "same document?" from the Rev alone,
which is the question that actually matters; the timestamp alone cannot answer
it, because every nightly deploy produces a new one.

Why post-render rather than the reference template: Pandoc copies header parts
from the reference .docx verbatim, so a header there can only be static text.
A Word DATE field would render the reader's clock at open time, not the build
clock. So the header is generated here, after Quarto has produced the file.

The header is attached as a `first`-page header with `<w:titlePg/>`, so it
appears on page 1 only. To put it on every page, also emit a `default`-type
headerReference (see attach_header).

Usage:
    python scripts/stamp_docx_header.py <rendered.docx> --source <source.qmd>
    python scripts/stamp_docx_header.py <rendered.docx> --source <src.qmd> --check
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
CT = "{http://schemas.openxmlformats.org/package/2006/content-types}"

HEADER_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"
HEADER_RELTYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/header"

# Emitted when git cannot answer honestly. Never silently substitute the
# render time here: a Rev that tracks the clock is worse than no Rev, because
# it looks authoritative while telling the reader nothing about the content.
REV_UNKNOWN = "uncommitted"

# Lets a re-stamp recognise and remove its own previous header part instead of
# leaving an orphan behind each time.
STAMP_MARKER = "<!-- uiao-docx-header-stamp -->"


class ShallowCloneError(RuntimeError):
    """Raised when git history is too shallow for a per-file Rev to mean anything."""


def run_git(args: list[str], repo: Path) -> str:
    out = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
    )
    return out.stdout.strip() if out.returncode == 0 else ""


def assert_full_history(repo: Path) -> None:
    """A shallow clone makes `git log -- <file>` return the tip for every file.

    Every document would then report the same Rev, and it would change on every
    commit to the branch -- authoritative-looking and wrong. Refuse instead.
    """
    if run_git(["rev-parse", "--is-shallow-repository"], repo) == "true":
        raise ShallowCloneError(
            "repository is a shallow clone, so a per-file Rev cannot be computed. "
            "Set `fetch-depth: 0` on the checkout step that renders DOCX."
        )


def document_inputs(source: Path, repo: Path) -> list[Path]:
    """This document's own sources: the .qmd plus the figures it references.

    Scope note, deliberate: a change to the shared reference template or to a
    Lua filter also changes the rendered output but does NOT move the Rev. That
    matches "was this particular document changed" -- and avoids one template
    tweak bumping the Rev of every document in the corpus. If you later want
    the stricter reading, add those paths here.
    """
    # Absolute, because git runs with `-C <repo>` while the caller's cwd is
    # usually docs/ (the render working-directory). A path relative to the
    # caller would silently resolve to nothing from the repo root.
    source = source.resolve()
    inputs = [source]
    try:
        text = source.read_text(encoding="utf8")
    except OSError:
        return inputs
    for ref in re.findall(r"]\(([^)\s]+\.(?:png|svg|jpg|jpeg|gif))", text):
        candidate = (source.parent / ref).resolve()
        # Figures are referenced as .png, but per ADR-093 the tracked source is
        # the sibling .svg and the .png is an untracked build artifact. Follow
        # the reference to whichever of the two git actually knows about, or a
        # figure change would never move the Rev.
        for path in (candidate, candidate.with_suffix(".svg")):
            try:
                path.relative_to(repo.resolve())
            except ValueError:
                continue  # outside the repo; not ours to track
            if path.exists():
                inputs.append(path)
                break
    return inputs


def compute_rev(source: Path, repo: Path) -> tuple[str, str]:
    """Return (short_sha, iso_date) of the newest commit touching this document."""
    assert_full_history(repo)
    best: tuple[int, str, str] | None = None
    for path in document_inputs(source, repo):
        line = run_git(["log", "-1", "--format=%ct\t%h\t%cs", "--", str(path)], repo)
        if not line or "\t" not in line:
            continue
        ts, sha, date = line.split("\t")
        stamp = (int(ts), sha, date)
        if best is None or stamp[0] > best[0]:
            best = stamp
    if best is None:
        return REV_UNKNOWN, ""
    return best[1], best[2]


def header_text(source: Path, repo: Path, now: dt.datetime) -> str:
    sha, date = compute_rev(source, repo)
    rendered = now.strftime("%Y-%m-%d %H:%M UTC")
    if sha == REV_UNKNOWN:
        return f"Rendered {rendered}  ·  Rev {REV_UNKNOWN}"
    return f"Rendered {rendered}  ·  Rev {sha} ({date})"


def header_xml(text: str) -> bytes:
    esc = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        + STAMP_MARKER
        + '<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:p><w:pPr>"
        '<w:jc w:val="right"/>'
        '<w:spacing w:after="0"/>'
        "<w:rPr>"
        '<w:sz w:val="16"/><w:szCs w:val="16"/>'
        '<w:color w:val="6E7781"/>'
        "</w:rPr>"
        "</w:pPr>"
        "<w:r><w:rPr>"
        '<w:sz w:val="16"/><w:szCs w:val="16"/>'
        '<w:color w:val="6E7781"/>'
        "</w:rPr>"
        f'<w:t xml:space="preserve">{esc}</w:t>'
        "</w:r></w:p>"
        "</w:hdr>"
    ).encode("utf8")


def next_free(names: set[str]) -> tuple[str, str]:
    n = 1
    while f"word/header{n}.xml" in names:
        n += 1
    return f"header{n}.xml", f"word/header{n}.xml"


def next_rid(rels_root: ET.Element) -> str:
    used = {r.get("Id", "") for r in rels_root}
    n = 1
    while f"rIdHdr{n}" in used:
        n += 1
    return f"rIdHdr{n}"


def attach_header(doc_xml: bytes, rid: str) -> bytes:
    """Point every section's first page at the new header and enable titlePg."""
    ET.register_namespace("w", W[1:-1])
    ET.register_namespace("r", R[1:-1])
    root = ET.fromstring(doc_xml)
    sect_prs = [el for el in root.iter(W + "sectPr")]
    if not sect_prs:
        raise RuntimeError("document has no sectPr; cannot attach a header")
    for sect in sect_prs:
        for existing in sect.findall(W + "headerReference"):
            if existing.get(W + "type") == "first":
                sect.remove(existing)  # idempotent: replace our own prior stamp
        ref = ET.Element(W + "headerReference")
        ref.set(W + "type", "first")
        ref.set(R + "id", rid)
        sect.insert(0, ref)
        if sect.find(W + "titlePg") is None:
            sect.append(ET.Element(W + "titlePg"))
    return ET.tostring(root, xml_declaration=True, encoding="UTF-8")


def stamp(docx: Path, source: Path, repo: Path, now: dt.datetime) -> str:
    text = header_text(source, repo, now)

    with zipfile.ZipFile(docx) as zf:
        names = zf.namelist()
        parts = {n: zf.read(n) for n in names}

    # Drop any header this script wrote on a previous run, along with its
    # relationship and content-type override, so re-stamping cannot accumulate
    # orphaned parts. Headers from the reference template are left alone.
    stale = [n for n in names if n.startswith("word/header") and STAMP_MARKER.encode() in parts[n]]
    for n in stale:
        names.remove(n)
        parts.pop(n, None)

    hdr_name, hdr_path = next_free(set(names))

    # relationship
    ET.register_namespace("", REL[1:-1])
    rels_root = ET.fromstring(parts["word/_rels/document.xml.rels"])
    stale_names = {Path(n).name for n in stale}
    for rel_el in list(rels_root):
        if rel_el.get("Target", "") in stale_names:
            rels_root.remove(rel_el)
    rid = next_rid(rels_root)
    rel = ET.SubElement(rels_root, REL + "Relationship")
    rel.set("Id", rid)
    rel.set("Type", HEADER_RELTYPE)
    rel.set("Target", hdr_name)
    parts["word/_rels/document.xml.rels"] = ET.tostring(rels_root, xml_declaration=True, encoding="UTF-8")

    # content-type override
    ET.register_namespace("", CT[1:-1])
    ct_root = ET.fromstring(parts["[Content_Types].xml"])
    for ov in list(ct_root):
        if ov.get("PartName", "").lstrip("/") in stale:
            ct_root.remove(ov)
    override = ET.SubElement(ct_root, CT + "Override")
    override.set("PartName", f"/{hdr_path}")
    override.set("ContentType", HEADER_CT)
    parts["[Content_Types].xml"] = ET.tostring(ct_root, xml_declaration=True, encoding="UTF-8")

    parts[hdr_path] = header_xml(text)
    parts["word/document.xml"] = attach_header(parts["word/document.xml"], rid)

    fd, tmp = tempfile.mkstemp(suffix=".docx", dir=str(docx.parent))
    os.close(fd)
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
        for name in names:
            out.writestr(name, parts[name])
        out.writestr(hdr_path, parts[hdr_path])
    shutil.move(tmp, docx)
    return text


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("docx", type=Path, help="rendered .docx to stamp, in place")
    ap.add_argument("--source", type=Path, required=True, help="the .qmd it was rendered from")
    ap.add_argument("--repo", type=Path, default=Path("."), help="repository root (default: cwd)")
    ap.add_argument(
        "--check",
        action="store_true",
        help="print the header line that would be stamped, and stamp nothing",
    )
    args = ap.parse_args()

    if not args.docx.is_file():
        print(f"error: no such .docx: {args.docx}", file=sys.stderr)
        return 2
    if not args.source.is_file():
        print(f"error: no such source: {args.source}", file=sys.stderr)
        return 2

    now = dt.datetime.now(dt.timezone.utc)
    try:
        if args.check:
            print(header_text(args.source, args.repo, now))
            return 0
        print(f"{args.docx}: {stamp(args.docx, args.source, args.repo, now)}")
    except ShallowCloneError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
