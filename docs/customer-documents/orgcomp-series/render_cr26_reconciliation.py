#!/usr/bin/env python3
"""Generate the ADR-111 rule set → CR26 Moderate indicator reconciliation.

Closes the "KSI-count reconciliation (open item)" the OrgComp series flagged in the
Executive Summary and Vol IV Book 06: the series headlines "29/29" against the
internal ADR-111 rule set, which is NOT the CR26 Moderate indicator catalog.
This script produces the rule-ID-by-rule-ID diff by matching each internal
rule's declared `Mappings.CR26` indicator ID against the authoritative FedRAMP
CR26 OSCAL catalog committed in the repo — no indicator IDs are invented.

Sources (both in-repo, authoritative):
  - Internal rules:  src/uiao/ksi/rules/KSI-0NN.yaml  (the 29-rule "ADR-111 set")
  - CR26 catalog:    src/uiao/canon/compliance/reference/fedramp-cr26/snapshot/
                     <hash>/catalog/json/FedRAMP_CR26_catalog.json

Usage:
    python render_cr26_reconciliation.py               # write OrgComp_CR26_Reconciliation.md
    python render_cr26_reconciliation.py --check        # drift gate (exit 1 if stale)
"""

from __future__ import annotations

import argparse
import glob
import json
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
    raise SystemExit(f"repo root not found (no .git above {p})")


try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML required: pip install pyyaml")

HERE = Path(__file__).resolve().parent
REPO = _repo_root()  # docs/customer-documents/orgcomp-series -> repo root
OUT = HERE / "OrgComp_CR26_Reconciliation.md"

# The 4 themes carried by the ScuBA baseline rules (KSI-001..010), which attest
# M365 baseline state but declare no CR26 indicator ID.
SCUBA_THEMES = {"KSI-IAM", "KSI-SVC", "KSI-MLA", "KSI-CNA"}

# Presentation order: ScuBA-touched themes first, then the fully-mapped themes.
THEME_ORDER = [
    "KSI-IAM",
    "KSI-CNA",
    "KSI-SVC",
    "KSI-MLA",
    "KSI-CMT",
    "KSI-PIY",
    "KSI-SCR",
    "KSI-CED",
    "KSI-INR",
    "KSI-RPL",
]


def find_catalog() -> Path:
    matches = sorted(
        REPO.glob("src/uiao/canon/compliance/reference/fedramp-cr26/snapshot/*/catalog/json/FedRAMP_CR26_catalog.json")
    )
    if not matches:
        sys.exit("CR26 catalog not found under src/uiao/canon/compliance/reference/fedramp-cr26/")
    return matches[0]


def walk(groups):
    for g in groups:
        if g.get("id", "").startswith("KSI"):
            yield ("group", g["id"], g.get("title", ""))
        for c in g.get("controls", []) or []:
            yield ("ctrl", c.get("id", ""), c.get("title", ""))
            for s in c.get("controls", []) or []:
                yield ("ctrl", s.get("id", ""), s.get("title", ""))
        yield from walk(g.get("groups", []) or [])


def load_catalog(path: Path):
    cat = json.loads(path.read_text(encoding="utf-8"))["catalog"]
    themes: dict[str, dict] = {}
    for kind, cid, title in walk(cat.get("groups", []) or []):
        if kind == "group":
            themes.setdefault(cid, {"title": title, "ind": []})
        elif kind == "ctrl" and cid.startswith("KSI") and not cid.endswith("_smt"):
            th = "-".join(cid.split("-")[:2])
            themes.setdefault(th, {"title": "", "ind": []})
            themes[th]["ind"].append((cid, title))
    return themes


def load_rules():
    rules = {}
    for f in sorted(glob.glob(str(REPO / "src/uiao/ksi/rules/KSI-0*.yaml"))):
        d = yaml.safe_load(Path(f).read_text(encoding="utf-8"))
        m = d.get("Mappings", {}) or {}
        rules[d["KSI_ID"]] = {
            "cr26": m.get("CR26", ""),
            "scuba": m.get("CISA_SCUBA", ""),
            "title": d.get("Title", ""),
            "theme": d.get("Theme", ""),
        }
    return rules


