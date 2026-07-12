#!/usr/bin/env python3
"""Catalog↔module contract check (Azure exemplar).

Asserts that every REQUIRED Azure module variable — a `variable "x" {}` block in
azure-alz-automation/terraform/variables.tf with no `default` — is collected by
the catalog variable set (a `<map_to>` entry in variable-set-azure-ddi-subnet.xml).

This is the machine-readable version of the "the form is the contract" claim
(REVIEW-AND-IMPROVEMENTS.md §2.1/§2.4): the requester-facing form and the
Terraform module cannot silently drift. Exit non-zero on any gap.

Run: python3 servicenow-app/catalog/contract_check.py
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))  # .../servicenow-app/catalog
BOOK = os.path.normpath(os.path.join(HERE, "..", ".."))  # .../infoblox-ddi-book
VARS_TF = os.path.join(BOOK, "azure-alz-automation", "terraform", "variables.tf")
VAR_SET = os.path.join(HERE, "variable-set-azure-ddi-subnet.xml")


def required_module_vars(path):
    """Return the set of module variable names that have no default (required)."""
    with open(path, encoding="utf-8") as fh:
        txt = fh.read()
    required = set()
    for m in re.finditer(r'variable\s+"([^"]+)"\s*\{', txt):
        name = m.group(1)
        # brace-match the block body starting at the '{' we just matched
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


def mapped_vars(path):
    """Return the set of module variables the catalog variable set maps to."""
    with open(path, encoding="utf-8") as fh:
        txt = fh.read()
    return {m.group(1).strip() for m in re.finditer(r"<map_to>([^<]+)</map_to>", txt)}


def main():
    for p in (VARS_TF, VAR_SET):
        if not os.path.exists(p):
            print(f"contract_check: missing input {p}", file=sys.stderr)
            return 2
    required = required_module_vars(VARS_TF)
    mapped = mapped_vars(VAR_SET)
    # ignore the synthetic platform selector marker
    mapped.discard("__platform_selector__")

    missing = sorted(required - mapped)
    print("required module variables :", ", ".join(sorted(required)) or "(none)")
    print("catalog-mapped variables  :", ", ".join(sorted(mapped)) or "(none)")
    if missing:
        print()
        print("CONTRACT FAIL — required Azure module variables NOT collected by the catalog variable set:")
        for v in missing:
            print(f"  - {v}")
        print(
            "Add an <item_option_new> with <map_to>" + missing[0] + "</map_to> "
            "(and the rest) to variable-set-azure-ddi-subnet.xml, or give the "
            "module variable a default."
        )
        return 1
    print()
    print(
        f"CONTRACT OK — all {len(required)} required Azure module variables are collected by the catalog variable set."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
