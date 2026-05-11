"""ApplicationIdentity — UIAO_129 implementation.

Per UIAO_129, every application is a first-class identity primitive with
six required canonical bindings (DNS, address, IAM, trust, segmentation,
location). This module ships the runtime data model and the drift-class
detection helpers; the JSON Schema at
``src/uiao/schemas/application-identity/application-identity.schema.json``
is the authoritative on-disk shape.

This module pairs with:

- :mod:`uiao.governance.tenancy` (UIAO_112) — application identities are
  tenant-scoped; cross-tenant references are :data:`DRIFT-AUTHZ` findings.
- :mod:`uiao.governance.drift` (UIAO_110) — emits the same drift-class
  taxonomy this module's helpers detect.
- :mod:`uiao.governance.issuer_resolution` (UIAO_110, ADR-012) — the trust
  binding's authority chain is validated there at runtime; this module
  records the *binding declaration*, not the runtime chain check.

What this module deliberately does NOT do:

- It does not *create* application identities. Authoring is a canon-
  change operation (a YAML file under ``src/uiao/canon/applications/``),
  reviewed via the canon-change ADR process. This module loads, validates,
  and queries.
- It does not enforce policy. Enforcement consumes :class:`ApplicationIdentity`
  objects via :mod:`uiao.governance.enforcement`; the application-identity
  layer is the *naming* layer, not the *enforcement* layer.

Public surface:

- :class:`LifecycleState` — five-state enum per UIAO_129 §4.
- :class:`BindingKind` — six-binding enum per UIAO_129 §2.
- :class:`Binding` — one binding (kind, authority adapter, value, verified_at).
- :class:`ApplicationIdentity` — the canonical primitive; carries all
  six bindings plus lifecycle state and transition history.
- :class:`ApplicationIdentityRegistry` — loads canon YAML, resolves by id.
- :func:`detect_schema_drift`, :func:`detect_authz_drift`,
  :func:`detect_provenance_drift` — drift-class detection helpers.
- :class:`DriftFinding` — return shape from the detection helpers.

UIAO_130 (Application Identity Onboarding Runbook) is the operational
companion to this spec; it documents the canon-change workflow that
produces the YAML records this module loads.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

# UIAO_129 §2: six required bindings, no more, no fewer.
REQUIRED_BINDING_KINDS: frozenset[str] = frozenset({"dns", "address", "iam", "trust", "segmentation", "location"})

# UIAO_129 §2 example & schema id pattern. Stable URN form: "app:<slug>".
APP_ID_PATTERN = re.compile(r"^app:[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$")


class LifecycleState(str, Enum):
    """UIAO_129 §4 five-state lifecycle.

    Allowed transitions are encoded in :data:`_ALLOWED_TRANSITIONS` below.
    Any other transition is a :class:`ValueError` at the model layer and
    a ``DRIFT-PROVENANCE`` finding at the runtime audit layer (the
    on-disk transition history must be append-only — if it isn't, the
    canon record disagrees with the evidence graph).
    """

    PROPOSED = "proposed"
    PROVISIONED = "provisioned"
    ACTIVE = "active"
    QUARANTINED = "quarantined"
    RETIRED = "retired"


# Canonical lifecycle graph. Read as: from_state -> {allowed to_states}.
_ALLOWED_TRANSITIONS: dict[LifecycleState, frozenset[LifecycleState]] = {
    LifecycleState.PROPOSED: frozenset({LifecycleState.PROVISIONED, LifecycleState.RETIRED}),
    LifecycleState.PROVISIONED: frozenset({LifecycleState.ACTIVE, LifecycleState.QUARANTINED, LifecycleState.RETIRED}),
    LifecycleState.ACTIVE: frozenset({LifecycleState.QUARANTINED, LifecycleState.RETIRED}),
    LifecycleState.QUARANTINED: frozenset({LifecycleState.ACTIVE, LifecycleState.RETIRED}),
    LifecycleState.RETIRED: frozenset(),  # terminal
}


class BindingKind(str, Enum):
    """The six required binding kinds per UIAO_129 §2."""

    DNS = "dns"
    ADDRESS = "address"
    IAM = "iam"
    TRUST = "trust"
    SEGMENTATION = "segmentation"
    LOCATION = "location"


@dataclass(frozen=True)
class Binding:
    """One application-identity binding.

    The ``authority_adapter`` field names the canon adapter that owns this
    binding's truth. Per UIAO_129 §3, each binding has exactly one
    authority — values that disagree across authorities are
    ``DRIFT-SEMANTIC`` findings, not policy ambiguity.
    """

    kind: BindingKind
    authority_adapter: str
    value: str
    verified_at: datetime | None = None

    def is_stale(self, *, freshness_window_hours: float, now: datetime | None = None) -> bool:
        """Return True if the binding's last-verified time is older than
        ``freshness_window_hours``. Bindings without ``verified_at`` are
        always stale."""
        if self.verified_at is None:
            return True
        current = now or datetime.now(timezone.utc)
        # If verified_at is naive, treat as UTC for the comparison.
        verified = self.verified_at if self.verified_at.tzinfo else self.verified_at.replace(tzinfo=timezone.utc)
        delta_hours = (current - verified).total_seconds() / 3600.0
        return delta_hours > freshness_window_hours


@dataclass(frozen=True)
class LifecycleTransition:
    """One signed lifecycle transition record. The on-disk canon copy
    mirrors the authoritative event in the evidence graph (UIAO_113)."""

    from_state: LifecycleState
    to_state: LifecycleState
    at: datetime
    reason: str | None = None
    drift_finding_id: str | None = None


@dataclass
class ApplicationIdentity:
    """An application identity record.

    Construct via :meth:`from_mapping` (canon load) or directly when
    authoring tests. The constructor does NOT validate binding presence;
    use :func:`detect_schema_drift` for that check — that decoupling lets
    the registry load partially-broken records and report their drift
    rather than refusing to load them at all.
    """

    id: str
    name: str
    tenant_id: str
    lifecycle_state: LifecycleState
    bindings: dict[BindingKind, Binding] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    transition_history: list[LifecycleTransition] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not APP_ID_PATTERN.match(self.id):
            raise ValueError(
                f"ApplicationIdentity id {self.id!r} does not match required pattern "
                f"{APP_ID_PATTERN.pattern!r} (app:<slug>, slug is kebab-case 2-64 chars)"
            )

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> ApplicationIdentity:
        """Parse a single record from canon YAML.

        Unknown bindings (kinds outside :data:`REQUIRED_BINDING_KINDS`)
        are dropped at load — they cannot exist per the schema, and a
        well-formed authoring cycle catches them via the JSON Schema
        gate before the canon-change PR merges. We are defensive at the
        runtime boundary regardless.
        """
        bindings_raw = raw.get("bindings") or {}
        bindings: dict[BindingKind, Binding] = {}
        for kind_str, binding_raw in bindings_raw.items():
            if kind_str not in REQUIRED_BINDING_KINDS:
                continue
            kind = BindingKind(kind_str)
            verified_at_raw = binding_raw.get("verified_at")
            verified_at = _parse_datetime(verified_at_raw) if verified_at_raw else None
            bindings[kind] = Binding(
                kind=kind,
                authority_adapter=binding_raw["authority_adapter"],
                value=binding_raw["value"],
                verified_at=verified_at,
            )
        transitions_raw = raw.get("transition_history") or []
        transitions = [
            LifecycleTransition(
                from_state=LifecycleState(t["from_state"]),
                to_state=LifecycleState(t["to_state"]),
                at=_parse_datetime(t["at"]),
                reason=t.get("reason"),
                drift_finding_id=t.get("drift_finding_id"),
            )
            for t in transitions_raw
        ]
        return cls(
            id=raw["id"],
            name=raw["name"],
            tenant_id=raw["tenant_id"],
            lifecycle_state=LifecycleState(raw["lifecycle_state"]),
            bindings=bindings,
            created_at=_parse_datetime(raw.get("created_at")) if raw.get("created_at") else None,
            updated_at=_parse_datetime(raw.get("updated_at")) if raw.get("updated_at") else None,
            transition_history=transitions,
        )

    def transition_to(
        self,
        *,
        new_state: LifecycleState,
        at: datetime,
        reason: str | None = None,
        drift_finding_id: str | None = None,
    ) -> LifecycleTransition:
        """Apply a lifecycle transition, validating against the canonical
        graph. Raises :class:`ValueError` for disallowed transitions, for
        terminal-state exits (RETIRED is terminal), and for QUARANTINE
        transitions without a ``drift_finding_id`` (UIAO_129 §4: quarantine
        transitions are tied to a drift finding)."""
        allowed = _ALLOWED_TRANSITIONS[self.lifecycle_state]
        if new_state not in allowed:
            raise ValueError(
                f"Disallowed transition {self.lifecycle_state.value!r} -> {new_state.value!r} "
                f"for application {self.id!r}; allowed targets: {sorted(s.value for s in allowed) or '(terminal)'}"
            )
        if new_state is LifecycleState.QUARANTINED and not drift_finding_id:
            raise ValueError(
                f"Transition to QUARANTINED requires a drift_finding_id (UIAO_129 §4) for application {self.id!r}"
            )
        transition = LifecycleTransition(
            from_state=self.lifecycle_state,
            to_state=new_state,
            at=at,
            reason=reason,
            drift_finding_id=drift_finding_id,
        )
        self.transition_history.append(transition)
        self.lifecycle_state = new_state
        self.updated_at = at
        return transition


def _parse_datetime(value: Any) -> datetime:
    """Parse YAML datetime / ISO 8601 string to a :class:`datetime`. YAML
    1.1 may already give us a :class:`datetime`; strings get round-tripped
    through ``fromisoformat`` (which accepts the canonical Z suffix in
    Python 3.11+)."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        # fromisoformat in 3.11+ accepts the Z suffix; older Python wants +00:00.
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise TypeError(f"Cannot parse datetime from {type(value).__name__}: {value!r}")


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


