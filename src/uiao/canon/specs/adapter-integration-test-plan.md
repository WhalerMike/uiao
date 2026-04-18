---
document_id: UIAO_123
title: "UIAO Adapter Integration & Test Plan — Canonical Template"
version: "1.0"
status: Current
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-16"
updated_at: "2026-04-16"
boundary: "GCC-Moderate"
---

# UIAO Adapter Integration & Test Plan — Canonical Template

This template defines the standard integration and test plan for every
UIAO adapter. Each adapter's implementation MUST follow this phased
approach from development through production deployment.

---

## 1. Test Plan Overview

### 1.1 Purpose

Verify that the adapter correctly implements all 7 canonical responsibility
domains, produces valid OSCAL artifacts (SAR, POA&M, SSP), and operates
safely within the GCC-Moderate governance boundary.

### 1.2 Scope

| Phase | Environment | What it proves |
|-------|-------------|----------------|
| Unit | Local dev | Individual method contracts (type, shape, determinism) |
| Integration | Local + fixtures | End-to-end data flow: vendor format → claims → OSCAL |
| System | CI pipeline | Cross-adapter composition, conformance gate, regression |
| Acceptance | Staging tenant | Real vendor API round-trip with test credentials |
| Production | Azure Gov | Full operational deployment with monitoring |

### 1.3 Prerequisites

- Adapter code subclasses `DatabaseAdapterBase` (all 7 abstract methods)
- Adapter registered in `__init__.py` `__all__` and `test_adapters.py` registry
- Canon registry entry exists in `uiao-core/canon/{modernization,adapter}-registry.yaml`
- At least one realistic fixture file in `tests/fixtures/`

---

## 2. Phase 1: Unit Testing

### 2.1 Conformance Criteria (30 checks)

Run `python -m uiao.impl.adapters.conformance_check --adapter=<id>` and
verify 30/30 PASS. These check:

| Domain | Criteria count | Key checks |
|--------|----------------|------------|
| 2.1 Connection & Identity | 5 | Type, identity pattern, endpoint, auth, UTC |
| 2.2 Schema Discovery | 4 | Type, vendor fields, unmapped, hash determinism |
| 2.3 Query Normalization | 3 | Type, native syntax, hash determinism |
| 2.4 Data Normalization | 5 | Empty, single, claim_id pattern, source, hash |
| 2.5 Drift Detection | 3 | Type, drift_type, details |
| 2.6 Evidence Packaging | 4 | Type, KSI ID, source, provenance |
| 2.7 Convenience | 3 | Type, adapter_id, vendor |
| 4.x Canon Consistency | 3 | ADAPTER_ID, __all__, registry |

### 2.2 Extension Method Tests

Each adapter-specific extension method must have:
- **Happy-path test**: realistic input → correct output type + content
- **Edge-case test**: empty input, malformed input, missing fields
- **Determinism test**: same input twice → identical output hashes

### 2.3 Pass/Fail Criteria

| Criterion | Pass | Fail |
|-----------|------|------|
| Conformance check | 30/30 | Any criterion < 30 |
| Extension method coverage | ≥1 happy + ≥1 edge per method | Missing coverage |
| Fixture file exists | ≥1 per adapter | No fixture |
| Zero `NotImplementedError` | All methods have real impl | Any stub remaining |

---

## 3. Phase 2: Integration Testing

### 3.1 OSCAL Pipeline Tests

Each adapter must prove it can produce all three OSCAL artifact types:

| Artifact | Test pattern | Acceptance |
|----------|-------------|------------|
| **SAR** | `build_adapter_bundle() → build_sar()` | Valid JSON with metadata, observations, findings, reviewed-controls |
| **POA&M** | `drift → drift_to_poam_findings() → build_poam()` | Valid JSON with poam-items, risk levels, related controls |
| **SSP** | `build_adapter_ssp()` | Valid JSON with system-security-plan, implemented-requirements |

### 3.2 Multi-Adapter Composition

Test that the adapter's evidence can be injected into an SSP alongside
other adapters' evidence without conflict:

```python
ssp = _minimal_ssp_skeleton("Multi-Adapter System")
inject_adapter_evidence_into_ssp(ssp, bundle_from_this_adapter)
inject_adapter_evidence_into_ssp(ssp, bundle_from_other_adapter)
assert len(ssp["control-implementation"]["implemented-requirements"]) >= 2
```

