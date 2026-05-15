---
title: "Phase 1a — BaseCollector envelope upgrade (diff sketch)"
status: DRAFT
date: 2026-05-15
---

# Phase 1a — `BaseCollector` envelope upgrade

This file sketches the diff applied to
[`src/uiao/collectors/base_collector.py`](../../../src/uiao/collectors/base_collector.py)
when Phase 1a lands. It is **informative only** — a real PR would carry
the actual diff; this draft documents the shape so reviewers can verify
the migration preserves the legacy `EvidenceProvenance` contract.

## What changes

Three additions, **zero removals or signature changes**:

1. `EvidenceProvenance.from_envelope()` and `to_envelope()` classmethods —
   the projection/promotion bridge per ADR-071 §2.
2. `BaseCollector._emit_envelope(envelope, claim)` — protected method
   that subclasses call once per emission, routing to
   `uiao.telemetry.provenance.emit()`.
3. `BaseCollector._build_envelope(raw_data)` — convenience constructor
   that reads the collector's manifest for `issuer_identity` and
   `source_system` defaults, calls `Envelope.for_claim()`, then `seal()`.

## What does NOT change

- `BaseCollector.collect()` signature.
- `EvidenceObject` shape.
- `EvidenceProvenance.to_dict()` output (legacy callers continue to see
  the 3-field shape).
- Any existing collector implementation.

The retrofit is therefore opt-in per collector: a collector that doesn't
override `_build_envelope()` continues to emit only the legacy 3-field
provenance, with the base class auto-promoting it to a full envelope at
`_emit_envelope()` time using the manifest's defaults. A collector that
opts in constructs the full envelope itself.

## Diff sketch

```python
# Existing — unchanged:
@dataclass
class EvidenceProvenance:
    collector_id: str
    hash: str
    collection_timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "collector_id": self.collector_id,
            "hash": self.hash,
            "collection_timestamp": self.collection_timestamp.isoformat(),
        }

    # --- NEW — Phase 1a additions:

    @classmethod
    def from_envelope(cls, env: "Envelope") -> "EvidenceProvenance":
        """Project a full Envelope into the legacy 3-field shape.

        Used inside `BaseCollector.collect()` so the returned
        EvidenceObject keeps its existing field shape; the full envelope
        is persisted to the event log separately via _emit_envelope().
        """
        return cls(
            collector_id=env.source_system.split(":", 1)[0],
            hash=env.lineage_hash,
            collection_timestamp=datetime.fromisoformat(env.extraction_timestamp),
        )

    def to_envelope(
        self,
        *,
        issuer_identity: str,
        source_system: str,
        claim_id: str,
        source_classification: SourceClassification = "authoritative",
    ) -> "Envelope":
        """Promote a legacy 3-field provenance into a full Envelope.

        Used by collectors that haven't been retrofitted to construct
        Envelopes directly; the base class calls this in _emit_envelope().
        """
        env = Envelope.for_claim(
            claim_id=claim_id,
            issuer_identity=issuer_identity,
            source_system=source_system,
            source_classification=source_classification,
        )
        return env.model_copy(
            update={
                "lineage_hash": self.hash,
                "signature": "",   # MUST be sealed by the collector before emit
                "extraction_timestamp": self.collection_timestamp.isoformat(),
            }
        )


class BaseCollector(abc.ABC):
    # ... existing attributes and methods unchanged ...

    # --- NEW — Phase 1a additions:

    def _build_envelope(self, raw_data: Any, *, ksi_id: str) -> Envelope:
        """Construct a sealed Envelope for the given raw data.

        Default implementation reads the collector's manifest for
        issuer_identity and source_system. Subclasses can override to
        carry domain-specific defaults (e.g., source_classification or
        a non-default consent envelope).
        """
        envelope = Envelope.for_claim(
            claim_id=new_claim_id(domain=self.DOMAIN, claim_type=ksi_id),
            issuer_identity=self._manifest_issuer_identity(),
            source_system=self._manifest_source_system(),
            source_classification="authoritative",
        )
        return envelope.seal(
            source_record=raw_data,
            mtls_thumbprint=self._tls_thumbprint(),
        )

    def _emit_envelope(self, envelope: Envelope, *, claim: Any) -> EmitOutcome:
        """Route the envelope through the shared provenance sink.

        Called by `collect()` once per evidence object. The returned
        EmitOutcome carries the acceptance decision; on rejection the
        collector MUST raise rather than returning a partial
        EvidenceObject (otherwise the OSCAL pipeline sees orphaned
        evidence with no envelope in the event log).
        """
        from uiao.telemetry.provenance import emit as sink_emit
        return sink_emit(envelope, claim=claim, adapter_id=self.collector_id)

    def _manifest_issuer_identity(self) -> str:
        # Subclasses override or set self._config["issuer_identity"]
        # via the manifest; default raises so the gap is loud.
        v = self._config.get("issuer_identity", "")
        if not v:
            raise RuntimeError(
                f"collector {self.COLLECTOR_ID} has no issuer_identity declared; "
                "cannot construct provenance envelope"
            )
        return v

    def _manifest_source_system(self) -> str:
        v = self._config.get("source_system", "")
        if not v:
            raise RuntimeError(
                f"collector {self.COLLECTOR_ID} has no source_system declared; "
                "cannot construct provenance envelope"
            )
        return v

    def _tls_thumbprint(self) -> str:
        # In production, read from the runtime's mTLS context.
        # During tests, the collector may inject a deterministic value.
        return self._config.get("tls_thumbprint", "")
```

