---
adr_id: adr-071
title: "Adapter emit() Hook and Provenance Event Log — Three-Surface Binding for the Runtime Envelope"
status: PROPOSED
decided: null
deciders: Michael Stratton
updated: 2026-05-15
next_review: 2026-11-01
review_trigger: First production adapter retrofit; OSCAL bundle latency regression; assessor feedback on event-log replay
impact: Promotes ADR-070 envelope from typed contract to live wire-format on three adapter surfaces (collectors, modernization, enforcement); replaces the legacy 3-field `EvidenceProvenance` with a backward-compatible projection of the new envelope; adds `evidence/provenance/<adapter>/<yyyy-mm>/*.jsonl` as a canonical artifact tree
supersedes: null
superseded_by: null
classification: Controlled
boundary: GCC-Moderate
depends_on: adr-070
---

# ADR-071: Adapter emit() Hook and Provenance Event Log

## Status

**PROPOSED** — 2026-05-15

## Context

ADR-070 ships the provenance envelope as a typed contract. That contract
is unwired — no adapter actually constructs one yet. ADR-071 wires it into
the substrate, and in doing so confronts a finding that the original
whitepaper strategy did not surface:

**The substrate has no single `BaseAdapter`.** Three independent surfaces
emit substrate evidence today, each with its own idiom:

| Surface | Base class / pattern | Today's "envelope" |
|---|---|---|
| Evidence collectors | `BaseCollector.collect()` → `EvidenceObject` | 3-field `EvidenceProvenance` (`collector_id`, `hash`, `collection_timestamp`) |
| Enforcement adapters | `EnforcementAdapter.enforce()` → `AdapterResult` | None |
| Modernization adapters | Free-form module per adapter | None |

A naïve "wire `Envelope` into `BaseAdapter.emit()`" plan would break
existing collectors (which expect the legacy provenance shape on
`EvidenceObject`) and would still not cover the modernization adapters
(which have no base class to wire into).

The substrate also lacks an event-log persistence target. The OSCAL
bundle generator (`src/uiao/generators/oscal.py`) reads from a
point-in-time snapshot of evidence files; there is no equivalent of an
append-only emission stream that an assessor could replay to reconstruct
the bundle's state at any past instant. The whitepaper claims
"reproducible evidence bundles" but today that is reproducibility of the
*snapshot* at a moment, not reproducibility of the *event history*
leading up to it.

Both gaps must close in the same phase, because the JSONL event log is
where the three surfaces converge: each surface emits envelopes through
the same sink, and the OSCAL bundle then reads from the merged stream
regardless of which surface produced any given envelope.

## Decision

**The runtime envelope is bound to three adapter surfaces through a
shared `provenance_sink` writer that persists envelopes to an append-only
JSONL event log. The legacy 3-field `EvidenceProvenance` is preserved as
a backward-compatible projection of the new envelope — not replaced
breaking-style.**

Four sub-decisions land with this:

### 1. Three-surface binding, one shared sink

Each adapter surface gets its own emit() hook tailored to its idiom; all
three converge on `uiao.telemetry.provenance.emit(envelope, claim)`:

| Surface | New hook | Existing method preserved? |
|---|---|---|
| `BaseCollector` | `_emit_envelope(envelope, claim)` called from `collect()` | Yes — `collect()` signature unchanged |
| `ModernizationAdapter` (new ABC) | `emit(claim, envelope)` is the only emission path | N/A — new surface |
| `EnforcementAdapter` | `enforce()` returns `AdapterResult` carrying an `Envelope` field | Yes — `enforce()` signature compatible (envelope optional in v1, required in v2) |

All three hooks delegate to the same `provenance_sink.emit()`. The sink
runs the sync validation suite from ADR-070 §2 inline:

1. Schema check (pydantic model validation)
2. Signature check (mTLS thumbprint resolves to a trusted issuer)
3. Identity-plane resolution (`issuer_identity` resolves)
4. Consent-envelope alignment (when `consent_envelope` is present)

On any failure, the sink returns a P1 `DriftFinding` with `subkind="runtime"`;
the adapter is responsible for not shipping the claim downstream. The
sink does **not** silently drop — per ADR-006, every emission is recorded
in the event log including failed ones (with the finding attached).

### 2. Legacy `EvidenceProvenance` is a projection, not a replacement

The existing `BaseCollector.EvidenceProvenance` has three fields:
`collector_id`, `hash`, `collection_timestamp`. The new `Envelope` has
ten required fields. Rather than breaking every existing collector by
removing the legacy class, ADR-071 retains it as a **projection** of the
new envelope:

```python
class EvidenceProvenance:
    """Legacy 3-field provenance projection (collector_id, hash, timestamp).

    Backed by an underlying Envelope. Existing collectors continue to
    construct EvidenceProvenance directly; the BaseCollector base class
    auto-promotes it to a full Envelope at _emit_envelope() time using
    the collector's manifest-declared issuer_identity and source_system.
    """
    @classmethod
    def from_envelope(cls, env: Envelope) -> "EvidenceProvenance": ...

    def to_envelope(
        self, *, issuer_identity: str, source_system: str
    ) -> Envelope: ...
```

