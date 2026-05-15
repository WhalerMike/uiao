---
title: "Phase 3 — Walker + Sink consolidation onto canonical DriftFinding"
status: DRAFT
date: 2026-05-15
---

# Phase 3 — Walker + Sink consolidation diff

This file sketches the diff applied to
[`src/uiao/substrate/walker.py`](../../../src/uiao/substrate/walker.py) and
the runtime sink (Phase 1's `src/uiao/telemetry/provenance.py`) when
Phase 3 lands. Both files adopt the canonical
`src/uiao/models/drift_finding.py` class via re-export — no caller
sees a name change.

## Substrate walker

### Before (today)

```python
# src/uiao/substrate/walker.py

@dataclass
class DriftFinding:
    drift_class: str
    severity: str
    path: str
    detail: str
    subkind: Optional[str] = None
```

### After (Phase 3)

```python
# src/uiao/substrate/walker.py
from uiao.models.drift_finding import DriftFinding  # re-export

# Local dataclass deleted; all existing callers continue to work
# because the imported class is API-compatible (same field names,
# same defaults, same constructor signature).
```

All callers across the substrate use either
`from uiao.substrate.walker import DriftFinding` (legacy) or
`from uiao.models.drift_finding import DriftFinding` (new). Both
resolve to the same class.

### Caller-side changes — none required

Every `DriftFinding(drift_class=..., severity=..., path=..., detail=...,
subkind=...)` call site continues to work unchanged because the
canonical class preserves the original five-field constructor signature.
The new §4 contract fields default to empty/unset; only the router
populates them.

## Runtime sink

### Before (Phase 1)

```python
# inbox/drafts/phase1-emit-hook-and-evidence-capture/provenance_sink.py
@dataclass
class DriftFinding:
    drift_class: str
    severity: str
    path: str
    detail: str
    subkind: str = "runtime"
```

### After (Phase 3)

```python
# src/uiao/telemetry/provenance.py
from uiao.models.drift_finding import DriftFinding, runtime_finding  # re-export

# Local dataclass deleted; sink emission sites use the runtime_finding
# convenience constructor:
#
#   finding = runtime_finding(
#       drift_class="DRIFT-PROVENANCE",
#       severity="P1",
#       path=envelope.claim_id,
#       detail="...",
#       detected_by=adapter_id,
#   )
```

### Router wiring

The sink's `ProvenanceSink.emit()` (from Phase 2) calls the router on
every finding produced by the validator pipeline:

```python
# src/uiao/telemetry/provenance.py — after Phase 3

from uiao.governance.router import RemediationRouter

class ProvenanceSink:
    def __init__(
        self,
        *,
        adapter_id: str,
        manifest: dict,
        registries: list[Path],
        router: RemediationRouter,   # NEW — injected at boot
    ) -> None:
        self.adapter_id = adapter_id
        self.pipeline: list[Validator] = build_pipeline(
            adapter_id=adapter_id,
            manifest=manifest,
            registries=registries,
        )
        self._router = router

    def emit(self, envelope: Envelope, *, claim: dict) -> EmitOutcome:
        findings: list[DriftFinding] = []
        for validator in self.pipeline:
            finding = validator.check(envelope, claim=claim, adapter_id=self.adapter_id)
            if finding is not None:
                # --- NEW Phase 3: route each finding through the router ---
                routed = self._router.route(finding)
                findings.append(routed)

        accepted = not any(f.severity == "P1" for f in findings)
        event_type: EventType = "accept" if accepted else "reject"
        log_path = _write_event(
            envelope, claim=claim, adapter_id=self.adapter_id,
            event_type=event_type, findings=findings,
        )
        if accepted:
            _enqueue_chain_check(envelope, claim=claim, adapter_id=self.adapter_id)

        return EmitOutcome(accepted=accepted, envelope=envelope,
                           findings=findings, log_path=log_path)
```

Two things shifted:

1. **Router invocation per finding.** Each validator finding goes
   through `self._router.route()` before being collected. The routed
   finding carries the populated §4 contract fields (action,
   escalation_path, detected_by — and, after handler execution,
   auto_remediated / remediation_timestamp / remediation_evidence).
2. **The event log writes the routed finding.** The JSONL line shape
   from Phase 1 (envelope + `_event_meta`) gains the contract fields
   automatically because `DriftFinding.to_dict()` now includes them.
   Existing event-log readers see the same keys plus new ones.

## Substrate walker — router wiring

The walker is exercised at PR time by `walk_substrate()`. After Phase 3,
the walker emits findings, but routing is **optional**:

```python
# src/uiao/substrate/walker.py — after Phase 3

def walk_substrate(
    workspace_root: Optional[Path] = None,
    router: Optional["RemediationRouter"] = None,   # NEW; optional
) -> SubstrateReport:
    # ... existing scan logic unchanged ...

    if router is not None:
        report.findings = [router.route(f) for f in report.findings]

    return report
```

Why optional: substrate-drift CI runs the walker as a pure-detection
pass; CI does not have a POA&M store wired up, so calling the router
there would either fail (no backend) or no-op (in-memory backend with
no persistence). Production substrate boot wires the router; CI does
not. The `subkind="hygiene"` findings still flow through the router
during production boot via a separate call path.

### Production boot — single wiring point

```python
# src/uiao/runtime/boot.py — after Phase 3

from uiao.governance.router import RemediationRouter, RuleTable, Handlers
from uiao.evidence.poam import PoamStore
from uiao.telemetry.provenance import EventLogAppender, register_sink

def boot_substrate() -> None:
    # Phase 3: wire the router once, share across walker + sink.
    router = RemediationRouter(
        table=RuleTable.from_yaml(Path("src/uiao/canon/data/remediation-routes.yaml")),
        handlers=Handlers(
            poam_store=PoamStore.from_config(...),
            event_log=EventLogAppender.from_config(...),
        ),
    )

    # Walker pass: emit + route hygiene findings into POA&M.
    report = walk_substrate(router=router)

    # Sink registration: each adapter's sink instance gets the same router.
    for adapter_id, manifest in _iter_active_adapters():
        register_sink(
            adapter_id=adapter_id,
            manifest=manifest,
            registries=[_REGISTRY_PATHS],
            router=router,
        )
```

The router is constructed once and shared. Walker hygiene findings and
sink runtime findings both pass through the same rule table, the same
handlers, the same POA&M store, the same event log.

## Tests

Tests in PR-3a cover the consolidation:

| Test | What it verifies |
|---|---|
| `test_walker_drift_finding_is_canonical` | `from uiao.substrate.walker import DriftFinding` returns the same class as `from uiao.models.drift_finding import DriftFinding` |
| `test_legacy_walker_callsite_unchanged` | `DriftFinding(drift_class=..., severity=..., path=..., detail=...)` constructs a finding with §4 fields defaulted |
| `test_runtime_finding_convenience_constructor` | `runtime_finding()` sets `subkind="runtime"` and pre-populates `detected_by` |
| `test_router_populates_contract` | Routing a finding sets `remediation_action`, `escalation_path`, `detected_by` |
| `test_fix_demotes_to_flag_without_apply` | DRIFT-IDENTITY P2 finding with no registered apply() → routed via `fix` → demotes to `flag` → POA&M entry written |
| `test_log_handler_does_not_write_poam` | DRIFT-SEMANTIC P2 → `log` action → event log appended, POA&M store untouched |
| `test_invalid_drift_class_raises` | `DriftFinding(drift_class="NONSENSE", ...)` raises ValueError per __post_init__ check |
