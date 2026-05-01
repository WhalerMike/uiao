---
deliverable_id: Spec2-D3.5
title: "OrgPath Population Pipeline"
spec: UIAO_136 / Spec 2 — HR-Agnostic Provisioning Architecture
phase: 3
status: Draft
version: 0.1
owner: Identity Architecture
created: 2026-05-01
updated: 2026-05-01
canonical_adrs:
  - ADR-003
  - ADR-035
  - ADR-036
  - ADR-037
  - ADR-038
  - ADR-039
  - ADR-040
  - ADR-048
canonical_docs:
  - UIAO_007
  - UIAO_135
  - UIAO_136
upstream_deliverables:
  - Spec2-D1.2
  - Spec2-D3.1
  - Spec2-D3.2
  - Spec2-D3.4
sibling_deliverables:
  - Spec2-D3.7
boundary: GCC-Moderate
classification: Controlled
---

# Spec 2 — D3.5: OrgPath Population Pipeline

> **Status (v0.1, 2026-05-01):** Initial draft. The pipeline this
> document describes is the load-bearing identity-attribute
> primitive for the OrgTree (per ADR-035 / ADR-048). v0.2
> verification will reconcile the cascade timings against
> Microsoft Entra dynamic-group rule-evaluation latency
> documentation.

## 1. Purpose, Scope, and Reference

This deliverable is the canonical OrgPath Population Pipeline
specification called for in
[`UIAO_136`](../UIAO_136_priority1-transformation-project-plans.md)
§SPEC 2 → Phase 3 → D3.5:

> *End-to-end specification: HR org hierarchy → middleware →
> OrgPath calculation → extensionAttribute/custom security
> attribute write → dynamic group membership cascade → policy
> assignment cascade.*

OrgPath is the single most-load-bearing UIAO attribute. Per
ADR-035 (codebook binding) + ADR-048 (attribute selection),
OrgPath is stamped on every Entra ID identity (user, device, and
ultimately service principal) and read by the OrgTree adapters
(MOD_B / C / D / N — ADR-036 / ADR-037 / ADR-038 / ADR-039) to
drive group membership, admin-unit scoping, device-plane
propagation, and policy targeting.

D3.5 is the end-to-end specification of how an HR org-hierarchy
fact becomes an OrgPath cascade observable across the OrgTree.

### 1.1 Scope

In scope:

- The end-to-end pipeline from HR ingestion → OrgPath presence
  in `extensionAttribute1` → dynamic-group membership change →
  policy-targeting evaluation.
