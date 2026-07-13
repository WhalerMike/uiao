"""Identity Governance Pipeline — orchestrates the full JML + orphan detection run.

Single entry point for the scheduled identity governance job.  Runs:
  1. Human JML: diff current vs prior HRIT snapshot → joiner/mover/leaver events
  2. Orphan detection: cross-reference service identity snapshot with LEAVER ids
  3. Evidence artifacts: write JSON logs to output directory
  4. Gate evaluation: return non-zero exit status if P1 findings are present

Designed to be called from a CI job, cron, or ServiceNow webhook.  The gate
result (exit 1 on P1) is what makes "UIAO governance didn't run" observable
without reading logs.

Actuation tier: L2 (Advise) — pipeline produces findings and evidence;
it changes nothing.  See UIAO_200 for tier mapping.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from uiao.adapters.modernization.hrit.inventory import HRRecord
from uiao.adapters.modernization.hrit.quarantine import (
    QuarantineConfig,
    QuarantineReport,
    evaluate_hr_quarantine,
)
from uiao.governance.identity.jml import HumanJMLEventSet, detect_events
from uiao.governance.identity.jml import write_evidence_artifacts as write_human_artifacts
from uiao.governance.identity.service_identity import (
    ServiceIdentityEventSet,
    ServiceIdentityRecord,
    detect_service_events,
)
from uiao.governance.identity.service_identity import (
    write_evidence_artifacts as write_service_artifacts,
)

# ---------------------------------------------------------------------------
# Gate result
# ---------------------------------------------------------------------------


@dataclass
class GateResult:
    """Outcome of one identity governance pipeline run."""

    p1_count: int
    p2_count: int
    human_events: HumanJMLEventSet
    service_events: ServiceIdentityEventSet
    evidence_paths: list[Path] = field(default_factory=list)
    gate_passed: bool = True
    summary_lines: list[str] = field(default_factory=list)
    quarantine: QuarantineReport | None = None

    @property
    def quarantined_ids(self) -> list[str]:
        """Employee ids the HR-quarantine gate held — must NOT be provisioned."""
        return list(self.quarantine.held) if self.quarantine is not None else []

    def to_dict(self) -> dict:
        d = {
            "gate_passed": self.gate_passed,
            "p1_count": self.p1_count,
            "p2_count": self.p2_count,
            "human": {
                "joiners": len(self.human_events.joiners),
                "movers": len(self.human_events.movers),
                "leavers": len(self.human_events.leavers),
                "pending_leavers": len(self.human_events.pending_leavers),
            },
            "service": {
                "created": len(self.service_events.created),
                "owner_changed": len(self.service_events.owner_changed),
                "expiring": len(self.service_events.expiring),
                "orphaned": len(self.service_events.orphaned),
            },
            "evidence_paths": [str(p) for p in self.evidence_paths],
        }
        if self.quarantine is not None:
            d["quarantine"] = {
                "held": list(self.quarantine.held),
                "held_count": self.quarantine.held_count,
                "cleared_count": self.quarantine.cleared_count,
                "reason_counts": self.quarantine.reason_counts(),
            }
        return d

    def write_gate_report(self, output_dir: Path) -> Path:
        """Write gate-report.json to output_dir."""
        report_path = output_dir / "gate-report.json"
        report_path.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return report_path


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _latest_extracted_at(records: list[HRRecord]) -> str:
    """Newest ``extracted_at`` across records ("as of this extract").

    Used as the default clock for the HR-quarantine staleness check so a run
    is deterministic and replayable. Empty when there are no records (the gate
    then cannot compute an age and skips the staleness check).
    """
    stamps = [r.extracted_at for r in records if r.extracted_at]
    return max(stamps) if stamps else ""


def run_pipeline(
    current_hrit: list[HRRecord],
    current_services: list[ServiceIdentityRecord],
    *,
    prior_hrit: list[HRRecord] | None = None,
    prior_services: list[ServiceIdentityRecord] | None = None,
    output_dir: str | Path | None = None,
    fail_on_p1: bool = True,
    now: str | None = None,
    quarantine_config: QuarantineConfig | None = None,
) -> GateResult:
    """Run the full identity governance pipeline.

    Parameters
    ----------
    current_hrit:
        HR records from the current HRIT extract.
    current_services:
        Service identity records from the current principal inventory.
    prior_hrit:
        HR records from the prior HRIT extract.  None on first run (all
        active records treated as joiners).
    prior_services:
        Service identity records from the prior inventory run.  None on
        first run (all active accounts treated as CREATED).
    output_dir:
        Directory to write evidence artifacts and gate report.  Created
        if it does not exist.  If None, no artifacts are written.
    fail_on_p1:
        When True (default), ``GateResult.gate_passed`` is False if any
        P1 findings are present.  The CLI uses this to set exit code 1.
    now:
        Current time (ISO-8601) for the HR-quarantine staleness check.  When
        None, defaults to the newest ``extracted_at`` across ``current_hrit``
        (i.e. "as of this extract"), keeping the run deterministic and
        replayable in evidence.
    quarantine_config:
        Threshold overrides for the HR-quarantine gate.  Defaults are
        conservative (see ``QuarantineConfig``).

    Returns
    -------
    GateResult
    """
    # --- Step 0: HR-feed quarantine gate -------------------------------------
    # Hold records unsafe to provision from (stale snapshot, null placement,
    # improbable OrgPath move) BEFORE the JML diff acts on them.  Prior
    # placements come from the prior HRIT snapshot's resolved OrgPaths.
    prior_placements = {
        r.employee_id: r.resolved_orgpath
        for r in (prior_hrit or [])
        if r.resolved_orgpath
    }
    quarantine_now = now if now is not None else _latest_extracted_at(current_hrit)
    quarantine = evaluate_hr_quarantine(
        current_hrit,
        now=quarantine_now,
        prior_placements=prior_placements,
        config=quarantine_config,
    )

    # --- Step 1: human JML ---------------------------------------------------
    human_events = detect_events(current_hrit, prior_hrit)

    # --- Step 2: service identity (orphan + lifecycle) -----------------------
    leaver_ids = {ev.record.employee_id for ev in human_events.leavers}
    # Also include pending leavers (advance-notice window): their accounts
    # should be flagged for pre-emptive custody transfer.
    leaver_ids |= {ev.record.employee_id for ev in human_events.pending_leavers if ev.pending_leaver}

    service_events = detect_service_events(
        current_services,
        prior_services,
        leaver_employee_ids=leaver_ids,
    )

    # --- Step 3: collect findings --------------------------------------------
    human_findings = human_events.all_findings
    service_findings = service_events.all_findings

    p1_count = sum(1 for f in human_findings + service_findings if f.severity.value == "P1")
    p2_count = sum(1 for f in human_findings + service_findings if f.severity.value == "P2")

    # Quarantine findings carry plain string severities (P1 | P2); count them
    # alongside the enum-severity JML/service findings so the gate sees them.
    p1_count += sum(1 for f in quarantine.findings if f.severity == "P1")
    p2_count += sum(1 for f in quarantine.findings if f.severity == "P2")

    gate_passed = not (fail_on_p1 and p1_count > 0)

    # --- Step 4: summary lines -----------------------------------------------
    summary_lines = [
        human_events.summary(),
        service_events.summary(),
        f"HR quarantine: {quarantine.held_count} held, {quarantine.cleared_count} cleared.",
        f"Findings: {p1_count} P1, {p2_count} P2.",
        "GATE: PASSED" if gate_passed else f"GATE: FAILED — {p1_count} P1 finding(s) require immediate action.",
    ]

    # --- Step 5: evidence artifacts ------------------------------------------
    evidence_paths: list[Path] = []
    if output_dir is not None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        evidence_paths.extend(write_human_artifacts(human_events, out))
        evidence_paths.extend(write_service_artifacts(service_events, out))

    result = GateResult(
        p1_count=p1_count,
        p2_count=p2_count,
        human_events=human_events,
        service_events=service_events,
        evidence_paths=evidence_paths,
        gate_passed=gate_passed,
        summary_lines=summary_lines,
        quarantine=quarantine,
    )

    if output_dir is not None:
        report_path = result.write_gate_report(Path(output_dir))
        evidence_paths.append(report_path)

    return result


# ---------------------------------------------------------------------------
# Snapshot loaders (JSON round-trip for CLI / pipeline use)
# ---------------------------------------------------------------------------


def hrit_records_from_json(path: str | Path) -> list[HRRecord]:
    """Load HRIT records from a JSON file produced by the HRIT extractor.

    Expected shape: ``{"records": [{...HRRecord fields...}]}``
    or a bare list ``[{...}]``.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = data if isinstance(data, list) else data.get("records", [])
    return [
        HRRecord(
            employee_id=r["employee_id"],
            first_name=r.get("first_name", ""),
            last_name=r.get("last_name", ""),
            department=r.get("department", ""),
            hire_date=r.get("hire_date", ""),
            worker_type=r.get("worker_type", "FullTimeEmployee"),
            location_code=r.get("location_code", ""),
            country=r.get("country", "US"),
            employment_status=r.get("employment_status", "Active"),
            extracted_at=r.get("extracted_at", ""),
            division=r.get("division"),
            organization_code=r.get("organization_code"),
            cost_center=r.get("cost_center"),
            job_title=r.get("job_title"),
            manager_employee_id=r.get("manager_employee_id"),
            termination_date=r.get("termination_date"),
            resolved_orgpath=r.get("resolved_orgpath"),
        )
        for r in rows
    ]


def service_records_from_json(path: str | Path) -> list[ServiceIdentityRecord]:
    """Load service identity records from a JSON file.

    Expected shape: ``{"principals": [{...}]}`` (AGD fixture format)
    or a bare list.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = data if isinstance(data, list) else data.get("principals", data.get("records", []))
    return [
        ServiceIdentityRecord(
            principal_id=r["principal_id"],
            display_name=r.get("display_name", r["principal_id"]),
            account_class=r.get("account_class", "ServicePrincipal"),
            department=r.get("department", ""),
            division=r.get("division"),
            cost_center=r.get("cost_center"),
            owner_employee_id=r.get("owner_employee_id"),
            owner_display_name=r.get("owner_display_name"),
            credential_expiry_date=r.get("credential_expiry_date"),
            last_rotation_date=r.get("last_rotation_date"),
            purpose=r.get("purpose"),
            orgpath=r.get("orgpath"),
            extracted_at=r.get("extracted_at", ""),
            is_active=r.get("is_active", True),
        )
        for r in rows
    ]
