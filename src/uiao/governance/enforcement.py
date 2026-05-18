"""Enforcement Runtime — dispatches EPL policy actions when findings land
(UIAO_111, §3.3).

The substrate's drift detectors (§0.4 / §0.5 / §1.1) and OSCAL emitters
produce findings; the EPL (§3.5) tells what to do when a finding
matches a policy. The Enforcement Runtime is the moving part in the
middle: takes a finding, runs it through the EPL evaluator, and
dispatches each matched policy's action through a handler.

Pipeline:

    Finding / DriftState  ─────► EPLEvaluator.evaluate(ctx)
            │
            ▼
    list[EPLMatch]
            │
            ▼
    EnforcementRuntime.dispatch(matches)
            │     │     │     │     │
            ▼     ▼     ▼     ▼     ▼
        log  alert  remediate  block  escalate
        │     │     │           │     │
        └─────┴─────┴───────────┴─────┘
                       │
                       ▼
            EnforcementAction records
                       │
                       ▼
            EnforcementJournal (JSONL on disk)

Handlers are pluggable: each :class:`EnforcementHandler` knows how to
dispatch a single :class:`EPLAction` verb. The runtime ships
default handlers for all five verbs; production deployments swap
real backends in (e.g. PagerDuty alerts, ServiceNow tickets,
adapter-driven remediation calls).

Action results land in an :class:`EnforcementJournal` — append-only
JSONL that becomes the substrate's audit trail for "what was
enforced when". The journal is the natural input to UIAO_109 Data
Lake archival.

The runtime never directly mutates an adapter or upstream system in
v1: it produces structured action records and delegates the actual
side-effect to a pluggable handler. That keeps the runtime testable
and the side-effects auditable.
"""

from __future__ import annotations

import abc
import json
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from uiao.governance.epl import EPLAction, EPLContext, EPLEvaluator, EPLMatch
from uiao.governance.feature_flags import FeatureFlagRegistry
from uiao.governance.tenancy import Tenant, TenantContext

JOURNAL_TAGGING_FLAG = "enforcement.journal.tenant-tagging"
EPL_BLOCK_ACTION_FLAG = "epl.action.block.enabled"

# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _isoformat(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


@dataclass(frozen=True)
class EnforcementAction:
    """One dispatched action — input to the audit journal."""

    policy_id: str
    action: EPLAction
    actor: str
    sla_hours: int
    target: str
    """Free-form target identifier — adapter id, control id, run id,
    whatever the handler thinks identifies the subject of the action.
    Surfaced in the journal so reviewers can correlate."""
    dispatched_at: str  # ISO-8601 UTC
    status: str  # "dispatched" | "skipped" | "failed"
    details: str = ""
    extra: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "action": self.action.value,
            "actor": self.actor,
            "sla_hours": self.sla_hours,
            "target": self.target,
            "dispatched_at": self.dispatched_at,
            "status": self.status,
            "details": self.details,
            "extra": dict(self.extra),
        }


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


class EnforcementHandler(abc.ABC):
    """Dispatches a single :class:`EPLAction` verb."""

    action: EPLAction

    @abc.abstractmethod
    def dispatch(
        self,
        match: EPLMatch,
        target: str,
        *,
        now: Optional[datetime] = None,
    ) -> EnforcementAction: ...


def _build_action(
    match: EPLMatch,
    target: str,
    *,
    status: str,
    details: str,
    now: Optional[datetime] = None,
    extra: Optional[Mapping[str, Any]] = None,
) -> EnforcementAction:
    return EnforcementAction(
        policy_id=match.policy.id,
        action=match.policy.action,
        actor=match.policy.actor,
        sla_hours=match.policy.sla_hours,
        target=target,
        dispatched_at=_isoformat(now or _now_utc()),
        status=status,
        details=details,
        extra=dict(extra or {}),
    )


class LoggingHandler(EnforcementHandler):
    """Default LOG handler — records the action and nothing else."""

    action = EPLAction.LOG

    def dispatch(
        self,
        match: EPLMatch,
        target: str,
        *,
        now: Optional[datetime] = None,
    ) -> EnforcementAction:
        return _build_action(
            match,
            target,
            status="dispatched",
            details=f"logged policy {match.policy.id} on {target}",
            now=now,
        )


class AlertHandler(EnforcementHandler):
    """Default ALERT handler — records an alert intent. Production
    deployments swap this for PagerDuty / Opsgenie / email integration."""

    action = EPLAction.ALERT

    def dispatch(
        self,
        match: EPLMatch,
        target: str,
        *,
        now: Optional[datetime] = None,
    ) -> EnforcementAction:
        return _build_action(
            match,
            target,
            status="dispatched",
            details=(f"alert fired: {match.policy.id} → {match.policy.actor} (SLA {match.policy.sla_hours}h)"),
            now=now,
        )