- The cascade timings (each stage's latency).
- The version-stamping rules (calculator version captured in
  every record's provenance).
- The drift-detection contract (ADR-040 binding).
- Edge cases: re-org events, codebook updates, manual operator
  attribute overrides.

Out of scope:

- The OrgPath codebook itself (ADR-035 + D1.2).
- The attribute mapping engine (D3.4).
- The middleware (D3.2; D3.5 is downstream of D3.2's OrgPath
  calculator sub-component).
- Per-adapter logic for MOD_B / C / D / N (each has its own ADR).

## 2. The Pipeline Stages

```
Stage 0: HR system has the canonical org hierarchy
         (department, division, location, cost center, organization)
              │
              │  (per-source HR adapter)
              ▼
Stage 1: Canonical D1.1 record at the middleware boundary
              │
              │  (D3.2 §3.2 OrgPath calculator + ADR-035 codebook)
              ▼
Stage 2: OrgPath string computed (e.g., "GOV/EXEC/OPM/HRIT")
              │
              │  (D3.2 §3.5 SCIM payload builder)
              ▼
Stage 3: SCIM payload with extensionAttribute1 = OrgPath
              │
              │  (D3.1 §5 bulkUpload)
              ▼
Stage 4: Entra ID provisioning service writes user.extensionAttribute1
              │
              │  (Entra dynamic-group engine; MOD_B / ADR-036)
              ▼
Stage 5: Dynamic group memberships recompute
              │
              │  (Entra group cascade)
              ▼
Stage 6: Group-scoped policies (Intune, Azure Policy, CA — MOD_N / ADR-039)
         re-evaluate target users
              │
              │  (Entra admin-units evaluator; MOD_D / ADR-037)
              ▼
Stage 7: Administrative-unit membership (when AU is OrgPath-bound) updates
              │
              │  (Device plane; MOD_C / ADR-038)
              ▼
Stage 8: Device-side OrgPath propagation (Entra device + Arc machine ARM tag)
              │
              ▼
[Drift engine; ADR-040 — observes stages 4 → 8 for inconsistencies]
```

## 3. Per-Stage Latency Profile

The cumulative cascade is asynchronous; each stage has a
characteristic latency. UIAO's planning assumptions:

| Stage | Latency target | Source |
|---|---|---|
| 1 → 2 (middleware compute) | <100 ms per record | Middleware in-process |
| 2 → 3 (SCIM assembly) | <50 ms per record | Middleware in-process |
| 3 → 4 (bulkUpload + provisioning service) | seconds; up to a few minutes for batch processing | Microsoft async; per D3.1 §3.4 verification |
| 4 → 5 (dynamic group recompute) | seconds to ~10 minutes | Microsoft documented as "near real time"; UIAO planning value: 10 min p95 |
| 5 → 6 (policy targeting) | minutes for Intune / hours for some Azure Policy cases | Per-policy-engine |
| 5 → 7 (AU recompute when OrgPath-bound) | seconds to minutes | Per Microsoft docs |
| 4 → 8 (device-plane propagation) | minutes; depends on device check-in cadence | Per MOD_C / ADR-038 |

**Cumulative end-to-end** (typical): a single HR-side org change
becomes observable in dynamic group membership within ~15
minutes p95, in Intune policy targeting within ~30 minutes p95,
and in device-plane Arc machine tags within an hour p95.

These are operational planning values, NOT contractual SLAs.
Microsoft does not publish hard latency SLAs for these cascades;
UIAO's drift engine treats deviations beyond 2× the planning
value as DRIFT-PROVENANCE findings.

## 4. Version Stamping

Every record's provenance (D3.1 §8.2) MUST carry:

```yaml
middleware:
  version: <middleware semver>
  orgpath_calculator_version: <calculator semver>
  upn_generator_version: <UPN gen semver>
  worker_type_taxonomy_version: <D1.6 semver>
```

The OrgPath value AND its calculator version are the joint anchor
for drift detection. A user whose stored OrgPath was emitted by
calculator v1.0 but the current calculator is v1.1 is a candidate
DRIFT-PROVENANCE finding; the drift engine evaluates whether the
two versions produce the same OrgPath for the user's current HR
attributes, and surfaces only genuine differences.

## 5. Re-Org Event Handling

A "re-org" is an HR-side organizational change affecting >100
records in a single sync cycle (tenant-policy threshold). The
middleware MUST detect these and:

1. Emit `provisioning.scope.reorg-detected` provenance event with
   the count of affected records.
2. Throttle the SCIM bulkUpload rate to prevent overwhelming the
   downstream cascade (rate limit applies regardless, but the
   middleware lengthens batch intervals).
3. Pre-warn the operator surface (the dynamic-group cascade for a
   re-org of 1,000 records may take an hour to settle; ops should
   know).
4. Continue normal processing — re-org is not an exceptional
   workflow, just a high-volume one.

## 6. Codebook Update Handling

When the OrgPath codebook (ADR-035) is updated:

1. The codebook update lands as a governance change with its own
   ADR or registry entry.
2. The middleware reads the new codebook on next startup or
   hot-reload (per implementation).
3. The next sync cycle MAY produce different OrgPath values for
   the same HR records (new codebook → new mapping).
4. Each affected record emits a provenance event with the new
   codebook version stamped in `middleware.orgpath_calculator_version`.
5. The drift engine identifies the codebook-version flip and
   generates a `codebook-update` aggregate finding rather than
   per-record drift findings (single root cause).

## 7. Manual Operator Override

In rare cases, an operator may need to set OrgPath manually
(e.g., for a sensitive matrix-organization role where the
codebook-derived value is wrong). UIAO's posture:

- Manual override is a **tenant-policy decision**, not a
  middleware default.
- When tenant policy permits it, manual overrides are written
  via a dedicated CLI (`uiao orgpath set <employeeId> <value>`),
  which emits its own `provisioning.orgpath.manual-override`
  provenance event with operator identity, justification, and
  expiration.
- The middleware MUST detect manual-overridden records on
  subsequent syncs and NOT recompute their OrgPath (respect the
  override) UNTIL the override expires.
- Override expiration: 30 days default, configurable; MUST emit
  `provisioning.orgpath.override-expired` when reverting to
  codebook value.

## 8. Drift Detection Contract

ADR-040 names the drift engine. D3.5's contract with the drift
engine:

| Drift class | Trigger |
|---|---|
| `DRIFT-IDENTITY` | A user's stored OrgPath does not match what the current calculator produces from current HR attributes |
| `DRIFT-PROVENANCE` | A record's emitted-calculator-version is older than the deployed-calculator-version AND the calculation results would differ |
| `DRIFT-SCHEMA` | An identity is missing the OrgPath attribute (extensionAttribute1 is null) when scope/filter rules say it should be populated |
| `DRIFT-AUTHZ` | A dynamic group's membership disagrees with what its rule should evaluate against current users' OrgPath values |
| `DRIFT-SEMANTIC` | An admin-unit's membership / a policy's targeting disagrees with the dynamic group's membership (cascade incomplete) |

The drift engine emits findings per its own canonical event shape;
D3.5 only commits to providing the upstream version stamps and
deterministic calculator behavior.

## 9. Cascade Health Monitoring

D3.7 binds alerts on the cascade-stage latencies above.
Specifically:

- **Stage 4 → 5 (group recompute)** — alert if any record's
  emitted OrgPath is not reflected in dynamic group membership
  within 2× the planning value (20 min p95 → 40 min hard alert).
- **Stage 5 → 6 (policy targeting)** — alert if Intune policy
  target lists do not reflect the new dynamic group membership
  within 2× the planning value.
- **Stage 4 → 8 (device propagation)** — same pattern.

The alerts are actionable: persistent stage-4-to-5 lag indicates
either a tenant-side rule-evaluation issue or a Microsoft-side
cascade slowdown. Alerts include the stage name, affected record
count, and the time the cascade has been pending.

## 10. References

### 10.1 Primary canon

- [ADR-003](../adr/adr-003-api-driven-inbound-provisioning.md)
- [ADR-035](../adr/adr-035-orgpath-codebook-binding.md)
- [ADR-036](../adr/adr-036-dynamic-group-provisioning.md) — MOD_B; consumes Stage 4 output.
- [ADR-037](../adr/adr-037-admin-unit-provisioning.md) — MOD_D; consumes Stage 4 / 7.
- [ADR-038](../adr/adr-038-device-plane-orgpath.md) — MOD_C; consumes Stage 4 / 8.
- [ADR-039](../adr/adr-039-policy-targeting.md) — MOD_N; consumes Stage 6.
- [ADR-040](../adr/) — drift engine.
- [ADR-048](../adr/adr-048-orgpath-attribute-storage-decision.md) — extensionAttribute1 selection.

### 10.2 UIAO docs

- [UIAO_007](../UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md)
- [UIAO_136](../UIAO_136_priority1-transformation-project-plans.md) — §SPEC 2 → Phase 3 → D3.5.

### 10.3 Spec 2 sister deliverables

- [Spec2-D3.1](./Spec2-D3.1-APIDrivenInboundProvisioningArchitecture.md) — substrate.
- [Spec2-D3.2](./Spec2-D3.2-IntegrationMiddlewareSpecification.md) — owns Stage 1–3.
- [Spec2-D3.4](./Spec2-D3.4-AttributeMappingEngineConfiguration.md) — direct-mapping for `extensionAttribute1`.
- [Spec2-D3.7](./Spec2-D3.7-MonitoringAlertingConfiguration.md) — cascade-stage alerting rules.
- Spec2-D1.2 — HR-to-OrgPath translation rules (forthcoming).

### 10.4 Microsoft documentation (verification pending in v0.2)

- Microsoft Learn — Microsoft Entra dynamic group rule-evaluation latency.
- Microsoft Learn — Administrative units membership-rule semantics.
- Microsoft Learn — Intune assignment evaluation timing.

### 10.5 Compliance

- NIST SP 800-53 Rev 5: AC-2, AC-3 (the OrgPath drives access enforcement decisions), AU-2 (cascade observability).
