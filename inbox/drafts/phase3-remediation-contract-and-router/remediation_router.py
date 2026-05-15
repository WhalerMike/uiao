"""RemediationRouter — dispatches DriftFindings to halt/fix/flag/log handlers.

Per ADR-073, every finding emitted by the substrate walker or the
runtime sink flows through this router. The router consults a
per-drift-class × severity rule table (loaded from
`src/uiao/canon/data/remediation-routes.yaml`) and dispatches to one
of four handlers. Routing decisions are recorded on the finding via
its §4 remediation contract fields.

This file is a DRAFT skeleton. Promotion to
`src/uiao/governance/router.py` happens when ADR-073 is ACCEPTED.
"""

from __future__ import annotations

import logging
import uuid as _uuid_mod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional, Protocol

# Imports resolve once Phase 3 promotes to canon paths.
from uiao.models.drift_finding import (
    DEFAULT_ESCALATION_PATHS,
    DriftFinding,
    VALID_REMEDIATION_ACTIONS,
)
from uiao.models.poam import (
    POAMEntry,
    RemediationStatus,
    RiskRating,
)


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rule table
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Rule:
    """One row in the remediation-routes table.

    Maps (drift_class, severity) to an action and a default escalation
    path. The `fix_if_deterministic` flag tells the router to attempt
    the `fix` handler first and demote to `flag` if no apply() is
    registered or the apply() fails.
    """

    drift_class: str
    severity: str
    action: str  # "halt" | "fix" | "flag" | "log"
    escalation_path: str
    fix_if_deterministic: bool = False


class RuleTable:
    """In-memory lookup of (drift_class, severity) → Rule.

    Loaded from `remediation-routes.yaml` at boot. A lookup miss falls
    back to a conservative default (`log` to Canon Steward) so a
    finding never goes unrouted.
    """

    def __init__(self, rules: list[Rule]) -> None:
        self._by_key: dict[tuple[str, str], Rule] = {
            (r.drift_class, r.severity): r for r in rules
        }

    @classmethod
    def from_yaml(cls, path: Path) -> "RuleTable":
        # Phase 3 STUB — real implementation loads YAML and validates
        # every drift_class is in the canonical taxonomy.
        return cls(_DEFAULT_RULES)

    def lookup(self, drift_class: str, severity: str) -> Rule:
        """Return the rule for (drift_class, severity); fallback to conservative default."""
        rule = self._by_key.get((drift_class, severity))
        if rule is not None:
            return rule
        return Rule(
            drift_class=drift_class,
            severity=severity,
            action="log",
            escalation_path=DEFAULT_ESCALATION_PATHS.get(drift_class, "Canon Steward"),
        )


# Conservative default rule table — matches ADR-073 §2.
# In production, `remediation-routes.yaml` overrides this.
_DEFAULT_RULES: list[Rule] = [
    Rule("DRIFT-PROVENANCE", "P1", "halt", "CISO"),
    Rule("DRIFT-PROVENANCE", "P2", "fix", "Canon Steward", fix_if_deterministic=True),
    Rule("DRIFT-AUTHZ", "P1", "halt", "CISO"),
    Rule("DRIFT-AUTHZ", "P2", "flag", "Canon Steward"),
    Rule("DRIFT-IDENTITY", "P1", "halt", "Architecture Lead"),
    Rule("DRIFT-IDENTITY", "P2", "fix", "Architecture Lead", fix_if_deterministic=True),
    Rule("DRIFT-SCHEMA", "P1", "halt", "Architecture Lead"),
    Rule("DRIFT-SCHEMA", "P2", "fix", "Architecture Lead", fix_if_deterministic=True),
    Rule("DRIFT-SCHEMA", "P3", "flag", "Architecture Lead"),
    Rule("DRIFT-SEMANTIC", "P2", "log", "Canon Steward"),
    Rule("DRIFT-SEMANTIC", "P3", "log", "Canon Steward"),
    Rule("DRIFT-BOUNDARY", "P1", "halt", "Architecture Lead"),
    Rule("DRIFT-BOUNDARY", "P2", "flag", "Architecture Lead"),
]


# ---------------------------------------------------------------------------
# Backends — what the handlers write to
# ---------------------------------------------------------------------------


class PoamStore(Protocol):
    """Minimal protocol the `flag` handler uses.

    Concrete implementation is `uiao.evidence.poam.PoamStore`; the
    protocol exists so the router can be unit-tested with an in-memory
    fake.
    """

    def write(self, entry: POAMEntry) -> str:
        """Write a POAMEntry; return its assigned UUID."""
        ...


class EventLogAppender(Protocol):
    """Protocol for the runtime event log writer.

    Reuses `uiao.telemetry.provenance._write_event` in production; the
    protocol exists so the `log` handler can be tested without a real
    filesystem.
    """

    def append(self, finding: DriftFinding) -> Path:
        ...


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


HandlerFn = Callable[[DriftFinding], DriftFinding]


