---
document_id: UIAO_130
title: "UIAO Application Identity Onboarding Runbook"
version: "1.0"
status: Current
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-17"
updated_at: "2026-04-17"
boundary: "GCC-Moderate"
---

# UIAO Application Identity Onboarding Runbook

## 1. Overview

This runbook defines the canonical sequence for bringing a new
application onto the UIAO substrate as a first-class identity
object. It is the operational counterpart to UIAO_129
(Application Identity Model). Onboarding produces one fully-bound
application identity with all six bindings required by
UIAO_129 §2, a signed state-change event in the evidence graph
(UIAO_113), and a green drift scan across all five drift classes.

The runbook is used by agency operators following the Operator
track of UIAO_125, and by contributors testing a new adapter
against the substrate fixtures.

## 2. Preconditions

Before onboarding begins, the following must be in place:

1. **Canon available.** `$UIAO_WORKSPACE_ROOT` resolves; `uiao
   substrate walk` exits clean with no DRIFT-SCHEMA or
   DRIFT-PROVENANCE findings.
2. **Authority Plane reachable.** IPAM, IAM, Certificate / Token
   Services, and Policy Engine endpoints respond to health checks.
   Their adapter conformance status is green per UIAO_121 (with
   tier evidence per UIAO_131).
3. **Owner declared.** The application has a named owner with
   write access to the onboarding request queue and the evidence
   graph.
4. **Naming decision made.** The canonical DNS name (per UIAO_129
   §2 first binding) is decided and documented. Subdomain follows
   the agency's delegation policy.
5. **Governance findings reviewed.** If any open finding in
   `docs/findings/` blocks a capability required for this
   application, the finding is acknowledged in the onboarding
   request and the application is either (a) scoped to avoid the
   blocked capability or (b) put on hold pending finding
   resolution.

## 3. State sequence

The runbook drives the lifecycle defined in UIAO_129 §4. Each
step ends with a state-change event signed into the evidence
graph; the next step is gated on the prior event's cryptographic
verification.

### 3.1 Proposed

Operator files an onboarding request with: canonical DNS name
proposal, requested address prefix, IAM tenant, intended trust
anchor type (mTLS or OIDC), proposed segmentation label, and
logical location.

Gate: naming policy validator (agency-specific).
Output: `proposed` event in evidence graph.

### 3.2 Provisioned

All six UIAO_129 §2 bindings are created:

1. DNS zone / record via IPAM adapter.
2. Address prefix allocated; cloud-native VPC/VNet reconciliation
   confirmed.
3. IAM workload identity issued (short-lived credentials; rotation
   configured).
4. Trust anchor created (mTLS cert issued with DNS SAN, or OIDC
   client registered with JWT issuer).
5. Segmentation label published by Policy Engine.
6. Logical location attributes registered.

Gate: all six bindings return success from their authority's
conformance check (UIAO_121).
Output: `provisioned` event; drift scan runs automatically — must
return zero findings across DRIFT-SCHEMA, DRIFT-IDENTITY,
DRIFT-AUTHZ, DRIFT-PROVENANCE, DRIFT-SEMANTIC.

### 3.3 Active

Enforcement points pick up the segmentation label; traffic flows;
telemetry begins emitting events tagged with the application
identity.

Gate: first 100 telemetry events arrive correctly tagged (no
DRIFT-PROVENANCE findings on application-identity grouping key).
Gate: Zero-Trust evaluation returns `permit` for authorized
peers, `deny` for unauthorized peers.
Output: `active` event.

### 3.4 Quarantined (conditional)

Entered only on drift finding P2 or higher, or on explicit
operator quarantine. All traffic to the application is diverted
to a forensic path; bindings remain in place; evidence is
preserved. The application is still reachable by the
investigation team but not in the production path.

Gate: quarantine envelope verified (network ACL + DNS change).
Output: `quarantined` event; drift finding ID attached;
investigation ticket opened.

### 3.5 Retired

Bindings deallocated in reverse-provisioning order. Address
released after configured hold-down; certificate revoked; IAM
identity decommissioned; DNS record removed; segmentation label
deleted.

Gate: all adapters confirm deallocation; no orphan bindings
detectable via `uiao substrate drift`.
Output: `retired` event; evidence graph retains full state
history for the audit retention window declared in UIAO_004.

## 4. Rollback

Each provisioned step has a defined rollback that restores the
prior state and emits a compensating event. Rollback is invoked
on:

- any Authority Plane adapter returning `unavailable` during
  provisioning
- drift scan returning P1 finding post-provisioned but
  pre-active
- operator abort during the onboarding window

Rollback never deletes evidence graph events — it emits
compensating events so the ledger is append-only.

## 5. Evidence outputs

Each application identity onboarding produces:

1. Signed events in the evidence graph for each state transition.
2. A per-application OSCAL-native evidence bundle referenced
   from UIAO_113, usable in SAR / POA&M generation.
3. A drift-scan baseline that subsequent runs compare against.
4. A provenance record naming the onboarding operator, the
   runbook version, and the exact timestamp of each state change.

## 6. Operator commands

```bash
uiao app propose --name payroll.agency.gov --owner "Payroll Team"
uiao app provision --name payroll.agency.gov
uiao app activate --name payroll.agency.gov
uiao app status --name payroll.agency.gov          # any state
uiao app quarantine --name payroll.agency.gov --finding DRIFT-IDENTITY-P1-42
uiao app retire --name payroll.agency.gov --confirm
```

Each command returns exit 0 on success and a non-zero drift-class
code on failure; the codes map to the five drift classes in
UIAO_129 §7.

## 7. Failure modes and handling

| Failure | Detection | Remediation |
|---|---|---|
| IPAM unreachable during provisioning | adapter health check fails | rollback; retry after IPAM restored |
| IAM issued identity without required metadata | DRIFT-SCHEMA on first telemetry event | rollback; fix IAM adapter configuration |
| Certificate SAN does not match canonical DNS name | DRIFT-IDENTITY on first mTLS handshake | rollback; reissue certificate |
| Policy rule references IP instead of identity | DRIFT-AUTHZ on first policy evaluation | block activation; fix rule; retry |
| Telemetry event missing application-identity key | DRIFT-PROVENANCE on first event | block activation; fix adapter mapping; retry |
| Binding value differs between authority and consumer | DRIFT-SEMANTIC on reconciliation run | open investigation; do not activate until resolved |

## 8. Cross-references

- UIAO_003 — Adapter Segmentation Overview
- UIAO_110 — Drift Engine Specification
- UIAO_113 — Evidence Graph Model (event schema)
- UIAO_120 — Zero-Trust Integration Layer (consumer)
- UIAO_121 — Adapter Conformance Test Plan — Template
- UIAO_124 — Adapter Operations Runbook (parent operational context)
- UIAO_125 — Training Program (Operator track curriculum)
- UIAO_129 — Application Identity Model (declarative spec)
- UIAO_131 — Adapter Test Strategy (tier evidence for bindings)
- UIAO_200 — Substrate Manifest
- `docs/findings/` — governance findings that may block specific
  capabilities required for onboarding
- ADR-030 — Pre-UIAO Terminology Reconciliation (authorizes this
  runbook as canon)
