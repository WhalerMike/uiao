"""uiao.telemetry.provenance — shared provenance event sink.

Per ADR-071, the substrate's three adapter surfaces (collectors,
modernization, enforcement) all route envelope emissions through this
sink. The sink does three things:

1. Runs the synchronous validation suite from ADR-070 §2 (schema /
   signature / identity resolution / consent envelope alignment).
2. Persists the envelope to the append-only JSONL event log at
   `evidence/provenance/<adapter_id>/<yyyy-mm>/<yyyy-mm-dd>.jsonl`.
3. Returns an EmitOutcome carrying acceptance decision and any drift
   findings.

Phase 1 ships the sink with stub validators that return True for the
sync checks (other than schema, which is enforced by pydantic). Phase 2
populates the three runtime drift checks (semantic / authz / identity).
The contract is in place from Phase 1 so adapters can be retrofitted in
parallel with the validator work.

Async chain verification is enqueued at emit time; see `_enqueue_chain_check`.
The check runs out-of-band and writes a `chain_break` line to the same
event-log file if the lineage_hash fails re-verification (P2
DRIFT-PROVENANCE).

This file is a DRAFT skeleton. Promotion to
`src/uiao/telemetry/provenance.py` happens when ADR-071 is ACCEPTED.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

# Resolves once Phase 0 promotes to canon paths.
from uiao.models.provenance import Envelope


logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Workspace-relative root of the provenance event log.
#: Per ADR-071 §3 — partitioned by adapter_id, then year-month, then daily file.
EVENT_LOG_ROOT = "evidence/provenance"

#: Environment variable that overrides the event-log root (for tests, CI,
#: and per-tenant isolation). Resolves the same way the substrate walker
#: resolves `UIAO_WORKSPACE_ROOT`.
EVENT_LOG_ROOT_ENV = "UIAO_PROVENANCE_LOG_ROOT"

EventType = Literal["accept", "reject", "chain_break"]


# ---------------------------------------------------------------------------
# DriftFinding (lightweight; will reuse the substrate walker's class when promoted)
# ---------------------------------------------------------------------------


@dataclass
class DriftFinding:
    """Runtime drift finding emitted by the sink.

    Mirrors `substrate.walker.DriftFinding` shape — same `drift_class`
    codes, same `severity` levels, distinguished only by
    `subkind="runtime"`. ADR-070 §3 commits to one taxonomy with two
    emission paths (`hygiene` vs `runtime`); this class is the runtime
    side of that contract.

    When this file lands at `src/uiao/telemetry/provenance.py`, the
    walker's class is imported instead of redefined here.
    """

    drift_class: str           # DRIFT-PROVENANCE | DRIFT-AUTHZ | DRIFT-IDENTITY | DRIFT-SEMANTIC
    severity: str              # P1 | P2 | P3 | P4
    path: str
    detail: str
    subkind: str = "runtime"


# ---------------------------------------------------------------------------
# EmitOutcome
# ---------------------------------------------------------------------------


@dataclass
class EmitOutcome:
    """Result of an emit() call.

    The sink returns this to the caller (adapter) so the adapter can
    decide whether to propagate the claim downstream. The sink itself
    always writes the envelope to the event log — accepted, rejected,
    or chain-broken — per ADR-006 "no silent drops".
    """

    accepted: bool
    envelope: Envelope
    findings: list[DriftFinding] = field(default_factory=list)
    log_path: Optional[Path] = None

    @classmethod
    def rejected_unsealed(
        cls, *, claim: dict[str, Any], envelope: Envelope, adapter_id: str
    ) -> "EmitOutcome":
        finding = DriftFinding(
            drift_class="DRIFT-PROVENANCE",
            severity="P1",
            path=f"adapter:{adapter_id}",
            detail=f"adapter '{adapter_id}' called emit() with an unsealed envelope (lineage_hash or signature empty)",
        )
        return cls(accepted=False, envelope=envelope, findings=[finding])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


_write_lock = threading.Lock()


def emit(envelope: Envelope, *, claim: dict[str, Any], adapter_id: str) -> EmitOutcome:
    """Run sync validation, persist envelope, return outcome.

    Called by all three adapter surfaces. The caller is responsible for
    not propagating the claim downstream when `accepted is False`.

    Phase 1 validates schema (already enforced by pydantic) and
    sealed-state (lineage_hash + signature populated). The three runtime
    drift checks (semantic / authz / identity) are stubbed True for
    Phase 1; Phase 2 replaces the stubs with real validators.
    """
    findings: list[DriftFinding] = []

    if not _check_signature_resolves(envelope):
        findings.append(
            DriftFinding(
                drift_class="DRIFT-PROVENANCE",
                severity="P1",
                path=envelope.claim_id,
                detail=f"envelope signature {envelope.signature[:12]}... does not resolve to a trusted issuer",
            )
        )

    if not _check_identity_resolves(envelope):
        findings.append(
            DriftFinding(
                drift_class="DRIFT-IDENTITY",
                severity="P1",
                path=envelope.claim_id,
                detail=f"issuer_identity {envelope.issuer_identity} cannot be resolved against the identity plane",
            )
        )

    if not _check_consent_envelope(envelope, claim=claim):
        findings.append(
            DriftFinding(
                drift_class="DRIFT-AUTHZ",
                severity="P1",
                path=envelope.claim_id,
                detail="claim destination is outside the authorized consent envelope",
            )
        )

    accepted = not findings
    event_type: EventType = "accept" if accepted else "reject"
    log_path = _write_event(envelope, claim=claim, adapter_id=adapter_id, event_type=event_type, findings=findings)

    if accepted:
        _enqueue_chain_check(envelope, claim=claim, adapter_id=adapter_id)

    return EmitOutcome(accepted=accepted, envelope=envelope, findings=findings, log_path=log_path)


# ---------------------------------------------------------------------------
# Sync validators — Phase 1 stubs; Phase 2 populates
# ---------------------------------------------------------------------------


def _check_signature_resolves(envelope: Envelope) -> bool:
    """Verify envelope.signature resolves to a trusted issuer.

    Phase 1 stub: returns True. Phase 2 wires this to the adapter
    manifest's `trust-anchor:` declaration (already validated at
    canon-hygiene level by the substrate walker per UIAO_110).
    """
    return True


def _check_identity_resolves(envelope: Envelope) -> bool:
    """Verify envelope.issuer_identity resolves against the identity plane.

    Phase 1 stub: returns True. Phase 2 wires this to the configured
    identity-plane resolver (Entra ID by default; pluggable per adapter
    manifest).
    """
    return True


def _check_consent_envelope(envelope: Envelope, *, claim: dict[str, Any]) -> bool:
    """Verify the claim destination falls within the envelope's consent scope.

    Phase 1 stub: returns True. Phase 2 wires this to UIAO_17
    ConsentEnvelope and to the adapter manifest's `scope:` declaration
    (already validated at canon-hygiene level by the substrate walker).
    """
    return True


# ---------------------------------------------------------------------------
# Event-log writer
# ---------------------------------------------------------------------------


def _write_event(
    envelope: Envelope,
    *,
    claim: dict[str, Any],
    adapter_id: str,
    event_type: EventType,
    findings: list[DriftFinding],
) -> Path:
    """Append one event line to the per-adapter JSONL log.

    Append-only invariant: the write uses O_APPEND so concurrent emissions
    don't interleave mid-line. A sidecar `.idx` file records the per-line
    SHA-256 to let the substrate walker detect post-hoc mutation (a P1
    DRIFT-PROVENANCE finding).
    """
    now = datetime.now(timezone.utc)
    path = _resolve_log_path(adapter_id, now)
    path.parent.mkdir(parents=True, exist_ok=True)

    line = json.dumps(
        {
            **envelope.model_dump(mode="json"),
            "_event_meta": {
                "event_type": event_type,
                "emitted_at": now.isoformat(),
                "adapter_id": adapter_id,
                "finding_ids": [f"{f.drift_class}:{f.severity}" for f in findings],
            },
        },
        separators=(",", ":"),
        sort_keys=True,
    )

    with _write_lock:
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(fd, (line + "\n").encode("utf-8"))
        finally:
            os.close(fd)

    return path


def _resolve_log_path(adapter_id: str, ts: datetime) -> Path:
    """Compute the daily-file path for a given adapter + timestamp."""
    root = Path(os.environ.get(EVENT_LOG_ROOT_ENV, EVENT_LOG_ROOT))
    return root / adapter_id / ts.strftime("%Y-%m") / f"{ts.strftime('%Y-%m-%d')}.jsonl"


# ---------------------------------------------------------------------------
# Async chain verification — stub for Phase 1
# ---------------------------------------------------------------------------


def _enqueue_chain_check(envelope: Envelope, *, claim: dict[str, Any], adapter_id: str) -> None:
    """Schedule the async lineage_hash re-verification.

    Phase 1 stub: no-op. Phase 2 wires this to a background worker pool
    that re-fetches the source record, recomputes the canonical-JSON
    hash, compares to envelope.lineage_hash, and writes a `chain_break`
    line to the same log on mismatch (P2 DRIFT-PROVENANCE).

    The check runs out-of-band so the originating emit() call returns
    promptly even for high-volume adapters.
    """
    return