@dataclass
class ApplicationIdentityRegistry:
    """In-memory index of :class:`ApplicationIdentity` records loaded from
    canon. Single-tenant deployments have one registry; multi-tenant
    deployments have one per tenant scope (UIAO_112)."""

    applications: dict[str, ApplicationIdentity] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: Path) -> ApplicationIdentityRegistry:
        """Load every ``*.yaml`` / ``*.yml`` under ``path`` (recursive)
        and index by application id. Files that fail to parse are skipped
        with no exception — the substrate-walker reports them as
        ``DRIFT-SCHEMA`` findings during its next run."""
        registry = cls()
        if not path.exists():
            return registry
        for child in sorted(path.rglob("*.yaml")):
            try:
                raw = yaml.safe_load(child.read_text(encoding="utf-8"))
            except (OSError, yaml.YAMLError):
                continue
            if not isinstance(raw, dict):
                continue
            try:
                app = ApplicationIdentity.from_mapping(raw)
            except (KeyError, ValueError, TypeError):
                continue
            registry.applications[app.id] = app
        return registry

    def get(self, app_id: str) -> ApplicationIdentity | None:
        return self.applications.get(app_id)

    def for_tenant(self, tenant_id: str) -> list[ApplicationIdentity]:
        return [a for a in self.applications.values() if a.tenant_id == tenant_id]


