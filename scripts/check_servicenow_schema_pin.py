#!/usr/bin/env python3
"""Check the ServiceNow deployment contract pin (UIAO_211).

The pin has two sides:

* **Assertion side** — ``src/uiao/canon/data/servicenow/expected-schema.yaml``:
  every table and column UIAO code depends on, with the call site that proves
  the dependency.
* **Evidence side** — a ``sys_dictionary`` / ``sys_db_object`` export from the
  target instance, committed under ``.../servicenow/deployment/``.

This script enforces three things:

1. **Structure** — the assertion file is internally coherent: required keys
   present, every ``conflict:`` id resolves to an entry under ``unresolved``,
   no duplicate column names within a table.
2. **Code agreement** — every custom column the assertion file names actually
   appears in the source file its ``code-ref`` points at. This catches the
   assertion side drifting away from the code it claims to describe, and it
   runs today, with no instance access.
3. **Instance agreement** — when an export exists, every expected column is
   present in it, and every UIAO-looking column in the export is accounted
   for. With no export this is reported as pending, not failed: the export is
   an activation gate in UIAO_211 §4, not a precondition for the pin landing.

Exit 0 when everything checked passes; 1 on any failure. ``--strict`` also
fails when the export is missing, for use once the export has landed and the
gate should hold the line.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any

import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "src" / "uiao" / "canon" / "data" / "servicenow"
EXPECTED_PATH = DATA_DIR / "expected-schema.yaml"
DEPLOYMENT_DIR = DATA_DIR / "deployment"

REQUIRED_TOP_KEYS = {"schema-version", "registry-class", "updated", "instance", "tables"}
REQUIRED_TABLE_KEYS = {"name", "kind", "access", "used-by"}
CODE_REF_RE = re.compile(r"^(?P<path>[^:]+)(?::(?P<line>\d+))?$")


def _load_expected() -> dict[str, Any]:
    if not EXPECTED_PATH.exists():
        raise SystemExit(f"missing assertion file: {EXPECTED_PATH.relative_to(REPO_ROOT)}")
    return yaml.safe_load(EXPECTED_PATH.read_text(encoding="utf-8")) or {}


def _find_export() -> pathlib.Path | None:
    """Return the newest committed sys_dictionary export, or None."""
    if not DEPLOYMENT_DIR.is_dir():
        return None
    candidates = sorted(DEPLOYMENT_DIR.glob("sys-dictionary*.json"))
    return candidates[-1] if candidates else None


def check_structure(doc: dict[str, Any]) -> list[str]:
    """Validate the assertion file's own coherence."""
    failures: list[str] = []

    missing = REQUIRED_TOP_KEYS - set(doc)
    if missing:
        failures.append(f"expected-schema.yaml missing top-level keys: {sorted(missing)}")

    unresolved_ids = {u.get("id") for u in doc.get("unresolved", []) or []}
    seen_tables: set[str] = set()

    for table in doc.get("tables", []) or []:
        name = table.get("name", "<unnamed>")
        table_missing = REQUIRED_TABLE_KEYS - set(table)
        if table_missing:
            failures.append(f"table {name}: missing keys {sorted(table_missing)}")
        if name in seen_tables:
            failures.append(f"table {name}: duplicate table entry")
        seen_tables.add(name)

        seen_columns: set[str] = set()
        for col in table.get("custom-columns", []) or []:
            col_name = col.get("name", "<unnamed>")
            if col_name in seen_columns:
                failures.append(f"table {name}: duplicate column {col_name}")
            seen_columns.add(col_name)
            if "code-ref" not in col:
                failures.append(f"table {name}, column {col_name}: no code-ref")
            conflict = col.get("conflict")
            if conflict and conflict not in unresolved_ids:
                failures.append(f"table {name}, column {col_name}: conflict '{conflict}' has no entry under unresolved")

    for entry in doc.get("unresolved", []) or []:
        for key in ("id", "severity", "summary", "consequence", "resolution-requires"):
            if key not in entry:
                failures.append(f"unresolved {entry.get('id', '<unnamed>')}: missing '{key}'")

    return failures


