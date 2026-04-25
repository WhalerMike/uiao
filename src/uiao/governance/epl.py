"""EPL — Enforcement Policy Language (UIAO_116, §3.5).

EPL is the policy language the substrate's Enforcement Runtime
(UIAO_111, §3.3) consumes to decide what to do when a DriftState
or finding lands. Each policy is a YAML document with two clauses:

    when:  trigger predicate (which findings the policy applies to)
    then:  action to take (alert / log / remediate / block / escalate)

Policies live in ``src/uiao/canon/policies/*.yaml`` and are loaded
into an :class:`EPLEvaluator` that, given a finding context, returns
the matched policies and projected actions.

Mirrors the §0.4 (consent-envelope) and §3.6 (ZTMM) governance
modules: registry-driven declarations, evaluator class, OSCAL surfacing,
substrate-walker hygiene gate.

EPL design (v1.0):
    Policy:
        id            str (unique)
        description   str
        when:
            drift_class    list[str]   one of DRIFT-SCHEMA/SEMANTIC/...
                                       PROVENANCE/AUTHZ/IDENTITY/BOUNDARY
            controls       list[str]   NIST control ids (AC-2, IA-2, ...)
            adapter_ids    list[str]   adapter ids from canon registry
            pillars        list[str]   ZTMM pillars (UIAO_120 vocabulary)
            severity_min   str         "Low" / "Medium" / "High"
                                       (or "P5" .. "P1") — triggers when
                                       finding severity ≥ this value.
        then:
            action         str         one of: log, alert, remediate,
                                       block, escalate
            actor          str         responsible actor / system
            sla_hours      int         response SLA
            runbook        str         optional UIAO doc reference

Evaluation semantics:
    A policy MATCHES a context when **every** non-empty `when:` field
    intersects the corresponding context field. Empty fields are
    wildcards. Severity is compared by ordinal (Low<Medium<High).

    Multiple policies can match a single context; the evaluator
    returns all of them in a stable order (id-sorted).

    Reference policies ship in
    ``src/uiao/canon/policies/`` and load by default via
    :func:`load_canonical_policies`.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_DIR = REPO_ROOT / "uiao" / "canon" / "policies"

# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------


class EPLAction(str, Enum):
    """Action verbs the Enforcement Runtime knows how to dispatch."""

    LOG = "log"
    ALERT = "alert"
    REMEDIATE = "remediate"
    BLOCK = "block"
    ESCALATE = "escalate"

    @classmethod
    def parse(cls, value: str) -> Optional[EPLAction]:
        if not value:
            return None
        try:
            return cls(str(value).strip().lower())
        except ValueError:
            return None


# Severity ordinal so "min" comparisons work uniformly across the
# Finding vocabulary (Low/Medium/High) and the drift-engine vocabulary
# (P5..P1). Higher number = more severe.
_SEVERITY_ORDINAL: dict[str, int] = {
    "low": 1,
    "p5": 1,
    "p4": 1,
    "info": 1,
    "informational": 1,
    "benign": 1,
    "medium": 2,
    "p3": 2,
    "warn": 2,
    "warning": 2,
    "moderate": 2,
    "risky": 2,
    "high": 3,
    "p2": 3,
    "p1": 3,
    "critical": 3,
    "very-high": 3,
    "unauthorized": 3,
}


def _severity_rank(value: Optional[str]) -> int:
    if not value:
        return 0
    return _SEVERITY_ORDINAL.get(str(value).strip().lower(), 0)


# Stable namespace UUID for deriving deterministic resource UUIDs from a
# policy id. Sibling to _OSCAL_GRAPH_RESOURCE_NS / _OSCAL_ZTMM_RESOURCE_NS.
_OSCAL_EPL_RESOURCE_NS = uuid.UUID("d4e5f6a7-3c2b-5d18-a892-1b3c4d5e6f70")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EPLTrigger:
    """A policy's `when:` clause."""

    drift_class: frozenset[str] = frozenset()
    controls: frozenset[str] = frozenset()
    adapter_ids: frozenset[str] = frozenset()
    pillars: frozenset[str] = frozenset()
    severity_min: str = ""

    @property
    def is_empty(self) -> bool:
        return not (self.drift_class or self.controls or self.adapter_ids or self.pillars or self.severity_min)


@dataclass(frozen=True)
class EPLPolicy:
    """One enforcement policy."""

    id: str
    description: str = ""
    when: EPLTrigger = field(default_factory=EPLTrigger)
    action: EPLAction = EPLAction.LOG
    actor: str = ""
    sla_hours: int = 0
    runbook: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "when": {
                "drift_class": sorted(self.when.drift_class),
                "controls": sorted(self.when.controls),
                "adapter_ids": sorted(self.when.adapter_ids),
                "pillars": sorted(self.when.pillars),
                "severity_min": self.when.severity_min,
            },
            "then": {
                "action": self.action.value,
                "actor": self.actor,
                "sla_hours": self.sla_hours,
                "runbook": self.runbook,
            },
        }


