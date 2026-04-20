---
document_id: UIAO_121
title: "UIAO Adapter Conformance Test Plan — Template"
version: "1.0"
status: Current
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-16"
updated_at: "2026-04-16"
boundary: "GCC-Moderate"
---

# UIAO Adapter Conformance Test Plan — Template

This template defines the standard test plan structure and pass/fail
criteria for every UIAO adapter. Each adapter's Adapter Validation Suite
(AVS) document in `uiao-docs/docs/customer-documents/adapter-validation-suites/<adapter-id>/`
MUST be populated from this template.

## 1. Scope

Every adapter registered in `canon/adapter-registry.yaml` or
`canon/modernization-registry.yaml` must pass conformance testing
against the 7 canonical responsibility domains defined in
`DatabaseAdapterBase` (see `uiao/src/uiao/impl/adapters/database_base.py`),
plus any adapter-specific extension methods.

Testing is structured in three tiers:

| Tier | Name | What it tests | Required for |
|------|------|---------------|-------------|
| T1 | **Contract Conformance** | All 7 abstract domains return correct types; ADAPTER_ID matches canon | `status: active` |
| T2 | **Provenance & Evidence** | KSI bundles carry valid provenance; evidence hashes are deterministic | Level 2 certification |
| T3 | **Integration End-to-End** | Real vendor API round-trip with mocked or sandbox credentials; CLI wiring | Level 3 (production) |

## 2. Domain-Level Pass/Fail Criteria

### Domain 2.1 — Connection & Identity

| # | Criterion | Pass | Fail |
|---|-----------|------|------|
| 2.1.1 | `connect()` returns `ConnectionProvenance` | Instance type check passes | Returns None or wrong type |
| 2.1.2 | `identity` field contains adapter-specific identifier | Non-empty, matches `<adapter-id>:...` pattern | Empty or generic |
| 2.1.3 | `endpoint` matches configured backend | Matches config value or default | Hardcoded or missing |
| 2.1.4 | `auth_method` reflects actual auth mechanism | One of: api-key, client-credential, oauth-bearer, local, iam-role | Empty |
| 2.1.5 | `timestamp` is UTC | `tzinfo` is `timezone.utc` | Naive datetime or wrong zone |

### Domain 2.2 — Schema Discovery & Canonical Mapping

| # | Criterion | Pass | Fail |
|---|-----------|------|------|
| 2.2.1 | `discover_schema()` returns `SchemaMappingObject` | Instance type check passes | Wrong type |
| 2.2.2 | `vendor_schema` contains adapter-relevant field names | At least 3 vendor-specific fields | Empty or generic |
| 2.2.3 | `canonical_schema` references UIAO identity pattern | Contains `<adapter-id>:...` identity template | Missing identity mapping |
| 2.2.4 | `unmapped_fields` is non-empty | At least 1 field listed | Empty (implies perfect mapping, unlikely) |
| 2.2.5 | `version_hash` is deterministic | Two calls produce identical hash | Hash changes between calls |

### Domain 2.3 — Query Normalization & Deterministic Extraction

| # | Criterion | Pass | Fail |
|---|-----------|------|------|
| 2.3.1 | `execute_query()` returns `QueryProvenance` | Instance type check passes | Wrong type |
| 2.3.2 | `vendor_query` reflects the adapter's native query language | Contains adapter-specific syntax (API path, xpath, OData, etc.) | Generic or empty |
| 2.3.3 | `execution_plan_hash` is deterministic | Same input → same hash | Hash varies on identical input |

### Domain 2.4 — Data Normalization & Claim Construction

| # | Criterion | Pass | Fail |
|---|-----------|------|------|
| 2.4.1 | `normalize([])` returns empty `ClaimSet` | `len(claims) == 0` | Raises or returns non-empty |
| 2.4.2 | `normalize([single_record])` produces exactly 1 `ClaimObject` | `len(claims) == 1` | 0 or >1 |
| 2.4.3 | `claim_id` follows `<adapter-id>:...` pattern | Starts with ADAPTER_ID | Missing or wrong prefix |
| 2.4.4 | `source` field equals `ADAPTER_ID` | Exact match | Mismatch |
| 2.4.5 | `provenance_hash` is non-empty and deterministic | Same record → same hash | Empty or varies |
| 2.4.6 | Multiple records produce unique `claim_id` values | `len(set(ids)) == len(records)` | Duplicates |