class EscalateHandler(EnforcementHandler):
    """Default ESCALATE handler — records an escalation intent. Same
    structure as :class:`AlertHandler` but tagged as priority-elevated;
    production deployments tend to wire this to on-call paging."""

    action = EPLAction.ESCALATE

    def dispatch(
        self,
        match: EPLMatch,
        target: str,
        *,
        now: Optional[datetime] = None,
    ) -> EnforcementAction:
        return _build_action(
            match,
            target,
            status="dispatched",
            details=(f"escalation fired: {match.policy.id} → {match.policy.actor} (SLA {match.policy.sla_hours}h)"),
            now=now,
            extra={"priority": "high"},
        )


@dataclass
class BlockHandler(EnforcementHandler):
    """Default BLOCK handler — appends to an in-memory deny-list.

    Production deployments hand a real registry adapter (e.g. the
    UIAO_100 scheduler's "skip these adapters on the next dispatch"
    set). The default just records what would be blocked so tests
    can assert on the side-effect.

    UIAO_119 v2 check-point — when ``flags`` and ``tenant_context``
    are both supplied, ``dispatch`` consults the
    ``epl.action.block.enabled`` feature flag. Dispatching against a
    disabled flag returns a ``status="skipped"`` action whose details
    cite the gate; the in-memory ``blocked`` set is left unchanged.
    Without ``flags`` the handler dispatches unconditionally
    (back-compat).
    """

    action: EPLAction = EPLAction.BLOCK
    blocked: set[str] = field(default_factory=set)
    flags: Optional[FeatureFlagRegistry] = None
    tenant_context: Optional[TenantContext] = None
    tenant: Optional[Tenant] = None

    def dispatch(
        self,
        match: EPLMatch,
        target: str,
        *,
        now: Optional[datetime] = None,
    ) -> EnforcementAction:
        if self.flags is not None and self.tenant_context is not None:
            if not self.flags.is_enabled(EPL_BLOCK_ACTION_FLAG, self.tenant_context, self.tenant):
                return _build_action(
                    match,
                    target,
                    status="skipped",
                    details=(
                        f"block gated by feature flag {EPL_BLOCK_ACTION_FLAG} "
                        f"(disabled for environment={self.tenant_context.environment.value})"
                    ),
                    now=now,
                )
        self.blocked.add(target)
        return _build_action(
            match,
            target,
            status="dispatched",
            details=f"block list now includes {target}",
            now=now,
        )


@dataclass
class RemediateHandler(EnforcementHandler):
    """Default REMEDIATE handler — looks up the adapter remediation
    callable from a registry mapping ``{adapter_id: callable}`` and
    invokes it. Adapters without a wired remediation fall through to
    a "skipped" action whose details cite the missing wiring.

    The callable signature is ``(match, target) → tuple[bool, str]``
    where the bool is success and the str is a short reason.
    """

    action: EPLAction = EPLAction.REMEDIATE
    adapter_remediations: Mapping[str, Any] = field(default_factory=dict)

    def dispatch(
        self,
        match: EPLMatch,
        target: str,
        *,
        now: Optional[datetime] = None,
    ) -> EnforcementAction:
        # Target string is the adapter id when the EPLMatch came from
        # a finding with adapter_id; fall back to skipping otherwise.
        adapter_id = match.context.adapter_id or target
        callable_ = self.adapter_remediations.get(adapter_id)
        if callable_ is None:
            return _build_action(
                match,
                target,
                status="skipped",
                details=(f"no remediation wired for adapter '{adapter_id}'; operator must wire it"),
                now=now,
            )
        try:
            ok, reason = callable_(match, target)
        except Exception as exc:  # noqa: BLE001 — handler boundary
            return _build_action(
                match,
                target,
                status="failed",
                details=f"remediation raised: {exc}",
                now=now,
                extra={"adapter_id": adapter_id},
            )
        return _build_action(
            match,
            target,
            status="dispatched" if ok else "failed",
            details=f"remediation: {reason}",
            now=now,
            extra={"adapter_id": adapter_id},
        )


# ---------------------------------------------------------------------------
# Journal
# ---------------------------------------------------------------------------


@dataclass
class EnforcementJournal:
    """Append-only JSONL log of dispatched enforcement actions.

    The journal is the substrate's audit trail. Each action is one line
    of JSON with a stable schema; downstream consumers (Auditor API,
    OSCAL POA&M generator, Data Lake archival) read it.

    Either ``path`` or ``records`` is the source of truth: when ``path``
    is set, every :meth:`record` appends to that file; when ``path`` is
    ``None`` the records live only in memory (useful in tests).
    """

    path: Optional[Path] = None
    records: list[EnforcementAction] = field(default_factory=list)

    def record(self, action: EnforcementAction) -> None:
        self.records.append(action)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(action.as_dict(), sort_keys=True) + "\n")

    def read_all(self) -> list[EnforcementAction]:
        """Return all records (in-memory + on-disk if path is set)."""
        if self.path is None or not self.path.is_file():
            return list(self.records)
        out: list[EnforcementAction] = []
        try:
            for line in self.path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(data, dict):
                    continue
                out.append(
                    EnforcementAction(
                        policy_id=str(data.get("policy_id", "")),
                        action=EPLAction(str(data.get("action", "log"))),
                        actor=str(data.get("actor", "")),
                        sla_hours=int(data.get("sla_hours", 0) or 0),
                        target=str(data.get("target", "")),
                        dispatched_at=str(data.get("dispatched_at", "")),
                        status=str(data.get("status", "")),
                        details=str(data.get("details", "")),
                        extra=data.get("extra", {}) if isinstance(data.get("extra"), dict) else {},
                    )
                )
        except OSError:
            pass
        return out