def render() -> str:
    catalog_path = find_catalog()
    snap = catalog_path.parts[catalog_path.parts.index("snapshot") + 1]
    themes = load_catalog(catalog_path)
    rules = load_rules()
    cr26_to_rule = {r["cr26"]: rid for rid, r in rules.items() if r["cr26"]}

    order = [t for t in THEME_ORDER if t in themes]
    tot = sum(len(themes[t]["ind"]) for t in order)
    mapped = sum(1 for t in order for cid, _ in themes[t]["ind"] if cid in cr26_to_rule)

    L = []
    L.append("# ADR-111 Rule Set → CR26 Moderate Indicator Reconciliation")
    L.append("")
    L.append(
        "> **Generated file — do not hand-edit.** Produced by "
        "`render_cr26_reconciliation.py`. Regenerate when the internal rules or "
        "the CR26 catalog snapshot change."
    )
    L.append("")
    L.append(
        "> **Provenance.** Internal rule set: the host repo's 29 "
        "`ksi/rules/KSI-0NN.yaml` files (the series' \"ADR-111 rule "
        'set"). CR26 catalog: the authoritative FedRAMP CR26 OSCAL catalog '
        "committed in the host repo at "
        f"`.../compliance/reference/fedramp-cr26/snapshot/{snap}/"
        "catalog/json/FedRAMP_CR26_catalog.json`. Each rule's declared "
        "`Mappings.CR26` indicator ID is matched against the catalog's leaf "
        "indicators — no IDs are invented."
    )
    L.append("")
    L.append("## Headline delta")
    L.append("")
    L.append(
        f"- **CR26 Moderate indicators in the in-repo catalog snapshot:** "
        f"**{tot}** across 10 themes (the finalized published catalog may count "
        "56–63 depending on statement-level vs indicator-level counting; this "
        "snapshot enumerates indicator-level IDs)."
    )
    L.append("- **Internal ADR-111 rules:** **29**.")
    L.append(
        f"- **Indicators explicitly mapped 1:1 to an internal rule "
        f"(satisfied at indicator-ID level):** **{mapped} of {tot}**."
    )
    L.append(
        f"- **Indicators not yet bound to an internal rule ID (not-yet-mapped):** "
        f"**{tot - mapped} of {tot}** — four of these themes are *partially* "
        "addressed by the 10 CISA ScuBA baseline rules (KSI-001..010), which "
        "attest M365 baseline state but declare no CR26 indicator ID."
    )
    L.append("")
    L.append(
        f'So "29/29 satisfied" is a statement about the **internal rule set**, '
        "not the CR26 Moderate catalog: at the CR26 indicator level, coverage is "
        f"**{mapped}/{tot} explicitly mapped**, with {tot - mapped} indicators "
        "still to be bound (mostly the IAM/CNA/SVC/MLA themes the ScuBA rules "
        "touch without an indicator-ID binding). The POA&M is therefore expected "
        "to be non-empty once these are assessed against the finalized CR26 list."
    )
    L.append("")
    L.append("## Per-theme reconciliation")
    L.append("")
    L.append("| Theme | CR26 indicator | Internal rule | Status |")
    L.append("|---|---|---|---|")
    for th in order:
        title = themes[th]["title"]
        for cid, ititle in themes[th]["ind"]:
            rid = cr26_to_rule.get(cid)
            if rid:
                status = "✅ Mapped"
                rulecell = f"{rid} — {rules[rid]['title']}"
            elif th in SCUBA_THEMES:
                status = "🟡 Partial — ScuBA baseline, no indicator-ID binding"
                rulecell = "— (ScuBA rules KSI-001..010 attest this theme)"
            else:
                status = "⬜ Not yet mapped"
                rulecell = "—"
            L.append(f"| {th} ({title}) | {cid} — {ititle} | {rulecell} | {status} |")
    L.append("")
    L.append("## Theme summary")
    L.append("")
    L.append("| Theme | Indicators | Mapped 1:1 | Coverage |")
    L.append("|---|---|---|---|")
    for th in order:
        inds = themes[th]["ind"]
        n = len(inds)
        m = sum(1 for cid, _ in inds if cid in cr26_to_rule)
        cov = "fully mapped" if m == n else ("partial (ScuBA baseline)" if th in SCUBA_THEMES else "not yet mapped")
        L.append(f"| {th} — {themes[th]['title']} | {n} | {m} | {cov} |")
    L.append(f"| **Total** | **{tot}** | **{mapped}** | **{mapped}/{tot} explicitly mapped** |")
    L.append("")

    # Remediation plan for the not-yet-mapped indicators.
    unmapped = [
        (th, themes[th]["title"], len(themes[th]["ind"]))
        for th in order
        if sum(1 for cid, _ in themes[th]["ind"] if cid in cr26_to_rule) == 0
    ]
    unmapped_total = sum(n for _, _, n in unmapped)
    L.append("## Remediation plan for the not-yet-mapped indicators")
    L.append("")
    L.append(
        f"The **{unmapped_total} not-yet-mapped indicators** fall entirely in the "
        f"{len(unmapped)} themes below, each attested today at the CISA ScuBA "
        "baseline level (rules KSI-001..010) but not yet bound to a CR26 indicator "
        "ID. The external dependency has **cleared** — the finalized CR26 Moderate "
        "list was published **June 25, 2026** — so this is actionable now, not "
        "blocked. Owner is stated by role (no individual named here); the "
        "authorization timeline dates are from the ConMon Gap Roadmap."
    )
    L.append("")
    L.append("| Theme | Unmapped indicators | Disposition | Owner (role) | Target |")
    L.append("|---|---|---|---|---|")
    for th, title, n in unmapped:
        L.append(
            f"| {th} — {title} | {n} | Bind each indicator to a rule, **or** record "
            "an explicit ScuBA-baseline attestation decision | OrgComp compliance "
            "authoring lead (OIS ConMon lead accountable) | Before independent SCA; "
            "no later than the Class B+C window (Aug 31, 2026) |"
        )
    L.append(f"| **Total** | **{unmapped_total}** | — | — | — |")
    L.append("")
    L.append(
        "Until these are dispositioned, the POA&M is expected to be non-empty: each "
        "unmapped indicator is a candidate POA&M item pending the binding decision "
        "and the independent SCA verdict."
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
        print(f"OK — {OUT.name} matches the rules and CR26 catalog.")
        return 0

    OUT.write_text(content, encoding="utf-8")
    print(f"Wrote {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
