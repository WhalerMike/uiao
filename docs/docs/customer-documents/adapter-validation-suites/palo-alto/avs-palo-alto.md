---
title: "AVS — Palo Alto Networks NGFW"
doc-type: adapter-validation-suite
adapter-id: palo-alto
adapter-status: beta
uiao-121-version: "1.0"
generated: "2026-04-23"
conformance-runner: "tests/test_adapter_conformance.py"
---

# Adapter Validation Suite — Palo Alto Networks NGFW

**Adapter ID:** `palo-alto`
**Registry Status:** `beta`
**Conformance Runner:** `tests/test_adapter_conformance.py`
**Generated:** 2026-04-23

## Test Tier Status

| Tier | Name | Status |
|------|------|--------|
| T1 | Live commercial-tenant tests | N/A (no developer sandbox) |
| T2 | Contract tests (fixtures) | green |
| T3 | Reference deployment | excluded — no partner agency deployment yet |

## Conformance Matrix

All criteria validated by automated runner (`pytest tests/test_adapter_conformance.py`).

| Criterion | Description | Status |
|-----------|-------------|--------|
| 2.1.1 | connect() returns ConnectionProvenance | PASS |
| 2.1.2 | identity non-empty | PASS |
| 2.1.3 | endpoint non-empty | PASS |
| 2.1.4 | auth_method non-empty | PASS |
| 2.1.5 | timestamp present | PASS |
| 2.2.1 | discover_schema() returns SchemaMappingObject | PASS |
| 2.2.2 | vendor_schema non-empty | PASS |
| 2.2.3 | version_hash deterministic | PASS |
| 2.3.1 | execute_query() returns QueryProvenance | PASS |
| 2.3.2 | execution_plan_hash deterministic | PASS |
| 2.4.1 | normalize([]) returns empty ClaimSet | PASS |
| 2.4.2 | normalize([record]) returns 1 claim | PASS |
| 2.4.3 | claim_id has adapter prefix | PASS |
| 2.4.4 | claim source equals ADAPTER_ID | PASS |
| 2.4.5 | 3 records returns 3 claims | PASS |
| 2.5.1 | detect_drift() returns DriftReport | PASS |
| 2.5.2 | drift report structure valid | PASS |
| 2.7.1 | collect_evidence() returns EvidenceObject | PASS |
| 2.7.2 | ksi_id matches input | PASS |
| 2.7.3 | source equals ADAPTER_ID | PASS |
| 2.7.4 | provenance is dict | PASS |

## Canon Consistency

| Criterion | Status |
|-----------|--------|
| 4.1 ADAPTER_ID matches registry | PASS |
| 4.2 Registered in `__init__.py` `__all__` | PASS |
| 4.3 Appears in `test_adapters.py` ADAPTER_REGISTRY | PASS |

## Notes

- Tier 2 contract fixtures: `tests/fixtures/contract/palo-alto/`
- All Domain 2.1–2.7 criteria validated offline, no live tenant required
- Extension methods validated in `tests/test_palo_alto_adapter.py`