Migration is per-collector and reversible: a collector that opts in to
constructing a full `Envelope` directly does so; a collector that hasn't
been touched gets auto-promotion at the base class. The OSCAL bundle
reader normalizes both into the full envelope when reading the event log.

### 3. JSONL event log shape

The event log is the canonical persistence target. Three properties make
it work as a replay surface:

- **Path layout.** `evidence/provenance/<adapter_id>/<yyyy-mm>/<yyyy-mm-dd>.jsonl`.
  Year-month partitioning lets the OSCAL reader load a bounded window
  without scanning the whole tree; daily files keep individual files
  under typical filesystem-friendly sizes.
- **Line shape.** Each line is the full envelope **plus** a `_event_meta`
  block carrying `event_type` (`accept` | `reject` | `chain_break`),
  `emitted_at`, `finding_id` (when `event_type != accept`), and
  `adapter_id`. The envelope itself is unmodified — the event log is the
  envelope event-sourced into a stream.
- **Append-only invariant.** The sink writes with `O_APPEND`; the
  substrate walker emits a P1 `DRIFT-PROVENANCE` finding if any line in
  the log is mutated post-write (verified by per-line content hash in
  the sidecar `.idx` file, populated at write time).

The log is the audit trail for both the runtime-drift findings (Phase 2)
and the OSCAL bundle replay (Phase 1d's reader).

### 4. OSCAL pipeline reads the event log alongside the snapshot

`src/uiao/generators/oscal.py` gains a new mode: `--source event-log`.
The default remains `--source snapshot` (today's behavior, no
regression). When the new mode is selected, the generator:

1. Loads envelopes from the configured time window of JSONL files
2. Filters to `event_type=accept` envelopes (rejected emissions don't
   contribute to evidence bundles, but the rejection lines remain in
   the log as audit trail)
3. Reconstructs the evidence bundle from the envelope stream rather than
   from the snapshot tree
4. Produces a byte-identical bundle hash to the snapshot mode when run
   on the same canon version + same accepted envelope set — verified by
   a reproducibility test

This extends ADR-006 determinism from "snapshot regen" to "event-history
regen" without breaking the existing snapshot path.

## Consequences

### Positive

- **Three-surface binding closes the whitepaper TARGET row.** Once all
  four sub-PRs ship, every substrate emission carries an envelope; the
  "continuous event-time evidence capture" row moves to SHIPPED.
- **Legacy collectors keep working unchanged.** No big-bang migration;
  the `EvidenceProvenance → Envelope` projection lets the substrate
  ship the new contract without breaking existing tests or production
  collectors.
- **Event log enables historical replay.** An assessor can rebuild the
  evidence bundle as it would have appeared at any past instant by
  filtering the JSONL stream by `_event_meta.emitted_at`. This is what
  FedRAMP 20x machine-readable evidence assumes; today the substrate
  cannot deliver it.
- **One sink, one event-shape, one taxonomy.** The three surfaces emit
  to the same sink with the same line shape; the runtime-drift findings
  (Phase 2) all share one log to read from.
- **Feature flags gate each retrofit.** `uiao.envelope.collectors`,
  `uiao.envelope.modernization`, `uiao.envelope.enforcement` — each can
  flip independently, so a regression in one surface doesn't roll back
  the others.

### Negative

- **Adapter authors face three different hooks.** Worth flagging — a
  collector author writes `_emit_envelope` inside `collect()`, a
  modernization adapter author writes `emit()` directly, an enforcement
  adapter author returns an `Envelope`-carrying `AdapterResult`. The
  asymmetry is real; we accept it because each surface has a different
  call-site semantics and a unified API would be lossy on at least one.
- **Disk pressure from the event log.** Every emission writes ~2 KB of
  JSON. At 100k emissions/day per adapter, that's ~200 MB/day per
  adapter. Mitigated by daily partitioning + the existing evidence-
  compression policy from ADR-022; not free.
- **Event-log replay can drift from snapshot replay.** If a collector
  emits an envelope and is later corrected via an `EvidenceObject`
  mutation in the snapshot tree (a real pattern today), the two replays
  diverge. The reproducibility test in §4 catches this; the fix is to
  forbid post-hoc snapshot mutation, which is a Phase 2 follow-on.
- **`EnforcementAdapter` envelope is optional in v1.** The result type
  carries an `Optional[Envelope]` initially; enforcement adapters that
  haven't been retrofitted emit `None`. The sink synthesizes a degenerate
  envelope with `source_classification="derived"` and a flag indicating
  auto-synthesis. Documented; not pretty. Phase 1c-final removes the
  optionality.

### Neutral

- The sink ships as `src/uiao/telemetry/provenance.py`, a new module.
  No collision with the existing `gcc_boundary_probe/telemetry.py`
  (that's a specific in-boundary collector, not a sink).
- The event log path lives under `evidence/`, which already exists as
  a runtime-evidence directory. No new top-level directory.

## Alternatives considered

### Alternative A — Unify the three surfaces under a new `BaseAdapter`

Introduce a new `BaseAdapter` ABC and migrate all three surfaces under
it. **Rejected** because:

- Migrating `BaseCollector` and `EnforcementAdapter` to a new common
  ancestor would touch every collector and enforcement adapter — a much
  larger PR set than the three-hook binding.
- The three call-site semantics genuinely differ (collect → query a
  source; enforce → mutate state; emit → assert a claim). Forcing them
  through one method would obscure each adapter's intent.
- The shared sink already gives us the property we want (one event log,
  one taxonomy) without forcing the call-sites into the same shape.

### Alternative B — Replace `EvidenceProvenance` outright

Drop the legacy 3-field class and require every collector to construct
a full `Envelope`. **Rejected** because:

- Touches every collector in one PR, blocking ADR-071 on full retrofit.
- Loses the gentle migration path that lets us land the sink + base
  class without breaking production.
- The projection is small (≈20 LOC) and has a defined end-of-life
  (Phase 1a-final).

### Alternative C — Database-backed event log

Persist envelopes to SQLite or Postgres rather than JSONL. **Rejected**
because:

- Adds a runtime dependency the substrate currently does not have.
- The append-only + per-line-hash + filesystem-replay model is the
  pattern the rest of the substrate already uses (evidence bundles,
  KSI artifacts, schedrun outputs).
- An assessor running `uiao oscal regenerate --source event-log` should
  not need a database server running; JSONL is portable enough that
  a tarball + Python is sufficient for replay.

A future ADR may revisit this if event-log scan latency becomes the
gating factor for OSCAL regeneration; for now, JSONL is the right call.

## Mechanical interface (informative)

### Collector surface (Phase 1a)

```python
class BaseCollector(abc.ABC):
    def collect(self, ksi_id: str) -> EvidenceObject:
        record = self._fetch(ksi_id)
        envelope = Envelope.for_claim(
            claim_id=new_claim_id(domain=self.DOMAIN, claim_type=ksi_id),
            issuer_identity=self.MANIFEST["issuer_identity"],
            source_system=self.MANIFEST["source_system"],
            source_classification="authoritative",
        ).seal(source_record=record, mtls_thumbprint=self._tls_thumbprint())
        self._emit_envelope(envelope, claim=record)   # routes to sink
        return EvidenceObject(..., provenance=EvidenceProvenance.from_envelope(envelope))
```

### Modernization surface (Phase 1b)

```python
class ModernizationAdapter(abc.ABC):
    ADAPTER_ID: ClassVar[str]
    def emit(self, claim: dict[str, Any], envelope: Envelope) -> None:
        provenance_sink.emit(envelope, claim, adapter_id=self.ADAPTER_ID)
```

### Enforcement surface (Phase 1c)

```python
@dataclass
class AdapterResult:
    adapter_id: str
    success: bool
    output: dict = field(default_factory=dict)
    error: Optional[str] = None
    envelope: Optional[Envelope] = None   # v1 optional; v2 required
```

## Cross-references

- [`inbox/drafts/phase0-runtime-provenance-envelope/adr-070-runtime-provenance-envelope.md`](../phase0-runtime-provenance-envelope/adr-070-runtime-provenance-envelope.md) — typed envelope this ADR wires
- [`src/uiao/canon/adr/adr-006-evidence-determinism.md`](../../../src/uiao/canon/adr/adr-006-evidence-determinism.md) — determinism extended to event-log replay
- [`src/uiao/canon/adr/adr-009-drift-ledger-immutability.md`](../../../src/uiao/canon/adr/adr-009-drift-ledger-immutability.md) — immutability the JSONL log inherits
- [`src/uiao/canon/adr/adr-022-evidence-compression.md`](../../../src/uiao/canon/adr/adr-022-evidence-compression.md) — compression policy that bounds event-log disk pressure
- [`src/uiao/collectors/base_collector.py`](../../../src/uiao/collectors/base_collector.py) — legacy `EvidenceProvenance` retained as projection
- [`src/uiao/enforcement/runtime.py`](../../../src/uiao/enforcement/runtime.py) — `EnforcementAdapter.enforce()` to be extended
- [`src/uiao/generators/oscal.py`](../../../src/uiao/generators/oscal.py) — OSCAL generator gains `--source event-log` mode

## Revision history

| Version | Date | Author | Summary |
|---|---|---|---|
| 1.0 | 2026-05-15 | UIAO Architecture | Initial PROPOSED draft — Phase 1 of the whitepaper TARGET → SHIPPED plan; reconciles legacy `EvidenceProvenance` and locks JSONL event-log shape |
