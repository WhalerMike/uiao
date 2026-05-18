# UIAO Thin Adapter Pattern — Proposal Draft

> **Status:** Inbox draft. Not canon. Promoting any part of this document to
> `src/uiao/canon/` requires a UIAO_NNN allocation in `document-registry.yaml`
> and an ADR per AGENTS.md §I5.

## Purpose

Provide a minimal interface between UIAO and external systems for use cases
where the full `DatabaseAdapterBase` seven-domain contract (UIAO_121) is
heavier than the integration requires — e.g. lightweight state-sync edges,
read-through caches, or experimental connectors that have not yet earned a
conformance/modernization classification.

## Adapter responsibilities

The thin adapter is bounded to four verbs and nothing else:

- **Read state** of an object from the external system.
- **Write state** of an object to the external system.
- **Read events** (changes) from the external system since a watermark.
- **Apply** a single change to a single object.

Explicitly **out of scope** for a thin adapter:

- **No business logic.** Decisions about *what* state should be belong to the
  caller (policy plane / orchestrator).
- **No policy logic.** Allow/deny, scoring, or compliance evaluation belong
  to KSI / enforcement / governance modules — never the adapter.
- **No lifecycle logic.** Reconciliation loops, retry policy, scheduling, and
  state-machine transitions belong to the orchestrator. The adapter is a
  pure I/O edge.

## Adapter methods

```
get_state(object_id) -> payload
set_state(object_id, payload) -> ack
list_changes(since_timestamp) -> [change]
apply_change(object_id, payload) -> ack
```

Conventions:

- `object_id` is a stable, namespace-qualified identifier owned by the
  external system. The adapter does not mint identifiers.
- `payload` is structured (dict / dataclass / pydantic model); no
  free-form strings.
- `since_timestamp` is monotonic and supplied by the caller. The adapter
  does not persist a watermark.
- All four methods are synchronous from the caller's perspective; async
  transport is an implementation detail.

## Statelessness requirement

Thin adapters **must be stateless**. Concretely:

- No instance attributes that survive a single method call other than
  immutable configuration (endpoint, credentials handle, schema version).
- No in-memory caches, no retry counters, no watermark storage. Callers
  pass everything the adapter needs on each invocation.
- Idempotency is the caller's responsibility for `set_state` /
  `apply_change`. The adapter forwards the call; it does not deduplicate.
- Two concurrent instances of the same adapter against the same target
  must be safe by construction.

## Relationship to the canonical adapter framework

This pattern is **not a replacement** for `DatabaseAdapterBase`. The
existing seven-domain contract (UIAO_121) remains the normative interface
for any adapter that participates in the governance pipeline (claims,
evidence, drift detection, KSI evaluation).

Open questions for canon review:

1. Should thin adapters live in a separate registry, or be a sub-class of
   the existing `mission-class = integration` axis?
2. How does a thin adapter's `list_changes` output relate to the
   `DRIFT-*` taxonomy in `docs/docs/16_DriftDetectionStandard.qmd`? Is it
   a feeder for `DRIFT-SEMANTIC`, or an unrelated signal?
3. What is the promotion path from a thin adapter (experimental) to a
   full `conformance` or `modernization` adapter under the dual-axis
   taxonomy (UIAO_003)?

These must be resolved before any code references this pattern.
