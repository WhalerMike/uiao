"""Smoke tests for scripts/conmon/aggregate.py.

Covers three paths:

1. Registry-only (no evidence tree): every CA-7 adapter surfaces as a
   card with `last_run_at: null` and zero finding counts; POA&M CSV has
   only a header; SLA issue list is empty.

2. Evidence present + fresh critical finding (inside 72-hour window):
   card counts reflect the finding; no SLA breach emitted.

3. Evidence present + stale critical finding (outside 72-hour window,
   unacknowledged): SLA issue payload emitted with a stable
   fingerprint.

These tests run without any `uiao` package imports — the aggregator is
pure stdlib + PyYAML.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import pathlib
import sys
import textwrap

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
AGGREGATE_PATH = REPO_ROOT / "scripts" / "conmon" / "aggregate.py"


def _load_aggregate_module():
    spec = importlib.util.spec_from_file_location("conmon_aggregate", AGGREGATE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["conmon_aggregate"] = module  # needed for @dataclass lookup
    spec.loader.exec_module(module)
    return module


aggregate = _load_aggregate_module()


REGISTRY_YAML = textwrap.dedent(
    """
    schema-version: "1.0.0"
    registry-class: conformance
    updated: "2026-04-21"
    adapters:
      - id: scubagear
        name: CISA ScubaGear
        class: conformance
        mission-class: policy
        status: active
        controls:
          - CA-7
        gcc-boundary: gcc-moderate
        ssot-mutation: never
        certificate-anchored: true
        object-identity-only: true
        notes: |
          fedramp-rfc-0026 (advisory):
            requirement: RV5-CA07-VLN
            pathway: pathway-2-traditional
            planned-pathway: pathway-1-modernized
            pathway-transition-trigger: VDR release
      - id: not-ca7
        name: Unrelated adapter
        class: conformance
        mission-class: telemetry
        status: reserved
        controls:
          - RA-5
        gcc-boundary: gcc-moderate
        ssot-mutation: never
        certificate-anchored: true
        object-identity-only: true
    """
).strip()


def _write_registry(tmp_path: pathlib.Path) -> pathlib.Path:
    registry = tmp_path / "adapter-registry.yaml"
    registry.write_text(REGISTRY_YAML, encoding="utf-8")
    return registry


def _read_summary(output_dir: pathlib.Path) -> dict:
    return json.loads((output_dir / "conmon-aggregate-summary.json").read_text())


def _read_sla(output_dir: pathlib.Path) -> list[dict]:
    return json.loads((output_dir / "conmon-sla-issues.json").read_text())


def _read_poam_rows(output_dir: pathlib.Path) -> list[dict]:
    with (output_dir / "conmon-poam.csv").open("r", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_registry_only_no_evidence(tmp_path):
    registry = _write_registry(tmp_path)
    output_dir = tmp_path / "out"
    evidence_root = tmp_path / "evidence" / "conformance"

    rc = aggregate.main(
        [
            "--registry",
            str(registry),
            "--evidence-root",
            str(evidence_root),
            "--output-dir",
            str(output_dir),
            "--now",
            "2026-04-21T12:00:00Z",
        ]
    )
    assert rc == 0

    summary = _read_summary(output_dir)
    ids = [c["id"] for c in summary["adapters"]]
    assert ids == ["scubagear"], "only CA-7-tagged adapters should appear"
    card = summary["adapters"][0]
    assert card["last_run_at"] is None
    assert card["sla_breach_count"] == 0
    assert card["pathway"] == "pathway-2-traditional"
    assert card["requirement"] == "RV5-CA07-VLN"
    assert sum(card["finding_counts"].values()) == 0

    assert _read_poam_rows(output_dir) == []
    assert _read_sla(output_dir) == []


def _write_findings(evidence_root: pathlib.Path, adapter_id: str, findings: list[dict]) -> pathlib.Path:
    run_dir = evidence_root / adapter_id / "2026-04"
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "findings.json"
    path.write_text(json.dumps({"findings": findings}), encoding="utf-8")
    return path


def test_fresh_critical_inside_sla(tmp_path):
    registry = _write_registry(tmp_path)
    evidence_root = tmp_path / "evidence" / "conformance"
    _write_findings(
        evidence_root,
        "scubagear",
        [
            {
                "id": "f-001",
                "rule": "SCUBA.AAD.2.1",
                "severity": "critical",
                "title": "fresh critical",
                "detected_at": "2026-04-21T06:00:00Z",
            }
        ],
    )

    rc = aggregate.main(
        [
            "--registry",
            str(registry),
            "--evidence-root",
            str(evidence_root),
            "--output-dir",
            str(tmp_path / "out"),
            "--now",
            "2026-04-21T12:00:00Z",  # 6h later — well inside 72h
        ]
    )
    assert rc == 0

    summary = _read_summary(tmp_path / "out")
    card = summary["adapters"][0]
    assert card["finding_counts"]["critical"] == 1
    assert card["sla_breach_count"] == 0
    assert _read_sla(tmp_path / "out") == []

    rows = _read_poam_rows(tmp_path / "out")
    assert len(rows) == 1
    assert rows[0]["severity"] == "critical"
    assert rows[0]["requirement"] == "RV5-CA07-VLN"


def test_stale_critical_breaches_sla(tmp_path):
    registry = _write_registry(tmp_path)
    evidence_root = tmp_path / "evidence" / "conformance"
    _write_findings(
        evidence_root,
        "scubagear",
        [
            {
                "id": "f-002",
                "rule": "SCUBA.AAD.3.5",
                "severity": "critical",
                "title": "stale critical",
                "detected_at": "2026-04-18T12:00:00Z",  # 72h+ before "now"
            }
        ],
    )

    rc = aggregate.main(
        [
            "--registry",
            str(registry),
            "--evidence-root",
            str(evidence_root),
            "--output-dir",
            str(tmp_path / "out"),
            "--now",
            "2026-04-21T12:30:00Z",  # 72.5h later
        ]
    )
    assert rc == 0

    summary = _read_summary(tmp_path / "out")
    assert summary["adapters"][0]["sla_breach_count"] == 1

    sla = _read_sla(tmp_path / "out")
    assert len(sla) == 1
    assert sla[0]["adapter"] == "scubagear"
    assert "conmon-cure" in sla[0]["labels"]
    assert len(sla[0]["fingerprint"]) == 16


def test_acknowledged_critical_does_not_breach(tmp_path):
    registry = _write_registry(tmp_path)
    evidence_root = tmp_path / "evidence" / "conformance"
    _write_findings(
        evidence_root,
        "scubagear",
        [
            {
                "id": "f-003",
                "severity": "critical",
                "detected_at": "2026-04-10T00:00:00Z",  # old
                "acknowledged_at": "2026-04-10T06:00:00Z",
            }
        ],
    )

    rc = aggregate.main(
        [
            "--registry",
            str(registry),
            "--evidence-root",
            str(evidence_root),
            "--output-dir",
            str(tmp_path / "out"),
            "--now",
            "2026-04-21T12:00:00Z",
        ]
    )
    assert rc == 0
    assert _read_sla(tmp_path / "out") == []


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
