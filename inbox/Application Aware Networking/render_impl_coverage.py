#!/usr/bin/env python3
"""Generate the ServiceNow implementation-coverage matrix from the control maps.

The maps define WHAT is governed (55 catalog items across 6 scoped-app lanes);
the kits carry HOW MUCH of it is actually implemented. This renders, per item:

  blueprinted — the item key appears in a flow blueprint
  tested      — the item key appears in an ATF spec
  status      — specified -> blueprinted -> tested (each implies the last)

"Scripted" (a client method exists for the item) is deliberately NOT inferred:
item keys don't appear in Script Include method names, and guessing the mapping
would fake precision. When the push adds an `impl:` block to map items, this
generator picks it up as the authoritative link.

Output: AAN_Implementation_Coverage.md (drift-gated with --check). This is the
tracking board for the "full ServiceNow implementations" push — 'complete' is a
measured claim here, not an asserted one.

Usage:
    python render_impl_coverage.py            # write the matrix
    python render_impl_coverage.py --check    # drift gate (exit 1 if stale)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "AAN_Implementation_Coverage.md"

# lane map -> the kit dir whose flow/ and atf/ artifacts implement it
LANES = {
    "servicenow-day2/helpdesk-control-map.json": "servicenow-day2",
    "servicenow-day2/landingzone-control-map.json": "servicenow-day2",
    "servicenow-day2/appreg-control-map.json": "servicenow-day2",
    "servicenow-day2/telephony-control-map.json": "servicenow-day2",
    "servicenow-day2/saas-control-map.json": "servicenow-day2",
    "x_fed_compliance/data/control-map.json": "x_fed_compliance",
}


def _kit_text(kit: Path, sub: str) -> str:
    return "\n".join(
        p.read_text(encoding="utf-8", errors="replace") for p in sorted(kit.glob(f"{sub}/**/*")) if p.is_file()
    )


def render() -> str:
    rows = []
    totals = {"specified": 0, "blueprinted": 0, "tested": 0}
    for map_rel, kit_rel in LANES.items():
        map_path = HERE / map_rel
        kit = HERE / kit_rel
        cat = json.loads(map_path.read_text(encoding="utf-8"))["catalog"]
        flow_text = _kit_text(kit, "flow")
        atf_text = _kit_text(kit, "atf")
        lane = map_path.name.replace("-control-map.json", "").replace("control-map.json", kit_rel)
        for key, item in cat.items():
            impl = item.get("impl", {})
            blueprinted = key in flow_text or impl.get("flow")
            tested = key in atf_text or impl.get("atf")
            status = "tested" if tested else "blueprinted" if blueprinted else "specified"
            totals["specified"] += 1
            if blueprinted:
                totals["blueprinted"] += 1
            if tested:
                totals["tested"] += 1
            rows.append(
                (
                    lane,
                    key,
                    item["control"],
                    "yes" if blueprinted else "—",
                    "yes" if tested else "—",
                    status,
                    impl.get("method", "—"),
                )
            )

    L = [
        "# AAN ServiceNow Implementation Coverage",
        "",
        "> **Generated file — do not hand-edit.** Produced by `render_impl_coverage.py`",
        "> from the six lane control maps and the kit artifacts on disk; CI-gated. This",
        "> is the tracking board for the full-ServiceNow-implementation push: every",
        "> governed catalog item, and how far its implementation has actually gotten.",
        "",
        f"**{totals['specified']} governed items** — "
        f"{totals['blueprinted']} blueprinted ({100 * totals['blueprinted'] // max(totals['specified'], 1)}%), "
        f"{totals['tested']} with an ATF spec ({100 * totals['tested'] // max(totals['specified'], 1)}%). "
        "'Scripted' is recorded only via an explicit `impl.method` on the map item — never inferred.",
        "",
        "| Lane | Catalog item | Control | Blueprint | ATF | Status | Client method |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in sorted(rows):
        L.append("| " + " | ".join(r) + " |")
    L.append("")
    L.append(": Implementation coverage by governed catalog item {.striped .hover}")
    L.append("")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    content = render() + "\n"
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != content:
            print(f"DRIFT — regenerate: python {Path(__file__).name}")
            return 1
        print(f"OK — {OUT.name} matches the maps and kit artifacts.")
        return 0
    OUT.write_text(content, encoding="utf-8")
    print(f"Wrote {OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
