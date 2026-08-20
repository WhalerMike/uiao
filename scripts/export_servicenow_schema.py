#!/usr/bin/env python3
"""Take the ServiceNow deployment export required by UIAO_211 §4.

Reads ``sys_dictionary`` and ``sys_db_object`` for the tables UIAO depends on,
writes them under ``src/uiao/canon/data/servicenow/deployment/``, and records
each artifact's SHA-256 in that directory's export log.

The host is resolved through ``ServiceNowCollector`` rather than built here,
so this script and the adapters can never disagree about which cloud they are
talking to — the defect PR #1436 fixed. Credentials come from the environment
and are never accepted as arguments, so they cannot land in shell history:

    SERVICENOW_INSTANCE   instance name (host is <instance>.servicenowservices.com)
    SERVICENOW_TOKEN      OAuth bearer token
    SERVICENOW_BASE_URL   optional; full base URL, overrides the two above
    SERVICENOW_DOMAIN     optional; overrides the GCC domain default

The export is **configuration inventory only**. The field lists below are
fixed, not user-supplied, so no record data can be pulled through this path
even by accident.

Usage:
    python scripts/export_servicenow_schema.py --env prod
    python scripts/export_servicenow_schema.py --env prod --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import sys
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from uiao.collectors.servicenow_collector import ServiceNowCollector  # noqa: E402

DEPLOYMENT_DIR = REPO_ROOT / "src" / "uiao" / "canon" / "data" / "servicenow" / "deployment"
EXPECTED_PATH = REPO_ROOT / "src" / "uiao" / "canon" / "data" / "servicenow" / "expected-schema.yaml"

LOG_HEADER = "| Artifact | SHA-256 | Instance | Exported | Operator |"
LOG_PLACEHOLDER = "| *(none yet)* | — | — | — | — |"


def tables_from_expected() -> list[str]:
    """Read the table list from the assertion side, so the two cannot drift."""
    import yaml

    doc = yaml.safe_load(EXPECTED_PATH.read_text(encoding="utf-8")) or {}
    return [str(t["name"]) for t in doc.get("tables", []) or [] if t.get("name")]


def build_jobs(tables: list[str]) -> list[dict[str, Any]]:
    joined = ",".join(tables)
    return [
        {
            "artifact": "sys-dictionary",
            "table": "sys_dictionary",
            "query": f"nameIN{joined}^elementISNOTEMPTY",
            "fields": "name,element,internal_type,column_label,active,sys_scope.scope",
            "limit": 2000,
        },
        {
            "artifact": "sys-db-object",
            "table": "sys_db_object",
            "query": f"nameIN{joined}",
            "fields": "name,label,super_class,sys_scope.scope",
            "limit": 200,
        },
    ]


def _sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rel(path: pathlib.Path) -> str:
    """Repo-relative for display, absolute when the path sits outside the repo."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def update_export_log(entries: list[tuple[str, str]], instance: str, exported: str, operator: str) -> None:
    """Replace the placeholder row in the deployment README with real rows."""
    readme = DEPLOYMENT_DIR / "README.md"
    if not readme.exists():
        return
    text = readme.read_text(encoding="utf-8")
    rows = "\n".join(f"| `{name}` | `{digest}` | {instance} | {exported} | {operator} |" for name, digest in entries)
    if LOG_PLACEHOLDER in text:
        text = text.replace(LOG_PLACEHOLDER, rows)
    elif LOG_HEADER in text:
        text = text.replace(LOG_HEADER, LOG_HEADER, 1).rstrip() + "\n" + rows + "\n"
    readme.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env", default="prod", help="Instance tag for the filenames (default: prod).")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the requests that would be made and exit without calling out.",
    )
    parser.add_argument("--operator", default="", help="Name recorded in the export log.")
    args = parser.parse_args()

    collector = ServiceNowCollector()
    tables = tables_from_expected()
    jobs = build_jobs(tables)

    # The collector falls back to a literal "your-instance" placeholder when
    # nothing is configured. Never print that as if it were a host — a
    # copy-pasteable fake URL is how the defect in #1436 travelled.
    configured = bool(os.environ.get("SERVICENOW_INSTANCE") or os.environ.get("SERVICENOW_BASE_URL"))
    base = collector.base_url if configured else "https://<instance>.servicenowservices.com"

    print(f"base URL:  {base}" + ("" if configured else "   [NOT CONFIGURED]"))
    print(f"tables:    {len(tables)} ({', '.join(tables)})")

    for job in jobs:
        dest = DEPLOYMENT_DIR / f"{job['artifact']}.{args.env}.json"
        print(f"\n  GET {base}/api/now/table/{job['table']}")
        print(f"      sysparm_query={job['query']}")
        print(f"      sysparm_fields={job['fields']}")
        print(f"      -> {_rel(dest)}")

    if args.dry_run:
        print("\ndry run — nothing fetched, nothing written")
        return 0

    # Fail closed rather than dial a placeholder host or write an empty export.
    if not os.environ.get("SERVICENOW_INSTANCE") and not os.environ.get("SERVICENOW_BASE_URL"):
        print(
            "\nSERVICENOW_INSTANCE (or SERVICENOW_BASE_URL) is not set — refusing to "
            "construct a host. See UIAO_211 §4.",
            file=sys.stderr,
        )
        return 1
    if not os.environ.get("SERVICENOW_TOKEN"):
        print(
            "\nSERVICENOW_TOKEN is not set — the collector would return an empty "
            "scaffold and this would write an export that falsely reports every "
            "column missing.",
            file=sys.stderr,
        )
        return 1

    DEPLOYMENT_DIR.mkdir(parents=True, exist_ok=True)
    written: list[tuple[str, str]] = []

    for job in jobs:
        payload = collector.fetch_relevant_records(
            table=job["table"],
            sysparm_query=job["query"],
            sysparm_fields=job["fields"],
            sysparm_limit=job["limit"],
        )
        records = payload.get("result", [])
        if not records:
            print(
                f"\n{job['table']}: returned zero records — not writing an empty export. "
                f"Check the account's read access to the dictionary.",
                file=sys.stderr,
            )
            return 1

        dest = DEPLOYMENT_DIR / f"{job['artifact']}.{args.env}.json"
        dest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        digest = _sha256(dest)
        written.append((dest.name, digest))
        print(f"\n{_rel(dest)}  ({len(records)} records)")
        print(f"  sha256 {digest}")

    from datetime import datetime, timezone

    exported = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    update_export_log(written, args.env, exported, args.operator or "—")

    print("\nExport complete. Next:")
    print("  python scripts/check_servicenow_schema_pin.py")
    print("  resolve `control-id-prefix` in expected-schema.yaml using the dictionary result")
    return 0


if __name__ == "__main__":
    sys.exit(main())