@dataclass
class Handlers:
    """The four handler implementations bundled together for the router."""

    poam_store: PoamStore
    event_log: EventLogAppender
    fix_registry: dict[str, Callable[..., Optional[str]]] = field(default_factory=dict)

    def halt(self, finding: DriftFinding) -> DriftFinding:
        """Record the finding; signal the caller to stop.

        The halt itself is the caller's responsibility — the sink
        short-circuits emission on P1, the substrate walker fails CI
        on P1, etc. The handler just records that the contract was
        honored and writes to the event log so the action is auditable.
        """
        logger.warning(
            "HALT — drift_class=%s severity=%s path=%s detail=%s",
            finding.drift_class,
            finding.severity,
            finding.path,
            finding.detail,
        )
        self.event_log.append(finding)
        return finding

    def fix(self, finding: DriftFinding) -> DriftFinding:
        """Attempt adapter-specific auto-remediation; demote to flag on failure.

        The router looks up `finding.drift_class` in the fix_registry.
        If an apply() is registered AND succeeds, it returns a
        commit_sha or equivalent evidence string; the finding is
        marked auto_remediated. If no apply() is registered or it
        fails, the finding is demoted to `flag` and routed through the
        flag handler instead.
        """
        apply_fn = self.fix_registry.get(finding.drift_class)
        if apply_fn is None:
            logger.info(
                "FIX → FLAG (no apply() registered for %s)", finding.drift_class
            )
            return self.flag(
                finding.with_routing(
                    action="flag",
                    escalation=finding.escalation_path or "Canon Steward",
                    detected_by=finding.detected_by,
                )
            )

        try:
            evidence = apply_fn(finding=finding)
        except Exception:
            logger.exception(
                "FIX → FLAG (apply() raised for %s)", finding.drift_class
            )
            return self.flag(
                finding.with_routing(
                    action="flag",
                    escalation=finding.escalation_path or "Canon Steward",
                    detected_by=finding.detected_by,
                )
            )

        if not evidence:
            logger.info(
                "FIX → FLAG (apply() returned no evidence for %s)", finding.drift_class
            )
            return self.flag(
                finding.with_routing(
                    action="flag",
                    escalation=finding.escalation_path or "Canon Steward",
                    detected_by=finding.detected_by,
                )
            )

        completed = finding.with_remediation_evidence(
            evidence=evidence, auto_remediated=True
        )
        self.event_log.append(completed)
        return completed

    def flag(self, finding: DriftFinding) -> DriftFinding:
        """Write the finding to POA&M; record the POA&M UUID as evidence."""
        entry = _finding_to_poam_entry(finding)
        poam_uuid = self.poam_store.write(entry)
        completed = finding.with_remediation_evidence(
            evidence=poam_uuid, auto_remediated=False
        )
        self.event_log.append(completed)
        return completed

    def log(self, finding: DriftFinding) -> DriftFinding:
        """Append the finding to the event log; no further action."""
        self.event_log.append(finding)
        return finding


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


class RemediationRouter:
    """Dispatch a DriftFinding to the right handler per the rule table."""

    def __init__(self, *, table: RuleTable, handlers: Handlers) -> None:
        self._table = table
        self._handlers = handlers
        self._handler_map: dict[str, HandlerFn] = {
            "halt": handlers.halt,
            "fix": handlers.fix,
            "flag": handlers.flag,
            "log": handlers.log,
        }

    def register_fix(
        self, *, drift_class: str, fn: Callable[..., Optional[str]]
    ) -> None:
        """Adapter calls this at boot to declare an apply() function.

        The fn signature is `(finding: DriftFinding) -> Optional[str]`.
        It returns evidence (commit_sha or equivalent) on success, or
        None on failure. Exceptions are caught by the fix handler and
        demote to flag.
        """
        self._handlers.fix_registry[drift_class] = fn

    def route(self, finding: DriftFinding) -> DriftFinding:
        """Route a single finding through the action selected by the rule table."""
        rule = self._table.lookup(finding.drift_class, finding.severity)
        routed = finding.with_routing(
            action=rule.action,
            escalation=rule.escalation_path,
            detected_by=finding.detected_by or "substrate",
        )
        handler = self._handler_map[rule.action]
        return handler(routed)

    def route_many(self, findings: list[DriftFinding]) -> list[DriftFinding]:
        """Route a batch; preserves order; returns the post-routing findings."""
        return [self.route(f) for f in findings]


# ---------------------------------------------------------------------------
# POA&M projection
# ---------------------------------------------------------------------------


def _finding_to_poam_entry(finding: DriftFinding) -> POAMEntry:
    """Project a DriftFinding into a POAMEntry for the `flag` handler."""
    return POAMEntry(
        uuid=str(_uuid_mod.uuid4()),
        finding_id=f"{finding.drift_class}:{finding.path}:{finding.detection_timestamp}",
        title=f"{finding.drift_class} ({finding.severity}) — {finding.path}",
        description=finding.detail,
    )
