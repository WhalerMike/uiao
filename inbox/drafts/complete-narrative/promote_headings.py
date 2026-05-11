"""
Promote heading structure that pandoc dropped during docx → gfm conversion.

The OrgPath narrative manuscripts use Word Heading1/Heading2/Heading3 styles
in the source .docx, but pandoc 3.9 fails to map those style IDs to ATX
headings — producing flat markdown where every section heading reads as
plain prose. This script restores the structure heuristically:

    **CHAPTER N**
    Chapter Title text

becomes

    ## Chapter N — Chapter Title text

and standalone short lines that look like section headings (≤120 chars,
no terminal punctuation, surrounded by blank lines, not inside a table or
HTML block) are promoted to `### Heading`.

Also strips the leading docx title block and table-of-contents — both are
redundant with the Quarto YAML frontmatter and Quarto's auto-generated
page TOC.

Usage:
    python promote_headings.py SRC_DIR DST_DIR

The script copies YAML frontmatter from DST_DIR (already-published .qmd
files) and replaces only the body. Run it from the repo root.
"""
from __future__ import annotations
import re
import sys
import pathlib

SPELLED = (
    'one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|'
    'thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty'
)
SPELLED_TO_NUM = {
    w: i + 1
    for i, w in enumerate(SPELLED.split('|'))
}

# Bold chapter markers — explicit, always trusted. Handles:
#   **CHAPTER 1** / **Chapter 1** / **CHAPTER ONE** / **Chapter One**
#   **Chapter 1 — Title** / **Chapter One — Title**
#   **Ch. 1** Title             (UIAO TOC + body marker style)
#   *Chapter 1* / *Chapter One*  (italic, single-asterisk variant)
CHAPTER_BOLD = re.compile(
    r'^(?:\*\*|\*)\s*(?:Chapter|Ch\.)\s+(\d+|' + SPELLED + r')\s*'
    r'(?:[—\-:]\s*(.+?))?\s*(?:\*\*|\*)'
    r'(?:\s+(.+?))?\s*$',  # optional plain-text trailing title after close
    re.IGNORECASE,
)
# Plain (no bold) chapter markers — must be standalone short lines:
#   Chapter 1 / Chapter One / Chapter 1 — Title / Chapter One — Title
CHAPTER_PLAIN = re.compile(
    r'^Chapter\s+(\d+|' + SPELLED + r')\s*'
    r'(?:[—\-:]\s*(.+?))?\s*$',
    re.IGNORECASE,
)
# **PART X — Title** / **Part One: Title** dividers (some manuscripts split
# into Parts of Chapters). Handles ALL CAPS or mixed-case Part labels and
# colon or em-dash separators.
PART_RE = re.compile(
    r'^\*\*\s*PART\s+([A-Za-z0-9]+)\s*(?:[—\-:]\s*(.+?))?\s*\*\*\s*$',
    re.I,
)

HTML_BLOCK_OPEN = re.compile(r'^\s*<(table|tbody|thead|tr|td|th|colgroup|col)\b', re.I)
HTML_BLOCK_CLOSE = re.compile(r'</(table|tbody|thead|tr|td|th|colgroup|col)>', re.I)
PIPE_TABLE_RE = re.compile(r'^\s*\|.*\|\s*$')
LIST_MARKER_RE = re.compile(r'^\s*([-*+]|\d+\.)\s+')
CODE_FENCE_RE = re.compile(r'^\s*```')
TERMINAL_PUNCT = '.;:?!,'


def is_section_heading(line: str) -> bool:
    """
    Heuristic: a line is a section heading if it's short, has no terminal
    punctuation, doesn't look like a list/code/table/HTML, and reads as a
    title-cased phrase.
    """
    s = line.strip()
    if not s:
        return False
    if len(s) > 120:
        return False
    if s.endswith(tuple(TERMINAL_PUNCT)):
        return False
    if s.startswith(('<', '|', '+', '#', '>', '`')):
        return False
    if LIST_MARKER_RE.match(s):
        return False
    if s.startswith('**') and s.endswith('**'):
        return False  # already-bold standalone — handled separately
    if s.startswith('*') and s.endswith('*'):
        return False  # italic byline / subtitle
    # Must contain at least one letter
    if not re.search(r'[A-Za-z]', s):
        return False
    # Avoid fragments like "What is X?" by length sanity
    words = s.split()
    if len(words) < 2 or len(words) > 18:
        return False
    return True