## Existing-collector retrofit pattern

For each existing collector (≈4 today), the retrofit is one of:

### Pattern A — minimal retrofit (no code change in the collector)

The collector continues to return an `EvidenceObject` with a legacy
3-field `EvidenceProvenance`. The base class auto-promotes via
`EvidenceProvenance.to_envelope()` using the manifest defaults, and
`_emit_envelope()` routes the promoted envelope to the sink.

Requirement: the collector's manifest MUST declare `issuer_identity:`
and `source_system:`. If they're missing, `_manifest_issuer_identity()`
raises — caught by the substrate walker as a P2 finding.

### Pattern B — full retrofit (collector constructs Envelope directly)

The collector overrides `collect()` to build the full envelope via
`self._build_envelope(raw_data, ksi_id=ksi_id)`, call
`self._emit_envelope(envelope, claim=raw_data)`, then return the
EvidenceObject with `EvidenceProvenance.from_envelope(envelope)`. This
is the target end-state for every collector.

## Retrofit order (proposed)

Concrete collectors to migrate, in suggested order — lowest risk first:

| Collector | Surface | Pattern | Notes |
|---|---|---|---|
| Test fixture collectors | tests/ | A | No production impact; smoke-tests the auto-promotion path |
| AD survey collector | `adapters/modernization/active_directory/` | A → B | Pattern A in PR-1a; promote to Pattern B once the AD adapter retrofit lands in Phase 1b |
| GCC boundary probe | `adapters/modernization/gcc_boundary_probe/` | A → B | Same — Pattern A first, full retrofit alongside Phase 1b |
| KSI evidence collectors | `collectors/` | B | Full retrofit; these are the highest-value content for OSCAL bundles |

Each collector ships in its own PR, gated by the `uiao.envelope.collectors`
feature flag. The flag flips to `expires_at` once all collectors are at
Pattern B.

## Tests

Phase 1a ships with the following tests:

1. `test_evidence_provenance_round_trip` — `from_envelope(to_envelope(...))`
   preserves the 3 legacy fields exactly.
2. `test_base_collector_auto_promotes` — a Pattern-A collector emits an
   envelope to the sink even without code change, using manifest defaults.
3. `test_event_log_append_only` — concurrent emissions don't interleave;
   sidecar `.idx` file matches per-line SHA-256.
4. `test_oscal_bundle_event_log_replay` — a bundle reconstructed from
   the event log is byte-identical to a bundle from the snapshot tree
   when both see the same accepted-envelope set (Phase 1d test, lands
   with the OSCAL `--source event-log` mode).
