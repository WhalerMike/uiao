"""Tests for the UIAO link registry (UIAO_145 / ADR-132 Phase 1).

Covers:
- The link-registry JSON Schema meta-validates as Draft 2020-12
- The shipped ``src/uiao/canon/link-registry.yaml`` validates against it
- A minimal valid link entry passes; targeted mutations fail
  (unknown counterparty class, unknown ssot-stance, missing
  agreement fields, bad control pattern, additionalProperties)
- The substrate walker's ``_scan_link_registry`` emits the UIAO_145 §4
  findings: undeclared stance (P2), unknown stance value (P3), missing
  agreement block (P2), ``unrecorded`` agreement (P3), malformed
  next-review (P3), dangling authorized-by path (DRIFT-PROVENANCE P2)
- The shipped registry produces no P1/P2 walker findings (baseline
  hygiene: backfilled links declare stance, agreement, and resolvable
  authorizations)
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator

from uiao.substrate.walker import SubstrateReport, _scan_link_registry

REPO_ROOT = Path(__file__).parent.parent
SCHEMA_PATH = REPO_ROOT / "src" / "uiao" / "schemas" / "link-registry" / "link-registry.schema.json"
REGISTRY_PATH = REPO_ROOT / "src" / "uiao" / "canon" / "link-registry.yaml"


def _load_schema() -> dict[str, Any]:
    result: dict[str, Any] = json.loads(SCHEMA_PATH.read_text())
    return result


_MINIMAL_VALID_LINK: dict[str, Any] = {
    "id": "example-partner-exchange",
    "name": "Example partner data exchange",
    "counterparty": {"name": "Example Partner Agency", "class": "federal-agency"},
    "direction": "inbound",
    "ssot-stance": "they-are-source",
    "status": "active",
    "agreement": {
        "type": "mou",
        "artifact-location": "src/uiao/canon/specs/single-ato-reciprocity-model.md",
        "provenance-anchored": True,
    },
    "controls": ["CA-3"],
    "authorized-by": ["src/uiao/canon/adr/adr-132-orglink-link-object-class.md"],
}


def _registry_with(link: dict[str, Any]) -> dict[str, Any]:
    return {"schema-version": "1.0.0", "updated": "2026-07-25", "links": [link]}


# ---------------------------------------------------------------------------
# Schema-level tests
# ---------------------------------------------------------------------------


def test_schema_meta_validates() -> None:
    Draft202012Validator.check_schema(_load_schema())


def test_shipped_registry_validates() -> None:
    validator = Draft202012Validator(_load_schema())
    data = yaml.safe_load(REGISTRY_PATH.read_text())
    errors = list(validator.iter_errors(data))
    assert not errors, [e.message for e in errors]


def test_shipped_registry_link_ids_unique() -> None:
    data = yaml.safe_load(REGISTRY_PATH.read_text())
    ids = [entry["id"] for entry in data["links"]]
    assert len(ids) == len(set(ids))


def test_minimal_valid_link_passes() -> None:
    validator = Draft202012Validator(_load_schema())
    errors = list(validator.iter_errors(_registry_with(_MINIMAL_VALID_LINK)))
    assert not errors, [e.message for e in errors]


@pytest.mark.parametrize(
    ("mutation", "value"),
    [
        (("counterparty", "class"), "galactic-federation"),
        (("ssot-stance",), "maybe-source"),
        (("direction",), "sideways"),
        (("status",), "zombie"),
        (("controls",), ["ca-3"]),
        (("agreement", "type"), "handshake"),
    ],
)
def test_invalid_enum_values_fail(mutation: tuple[str, ...], value: Any) -> None:
    link = copy.deepcopy(_MINIMAL_VALID_LINK)
    target: Any = link
    for key in mutation[:-1]:
        target = target[key]
    target[mutation[-1]] = value
    validator = Draft202012Validator(_load_schema())
    assert list(validator.iter_errors(_registry_with(link)))


def test_missing_required_agreement_fields_fail() -> None:
    link = copy.deepcopy(_MINIMAL_VALID_LINK)
    del link["agreement"]["provenance-anchored"]
    validator = Draft202012Validator(_load_schema())
    assert list(validator.iter_errors(_registry_with(link)))


def test_empty_authorized_by_fails() -> None:
    link = copy.deepcopy(_MINIMAL_VALID_LINK)
    link["authorized-by"] = []
    validator = Draft202012Validator(_load_schema())
    assert list(validator.iter_errors(_registry_with(link)))


def test_additional_properties_rejected() -> None:
    link = copy.deepcopy(_MINIMAL_VALID_LINK)
    link["payload-sample"] = {"ssn": "000-00-0000"}
    validator = Draft202012Validator(_load_schema())
    assert list(validator.iter_errors(_registry_with(link)))


# ---------------------------------------------------------------------------
# Walker-scan tests
# ---------------------------------------------------------------------------


def _write_registry(tmp_path: Path, links: list[dict[str, Any]]) -> Path:
    reg_dir = tmp_path / "src" / "uiao" / "canon"
    reg_dir.mkdir(parents=True, exist_ok=True)
    body = {"schema-version": "1.0.0", "updated": "2026-07-25", "links": links}
    (reg_dir / "link-registry.yaml").write_text(yaml.safe_dump(body))
    return tmp_path


def _scan(tmp_path: Path) -> SubstrateReport:
    report = SubstrateReport(workspace_root=tmp_path, manifest_present=True, contract_present=True)
    _scan_link_registry(tmp_path, report)
    return report


def _walker_link(**overrides: Any) -> dict[str, Any]:
    link = copy.deepcopy(_MINIMAL_VALID_LINK)
    link.update(overrides)
    return link


def _touch(tmp_path: Path, rel: str) -> None:
    target = tmp_path / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("stub")


def test_walker_missing_registry_is_not_a_finding(tmp_path: Path) -> None:
    report = _scan(tmp_path)
    assert report.ok


def test_walker_clean_link_yields_no_findings(tmp_path: Path) -> None:
    root = _write_registry(tmp_path, [_walker_link()])
    _touch(root, _MINIMAL_VALID_LINK["authorized-by"][0])
    report = _scan(root)
    assert report.ok, [f.detail for f in report.findings]


def test_walker_flags_undeclared_stance_p2(tmp_path: Path) -> None:
    link = _walker_link()
    del link["ssot-stance"]
    root = _write_registry(tmp_path, [link])
    _touch(root, link["authorized-by"][0])
    report = _scan(root)
    assert any(
        f.severity == "P2" and f.drift_class == "DRIFT-SCHEMA" and "ssot-stance" in f.detail for f in report.findings
    )


def test_walker_flags_unknown_stance_p3(tmp_path: Path) -> None:
    link = _walker_link(**{"ssot-stance": "maybe-source"})
    root = _write_registry(tmp_path, [link])
    _touch(root, link["authorized-by"][0])
    report = _scan(root)
    assert any(f.severity == "P3" and "unknown ssot-stance" in f.detail for f in report.findings)


def test_walker_flags_missing_agreement_p2(tmp_path: Path) -> None:
    link = _walker_link()
    del link["agreement"]
    root = _write_registry(tmp_path, [link])
    _touch(root, link["authorized-by"][0])
    report = _scan(root)
    assert any(f.severity == "P2" and "no agreement" in f.detail for f in report.findings)


def test_walker_flags_unrecorded_agreement_p3(tmp_path: Path) -> None:
    link = _walker_link()
    link["agreement"] = {
        "type": "unrecorded",
        "artifact-location": "SharePoint > somewhere",
        "provenance-anchored": False,
    }
    root = _write_registry(tmp_path, [link])
    _touch(root, link["authorized-by"][0])
    report = _scan(root)
    assert any(f.severity == "P3" and "unrecorded" in f.detail for f in report.findings)


def test_walker_flags_malformed_next_review_p3(tmp_path: Path) -> None:
    link = _walker_link()
    link["agreement"]["next-review"] = "next spring"
    root = _write_registry(tmp_path, [link])
    _touch(root, link["authorized-by"][0])
    report = _scan(root)
    assert any(f.severity == "P3" and "next-review" in f.detail for f in report.findings)


def test_walker_flags_dangling_authorization_provenance_p2(tmp_path: Path) -> None:
    link = _walker_link(**{"authorized-by": ["src/uiao/canon/adr/adr-999-does-not-exist.md"]})
    root = _write_registry(tmp_path, [link])
    report = _scan(root)
    assert any(
        f.drift_class == "DRIFT-PROVENANCE" and f.severity == "P2" and "adr-999" in f.detail for f in report.findings
    )


def test_walker_skips_inactive_links_for_active_only_rules(tmp_path: Path) -> None:
    link = _walker_link(status="proposed")
    del link["ssot-stance"]
    del link["agreement"]
    root = _write_registry(tmp_path, [link])
    _touch(root, link["authorized-by"][0])
    report = _scan(root)
    assert not [f for f in report.findings if f.severity in ("P1", "P2")], [f.detail for f in report.findings]


def test_shipped_registry_has_no_p1_or_p2_walker_findings() -> None:
    report = SubstrateReport(workspace_root=REPO_ROOT, manifest_present=True, contract_present=True)
    _scan_link_registry(REPO_ROOT, report)
    blockers = [f for f in report.findings if f.severity in ("P1", "P2")]
    assert not blockers, [f.detail for f in blockers]
