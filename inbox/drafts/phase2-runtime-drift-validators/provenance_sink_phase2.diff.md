---
title: "Phase 2 — provenance_sink.py diff sketch (replace Phase 1 stubs)"
status: DRAFT
date: 2026-05-15
---

# Phase 2 — `provenance_sink.py` changes

This file sketches the diff applied to
`src/uiao/telemetry/provenance.py` (built from Phase 1) when Phase 2
lands. It is **informative only** — a real PR carries the actual diff;
this draft documents the shape so reviewers can verify the change is
strictly additive (no behavior change for adapters already on Phase 1's
contract).

## What changes

Two material changes plus a deletion:

1. **The four stub validators are removed.** `_check_signature_resolves`,
   `_check_identity_resolves`, `_check_consent_envelope` (and the never-
   landed `_check_semantic_freshness`) are deleted from the sink.
2. **The validator pipeline is constructed at sink init.** A new
   `ProvenanceSink` class holds the per-adapter pipeline; the
   module-level `emit()` function becomes a thin wrapper that dispatches
   to the right per-adapter sink instance.
3. **The accept rule changes from "any finding" to "any P1 finding."**
   One-line change in the emission decision; matches the substrate
   walker's `blocking` semantic.

## What does NOT change

- The public `emit()` signature.
- The `EmitOutcome` shape.
- The event-log line format.
- The async chain-check enqueue (still a no-op stub for now).

## Diff sketch

```python
# src/uiao/telemetry/provenance.py — after Phase 2 lands

from uiao.telemetry.validators import build_pipeline, Validator

# --- DELETED ---
# def _check_signature_resolves(envelope): return True
# def _check_identity_resolves(envelope): return True
# def _check_consent_envelope(envelope, *, claim): return True


# --- NEW: per-adapter sink instance ---

class ProvenanceSink:
    """Per-adapter sink instance that owns the validator pipeline.

    Constructed once per adapter at substrate boot; the module-level
    `emit()` looks up the right instance by adapter_id.
    """

    def __init__(
        self,
        *,
        adapter_id: str,
        manifest: dict,
        registries: list[Path],
    ) -> None:
        self.adapter_id = adapter_id
        self.pipeline: list[Validator] = build_pipeline(
            adapter_id=adapter_id,
            manifest=manifest,
            registries=registries,
        )

    def emit(self, envelope: Envelope, *, claim: dict) -> EmitOutcome:
        # Run every validator in pipeline order; collect findings.
        # Sink does NOT short-circuit — every finding is useful in
        # the event log, even if the emission is already rejected.
        findings: list[DriftFinding] = []
        for validator in self.pipeline:
            finding = validator.check(envelope, claim=claim, adapter_id=self.adapter_id)
            if finding is not None:
                findings.append(finding)

        # --- CHANGED: P1-only accept rule (was: not findings) ---
        accepted = not any(f.severity == "P1" for f in findings)
        event_type: EventType = "accept" if accepted else "reject"

        log_path = _write_event(
            envelope,
            claim=claim,
            adapter_id=self.adapter_id,
            event_type=event_type,
            findings=findings,
        )

        if accepted:
            _enqueue_chain_check(envelope, claim=claim, adapter_id=self.adapter_id)

        return EmitOutcome(
            accepted=accepted,
            envelope=envelope,
            findings=findings,
            log_path=log_path,
        )


# --- NEW: module-level registry of per-adapter sink instances ---

_sinks: dict[str, ProvenanceSink] = {}
_sinks_lock = threading.Lock()


def register_sink(*, adapter_id: str, manifest: dict, registries: list[Path]) -> None:
    """Construct and register the per-adapter sink instance.

    Called once per adapter at substrate boot. Idempotent — calling
    twice with the same adapter_id replaces the existing sink (used
    for hot manifest reloads).
    """
    with _sinks_lock:
        _sinks[adapter_id] = ProvenanceSink(
            adapter_id=adapter_id,
            manifest=manifest,
            registries=registries,
        )


# --- CHANGED: module-level emit() dispatches to per-adapter sink ---

def emit(envelope: Envelope, *, claim: dict, adapter_id: str) -> EmitOutcome:
    """Module-level emit — dispatches to the per-adapter sink instance.

    Falls back to a degenerate sink (signature+identity only, no
    consent envelope, no freshness window) when no per-adapter sink
    is registered. The degenerate sink emits a P3 DRIFT-SCHEMA
    advisory so the gap is loud.
    """
    sink = _sinks.get(adapter_id) or _fallback_sink(adapter_id)
    return sink.emit(envelope, claim=claim)


def _fallback_sink(adapter_id: str) -> ProvenanceSink:
    """Build a sink with no manifest registered — happens during tests
    or before substrate boot completes. The pipeline is the same shape
    but with empty trust-anchor map, default Entra resolver, and
    global-default freshness window. A P3 finding is appended to every
    emission flagging the absent registration.
    """
    logger.warning(
        "no per-adapter sink registered for %s; using fallback. Register via "
        "uiao.telemetry.provenance.register_sink() at substrate boot.",
        adapter_id,
    )
    return ProvenanceSink(adapter_id=adapter_id, manifest={}, registries=[])
```

## Substrate boot wiring

A new module `src/uiao/runtime/boot.py` runs once at substrate startup:

```python
def register_all_sinks() -> None:
    """Iterate every active adapter in canon and register its sink.

    Reads adapter-registry.yaml and modernization-registry.yaml,
    loads each active adapter's manifest, and calls
    provenance.register_sink() for each. Called from `uiao.cli`
    immediately after `walk_substrate()` clears at boot time.
    """
    ...
```

The CLI surface gains one line in `uiao.cli.app.startup()`:

```python
from uiao.telemetry import provenance
from uiao.runtime import boot
...
boot.register_all_sinks()   # NEW — Phase 2
```

## Tests

The Phase 2 PR ships with the following tests under `tests/telemetry/`:

| Test | What it verifies |
|---|---|
| `test_signature_validator_rejects_empty_signature` | Empty `envelope.signature` → P1 DRIFT-PROVENANCE → emission rejected |
| `test_identity_validator_rejects_unresolvable_principal` | Stub resolver returns `resolved=False` → P1 DRIFT-IDENTITY → rejected |
| `test_identity_validator_uses_manifest_resolver` | Manifest declares custom `identity_resolver:` → that resolver is used, not the default |
| `test_authz_validator_rejects_expired_consent` | Consent with `consent_expiry` in the past → P1 DRIFT-AUTHZ → rejected |
| `test_authz_validator_requires_mou_on_cross_boundary` | `cross_boundary_flag=true` + no `mou_reference` → P1 DRIFT-AUTHZ → rejected |
| `test_authz_validator_skips_without_consent_envelope` | No consent_envelope → no finding → accepted (not every claim is gated) |
| `test_semantic_validator_logs_stale_but_does_not_reject` | `extraction_timestamp` > window → **accepted** + P2 DRIFT-SEMANTIC finding logged |
| `test_pipeline_order` | Validators run in declared order; all findings collected; sink does not short-circuit |
| `test_accept_rule_is_p1_only` | P2/P3 findings present, no P1 → `accepted=True` |
| `test_consent_envelope_round_trip` | `ConsentEnvelope` model serializes/deserializes from `17_ConsentEnvelope.qmd` §3 YAML examples |
| `test_entra_resolver_cache_ttl` | Repeated resolutions of the same principal within TTL return cached result without network call |

No existing test should break. The Phase 1 stubs returned True for
every check, so any test that asserted "emit always accepts" must be
updated — but those tests are smoke-tests for the sink, not
correctness tests for the validators.