def _normalize_num(raw: str) -> str:
    """'1'→'1', 'one'/'One'/'ONE'→'1', etc."""
    s = raw.strip().lower()
    return s if s.isdigit() else str(SPELLED_TO_NUM[s])


def chapter_marker(
    line: str,
    lines: list[str] | None = None,
    i: int | None = None,
) -> tuple[str, str] | None:
    """If `line` is a chapter marker, return (number_str, inline_title_or_'').
    Plain (non-bold) markers require standalone-line context to disambiguate
    from prose like 'Chapter Two covers...'."""
    m = CHAPTER_BOLD.match(line)
    if m:
        # group(2) is the inline title between '—' and the closing **; group(3)
        # is the trailing-title form '**Ch. 1** Title'.
        title = (m.group(2) or '').strip() or (m.group(3) or '').strip()
        return (_normalize_num(m.group(1)), title)

    m = CHAPTER_PLAIN.match(line)
    if m:
        # Plain markers MUST be standalone, short, and not inside an HTML
        # block (TOC tables include 'Chapter N — Title' rows).
        if lines is None or i is None:
            return None
        if not is_standalone(lines, i):
            return None
        if len(line.strip()) > 150:
            return None
        if in_html_table(lines[: i + 1], i):
            return None
        title = (m.group(2) or '').strip()
        # Plain chapter heads typically include the title on the same line
        # ("Chapter 1 — Title"). A bare "Chapter Two" prose-fragment is
        # rejected by length+context above.
        return (_normalize_num(m.group(1)), title)

    return None


TOC_HEADER_RE = re.compile(
    r'^\s*(?:\*\*\s*)?(?:Table\s+of\s+)?Contents(?:\s*\*\*)?\s*$',
    re.IGNORECASE,
)


def find_first_structural_marker(lines: list[str]) -> int:
    """Return index of the first chapter marker OR Part divider, signalling
    the end of the title block / TOC. If the document has an explicit
    'Table of Contents' header, skip past the entire contiguous TOC block
    (interleaved bold chapter/part markers + blank lines) and return the
    index of the first body-content marker after it. Returns len(lines)
    if neither structure is found."""
    # Pass 1: look for an explicit 'Table of Contents' header.
    toc_at = None
    for i, line in enumerate(lines):
        if TOC_HEADER_RE.match(line):
            toc_at = i
            break

    if toc_at is not None:
        # Skip the TOC: a contiguous run of bold chapter/part markers
        # interleaved with blank lines. The TOC ends at the first line
        # that is neither blank nor a bold chapter/part marker.
        i = toc_at + 1
        while i < len(lines):
            ln = lines[i].strip()
            if (
                ln == ''
                or CHAPTER_BOLD.match(ln)
                or PART_RE.match(ln)
            ):
                i += 1
                continue
            break
        # From here, scan to the next chapter/part marker (the real body
        # start) — but only those NOT inside an HTML block.
        for j in range(i, len(lines)):
            if chapter_marker(lines[j], lines, j) or PART_RE.match(lines[j]):
                return j
        # No post-TOC structural marker: fall back to the line after TOC.
        return min(i, len(lines))

    # Pass 2: no explicit TOC — return the first chapter / Part marker.
    for i, line in enumerate(lines):
        if chapter_marker(line, lines, i):
            return i
        if PART_RE.match(line):
            return i
    return len(lines)


def in_html_table(lines: list[str], i: int) -> bool:
    """Crude scan: are we inside an HTML <table>...</table> block at index i?"""
    depth = 0
    for k in range(i + 1):
        if re.search(r'<table\b', lines[k], re.I):
            depth += 1
        if re.search(r'</table>', lines[k], re.I):
            depth -= 1
    return depth > 0


def in_code_fence(lines: list[str], i: int) -> bool:
    fence = False
    for k in range(i + 1):
        if CODE_FENCE_RE.match(lines[k]):
            fence = not fence
    return fence


def is_standalone(lines: list[str], i: int) -> bool:
    """Is the line at i surrounded by blank lines (or doc edges)?"""
    prev_blank = (i == 0) or lines[i - 1].strip() == ''
    next_blank = (i == len(lines) - 1) or lines[i + 1].strip() == ''
    return prev_blank and next_blank


