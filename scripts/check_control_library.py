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
  4. Every ``status:`` value is in the OSCAL implementation-status vocabulary.

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

# Legacy schema-B fields. The canonical control schema (schema-A) uses
# narrative / implemented_by / evidence / parameters; these field names are a
# retired second-schema variant and must not reappear (see the control_narrative
# → narrative normalization and the automation → implemented_by/evidence unify).
_LEGACY_FIELDS = {"control_narrative", "responsible_role", "implementation_status", "automation"}

# OSCAL implementation-status vocabulary. narrative_loader._build_oscal_props
# copies ``status`` verbatim into the ``implementation-status`` prop, so any
# value outside this set is emitted into the generated SSP as a non-conformant
# prop. Case matters: OSCAL values are lowercase (a ``status: Implemented``
# drift across the CA/MA/MP/PL/PS/RA families produced exactly that, and went
# unnoticed because nothing validated the field).
_STATUS_VOCAB = {"implemented", "partial", "partially-implemented", "not-implemented", "not-applicable"}


def scan() -> dict:
    idx = yaml.safe_load(INDEX.read_text())
    families = idx.get("families", {})
    rows, mismatches, schema_drift, status_drift = {}, [], [], []
    base = enh = total_files = 0
    for fam, meta in families.items():
        famdir = LIB_DIR / fam
        paths = sorted(famdir.glob("*.yml")) if famdir.is_dir() else []
        files = [p.name for p in paths]
        n = len(files)
        total_files += n
        fam_enh = sum(1 for f in files if "(" in f)
        enh += fam_enh
        base += n - fam_enh
        rows[fam] = {"declared": meta.get("count"), "actual": n}
        if meta.get("count") != n:
            mismatches.append(f"family {fam}: index={meta.get('count')} files={n}")
        # Schema-drift guard: every control must use the canonical schema-A
        # field set. Flag legacy schema-B fields so the control_narrative /
        # automation drift (fixed once) cannot silently return.
        for p in paths:
            try:
                d = yaml.safe_load(p.read_text()) or {}
            except Exception:
                continue
            legacy = _LEGACY_FIELDS & set(d)
            if legacy:
                schema_drift.append(f"{fam}/{p.name}: {', '.join(sorted(legacy))}")
            # Status-vocabulary guard: the value is copied verbatim into the
            # OSCAL implementation-status prop, so an out-of-vocabulary value
            # (including a wrong-case one) reaches the generated SSP.
            status = d.get("status")
            if status is not None and status not in _STATUS_VOCAB:
                status_drift.append(f"{fam}/{p.name}: status={status!r}")

    if idx.get("total_controls") != total_files:
        mismatches.append(f"total_controls: index={idx.get('total_controls')} sum_of_families={total_files}")
    if idx.get("base_controls") != base:
        mismatches.append(f"base_controls: index={idx.get('base_controls')} computed={base}")
    if idx.get("enhancements") != enh:
        mismatches.append(f"enhancements: index={idx.get('enhancements')} computed={enh}")

    if schema_drift:
        mismatches.append(
            f"schema drift: {len(schema_drift)} file(s) use non-canonical "
            f"(schema-B) fields — {', '.join(sorted(_LEGACY_FIELDS))}"
        )

    if status_drift:
        mismatches.append(
            f"status drift: {len(status_drift)} file(s) carry a status outside the "
            f"OSCAL vocabulary — {'|'.join(sorted(_STATUS_VOCAB))}"
        )

    root_legacy = sorted(p.name for p in LIB_DIR.glob("*.yml"))
    return {
        "total_files": total_files,
        "base": base,
        "enhancements": enh,
        "index_total": idx.get("total_controls"),
        "families": rows,
        "root_legacy_files": root_legacy,
        "schema_drift": schema_drift,
        "status_drift": status_drift,
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
        print(f"Schema-drift files       : {len(r['schema_drift'])}")
        for d in r["schema_drift"]:
            print(f"    - {d}")
        print(f"Status-drift files       : {len(r['status_drift'])}")
        for d in r["status_drift"]:
            print(f"    - {d}")
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