# ---------------------------------------------------------------------------
# Runtime
# ---------------------------------------------------------------------------


def _default_handlers() -> dict[EPLAction, EnforcementHandler]:
    return {
        EPLAction.LOG: LoggingHandler(),
        EPLAction.ALERT: AlertHandler(),
        EPLAction.ESCALATE: EscalateHandler(),
        EPLAction.BLOCK: BlockHandler(),
        EPLAction.REMEDIATE: RemediateHandler(),
    }


@dataclass
class EnforcementRuntime:
    """Glues EPL evaluation to action dispatch + journaling.

    The runtime is the moving part in the middle of UIAO_111. Tests
    construct it with a curated handler set + an in-memory journal;
    production deployments inject real handlers + a disk-backed journal.

    UIAO_119 v2 wire-up — when ``tenant_context`` is supplied, every
    dispatched action carries the tenant tagging payload
    (``tenant_id`` / ``actor`` / ``environment``, plus ``tenant_class``
    when ``tenant`` is also supplied) merged into ``action.extra``
    before the journal records it. The optional ``flags`` registry
    gates the behavior on the ``enforcement.journal.tenant-tagging``
    feature flag — when ``flags`` is set and the flag is disabled for
    the runtime's context, tagging is skipped. Without ``flags`` the
    tagging is unconditional; pass it only when an operator wants the
    rollout-controlled behavior.
    """

    evaluator: EPLEvaluator
    handlers: Mapping[EPLAction, EnforcementHandler] = field(default_factory=_default_handlers)
    journal: EnforcementJournal = field(default_factory=EnforcementJournal)
    tenant_context: Optional[TenantContext] = None
    tenant: Optional[Tenant] = None
    flags: Optional[FeatureFlagRegistry] = None

    def _tagging_enabled(self) -> bool:
        if self.tenant_context is None:
            return False
        if self.flags is None:
            return True
        return self.flags.is_enabled(JOURNAL_TAGGING_FLAG, self.tenant_context, self.tenant)

    def _maybe_tag(self, action: EnforcementAction) -> EnforcementAction:
        if not self._tagging_enabled():
            return action
        assert self.tenant_context is not None  # narrow type for mypy
        tags = self.tenant_context.as_tag_dict(self.tenant)
        merged: dict[str, Any] = dict(action.extra)
        merged.update(tags)
        return replace(action, extra=merged)

    def dispatch_matches(
        self,
        matches: Iterable[EPLMatch],
        target: str,
        *,
        now: Optional[datetime] = None,
    ) -> list[EnforcementAction]:
        """Dispatch a precomputed list of EPL matches against ``target``.

        Returns the list of :class:`EnforcementAction` records, also
        appended to the journal.
        """
        out: list[EnforcementAction] = []
        for match in matches:
            handler = self.handlers.get(match.policy.action)
            if handler is None:
                action = _build_action(
                    match,
                    target,
                    status="skipped",
                    details=f"no handler registered for action {match.policy.action.value}",
                    now=now,
                )
            else:
                action = handler.dispatch(match, target, now=now)
            action = self._maybe_tag(action)
            self.journal.record(action)
            out.append(action)
        return out

    def dispatch_context(
        self,
        ctx: EPLContext,
        *,
        target: str = "",
        now: Optional[datetime] = None,
    ) -> list[EnforcementAction]:
        """Evaluate ``ctx`` against EPL and dispatch every match.

        ``target`` defaults to the context's ``adapter_id`` when set,
        otherwise its first ``control_id``, otherwise ``"unknown"``.
        """
        matches = self.evaluator.evaluate(ctx)
        if not matches:
            return []
        if not target:
            target = ctx.adapter_id or (next(iter(ctx.controls), "") if ctx.controls else "") or "unknown"
        return self.dispatch_matches(matches, target, now=now)

    def dispatch_finding(
        self,
        finding: Any,
        *,
        now: Optional[datetime] = None,
    ) -> list[EnforcementAction]:
        ctx = EPLContext.from_finding(finding)
        return self.dispatch_context(ctx, now=now)

    def dispatch_drift_state(
        self,
        drift_state: Any,
        *,
        now: Optional[datetime] = None,
    ) -> list[EnforcementAction]:
        ctx = EPLContext.from_drift_state(drift_state)
        return self.dispatch_context(ctx, now=now)


__all__ = [
    "EPL_BLOCK_ACTION_FLAG",
    "JOURNAL_TAGGING_FLAG",
    "AlertHandler",
    "BlockHandler",
    "EnforcementAction",
    "EnforcementHandler",
    "EnforcementJournal",
    "EnforcementRuntime",
    "EscalateHandler",
    "LoggingHandler",
    "RemediateHandler",
]
