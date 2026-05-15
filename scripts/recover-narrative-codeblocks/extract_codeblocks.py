"""Extract code blocks from a pandoc-source .docx using stdlib only.

Strategy:
  - .docx is a zip; word/document.xml carries the body.
  - For each <w:p>, inspect runs: if the run-font (w:rFonts/@w:ascii) is in the
    monospace allowlist, the run is "code." A paragraph is a "code paragraph"
    if its monospace-character share exceeds 50%.
  - Consecutive code paragraphs form one code block.
  - Within a paragraph, <w:br/> elements become line breaks; each <w:p> is
    itself a line break (Word treats one paragraph per line in code blocks).

Outputs JSON to stdout: list of {block_index, paragraph_count, char_count, text, preview}.
"""

import json
import sys
import zipfile
from xml.etree import ElementTree as ET

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
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


def get_run_font(r):
    """Return the ascii font name of a run, or '' if not set."""
    rPr = r.find(f"{W}rPr")
    if rPr is None:
        return ""
    rFonts = rPr.find(f"{W}rFonts")
    if rFonts is None:
        return ""
    return rFonts.get(f"{W}ascii", "") or ""


def run_text_with_breaks(r):
    """Reconstruct the text of a run, treating <w:br/> as newlines."""
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
    """Reconstruct paragraph text across all runs."""
    out = []
    for r in p.findall(f"{W}r"):
        out.append(run_text_with_breaks(r))
    return "".join(out)


def paragraph_monospace_share(p):
    """What fraction of paragraph text is in a monospace font?"""
    total = 0
    mono = 0
    for r in p.findall(f"{W}r"):
        text = run_text_with_breaks(r)
        n = len(text)
        total += n
        if get_run_font(r) in MONOSPACE:
            mono += n
    if total == 0:
        return 0.0
    return mono / total


def main(docx_path):
    with zipfile.ZipFile(docx_path) as z, z.open("word/document.xml") as f:
        xml_bytes = f.read()
    root = ET.fromstring(xml_bytes)
    body = root.find(f"{W}body")

    # Walk paragraphs in document order.
    paras = body.findall(f"{W}p")

    blocks = []
    current = None  # list of paragraph texts

    for p in paras:
        share = paragraph_monospace_share(p)
        text = paragraph_text(p)
        is_code = share > 0.5 and text.strip() != ""
        if is_code:
            if current is None:
                current = []
            current.append(text)
        else:
            if current:
                blocks.append(current)
                current = None
    if current:
        blocks.append(current)

    out = []
    for i, block in enumerate(blocks):
        joined = "\n".join(block)
        out.append(
            {
                "block_index": i,
                "paragraph_count": len(block),
                "char_count": len(joined),
                "preview_first_120": joined[:120],
                "preview_last_60": joined[-60:],
                "text": joined,
            }
        )

    # Print JSON summary, then full text per block
    summary = [{k: v for k, v in b.items() if k != "text"} for b in out]
    print(json.dumps({"path": docx_path, "block_count": len(out), "blocks": summary}, indent=2))


if __name__ == "__main__":
    main(sys.argv[1])
