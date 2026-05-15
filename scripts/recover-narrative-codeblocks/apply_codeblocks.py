"""Surgically replace flattened code blocks in a .qmd with their .docx originals.

Strategy:
  - Extract code blocks from the source .docx (using the same logic as extract.py).
  - For each extracted block, compute a fingerprint: the first 80 chars after
    collapsing whitespace.
  - Walk the .qmd line by line. For any "long" line (heuristic: > 400 chars OR
    starts with '\\<#' or '\\#' or '{' or '//' code-block markers), de-escape
    the pandoc escapes and collapse whitespace, then compare its leading 80
    chars to each block's fingerprint. On match, replace the line with the
    fenced code block.
  - Detect language per block by leading content.

Usage:
    python apply.py <source.docx> <input.qmd> <output.qmd>
"""

import re
import sys
import zipfile
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

MONOSPACE = {
    "Consolas",
    "Courier New",
    "Courier",
    "Cascadia Code",
    "Cascadia Mono",
    "Lucida Console",
    "Source Code Pro",
    "Monaco",
    "Menlo",
    "DejaVu Sans Mono",
    "Liberation Mono",
}

# Pandoc escape patterns to strip when comparing flattened text to docx text.
# Order matters: backslash-escapes for these chars become just the char.
PANDOC_ESCAPED_CHARS = list("\\<>#$|*[]()_{}~`")


def get_run_font(r):
    rPr = r.find(f"{W}rPr")
    if rPr is None:
        return ""
    rFonts = rPr.find(f"{W}rFonts")
    if rFonts is None:
        return ""
    return rFonts.get(f"{W}ascii", "") or ""


def run_text_with_breaks(r):
    pieces = []
    for child in r:
        tag = child.tag
        if tag == f"{W}t":
            pieces.append(child.text or "")
        elif tag == f"{W}tab":
            pieces.append("\t")
        elif tag == f"{W}br":
            pieces.append("\n")
    return "".join(pieces)


def paragraph_text(p):
    return "".join(run_text_with_breaks(r) for r in p.findall(f"{W}r"))


def paragraph_monospace_share(p):
    total = 0
    mono = 0
    for r in p.findall(f"{W}r"):
        text = run_text_with_breaks(r)
        n = len(text)
        total += n
        if get_run_font(r) in MONOSPACE:
            mono += n
    return mono / total if total else 0.0


def extract_blocks(docx_path):
    with zipfile.ZipFile(docx_path) as z:
        xml_bytes = z.read("word/document.xml")
    root = ET.fromstring(xml_bytes)
    body = root.find(f"{W}body")
    blocks = []
    current = []
    for p in body.findall(f"{W}p"):
        share = paragraph_monospace_share(p)
        text = paragraph_text(p)
        if share > 0.5 and text.strip():
            current.append(text)
        else:
            if current:
                blocks.append("\n".join(current))
                current = []
    if current:
        blocks.append("\n".join(current))
    return blocks


def detect_language(text):
    head = text[:200].lstrip()
    if head.startswith("{"):
        return "json"
    if head.startswith("//"):
        return "kql"
    if (
        head.startswith("<#")
        or head.startswith("#")
        or head.startswith("param(")
        or head.startswith("Configuration ")
        or head.startswith("Connect-")
        or head.startswith("Get-")
        or head.startswith("Set-")
        or head.startswith("(device.")
    ):
        # The (device.) case is the dynamic membership rule snippets.
        if head.startswith("(device."):
            return ""  # no language, short rule
        return "powershell"
    return ""


def collapse_whitespace(s):
    return re.sub(r"\s+", " ", s).strip()


def deescape_pandoc(s):
    """Remove backslash escapes inserted by pandoc for special chars."""
    out = []
    i = 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s) and s[i + 1] in PANDOC_ESCAPED_CHARS:
            out.append(s[i + 1])
            i += 2
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def fingerprint(text, n=80):
    """First n chars of de-escaped, whitespace-collapsed text."""
    return collapse_whitespace(deescape_pandoc(text))[:n]


def looks_like_flattened_code(line):
    """Heuristic: is this .qmd line a flattened code block?"""
    if len(line) < 400:
        # Allow shorter code blocks too — but only if they look code-y.
        stripped = line.strip()
        if not stripped:
            return False
        return stripped.startswith(("\\<#", "\\#", "{", "//", "(device.")) and " " in stripped
    return True


def main(docx_path, qmd_path, out_path):
    blocks = extract_blocks(docx_path)
    print(f"Extracted {len(blocks)} blocks from {docx_path}", file=sys.stderr)

    # Compute fingerprint per block
    block_fps = [(fingerprint(b), b) for b in blocks]

    with open(qmd_path, encoding="utf-8") as f:
        qmd_lines = f.readlines()

    out_lines = []
    matched_blocks = set()
    matches_per_line = {}

    for lineno, line in enumerate(qmd_lines, 1):
        bare = line.rstrip("\n")
        if not looks_like_flattened_code(bare):
            out_lines.append(line)
            continue
        line_fp = fingerprint(bare)
        if not line_fp:
            out_lines.append(line)
            continue
        # Find a block whose fingerprint matches.
        match_idx = None
        for i, (fp, _) in enumerate(block_fps):
            if i in matched_blocks:
                continue
            if fp and fp == line_fp:
                match_idx = i
                break
        if match_idx is None:
            # Try prefix match — sometimes pandoc adds a leading char.
            for i, (fp, _) in enumerate(block_fps):
                if i in matched_blocks:
                    continue
                if fp and (fp[:60] in line_fp or line_fp[:60] in fp):
                    match_idx = i
                    break
        if match_idx is None:
            out_lines.append(line)
            continue
        # Replace
        block_text = block_fps[match_idx][1]
        lang = detect_language(block_text)
        fence = f"```{lang}\n{block_text}\n```\n"
        out_lines.append(fence)
        matched_blocks.add(match_idx)
        matches_per_line[lineno] = match_idx
        print(
            f"  line {lineno}: matched block {match_idx} ({lang or 'no-lang'}, {len(block_text)} chars)",
            file=sys.stderr,
        )

    # Report unmatched blocks
    unmatched = set(range(len(blocks))) - matched_blocks
    if unmatched:
        print(f"\n  WARNING: {len(unmatched)} blocks unmatched: {sorted(unmatched)}", file=sys.stderr)
        for i in sorted(unmatched):
            print(f"    block {i}: fp={block_fps[i][0]!r}", file=sys.stderr)

    with open(out_path, "w", encoding="utf-8") as f:
        f.writelines(out_lines)
    print(f"\nWrote {out_path}; matched {len(matched_blocks)}/{len(blocks)} blocks", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
