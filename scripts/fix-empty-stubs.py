#!/usr/bin/env python3
"""
fix-empty-stubs.py  —  Add frontmatter to all 0-byte .qmd files
under docs/customer-documents/.

Run from repo root:
    python scripts/fix-empty-stubs.py

Safe to re-run: skips files that already have content.
"""

import sys
from pathlib import Path
from datetime import date

CD = Path("docs/customer-documents")
if not CD.exists():
    print(f"ERROR: {CD} not found. Run from repo root.", file=sys.stderr)
    sys.exit(1)

TODAY = date.today().isoformat()
fixed = 0

for qmd in sorted(CD.rglob("*.qmd")):
    if qmd.stat().st_size > 0:
        continue
    stem = qmd.stem.replace("-", " ").replace("_", " ").title()
    family = qmd.parent.name
    rel = qmd.relative_to(CD)

    content = f"""---
title: "{stem}"
subtitle: "UIAO Customer Documents"
doc-type: stub
audience: [Customer, Technical]
classification: Controlled
boundary: GCC-Moderate
family: {family}
status: Stub
repo-path: docs/customer-documents/{rel.as_posix()}
created-at: {TODAY}
updated-at: {TODAY}
---

# {stem}

::: {{{{.callout-note}}}}
## Under Development
This document is a placeholder.
Content will be populated from canonical sources.
:::
"""
    qmd.write_text(content, newline="\n")
    print(f"  Fixed: {rel}")
    fixed += 1

print(f"\nDone. Fixed {fixed} files.")