@dataclass(frozen=True)
class EPLContext:
    """Trigger context the evaluator matches against.

    All fields are optional; the evaluator treats empty trigger fields
    as wildcards. Use the @classmethod helpers (``from_drift_state`` /
    ``from_finding``) to build a context from existing UIAO objects.
    """

    drift_class: str = ""
    controls: frozenset[str] = frozenset()
    adapter_id: str = ""
    pillars: frozenset[str] = frozenset()
    severity: str = ""

    @classmethod
    def from_drift_state(cls, ds: Any) -> EPLContext:
        """Build a context from a :class:`DriftState`."""
        drift_class = str(getattr(ds, "drift_class", "") or "")
        return cls(
            drift_class=drift_class,
            controls=frozenset({str(getattr(ds, "policy_ref", "") or "")} - {""}),
            severity=str(getattr(ds, "classification", "") or ""),
        )

    @classmethod
    def from_finding(cls, finding: Any) -> EPLContext:
        """Build a context from a graph FindingNode-style object."""
        extra = getattr(finding, "extra", {}) or {}
        return cls(
            drift_class=str(getattr(finding, "drift_class", "") or ""),
            controls=frozenset({str(getattr(finding, "control_id", "") or "")} - {""}),
            adapter_id=str(extra.get("adapter_id", "") or ""),
            severity=str(getattr(finding, "severity", "") or ""),
        )


@dataclass(frozen=True)
class EPLMatch:
    """One (policy, context) pair that fired."""

    policy: EPLPolicy
    context: EPLContext

    def as_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy.id,
            "action": self.policy.action.value,
            "actor": self.policy.actor,
            "sla_hours": self.policy.sla_hours,
            "context": {
                "drift_class": self.context.drift_class,
                "controls": sorted(self.context.controls),
                "adapter_id": self.context.adapter_id,
                "pillars": sorted(self.context.pillars),
                "severity": self.context.severity,
            },
        }


# ---------------------------------------------------------------------------
# YAML parsing
# ---------------------------------------------------------------------------


def _coerce_set(value: Any) -> frozenset[str]:
    if value is None:
        return frozenset()
    if isinstance(value, str):
        s = value.strip()
        return frozenset({s}) if s else frozenset()
    if isinstance(value, (list, tuple, set, frozenset)):
        return frozenset(str(v).strip() for v in value if str(v).strip())
    return frozenset()


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_policy(raw: Mapping[str, Any]) -> Optional[EPLPolicy]:
    """Parse one policy YAML mapping. Returns None when invalid."""
    if not isinstance(raw, Mapping):
        return None
    pid = str(raw.get("id", "")).strip()
    if not pid:
        return None
    when_raw = raw.get("when") or {}
    if not isinstance(when_raw, Mapping):
        when_raw = {}
    then_raw = raw.get("then") or {}
    if not isinstance(then_raw, Mapping):
        then_raw = {}

    when = EPLTrigger(
        drift_class=_coerce_set(when_raw.get("drift_class")),
        controls=_coerce_set(when_raw.get("controls")),
        adapter_ids=_coerce_set(when_raw.get("adapter_ids")),
        pillars=_coerce_set(when_raw.get("pillars")),
        severity_min=str(when_raw.get("severity_min", "")).strip(),
    )

    action = EPLAction.parse(str(then_raw.get("action", "log")))
    if action is None:
        action = EPLAction.LOG

    return EPLPolicy(
        id=pid,
        description=str(raw.get("description", "")).strip(),
        when=when,
        action=action,
        actor=str(then_raw.get("actor", "")).strip(),
        sla_hours=_coerce_int(then_raw.get("sla_hours"), 0),
        runbook=str(then_raw.get("runbook", "")).strip(),
    )