def check_code_agreement(doc: dict[str, Any]) -> list[str]:
    """Every asserted column must appear in the source file it cites."""
    failures: list[str] = []

    for table in doc.get("tables", []) or []:
        table_name = table.get("name", "<unnamed>")

        for ref in table.get("used-by", []) or []:
            src = REPO_ROOT / ref.split("#")[0].strip()
            if not src.exists():
                failures.append(f"table {table_name}: used-by path does not exist: {ref}")

        for col in table.get("custom-columns", []) or []:
            col_name = col.get("name")
            raw_ref = col.get("code-ref")
            if not (col_name and raw_ref):
                continue
            m = CODE_REF_RE.match(str(raw_ref))
            if not m:
                failures.append(f"column {col_name}: unparseable code-ref '{raw_ref}'")
                continue
            src = REPO_ROOT / m.group("path")
            if not src.exists():
                failures.append(f"column {col_name}: code-ref file does not exist: {raw_ref}")
                continue
            text = src.read_text(encoding="utf-8", errors="replace")
            if col_name not in text:
                failures.append(
                    f"column {col_name}: not found in {m.group('path')} — "
                    f"the assertion file has drifted from the code it cites"
                )

    return failures


def check_instance_agreement(doc: dict[str, Any], export_path: pathlib.Path) -> list[str]:
    """Compare asserted columns against a committed sys_dictionary export.

    The export is expected to be a JSON list of ServiceNow ``sys_dictionary``
    records, i.e. objects carrying at least ``name`` (the table) and
    ``element`` (the column), which is the shape the Table API returns.
    """
    failures: list[str] = []

    try:
        raw = json.loads(export_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"export {export_path.name}: not valid JSON — {exc}"]

    records = raw.get("result", raw) if isinstance(raw, dict) else raw
    if not isinstance(records, list):
        return [f"export {export_path.name}: expected a list of sys_dictionary records"]

    present: set[tuple[str, str]] = set()
    for rec in records:
        if isinstance(rec, dict) and rec.get("name") and rec.get("element"):
            present.add((str(rec["name"]), str(rec["element"])))

    asserted: set[tuple[str, str]] = set()
    for table in doc.get("tables", []) or []:
        table_name = str(table.get("name"))
        for col in table.get("custom-columns", []) or []:
            asserted.add((table_name, str(col.get("name"))))

    for table_name, col_name in sorted(asserted - present):
        failures.append(f"{table_name}.{col_name}: asserted by UIAO code but absent from the instance export")

    uiao_like = {(t, c) for (t, c) in present if "uiao" in c.lower()}
    for table_name, col_name in sorted(uiao_like - asserted):
        failures.append(f"{table_name}.{col_name}: present on the instance but not asserted by any UIAO code path")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Also fail when no deployment export is present (use once the export has landed).",
    )
    args = parser.parse_args()

    doc = _load_expected()
    failures: list[str] = []
    failures += check_structure(doc)
    failures += check_code_agreement(doc)

    export = _find_export()
    if export is not None:
        failures += check_instance_agreement(doc, export)

    table_count = len(doc.get("tables", []) or [])
    column_count = sum(len(t.get("custom-columns", []) or []) for t in doc.get("tables", []) or [])
    unresolved = doc.get("unresolved", []) or []

    print(f"tables asserted:   {table_count}")
    print(f"columns asserted:  {column_count}")
    print(f"unresolved items:  {len(unresolved)}")
    for entry in unresolved:
        print(f"  - [{entry.get('severity', '?')}] {entry.get('id')}")

    if export is None:
        rel = DEPLOYMENT_DIR.relative_to(REPO_ROOT)
        print(f"instance export:   NOT PRESENT ({rel}/) — instance agreement pending")
        if args.strict:
            failures.append(
                "no deployment export found and --strict was requested; see UIAO_211 §4 for the required artifacts"
            )
    else:
        print(f"instance export:   {export.relative_to(REPO_ROOT)}")

    if failures:
        print("\nFAILURES:", file=sys.stderr)
        for line in failures:
            print(f"  - {line}", file=sys.stderr)
        return 1

    print("\nOK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
