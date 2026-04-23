"""UIAO ConMon aggregator for FedRAMP RFC-0026 CA-7 Pathway 2.

Consumes per-adapter `findings.json` artifacts under
`evidence/conformance/<adapter-id>/<run-id>/findings.json`, cross-walks
them against `src/uiao/canon/adapter-registry.yaml` (RFC-0026 pathway
metadata), and emits three artifacts:

1. `conmon-poam.csv`
   Monthly POA&M rollup in the column shape FedRAMP expects.
   Intentionally a subset of the full POA&M template — the remaining
   columns are marked TODO in the header row and are wired up as the
   upstream template shape stabilizes (see UIAO_132 §7 O1).

2. `conmon-aggregate-summary.json`
   Dashboard-JSON card per ADR-043 D4 / UIAO_132 §5. One entry per
   CA-7-tagged conformance adapter, carrying: pathway posture, last
   findings run timestamp, finding counts by severity, and the current
   72-hour critical-finding SLA state.

3. `conmon-sla-issues.json`
   List of governance-issue payloads the calling workflow should open
   for any CRITICAL finding that has blown the 72-hour
   acknowledgement SLA (ADR-043 D2 / UIAO_132 §2.2). Idempotent:
   consumers are expected to dedupe on the `fingerprint` field.

Design:
- Pure stdlib + PyYAML. No `uiao` package import. Runs on a GitHub
  Actions runner with `pip install --quiet pyyaml` and nothing else.
- Missing evidence tree is NOT an error — reserved-slot adapters
  (`vuln-scan`, `stig-compliance`, `patch-state`, `intune`) have no
  findings yet. The dashboard card reflects this as
  `last_run: null, status: reserved`.
- Finds adapter entries by scanning adapter-registry.yaml for
  `controls` lists that include CA-7.

Usage:
    python scripts/conmon/aggregate.py \
        --registry src/uiao/canon/adapter-registry.yaml \
        --evidence-root evidence/conformance \
        --output-dir exports/conmon \
        --now 2026-04-21T12:00:00Z   # optional; defaults to UTC now

Exit codes:
    0 — artifacts emitted successfully (no SLA breach in this run
        does not change exit code; the workflow reads
        conmon-sla-issues.json and acts on it separately).
    1 — registry missing or malformed.
    2 — I/O failure writing outputs.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import datetime as dt
import hashlib
import json
import pathlib
import sys
from typing import Any

import yaml

# Severities handled in aggregation. The adapter emits whatever it
# emits — we normalize to this five-level scale before counting.
SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]

# 72-hour SLA per ADR-043 D2 / UIAO_132 §2.2. Self-imposed; applies
# only to CRITICAL-severity findings.
CRITICAL_SLA_HOURS = 72


@dataclasses.dataclass
class AdapterCard:
    """Dashboard card for a single CA-7-tagged conformance adapter."""

    id: str
    name: str
    status: str
    requirement: str | None
    pathway: str | None
    planned_pathway: str | None
    transition_trigger: str | None
    last_run_at: str | None
    finding_counts: dict[str, int]
    sla_breach_count: int

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--registry",
        type=pathlib.Path,
        default=pathlib.Path("src/uiao/canon/adapter-registry.yaml"),
        help="Path to the conformance adapter registry.",
    )
    parser.add_argument(
        "--evidence-root",
        type=pathlib.Path,
        default=pathlib.Path("evidence/conformance"),
        help="Root of per-adapter findings.json artifacts.",
    )
    parser.add_argument(
        "--output-dir",
        type=pathlib.Path,
        default=pathlib.Path("exports/conmon"),
        help="Destination directory for the three emitted artifacts.",
    )
    parser.add_argument(
        "--now",
        type=str,
        default=None,
        help="ISO 8601 UTC timestamp to treat as 'now' (test hook).",
    )
    return parser.parse_args(argv)


def utcnow(override: str | None) -> dt.datetime:
    if override:
        # Tolerate trailing Z; datetime.fromisoformat handles offsets
        # natively from 3.11 onward but not the Z shorthand.
        normalized = override.replace("Z", "+00:00")
        return dt.datetime.fromisoformat(normalized).astimezone(dt.timezone.utc)
    return dt.datetime.now(tz=dt.timezone.utc)


def load_registry(registry_path: pathlib.Path) -> list[dict[str, Any]]:
    if not registry_path.is_file():
        raise SystemExit(f"adapter registry not found: {registry_path}")
    with registry_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    adapters = data.get("adapters")
    if not isinstance(adapters, list):
        raise SystemExit(f"adapter registry malformed: {registry_path}")
    return adapters


def is_ca7_adapter(adapter: dict[str, Any]) -> bool:
    controls = adapter.get("controls") or []
    return "CA-7" in controls


def parse_rfc0026_block(notes: str | None) -> dict[str, str | None]:
    """Extract the RFC-0026 advisory block from an adapter's `notes`.

    The block is a convention today (ADR-043 N1): a YAML-ish key-value
    stanza under a `fedramp-rfc-0026:` header inside the free-text
    `notes` body. We parse it with a forgiving line-by-line scanner
    rather than treating `notes` as real YAML, because the surrounding
    prose is not valid YAML.
    """
    result: dict[str, str | None] = {
        "requirement": None,
        "pathway": None,
        "planned-pathway": None,
        "pathway-transition-trigger": None,
    }
    if not notes:
        return result
    in_block = False
    for raw_line in notes.splitlines():
        line = raw_line.rstrip()
        if not in_block:
            if line.strip().startswith("fedramp-rfc-0026"):
                in_block = True
            continue
        if not line.strip():
            continue
        stripped = line.lstrip()
        if ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        key = key.strip().lower()
        value = value.strip()
        if key in result:
            result[key] = value or None
    return result


def newest_findings(adapter_id: str, evidence_root: pathlib.Path) -> pathlib.Path | None:
    """Return the newest findings.json path for this adapter, or None."""
    adapter_dir = evidence_root / adapter_id
    if not adapter_dir.is_dir():
        return None
    candidates = sorted(
        adapter_dir.rglob("findings.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def load_findings(findings_path: pathlib.Path) -> list[dict[str, Any]]:
    with findings_path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("findings"), list):
        return payload["findings"]
    return []


def normalize_severity(raw: Any) -> str:
    if not isinstance(raw, str):
        return "info"
    value = raw.strip().lower()
    return value if value in SEVERITY_ORDER else "info"


def fingerprint(adapter_id: str, finding: dict[str, Any]) -> str:
    """Stable identifier for de-duping governance issues across runs."""
    parts = [
        adapter_id,
        str(finding.get("id", "")),
        str(finding.get("control", "")),
        str(finding.get("rule", "")),
        str(finding.get("target", "")),
    ]
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return digest[:16]


def iso(ts: dt.datetime) -> str:
    return ts.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def collect_adapter_state(
    adapter: dict[str, Any],
    evidence_root: pathlib.Path,
    now: dt.datetime,
) -> tuple[AdapterCard, list[dict[str, Any]], list[dict[str, Any]]]:
    """Build one dashboard card + its POA&M rows + its SLA issue payloads."""
    rfc = parse_rfc0026_block(adapter.get("notes"))
    adapter_id = str(adapter.get("id", "?"))
    findings_path = newest_findings(adapter_id, evidence_root)

    counts = {sev: 0 for sev in SEVERITY_ORDER}
    poam_rows: list[dict[str, Any]] = []
    sla_issues: list[dict[str, Any]] = []
    last_run_at: str | None = None

    if findings_path is None:
        card = AdapterCard(
            id=adapter_id,
            name=str(adapter.get("name", adapter_id)),
            status=str(adapter.get("status", "unknown")),
            requirement=rfc["requirement"],
            pathway=rfc["pathway"],
            planned_pathway=rfc["planned-pathway"],
            transition_trigger=rfc["pathway-transition-trigger"],
            last_run_at=None,
            finding_counts=counts,
            sla_breach_count=0,
        )
        return card, poam_rows, sla_issues

    last_run_at = iso(dt.datetime.fromtimestamp(findings_path.stat().st_mtime, tz=dt.timezone.utc))

    for finding in load_findings(findings_path):
        severity = normalize_severity(finding.get("severity"))
        counts[severity] = counts.get(severity, 0) + 1

        fp = fingerprint(adapter_id, finding)
        poam_rows.append(
            {
                "poam_id": fp,
                "adapter": adapter_id,
                "control": finding.get("control") or "CA-7",
                "rule": finding.get("rule", ""),
                "severity": severity,
                "title": finding.get("title", ""),
                "description": finding.get("description", ""),
                "target": finding.get("target", ""),
                "detected_at": finding.get("detected_at", last_run_at),
                "status": finding.get("status", "open"),
                "requirement": rfc["requirement"] or "",
                "pathway": rfc["pathway"] or "",
            }
        )

        if severity != "critical":
            continue
        ack_at = finding.get("acknowledged_at")
        detected_raw = finding.get("detected_at", last_run_at)
        try:
            detected_at = dt.datetime.fromisoformat(str(detected_raw).replace("Z", "+00:00"))
        except ValueError:
            continue
        if ack_at:
            continue
        age_hours = (now - detected_at).total_seconds() / 3600.0
        if age_hours < CRITICAL_SLA_HOURS:
            continue
        sla_issues.append(
            {
                "fingerprint": fp,
                "adapter": adapter_id,
                "title": f"[conmon-cure] {adapter_id} critical finding unacknowledged — {finding.get('title', fp)}",
                "labels": ["conmon-cure", "ca-7", "rfc-0026"],
                "body": _sla_issue_body(adapter_id, finding, rfc, age_hours),
            }
        )

    card = AdapterCard(
        id=adapter_id,
        name=str(adapter.get("name", adapter_id)),
        status=str(adapter.get("status", "unknown")),
        requirement=rfc["requirement"],
        pathway=rfc["pathway"],
        planned_pathway=rfc["planned-pathway"],
        transition_trigger=rfc["pathway-transition-trigger"],
        last_run_at=last_run_at,
        finding_counts=counts,
        sla_breach_count=len(sla_issues),
    )
    return card, poam_rows, sla_issues


def _sla_issue_body(
    adapter_id: str,
    finding: dict[str, Any],
    rfc: dict[str, str | None],
    age_hours: float,
) -> str:
    return (
        f"Critical finding from `{adapter_id}` has been unacknowledged for "
        f"{age_hours:.1f} hours (> {CRITICAL_SLA_HOURS}h SLA per ADR-043 D2).\n\n"
        f"- Requirement: {rfc['requirement'] or 'unknown'}\n"
        f"- Pathway: {rfc['pathway'] or 'unknown'}\n"
        f"- Rule: {finding.get('rule', '')}\n"
        f"- Target: {finding.get('target', '')}\n"
        f"- Detected: {finding.get('detected_at', 'unknown')}\n\n"
        f"Resolve per the 45-day cure window in "
        f"`docs/docs/conmon-corrective-action-playbook.qmd` — this issue is "
        f"the D+0 artifact for this finding."
    )


def write_poam_csv(rows: list[dict[str, Any]], out_path: pathlib.Path) -> None:
    fields = [
        "poam_id",
        "adapter",
        "control",
        "rule",
        "severity",
        "title",
        "description",
        "target",
        "detected_at",
        "status",
        "requirement",
        "pathway",
    ]
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def write_json(obj: Any, out_path: pathlib.Path) -> None:
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, sort_keys=True)
        fh.write("\n")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    now = utcnow(args.now)
    adapters = load_registry(args.registry)

    cards: list[dict[str, Any]] = []
    poam_rows: list[dict[str, Any]] = []
    sla_issues: list[dict[str, Any]] = []

    for adapter in adapters:
        if not is_ca7_adapter(adapter):
            continue
        card, rows, issues = collect_adapter_state(adapter, args.evidence_root, now)
        cards.append(card.to_dict())
        poam_rows.extend(rows)
        sla_issues.extend(issues)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    try:
        write_poam_csv(poam_rows, args.output_dir / "conmon-poam.csv")
        write_json(
            {
                "generated_at": iso(now),
                "rfc": "FedRAMP RFC-0026",
                "spec": "UIAO_132",
                "sla_hours_critical": CRITICAL_SLA_HOURS,
                "adapters": cards,
            },
            args.output_dir / "conmon-aggregate-summary.json",
        )
        write_json(sla_issues, args.output_dir / "conmon-sla-issues.json")
    except OSError as exc:
        print(f"ERROR: failed to write outputs: {exc}", file=sys.stderr)
        return 2

    print(f"conmon-aggregate: adapters={len(cards)} poam_rows={len(poam_rows)} sla_breaches={len(sla_issues)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
