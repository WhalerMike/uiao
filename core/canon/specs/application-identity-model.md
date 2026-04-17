---
document_id: UIAO_129
title: "UIAO Application Identity Model"
version: "1.0"
status: Current
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-17"
updated_at: "2026-04-17"
boundary: "GCC-Moderate"
---

# UIAO Application Identity Model

## 1. Overview

The Application Identity Model treats every application as a
first-class identity primitive that is authoritative across
naming, addressing, authentication, policy, telemetry, and
enforcement. An application is not a set of IPs, VLANs, or
tenant bindings — it is a canonical identity object with
deterministic bindings to each of those surfaces.

This spec defines the primitive, its authoritative bindings,
its lifecycle, and the drift classes that apply when any
binding diverges from canon. It sits under UIAO_003 (Adapter
Segmentation Overview) and is consumed by UIAO_112 (Multi-
Tenant Isolation), UIAO_113 (Evidence Graph), UIAO_116
(Enforcement Policy Language), and UIAO_120 (Zero-Trust
Integration Layer). Its operational counterpart is UIAO_130
(Application Identity Onboarding Runbook).

## 2. The Application Identity Primitive

An Application Identity is a canonical object with six required
bindings:

| Binding | Authority | Example |
|---|---|---|
| Canonical DNS name | DNS authority (IPAM-managed) | `payroll.agency.gov` |
| Address space | IPAM | `10.42.0.0/24` + cloud VPC/VNet prefix |
| Workload identity | IAM | SPIFFE ID, managed identity, service principal |
| Trust anchor | Certificate / token service | mTLS cert + SAN; OIDC/JWT |
| Segmentation label | Policy Engine | overlay segment / microsegment ID |
| Logical location | Registry | region / cloud / SDN fabric / SD-WAN zone |

All six are required. An application missing any binding is a
DRIFT-IDENTITY finding (see §7).

## 3. Authoritative Bindings

Each binding has exactly one authority. Authority is declared
in `core/canon/adapter-registry.yaml` and is the only place
that may be the source of truth for that binding. Overlays
and enforcement points consume the binding — they do not
define it.

- **DNS binding** — IPAM-managed zone; changes auditable and
  tied to ownership.
- **Address binding** — IPAM authoritative; reconciled against
  cloud-native VPC/VNet records.
- **IAM binding** — identity issued with short-lived
  credentials and automated rotation; workload metadata
  (owner, environment, allowed peers) consumed by the Policy
  Engine.
- **Trust binding** — mTLS for persistent high-assurance flows
  (service mesh); OAuth/OIDC for ephemeral API calls and
  cross-domain integrations. Binding cryptographically ties
  DNS name + workload identity to the application identity.
- **Segmentation binding** — Policy Engine publishes label;
  Control Plane translates to overlay enforcement.
- **Location binding** — used for locality-aware routing,
  data residency, multiregion failover. Location telemetry
  may contain PII; see UIAO_004 privacy requirements.

## 4. Lifecycle

Five states, all transitions logged to the evidence graph
(UIAO_113):

1. **Proposed** — requested in the onboarding runbook
   (UIAO_130); naming and address reserved but not bound.
2. **Provisioned** — all six bindings created; not yet
   reachable.
3. **Active** — enforcement points routing traffic; telemetry
   flowing; policy evaluated continuously.
4. **Quarantined** — a binding failure or drift finding has
   moved the application out of production path; forensic
   evidence retained.
5. **Retired** — bindings deallocated; address released after
   hold-down; certificates revoked; identity decommissioned.

Each transition requires a signed state change event in the
evidence graph. Quarantine transitions are tied to a drift
finding ID.

## 5. Policy Objects

Application identity is the primary policy object for:

- allow/deny connectivity between applications (not between
  subnets)
- SLA / QoS class assignment
- locality / residency constraints
- Zero-Trust evaluation envelopes (identity + device posture +
  session claims; see UIAO_120)

Subnets and IPs are never policy objects. Rules that reference
subnets are a DRIFT-AUTHZ finding.

## 6. Telemetry Mapping

Every telemetry event — flow record, policy decision, enforcement
action, failover event — must carry the application identity as
a first-class grouping key. Events emitted without application
identity are incomplete and logged as DRIFT-PROVENANCE findings.

The mapping between event types and required application-identity
fields is declared in UIAO_113 (Graph Schema).

## 7. Drift Classes

| Class | Trigger | Severity |
|---|---|---|
| DRIFT-SCHEMA | Application record missing a required binding | P2 |
| DRIFT-IDENTITY | Workload presents identity not bound to canonical DNS name | P1 |
| DRIFT-AUTHZ | Policy rule references subnet/IP instead of application identity | P2 |
| DRIFT-PROVENANCE | Telemetry event missing application-identity grouping key | P3 |
| DRIFT-SEMANTIC | Binding value differs between authority and consumer | P2 |

Detection runs continuously in the drift engine (UIAO_110).

## 8. Cross-References

- UIAO_003 — Adapter Segmentation Overview (taxonomy parent)
- UIAO_110 — Drift Engine (detection runtime)
- UIAO_112 — Multi-Tenant Isolation (tenant boundary)
- UIAO_113 — Evidence Graph (event schema)
- UIAO_116 — Enforcement Policy Language (policy expression)
- UIAO_120 — Zero-Trust Integration Layer (consumer)
- UIAO_130 — Application Identity Onboarding Runbook (operational)
- UIAO_131 — Adapter Test Strategy (conformance for bindings)
- ADR-030 — Pre-UIAO Terminology Reconciliation (vocabulary
  authorizing this spec)
