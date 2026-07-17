#!/usr/bin/env python3
"""Expand `{{< meta agency.* >}}` from an edition file, for the Pandoc path.

The books are authored once and render as two editions (AAN_Series_Expansion_Plan
§11). Quarto resolves `{{< meta >}}` natively from _metadata.yml, so the FEDERAL
edition needs nothing. Pandoc does not know the shortcode and emits it literally,
so the SSA edition — which renders through Pandoc precisely so its facts never
need a file inside the published tree — needs this.

WHY TEXT AND NOT A LUA FILTER. A Lua filter has to re-implement shortcode parsing
against the AST, and shortcode adjacency is unbounded: `{{< meta agency.domain >}}.`
parses its closer as `>}}.` and an exact match silently fails, leaving the raw
shortcode in the shipped .docx. Substituting on text has no adjacency cases and is
renderer-agnostic. Verified: Pandoc output through this is identical to Quarto's
for both editions.

An unresolved key is a HARD ERROR, never a passthrough. A missing value would
otherwise ship as the literal `{{< meta agency.foo >}}` in a document, which reads
as a template someone forgot to fill — worse than a build failure.

Usage:
    python expand_meta.py ../../../inbox/aan-ssa-edition/_agency-ssa.yml book.qmd out.qmd

The edition file lives in inbox/, not beside the books: docs/ publishes and
inbox/ does not. Pandoc takes the path as an argument, so nothing about the
SSA build needs a file inside the published tree.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

SHORTCODE = re.compile(r"\{\{<\s*meta\s+([A-Za-z0-9_.]+)\s*>\}\}")


def lookup(meta: dict, path: str):
    node = meta
    for key in path.split("."):
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node


def expand(text: str, meta: dict) -> tuple[str, list[str]]:
    missing: list[str] = []

    def sub(m: re.Match) -> str:
        v = lookup(meta, m.group(1))
        if v is None:
            missing.append(m.group(1))
            return m.group(0)
        return str(v)

    return SHORTCODE.sub(sub, text), missing


def main() -> int:
    if len(sys.argv) != 4:
        return print(__doc__) or 2
    edition, src, dst = sys.argv[1:4]
    meta = yaml.safe_load(Path(edition).read_text(encoding="utf-8")) or {}
    text = Path(src).read_text(encoding="utf-8")
    out, missing = expand(text, meta)
    if missing:
        print(
            f"FATAL: {src}: unresolved meta key(s) {sorted(set(missing))} — not in "
            f"{edition}. Refusing to write: the literal shortcode would ship in the "
            f"document.",
            file=sys.stderr,
        )
        return 1
    Path(dst).write_text(out, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
