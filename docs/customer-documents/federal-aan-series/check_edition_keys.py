#!/usr/bin/env python3
"""Every `{{< meta agency.* >}}` a book uses must exist in BOTH editions.

The books are authored once and render twice (AAN_Series_Expansion_Plan §11):
the FEDERAL edition from _metadata.yml (Quarto, native shortcode) and the SSA
edition from _agency-ssa.yml (Pandoc, via expand_meta.py). A key present in one
edition and missing from the other does not fail loudly — it produces a document
with a raw `{{< meta agency.foo >}}` sitting in the prose, which reads as a
template someone forgot to fill. Under Quarto it renders as `?var:agency.foo`.
Either way it ships.

  1. USED => DEFINED IN BOTH — a key any book references resolves in both editions.
  2. NO ORPHANS — a key defined in one edition but not the other is a half-built
     substitution waiting to be used.
  3. NO DEAD KEYS — a key defined in both but referenced nowhere is config that
     claims to matter and does not. (Reported, not fatal: a key may be staged
     ahead of the prose that will use it.)

Usage:
    python check_edition_keys.py     # gate; exit 1 on any breach
"""

from __future__ import annotations

import glob
import re
import sys
from pathlib import Path

import yaml


def _repo_root() -> Path:
    """Walk up to the repository root rather than counting directory levels."""
    p = Path(__file__).resolve()
    for cand in [p, *p.parents]:
        if (cand / ".git").exists():
            return cand
    raise SystemExit("repo root not found")


HERE = Path(__file__).resolve().parent
FEDERAL = HERE / "_metadata.yml"
# The SSA edition file lives in inbox/, NOT beside the books. That is the whole
# point: docs/ publishes, inbox/ does not. This gate therefore spans both trees --
# it is the only thing keeping the two editions in sync across that boundary.
SSA = _repo_root() / "inbox" / "aan-ssa-edition" / "_agency-ssa.yml"
SHORTCODE = re.compile(r"\{\{<\s*meta\s+([A-Za-z0-9_.]+)\s*>\}\}")


def flatten(d, prefix=""):
    out = set()
    for k, v in (d or {}).items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out |= flatten(v, key + ".")
        else:
            out.add(key)
    return out


def defined(path: Path) -> set[str]:
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {k for k in flatten(doc) if k.startswith("agency.")}


def main() -> int:
    used: dict[str, list[str]] = {}
    for f in sorted(glob.glob(str(HERE / "Vol_*_Book_*.qmd"))):
        for m in SHORTCODE.finditer(Path(f).read_text(encoding="utf-8")):
            used.setdefault(m.group(1), []).append(Path(f).name)

    fed, ssa = defined(FEDERAL), defined(SSA)
    problems: list[str] = []

    for key, files in sorted(used.items()):
        for label, keys in (("federal (_metadata.yml)", fed), ("SSA (_agency-ssa.yml)", ssa)):
            if key not in keys:
                problems.append(
                    f"  {key!r} is used by {len(files)} book(s) (e.g. {files[0]}) but is "
                    f"not defined in the {label} edition — that edition would ship the raw "
                    f"shortcode in its prose"
                )

    for key in sorted(fed - ssa):
        problems.append(f"  {key!r} is defined in federal but not SSA — half a substitution")
    for key in sorted(ssa - fed):
        problems.append(f"  {key!r} is defined in SSA but not federal — half a substitution")

    dead = sorted((fed & ssa) - set(used))

    print("AAN edition keys")
    print("=" * 68)
    print(f"keys used by books: {len(used)} | federal defines: {len(fed)} | SSA defines: {len(ssa)}")
    if dead:
        print(f"defined but unused ({len(dead)}): {', '.join(dead)}")
    if problems:
        print(f"\nFAIL — {len(problems)} breach(es):")
        print("\n".join(problems))
        return 1
    print("\nOK — every key a book uses resolves in both editions, and neither edition defines a key the other lacks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
