#!/usr/bin/env python3
"""Rebuild src/uiao/rules/ksi/index.yaml from the rule files on disk.

The index is a *derived* artifact: every entry is read from the rule file it
points at, so the index can never disagree with the library (the previous
hand-maintained index drifted in both directions — it listed rules that had
been removed and missed four whole category directories).

Usage:
    python scripts/rebuild_ksi_index.py           # rewrite the index
    python scripts/rebuild_ksi_index.py --check   # exit 1 if the committed
                                                  # index differs (CI gate)

Output is deterministic (sorted by ksi_id, no timestamps), so --check is a
pure regen-and-diff.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
KSI_ROOT = REPO_ROOT / "src" / "uiao" / "rules" / "ksi"
INDEX_PATH = KSI_ROOT / "index.yaml"

#: Library metadata files that live under rules/ksi/ but are not rules.
NON_RULE_FILES = {"index.yaml", "ksi_schema.yaml", "uiao-control-to-ksi-mapping.yaml"}

_FAMILY_FROM_ID = re.compile(r"^KSI-([A-Z]{2})-\d+$")


def _rule_files() -> list[Path]:
    return sorted(p for p in KSI_ROOT.rglob("*.yaml") if p.name not in NON_RULE_FILES)


def _controls(rule: dict[str, Any]) -> list[str]:
    """The rule's control list under either dialect (controls / related_controls)."""
    for key in ("controls", "related_controls"):
        value = rule.get(key)
        if isinstance(value, list):
            return [str(c) for c in value]
    return []


def _family(rule: dict[str, Any]) -> str | None:
    declared = rule.get("family")
    if isinstance(declared, str) and declared.strip():
        return declared.strip()
    match = _FAMILY_FROM_ID.match(str(rule.get("ksi_id", "")))
    if match:
        return match.group(1)
    return None


def build_index() -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    seen: dict[str, Path] = {}
    for path in _rule_files():
        rule = yaml.safe_load(path.read_text(encoding="utf-8"))
        ksi_id = str(rule["ksi_id"])
        if ksi_id in seen:
            raise SystemExit(f"duplicate ksi_id {ksi_id!r}: {seen[ksi_id]} and {path}")
        seen[ksi_id] = path
        entry: dict[str, Any] = {
            "ksi_id": ksi_id,
            "title": str(rule.get("title", "")),
            "category": str(rule.get("category", path.parent.name)),
        }
        family = _family(rule)
        if family:
            entry["family"] = family
        severity = rule.get("severity")
        if severity:
            entry["severity"] = str(severity)
        entry["control_count"] = len(_controls(rule))
        entry["path"] = path.relative_to(REPO_ROOT / "src" / "uiao").as_posix()
        entry["enabled"] = bool(rule.get("enabled", False))
        entries.append(entry)

    entries.sort(key=lambda e: e["ksi_id"])
    categories: dict[str, int] = {}
    for entry in entries:
        categories[entry["category"]] = categories.get(entry["category"], 0) + 1

    return {
        "version": "2.0",
        "description": (
            "UIAO KSI rule-library index — DERIVED from the rule files by "
            "scripts/rebuild_ksi_index.py; do not hand-edit (CI regen-and-diff "
            "gate). This is the UIAO-native indicator catalog keyed to NIST "
            "800-53 families, not the official FedRAMP 20x KSI taxonomy "
            "(KSI-CNA/IAM/MLA/…, see uiao.models.fedramp)."
        ),
        "stats": {
            "total_ksis": len(entries),
            "enabled": sum(1 for e in entries if e["enabled"]),
            "categories": dict(sorted(categories.items())),
        },
        "ksis": entries,
    }


def render() -> str:
    return yaml.safe_dump(build_index(), sort_keys=False, allow_unicode=True, width=100)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if the committed index differs from the regenerated one",
    )
    args = parser.parse_args(argv)

    fresh = render()
    if args.check:
        committed = INDEX_PATH.read_text(encoding="utf-8") if INDEX_PATH.exists() else ""
        if committed != fresh:
            sys.stderr.write(
                "rules/ksi/index.yaml is out of sync with the rule files on disk.\n"
                "Regenerate it: python scripts/rebuild_ksi_index.py\n"
            )
            return 1
        print(f"index in sync: {build_index()['stats']['total_ksis']} rules")
        return 0

    INDEX_PATH.write_text(fresh, encoding="utf-8")
    stats = build_index()["stats"]
    print(f"wrote {INDEX_PATH} — {stats['total_ksis']} rules, {len(stats['categories'])} categories")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
