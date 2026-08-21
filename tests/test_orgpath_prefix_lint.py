"""Tests for the OrgPath prefix guard (ADR-127).

The guard fails CI when a ``-startsWith`` / ``like`` expression carries a
hybrid OrgPath prefix (``Facet=Value`` segments) that is either missing its
trailing ``|`` or not anchored at the first segment of the derived path.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "check_orgpath_prefix_delimiter",
    Path(__file__).parent.parent / "scripts" / "check_orgpath_prefix_delimiter.py",
)
lint = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(lint)


# ---------------------------------------------------------------------------
# Prefix classification
# ---------------------------------------------------------------------------


def test_hybrid_prefixes_are_in_scope() -> None:
    assert lint.is_orgpath_prefix("Division=East")
    assert lint.is_orgpath_prefix("Division=East|")
    assert lint.is_orgpath_prefix("Region=NCR|Department=IT")
    assert lint.is_orgpath_prefix("Region=NCR|Department=IT|*")


def test_legacy_model_a_and_b_styles_are_out_of_scope() -> None:
    # No Facet=Value segments — grandfathered content never trips the gate.
    assert not lint.is_orgpath_prefix("ORG-FIN")
    assert not lint.is_orgpath_prefix("/Root/Finance/")
    assert not lint.is_orgpath_prefix("CORP/US/EAST")
    assert not lint.is_orgpath_prefix("CERT-")


def test_termination_check_handles_like_wildcard() -> None:
    assert lint.is_terminated("Division=East|")
    assert lint.is_terminated("Region=NCR|Department=IT|*")
    assert not lint.is_terminated("Division=East")
    assert not lint.is_terminated("Region=NCR|Department=IT*")


# ---------------------------------------------------------------------------
# Line scanning
# ---------------------------------------------------------------------------


def test_flags_unterminated_startswith_prefix() -> None:
    line = '(device.extensionAttribute15 -startsWith "Division=East")'
    findings = lint.scan_text(line, "rules.yaml")
    assert len(findings) == 1
    assert "Division=East" in findings[0]
    assert "trailing" in findings[0]


def test_passes_terminated_startswith_prefix() -> None:
    line = '(device.extensionAttribute15 -startsWith "Region=NCR|Department=IT|")'
    assert lint.scan_text(line, "rules.yaml") == []


def test_flags_unterminated_azure_policy_like() -> None:
    line = '        "like": "Region=NCR|Department=IT*"'
    findings = lint.scan_text(line, "policy.json")
    assert len(findings) == 1


def test_passes_terminated_azure_policy_like() -> None:
    line = '        "like": "Region=NCR|Department=IT|*"'
    assert lint.scan_text(line, "policy.json") == []


def test_passes_kusto_startswith() -> None:
    good = '| where tags["OrgPath"] startswith "Region=NCR|Department=IT|"'
    bad = '| where tags["OrgPath"] startswith "Region=NCR|Department=IT"'
    assert lint.scan_text(good, "report.kql") == []
    assert len(lint.scan_text(bad, "report.kql")) == 1


def test_yaml_predicate_style_covered() -> None:
    # Canon rule-library predicate shape (UIAO_152 / UIAO_153):
    #   - { facet: org_path, op: -startsWith, value: "…" }
    good = '        - { facet: org_path, op: -startsWith, value: "Region=NCR|Department=IT|" }'
    bad = '        - { facet: org_path, op: -startsWith, value: "Region=NCR|Department=IT" }'
    assert lint.scan_text(good, "dynamic-groups.yaml") == []
    assert len(lint.scan_text(bad, "dynamic-groups.yaml")) == 1


def test_ignores_non_orgpath_startswith() -> None:
    # Graph display-name filters and legacy composite paths are not prefixes
    # of the hybrid derived path.
    lines = "\n".join(
        [
            "$filter=startsWith(displayName,'CERT-')",
            '(device.extensionAttribute1 -startsWith "ORG-FIN")',
            '(user.extension_abc_OrgPath -startsWith "/Root/Finance/")',
        ]
    )
    assert lint.scan_text(lines, "legacy.qmd") == []


def test_allow_marker_exempts_line() -> None:
    line = '-startsWith "Division=East"  # deliberately broken example, orgpath-prefix-allow'
    assert lint.scan_text(line, "doc.qmd") == []


# ---------------------------------------------------------------------------
# Repo gate — the corpus must be clean
# ---------------------------------------------------------------------------


def test_repo_has_no_malformed_orgpath_prefixes() -> None:
    root = lint.repo_root()
    anchor = lint.anchor_label(root)
    findings: list[str] = []
    for path in lint.iter_scan_files(root):
        text = path.read_text(encoding="utf-8", errors="replace")
        findings.extend(lint.scan_text(text, str(path.relative_to(root)), anchor))
    assert findings == [], "\n".join(findings)


# ---------------------------------------------------------------------------
# Anchoring — a mid-path prefix is well-formed and matches nothing
# ---------------------------------------------------------------------------


def test_anchor_label_comes_from_the_codebook() -> None:
    # Read from the SSOT, not hard-coded, so extending derived_from cannot
    # leave the guard checking a stale anchor.
    assert lint.anchor_label(lint.repo_root()) == "Region"


def test_mid_path_prefix_is_flagged() -> None:
    # The exact defect this rule exists for: well-formed, delimiter-terminated,
    # invisible to the slot guard, and matches nobody because the derived path
    # is composed Region-first.
    line = '\'(user.extensionAttribute15 -startsWith "Department=Finance|")\''
    findings = lint.scan_text(line, "runbook.md", "Region")
    assert len(findings) == 1
    assert "does not start at 'Region='" in findings[0]


def test_anchored_prefixes_pass() -> None:
    for value in (
        '(user.extensionAttribute15 -startsWith "Region=NCR|")',
        '(user.extensionAttribute15 -startsWith "Region=NCR|Department=IT|")',
        '(d.extensionAttribute15 -startsWith "Region=NCR|Department=IT|Division=CyberOps|")',
        '"like": "Region=NCR|Department=IT|*"',
    ):
        assert lint.scan_text(value, "doc.qmd", "Region") == [], value


def test_anchor_rule_is_inert_when_the_codebook_declares_no_anchor() -> None:
    assert lint.scan_text('-startsWith "Department=Finance|"', "doc.qmd", "") == []


def test_allow_marker_exempts_an_unanchored_line() -> None:
    line = '-startsWith "Department=Finance|"  # broken on purpose, orgpath-prefix-allow'
    assert lint.scan_text(line, "doc.qmd", "Region") == []