### Domain 2.5 — Drift Detection & Version Integrity

| # | Criterion | Pass | Fail |
|---|-----------|------|------|
| 2.5.1 | `detect_drift()` returns `DriftReport` | Instance type check passes | Wrong type |
| 2.5.2 | `drift_type` contains adapter-specific prefix | Contains ADAPTER_ID or adapter-specific domain name | Generic |
| 2.5.3 | `details` dict contains `adapter` key | `details["adapter"] == ADAPTER_ID` | Missing |

### Domain 2.6 — Evidence Packaging & KSI Integration

| # | Criterion | Pass | Fail |
|---|-----------|------|------|
| 2.6.1 | `collect_evidence(ksi_id)` returns `EvidenceObject` | Instance type check passes | Wrong type |
| 2.6.2 | `ksi_id` is preserved | `evidence.ksi_id == input` | Mutated or missing |
| 2.6.3 | `source` equals `ADAPTER_ID` | Exact match | Mismatch |
| 2.6.4 | `provenance` dict is non-empty | Contains `adapter_id`, `hash`, `timestamp` | Empty |

### Domain 2.7 — Convenience & Alignment

| # | Criterion | Pass | Fail |
|---|-----------|------|------|
| 2.7.1 | `collect_and_align()` returns dict | `isinstance(result, dict)` | Wrong type |
| 2.7.2 | `adapter_id` field matches `ADAPTER_ID` | Exact match | Mismatch |
| 2.7.3 | `vendor` field is human-readable | Non-empty string | Empty |
| 2.7.4 | `metadata` dict contains `last_collected` ISO timestamp | Parseable ISO 8601 | Missing or unparseable |

## 3. Extension Method Criteria

Adapter-specific extension methods that are **stubs** (raising
`NotImplementedError`) must pass:

| # | Criterion | Pass | Fail |
|---|-----------|------|------|
| 3.1 | Stub raises `NotImplementedError` | Exception raised | Returns silently or raises different exception |
| 3.2 | Error message names the method | Method name appears in `str(exception)` | Generic message |

Extension methods that are **implemented** must additionally pass:

| # | Criterion | Pass | Fail |
|---|-----------|------|------|
| 3.3 | Return type matches docstring signature | Instance type check | Wrong type |
| 3.4 | Provenance hash is non-empty on output claims | All claims have `provenance_hash` | Any claim missing hash |
| 3.5 | No target mutation (conformance adapters only) | Target state unchanged after call | State modified |

## 4. Canon Consistency Criteria

| # | Criterion | Pass | Fail |
|---|-----------|------|------|
| 4.1 | `ADAPTER_ID` matches canon registry `id` field | Exact match against `canon/{modernization,adapter}-registry.yaml` | Mismatch |
| 4.2 | Adapter is registered in `__init__.py` `__all__` | Import succeeds from `uiao.adapters` | ImportError |
| 4.3 | Adapter appears in `test_adapters.py` `ADAPTER_REGISTRY` | Parametrized smoke tests cover it | Missing from registry |
| 4.4 | Schema invariants hold | `gcc-boundary`, `ssot-mutation: never`, `certificate-anchored: true`, `object-identity-only: true` are respected in adapter behavior | Violation |

## 5. Per-Adapter Test Plan Population

Each AVS document (`avs-<adapter-id>.qmd`) should contain a
**Conformance Matrix** table structured as:

```markdown
## Conformance Matrix

| Domain | Criterion | Expected | Actual | Status |
|--------|-----------|----------|--------|--------|
| 2.1.1  | connect() returns ConnectionProvenance | ConnectionProvenance | — | PENDING |
| 2.1.2  | identity contains adapter ID | "terraform:..." | — | PENDING |
| ...    | ...       | ...      | ...    | ...    |
```

Status values: `PASS`, `FAIL`, `PENDING`, `N/A` (for stubs not yet implemented).

## 6. Automation

The conformance criteria in §2–§4 are designed to be machine-verifiable.
The existing `tests/test_<adapter>_adapter.py` files in `uiao`
implement most T1 criteria as pytest assertions. A future
`tools/adapter_conformance_check.py` could run the full matrix and
produce a JSON report suitable for the Evidence Fabric.

---

*End of Template — UIAO Adapter Conformance Test Plan v1.0*
