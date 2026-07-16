#!/usr/bin/env python3
"""No autonomous write to the estate without an approved decision behind it.

ADR-092 s4: the federal default production ceiling is L3 -- a human approves
before anything changes the estate. L4 (autonomous) is permitted for an operation
class ONLY when all five conditions hold; condition 1 is that the class is
enumerated in a Governance-Plane-approved decision (an ADR or a board record).

`approval: automated` on an item that WRITES to the estate is an L4 claim. Before
this gate, four such items existed (appreg.credential.rotate, saas.credential.rotate,
saas.leaver, saas.identifier) with no decision behind any of them -- and the only
written justification pointed at an "L4 note" that did not exist. Nothing caught
it, because nothing was looking.

The rule, machine-checked: every `approval: automated` item must declare which it
is --

    "estate_write": false        it reads/records; it changes nothing in the
                                 estate, so no L3 question arises. Reading is not
                                 actuating.

    "l4_adr": "ADR-NNN"          it writes autonomously AND a Governance-Plane
                                 decision enumerates the class (condition 1). The
                                 ADR must exist on disk.

An automated item that declares neither is an undeclared L4 exceedance and fails.

Note what this gate does NOT do: it cannot check conditions 2-5 (blast radius,
rollback, a clean dry-run record over an observation window, halt_on_critical).
Those need human judgment and operational evidence. Naming an ADR here asserts
that a human checked them -- it does not prove it. This gate makes the claim
explicit and attributable; it does not make it true.

Usage:
    python check_l3_ceiling.py     # gate; exit 1 on any undeclared exceedance
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ADR_DIR = HERE.parents[2] / "src" / "uiao" / "canon" / "adr"

# Map discovery must match check_actuator_coverage.py / validate_day2_control_maps.py.
# A gate that globs fewer maps than its siblings is how the last blind spot happened.
MAP_GLOBS = [
    (HERE, "*-control-map.json"),
    (HERE.parent / "x_ssa_fed_compliance" / "data", "control-map.json"),
]


def control_maps() -> list[Path]:
    found: list[Path] = []
    for base, pattern in MAP_GLOBS:
        found.extend(sorted(base.glob(pattern)))
    return found


def items(path: Path):
    d = json.loads(path.read_text(encoding="utf-8"))
    cat = d.get("catalog", d)
    for k, v in cat.items():
        if isinstance(v, dict) and v.get("control"):
            yield k, v


def adr_exists(ref: str) -> bool:
    stem = ref.strip().lower().replace("adr-", "")
    return any(ADR_DIR.glob(f"adr-{stem}*.md")) if ADR_DIR.is_dir() else False


def main() -> int:
    problems: list[str] = []
    n_auto = n_read = n_l4 = 0

    for m in control_maps():
        lane = m.name.replace("-control-map.json", "")
        if lane == "control-map.json":
            lane = m.parent.parent.name
        for key, v in items(m):
            deferred = v.get("l4_deferred")
            automated = v.get("approval") == "automated"

            # A deferral and an autonomous claim are contradictory: one says "a
            # human approves until we earn L4", the other says "no human does".
            if deferred and automated:
                problems.append(
                    f"  {lane}/{key}: carries l4_deferred but is still approval:automated "
                    f"— the deferral says a human approves; the approval says none does"
                )
                continue
            if not automated:
                continue

            n_auto += 1
            if v.get("estate_write") is False:
                n_read += 1
                continue
            adr = v.get("l4_adr")
            if not adr:
                problems.append(
                    f"  {lane}/{key}: control {v.get('control')} is approval:automated with "
                    f"neither 'estate_write': false nor an 'l4_adr' — an autonomous estate "
                    f"write above the ADR-092 federal L3 ceiling, with no decision behind it"
                )
                continue
            n_l4 += 1
            if not adr_exists(adr):
                problems.append(
                    f"  {lane}/{key}: l4_adr names {adr!r} but no such ADR exists on disk — "
                    f"an L4 claim citing a decision that cannot be read is the defect this "
                    f"gate was written for"
                )

    print("Day-2 L3 ceiling (ADR-092 s4)")
    print("=" * 68)
    print(
        f"automated items: {n_auto} | declared reads/records: {n_read} | "
        f"enumerated L4 writes: {n_l4}"
    )
    if problems:
        print(f"\nFAIL — {len(problems)} undeclared exceedance(s):")
        print("\n".join(problems))
        return 1
    print(
        "\nOK — every autonomous item either changes nothing in the estate, or names "
        "a Governance-Plane decision that enumerates it."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