### 3.3 Remediation Pipeline

If the adapter produces DriftReports, test the full remediation loop:

```python
drift → poam_findings → change_requests → ServiceNow normalize → claims
```

### 3.4 Pass/Fail Criteria

| Criterion | Pass | Fail |
|-----------|------|------|
| SAR generation | Valid JSON, ≥1 observation per claim | Invalid JSON or empty |
| POA&M generation | Valid JSON, items match drift count | Missing items |
| SSP injection | implemented-requirements present | Empty or exception |
| JSON serializable | `json.dumps()` succeeds | TypeError |
| Deterministic | Two runs produce same structure | Hash mismatch |

---

## 4. Phase 3: System Testing (CI)

### 4.1 CI Gates

| Gate | Workflow | Trigger | Blocks merge? |
|------|----------|---------|---------------|
| pytest | `ci.yml` | Every PR | Yes |
| Conformance | `adapter-conformance.yml` | Adapter PRs | Yes |
| Link check | `link-check.yml` | Doc PRs | Yes |

### 4.2 Regression Testing

Every adapter PR must pass the full test suite (`pytest -q`), not just
the adapter-specific tests. This catches cross-adapter regressions.

### 4.3 Pass/Fail Criteria

| Criterion | Pass | Fail |
|-----------|------|------|
| CI green | All required checks pass | Any check fails |
| No regressions | Other adapter tests still pass | Other tests break |
| Conformance | 420/420 (or current total) | Any decrease |

---

## 5. Phase 4: Acceptance Testing

### 5.1 Prerequisites

- Test tenant/credentials available for the vendor API
- Network access from runner to vendor endpoint
- Adapter config populated with real credentials

### 5.2 Test Cases

| # | Test | Input | Expected output |
|---|------|-------|-----------------|
| A1 | Connect to real API | Real credentials | ConnectionProvenance with valid endpoint |
| A2 | Extract real data | Live API call | ClaimSet with ≥1 real resource |
| A3 | Provenance valid | Real data | Hash matches re-extraction |
| A4 | Drift detection | Real + baseline | DriftReport with actionable items |
| A5 | Evidence bundle | Real data | EvidenceObject with full provenance chain |
| A6 | OSCAL generation | Real bundle | Valid SAR/POA&M/SSP JSON |
| A7 | Error handling | Invalid credentials | Graceful error, no data leak |
| A8 | Rate limiting | Burst requests | Retry succeeds with backoff |

### 5.3 Pass/Fail Criteria

| Criterion | Pass | Fail |
|-----------|------|------|
| All A1-A8 pass | Green across all | Any test fails |
| No credential leak | Credentials not in logs/output | Any exposure |
| Performance | < 30s for typical extraction | Timeout |
| Idempotent | Two runs produce same claims | Hash mismatch |

---

## 6. Phase 5: Production Deployment

### 6.1 Prerequisites

- Phase 4 acceptance tests pass
- Canon registry entry at `status: active`
- ATS + AVS documentation authored
- Conformance matrix in AVS shows all PASS
- Runner class matches canon (github-hosted vs on-prem-self-hosted)

### 6.2 Deployment Checklist

- [ ] Adapter code merged to main
- [ ] Canon registry status = active
- [ ] CI conformance gate passing
- [ ] ATS + AVS documentation complete
- [ ] Credentials stored as GitHub secrets (never in code)
- [ ] Monitoring: adapter health check scheduled
- [ ] Alerting: failure notifications configured
- [ ] Runbook: operational procedures documented

### 6.3 Post-Deployment Verification

- [ ] First real run produces valid evidence
- [ ] Evidence ingested by Evidence Fabric
- [ ] OSCAL artifacts generated from real evidence
- [ ] No drift from expected baseline
- [ ] Performance within SLA (< 30s extraction, < 5min full pipeline)

---

## 7. Per-Adapter Test Plan Customization

Each adapter's AVS document should include a section titled
**"Integration Test Plan"** that maps this template to the adapter's
specific:

- Vendor API endpoints and authentication methods
- Fixture files and their content
- Control-specific test cases (e.g., SC-7 for firewall, IA-2 for identity)
- Edge cases unique to the vendor (throttling, pagination, XML namespaces)
- Runner class requirements (github-hosted vs on-prem)

---

*End of Template — UIAO Adapter Integration & Test Plan v1.0*
