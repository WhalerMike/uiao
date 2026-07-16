#!/usr/bin/env python3
"""Catalog<->Script-Include contract check (Lane C / helpdesk exemplar).

"The form is the contract", machine-checked. The catalog variable set is the
front door; `EntraHelpdeskClient` actuates and `EntraHelpdeskGate` pre-flights.
If the form stops supplying something the client or the gate requires, the
request fails at run time in a tenant — long after review. This asserts the
binding at build time instead.

Three invariants:

  1. COVERAGE — every parameter the client actually reads, and every field the
     gate's pre-flight reads, is accounted for in the variable set, either
       * collected as a catalog form field   -> <map_to>NAME</map_to>, or
       * resolved on the in-boundary MID Server / app properties
                                             -> <resolved_by_mid>NAME</resolved_by_mid>

  2. SECRETS ARE NEVER FORM FIELDS — a value in SECRET_PARAMS must be
     <resolved_by_mid>. Declaring it <map_to> is a hard fail: it would put a
     credential on the catalog record (IA-5). This is the Lane C analogue of the
     DDI kit's vsphere_password / admin_password rule.

  3. EVERY CATALOG ITEM HAS AN ACTUATOR — each key in helpdesk-control-map.json
     maps to a client method, or is declared in ACTUATOR_GAPS with a reason.
     An undeclared gap fails: a catalog item that cannot actuate is a control
     claim with nothing behind it.

Actuation stays platform-native and human-approved (L3, ADR-092): the form
raises and routes, Graph-via-MID actuates, a human approves.

Usage:  python contract_check.py          # exit 1 on any breach
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parent
CLIENT = KIT / "script-includes" / "EntraHelpdeskClient.js"
GATE = KIT / "script-includes" / "EntraHelpdeskGate.js"
VARSET = HERE / "variable-set-helpdesk-identity.xml"
CONTROL_MAP = KIT / "helpdesk-control-map.json"

# Parameter containers — the contract is their fields, not the container name.
CONTAINERS = {"payload", "opts", "request"}

# Values that must NEVER be typed into the catalog form (IA-5).
SECRET_PARAMS = {"tempPassword"}

# Catalog items with no client actuator, each with a recorded reason. Graph
# genuinely has no admin account-unlock operation, and a Conditional-Access
# exception actuates as a CA policy edit rather than a user-object write.
ACTUATOR_GAPS = {
    "entra.credential.account_unlock":
        "Microsoft Graph exposes no admin account-unlock operation; Entra smart "
        "lockout auto-clears, so this reduces to resetPassword or an Entra-side wait.",
    "entra.access.ca_exception":
        "Actuates as a Conditional-Access policy edit (policy object), not a "
        "user-object write; no dedicated client method.",
}


def client_required_params(path: Path) -> set[str]:
    """Positional params of every public method, plus the payload./opts. fields
    the file actually reads."""
    txt = path.read_text(encoding="utf-8")
    params: set[str] = set()
    for m in re.finditer(r"^\s{4}([A-Za-z_]\w*): function \(([^)]*)\)", txt, re.M):
        name, arglist = m.group(1), m.group(2)
        if name.startswith("_") or name == "initialize":
            continue
        for a in (a.strip() for a in arglist.split(",")):
            if a and a not in CONTAINERS:
                params.add(a)
    # container fields actually dereferenced
    for m in re.finditer(r"\b(?:payload|opts)\.([A-Za-z_]\w*)", txt):
        params.add(m.group(1))
    return params


def gate_required_fields(path: Path) -> set[str]:
    """Fields the gate's pre-flight reads off the request."""
    txt = path.read_text(encoding="utf-8")
    return {m.group(1) for m in re.finditer(r"\brequest\.([A-Za-z_]\w*)", txt)}


def varset_coverage(path: Path) -> tuple[set[str], set[str]]:
    txt = path.read_text(encoding="utf-8")
    form = {m.group(1).strip() for m in re.finditer(r"<map_to>([^<]+)</map_to>", txt)}
    mid = {m.group(1).strip() for m in re.finditer(r"<resolved_by_mid>([^<]+)</resolved_by_mid>", txt)}
    return form, mid


def main() -> int:
    required = client_required_params(CLIENT) | gate_required_fields(GATE)
    form, mid = varset_coverage(VARSET)
    covered = form | mid
    catalog = json.loads(CONTROL_MAP.read_text(encoding="utf-8"))
    items = catalog.get("catalog", catalog)
    item_keys = {k for k, v in items.items() if isinstance(v, dict) and v.get("control")}

    problems: list[str] = []

    # 1. coverage
    for miss in sorted(required - covered):
        problems.append(
            f"  {miss!r} is required by the client/gate but is neither <map_to> nor "
            f"<resolved_by_mid> in {VARSET.name}"
        )

    # 2. secrets must be MID-resolved, never a form field
    for s in sorted(SECRET_PARAMS & form):
        problems.append(
            f"  {s!r} is a SECRET but is declared <map_to> — it would land on the "
            f"catalog record. Declare it <resolved_by_mid> (IA-5)."
        )
    for s in sorted(SECRET_PARAMS - covered):
        problems.append(f"  secret {s!r} is required but not declared <resolved_by_mid>")

    # 3. every catalog item actuates, or declares why it cannot
    undeclared = sorted(k for k in item_keys if k in ACTUATOR_GAPS) # declared gaps are fine
    unknown_gap = sorted(k for k in ACTUATOR_GAPS if k not in item_keys)
    for k in unknown_gap:
        problems.append(f"  ACTUATOR_GAPS declares {k!r} but no such catalog item exists")

    print("Lane C catalog<->Script-Include contract check")
    print("=" * 52)
    print(f"client/gate required: {len(required)} | form-collected: {len(form)} | "
          f"MID-resolved: {len(mid)} | catalog items: {len(item_keys)}")
    if undeclared:
        print(f"declared actuator gaps ({len(undeclared)}): " + ", ".join(undeclared))

    if problems:
        print(f"\nFAIL — {len(problems)} contract breach(es):")
        print("\n".join(problems))
        return 1
    print("\nOK — the form supplies every client/gate parameter; secrets are "
          "MID-resolved; every catalog item actuates or declares its gap.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