def load_policies(paths: Iterable[str | Path]) -> list[EPLPolicy]:
    """Load EPL policies from a list of YAML file paths.

    Each YAML may contain either a single policy mapping or a top-level
    ``policies:`` list of mappings. Invalid entries are silently dropped.
    Order: input order preserved; duplicates by id keep the **last** seen.
    """
    by_id: dict[str, EPLPolicy] = {}
    for path in paths:
        p = Path(path)
        if not p.is_file():
            continue
        try:
            doc = yaml.safe_load(p.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        if doc is None:
            continue
        items: list[Any]
        if isinstance(doc, list):
            items = list(doc)
        elif isinstance(doc, Mapping) and isinstance(doc.get("policies"), list):
            items = list(doc["policies"])
        elif isinstance(doc, Mapping) and "id" in doc:
            items = [doc]
        else:
            continue
        for raw in items:
            policy = _parse_policy(raw if isinstance(raw, Mapping) else {})
            if policy is not None:
                by_id[policy.id] = policy
    return sorted(by_id.values(), key=lambda p: p.id)


def load_canonical_policies(
    policy_dir: str | Path | None = None,
) -> list[EPLPolicy]:
    """Load all reference policies from ``src/uiao/canon/policies/``.

    The directory is walked for ``*.yaml`` and ``*.yml``; both flat
    file-per-policy and ``policies:`` list-of-policies forms work.
    Returns an empty list when the directory is missing.
    """
    root = Path(policy_dir) if policy_dir else DEFAULT_POLICY_DIR
    if not root.is_dir():
        return []
    paths = sorted(p for p in root.iterdir() if p.suffix in (".yaml", ".yml"))
    return load_policies(paths)


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------


@dataclass
class EPLEvaluator:
    """Evaluates a context against a loaded policy set.

    Construction is cheap: hold a list of policies and match each one's
    `when:` clause against the supplied :class:`EPLContext`. The
    evaluator is stateless across calls.
    """

    policies: list[EPLPolicy] = field(default_factory=list)

    def _matches(self, policy: EPLPolicy, ctx: EPLContext) -> bool:
        when = policy.when
        if when.is_empty:
            # An empty when matches everything — this is rarely intended;
            # we still respect it for completeness.
            return True
        if when.drift_class and ctx.drift_class not in when.drift_class:
            return False
        if when.controls and not (when.controls & ctx.controls):
            return False
        if when.adapter_ids and ctx.adapter_id not in when.adapter_ids:
            return False
        if when.pillars and not (when.pillars & ctx.pillars):
            return False
        if when.severity_min:
            if _severity_rank(ctx.severity) < _severity_rank(when.severity_min):
                return False
        return True

    def evaluate(self, ctx: EPLContext) -> list[EPLMatch]:
        """Return all policies that match the context, id-sorted."""
        out = [EPLMatch(policy=p, context=ctx) for p in self.policies if self._matches(p, ctx)]
        return sorted(out, key=lambda m: m.policy.id)

    def evaluate_drift_state(self, drift_state: Any) -> list[EPLMatch]:
        return self.evaluate(EPLContext.from_drift_state(drift_state))

    def evaluate_finding(self, finding: Any) -> list[EPLMatch]:
        return self.evaluate(EPLContext.from_finding(finding))


# ---------------------------------------------------------------------------
# OSCAL back-matter projection
# ---------------------------------------------------------------------------


def _resource_uuid_for_policy(policy_id: str) -> str:
    """Deterministic UUID for an OSCAL back-matter resource keyed on
    the policy id. Same policy id → same UUID across all OSCAL artifacts."""
    return str(uuid.uuid5(_OSCAL_EPL_RESOURCE_NS, policy_id))


def back_matter_resources_for_policies(
    policies: Iterable[EPLPolicy],
) -> list[dict[str, Any]]:
    """Build OSCAL back-matter resources from a policy list.

    One resource per policy; each carries the policy's action, actor,
    SLA, and trigger predicate as OSCAL props under
    ``https://uiao.gov/ns/oscal/epl``. OSCAL consumers can navigate
    from a finding's ``links: [{rel: "epl-policy", href: "#<uuid>"}]``
    to the back-matter resource by UUID.
    """
    ns = "https://uiao.gov/ns/oscal/epl"
    out: list[dict[str, Any]] = []
    for policy in policies:
        props = [
            {"name": "epl-policy-id", "value": policy.id, "ns": ns},
            {"name": "epl-action", "value": policy.action.value, "ns": ns},
            {"name": "epl-actor", "value": policy.actor or "—", "ns": ns},
            {"name": "epl-sla-hours", "value": str(policy.sla_hours), "ns": ns},
        ]
        if policy.runbook:
            props.append({"name": "epl-runbook", "value": policy.runbook, "ns": ns})
        for cls in sorted(policy.when.drift_class):
            props.append({"name": "epl-when-drift-class", "value": cls, "ns": ns})
        for ctrl in sorted(policy.when.controls):
            props.append({"name": "epl-when-control", "value": ctrl, "ns": ns})
        for aid in sorted(policy.when.adapter_ids):
            props.append({"name": "epl-when-adapter", "value": aid, "ns": ns})
        for pillar in sorted(policy.when.pillars):
            props.append({"name": "epl-when-pillar", "value": pillar, "ns": ns})
        if policy.when.severity_min:
            props.append({"name": "epl-when-severity-min", "value": policy.when.severity_min, "ns": ns})
        out.append(
            {
                "uuid": _resource_uuid_for_policy(policy.id),
                "title": f"UIAO_116 EPL policy: {policy.id}",
                "description": policy.description or f"Enforcement-policy reference for {policy.id}.",
                "props": props,
            }
        )
    return out


__all__ = [
    "EPLAction",
    "EPLContext",
    "EPLEvaluator",
    "EPLMatch",
    "EPLPolicy",
    "EPLTrigger",
    "back_matter_resources_for_policies",
    "load_canonical_policies",
    "load_policies",
]