# ---------------------------------------------------------------------------
# Drift detection helpers (UIAO_129 §7)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DriftFinding:
    """One drift-class finding emitted by an application-identity
    detection helper. Uses the canonical drift-class taxonomy from
    UIAO_110."""

    drift_class: str
    severity: str
    application_id: str | None
    detail: str

    def __str__(self) -> str:
        target = self.application_id or "<global>"
        return f"[{self.drift_class}/{self.severity}] {target}: {self.detail}"


def detect_schema_drift(application: ApplicationIdentity) -> list[DriftFinding]:
    """Return one ``DRIFT-SCHEMA`` finding per missing required binding.

    Per UIAO_129 §7, a missing binding is severity P2.
    """
    present = {kind.value for kind in application.bindings.keys()}
    missing = REQUIRED_BINDING_KINDS - present
    return [
        DriftFinding(
            drift_class="DRIFT-SCHEMA",
            severity="P2",
            application_id=application.id,
            detail=f"missing required binding: {kind!r}",
        )
        for kind in sorted(missing)
    ]


def detect_authz_drift(
    *,
    policy_rule_targets: Iterable[str],
    known_application_ids: Iterable[str],
) -> list[DriftFinding]:
    """Scan policy rule targets for non-application-identity references.

    Per UIAO_129 §5, subnets and IPs are never policy objects. Any rule
    target that is not a known application identity emits a
    ``DRIFT-AUTHZ`` finding at severity P2.

    The caller passes the targets and the set of known app ids; this
    helper does not mutate either side. The intent is that the caller
    is the policy loader (:mod:`uiao.governance.epl`).
    """
    known = set(known_application_ids)
    findings: list[DriftFinding] = []
    for target in policy_rule_targets:
        if target in known:
            continue
        findings.append(
            DriftFinding(
                drift_class="DRIFT-AUTHZ",
                severity="P2",
                application_id=None,
                detail=(
                    f"policy rule target {target!r} is not a known application identity; "
                    "subnets and IPs are not policy objects (UIAO_129 §5)"
                ),
            )
        )
    return findings


def detect_provenance_drift(
    *,
    telemetry_event: Mapping[str, Any],
    grouping_key: str = "application_identity",
) -> list[DriftFinding]:
    """Return a ``DRIFT-PROVENANCE`` finding when a telemetry event omits
    the application-identity grouping key.

    Per UIAO_129 §6, every telemetry event MUST carry application identity
    as a first-class grouping key. Severity P3.
    """
    if grouping_key in telemetry_event and telemetry_event[grouping_key]:
        return []
    return [
        DriftFinding(
            drift_class="DRIFT-PROVENANCE",
            severity="P3",
            application_id=None,
            detail=(f"telemetry event missing application-identity grouping key {grouping_key!r} (UIAO_129 §6)"),
        )
    ]


__all__ = [
    "APP_ID_PATTERN",
    "REQUIRED_BINDING_KINDS",
    "ApplicationIdentity",
    "ApplicationIdentityRegistry",
    "Binding",
    "BindingKind",
    "DriftFinding",
    "LifecycleState",
    "LifecycleTransition",
    "detect_authz_drift",
    "detect_provenance_drift",
    "detect_schema_drift",
]
