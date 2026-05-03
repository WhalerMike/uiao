---
deliverable_id: Spec2-D4.1
title: "Test HR Data Set"
spec: UIAO_136 / Spec 2 — HR-Agnostic Provisioning Architecture
phase: 4
status: Draft
version: 0.1
owner: Identity Architecture
created: 2026-05-02
updated: 2026-05-02
canonical_adrs:
  - ADR-003
canonical_docs:
  - UIAO_007
  - UIAO_135
  - UIAO_136
upstream_deliverables:
  - Spec2-D1.1
  - Spec2-D1.6
sibling_deliverables:
  - Spec2-D4.2
  - Spec2-D4.3
  - Spec2-D4.4
boundary: GCC-Moderate
classification: Controlled
---

# Spec 2 — D4.1: Test HR Data Set

> **Status (v0.1, 2026-05-02):** Initial canonical specification of
> the synthetic HR data set every Spec 2 deployment uses for
> integration / performance / UAT testing (D4.2–D4.4).

## 1. Purpose, Scope, and Reference

This deliverable is the canonical Test HR Data Set specification
called for in
[`UIAO_136`](../UIAO_136_priority1-transformation-project-plans.md)
§SPEC 2 → Phase 4 → D4.1:

> *Synthetic HR data set covering all scenarios: new hire,
> termination, department transfer, manager change, name change,
> rehire, contractor conversion, LOA, multiple positions. Minimum
> 500 records. JSON/CSV test data.*

D4.1 specifies the synthetic data set used by D4.2 (integration
tests), D4.3 (performance tests), and D4.4 (UAT acceptance
criteria). It is the universally-shared test substrate; all three
sister specs assume this data.

### 1.1 Scope

In scope:

- The minimum-viable test record count and category distribution.
- The required scenario coverage (one record per JML / edge case
  category at minimum).
- The data-quality assumptions: clean records vs. deliberate
  data-quality failures.
- The format (JSON + CSV in parallel).
- Synthetic-data safety (no real PII, no realistic SSNs, etc.).
- Versioning + provenance.

Out of scope:

- The test runner / harness itself (D4.2 names it).
- Per-tenant test data (each deployment may layer additional
  tests).
- Automated test data generation tooling (the canonical fixture
  is hand-curated; tooling is per-deployment).

## 2. Record Count + Distribution

The canonical fixture: **500 records**, distributed:

| Category | Count | Purpose |
|---|---|---|
| Joiner (FTE, no edge cases) | 100 | Baseline POST `/Users` + day-of-hire flow |
| Joiner (PTE) | 30 | Worker-type variation |
| Joiner (Contractor) | 50 | Contractor UPN variant + scope |
| Joiner (Intern) | 20 | 30-day pre-hire window |
| Joiner (Vendor / Volunteer) | 10 | Edge worker types |
| Pre-hire (within 14-day window) | 30 | D2.7 pre-hire branch |
| Pre-hire (15–60 days out) | 10 | Deferral branch |
| Pre-hire (rescinded) | 5 | D2.7 §6.1 cleanup |
| Mover — department change | 30 | OrgPath cascade |
| Mover — manager change | 30 | Notification + access review trigger |
| Mover — title change | 20 | Title-bound group memberships |
| Mover — location change (cross-region) | 15 | usageLocation + license region |
| Mover — name change | 10 | UPN preservation rule |
| Leaver (active → terminated) | 50 | D2.3 11-step disable sequence |
| Leaver (manager of N direct reports) | 10 | Direct-report reassignment |
| Leaver (with delegated mailbox) | 5 | Delegation cleanup edge case |
| Rehire (Path A — within retention) | 15 | Reactivation |
| Rehire (Path B — past retention) | 5 | New-record-with-prior-link |
| Conversion (Contractor → FTE) | 15 | License tier change |
| Conversion (FTE → Contractor) | 10 | Reverse |
| Conversion (Intern → FTE) | 5 | Internship-to-employee |
| LOA / OnLeave | 10 | D2.8 §4.1 — flag, not Leaver |
| Multiple positions (matrix org) | 5 | Edge case; typically out-of-scope but exercises the schema |
| Bad-data: missing required field | 5 | D2.6 quarantine routing |
| Bad-data: stale `extracted_at` | 3 | Freshness SLA |
| Bad-data: `manager-stale` | 3 | Referential integrity |
| Bad-data: codebook miss | 3 | OrgPath calculator failure |
| Bad-data: UPN collision | 3 | UPN generator collision |
| Bad-data: workerType-unknown | 2 | D1.6 enum violation |
| Bad-data: usage-location-missing | 2 | License region failure |
| Records with non-ASCII names (diacritic preservation) | 10 | Internationalization |
| Records spanning 5 fictional agencies | 5 (parallel sets) | Multi-source-agency tests |
| Filler records (clean Joiner) | balance | Pad to 500 |

The exact distribution may shift; the canonical posture is:
**>=80% clean records, <=20% deliberate failures**, all categories
represented at >=1 record.

## 3. Scenario Coverage Matrix

Every D2.x workflow has at least one test record that exercises it:

| Workflow | D4.1 record count | D4.2 test coverage |
|---|---|---|
| D2.1 Joiner — pre-hire / day-of-hire / post-hire correction | 245 (joiner + pre-hire categories) | All three modes |
| D2.2 Mover — dept / manager / title / location / name | 105 | All five Mover trigger types |
| D2.3 Leaver — 11-step sequence including direct-report reassign + delegation cleanup | 65 | Sequence executes top-to-bottom |
| D2.4 Rehire — Path A + Path B | 20 | Both paths |
| D2.5 Conversion — contractor↔FTE + intern→FTE | 30 | Multiple conversion paths |
| D2.6 Quarantine — every failure_reason class | 21 (bad-data records) | Every class in §2 of D2.6 |
| D2.7 Pre-hire window — in-window / deferred / rescinded | 45 | All three branches |
| D2.8 Scope filter — LOA / sabbatical / multi-position | 15+ | Edge cases that pass / fail filter |

