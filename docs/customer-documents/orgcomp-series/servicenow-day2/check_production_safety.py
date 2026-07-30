#!/usr/bin/env python3
"""A control claim may not be certified against code the documentation forbids running.

Closes NEW-4 from the external security review (Rev 2).

The defect: `CURRENT-STATE-SCRIPTS.md` says, in the body text, "do not run this
skeleton against a live domain until the re-read, the injection path, and the
target-override are fixed." Meanwhile `check_actuator_coverage.py` resolved every
`actuator_ad` binding to a real method and reported

    OK - every item either names a method that exists, or declares why it cannot actuate

exit 0, 46 of 50 items actuated. So the machine-checked gate certified as
production-covered the exact code path the prose forbids.

That matters because this kit's whole design philosophy is that guarantees are
proven by gates rather than asserted in prose. An implementer who trusts the
gates over the prose -- which is what the kit trains them to do -- ships the
injection path.

This gate closes the loop. Control-map items may now carry:

    "unsafe_for_production": "<reason>"     this actuator must not run in prod

and Script Include files may carry a machine-readable banner:

    // @unsafe-for-production: <reason>

Either one makes every control-map item bound to that actuator fail the build,
by name, with the reason. Remove the marker when the defect is fixed; the gate
goes green on its own.

Note what this gate does NOT do: it does not verify that the reason is true, and
it does not detect an unsafe actuator that nobody marked. It converts a prose
disclosure into a build failure -- which is the specific gap it exists to close,
not a general safety property.

Usage:
    python check_production_safety.py                 # gate; exit 1 on any breach
    python check_production_safety.py --allow-unsafe  # report only, exit 0
                                                      # (sub-prod builds ONLY)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SI_DIR = HERE / "script-includes"

# Must match check_actuator_coverage.py / check_l3_ceiling.py. A gate that globs
# fewer maps than its siblings is how the last blind spot happened.
MAP_GLOBS = [
    (HERE, "*-control-map.json"),
    (HERE.parent / "x_fed_compliance" / "data", "control-map.json"),
]

BANNER = re.compile(r"^\s*//\s*@unsafe-for-production:\s*(.+)$", re.MULTILINE)
ACTUATOR = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)$")


def control_maps() -> list[Path]:
    found: list[Path] = []
    for base, pattern in MAP_GLOBS:
        if base.is_dir():
            found.extend(sorted(base.glob(pattern)))
    return found


def items(path: Path):
    d = json.loads(path.read_text(encoding="utf-8"))
    cat = d.get("catalog", d)
    for k, v in cat.items():
        if isinstance(v, dict) and v.get("control"):
            yield k, v


def unsafe_clients() -> dict[str, str]:
    """Script Includes carrying the @unsafe-for-production banner."""
    out: dict[str, str] = {}
    if not SI_DIR.is_dir():
        return out
    for js in sorted(SI_DIR.glob("*.js")):
        m = BANNER.search(js.read_text(encoding="utf-8", errors="replace"))
        if m:
            out[js.stem] = m.group(1).strip()
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--allow-unsafe", action="store_true",
                    help="report but do not fail. Sub-prod builds only -- never in a "
                         "promotion pipeline, which is the one place this gate matters.")
    args = ap.parse_args()

    banners = unsafe_clients()
    problems: list[str] = []
    n_items = n_bound = 0

    for m in control_maps():
        lane = m.name.replace("-control-map.json", "")
        if lane == "control-map.json":
            lane = m.parent.parent.name

        for key, v in items(m):
            n_items += 1

            # (a) the item itself is marked unsafe
            reason = v.get("unsafe_for_production")
            if reason:
                if len(str(reason).strip()) < 25:
                    problems.append(
                        f"  {lane}/{key}: unsafe_for_production is not a real reason: {reason!r}"
                    )
                else:
                    problems.append(
                        f"  {lane}/{key}: control {v.get('control')} is bound to an actuator "
                        f"marked unsafe for production -- {reason}"
                    )
                continue

            # (b) the actuator it names is marked unsafe at the source
            for field in ("actuator", "actuator_ad"):
                ref = v.get(field)
                if not ref:
                    continue
                n_bound += 1
                mm = ACTUATOR.match(str(ref).strip())
                if not mm:
                    continue  # shape is check_actuator_coverage.py's job, not ours
                client = mm.group(1)
                if client in banners:
                    problems.append(
                        f"  {lane}/{key}: {field} names {ref} but {client}.js carries "
                        f"@unsafe-for-production -- {banners[client]}"
                    )

    print("Day-2 production safety (NEW-4)")
    print("=" * 68)
    print(f"governed items: {n_items} | actuator bindings checked: {n_bound} | "
          f"clients flagged unsafe: {len(banners)}")
    if banners:
        for c, r in sorted(banners.items()):
            print(f"  flagged: {c}.js -- {r}")

    if problems:
        verdict = "WARN" if args.allow_unsafe else "FAIL"
        print(f"\n{verdict} -- {len(problems)} control claim(s) certified against "
              f"code that must not run in production:")
        print("\n".join(problems))
        if args.allow_unsafe:
            print("\n--allow-unsafe was passed: reporting only. Do not use this flag "
                  "in a promotion pipeline.")
            return 0
        print("\nRemove the @unsafe-for-production banner (or the item's "
              "unsafe_for_production field) once the defect is fixed; this gate "
              "then goes green on its own.")
        return 1

    print("\nOK -- no control claim is bound to an actuator marked unsafe for production.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
