#!/usr/bin/env python3
"""The AD allowlist is declared twice; this proves the two copies agree.

The AD write leg validates caller-supplied parameters in TWO places, by design:

    script-includes/AdHybridClient.js   AdHybridClient.ACTIONS   (ServiceNow side)
    mid/Invoke-Day2AdAction.ps1         $Contracts               (MID Server side)

That duplication is deliberate defence in depth -- the MID wrapper refuses a
parameter even if something reached it without going through the Script Include.
It is also a drift hazard of exactly the kind UIAO_211 was written about: two
artifacts that must agree, with nothing comparing them. UIAO_211's finding was
that the ServiceNow adapter "compiled its hostname in ... with recorded test
fixtures that asserted the mistake -- so the suite agreed with the bug and stayed
green. The defect class was not a typo. It was that **no artifact existed for any
gate to compare the code against.**"

Here both artifacts exist. What was missing was the comparison.

Drift is silent and asymmetric, which is why eyeballing does not catch it:

  * A key added to the JS but not the PS is refused at the MID after being
    accepted by ServiceNow -- the task fails late, at actuation, with an error
    that names the MID rather than the allowlist.

  * A key added to the PS but not the JS is unreachable -- dead configuration
    that reads as supported.

  * An ACTION present in one and absent from the other is worse: a whole verb
    that either cannot dispatch or cannot execute.

What this gate does NOT do: it compares the ALLOWED-KEY SETS and the ACTION
NAMES. It cannot check that the two implementations treat a given key the same
way once accepted -- that is what scripts/servicenow-harness/ and the ATF suite
are for.

Exit codes: 0 in sync, 1 drift found, 2 the source files could not be parsed
(treated as failure -- an unparseable contract is not a passing contract).

    python check_allowlist_parity.py            # report
    python check_allowlist_parity.py --verbose  # per-action key listing
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent
JS_SOURCE = KIT / "script-includes" / "AdHybridClient.js"
PS_SOURCE = KIT / "mid" / "Invoke-Day2AdAction.ps1"

RULE = "=" * 68


class ParseError(RuntimeError):
    """The contract could not be read out of a source file."""


def parse_js_actions(text: str) -> dict[str, set[str]]:
    """Pull AdHybridClient.ACTIONS into {action: {allowed keys}}."""
    block = re.search(
        r"AdHybridClient\.ACTIONS\s*=\s*\{(.*?)\n\};",
        text,
        re.S,
    )
    if not block:
        raise ParseError(
            "AdHybridClient.ACTIONS not found -- the table was renamed, "
            "reformatted, or moved. Update this gate rather than deleting it."
        )

    actions: dict[str, set[str]] = {}
    for match in re.finditer(
        r"'([a-z][a-z0-9-]*)':\s*\{\s*allowed:\s*\[(.*?)\]",
        block.group(1),
        re.S,
    ):
        actions[match.group(1)] = set(re.findall(r"'([^']*)'", match.group(2)))

    if not actions:
        raise ParseError("AdHybridClient.ACTIONS parsed to zero actions")
    return actions


def parse_ps_contracts(text: str) -> dict[str, set[str]]:
    """Pull $Contracts into {action: {allowed keys}}."""
    block = re.search(r"\$Contracts\s*=\s*@\{(.*?)\n\}", text, re.S)
    if not block:
        raise ParseError(
            "$Contracts not found in the MID wrapper -- the table was renamed, "
            "reformatted, or moved. Update this gate rather than deleting it."
        )

    contracts: dict[str, set[str]] = {}
    for match in re.finditer(
        r"'([a-z][a-z0-9-]*)'\s*=\s*@\((.*?)\)",
        block.group(1),
        re.S,
    ):
        contracts[match.group(1)] = set(re.findall(r"'([^']*)'", match.group(2)))

    if not contracts:
        raise ParseError("$Contracts parsed to zero actions")
    return contracts


def compare(js: dict[str, set[str]], ps: dict[str, set[str]]) -> list[str]:
    """Return one human-readable line per drift finding."""
    findings: list[str] = []

    for action in sorted(set(js) - set(ps)):
        findings.append(
            f"action '{action}' is declared in AdHybridClient.ACTIONS but not in "
            f"$Contracts -- ServiceNow would dispatch it and the MID would refuse it"
        )

    for action in sorted(set(ps) - set(js)):
        findings.append(
            f"action '{action}' is declared in $Contracts but not in "
            f"AdHybridClient.ACTIONS -- unreachable, and reads as supported"
        )

    for action in sorted(set(js) & set(ps)):
        js_only = js[action] - ps[action]
        ps_only = ps[action] - js[action]
        if js_only:
            findings.append(
                f"action '{action}': key(s) {sorted(js_only)} accepted by the "
                f"Script Include but refused by the MID wrapper"
            )
        if ps_only:
            findings.append(
                f"action '{action}': key(s) {sorted(ps_only)} permitted by the "
                f"MID wrapper but unreachable through the Script Include"
            )

    return findings


def main(argv: list[str]) -> int:
    verbose = "--verbose" in argv

    print("Day-2 AD allowlist parity (AdHybridClient.ACTIONS vs $Contracts)")
    print(RULE)

    for source in (JS_SOURCE, PS_SOURCE):
        if not source.exists():
            print(f"FAIL -- source not found: {source}")
            return 2

    try:
        js = parse_js_actions(JS_SOURCE.read_text(encoding="utf-8"))
        ps = parse_ps_contracts(PS_SOURCE.read_text(encoding="utf-8"))
    except ParseError as exc:
        print(f"FAIL -- {exc}")
        return 2

    js_keys = sum(len(v) for v in js.values())
    ps_keys = sum(len(v) for v in ps.values())
    print(f"Script Include: {len(js)} actions / {js_keys} keys | MID wrapper: {len(ps)} actions / {ps_keys} keys")

    if verbose:
        print()
        for action in sorted(set(js) | set(ps)):
            print(f"  {action}")
            print(f"    JS: {sorted(js.get(action, set())) or '(none)'}")
            print(f"    PS: {sorted(ps.get(action, set())) or '(none)'}")

    findings = compare(js, ps)

    if findings:
        print()
        for finding in findings:
            print(f"  DRIFT -- {finding}")
        print()
        print(f"FAIL -- {len(findings)} parity finding(s). The two allowlists must agree; change both or neither.")
        return 1

    print()
    print("OK -- every action and every allowed key matches across the Script Include and the MID wrapper.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
