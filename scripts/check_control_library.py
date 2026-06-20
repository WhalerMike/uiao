#!/usr/bin/env python3
"""Validate the NIST 800-53 control-library against its own index.yaml.

The control-library under ``src/uiao/canon/data/control-library/`` is a
**curated** set of the controls UIAO implements/shares in depth — not an
attempt at the full 323-control FedRAMP Moderate baseline (the SSP, UIAO_185
§3, carries the all-323 control-by-control mapping at summary level). This
checker therefore validates **internal consistency** — that ``index.yaml``
faithfully describes the files on disk — rather than coverage against an
external baseline.

Checks (each a BLOCKING failure when ``--strict``):
  1. Every family directory's ``*.yml`` count matches ``families.<fam>.count``.
  2. ``total_controls`` == sum of family counts.
  3. ``base_controls`` / ``enhancements`` match the filename split
     (enhancements carry ``(N)`` in the name, e.g. ``AC-2(1).yml``).

Loose ``*.yml`` files at the control-library root (the legacy ``control-id``
schema reference controls, e.g. ``SC-8.yml`` / ``IA-2.yml``, exercised by
``tests/test_control_library.py``) are reported informationally — they are a
separate, non-family schema and are intentionally excluded from the family
totals.

Exit codes:
  0  consistent (or advisory mode)
  1  --strict and any mismatch

Usage:
  python scripts/check_control_library.py
  python scripts/check_control_library.py --strict
  python scripts/check_control_library.py --json
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
LIB_DIR = REPO_ROOT / "src" / "uiao" / "canon" / "data" / "control-library"
INDEX = LIB_DIR / "index.yaml"


def scan() -> dict:
    idx = yaml.safe_load(INDEX.read_text())
    families = idx.get("families", {})
    rows, mismatches = {}, []
    base = enh = total_files = 0
    for fam, meta in families.items():
        famdir = LIB_DIR / fam
        files = sorted(p.name for p in famdir.glob("*.yml")) if famdir.is_dir() else []
        n = len(files)
        total_files += n
        fam_enh = sum(1 for f in files if "(" in f)
        enh += fam_enh
        base += n - fam_enh
        rows[fam] = {"declared": meta.get("count"), "actual": n}
        if meta.get("count") != n:
            mismatches.append(f"family {fam}: index={meta.get('count')} files={n}")

    if idx.get("total_controls") != total_files:
        mismatches.append(f"total_controls: index={idx.get('total_controls')} sum_of_families={total_files}")
    if idx.get("base_controls") != base:
        mismatches.append(f"base_controls: index={idx.get('base_controls')} computed={base}")
    if idx.get("enhancements") != enh:
        mismatches.append(f"enhancements: index={idx.get('enhancements')} computed={enh}")

    root_legacy = sorted(p.name for p in LIB_DIR.glob("*.yml"))
    return {
        "total_files": total_files,
        "base": base,
        "enhancements": enh,
        "index_total": idx.get("total_controls"),
        "families": rows,
        "root_legacy_files": root_legacy,
        "mismatches": mismatches,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    ap.add_argument("--strict", action="store_true", help="exit 1 on any mismatch")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = ap.parse_args()

    r = scan()
    if args.json:
        print(json.dumps(r, indent=2))
    else:
        print("UIAO control-library integrity check")
        print("=" * 44)
        print(f"Family controls on disk : {r['total_files']}  (base {r['base']} + enhancements {r['enhancements']})")
        print(f"index.yaml total_controls: {r['index_total']}")
        print(f"Legacy root-schema files : {', '.join(r['root_legacy_files']) or '(none)'}")
        if r["mismatches"]:
            print("\nMISMATCHES:")
            for m in r["mismatches"]:
                print(f"  - {m}")
        else:
            print("\nConsistent: index.yaml matches the files on disk.")

    if r["mismatches"] and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
