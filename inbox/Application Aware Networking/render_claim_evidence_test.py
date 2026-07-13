#!/usr/bin/env python3
"""Generate the claim -> evidence -> test traceability matrix from the spine.

Every closure in aan-compliance-spine.yml is a control-closure *claim*. This
renders, for each claim, the evidence slot it lands in, the kit that implements
it (if any), and the named falsifying test that would prove it false (if one is
bound). Where a claim has no bound test, the matrix says so explicitly — so the
verification gap is countable, not hidden. Answers the critique's ask for a
claim -> evidence -> test column that makes the corpus self-auditing.

Coverage is stated honestly up top: the spine's generated-and-gated closures
cover only the books that carry closure rows; the rest of the series' control
tables are hand-authored and not spine-gated.

Usage:
    python render_claim_evidence_test.py            # write AAN_Claim_Evidence_Test_Matrix.md
    python render_claim_evidence_test.py --check     # drift gate (exit 1 if stale)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML required: pip install pyyaml")

HERE = Path(__file__).resolve().parent
SPINE = HERE / "aan-compliance-spine.yml"
OUT = HERE / "AAN_Claim_Evidence_Test_Matrix.md"


def render() -> str:
    d = yaml.safe_load(SPINE.read_text(encoding="utf-8"))
    closures = d["closures"]
    slots = d["slots"]
    total_books = len(d["books"])
    books_with_closures = len({c["book"] for c in closures})
    with_test = sum(1 for c in closures if c.get("test"))
    with_kit = sum(1 for c in closures if c.get("kit"))

    L = []
    L.append("# AAN Claim → Evidence → Test Traceability Matrix")
    L.append("")
    L.append(
        "> **Generated file — do not hand-edit.** Produced by "
        "`render_claim_evidence_test.py` from `aan-compliance-spine.yml`. "
        "Regenerate when closures change; CI-gated."
    )
    L.append("")
    L.append("## Coverage (stated honestly)")
    L.append("")
    L.append(
        f"- The spine records **{len(closures)} control-closure claims** across "
        f"**{books_with_closures} of {total_books} books**. The generated, "
        "CI-gated authorities tables cover only those closure-bearing books; the "
        "remaining books' NIST control tables are **hand-authored inline in the "
        "`.qmd` and are not spine-gated**. Do not read this matrix as series-wide "
        "control coverage — it is the coverage the spine can prove."
    )
    L.append(
        f"- **{with_test} of {len(closures)}** claims carry a named falsifying "
        f"test; **{with_kit} of {len(closures)}** name an implementing kit. A "
        "claim with no bound test is not disproven — it is **unverified** (Vol VI "
        "Book 08: \"a control dimension no test covers is still unverified\")."
    )
    L.append("")
    L.append("## Matrix")
    L.append("")
    L.append("| Control | Book | Plane | Evidence slot | Implementing kit | Falsifying test |")
    L.append("|---|---|---|---|---|---|")
    for c in sorted(closures, key=lambda r: (r["book"], r["plane"], r["control"])):
        ctrl = c["control"] + (" †" if c.get("necessity") else "")
        slot = slots.get(c["slot"], c["slot"])
        kit = c.get("kit", "—")
        test = c.get("test", "— *(no falsifying test bound yet)*")
        L.append(f"| {ctrl} | {c['book']} | {c['plane']} | {slot} | {kit} | {test} |")
    L.append("")
    L.append(
        "*† = Closure-Necessity anchor (no alternate closure path; see the "
        "per-book alternate-path rebuttals). Slot names are the evidence "
        "categories declared in the spine; a kit named here ships as source in "
        "the distribution kit under its volume.*"
    )
    L.append("")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="drift gate (exit 1 if stale)")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    content = render()
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != content:
            print(f"DRIFT — regenerate: python {Path(__file__).name}")
            return 1
        print(f"OK — {OUT.name} matches the spine.")
        return 0
    OUT.write_text(content, encoding="utf-8")
    print(f"Wrote {OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
