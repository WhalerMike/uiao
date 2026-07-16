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
  - every `control` looks like a NIST SP 800-53 control id (e.g. AC-2, SC-7(3));
  - **the map's control set matches the spine's closures for its book** — i.e.
    the map really is the projection it says it is.

That last check was missing until 2026-07-14, which meant the "projection of
aan-compliance-spine.yml, CI-checked against it" claim in every map header was
only partly true: slots and KSI themes were checked, the *projection* was not.
Three of the five lanes had already drifted (see _KNOWN_DELTAS). The check is
blocking for new drift; the pre-existing deltas are listed explicitly so they
are visible and owned rather than silently tolerated.

Usage:
    python validate_day2_control_maps.py            # validate (exit 1 on any error)
    python validate_day2_control_maps.py --check     # alias for the same
    python validate_day2_control_maps.py --strict-projection
                                                    # also fail on _KNOWN_DELTAS
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from pathlib import Path

def _repo_root() -> Path:
    """Walk up to the repository root rather than counting directory levels.

    A hardcoded `parents[N]` encodes this file's depth. That silently broke when
    the corpus moved from inbox/ (depth 2) to docs/customer-documents/ (depth 3):
    the index still resolved, just to the wrong directory. Walking to the .git
    marker survives the next move too.
    """
    p = Path(__file__).resolve()
    for cand in [p, *p.parents]:
        if (cand / ".git").exists():
            return cand
    raise SystemExit("repo root not found (no .git above %s)" % p)


try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML required: pip install pyyaml")

HERE = Path(__file__).resolve().parent
REPO = _repo_root()
SPINE = HERE / "aan-compliance-spine.yml"
# Every ServiceNow scoped-app control map in the AAN corpus: the day-2 lanes
# plus the Vol VII compliance app's map (x_fed_compliance/data/). One gate,
# all apps — a new app's map is covered by adding its glob + MAP_TO_BOOK entry.
MAPS = sorted((HERE / "servicenow-day2").glob("*-control-map.json")) + sorted(
    (HERE / "x_fed_compliance" / "data").glob("control-map.json")
)

REQUIRED = {"title", "control", "task_type", "approval", "actuation", "ksi", "slot"}
CONTROL_RE = re.compile(r"^[A-Z]{2}-\d+(\(\d+\))?$")

# Which book(s) each map projects — a str for one book, a list where an app
# operates several (its control set must equal the UNION of their closures).
# A map with no entry here is not projection-checked; add it when the lane
# gets a book.
MAP_TO_BOOK = {
    "helpdesk-control-map.json": "book-day2-helpdesk",
    "landingzone-control-map.json": "book-day2-landingzone",
    "appreg-control-map.json": "book-day2-appreg",
    "telephony-control-map.json": "book-day2-telephony",
    "saas-control-map.json": "book-sn-saas",
    # x_fed_compliance operates the Book 02/03/04 surfaces
    "control-map.json": ["book-sn-m365", "book-sn-azure", "book-sn-attestation"],
}

# Pre-existing map/spine divergences tolerated as warnings. EMPTY as of
# 2026-07-14: the three deltas found when the projection check was added were
# each resolved with an owner decision the same day —
#   helpdesk AC-3   -> the ca-exception catalog item was right; spine closure ADDED
#   appreg  AC-2    -> the machine-JML request item was right; spine closure ADDED
#   appreg  SC-17   -> appreg.credential.issue REBOUND IA-5(2) -> SC-17 (its note
#                      already cited SC-17; rotate keeps the IA-5(2) bind)
#   telephony AU-2  -> the closure was real but carried by nothing; catalog item
#                      tel.audit.collect ADDED (and a row in Vol IX Book 04)
# With this empty, EVERY map/spine delta is a hard error — do not repopulate it
# to make a red build green; resolve the delta or revert the change that made it.
_KNOWN_DELTAS: dict[str, dict[str, set[str]]] = {}


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


def spine_controls_by_book() -> dict[str, set[str]]:
    spine = yaml.safe_load(SPINE.read_text(encoding="utf-8"))
    out: dict[str, set[str]] = {}
    for c in spine["closures"]:
        out.setdefault(c["book"], set()).add(c["control"])
    return out


def check_projection(name: str, mapped: set[str], strict: bool) -> tuple[list[str], list[str]]:
    """Compare a lane map's control set to its book's spine closures.

    Returns (errors, warnings). A delta listed in _KNOWN_DELTAS is a warning
    unless *strict*; anything else is an error, so new drift cannot land.
    """
    book = MAP_TO_BOOK.get(name)
    if not book:
        return [], []
    books = [book] if isinstance(book, str) else list(book)
    by_book = spine_controls_by_book()
    spine_ctrls: set[str] = set()
    for b in books:
        spine_ctrls |= by_book.get(b, set())
    book = "+".join(books)
    map_only = mapped - spine_ctrls
    spine_only = spine_ctrls - mapped
    known = _KNOWN_DELTAS.get(name, {"map_only": set(), "spine_only": set()})

    errors, warnings = [], []
    for label, actual, allowed in (
        ("in the map but not closed in the spine", map_only, known["map_only"]),
        ("closed in the spine but bound to no catalog item", spine_only, known["spine_only"]),
    ):
        unexpected = actual - allowed
        if unexpected:
            errors.append(f"{name} -> {book}: {sorted(unexpected)} {label}")
        tolerated = actual & allowed
        if tolerated:
            msg = f"{name} -> {book}: {sorted(tolerated)} {label} (pre-existing, see _KNOWN_DELTAS)"
            (errors if strict else warnings).append(msg)
    return errors, warnings


def validate(strict_projection: bool = False) -> tuple[list[str], list[str]]:
    slots, themes = valid_slots(), valid_themes()
    errors: list[str] = []
    warnings: list[str] = []
    if not MAPS:
        return ["no control maps found under servicenow-day2/"], []
    for m in MAPS:
        d = json.loads(m.read_text(encoding="utf-8"))
        name = m.name
        mapped: set[str] = set()
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
            else:
                mapped.add(item["control"])
        perr, pwarn = check_projection(name, mapped, strict_projection)
        errors.extend(perr)
        warnings.extend(pwarn)
    return errors, warnings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    ap.add_argument("--check", action="store_true", help="alias; validation always runs")
    ap.add_argument(
        "--strict-projection",
        action="store_true",
        help="also fail on the pre-existing map/spine deltas in _KNOWN_DELTAS",
    )
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    errors, warnings = validate(strict_projection=args.strict_projection)
    if warnings:
        print("PRE-EXISTING MAP/SPINE DELTAS (not blocking; need an owner decision):",
              *(f"  {w}" for w in warnings), sep="\n")
        print()
    if errors:
        print("DAY-2 CONTROL-MAP DRIFT:", *(f"  {e}" for e in errors), sep="\n")
        return 1
    n = sum(len(json.loads(m.read_text(encoding="utf-8")).get("catalog") or {}) for m in MAPS)
    print(f"OK — {len(MAPS)} day-2 control maps, {n} catalog items, all consistent with the spine.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