## 4. Format

The fixture lives in two parallel formats:

```
tests/fixtures/spec2-d4.1/
├── canonical-records.json     # JSON — UIAO middleware ingest path
└── canonical-records.csv      # CSV — alternative format for spreadsheet review
```

Both formats are the source-of-truth; they are generated together
and any update touches both. The JSON shape conforms to D1.1's
canonical schema (one object per record).

### 4.1 JSON shape

```json
[
  {
    "employeeId": "TEST-EMP-00001",
    "firstName": "Aria",
    "lastName": "Müller",
    "displayName": "Müller, Aria",
    "email": "aria.muller@test.uiao.local",
    "department": "Office of Personnel Management",
    "division": "HRIT",
    "jobTitle": "Senior Software Engineer",
    "managerEmployeeId": "TEST-EMP-00789",
    "hireDate": "2026-04-15",
    "terminationDate": null,
    "workerType": "FullTimeEmployee",
    "locationCode": "US-DC",
    "costCenter": "CC-1234",
    "organizationCode": "GOV-EXEC-OPM",
    "country": "US",
    "employmentStatus": "Active",
    "phoneNumber": "+1-202-555-0100",
    "addresses": [
      { "type": "work", "streetAddress": "1900 E St NW",
        "locality": "Washington", "region": "DC",
        "postalCode": "20415", "country": "US" }
    ],
    "extracted_at": "2026-05-02T08:00:00Z",
    "adapter_metadata": {
      "source_system": "test-fixture",
      "scenario_class": "joiner-fte-clean"
    }
  }
]
```

### 4.2 CSV shape

Standard flat CSV with the same field set; nested fields
(addresses) are flattened to `addresses_0_streetAddress`,
`addresses_0_locality`, etc. The header row matches D1.1 field
names.

## 5. Synthetic-Data Safety

The fixture MUST satisfy:

| Constraint | Rule |
|---|---|
| No real PII | `firstName` / `lastName` from a public-domain fictional name list |
| No real SSNs | Numeric employeeId pattern `TEST-EMP-NNNNN`; never resembles SSN |
| No real emails | All `@test.uiao.local` domain |
| No real phone numbers | All in 555-01XX exchange (NANPA-reserved fictional range) |
| No real addresses | All from a public-domain test-address corpus |
| Diacritic test names | Per-region public-domain names with valid diacritics |
| `adapter_metadata.scenario_class` | REQUIRED; names which scenario the record exercises |

The fixture is committed to source control and is non-secret.

## 6. Provenance + Versioning

The fixture carries a header sidecar:

```yaml
# tests/fixtures/spec2-d4.1/META.yaml
fixture_id: spec2-d4.1
version: 0.1
record_count: 500
generated_at: 2026-05-02T08:00:00Z
generator: hand-curated
checksum: <SHA-256 of canonical-records.json>
scenarios_covered:
  - joiner-fte-clean: 100
  - joiner-pte: 30
  # ... (full enumeration)
```

The checksum makes drift detectable: if the fixture is modified
without bumping the version, CI's fixture-integrity check fails.

## 7. Multi-Agency Variant

For tenants whose deployments span multiple agencies, D4.1 also
ships a 5-agency parallel-set variant:

- 5 fictional agencies with their own department codebooks.
- 100 records per agency.
- Cross-agency manager links (test the "manager in different
  source") edge case.

This variant is OPTIONAL — single-agency deployments do not need
it.

## 8. Update Cadence

The canonical fixture is updated when:

1. New scenario classes emerge (e.g., D2.x specs add a workflow).
2. New `failure_reason` values are added (D2.6 §10 stability rule).
3. A bug surfaces in production whose test coverage was missing —
   the fixture is updated with a record that would have caught
   it.

Updates require:

- Bumping the fixture's `version` in META.yaml.
- Recomputing checksum.
- Rerunning the full D4.2 integration test suite to confirm no
  regressions.

## 9. References

### 9.1 Primary canon

- [ADR-003](../adr/adr-003-api-driven-inbound-provisioning.md)

### 9.2 UIAO docs

- [UIAO_136](../UIAO_136_priority1-transformation-project-plans.md) — §SPEC 2 → Phase 4 → D4.1.

### 9.3 Spec 2 sister deliverables

- [Spec2-D1.1 — Canonical HR Attribute Schema](./Spec2-D1.1-CanonicalHRAttributeSchema.md) — fixture conforms to this schema.
- [Spec2-D1.6 — Worker Type Classification Taxonomy](./Spec2-D1.6-WorkerTypeClassificationTaxonomy.md) — `workerType` enum.
- [Spec2-D4.2 — Integration Test Plan](./Spec2-D4.2-IntegrationTestPlan.md) — consumes this fixture.
- [Spec2-D4.3 — Performance & Scale Test Plan](./Spec2-D4.3-PerformanceScaleTestPlan.md) — extends this fixture for load testing.
- [Spec2-D4.4 — UAT Acceptance Criteria](./Spec2-D4.4-UATAcceptanceCriteria.md) — pass/fail per record per scenario.

### 9.4 Compliance

- NIST SP 800-53 Rev 5: SA-11 (developer security testing — the test fixture is a developer-test artifact).