def promote(text: str) -> str:
    lines = text.splitlines()
    n = len(lines)
    out: list[str] = []

    # 1. Strip everything before the first chapter / Part marker (title
    # block + TOC).
    first_ch = find_first_structural_marker(lines)
    if first_ch >= n:
        # No chapter / Part markers found — return unchanged
        return text

    # 2. Walk from first_ch, promoting structure
    i = first_ch
    while i < n:
        line = lines[i]
        ch = chapter_marker(line, lines, i)
        if ch:
            ch_num, inline_title = ch
            title = inline_title
            next_i = i + 1
            if not title:
                # Look ahead for chapter title on the next non-blank line
                j = i + 1
                while j < n and lines[j].strip() == '':
                    j += 1
                if j < n:
                    t = lines[j].strip()
                    # Title must look like a standalone short line
                    if (
                        t
                        and len(t) <= 200
                        and not t.startswith(('<', '|', '+', '#', '>', '*'))
                        and not LIST_MARKER_RE.match(t)
                    ):
                        title = t
                        next_i = j + 1
            if title:
                # Strip surrounding bold/italic if author already styled it
                title = title.strip().strip('*').strip('_').strip()
                out.append(f'## Chapter {ch_num} — {title}')
            else:
                out.append(f'## Chapter {ch_num}')
            out.append('')
            i = next_i
            continue

        # Promote **PART X** dividers to '## Part X — Title' (treated as
        # peer to chapters; some manuscripts split into Parts of Chapters)
        m = PART_RE.match(line)
        if m:
            num = m.group(1).upper()
            t = (m.group(2) or '').strip().strip('*').strip()
            out.append(f'## Part {num} — {t}' if t else f'## Part {num}')
            out.append('')
            i += 1
            continue

        # Promote standalone bold-only lines that are short and look like
        # section headings — e.g. **Section title**.
        bold_match = re.match(r'^\*\*(.+?)\*\*\s*$', line)
        if (
            bold_match
            and is_standalone(lines, i)
            and len(bold_match.group(1)) <= 120
            and not bold_match.group(1).strip().endswith(tuple(TERMINAL_PUNCT))
            and not in_html_table(lines[: i + 1], i)
            and not in_code_fence(lines[: i + 1], i)
        ):
            out.append(f'### {bold_match.group(1).strip()}')
            i += 1
            continue

        # Promote standalone heading-like lines to ### (skip inside tables/code)
        if (
            line.strip()
            and is_standalone(lines, i)
            and is_section_heading(line)
            and not in_html_table(lines[: i + 1], i)
            and not in_code_fence(lines[: i + 1], i)
        ):
            out.append(f'### {line.strip()}')
            i += 1
            continue

        out.append(line)
        i += 1

    # Collapse multiple blank lines
    result: list[str] = []
    blank = False
    for ln in out:
        if ln.strip() == '':
            if blank:
                continue
            blank = True
        else:
            blank = False
        result.append(ln)
    return '\n'.join(result).rstrip() + '\n'


def split_frontmatter(text: str) -> tuple[str, str]:
    """Return (frontmatter_block_with_delims, body)."""
    if not text.startswith('---\n'):
        return '', text
    end = text.find('\n---\n', 4)
    if end < 0:
        return '', text
    fm = text[: end + 5]  # include trailing '---\n'
    body = text[end + 5 :]
    return fm, body


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit('usage: promote_headings.py SRC_MD_DIR DST_QMD_DIR')
    src_dir = pathlib.Path(sys.argv[1])
    dst_dir = pathlib.Path(sys.argv[2])

    md_files = sorted(src_dir.glob('*.md'))
    qmd_files = sorted(dst_dir.glob('[0-9][0-9]-*.qmd'))
    if len(md_files) != len(qmd_files):
        sys.exit(f'mismatch: {len(md_files)} .md vs {len(qmd_files)} .qmd files')

    # Match by filename-prefix (sorted order is: alphabetical for .md,
    # numerical-prefix for .qmd) — read existing .qmd frontmatter, identify the
    # source-document field, and pair from that.
    qmd_by_source: dict[str, pathlib.Path] = {}
    for q in qmd_files:
        text = q.read_text(encoding='utf-8')
        m = re.search(r'^source-document:\s*"([^"]+)"', text, re.M)
        if m:
            qmd_by_source[m.group(1)] = q

    for md in md_files:
        q = qmd_by_source.get(md.name)
        if q is None:
            print(f'  SKIP (no qmd match): {md.name}', file=sys.stderr)
            continue
        existing = q.read_text(encoding='utf-8')
        fm, _old_body = split_frontmatter(existing)
        new_body = promote(md.read_text(encoding='utf-8'))
        out_text = fm + '\n' + new_body
        q.write_text(out_text, encoding='utf-8')
        print(f'  REWROTE: {q.name}  (body {len(new_body):,} chars)')


if __name__ == '__main__':
    main()
