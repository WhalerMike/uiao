#!/usr/bin/env python3
"""Guard published .qmd pages against accidental execution-engine binding.

The Quarto render only runs on push to ``main`` (see ``.github/workflows/
quarto.yml``), so a page that silently acquires a computational engine does not
fail a pull request — it fails the deploy, after merge, and the site stops
publishing until someone reads the render log. That is exactly what happened on
2026-08-21: the site did not deploy for five days.

The trap is in Quarto's own cell-detection regex, which is (verbatim, from
``src/core/pandoc/pandoc-partition.ts``)::

    /^[\\t >]*```+\\s*\\{([a-zA-Z][a-zA-Z0-9_.]*)([^}]*)?\\}\\s*$/gm

``\\s*`` matches newlines, so the opening fence and the ``{...}`` do NOT have to
be on the same line. A perfectly ordinary prose code block whose first content
line happens to be a brace expression::

    ```
    {region: NCR, department: IT, division: CyberOps}
    ```

is therefore read as a code cell in a language called ``region``. Since that is
neither ``ojs`` nor one of Quarto's built-in cell handlers (``mermaid``,
``dot``, …), Quarto binds the whole file to the Jupyter engine, tries to start a
python3 kernel, and dies on a runner that has no Jupyter installed.

This guard replicates that regex and fails on any scanned page that would bind
to a kernel engine without saying so. The fix is normally one line of front
matter — ``engine: markdown`` — which is also the honest declaration for a prose
page. A page that genuinely wants execution should declare ``engine:`` (or
``jupyter:``) explicitly, which satisfies this guard.

Run locally:  python scripts/check_qmd_engine.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Quarto's cell-detection regex, transliterated. Python's ``\s`` matches
# newlines exactly as JavaScript's does, and ``re.M`` matches the ``m`` flag, so
# this reproduces the upstream behaviour including the cross-line match.
CELL_RE = re.compile(
    r"^[\t >]*```+\s*\{([a-zA-Z][a-zA-Z0-9_.]*)([^}]*)?\}\s*$",
    re.MULTILINE,
)

# Languages Quarto renders itself, without starting a kernel. A cell in one of
# these keeps the file on the markdown engine, so it is not a finding.
HANDLER_LANGUAGES = frozenset(
    {
        "mermaid",
        "dot",
        "graphviz",
        "ojs",
        "embed",
        "include",
        "pagebreak",
        "tikz",
        "asciidoc",
        "verbatim",
    }
)

# Front-matter keys that declare an engine deliberately. Any of these means the
# author chose the binding, so the page is out of scope.
ENGINE_DECLARATIONS = ("engine:", "jupyter:", "knitr:", "julia:")

SCAN_GLOB = "docs/**/*.qmd"

ALLOW_MARKER = "qmd-engine-allow"


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def front_matter(text: str) -> str:
    """Return the YAML front matter block, or "" when the file has none."""
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    return text[:end] if end != -1 else ""


def declares_engine(text: str) -> bool:
    fm = front_matter(text)
    return any(line.strip().startswith(key) for line in fm.splitlines() for key in ENGINE_DECLARATIONS)


def scan_text(text: str, rel: str) -> list[str]:
    if declares_engine(text) or ALLOW_MARKER in text:
        return []
    findings: list[str] = []
    for match in CELL_RE.finditer(text):
        language = match.group(1).lower()
        if language in HANDLER_LANGUAGES:
            continue
        line = text[: match.start()].count("\n") + 1
        split = "\n" in match.group(0)
        why = (
            "fence and `{...}` are on separate lines, so this is prose Quarto misreads as a cell"
            if split
            else "declared cell language"
        )
        findings.append(f"{rel}:{line}: binds the file to a kernel engine via language {language!r} — {why}")
    return findings


def main() -> int:
    root = repo_root()
    files = sorted(p for p in root.glob(SCAN_GLOB) if p.is_file())
    findings: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        findings.extend(scan_text(text, path.relative_to(root).as_posix()))

    if findings:
        print(f"qmd engine guard FAILED — {len(findings)} page(s) would start a kernel:\n")
        for finding in findings:
            print(f"  {finding}")
        print(
            "\nAdd `engine: markdown` to the page's front matter (a prose page has no "
            "executable code), or break the `{...}` line so it is not the first line "
            f"of the block. To exempt one file deliberately, add the `{ALLOW_MARKER}` marker."
        )
        return 1

    print(f"qmd engine guard OK — scanned {len(files)} pages; none binds to a kernel engine unintentionally.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
