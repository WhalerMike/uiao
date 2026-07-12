#!/usr/bin/env python3
"""Catalog<->module contract check (all five platforms).

For each platform, assert that every REQUIRED module variable -- a
`variable "x" {}` block with no `default` in that package's
terraform/variables.tf -- is accounted for by the catalog variable set, either:

  * collected as a catalog form field  -> <map_to>VAR</map_to>, or
  * resolved on the in-boundary MID Server via the credential alias / app
    properties -> <resolved_by_mid>VAR</resolved_by_mid>  (for secrets and
    connection endpoints that must NEVER be typed into the catalog form, e.g.
    vsphere_password, nsx_password, admin_password).

This is the machine-readable form of "the form is the contract"
(REVIEW-AND-IMPROVEMENTS.md §2.1/§2.4): the requester-facing form and the
Terraform modules cannot silently drift. Blocking in the book CI; exit non-zero
on any gap.

Run: python3 servicenow-app/catalog/contract_check.py
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))  # .../servicenow-app/catalog
BOOK = os.path.normpath(os.path.join(HERE, "..", ".."))  # .../infoblox-ddi-book

# platform -> (package dir, variable-set XML filename in this dir)
PLATFORMS = [
    ("azure", "azure-alz-automation", "variable-set-azure-ddi-subnet.xml"),
    ("aws", "aws-lz-automation", "variable-set-aws-ddi-subnet.xml"),
    ("gcp", "gcp-lz-automation", "variable-set-gcp-ddi-subnet.xml"),
    ("oci", "oci-lz-automation", "variable-set-oci-ddi-subnet.xml"),
    ("vmware", "vmware-lz-automation", "variable-set-vmware-ddi-subnet.xml"),
]


def required_module_vars(path):
    """Return the set of module variable names that have no default (required)."""
    with open(path, encoding="utf-8") as fh:
        txt = fh.read()
    required = set()
    for m in re.finditer(r'variable\s+"([^"]+)"\s*\{', txt):
        name = m.group(1)
        start = txt.index("{", m.start())
        depth, j = 0, start
        while j < len(txt):
            if txt[j] == "{":
                depth += 1
            elif txt[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        block = txt[start:j]
        # a top-level `default =` anywhere in the block => optional
        if not re.search(r"(^|\n)\s*default\s*=", block):
            required.add(name)
    return required


def covered_vars(path):
    """Return (form_fields, mid_resolved) module-variable name sets from a variable set."""
    with open(path, encoding="utf-8") as fh:
        txt = fh.read()
    form = {m.group(1).strip() for m in re.finditer(r"<map_to>([^<]+)</map_to>", txt)}
    mid = {m.group(1).strip() for m in re.finditer(r"<resolved_by_mid>([^<]+)</resolved_by_mid>", txt)}
    form.discard("__platform_selector__")
    return form, mid


def main():
    rc = 0
    for plat, pkg, xml in PLATFORMS:
        vf = os.path.join(BOOK, pkg, "terraform", "variables.tf")
        xf = os.path.join(HERE, xml)
        if not os.path.exists(vf):
            print(f"[{plat}] SKIP — missing module variables.tf: {vf}")
            rc = 2
            continue
        if not os.path.exists(xf):
            print(f"[{plat}] SKIP — missing variable set: {xf}")
            rc = 2
            continue
        required = required_module_vars(vf)
        form, mid = covered_vars(xf)
        missing = sorted(required - form - mid)
        status = "OK" if not missing else "FAIL"
        print(
            f"[{plat:6}] required={len(required):2} "
            f"form={len(form & required):2} mid={len(mid & required):2} -> {status}"
        )
        if missing:
            print(f"          missing (neither a form field nor MID-resolved): {', '.join(missing)}")
            rc = 1
    print()
    if rc == 0:
        print(
            "CONTRACT OK — every required module variable across all five platforms is "
            "collected by a catalog form field or resolved on the in-boundary MID Server."
        )
    else:
        print("CONTRACT FAIL — see per-platform gaps above.")
    return rc


if __name__ == "__main__":
    sys.exit(main())
