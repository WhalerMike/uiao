"""AI Inventory scanner — L1 (observe) drift detector for federal AI systems.

Ingests the OMB 2025 Federal AI Use Case Inventory CSV and produces a
ScanResult containing drift findings for every system that violates
M-25-21 identity governance obligations.

Operating mode: L1 (observe only). No writes. Per ADR-109 §3 and ADR-092,
promotion to L2/L3 requires a separate governance-board decision.

Usage::

    from uiao.governance.ai_inventory import scan_inventory

    result = scan_inventory("data/2025_individually_reported_AI_use_cases.csv")
    print(result.summary())
    for f in result.p1_findings:
        print(f.to_event())

Canon reference: UIAO_196, ADR-109
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Set

from uiao.governance.ai_inventory.drift import (
    finding_agentic_ungoverned,
    finding_ato_gap,
    finding_no_orgpath,
    finding_pii_no_pia,
    finding_shadow,
    finding_unowned,
)
from uiao.governance.ai_inventory.schema import (
    AgentClass,
    AISystemRecord,
    ATOStatus,
)
from uiao.governance.drift_core import Finding, Severity, events_json, gate

# ---------------------------------------------------------------------------
# ScanResult
# ---------------------------------------------------------------------------


@dataclass
class ScanResult:
    """Output of one AI inventory scan.

    Attributes
    ----------
    scanned_at:
        UTC timestamp of the scan run.
    source_path:
        Path to the OMB CSV that was ingested.
    inventory_vintage:
        Year of the inventory (from filename or caller-supplied).
    records:
        All AISystemRecords parsed from the CSV (live + retired).
    live_records:
        Subset of records where ``is_live`` is True (deployed + pilot).
    findings:
        All drift findings produced for the live population.
    gate_result:
        Halt-on-critical decision dict from ``drift_core.gate()``.
    """

    scanned_at: str
    source_path: str
    inventory_vintage: str
    records: list[AISystemRecord]
    live_records: list[AISystemRecord]
    findings: list[Finding]
    gate_result: dict

    # --- convenience views -----------------------------------------------

    @property
    def p1_findings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.P1]

    @property
    def p2_findings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.P2]

    @property
    def ato_gaps(self) -> list[Finding]:
        from uiao.governance.ai_inventory.drift import DRIFT_AI_ATO_GAP

        return [f for f in self.findings if f.drift_class == DRIFT_AI_ATO_GAP]

    @property
    def shadow_systems(self) -> list[Finding]:
        from uiao.governance.ai_inventory.drift import DRIFT_AI_SHADOW

        return [f for f in self.findings if f.drift_class == DRIFT_AI_SHADOW]

    @property
    def agentic_ungoverned(self) -> list[Finding]:
        from uiao.governance.ai_inventory.drift import DRIFT_AI_AGENTIC_UNGOVERNED

        return [f for f in self.findings if f.drift_class == DRIFT_AI_AGENTIC_UNGOVERNED]

    def summary(self) -> str:
        total = len(self.records)
        live = len(self.live_records)
        p1 = len(self.p1_findings)
        p2 = len(self.p2_findings)
        gate_dec = self.gate_result.get("decision", "UNKNOWN")
        lines = [
            f"AI Inventory Scan  {self.scanned_at}",
            f"  Source  : {self.source_path}",
            f"  Vintage : {self.inventory_vintage}",
            f"  Records : {total} total  {live} live (deployed + pilot)",
            f"  Findings: {len(self.findings)} total  P1={p1}  P2={p2}",
            f"  Gate    : {gate_dec}",
            "",
            "  Finding breakdown:",
            f"    ATO gaps             : {len(self.ato_gaps)}",
            f"    Agentic ungoverned   : {len(self.agentic_ungoverned)}",
            f"    Shadow systems (P1)  : {len(self.shadow_systems)}",
            f"    No OrgPath           : {sum(1 for f in self.findings if 'no-orgpath' in f.drift_class)}",
            f"    Unowned              : {sum(1 for f in self.findings if 'unowned' in f.drift_class)}",
            f"    PII / no PIA         : {sum(1 for f in self.findings if 'pii-no-pia' in f.drift_class)}",
        ]
        return "\n".join(lines)

    def to_json(self) -> str:
        return json.dumps(
            {
                "scanned_at": self.scanned_at,
                "source_path": self.source_path,
                "inventory_vintage": self.inventory_vintage,
                "gate": self.gate_result,
                "counts": {
                    "total_records": len(self.records),
                    "live_records": len(self.live_records),
                    "findings": len(self.findings),
                    "p1": len(self.p1_findings),
                    "p2": len(self.p2_findings),
                },
                "findings": json.loads(events_json(self.findings)),
            },
            indent=2,
        )


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------


def _load_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def _infer_vintage(path: Path) -> str:
    """Extract year from filename like 2025_individually_reported_…csv."""
    stem = path.stem
    for part in stem.split("_"):
        if part.isdigit() and len(part) == 4:
            return part
    return "unknown"


def scan_inventory(
    csv_path: str | Path,
    *,
    known_registry_ids: Set[str] | None = None,
    evidence_ref: str = "omg-inventory",
    vintage: str | None = None,
) -> ScanResult:
    """Run the L1 AI identity drift scan against one OMB inventory CSV.

    Parameters
    ----------
    csv_path:
        Local path to the OMB ``2025_individually_reported_AI_use_cases.csv``
        (or the equivalent for a future vintage).
    known_registry_ids:
        Optional set of ``system_name_ato`` values already in UIAO's
        machine-identity registry. When supplied, the scanner emits
        ``DRIFT-IDENTITY::ai-shadow`` P1 findings for registry entries
        absent from the OMB CSV. Pass None to skip shadow detection.
    evidence_ref:
        Provenance tag embedded in every Finding for downstream
        evidence-bundle correlation.
    vintage:
        Four-digit inventory year string.  Inferred from filename when
        omitted.

    Returns
    -------
    ScanResult
        Contains all records, live records, findings, and gate decision.
        No writes are made; the scan is read-only (L1 per ADR-109 §3).
    """
    path = Path(csv_path)
    rows = _load_csv(path)
    inv_vintage = vintage or _infer_vintage(path)

    records: list[AISystemRecord] = [AISystemRecord.from_csv_row(r) for r in rows]
    live: list[AISystemRecord] = [r for r in records if r.is_live]

    findings: list[Finding] = []

    # Track inventory system_name_ato values for shadow detection
    inventory_ato_names: Set[str] = set()

    for rec in live:
        if rec.system_name_ato:
            inventory_ato_names.add(rec.system_name_ato)

        # --- P1: agentic AI without ATO ---------------------------------
        if rec.agent_class is AgentClass.AGENTIC and rec.ato_status is not ATOStatus.YES:
            findings.append(finding_agentic_ungoverned(rec, evidence_ref))
            # Still emit the ATO gap separately so it appears in ato_gaps
            # count even when it was already caught by agentic check.

        # --- P2: ATO gap ------------------------------------------------
        if rec.ato_status is ATOStatus.NO:
            findings.append(finding_ato_gap(rec, evidence_ref))

        # --- P2: no OrgPath (agency/bureau blank) -----------------------
        if rec.orgpath is None:
            findings.append(finding_no_orgpath(rec, evidence_ref))

        # --- P2: unowned ------------------------------------------------
        if not rec.contact_email:
            findings.append(finding_unowned(rec, evidence_ref))

        # --- P2: PII present but no PIA ---------------------------------
        if rec.has_pii and not rec.pia_url:
            findings.append(finding_pii_no_pia(rec, evidence_ref))

    # --- P1: shadow AI detection ----------------------------------------
    # Systems in UIAO registry that OMB does not know about.
    if known_registry_ids is not None:
        for registry_id in known_registry_ids:
            if registry_id not in inventory_ato_names:
                findings.append(
                    finding_shadow(
                        system_name=registry_id,
                        evidence_ref="uiao-registry",
                    )
                )

    gate_result = gate(findings)
    now = datetime.now(timezone.utc).isoformat()

    return ScanResult(
        scanned_at=now,
        source_path=str(path),
        inventory_vintage=inv_vintage,
        records=records,
        live_records=live,
        findings=findings,
        gate_result=gate_result,
    )
