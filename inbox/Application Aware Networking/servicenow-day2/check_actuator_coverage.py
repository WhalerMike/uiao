#!/usr/bin/env python3
"""Every day-2 control-map item must actuate — or say plainly that it cannot.

A control map is a claim: "this catalog item is where control X is closed." The
claim is only worth something if code actually actuates it. Before this gate, 38
of 48 governed items across four lanes had no actuator at all — control claims
with nothing behind them — and nothing said so.

This binds the maps to the code:

  1. DECLARED — every item carries exactly one of
       "actuator":     "ClientName.method"   (it actuates), or
       "actuator_gap": "<reason>"            (it cannot, and here is why)
     An item with neither is a silent claim and fails.

  2. THE METHOD EXISTS — an item naming ClientName.method must resolve to a real
     public method in script-includes/ClientName.js. This catches the drift a
     rename or deletion would otherwise hide until a request failed in a tenant.

  3. A GAP IS A SENTENCE, NOT A SHRUG — an actuator_gap must carry a real reason.

The declared gaps are the actuator backlog for the ServiceNow enforcement
build-out: `python check_actuator_coverage.py --backlog` prints them.

Usage:
    python check_actuator_coverage.py            # gate; exit 1 on any breach
    python check_actuator_coverage.py --backlog  # list the unimplemented items
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT_INCLUDES = HERE / "script-includes"
MIN_REASON = 25  # a gap reason shorter than this is a shrug, not an explanation


def public_methods(client: str) -> set[str] | None:
    """Public methods of a Script Include, or None if the file does not exist."""
    path = SCRIPT_INCLUDES / f"{client}.js"
    if not path.exists():
        return None
    txt = path.read_text(encoding="utf-8")
    return {
        m.group(1)
        for m in re.finditer(r"^\s{4}([A-Za-z_]\w*): function \(", txt, re.M)
        if not m.group(1).startswith("_") and m.group(1) != "initialize"
    }


def items(path: Path):
    d = json.loads(path.read_text(encoding="utf-8"))
    cat = d.get("catalog", d)
    for k, v in cat.items():
        if isinstance(v, dict) and v.get("control"):
            yield k, v


def main() -> int:
    backlog_mode = "--backlog" in sys.argv
    maps = sorted(HERE.glob("*-control-map.json"))
    problems: list[str] = []
    backlog: list[tuple[str, str, str, str]] = []
    n_items = n_act = n_gap = 0
    method_cache: dict[str, set[str] | None] = {}

    for m in maps:
        lane = m.name.replace("-control-map.json", "")
        for key, v in items(m):
            n_items += 1
            act, gap = v.get("actuator"), v.get("actuator_gap")

            # 1. exactly one of the two
            if act and gap:
                problems.append(f"  {lane}/{key}: declares BOTH actuator and actuator_gap")
                continue
            if not act and not gap:
                problems.append(
                    f"  {lane}/{key}: control {v.get('control')} is claimed with no "
                    f"'actuator' and no 'actuator_gap' — a control claim with nothing behind it"
                )
                continue

            if gap:
                n_gap += 1
                # 3. a gap must be a reason
                if len(gap.strip()) < MIN_REASON:
                    problems.append(f"  {lane}/{key}: actuator_gap is not a real reason: {gap!r}")
                backlog.append((lane, key, v.get("control", "?"), gap))
                continue

            # 2. the named method must exist
            n_act += 1
            if "." not in act:
                problems.append(f"  {lane}/{key}: actuator {act!r} is not 'ClientName.method'")
                continue
            client, method = act.split(".", 1)
            if client not in method_cache:
                method_cache[client] = public_methods(client)
            found = method_cache[client]
            if found is None:
                problems.append(
                    f"  {lane}/{key}: actuator names {client!r} but "
                    f"script-includes/{client}.js does not exist"
                )
            elif method not in found:
                problems.append(
                    f"  {lane}/{key}: {client}.{method}() does not exist "
                    f"(available: {', '.join(sorted(found)) or 'none'})"
                )

    if backlog_mode:
        print("Day-2 actuator backlog — control claims with no code behind them")
        print("=" * 68)
        by_lane: dict[str, list] = {}
        for lane, key, ctrl, gap in backlog:
            by_lane.setdefault(lane, []).append((key, ctrl, gap))
        for lane in sorted(by_lane):
            rows = by_lane[lane]
            print(f"\n{lane}  ({len(rows)} item{'s' if len(rows) != 1 else ''})")
            for key, ctrl, gap in rows:
                print(f"  - {key:32} {ctrl:10} {gap[:70]}")
        print(f"\n{len(backlog)} of {n_items} governed items have no actuator.")
        return 0

    print("Day-2 actuator coverage")
    print("=" * 68)
    pct = (n_act / n_items * 100) if n_items else 0
    print(f"maps: {len(maps)} | governed items: {n_items} | actuated: {n_act} ({pct:.0f}%) | "
          f"declared gaps: {n_gap}")
    if problems:
        print(f"\nFAIL — {len(problems)} coverage breach(es):")
        print("\n".join(problems))
        return 1
    print("\nOK — every item either names a method that exists, or declares why it "
          "cannot actuate. Run with --backlog for the unimplemented list.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
