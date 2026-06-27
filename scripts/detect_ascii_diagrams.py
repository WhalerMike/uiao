#!/usr/bin/env python3
"""Detect ASCII *architecture* diagrams across docs/ and src/uiao/canon/.

A real architecture diagram is a fenced code block rich in box-drawing
corners (``┌┐└┘``) and connectors/arrows — as opposed to a directory tree
(``├──`` / ``└──`` dominated, no corners) or a code-comment separator. The
detector exists so those diagrams can be converted to house-style SVG
figures (ADR-093); it reports file, line range, corner/arrow counts, and a
short preview.

Usage::

    python scripts/detect_ascii_diagrams.py
"""

from __future__ import annotations

from pathlib import Path

ROOTS = [Path("docs"), Path("src/uiao/canon")]
SKIP = (
    "image-prompts",
    "IMAGE-PROMPTS",
    ".manifest",
    "generate-series",
    "_site",
    "_freeze",
    ".quarto",
    "node_modules",
)
CORNERS = set("┌┐└┘╔╗╚╝")
ARROWS = set("▶◀►◄▲▼→←↓↑⟶")
TREE = set("├└")  # tree connectors
CODE_LANGS = {"powershell", "ps1", "bash", "sh", "python", "py", "yaml", "json", "sql"}


def scan(path: Path) -> list[tuple[int, int, int, int, list[str]]]:
    """Return (start, end, corners, arrows, preview) for each arch-diagram block."""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []

    out: list[tuple[int, int, int, int, list[str]]] = []
    in_fence = False
    start = 0
    buf: list[str] = []
    lang = ""
    for i, line in enumerate(lines, 1):
        stripped = line.lstrip()
        if stripped.startswith("```"):
            if not in_fence:
                in_fence, start, buf, lang = True, i, [], stripped[3:].strip().lower()
            else:
                corners = sum(ch in CORNERS for row in buf for ch in row)
                arrows = sum(ch in ARROWS for row in buf for ch in row)
                tree = sum(ch in TREE for row in buf for ch in row)
                is_code = lang in CODE_LANGS
                if corners >= 4 and (arrows >= 1 or corners >= 8) and tree < corners and not is_code:
                    out.append((start, i, corners, arrows, buf[:3]))
                in_fence = False
        elif in_fence:
            buf.append(line)
    return out


def main() -> int:
    hits: list[tuple[Path, int, int, int, int, list[str]]] = []
    for root in ROOTS:
        for ext in ("*.md", "*.qmd"):
            for path in root.rglob(ext):
                if any(skip in str(path) for skip in SKIP):
                    continue
                for start, end, corners, arrows, preview in scan(path):
                    hits.append((path, start, end, corners, arrows, preview))

    hits.sort(key=lambda h: (-h[4], str(h[0])))
    print(f"REAL architecture diagrams: {len(hits)}\n")
    for path, start, end, corners, arrows, preview in hits:
        print(f"{path}:{start}-{end}  (corners={corners} arrows={arrows})")
        for row in preview:
            print(f"    | {row[:72]}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
