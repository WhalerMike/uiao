#!/usr/bin/env python3
"""Validate the Vol IX ServiceNow Day-2 control maps against the SSOTs.

The `servicenow-day2/*-control-map.json` files declare, per governed catalog
item, the NIST control it satisfies, its KSI theme, and its evidence slot. Those
files describe themselves as a "projection of aan-compliance-spine.yml,
CI-checked against it" — this is the check that makes that claim true.

It enforces, for every catalog item in every control map:
  - boundary == "gcc-moderate" (series scope);
  - required fields present (title, control, task_type, approval, actuation,
    ksi, slot);
  - every `slot` is a real evidence slot declared in aan-compliance-spine.yml;
  - every `ksi` theme is a real CR26 theme in the in-repo FedRAMP CR26 catalog;
  - every `control` looks like a NIST SP 800-53 control id (e.g. AC-2, SC-7(3)).

Usage:
    python validate_day2_control_maps.py            # validate (exit 1 on any error)
    python validate_day2_control_maps.py --check     # alias for the same
"""

from __future__ import annotations

import glob
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML required: pip install pyyaml")

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SPINE = HERE / "aan-compliance-spine.yml"
MAPS = sorted((HERE / "servicenow-day2").glob("*-control-map.json"))

REQUIRED = {"title", "control", "task_type", "approval", "actuation", "ksi", "slot"}
CONTROL_RE = re.compile(r"^[A-Z]{2}-\d+(\(\d+\))?$")


def valid_slots() -> set[str]:
    return set(yaml.safe_load(SPINE.read_text(encoding="utf-8"))["slots"])


def valid_themes() -> set[str]:
    matches = sorted(
        REPO.glob(
            "src/uiao/canon/compliance/reference/fedramp-cr26/snapshot/*/"
            "catalog/json/FedRAMP_CR26_catalog.json"
        )
    )
    if not matches:
        sys.exit("CR26 catalog not found — cannot validate KSI themes")
    cat = json.loads(matches[0].read_text(encoding="utf-8"))["catalog"]
    themes = set()

    def walk(groups):
        for g in groups:
            if g.get("id", "").startswith("KSI-"):
                themes.add(g["id"])
            walk(g.get("groups", []) or [])

    walk(cat.get("groups", []) or [])
    return themes


def validate() -> list[str]:
    slots, themes = valid_slots(), valid_themes()
    errors: list[str] = []
    if not MAPS:
        return ["no control maps found under servicenow-day2/"]
    for m in MAPS:
        d = json.loads(m.read_text(encoding="utf-8"))
        name = m.name
        if d.get("boundary") != "gcc-moderate":
            errors.append(f"{name}: boundary is {d.get('boundary')!r}, expected 'gcc-moderate'")
        for key, item in (d.get("catalog") or {}).items():
            where = f"{name}:{key}"
            missing = REQUIRED - set(item)
            if missing:
                errors.append(f"{where}: missing fields {sorted(missing)}")
                continue
            if item["slot"] not in slots:
                errors.append(f"{where}: slot '{item['slot']}' not in the spine slots")
            for t in item["ksi"]:
                if t not in themes:
                    errors.append(f"{where}: ksi theme '{t}' not a CR26 catalog theme")
            if not CONTROL_RE.match(item["control"]):
                errors.append(f"{where}: control '{item['control']}' is not a NIST control id")
    return errors


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    errors = validate()
    if errors:
        print("DAY-2 CONTROL-MAP DRIFT:", *(f"  {e}" for e in errors), sep="\n")
        return 1
    n = sum(len(json.loads(m.read_text(encoding="utf-8")).get("catalog") or {}) for m in MAPS)
    print(f"OK — {len(MAPS)} day-2 control maps, {n} catalog items, all consistent with the spine.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
